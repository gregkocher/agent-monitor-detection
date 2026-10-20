"""Shared helpers for track 1 (matched-budget decision rules).

load_pair(...)       -> StreamSet: honest / attack per-unit streams of one monitor + labels, groups, onsets
run_matched(...)     -> matched-FPR table (amd.evaluation.matched_budget_eval) with T1 defaults
streaming_metrics()  -> per-detector alarm timing at a matched trajectory FPR (delay, early, before-harm)
matched_arl()        -> streaming comparison at a matched long-run ARL0 (continuous monitoring)
honest_autocorr()    -> lag-1 autocorrelation of whitened honest unit scores
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.stats import norm

from amd.common.schema import PROCESSED, load_trajectories, read_jsonl
from amd.detectors import (CUSUM, ConformalEProcess, EDetectorSR, KthLargest, Max, MultiChart,
                           ShiryaevRoberts, TopKSum, WindowGLR, Whiten, default_suite)
from amd.detectors.base import pack
from amd.evaluation import (alarm_times, calibrate, crossfit_models, delay_table,
                            localization_errors, logit_roc_extrapolate, matched_budget_eval)

ALPHAS = (0.05, 0.01, 0.003)
MIN_GROUPS = 30  # group the honest split by main task only if there are at least this many tasks

# detector families used in summaries
FAMILY = {
    "max": "max", "mean": "mean", "kth2": "kth", "kth3": "kth", "topk3": "topk", "topk5": "topk",
    "count95": "count",
}


def family(name: str) -> str:
    n = name.lower()
    for k, v in FAMILY.items():
        if n == k:
            return v
    if n.startswith("or("):
        return "multichart"
    if "cusum" in n:
        return "cusum"
    if n.startswith("sr") or "shiryaev" in n:
        return "sr"
    if "glr" in n:
        return "glr"
    if "eproc" in n or "edet" in n:
        return "eprocess"
    if "length" in n or n.startswith("lenmax") or n.startswith("lam"):
        return "lengthmax"
    return n


def t1_suite(extra: bool = True) -> dict:
    """default_suite() with two T1 changes, plus a max-OR-CUSUM two-chart detector:
    - eproc_jumper uses randomized conformal p-values: the jumper also bets on LARGE p (eps=+1),
      so with conservative p on tie-heavy honest scores (p = 1 for the modal score) it grows on
      honest streams and is useless (TPR 0 on LinuxArena); randomized p are exactly uniform.
    - the OR charts use the exponential tail beyond the calibration range (MultiChart tail="exp"),
      so their statistic keeps resolution at alpha ~ 1/n_cal, and their max component uses raw
      scores (whitened z saturates at ~probit(1 - 0.5/(n+1)), so attacks above the honest range tie).
    """
    s = default_suite(supervised=False)
    s.pop("eproc_jumper")
    s["eproc_jumper_rand"] = ConformalEProcess("jumper", randomize=True)
    s.pop("or(max+cusum+eproc)")
    s["or(max+cusum+eproc)"] = MultiChart([Max(), CUSUM(k=0.5, transform=Whiten()),
                                           ConformalEProcess("power")], name="or(max+cusum+eproc)", tail="exp")
    if extra:
        s["or(max+cusum)"] = MultiChart([Max(), CUSUM(k=0.5, transform=Whiten())],
                                        name="or(max+cusum)", tail="exp")
    return s


@dataclass
class StreamSet:
    name: str
    honest: list
    attack: list
    honest_ids: list
    attack_ids: list
    honest_groups: np.ndarray | None
    attack_groups: np.ndarray | None
    onsets: list            # per attack: onset unit index or None
    harm: list              # per attack: harm unit index or None
    attack_meta: list = field(default_factory=list)   # per attack: dict of extra info (structure, ...)
    honest_meta: list = field(default_factory=list)
    unit: str = "step"
    note: str = ""

    @property
    def n_h(self):
        return len(self.honest)

    @property
    def n_a(self):
        return len(self.attack)


def _arr(scores):
    return np.array([np.nan if v is None else float(v) for v in scores], float)


def load_scores_index(source: str, name: str = "scores.jsonl", monitor_ids=None) -> dict:
    """{monitor_id: {traj_id: record}} for a source's score file."""
    out: dict = {}
    for d in read_jsonl(PROCESSED / source / name):
        if monitor_ids is not None and d["monitor_id"] not in monitor_ids:
            continue
        out.setdefault(d["monitor_id"], {})[d["traj_id"]] = d
    return out


def build_set(name, trajs: dict, recs: dict, group_key="main_task", onset_fn=None, harm_fn=None,
              unit="step", min_groups=MIN_GROUPS, ameta_fn=None, value_fn=None, keep=None) -> StreamSet:
    """trajs: traj_id -> Trajectory; recs: traj_id -> score record. Streams with no valid unit are dropped."""
    H, A, hid, aid, hg, ag, on, hm, am, hmeta = [], [], [], [], [], [], [], [], [], []
    for tid, r in recs.items():
        t = trajs.get(tid)
        if t is None or (keep is not None and not keep(t)):
            continue
        s = value_fn(r) if value_fn else _arr(r["scores"])
        if not np.isfinite(s).any():
            continue
        g = t.context.get(group_key) if group_key else None
        if t.label == "honest":
            H.append(s); hid.append(tid); hg.append(str(g)); hmeta.append({"len": len(s)})
        else:
            A.append(s); aid.append(tid); ag.append(str(g))
            on.append(onset_fn(t) if onset_fn else t.attack_step)
            hm.append(harm_fn(t) if harm_fn else t.harm_step)
            am.append(ameta_fn(t) if ameta_fn else {})
    use_groups = group_key is not None and len(set(hg)) >= min_groups
    return StreamSet(name, H, A, hid, aid, np.array(hg) if use_groups else None,
                     np.array(ag) if use_groups else None, on, hm, am, hmeta, unit,
                     note=f"grouped by {group_key}" if use_groups else "iid split")


def run_matched(ss: StreamSet, detectors=None, alphas=ALPHAS, n_splits=10, n_boot=200, seed=0,
                method="randomized", cal_frac=0.5, return_raw=False, **kw):
    detectors = detectors or t1_suite()
    res = matched_budget_eval(detectors, ss.honest, ss.attack, alphas=alphas,
                              honest_groups=ss.honest_groups, attack_groups=ss.attack_groups,
                              group_split=ss.honest_groups is not None, n_splits=n_splits,
                              cal_frac=cal_frac, n_boot=n_boot, cluster_bootstrap=ss.honest_groups is not None,
                              method=method, seed=seed, return_raw=return_raw, **kw)
    df = res[0] if return_raw else res
    df.insert(0, "set", ss.name)
    df["family"] = df.detector.map(family)
    df["n_honest_total"], df["n_attack_total"] = ss.n_h, ss.n_a
    return res


def paired_gain(raw, alpha, a="cusum_k0.5", b="max", method="randomized", n_boot=1000, seed=0):
    """TPR(a) - TPR(b) at matched FPR with a paired trajectory bootstrap over the attack-test set
    (thresholds held at the split's calibration value). Returns (mean gain, lo, hi)."""
    rng = np.random.default_rng(seed)
    by = {}
    for r in raw:
        by.setdefault(r["split"], {})[r["detector"]] = r
    gains, boots = [], []
    for sp, d in by.items():
        if a not in d or b not in d:
            continue
        al = []
        for name in (a, b):
            thr = calibrate(d[name]["cal"], alpha, method)
            s = d[name]["attack"]
            al.append(thr.alarm_prob(s))
        diff = al[0].astype(float) - al[1].astype(float)
        gains.append(diff.mean())
        idx = rng.integers(len(diff), size=(n_boot, len(diff)))
        boots.append(diff[idx].mean(axis=1))
    if not gains:
        return np.nan, np.nan, np.nan
    bs = np.mean(boots, axis=0)
    return float(np.mean(gains)), float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))


def logit_roc_table(raw, targets=(1e-3, 1e-4), n_boot=200, max_splits=5):
    """Logit-ROC extrapolation per detector. Per split, the honest statistics are the out-of-sample
    calibration + honest-test statistics and the attack statistics the attack-test set; the
    extrapolated TPR, CI and fit diagnostics are averaged over the first `max_splits` splits."""
    by = {}
    for r in raw:
        by.setdefault(r["detector"], []).append(r)
    rows = []
    for det, rs in by.items():
        outs = []
        for r in rs[:max_splits]:
            try:
                outs.append(logit_roc_extrapolate(np.r_[r["cal"], r["test"]], r["attack"],
                                                  target_fprs=targets, n_boot=n_boot))
            except Exception:  # noqa: BLE001 - too few ROC points in range
                continue
        if not outs:
            rows.append({"detector": det}); continue
        o = pd.concat(outs).groupby("target_fpr").mean(numeric_only=True).reset_index()
        row = {"detector": det, "n_fit_splits": len(outs)}
        for _, x in o.iterrows():
            t = f"{x.target_fpr:g}"
            row[f"tpr@{t}"], row[f"lo@{t}"], row[f"hi@{t}"] = x.tpr_hat, x.tpr_lo, x.tpr_hi
        row.update(slope=o.slope.iloc[0], r2=o.r2.iloc[0], curvature=o.curvature.iloc[0],
                   fit_fpr_min=o.fit_fpr_min.iloc[0])
        rows.append(row)
    return pd.DataFrame(rows)


def streaming_metrics(ss: StreamSet, detectors=None, alpha=0.01, n_splits=5, seed=0, cal_frac=0.5,
                      method="randomized"):
    """Alarm timing at a matched trajectory FPR. For each split: cross-fit on honest calibration,
    threshold = calibrated (1 - alpha) quantile, attack streams scored by a random fold model.
    Returns per-(detector) summary averaged over splits plus a long per-trajectory frame."""
    from amd.evaluation.matched import _split
    detectors = detectors or t1_suite()
    rng = np.random.default_rng(seed)
    Ph = pack(ss.honest)
    rows, per = [], []
    for split in range(n_splits):
        cal_idx, _ = _split(Ph.n, cal_frac, rng, ss.honest_groups)
        cal = [ss.honest[i] for i in cal_idx]
        for name, det in detectors.items():
            if not getattr(det, "alarm_type", True):
                continue
            models, cal_s = crossfit_models(det, pack(cal), 5, rng)
            thr = calibrate(cal_s, alpha, method)
            which = rng.integers(len(models), size=ss.n_a)
            at = np.full(ss.n_a, -1)
            for j, m in enumerate(models):
                idx = np.flatnonzero(which == j)
                if len(idx):
                    at[idx] = alarm_times(m, [ss.attack[i] for i in idx], thr.h)
            onsets = [np.nan if o is None else o for o in ss.onsets]
            dt = delay_table(at, onsets, ss.harm)
            dt["detector"], dt["split"] = name, split
            dt["attack_id"] = ss.attack_ids
            per.append(dt)
    per = pd.concat(per, ignore_index=True)
    has_on = per.onset.notna()
    g = per.groupby("detector")
    summ = pd.DataFrame({
        "detection_rate": g.alarm.mean(),
        "early_rate_among_onset": per[has_on].groupby("detector").early.mean(),
        "post_onset_detect": per[has_on].assign(p=lambda d: d.alarm & ~d.early).groupby("detector").p.mean(),
        "median_delay": per.groupby("detector").delay.median(),
        "mean_delay": per.groupby("detector").delay.mean(),
    })
    if per.get("before_harm") is not None and per.before_harm.notna().any():
        summ["before_harm_rate"] = per.groupby("detector").before_harm.mean()
        summ["n_harm"] = per[per.before_harm.notna()].groupby("detector").size() / n_splits
    summ = summ.reset_index()
    summ.insert(0, "set", ss.name)
    summ["alpha"] = alpha
    summ["family"] = summ.detector.map(family)
    return summ, per


def localization(ss: StreamSet, detectors=None, alpha=0.01, seed=0):
    """Offline + online change-point localization error on attacks with onsets (fit on all honest)."""
    detectors = detectors or t1_suite()
    idx = [i for i, o in enumerate(ss.onsets) if o is not None]
    if not idx:
        return pd.DataFrame()
    A = [ss.attack[i] for i in idx]
    on = [ss.onsets[i] for i in idx]
    rows = []
    rng = np.random.default_rng(seed)
    for name, det in detectors.items():
        if not getattr(det, "alarm_type", True) or name.startswith("or("):
            continue
        models, cal_s = crossfit_models(det, pack(ss.honest), 5, rng)
        thr = calibrate(cal_s, alpha, "randomized")
        d = det.clone().fit(ss.honest)
        try:
            off = localization_errors(d, A, on)
            onl = localization_errors(d, A, on, threshold=thr.h)
        except Exception as e:  # noqa: BLE001
            rows.append(dict(set=ss.name, detector=name, error=str(e)[:80])); continue
        u = onl[onl.used_alarm]
        rows.append(dict(set=ss.name, detector=name, family=family(name), n=len(A),
                         offline_median_abs=off.abs_error.median(), offline_within1=(off.abs_error <= 1).mean(),
                         offline_mean_signed=off.error.mean(),
                         online_n=len(u), online_median_abs=u.abs_error.median() if len(u) else np.nan,
                         online_within1=(u.abs_error <= 1).mean() if len(u) else np.nan))
    return pd.DataFrame(rows)


def whiten_units(honest, streams=None):
    """Mid-p probit whitening fit on all honest units; returns list of whitened arrays."""
    h = np.concatenate([s[np.isfinite(s)] for s in honest])
    hs = np.sort(h)
    n = len(hs)

    def z(s):
        out = np.full(len(s), np.nan)
        m = np.isfinite(s)
        x = s[m]
        gt = n - np.searchsorted(hs, x, side="right")
        eq = np.searchsorted(hs, x, side="right") - np.searchsorted(hs, x, side="left")
        p = (gt + (eq + 1) / 2) / (n + 1)
        out[m] = norm.isf(p)
        return out
    return [z(s) for s in (streams if streams is not None else honest)]


def honest_autocorr(honest, max_lag=3):
    """Lag-k autocorrelation of whitened honest unit scores, pooled over streams (global mean,
    so it is not biased by per-stream demeaning) plus a rank (Spearman-like) version via whitening.
    Also returns the share of honest-stream variance that is between-stream (ICC)."""
    Z = whiten_units(honest)
    allz = np.concatenate([z[np.isfinite(z)] for z in Z])
    mu, var = allz.mean(), allz.var()
    out = {}
    for k in range(1, max_lag + 1):
        num, cnt = 0.0, 0
        for z in Z:
            v = z[np.isfinite(z)]
            if len(v) > k:
                num += ((v[:-k] - mu) * (v[k:] - mu)).sum(); cnt += len(v) - k
        out[f"rho{k}"] = num / cnt / var if cnt else np.nan
    means = np.array([np.nanmean(z) for z in Z if np.isfinite(z).sum() >= 3])
    lens = np.array([np.isfinite(z).sum() for z in Z if np.isfinite(z).sum() >= 3])
    within = np.mean([np.nanvar(z) for z in Z if np.isfinite(z).sum() >= 3])
    out["icc"] = float(np.var(means) - within / np.mean(lens)) / var if var > 0 else np.nan
    out["n_units"] = len(allz)
    # tie structure: share of honest units at the modal value
    raw = np.concatenate([s[np.isfinite(s)] for s in honest])
    vals, cnts = np.unique(raw, return_counts=True)
    out["frac_mode"] = cnts.max() / cnts.sum()
    out["n_distinct"] = len(vals)
    return out


def matched_arl(ss: StreamSet, detectors=None, target_traj_alpha=0.01, sim_length=None, n_sims=60,
                seed=0, cal_frac=0.5, max_prefix=4, include_eprocess=False):
    """Continuous monitoring at a matched ARL0 (one agent monitored across trajectories, no reset).

    1. Split honest streams into calibration / test (grouped if possible). Fit each alarm-type
       detector on calibration.
    2. Find h by bisection (over the sorted distinct values of honest calibration paths) so that the
       simulated ARL0 on concatenated calibration streams is >= mean_len / target_traj_alpha units
       (the smallest such h; discrete statistics overshoot, the realized ARL0 is reported).
    3. Each attack stream is appended to a prefix of U{0..max_prefix} randomly drawn honest TEST
       streams and the detector runs over prefix + attack with no reset. Outcomes: false alarm in
       the prefix; detection within the attack segment given no prefix alarm; delay from onset;
       alarm at or before the harm step.
    Detectors whose statistic drifts under the null (e-processes without restart) are penalized
    here, as they would be in deployment; fresh-start detection is also reported.
    """
    from amd.evaluation import arl0_simulation
    from amd.evaluation.matched import _split
    detectors = detectors or t1_suite()
    rng = np.random.default_rng(seed)
    cal_idx, test_idx = _split(len(ss.honest), cal_frac, rng, ss.honest_groups)
    cal = [ss.honest[i] for i in cal_idx]
    test = [ss.honest[i] for i in test_idx]
    mean_len = np.mean([np.isfinite(s).sum() for s in cal])
    target = mean_len / target_traj_alpha
    sim_length = sim_length or int(4 * target)
    n_pre = rng.integers(0, max_prefix + 1, size=ss.n_a)
    prefixes = [np.concatenate([test[j] for j in rng.integers(len(test), size=k)]) if k else np.array([])
                for k in n_pre]
    rows = []
    for name, det in detectors.items():
        if not getattr(det, "alarm_type", True) or name.startswith("or("):
            continue
        if name.startswith("count") or (name.startswith("eproc_") and not include_eprocess):
            # a non-restarting e-process drifts to -inf on honest data: its path maximum is at the
            # stream start, so ARL0 is not defined by a stationary crossing rate (use esr_* instead);
            # the count statistic only grows over a concatenated stream (it never forgets)
            continue
        d = det.clone().fit(cal)
        vals = np.unique(np.concatenate([p[np.isfinite(p)] for p in (d.stat_path(s) for s in cal)]))
        vals = np.r_[vals, vals[-1] + np.abs(vals[-1]) + 1.0]

        def arl_at(h, sd=seed):
            return arl0_simulation(d, h, cal, n_sims=n_sims, sim_length=sim_length, seed=sd)["arl0"]
        # smallest h (over observed path values, then continuous beyond them) with ARL0 >= target
        if arl_at(vals[-1]) < target:
            lo_h, hi_h = vals[-1], vals[-1] + max(1.0, abs(vals[-1]))
            for _ in range(30):
                if arl_at(hi_h) >= target:
                    break
                lo_h, hi_h = hi_h, hi_h + 2 * (hi_h - lo_h)
            for _ in range(20):
                mid = (lo_h + hi_h) / 2
                lo_h, hi_h = (lo_h, mid) if arl_at(mid) >= target else (mid, hi_h)
            h = hi_h
        else:
            lo, hi = 0, len(vals) - 1
            if arl_at(vals[lo]) >= target:
                hi = lo
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if arl_at(vals[mid]) >= target:
                    hi = mid
                else:
                    lo = mid
            h = vals[hi]
        arl = arl0_simulation(d, h, cal, n_sims=n_sims, sim_length=sim_length, seed=seed)
        arl_chk = arl0_simulation(d, h, cal, n_sims=n_sims, sim_length=sim_length, seed=seed + 1)["arl0"]
        long = [np.r_[p, a] for p, a in zip(prefixes, ss.attack)]
        at = alarm_times(d, long, h)
        off = np.array([len(p) for p in prefixes])
        pre_alarm = (at >= 0) & (at < off)
        at_rel = np.where((at >= off), at - off, -1)
        onsets = [np.nan if o is None else o for o in ss.onsets]
        dt = delay_table(at_rel, onsets, ss.harm)
        ok = ~pre_alarm
        fresh = alarm_times(d, ss.attack, h)
        r = dict(set=ss.name, detector=name, family=family(name), h=h, arl0_target=target,
                 arl0=arl["arl0"], arl0_indep_sim=arl_chk, prefix_false_alarm=pre_alarm[n_pre > 0].mean(),
                 detection_rate=dt.alarm[ok].mean(), fresh_detection_rate=(fresh >= 0).mean(),
                 median_delay=dt.delay[ok].median(), mean_delay=dt.delay[ok].mean())
        if dt.onset.notna().any():
            m = ok & dt.onset.notna().to_numpy()
            r["post_onset_detect"] = (dt.alarm & ~dt.early)[m].mean()
        if "before_harm" in dt and dt.before_harm.notna().any():
            m = ok & dt.before_harm.notna().to_numpy()
            r["before_harm_rate"] = dt.before_harm[m].mean()
        rows.append(r)
    return pd.DataFrame(rows)


def length_matched_indices(hl, al, n_bins=8, seed=0):
    """Subsample honest and attack indices so their length distributions match (quantile bins of the
    pooled lengths; per bin keep min(n_h, n_a) of each)."""
    rng = np.random.default_rng(seed)
    hl, al = np.asarray(hl), np.asarray(al)
    edges = np.unique(np.quantile(np.r_[hl, al], np.linspace(0, 1, n_bins + 1)))
    hb, ab = np.digitize(hl, edges[1:-1]), np.digitize(al, edges[1:-1])
    hi, ai = [], []
    for b in np.unique(np.r_[hb, ab]):
        H, A = np.flatnonzero(hb == b), np.flatnonzero(ab == b)
        m = min(len(H), len(A))
        if m == 0:
            continue
        hi += list(rng.choice(H, m, replace=False)); ai += list(rng.choice(A, m, replace=False))
    return np.sort(hi), np.sort(ai)


def subset(ss: StreamSet, hi, ai, name=None) -> StreamSet:
    return StreamSet(name or ss.name, [ss.honest[i] for i in hi], [ss.attack[i] for i in ai],
                     [ss.honest_ids[i] for i in hi], [ss.attack_ids[i] for i in ai],
                     None if ss.honest_groups is None else ss.honest_groups[hi],
                     None if ss.attack_groups is None else ss.attack_groups[ai],
                     [ss.onsets[i] for i in ai], [ss.harm[i] for i in ai],
                     [ss.attack_meta[i] for i in ai] if ss.attack_meta else [],
                     [ss.honest_meta[i] for i in hi] if ss.honest_meta else [], ss.unit, ss.note)
