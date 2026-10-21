"""Round-3 figures re-drawn from the saved CSVs (no recomputation).

    uv run python tracks/r3_t1/r3_figures.py
- fig_reflag_gain_vs_repeat_lr.pdf: top-3 sum - max (FPR 0.05) vs repeat-spike log-LR, one panel per data set,
  one point per monitor design.
- fig_reflag_tpr.pdf: best-of {max, top-3 sum} TPR per design (FPR 0.05 and 0.01), persistent-state gradual /
  positional and MonitoringBench all / S4.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "r2_t1"))
from r2lib import mpl_style  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "results" / "r3_t1"
COL = {"history-free": "#1baf7a", "history-aware": "#7d2a63", "reflag": "#eb6834", "ledger": "#2a78d6",
       "ledgernull": "#9fc3ee", "sample0": "#b0b0b0", "sample1": "#cfcfcf", "sample_mean": "#4a4a4a",
       "sample_units": "#eda100", "length_only": "#e87ba4"}


def reflag():
    plt = mpl_style()
    F = pd.read_csv(OUT / "reflag_features.csv")
    G = pd.read_csv(OUT / "reflag_gains.csv")
    datas = list(dict.fromkeys(F.data))
    nc = int(np.ceil(len(datas) / 2))
    fig, axes = plt.subplots(2, nc, figsize=(7.4, 4.6), squeeze=False)
    for ax, data in zip(axes.ravel(), datas):
        for design, c in COL.items():
            f = F[(F.data == data) & (F.design == design)]
            g = G[(G.set == f"{data}:{design}") & (G.alpha == 0.05) & (G.detector == "top3sum")]
            if f.empty or g.empty:
                continue
            g = g.iloc[0]
            ax.errorbar(f.rep_lr.iloc[0], g.gain_vs_max, yerr=[[g.gain_vs_max - g.lo], [g.hi - g.gain_vs_max]],
                        fmt="o", ms=4, lw=0.7, color=c, label=design)
        ax.axhline(0, color="#999", lw=0.8)
        ax.set_title(data, loc="left", fontsize=8)
    for ax in axes[1]:
        ax.set_xlabel("repeat-spike log-LR")
    for ax in axes[:, 0]:
        ax.set_ylabel("top-3 sum - max\n(FPR 0.05)")
    for ax in axes.ravel()[len(datas):]:
        ax.axis("off")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, ncol=5, loc="lower center", fontsize=6.5)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    fig.savefig(OUT / "fig_reflag_gain_vs_repeat_lr.pdf")

    M = pd.read_csv(OUT / "reflag_matched.csv")
    M = M[M.threshold_kind == "calibrated"]
    show = ["ps:gradual", "ps:positional", "mb:all", "mb:S4"]
    designs = [d for d in COL if d != "length_only"]
    fig, axes = plt.subplots(1, len(show), figsize=(7.4, 2.9), sharey=True)
    for ax, data in zip(axes, show):
        for k, al in enumerate((0.05, 0.01)):
            for j, design in enumerate(designs):
                m = M[(M.data == data) & (M.design == design) & (M.alpha == al)].set_index("detector")
                if m.empty:
                    continue
                for det, mk in (("max", "o"), ("top3sum", "^")):
                    ax.errorbar(m.loc[det].tpr, j + (0.18 if k == 0 else -0.18),
                                xerr=[[m.loc[det].tpr - m.loc[det].tpr_lo], [m.loc[det].tpr_hi - m.loc[det].tpr]],
                                fmt=mk, ms=3.5, lw=0.6, color=COL[design], alpha=1.0 if k == 0 else 0.55)
        ax.set_yticks(range(len(designs)), designs, fontsize=7)
        ax.set_title(data, loc="left", fontsize=8)
        ax.set_xlabel("TPR (o max, ^ top-3 sum)")
        ax.set_xlim(0, 1)
    fig.text(0.01, 0.01, "upper marker: FPR 0.05; lower (faded): FPR 0.01; 95% CI incl. calibration noise", fontsize=6.5)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "fig_reflag_tpr.pdf")


if __name__ == "__main__":
    reflag()
