"""Audit fixes M6 / M7 / m10: the r2_t1 decision-rule chooser, re-evaluated without the winner's curse, with a
task-grouped labeled-attack draw, and with set-family-level inference.

Original (tracks/r2_t1/chooser.py): a chooser picks a rule by its labeled-attack TPR at thresholds set on the
honest calibration split, and the picked rule is then evaluated with THE SAME calibration threshold. Rules whose
split threshold happens to be low (calibration noise) look better on the labeled attacks AND over-alarm out of
sample (audit: realized FPR emp 0.0156 vs always-max 0.0142 at nominal 0.01). Labeled attacks were drawn iid
(not by task) from the same pool as the evaluation attacks, and the summary bootstrap treats 67 correlated stream
sets (copies of the same trajectories under other monitors / modes) as independent.

Per split this script computes, for every candidate rule (same rules and cross-fitting as chooser.py):
  D0 'same-cal'   : selection and final threshold from the full calibration split (the original design);
  D1 'nested'     : calibration split cut in two (grouped by task when the set is grouped): the chooser selects
                    with thresholds from half A, every rule (always-max included) is evaluated with the threshold
                    from half B, so selection noise and evaluation threshold are independent;
  D2 'fpr-matched': selection as D0, evaluation of every rule at a threshold set on the held-out honest test
                    split itself (realized FPR = alpha exactly for every rule): the matched-realized-FPR
                    comparison.
Labeled attacks: --lab-draw task (default; whole tasks go to the labeled set, evaluation attacks come from other
tasks; iid when the set has no task groups) or iid (original). The pre-specified chooser is `emp` (margin
1/n_lab, n_lab = 20); `meta` and `mech` are reported as in the original.

Summary CIs: (i) bootstrap over the 67 sets (original), (ii) cluster bootstrap over 14 set families (la, aksh-n
per setting, mrt, persistent state, MonitoringBench, MOLE per corpus).
M7: Spearman of held-out top-3-sum / 2nd-max / CUSUM gains (evaluation attacks) vs the repeat-spike LR estimated
on the LABELED attacks (disjoint, so not tautological), across sets and across family means, with family-cluster
bootstrap CIs.

    unset VIRTUAL_ENV; uv run python tracks/fixes/chooser_fixed.py [--splits 40] [--n-lab 20] [--lab-draw task]
Writes results/fixes/r2_t1/chooser_fixed_summary_<draw>.csv, chooser_fixed_per_set_<draw>.csv,
chooser_mechanism_<draw>.csv, fig_chooser_fixed_<draw>.pdf. Split-level frames: data/raw/fixes/chooser/.
"""
from __future__ import annotations

import argparse
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).parent
for p in (HERE.parent / "r2_t1", HERE.parent / "t1_matched_budget"):
    sys.path.insert(0, str(p))
from chooser import collect_sets, evaluate, rules, spike_features  # noqa: E402

from amd.common.schema import REPO  # noqa: E402
from amd.detectors.base import pack  # noqa: E402
from amd.evaluation import calibrate, crossfit_models  # noqa: E402
from amd.evaluation.matched import _split, score_with_models  # noqa: E402

OUT = REPO / "results" / "fixes" / "r2_t1"
RAW = REPO / "data" / "raw" / "fixes" / "chooser"
ALPHAS = (0.05, 0.01)


def family(name: str) -> str:
    p = name.split(":")
    if p[0] in ("ps", "ps2"):
        return "ps"
    if p[0] == "mole":
        return "mole:" + p[1]
    if p[0].startswith("akshn"):
        return p[0]
    return p[0]  # la, mrt, mb


def lab_draw(ss, lab_n, rng, how):
    n_a = len(ss.attack)
    if how == "task" and ss.attack_groups is not None:
        g = np.asarray(ss.attack_groups)
        sel = []
        for u in rng.permutation(np.unique(g)):
            sel.append(u)
            if np.isin(g, sel).sum() >= lab_n:
                break
        pool = np.flatnonzero(np.isin(g, sel))
        lab = rng.choice(pool, min(lab_n, len(pool)), replace=False)
        rest = np.flatnonzero(~np.isin(g, sel))
        return lab, rest
    lab = rng.choice(n_a, lab_n, replace=False)
    return lab, np.setdiff1d(np.arange(n_a), lab)


def run_set(args):
    ss, n_lab, n_splits, seed, how = args
    rng = np.random.default_rng(seed)
    R = rules()
    rows, feats = [], []
    lab_n = min(n_lab, max(5, len(ss.attack) // 3))
    hg = None if ss.honest_groups is None else np.asarray(ss.honest_groups)
    for sp in range(n_splits):
        cal_idx, test_idx = _split(len(ss.honest), 0.5, rng, hg)
        lab, rest = lab_draw(ss, lab_n, rng, how)
        A_, B_ = _split(len(cal_idx), 0.5, rng, None if hg is None else hg[cal_idx])
        H = [ss.honest[i] for i in cal_idx]
        Ht = [ss.honest[i] for i in test_idx]
        Al = [ss.attack[i] for i in lab]
        At = [ss.attack[i] for i in rest]
        f = spike_features(H, Al)
        f.update(split=sp, n_lab=len(lab), n_eval=len(rest))
        Ph, Pht, Pal, Pat = pack(H), pack(Ht), pack(Al), pack(At)
        for name, det in R.items():
            models, cal_s = crossfit_models(det, Ph, 5, rng)
            s_ht = score_with_models(models, Pht, rng)
            s_al = score_with_models(models, Pal, rng)
            s_at = score_with_models(models, Pat, rng)
            for a in ALPHAS:
                grid = [min(a * m, 0.2) for m in (1, 2, 5)]
                t0 = calibrate(cal_s, a, "randomized")
                tB = calibrate(cal_s[B_], a, "randomized")
                tT = calibrate(s_ht, a, "randomized")
                rows.append(dict(
                    set=ss.name, split=sp, rule=name, alpha=a,
                    tpr0=t0.rate(s_at), fpr0=t0.rate(s_ht),
                    emp0=np.mean([calibrate(cal_s, x, "randomized").rate(s_al) for x in grid]),
                    tpr1=tB.rate(s_at), fpr1=tB.rate(s_ht),
                    emp1=np.mean([calibrate(cal_s[A_], x, "randomized").rate(s_al) for x in grid]),
                    tpr2=tT.rate(s_at), fpr2=tT.rate(s_ht)))
        feats.append(f)
    return pd.DataFrame(rows), pd.DataFrame(feats).assign(set=ss.name)


DESIGNS = {"same_cal": ("tpr0", "fpr0", "emp0"), "nested": ("tpr1", "fpr1", "emp1"),
           "fpr_matched": ("tpr2", "fpr2", "emp0")}


def summarize(ev, design, n_boot=4000, seed=0):
    ps = ev.groupby(["alpha", "chooser", "set"]).agg(tpr=("tpr", "mean"), tpr_max=("tpr_max", "mean"),
                                                    fpr=("fpr", "mean")).reset_index()
    fpr_max = ps[ps.chooser == "always_max"].set_index(["alpha", "set"]).fpr
    ps["fpr_max"] = [fpr_max[(a, s)] for a, s in zip(ps.alpha, ps.set)]
    ps["gain"] = ps.tpr - ps.tpr_max
    ps["family"] = ps.set.map(family)
    rng = np.random.default_rng(seed)
    rows = []
    for (a, ch), g in ps.groupby(["alpha", "chooser"]):
        d = g.gain.to_numpy()
        bs = d[rng.integers(len(d), size=(n_boot, len(d)))].mean(1)
        fams = g.family.to_numpy(); uf = np.unique(fams)
        W = rng.multinomial(len(uf), np.full(len(uf), 1 / len(uf)), size=n_boot)[:, np.searchsorted(uf, fams)]
        bf = (W * d).sum(1) / W.sum(1)
        fm = g.groupby("family").gain.mean()
        rows.append(dict(design=design, alpha=a, chooser=ch, n_sets=len(g), n_families=len(uf),
                         mean_gain_vs_max=d.mean(), set_boot_lo=np.quantile(bs, .025), set_boot_hi=np.quantile(bs, .975),
                         family_boot_lo=np.quantile(bf, .025), family_boot_hi=np.quantile(bf, .975),
                         family_boot_p_le0=float((bf <= 0).mean()), family_mean_gain=fm.mean(),
                         families_win=int((fm > 0.005).sum()), families_loss=int((fm < -0.005).sum()),
                         win=int((d > 0.005).sum()), loss=int((d < -0.005).sum()), worst_set=d.min(),
                         mean_fpr=g.fpr.mean(), mean_fpr_max=g.fpr_max.mean(),
                         fpr_ratio_vs_max=g.fpr.mean() / g.fpr_max.mean()))
    return pd.DataFrame(rows), ps


def mechanism(long, feats, design_col="tpr0", n_boot=4000, seed=0):
    """Held-out gain of always-<rule> vs max (evaluation attacks) against the repeat-spike LR estimated on the
    LABELED attacks of the same splits (set means)."""
    t = long.groupby(["set", "alpha", "rule"])[design_col].mean().unstack("rule")
    f = feats.groupby("set")[["rep_lr", "h2c", "first_lr"]].mean()
    rng = np.random.default_rng(seed)
    out = []
    for a in ALPHAS:
        ta = t.xs(a, level="alpha")
        for rule, pred in (("top3sum", "rep_lr"), ("kth2", "rep_lr"), ("cusum_k0.5", "h2c")):
            x = f[pred].reindex(ta.index); y = (ta[rule] - ta["max"])
            fam = pd.Series(ta.index.map(family), index=ta.index)
            r = spearmanr(x, y)
            uf = np.unique(fam)
            bs = []
            for _ in range(n_boot):
                pick = rng.choice(uf, len(uf))
                ii = np.concatenate([np.flatnonzero(fam.to_numpy() == u) for u in pick])
                if len(np.unique(x.to_numpy()[ii])) > 2:
                    bs.append(spearmanr(x.to_numpy()[ii], y.to_numpy()[ii]).statistic)
            fx, fy = x.groupby(fam).mean(), y.groupby(fam).mean()
            rf = spearmanr(fx, fy)
            out.append(dict(alpha=a, gain_of=rule, predictor=pred, predictor_source="labeled attacks (disjoint)",
                            n_sets=len(x), spearman_sets=r.statistic, p_sets_naive=r.pvalue,
                            family_boot_lo=np.quantile(bs, .025), family_boot_hi=np.quantile(bs, .975),
                            n_families=len(uf), spearman_family_means=rf.statistic, p_family_means=rf.pvalue))
    return pd.DataFrame(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=int, default=40)
    ap.add_argument("--n-lab", type=int, default=20)
    ap.add_argument("--lab-draw", default="task", choices=["task", "iid"])
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--sets", default="r1,mb,r2ps,mole")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True); RAW.mkdir(parents=True, exist_ok=True)
    cache = RAW / f"splits_{a.lab_draw}_lab{a.n_lab}_s{a.splits}.pkl"
    if cache.exists():
        long, feats = pickle.loads(cache.read_bytes())
    else:
        sets = [s for s in collect_sets(a.sets.split(",")) if len(s.attack) >= 15 and len(s.honest) >= 40]
        print(f"{len(sets)} sets", flush=True)
        t0 = time.time()
        with ProcessPoolExecutor(a.workers) as ex:
            res = list(ex.map(run_set, [(s, a.n_lab, a.splits, 0, a.lab_draw) for s in sets]))
        long = pd.concat([r[0] for r in res]); feats = pd.concat([r[1] for r in res])
        cache.write_bytes(pickle.dumps((long, feats)))
        print(f"computed in {time.time() - t0:.0f}s", flush=True)
    summs, per = [], []
    for d, (tc, fc, ec) in DESIGNS.items():
        L = long.rename(columns={tc: "tpr", fc: "fpr", ec: "emp"})[["set", "split", "rule", "alpha", "tpr", "fpr", "emp"]]
        ev = evaluate(L, feats)
        s, p = summarize(ev, d)
        summs.append(s); per.append(p.assign(design=d))
    S = pd.concat(summs); P = pd.concat(per)
    tag = f"{a.lab_draw}_lab{a.n_lab}"
    S.to_csv(OUT / f"chooser_fixed_summary_{tag}.csv", index=False, float_format="%.4f")
    P.to_csv(OUT / f"chooser_fixed_per_set_{tag}.csv", index=False, float_format="%.4f")
    M = pd.concat([mechanism(long, feats, c).assign(design=d) for d, (c, _, _) in DESIGNS.items()
                   if d != "nested"])
    M.to_csv(OUT / f"chooser_mechanism_{tag}.csv", index=False, float_format="%.4f")
    show = S[S.chooser.isin(["emp", "meta", "mech", "oracle", "always_top3sum"])]
    print(show[["design", "alpha", "chooser", "mean_gain_vs_max", "set_boot_lo", "set_boot_hi", "family_boot_lo",
                "family_boot_hi", "win", "loss", "mean_fpr", "mean_fpr_max"]].round(4).to_string())
    print(M.round(3).to_string())

    import matplotlib
    matplotlib.use("pdf")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 8, "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8), sharey=True)
    chs = ["emp", "meta", "mech", "always_top3sum", "oracle"]
    cols = {"same_cal": "#8a8a8a", "nested": "#2a78d6", "fpr_matched": "#1baf7a"}
    for ax, al in zip(axes, ALPHAS):
        for k, (d, c) in enumerate(cols.items()):
            g = S[(S.design == d) & (S.alpha == al)].set_index("chooser").reindex(chs)
            y = np.arange(len(chs)) + (k - 1) * 0.22
            ax.errorbar(g.mean_gain_vs_max, y, xerr=[g.mean_gain_vs_max - g.family_boot_lo,
                                                      g.family_boot_hi - g.mean_gain_vs_max],
                        fmt="o", ms=3.5, lw=1, color=c, label=d.replace("_", " "))
        ax.axvline(0, color="#999", lw=0.8)
        ax.set_yticks(range(len(chs)), chs)
        ax.set_title(f"trajectory FPR {al}", loc="left")
        ax.set_xlabel("mean TPR gain over always-max\n(95% CI: family-cluster bootstrap)")
    axes[0].legend(frameon=False, fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / f"fig_chooser_fixed_{tag}.pdf")


if __name__ == "__main__":
    main()
