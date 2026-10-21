"""Round-2 track-1 figures (vector PDF) for the rule chooser and the mechanism view, plus MOLE daily-budget curves.

    uv run python tracks/r2_t1/make_figures.py --chooser-tag all_lab20
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from r2lib import COLORS, LABEL, mpl_style  # noqa: E402

from amd.common.schema import REPO  # noqa: E402

OUT = REPO / "results" / "r2_t1"
FAM_COL = {"la": "#2a78d6", "akshn": "#1baf7a", "mrt": "#e87ba4", "ps": "#eda100", "mb": "#eb6834",
           "ps2": "#7d2a63", "mole": "#4a4a4a"}
FAM_LAB = {"la": "LinuxArena", "akshn": "aksh-n", "mrt": "MRT", "ps": "persistent state (gpt-4o)",
           "mb": "MonitoringBench", "ps2": "persistent state (round 2)", "mole": "MOLE (round 2)"}


def fam(s):
    f = s.split(":")[0]
    return "akshn" if f.startswith("akshn") else f


def chooser_figs(tag):
    plt = mpl_style()
    ps = pd.read_csv(OUT / f"chooser_per_set_{tag}.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.3), sharey=True)
    for ax, al in zip(axes, (0.05, 0.01)):
        g = ps[ps.alpha == al]
        base = g[g.chooser == "oracle"].set_index("set").gain.sort_values()
        y = np.arange(len(base))
        for ch, c, mk in (("oracle", "#b0b0b0", "|"), ("emp", "#1baf7a", "o"), ("meta", "#2a78d6", "x")):
            v = g[g.chooser == ch].set_index("set").gain.reindex(base.index)
            ax.scatter(v, y, s=14 if mk != "|" else 30, marker=mk, color=c, label=ch, zorder=3)
        ax.axvline(0, color="#999", lw=0.8)
        ax.set_yticks(y, [s[:34] for s in base.index], fontsize=4.2)
        ax.set_xlabel(f"TPR gain over always-max (FPR {al})")
        ax.set_title(f"FPR {al}", loc="left")
    axes[0].legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / f"fig_chooser_per_set_{tag}.pdf")

    # summary vs number of labeled attacks
    rows = []
    for f in sorted(OUT.glob("chooser_summary_*lab*.csv")):
        t = f.stem.replace("chooser_summary_", "")
        d = pd.read_csv(f)
        d["tag"] = t
        d["n_lab"] = int(t.split("lab")[-1])
        d["family"] = t.split("_lab")[0]
        rows.append(d)
    S = pd.concat(rows)
    fam_sel = S.family.iloc[0] if (S.family == tag.split("_lab")[0]).sum() == 0 else tag.split("_lab")[0]
    S = S[S.family == fam_sel]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8), sharey=False)
    for ax, al in zip(axes, (0.05, 0.01)):
        for ch, c in (("oracle", "#b0b0b0"), ("emp", "#1baf7a"), ("meta", "#2a78d6"), ("cusum_tuned", "#b23a80"),
                      ("mech", "#eda100"), ("always_top3sum", "#0f7a55")):
            g = S[(S.alpha == al) & (S.chooser == ch)].sort_values("n_lab")
            if g.empty:
                continue
            ax.errorbar(g.n_lab, g.mean_gain_vs_max, yerr=[g.mean_gain_vs_max - g.gain_lo, g.gain_hi - g.mean_gain_vs_max],
                        marker="o", ms=3.5, lw=1.2, capsize=2, color=c, label=ch.replace("_", " "))
        ax.axhline(0, color="#999", lw=0.8)
        ax.set_xscale("log"); ax.set_xticks([10, 20, 40], ["10", "20", "40"])
        ax.xaxis.set_minor_formatter(plt.NullFormatter()); ax.xaxis.set_minor_locator(plt.NullLocator())
        ax.set_xlabel("labeled attacks available to the chooser")
        ax.set_ylabel(f"mean TPR gain over max (FPR {al})")
        ax.set_title(f"FPR {al} ({S.n_sets.max()} sets)", loc="left")
    axes[1].legend(frameon=False, fontsize=6.5, loc="lower left")
    fig.tight_layout()
    fig.savefig(OUT / f"fig_chooser_vs_nlab_{fam_sel}.pdf")


def mechanism_fig(tag):
    plt = mpl_style()
    R = pd.read_csv(OUT.parents[1] / "data" / "raw" / "r2_t1" / "chooser_out" / f"chooser_rules_{tag}.csv")
    F = pd.read_csv(OUT / f"chooser_features_{tag}.csv")
    t = R.groupby(["set", "alpha", "rule"]).tpr.mean().unstack("rule")
    gain = t.sub(t["max"], axis=0).reset_index()
    fs = F.groupby("set")[["h2c", "rep_lr"]].mean()
    from scipy.stats import spearmanr
    fig, axes = plt.subplots(1, 3, figsize=(7.6, 2.8))
    for ax, (rule, x) in zip(axes, (("top3sum", "rep_lr"), ("kth2", "rep_lr"), ("cusum_k0.5", "h2c"))):
        g = gain[gain.alpha == 0.05].set_index("set").join(fs)
        for f, c in FAM_COL.items():
            s = g[g.index.map(fam) == f]
            if len(s):
                ax.scatter(s[x], s[rule], color=c, s=16, label=FAM_LAB[f], edgecolors="white", linewidths=0.3)
        r = spearmanr(g[x], g[rule])
        ax.axhline(0, color="#999", lw=0.8)
        ax.set_title(f"{LABEL.get(rule, rule)} - max\nSpearman {r.statistic:+.2f} (n={len(g)})", loc="left")
        ax.set_xlabel("repeat-spike log-LR (cal. split)" if x == "rep_lr" else "honest spike persistence h2c")
    axes[0].set_ylabel("TPR gain over max, FPR 0.05")
    axes[2].legend(frameon=False, fontsize=5.5, loc="lower left")
    fig.tight_layout()
    fig.savefig(OUT / f"fig_mechanism_{tag}.pdf")


def mole_rank_fig():
    f = OUT / "mole_daily_rank.csv"
    if not f.exists():
        return
    plt = mpl_style()
    R = pd.read_csv(f)
    corpora = list(dict.fromkeys(R.corpus))
    mons = list(dict.fromkeys(R.monitor))
    short = {"gpt53_single_day": "gpt53 single-day", "gpt53_multiday": "gpt53 multiday",
             "deepseek_v4_flash_single_day": "DeepSeek-V4 single-day"}
    fig, axes = plt.subplots(len(corpora), len(mons), figsize=(7.2, 2.1 * len(corpora) + 0.6), sharex=True,
                             sharey="row", squeeze=False)
    for i, c in enumerate(corpora):
        for j, m in enumerate(mons):
            ax = axes[i, j]
            g = R[(R.corpus == c) & (R.monitor == m)]
            for d, gg in g.groupby("detector"):
                col = "#000" if d == "today" else COLORS.get(d, "#888")
                ax.plot(gg.K, gg.recall, marker="o", ms=2.2, lw=1.4 if d == "today" else 0.9, color=col,
                        ls="--" if d == "today" else "-",
                        label="today's score only (MOLE)" if d == "today" else LABEL.get(d, d))
            ax.set_title(f"{short.get(c, c)}: {m}", loc="left", fontsize=7.5)
            if i == len(corpora) - 1:
                ax.set_xlabel("accounts reviewed per day (K)")
        axes[i, 0].set_ylabel("R@K/day")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, loc="lower center", ncol=5, fontsize=6.5)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(OUT / "fig_mole_daily_budget.pdf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chooser-tag", default="all_lab20")
    a = ap.parse_args()
    chooser_figs(a.chooser_tag)
    if (OUT / f"chooser_features_{a.chooser_tag}.csv").exists():
        mechanism_fig(a.chooser_tag)
    mole_rank_fig()


if __name__ == "__main__":
    main()
