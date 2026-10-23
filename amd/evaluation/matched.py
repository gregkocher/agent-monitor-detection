"""Matched-budget evaluation: every detector gets the same trajectory-level FPR budget.

Protocol (per repeated random split):
  1. Split honest trajectories into calibration / test (optionally grouped by task/context so
     no group is in both). If any detector is supervised, split attacks into fit / test; all
     detectors are scored on the same attack-test set.
  2. Calibration statistics are cross-fitted: the honest calibration set is cut into K folds,
     the detector (its per-unit transform and any learned aggregator state) is fit on K-1
     folds and the held-out fold's trajectory statistics are computed. Honest-test and
     attack-test trajectories are each scored by one of the same K fold models, chosen at
     random (score_with="folds", default), so every statistic comes from a model that never
     saw that trajectory and calibration / test statistics are exchangeable within each fold
     model, including their tie structure for discrete scores. score_with="full" instead
     refits on the whole calibration set to score test / attack trajectories (slightly more
     power, but cross-fit jitter then breaks ties between calibration and test statistics,
     which matters for integer scores and randomized thresholds). crossfit <= 1 uses one
     in-sample fit for everything (calibration p-values then include the unit itself).
  3. For each alpha, the threshold is the conformal (1 - alpha) quantile of the cross-fitted
     calibration statistics (or the plug-in randomized threshold). TPR = alarm rate on attack
     test; realized FPR = alarm rate on honest test.
  4. Uncertainty: B bootstrap replicates per split resample calibration, honest-test and
     attack-test trajectories independently (stratified by role), optionally by cluster
     (group); the threshold is recomputed in every replicate. Percentile CIs pool the
     replicates of all splits; point estimates average the splits.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..detectors.base import Detector, Packed, pack
from .calibration import RowThresholds, Threshold, calibrate, get_threshold_convention, row_thresholds


# ------------------------------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------------------------------


def crossfit_models(det: Detector, Ph: Packed, k: int = 5, rng=None, Pa: Packed | None = None,
                    attack_onsets=None):
    """Fit K fold models; return (models, out-of-fold calibration statistics).
    k <= 1: a single in-sample model."""
    rng = np.random.default_rng(rng)
    if k is None or k <= 1:
        d = det.clone()._fit_packed(Ph, Pa, attack_onsets)
        return [d], d.stats_packed(Ph)
    folds = np.array_split(rng.permutation(Ph.n), k)
    out = np.empty(Ph.n)
    models = []
    for f in folds:
        train = np.setdiff1d(np.arange(Ph.n), f)
        d = det.clone()._fit_packed(Ph.subset(train), Pa, attack_onsets)
        out[f] = d.stats_packed(Ph.subset(f))
        models.append(d)
    return models, out


def crossfit_stats(det: Detector, Ph: Packed, k: int = 5, rng=None, Pa: Packed | None = None,
                   attack_onsets=None) -> np.ndarray:
    """Out-of-fold trajectory statistics for the honest calibration set (k <= 1: in-sample)."""
    return crossfit_models(det, Ph, k, rng, Pa, attack_onsets)[1]


def score_with_models(models: list[Detector], P: Packed, rng=None) -> np.ndarray:
    """Score each trajectory with one fold model chosen uniformly at random."""
    rng = np.random.default_rng(rng)
    if len(models) == 1:
        return models[0].stats_packed(P)
    which = rng.integers(len(models), size=P.n)
    out = np.empty(P.n)
    for j, m in enumerate(models):
        idx = np.flatnonzero(which == j)
        if len(idx):
            out[idx] = m.stats_packed(P.subset(idx))
    return out


def _split(n, frac, rng, groups=None):
    if groups is None:
        perm = rng.permutation(n)
        m = int(round(frac * n))
        return np.sort(perm[:m]), np.sort(perm[m:])
    groups = np.asarray(groups)
    ug = rng.permutation(np.unique(groups))
    m = int(round(frac * len(ug)))
    a = np.isin(groups, ug[:m])
    return np.flatnonzero(a), np.flatnonzero(~a)


def bootstrap_weights(n: int, B: int, rng, groups=None) -> np.ndarray:
    """(B, n) integer multiplicities: iid trajectory bootstrap, or cluster bootstrap if groups."""
    if n == 0:
        return np.zeros((B, 0))
    if groups is None:
        return rng.multinomial(n, np.full(n, 1.0 / n), size=B).astype(float)
    groups = np.asarray(groups)
    ug, inv = np.unique(groups, return_inverse=True)
    G = len(ug)
    Wg = rng.multinomial(G, np.full(G, 1.0 / G), size=B).astype(float)
    return Wg[:, inv]


def _boot_threshold(sorted_cal: np.ndarray, Wc: np.ndarray, alpha: float, method: str):
    """Per-replicate threshold (h, gamma) from weighted calibration statistics (plug-in randomized or
    conformal rule). The conformal randomized rule is not an (h, gamma) pair: use
    calibration.row_thresholds, which covers every rule."""
    if method == "randomized" and get_threshold_convention() != "plugin":
        raise ValueError("_boot_threshold implements only the plug-in randomized rule; under the "
                         "'conformal' convention use amd.evaluation.calibration.row_thresholds")
    if method == "randomized_plugin":
        method = "randomized"
    vals, inv = np.unique(sorted_cal, return_inverse=True)
    Wu = np.zeros((Wc.shape[0], len(vals)))
    np.add.at(Wu.T, inv, Wc.T)
    m = Wu.sum(axis=1)
    cw = np.cumsum(Wu, axis=1)
    B = Wc.shape[0]
    if method == "conformal":
        k = np.ceil((1 - alpha) * (m + 1) - 1e-12)
        idx = (cw < k[:, None]).sum(axis=1)
        h = np.where(k <= m, vals[np.minimum(idx, len(vals) - 1)], np.inf)
        return h, np.zeros(B)
    target = alpha * m
    gt = m[:, None] - cw
    j = (gt > target[:, None] + 1e-9).sum(axis=1)  # first unique value with gt <= target
    j = np.minimum(j, len(vals) - 1)
    rows = np.arange(B)
    h = vals[j]
    gamma = np.clip((target - gt[rows, j]) / np.maximum(Wu[rows, j], 1e-12), 0, 1)
    return h, gamma


def _boot_rate(stats, W, h, gamma=None):
    """Weighted alarm rate per replicate; h is an (h, gamma) pair's h array or a RowThresholds."""
    if isinstance(h, RowThresholds):
        A = h.alarm(stats)
    else:
        A = (stats[None, :] > h[:, None]) + gamma[:, None] * (stats[None, :] == h[:, None])
    return (A * W).sum(axis=1) / np.maximum(W.sum(axis=1), 1)


# ------------------------------------------------------------------------------------------
# main entry point
# ------------------------------------------------------------------------------------------


def matched_budget_eval(
    detectors: dict[str, Detector],
    honest,
    attack,
    alphas=(1e-2, 3e-3, 1e-3),
    honest_contexts=None,
    attack_contexts=None,
    attack_onsets=None,
    honest_groups=None,
    attack_groups=None,
    group_split: bool = True,
    n_splits: int = 5,
    cal_frac: float = 0.5,
    attack_fit_frac: float | None = None,
    crossfit: int = 5,
    score_with: str = "folds",
    method: str = "conformal",
    analytic: bool = True,
    n_boot: int = 500,
    cluster_bootstrap: bool = False,
    ci: float = 0.95,
    seed: int = 0,
    return_raw: bool = False,
):
    """Evaluate detectors at matched trajectory-level FPR budgets.

    honest / attack: lists of score streams. attack_onsets: per attack stream onset index
    (used only to fit supervised detectors on post-onset units). honest_groups /
    attack_groups: cluster ids (task, context) for grouped splitting (if group_split) and
    cluster bootstrap (if cluster_bootstrap).

    Returns a DataFrame with one row per (detector, alpha, threshold kind):
    tpr, tpr_lo, tpr_hi, fpr, fpr_lo, fpr_hi, threshold, frac_unreachable (share of splits
    where alpha < 1/(n_cal+1) so no alarm is possible), n_cal, n_test, n_attack, supervised.
    With return_raw=True also returns per-split statistics.
    """
    rng = np.random.default_rng(seed)
    Ph_all = pack(honest, honest_contexts)
    Pa_all = pack(attack, attack_contexts)
    any_sup = any(d.supervised for d in detectors.values())
    if attack_fit_frac is None:
        attack_fit_frac = 0.5 if any_sup else 0.0
    if any_sup and attack_fit_frac <= 0:
        raise ValueError("supervised detectors need attack_fit_frac > 0")
    onsets_all = None if attack_onsets is None else np.asarray(attack_onsets, dtype=object)
    hg = None if honest_groups is None else np.asarray(honest_groups)
    ag = None if attack_groups is None else np.asarray(attack_groups)
    alphas = list(alphas)
    q = (1 - ci) / 2

    acc: dict = {}
    raw = []
    for split in range(n_splits):
        cal_idx, test_idx = _split(Ph_all.n, cal_frac, rng, hg if group_split else None)
        if attack_fit_frac > 0:
            afit_idx, atest_idx = _split(Pa_all.n, attack_fit_frac, rng, ag if group_split else None)
        else:
            afit_idx, atest_idx = np.array([], int), np.arange(Pa_all.n)
        Pc, Pt = Ph_all.subset(cal_idx), Ph_all.subset(test_idx)
        Pat = Pa_all.subset(atest_idx)
        Paf = Pa_all.subset(afit_idx) if len(afit_idx) else None
        onf = None if onsets_all is None or Paf is None else list(onsets_all[afit_idx])

        Wc = bootstrap_weights(len(cal_idx), n_boot, rng,
                               hg[cal_idx] if (cluster_bootstrap and hg is not None) else None)
        Wt = bootstrap_weights(len(test_idx), n_boot, rng,
                               hg[test_idx] if (cluster_bootstrap and hg is not None) else None)
        Wa = bootstrap_weights(len(atest_idx), n_boot, rng,
                               ag[atest_idx] if (cluster_bootstrap and ag is not None) else None)

        for name, det in detectors.items():
            sup = det.supervised
            models, cal_s = crossfit_models(det, Pc, crossfit, rng, Paf if sup else None,
                                            onf if sup else None)
            if score_with == "folds":
                test_s, att_s = score_with_models(models, Pt, rng), score_with_models(models, Pat, rng)
                d = models[0]
            else:
                d = det.clone()._fit_packed(Pc, Paf if sup else None, onf if sup else None)
                test_s, att_s = d.stats_packed(Pt), d.stats_packed(Pat)
            raw.append(dict(split=split, detector=name, cal=cal_s, test=test_s, attack=att_s,
                            cal_idx=cal_idx, test_idx=test_idx, attack_idx=atest_idx))
            sc = np.sort(cal_s)
            order = np.argsort(cal_s, kind="stable")
            Wc_sorted = Wc[:, order]
            kinds = [("calibrated", None)]
            if analytic and hasattr(d, "analytic_threshold"):
                kinds.append(("analytic", d))
            for alpha in alphas:
                for kind, dd in kinds:
                    if kind == "calibrated":
                        thr = calibrate(cal_s, alpha, method)
                        hb, gb = row_thresholds(sc, Wc_sorted, alpha, method), None
                    else:
                        thr = Threshold(h=dd.analytic_threshold(alpha), alpha=alpha, method="analytic")
                        hb, gb = np.full(n_boot, thr.h), np.zeros(n_boot)
                    key = (name, alpha, kind)
                    a = acc.setdefault(key, dict(tpr=[], fpr=[], h=[], unreach=[], btpr=[], bfpr=[],
                                                 sup=sup, n_cal=[], n_test=[], n_att=[]))
                    a["n_cal"].append(len(cal_idx))
                    a["n_test"].append(len(test_idx))
                    a["n_att"].append(len(atest_idx))
                    a["tpr"].append(thr.rate(att_s))
                    a["fpr"].append(thr.rate(test_s))
                    a["h"].append(thr.h)
                    a["unreach"].append(not np.isfinite(thr.h))
                    a["btpr"].append(_boot_rate(att_s, Wa, hb, gb))
                    a["bfpr"].append(_boot_rate(test_s, Wt, hb, gb))

    rows = []
    for (name, alpha, kind), a in acc.items():
        bt, bf = np.concatenate(a["btpr"]), np.concatenate(a["bfpr"])
        hs = np.array(a["h"], float)
        rows.append(dict(
            detector=name, alpha=alpha, threshold_kind=kind, supervised=a["sup"],
            tpr=np.mean(a["tpr"]), tpr_lo=np.quantile(bt, q), tpr_hi=np.quantile(bt, 1 - q),
            fpr=np.mean(a["fpr"]), fpr_lo=np.quantile(bf, q), fpr_hi=np.quantile(bf, 1 - q),
            tpr_split_sd=np.std(a["tpr"]),
            threshold=np.mean(hs[np.isfinite(hs)]) if np.isfinite(hs).any() else np.inf,
            frac_unreachable=np.mean(a["unreach"]),
            n_cal=float(np.mean(a["n_cal"])), n_test=float(np.mean(a["n_test"])),
            n_attack=float(np.mean(a["n_att"])),
        ))
    df = pd.DataFrame(rows)
    return (df, raw) if return_raw else df


def simple_matched(det: Detector, cal_honest, test_honest, attack, alpha: float,
                   method: str = "conformal", crossfit: int = 5, score_with: str = "folds",
                   seed: int = 0, cal_contexts=None, test_contexts=None, attack_contexts=None,
                   attack_fit=None, attack_fit_onsets=None):
    """One-shot matched evaluation with given cal / test / attack sets (no resampling).
    Returns (threshold, fpr_test, tpr, detector fitted on all calibration streams, stats)."""
    rng = np.random.default_rng(seed)
    Pc = pack(cal_honest, cal_contexts)
    Paf = None if attack_fit is None else pack(attack_fit)
    models, cal_s = crossfit_models(det, Pc, crossfit, rng, Paf, attack_fit_onsets)
    d = det.clone()._fit_packed(Pc, Paf, attack_fit_onsets)
    thr = calibrate(cal_s, alpha, method)
    Pt, Pa = pack(test_honest, test_contexts), pack(attack, attack_contexts)
    if score_with == "folds":
        test_s, att_s = score_with_models(models, Pt, rng), score_with_models(models, Pa, rng)
    else:
        test_s, att_s = d.stats_packed(Pt), d.stats_packed(Pa)
    return thr, thr.rate(test_s), thr.rate(att_s), d, dict(cal=cal_s, test=test_s, attack=att_s)
