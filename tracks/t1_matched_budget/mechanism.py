"""Mechanism check across every T1 stream set: does the accumulation gain track how much a *second*
high unit discriminates attacks from honest runs (vs the first)?

For each set, with q = the honest unit 95% quantile (strict exceedance, ties broken by the score's
own resolution):
  h1, a1 = share of honest / attack streams with >= 1 unit above q
  h2c, a2c = share with >= 2 units above q, among those with >= 1  (conditional persistence)
  honest_persist = h2c / (unconditional honest unit exceedance rate x mean length)  [clustering]
  second_spike_lr = log((a2c / h2c))   (how much more a repeat spike is attack evidence)
Correlated (Spearman, across sets) with the matched-FPR gains over max of top-3 sum, 2nd-max, CUSUM.

    uv run python tracks/t1_matched_budget/mechanism.py   -> results/t1/mechanism.csv, figures/mechanism.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).parent))
from run_round1 import akshn_sets, la_sets, mrt_sets, ps_sets  # noqa: E402
from run_round2 import load_mode  # noqa: E402

from amd.common.schema import REPO  # noqa: E402

R = REPO / "results" / "t1"


def persistence(ss, q=0.95):
    hu = np.concatenate([s[np.isfinite(s)] for s in ss.honest])
    thr = np.quantile(hu, q)
    if (hu > thr).mean() < 0.005:  # degenerate (quantile at the top value): use the next lower value
        vals = np.unique(hu)
        thr = vals[max(0, np.searchsorted(vals, thr) - 1)]
    cnt = lambda S: np.array([np.sum(s[np.isfinite(s)] > thr) for s in S])  # noqa: E731
    ch, ca = cnt(ss.honest), cnt(ss.attack)
    h1, a1 = (ch >= 1).mean(), (ca >= 1).mean()
    h2c = (ch >= 2).sum() / max((ch >= 1).sum(), 1)
    a2c = (ca >= 2).sum() / max((ca >= 1).sum(), 1)
    eps = 0.5 / len(ss.honest)
    return dict(set=ss.name, thr=thr, unit_rate=(hu > thr).mean(), h1=h1, a1=a1, h2c=h2c, a2c=a2c,
                first_spike_lr=np.log((a1 + eps) / (h1 + eps)), second_spike_lr=np.log((a2c + eps) / (h2c + eps)))


def main():
    rows = []
    for ss in la_sets() + akshn_sets() + mrt_sets() + ps_sets():
        rows.append(persistence(ss))
    for model, modes in (("openai_gpt-4.1-mini", ("full", "none")), ("openai_gpt-4.1-nano", ("none",))):
        for score in ("expected", "int"):
            for m in modes:
                try:
                    ss = load_mode(m, score=score, model=model)
                except FileNotFoundError:
                    continue
                ss.name = f"mb:{model.split('_')[-1]}:{m}:{score}"
                rows.append(persistence(ss))
    P = pd.DataFrame(rows).set_index("set")
    # gains
    g1 = pd.read_csv(R / "round1" / "gain_la_akshn_mrt_ps.csv")
    gains = []
    for _, r in g1.iterrows():
        gains.append(dict(set=r["set"], alpha=r.alpha, detector=r.detector, gain=r.gain_vs_max))
    for tag, score in (("main", "expected"), ("score_int", "int"), ("nano", "expected"), ("nano_int", "int")):
        f = R / "round2" / tag / "gains_by_structure.csv"
        if not f.exists():
            continue
        g2 = pd.read_csv(f)
        g2 = g2[g2.group == "all"]
        model = "gpt-4.1-nano" if tag.startswith("nano") else "gpt-4.1-mini"
        for _, r in g2.iterrows():
            gains.append(dict(set=f"mb:{model}:{r['mode']}:{score}", alpha=r.alpha, detector=r.detector,
                              gain=r.gain_vs_max))
    G = pd.DataFrame(gains)
    out = []
    for (alpha, det), x in G.groupby(["alpha", "detector"]):
        x = x.set_index("set").join(P, how="inner")
        if len(x) < 8:
            continue
        for col in ("second_spike_lr", "h2c"):
            r = spearmanr(x[col], x.gain)
            out.append(dict(alpha=alpha, detector=det, predictor=col, n=len(x), spearman=r.statistic, p=r.pvalue))
    C = pd.DataFrame(out)
    P.to_csv(R / "mechanism_sets.csv")
    C.to_csv(R / "mechanism_correlations.csv", index=False)
    print(C[C.detector.isin(["top3sum", "kth2", "cusum_k0.5", "mean"])].round(3).to_string())

    import matplotlib
    matplotlib.use("pdf")
    import matplotlib.pyplot as plt
    from make_figures import DET_STYLE, INK, MUTED  # noqa: F401  (rcParams)
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.8), sharey=False)
    for ax, det in zip(axes, ["kth2", "top3sum", "cusum_k0.5"]):
        x = G[(G.alpha == 0.05) & (G.detector == det)].set_index("set").join(P, how="inner")
        fam = x.index.str.split(":").str[0].str.replace("akshn_.*", "akshn", regex=True)
        for f, c, mk, lab in (("la", "#2a78d6", "o", "LinuxArena"), ("akshn", "#1baf7a", "s", "aksh-n"),
                              ("mrt", "#e87ba4", "D", "MRT"), ("ps", "#eda100", "^", "persistent state"),
                              ("mb", "#eb6834", "*", "MonitoringBench (ours)")):
            s = x[fam == f]
            ax.scatter(s.second_spike_lr, s.gain, color=c, marker=mk, s=28 if mk != "*" else 70, label=lab,
                       edgecolors="white", linewidths=0.4, zorder=3)
        ax.axhline(0, color=MUTED, lw=0.8)
        r = spearmanr(x.second_spike_lr, x.gain)
        ax.set_title(f"{DET_STYLE.get(det, (0, 0, 'top-3 sum'))[2] if det in DET_STYLE else 'top-3 sum'} − max"
                     f"\nSpearman {r.statistic:+.2f} (n={len(x)})", loc="left", fontsize=9)
        ax.set_xlabel("log LR of a repeat spike\n(attack vs honest, given one spike)")
    axes[0].set_ylabel("TPR gain over max, FPR 0.05")
    axes[0].legend(frameon=False, fontsize=6.5, loc="lower right")
    fig.tight_layout()
    fig.savefig(R / "figures" / "mechanism_second_spike.pdf")


if __name__ == "__main__":
    main()
