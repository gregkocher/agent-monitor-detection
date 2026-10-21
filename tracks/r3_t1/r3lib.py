"""Round-3 inference helpers (audit fixes C2, M6/M7).

gains_full: paired gain over max via amd.evaluation.paired (one joint honest + attack resample per replicate
reused across splits, cluster-aware, thresholds recomputed). Round 2's `paired_gain` (attack-only bootstrap,
thresholds fixed, replicates averaged across splits) gave CIs several times too narrow.
chooser_matched: the empirical rule chooser evaluated with nested calibration (select on one calibration half,
threshold from the other) and at matched realized FPR (thresholds set on the honest test half).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from amd.evaluation.calibration import calibrate


def gains_full(ss, raw, alphas, dets, base="max", n_boot=2000):
    """Gains over `base` with amd.evaluation.paired (audit fix C2): ONE joint resample per replicate reused across
    all splits (honest universe clustered by ss.honest_groups, attacks by ss.attack_groups), thresholds recomputed
    from the resampled calibration weights, replicate = split-average of the weighted contrast."""
    from amd.evaluation.paired import paired_gain_bootstrap
    rows = []
    for al in alphas:
        for d in dets:
            if d == base:
                continue
            r = paired_gain_bootstrap(raw, al, d, base, n_honest=len(ss.honest), n_attack=len(ss.attack),
                                      honest_groups=ss.honest_groups, attack_groups=ss.attack_groups,
                                      n_boot=n_boot, seed=0)
            rows.append(dict(set=ss.name, alpha=al, detector=d, gain_vs_max=r["est"], lo=r["lo"], hi=r["hi"],
                             p_le0=r["p_le0"]))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------------
# Rule chooser evaluated at MATCHED REALIZED FPR (audit M6/M7)
# ---------------------------------------------------------------------------------------------------------------
def chooser_matched(ss, n_lab=20, n_splits=40, alphas=(0.05, 0.01), seed=0):
    """Empirical rule chooser (tracks/r2_t1/chooser.py rules; labeled-attack TPR averaged over alpha' in
    {a, 2a, 5a}; switch from max only if the gain exceeds 1/n_lab) under two honest designs (audit M6/M7):
      nested      : the honest calibration half is cut in two (grouped when the set is grouped); the chooser
                    selects with thresholds from half A; the chosen rule AND always-max are evaluated with
                    thresholds from half B, so selection noise and evaluation threshold are independent;
      fpr_matched : selection on the full calibration half; every rule evaluated at a threshold set on the
                    held-out honest test half itself (realized FPR = alpha for all rules).
    Labeled attacks are drawn by whole task when the set has attack groups (evaluation attacks come from other
    tasks), else iid. Returns per-split rows: design, pick, TPR / realized FPR of the pick and of always-max."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "r2_t1"))
    from chooser import choose_emp, rules
    from amd.detectors.base import pack
    from amd.evaluation import crossfit_models
    from amd.evaluation.matched import _split, score_with_models
    rng = np.random.default_rng(seed)
    R = rules()
    n_a = len(ss.attack)
    lab_n = min(n_lab, max(5, n_a // 3))
    hg = None if ss.honest_groups is None else np.asarray(ss.honest_groups)
    ag = None if ss.attack_groups is None else np.asarray(ss.attack_groups)
    rows = []
    for sp in range(n_splits):
        cal_idx, test_idx = _split(len(ss.honest), 0.5, rng, hg)
        A_, B_ = _split(len(cal_idx), 0.5, rng, None if hg is None else hg[cal_idx])
        if ag is not None:
            sel = []
            for u in rng.permutation(np.unique(ag)):
                sel.append(u)
                if np.isin(ag, sel).sum() >= lab_n:
                    break
            pool = np.flatnonzero(np.isin(ag, sel))
            lab = rng.choice(pool, min(lab_n, len(pool)), replace=False)
            rest = np.flatnonzero(~np.isin(ag, sel))
        else:
            lab = rng.choice(n_a, lab_n, replace=False)
            rest = np.setdiff1d(np.arange(n_a), lab)
        Ph, Pht = pack([ss.honest[i] for i in cal_idx]), pack([ss.honest[i] for i in test_idx])
        Pal, Pat = pack([ss.attack[i] for i in lab]), pack([ss.attack[i] for i in rest])
        st = {}
        for name, det in R.items():
            models, cal_s = crossfit_models(det, Ph, 5, rng)
            st[name] = (np.asarray(cal_s), score_with_models(models, Pht, rng), score_with_models(models, Pal, rng),
                        score_with_models(models, Pat, rng))
        for a in alphas:
            grid = [min(a * m, 0.2) for m in (1, 2, 5)]
            for design in ("nested", "fpr_matched"):
                sel_cal = (lambda c: c[A_]) if design == "nested" else (lambda c: c)
                g = pd.DataFrame([dict(rule=n, emp=np.mean([calibrate(sel_cal(c), x, "randomized").rate(al_) for x in grid]))
                                  for n, (c, ht, al_, at) in st.items()])
                pick = choose_emp(g, len(lab))

                def ev(name):
                    c, ht, _, at = st[name]
                    t = calibrate(c[B_], a, "randomized") if design == "nested" else calibrate(ht, a, "randomized")
                    return t.rate(at), t.rate(ht)
                tc, fc = ev(pick)
                tm, fm = ev("max")
                rows.append(dict(set=ss.name, split=sp, alpha=a, design=design, pick=pick, tpr_choice=tc,
                                 fpr_choice=fc, tpr_max=tm, fpr_max=fm, n_lab=len(lab), n_eval=len(rest)))
    df = pd.DataFrame(rows)
    df["gain"] = df.tpr_choice - df.tpr_max
    return df


def chooser_summary(df, design="nested"):
    d = df[df.design == design]
    g = d.groupby(["set", "alpha"]).agg(tpr_choice=("tpr_choice", "mean"), fpr_choice=("fpr_choice", "mean"),
                                        tpr_max=("tpr_max", "mean"), fpr_max=("fpr_max", "mean"),
                                        gain=("gain", "mean"), share_switch=("pick", lambda x: float(np.mean(x != "max"))))
    g = g.reset_index()
    g["design"] = design
    return g
