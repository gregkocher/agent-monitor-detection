"""Vector figures (PDF) for Idea 05 round 1 from results/r5_jev/*.csv.

    unset VIRTUAL_ENV; uv run python -m tracks.r5_jev.make_figures
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from amd.common.schema import REPO  # noqa: E402

OUT = REPO / "results" / "r5_jev"
# reference categorical palette (fixed order), text in neutral inks
COL = {"jev": "#2a78d6", "nano": "#eb6834", "probe": "#1baf7a", "len": "#eda100", "decider": "#e87ba4",
       "oracle": "#4a3aa7", "rand": "#8a8984", "oracle_label": "#9085e9"}
NAME = {"jev": "JEV", "nano": "gpt-4.1-nano", "probe": "probe (FIBS axial)", "len": "action length",
        "rand": "random", "oracle": "oracle (LLM score)", "oracle_label": "label oracle", "decider": "Decider v1.2"}
INK, MUTED = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False})


def tpr_vs_e(df, panel, alpha, ax, title, firsts):
    d = df[(df.panel == panel) & (df.alpha == alpha) & (df.mapping == "floor")]
    if d.empty:
        ax.set_visible(False)
        return
    llm = d[d["first"] == "llm_only"].iloc[0]
    ax.axhspan(llm.tpr_lo, llm.tpr_hi, color="#d6d5d0", alpha=0.6, lw=0)
    ax.axhline(llm.tpr, color=INK, lw=1.5)
    ax.text(31.5, llm.tpr, "LLM only", va="center", fontsize=8, color=INK)
    jo = d[d["first"] == "jev_only"]
    if len(jo):
        ax.axhline(jo.iloc[0].tpr, color=COL["jev"], lw=1, ls=":")
        ax.text(31.5, jo.iloc[0].tpr, "JEV only", va="center", fontsize=8, color=MUTED)
    for f in firsts:
        x = d[d["first"] == f].sort_values("e")
        if x.empty:
            continue
        ls = "--" if f in ("rand", "oracle", "oracle_label") else "-"
        ax.errorbar(x.e * 100, x.tpr, yerr=[x.tpr - x.tpr_lo, x.tpr_hi - x.tpr], color=COL[f], lw=2, ls=ls,
                    marker="o", ms=4, capsize=2, label=NAME[f])
    ax.set_xticks([5, 10, 20, 30])
    ax.set_xlim(3, 38)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("escalated share of honest steps e (%)")
    ax.set_ylabel(f"TPR at {alpha:.0%} trajectory FPR")
    ax.set_title(title, fontsize=9, loc="left", color=INK)


def main():
    df = pd.read_csv(OUT / "cascade_cells.csv")
    firsts = ["jev", "nano", "probe", "len", "rand", "oracle", "oracle_label"]
    for alpha in (0.01, 0.05):
        fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.6), sharey=True)
        tpr_vs_e(df, "mb", alpha, axes[0], "MonitoringBench (2nd stage gpt-4.1-mini, none)", firsts)
        tpr_vs_e(df, "akshn_pooled", alpha, axes[1], "aksh-n pooled (2nd stage Gemini-3.1-Pro)", firsts)
        tpr_vs_e(df, "akshn_nano_pooled", alpha, axes[2], "aksh-n nano subset (pooled)", firsts)
        h, lab = axes[0].get_legend_handles_labels()
        fig.legend(h, lab, loc="lower center", ncol=7, frameon=False, fontsize=8)
        fig.tight_layout(rect=(0, 0.08, 1, 1))
        fig.savefig(OUT / f"fig_tpr_vs_e_alpha{int(alpha * 100)}.pdf")
        plt.close(fig)
    h = pd.read_csv(OUT / "hypotheses.csv")
    fig, ax = plt.subplots(figsize=(5.5, 2.6))
    y = range(len(h))[::-1]
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.axvline(-0.03, color="#e34948", lw=1, ls="--")
    ax.text(-0.03, len(h) - 0.4, "NI margin", color=MUTED, fontsize=7, ha="right")
    for yi, (_, r) in zip(y, h.iterrows()):
        ax.plot([r.lo, r.hi], [yi, yi], color=COL["jev"], lw=2)
        ax.plot(r.est, yi, "o", color=COL["jev"], ms=6)
        ax.text(max(r.hi, 0) + 0.01, yi, f"{r.est:+.3f} [{r.lo:+.3f}, {r.hi:+.3f}]"
                + ("  supported" if r.supported else "  not supported"), va="center", fontsize=7, color=INK)
    ax.set_yticks(list(y))
    ax.set_yticklabels(h.hypothesis)
    ax.set_xlabel("TPR difference at 1% trajectory FPR (95% CI)")
    lo, hi = min(h.lo.min(), -0.06), max(h.hi.max(), 0.05)
    ax.set_xlim(lo - 0.02, hi + 0.25)
    fig.tight_layout()
    fig.savefig(OUT / "fig_hypotheses.pdf")
    plt.close(fig)


if __name__ == "__main__":
    main()
