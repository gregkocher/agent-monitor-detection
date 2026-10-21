"""Round-3 inference helpers.

paired_gain_full: TPR(a) - TPR(b) at matched FPR with a FULL paired bootstrap. In every replicate the honest
calibration trajectories (cluster bootstrap by honest group if given) AND the attack trajectories (cluster
bootstrap by attack group if given) are resampled once, both detectors' thresholds are recomputed on the same
resampled calibration set (randomized plug-in, as in the point estimate), and the gain is computed on the same
resampled attacks. Replicates are pooled over the repeated honest splits. This replaces round 2's
`paired_gain` (attack-only bootstrap with thresholds held fixed), which ignored calibration noise and gave CIs
several times too narrow (results/audit/repro_t1_ps.csv).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from amd.evaluation.calibration import calibrate
from amd.evaluation.matched import _boot_rate, _boot_threshold, bootstrap_weights


def _by_split(raw):
    out = {}
    for r in raw:
        out.setdefault(r["split"], {})[r["detector"]] = r
    return out


def paired_gain_full(raw, alpha, a, b="max", honest_groups=None, attack_groups=None, n_boot=1000, seed=0,
                     method="randomized"):
    rng = np.random.default_rng(seed)
    pts, reps = [], []
    for sp, d in sorted(_by_split(raw).items()):
        if a not in d or b not in d:
            continue
        ra, rb = d[a], d[b]
        cal_idx, att_idx = ra["cal_idx"], ra["attack_idx"]
        Wc = bootstrap_weights(len(cal_idx), n_boot, rng, None if honest_groups is None else np.asarray(honest_groups)[cal_idx])
        Wa = bootstrap_weights(len(att_idx), n_boot, rng, None if attack_groups is None else np.asarray(attack_groups)[att_idx])
        g = []
        for r in (ra, rb):
            o = np.argsort(r["cal"], kind="mergesort")
            h, gam = _boot_threshold(np.asarray(r["cal"])[o], Wc[:, o], alpha, method)
            g.append(_boot_rate(np.asarray(r["attack"], float), Wa, h, gam))
        reps.append(g[0] - g[1])
        ta = calibrate(ra["cal"], alpha, method).rate(ra["attack"])
        tb = calibrate(rb["cal"], alpha, method).rate(rb["attack"])
        pts.append(ta - tb)
    if not pts:
        return dict(gain=np.nan, lo=np.nan, hi=np.nan, p_le0=np.nan)
    bs = np.concatenate(reps)
    return dict(gain=float(np.mean(pts)), lo=float(np.quantile(bs, 0.025)), hi=float(np.quantile(bs, 0.975)),
                p_le0=float(np.mean(bs <= 0)))


def gains_full(ss, raw, alphas, dets, base="max", n_boot=1000):
    rows = []
    for al in alphas:
        for d in dets:
            if d == base:
                continue
            r = paired_gain_full(raw, al, d, base, ss.honest_groups, ss.attack_groups, n_boot=n_boot)
            rows.append(dict(set=ss.name, alpha=al, detector=d, gain_vs_max=r["gain"], lo=r["lo"], hi=r["hi"],
                             p_le0=r["p_le0"]))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------------
# Rule chooser evaluated at MATCHED REALIZED FPR (audit M6/M7)
# ---------------------------------------------------------------------------------------------------------------
def chooser_matched(ss, n_lab=20, n_splits=40, alphas=(0.05, 0.01), seed=0, grid=None):
    """Out-of-sample evaluation of the empirical chooser (tracks/r2_t1/chooser.py: candidate rules, labeled-attack
    TPR averaged over alpha' in {a, 2a, 5a}, switch from max only if the gain exceeds 1/n_lab), with the
    comparison to always-max made at the chooser's OWN realized FPR on the honest test half.

    Per split: honest 50/50 split (grouped by honest_groups if given), n_lab labeled attacks drawn for the chooser,
    the rest are test attacks. Every rule is cross-fitted on the honest calibration half; the chosen rule's
    threshold is set at alpha; its realized FPR (honest test) and TPR (test attacks) are recorded. For max, TPR
    and realized FPR are traced over a dense grid of nominal levels (alpha x grid) and max's TPR is interpolated
    at the chooser's realized FPR (monotone in FPR). gain_matched = TPR(choice) - TPR_max(at that FPR).
    Returns a per-split frame."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "r2_t1"))
    from chooser import choose_emp, rules
    from amd.detectors.base import pack
    from amd.evaluation import crossfit_models
    from amd.evaluation.matched import _split, score_with_models
    grid = np.array(grid if grid is not None else np.geomspace(0.25, 4.0, 25))
    rng = np.random.default_rng(seed)
    R = rules()
    n_a = len(ss.attack)
    lab_n = min(n_lab, max(5, n_a // 3))
    rows = []
    for sp in range(n_splits):
        cal_idx, test_idx = _split(len(ss.honest), 0.5, rng, ss.honest_groups)
        lab = rng.choice(n_a, lab_n, replace=False)
        rest = np.setdiff1d(np.arange(n_a), lab)
        Ph, Pht = pack([ss.honest[i] for i in cal_idx]), pack([ss.honest[i] for i in test_idx])
        Pal, Pat = pack([ss.attack[i] for i in lab]), pack([ss.attack[i] for i in rest])
        st = {}
        for name, det in R.items():
            models, cal_s = crossfit_models(det, Ph, 5, rng)
            st[name] = (cal_s, score_with_models(models, Pht, rng), score_with_models(models, Pal, rng),
                        score_with_models(models, Pat, rng))
        for a in alphas:
            emp = []
            for name, (c, ht, al_, at) in st.items():
                e = np.mean([calibrate(c, min(a * m, 0.2), "randomized").rate(al_) for m in (1, 2, 5)])
                emp.append(dict(rule=name, emp=e))
            g = pd.DataFrame(emp)
            pick = choose_emp(g, lab_n)
            c, ht, _, at = st[pick]
            thr = calibrate(c, a, "randomized")
            tpr_c, fpr_c = thr.rate(at), thr.rate(ht)
            cm, htm, _, atm = st["max"]
            curve = [(calibrate(cm, min(a * m, 0.5), "randomized").rate(htm),
                      calibrate(cm, min(a * m, 0.5), "randomized").rate(atm)) for m in grid]
            fx, ty = np.array(curve).T
            o = np.argsort(fx, kind="mergesort")
            tpr_m_at = float(np.interp(fpr_c, fx[o], np.maximum.accumulate(ty[o])))
            thr_m = calibrate(cm, a, "randomized")
            rows.append(dict(set=ss.name, split=sp, alpha=a, pick=pick, tpr_choice=tpr_c, fpr_choice=fpr_c,
                             tpr_max=thr_m.rate(atm), fpr_max=thr_m.rate(htm), tpr_max_at_choice_fpr=tpr_m_at))
    df = pd.DataFrame(rows)
    df["gain_nominal"] = df.tpr_choice - df.tpr_max
    df["gain_matched"] = df.tpr_choice - df.tpr_max_at_choice_fpr
    return df


def chooser_summary(df):
    g = df.groupby(["set", "alpha"]).agg(tpr_choice=("tpr_choice", "mean"), fpr_choice=("fpr_choice", "mean"),
                                         tpr_max=("tpr_max", "mean"), fpr_max=("fpr_max", "mean"),
                                         gain_nominal=("gain_nominal", "mean"), gain_matched=("gain_matched", "mean"),
                                         share_switch=("pick", lambda x: float(np.mean(x != "max"))))
    return g.reset_index()
