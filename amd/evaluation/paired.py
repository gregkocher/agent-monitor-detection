"""Paired bootstrap for contrasts of matched-FPR TPRs (gain over max, difference-in-differences).

Why: the round-1/2 helpers (tracks/t1_matched_budget/t1lib.paired_gain, run_round2.paired_gains, the DiD in
run_round2) drew NEW attack-bootstrap indices in every honest split and then AVERAGED the replicates across
splits. Averaging S independent replicate draws shrinks the bootstrap spread by about sqrt(S), so the reported
CIs were several times too narrow. They also held thresholds fixed (no calibration noise) and resampled attacks
iid (no task clustering).

This module draws ONE joint resample per replicate and reuses it in every split:
  * honest trajectories (the whole honest universe the splits were cut from; optionally a cluster bootstrap by
    task / app / account) -> each split's calibration weights are the replicate weights restricted to that
    split's calibration indices, and the randomized (or conformal) threshold is recomputed from them;
  * attack trajectories (optionally clustered) -> the same weights for every split and every detector.
The replicate contrast is the split-average of the weighted contrast; the point estimate is the split-average
of the unweighted contrast (identical to the old point estimate). Cross-fitted per-unit transforms are held
fixed (statistics are taken from the matched-eval raw output), so whitening-model noise is not included.

Input `raw` is the list returned by `matched_budget_eval(..., return_raw=True)`: dicts with split, detector,
cal (cross-fitted calibration statistics), attack (attack statistics), cal_idx (indices into the honest
universe), attack_idx (indices into the attack universe).
"""
from __future__ import annotations

import numpy as np

from .calibration import calibrate
from .matched import _boot_threshold, bootstrap_weights


def _index(raws):
    """{(raw_id, split): {detector: record}}"""
    out = {}
    for k, raw in enumerate(raws):
        for r in raw:
            out.setdefault((k, r["split"]), {})[r["detector"]] = r
    return out


def paired_contrast_bootstrap(terms, n_honest: int, n_attack: int, alpha: float, honest_groups=None,
                              attack_groups=None, attack_mask=None, method: str = "randomized",
                              n_boot: int = 1000, seed: int = 0, calibration_noise: bool = True,
                              ci: float = 0.95, return_boot: bool = False) -> dict:
    """Contrast C = sum_j coef_j * TPR(raw_j, det_j) at matched FPR alpha, bootstrapped jointly.

    terms: list of (coef, raw, detector). All raws must index the same honest / attack universes and share split
    ids (e.g. two history modes scored on the same trajectories with the same split seed); a split is used only
    if every term has it, and the honest calibration indices of the terms must agree within a split when
    calibration_noise is on (checked).
    attack_mask: optional boolean array over the attack universe (subgroup contrast, e.g. one attack structure).
    Returns dict(est, lo, hi, se, p_le0, p_ge0, n_splits, n_boot) [+ boot].
    """
    rng = np.random.default_rng(seed)
    raws = []
    for _, raw, _ in terms:
        if not any(raw is r for r in raws):
            raws.append(raw)
    rid = [next(i for i, r in enumerate(raws) if r is raw) for _, raw, _ in terms]
    idx = _index(raws)
    splits = sorted({sp for (_, sp) in idx})
    splits = [sp for sp in splits
              if all((rid[j], sp) in idx and terms[j][2] in idx[(rid[j], sp)] for j in range(len(terms)))]
    if not splits:
        raise ValueError("no split contains every term")
    hg = None if honest_groups is None else np.asarray(honest_groups)
    ag = None if attack_groups is None else np.asarray(attack_groups)
    Wh = bootstrap_weights(n_honest, n_boot, rng, hg) if calibration_noise else None
    Wa = bootstrap_weights(n_attack, n_boot, rng, ag)
    mask = np.ones(n_attack, bool) if attack_mask is None else np.asarray(attack_mask, bool)
    est_s, boot_s = [], []
    for sp in splits:
        recs = [idx[(rid[j], sp)][terms[j][2]] for j in range(len(terms))]
        aidx = recs[0]["attack_idx"]
        for r in recs[1:]:
            if not np.array_equal(r["attack_idx"], aidx):
                raise ValueError("attack test sets differ between terms within a split")
        if calibration_noise:
            for r in recs[1:]:
                if not np.array_equal(r["cal_idx"], recs[0]["cal_idx"]):
                    raise ValueError("calibration sets differ between terms within a split")
        m = mask[aidx]
        if not m.any():
            continue
        wa = Wa[:, aidx][:, m]                              # (B, n_att_in_subgroup)
        den = np.maximum(wa.sum(axis=1), 1e-12)
        pt, bt = 0.0, np.zeros(n_boot)
        for (coef, _, _), r in zip(terms, recs):
            s_att = np.asarray(r["attack"], float)[m]
            thr = calibrate(r["cal"], alpha, method)
            pt += coef * thr.alarm_prob(s_att).mean()
            if calibration_noise:
                cal = np.asarray(r["cal"], float)
                order = np.argsort(cal, kind="stable")
                wc = Wh[:, np.asarray(r["cal_idx"])][:, order]
                h, g = _boot_threshold(cal[order], wc, alpha, method)
            else:
                h, g = np.full(n_boot, thr.h), np.full(n_boot, thr.gamma)
            A = (s_att[None, :] > h[:, None]) + g[:, None] * (s_att[None, :] == h[:, None])
            bt += coef * (A * wa).sum(axis=1) / den
        est_s.append(pt)
        boot_s.append(bt)
    q = (1 - ci) / 2
    b = np.mean(boot_s, axis=0)
    out = dict(est=float(np.mean(est_s)), lo=float(np.quantile(b, q)), hi=float(np.quantile(b, 1 - q)),
               se=float(np.std(b, ddof=1)), p_le0=float((b <= 0).mean()), p_ge0=float((b >= 0).mean()),
               n_splits=len(est_s), n_boot=n_boot)
    if return_boot:
        out["boot"] = b
    return out


def paired_gain_bootstrap(raw, alpha: float, a: str, b: str = "max", **kw) -> dict:
    """TPR(a) - TPR(b) on one raw output; see paired_contrast_bootstrap for keyword arguments."""
    return paired_contrast_bootstrap([(1.0, raw, a), (-1.0, raw, b)], alpha=alpha, **kw)


def paired_did_bootstrap(raw1, raw2, alpha: float, det: str, base: str = "max", **kw) -> dict:
    """[TPR1(det) - TPR1(base)] - [TPR2(det) - TPR2(base)] for two score sets of the same trajectories."""
    return paired_contrast_bootstrap([(1.0, raw1, det), (-1.0, raw1, base), (-1.0, raw2, det), (1.0, raw2, base)],
                                     alpha=alpha, **kw)
