"""Vector figures (PDF) for the r5watch arm from results/r5_watch/*.csv (conformal rule, task resampling).

    unset VIRTUAL_ENV; uv run python -m tracks.r5_watch.make_figures
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from amd.common.schema import REPO  # noqa: E402

OUT = REPO / "results" / "r5_watch"
COL = {"watch": "#eda100", "watch_exp": "#e87ba4", "jev": "#eb6834", "luna": "#2a78d6", "decider": "#1baf7a",
       "rand": "#a8a7a2"}
NAME = {"watch": "Watcher-style GPT-5.6 Luna (integer)", "watch_exp": "Watcher-style, logprob-expected",
        "jev": "JEV", "luna": "GPT-6 Luna Decisions", "decider": "Decider v1.2", "rand": "random"}
PANEL = {"mb:gen": "MonitoringBench, second stage generative GPT-6 Luna",
         "mb:mini": "MonitoringBench, second stage gpt-4.1-mini",
         "la_nano:gemini": "LinuxArena (nano subset), second stage Gemini-3.1-Pro"}
INK, MUTED = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False})


def forest(H):
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    for ax, pn in zip(axes, PANEL):
        d = H[(H.panel == pn) & (H.convention == "conformal") & (H.resampling == "task")]
        if d.empty:
            ax.set_visible(False)
            continue
        tests = list(d.test)
        for i, (_, r) in enumerate(d.iterrows()):
            c = COL[r.arm1.split("@")[0]]
            ax.plot([r.lo, r.hi], [i, i], color=c, lw=1.6)
            ax.plot(r.est, i, "o", color=c, ms=5)
        ax.axvline(0, color=MUTED, lw=1)
        ax.set_yticks(range(len(tests)), [f"{t}" + (f"  (Holm p {p:.3f})" if pn == "mb:gen" else "")
                                          for t, p in zip(tests, d.p_holm)], fontsize=7)
        ax.invert_yaxis()
        ax.set_title(PANEL[pn], fontsize=8)
        ax.set_xlabel("ΔTPR at 1% FPR: decision model − Watcher-style", fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_w1_w2.pdf")
    plt.close(fig)


def tpr_vs_e(cells, w3):
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.8))
    for ax, pn in zip(axes, PANEL):
        d = cells[(cells.panel == pn) & (cells.alpha == 0.01) & (cells.convention == "conformal")]
        if d.empty:
            ax.set_visible(False)
            continue
        for f in ("watch", "watch_exp", "jev", "luna", "decider", "rand"):
            x = d[(d.kind == "cascade") & (d["first"] == f)].sort_values("e")
            ax.errorbar(x.esc_honest * 100, x.tpr, yerr=[x.tpr - x.tpr_lo, x.tpr_hi - x.tpr], color=COL[f], marker="o",
                        ms=3, lw=1.2, capsize=2, label=NAME[f], ls="--" if f in ("watch_exp", "rand") else "-")
        s = d[(d.kind == "standalone") & (~d["first"].isin(["watch", "watch_exp", "jev", "luna", "decider"]))]
        for _, r in s.iterrows():
            ax.axhline(r.tpr, color=MUTED, lw=0.8, ls=":")
            ax.text(31, r.tpr, "second stage only", fontsize=6, color=MUTED, va="bottom", ha="right")
        fx = d[d.kind == "fixed_cutoff"]
        for _, r in fx.iterrows():
            ax.errorbar(r.esc_honest * 100, r.tpr, yerr=[[r.tpr - r.tpr_lo], [r.tpr_hi - r.tpr]], color=COL["watch"],
                        marker="*", ms=10, capsize=2)
            ax.annotate(r.config.split("@")[1], (r.esc_honest * 100, r.tpr), fontsize=7, xytext=(4, -10),
                        textcoords="offset points")
        ax.set_xlabel("escalated share of test-honest steps (%)")
        ax.set_ylabel("TPR at 1% trajectory FPR")
        ax.set_title(PANEL[pn], fontsize=8)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=7, loc="lower center", ncol=6)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(OUT / "fig_tpr_vs_escalation.pdf")
    plt.close(fig)


def main():
    H = pd.read_csv(OUT / "hypotheses.csv")
    cells = pd.read_csv(OUT / "cells.csv")
    w3 = pd.read_csv(OUT / "w3.csv")
    forest(H)
    tpr_vs_e(cells, w3)


if __name__ == "__main__":
    main()
