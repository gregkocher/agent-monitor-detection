"""Vector figures (PDF) for the r5luna arm from results/r5_luna/*.csv (conformal convention unless noted).

    unset VIRTUAL_ENV; uv run python -m tracks.r5_luna.make_figures
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from amd.common.schema import REPO  # noqa: E402

OUT = REPO / "results" / "r5_luna"
# reference categorical palette (fixed order); text in neutral inks
COL = {"luna": "#2a78d6", "jev": "#eb6834", "nano": "#1baf7a", "gen": "#eda100", "luna_full": "#4a3aa7",
       "jev_full": "#e87ba4"}
NAME = {"luna": "Luna Decisions", "jev": "JEV", "nano": "gpt-4.1-nano", "gen": "generative Luna",
        "luna_full": "Luna Decisions, full text", "jev_full": "JEV, full text"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#d6d5d0"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False})


def forest(H):
    tests = list(H[(H.convention == "conformal") & (H.resampling == "orig")].test)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    marks = [("conformal", "orig", "o", INK, "conformal (primary)"), ("plugin", "orig", "s", MUTED, "plug-in"),
             ("conformal", "task", "D", "#2a78d6", "conformal, main-task resampling")]
    for j, (conv, rs, m, c, lab) in enumerate(marks):
        d = H[(H.convention == conv) & (H.resampling == rs)].set_index("test")
        y = np.arange(len(tests)) + (j - 1) * 0.22
        for i, t in enumerate(tests):
            if t not in d.index:
                continue
            r = d.loc[t]
            ax.plot([r.lo, r.hi], [y[i], y[i]], color=c, lw=1.5)
            ax.plot(r.est, y[i], m, color=c, ms=5, mfc=c if j != 1 else "white", label=lab if i == 0 else None)
    ax.axvline(0, color=MUTED, lw=1)
    labels = []
    d0 = H[(H.convention == "conformal") & (H.resampling == "orig")].set_index("test")
    for t in tests:
        r = d0.loc[t]
        labels.append(f"{t}  ({r.arm1} − {r.arm2})\nHolm p = {r.p_holm:.3f}")
    ax.set_yticks(np.arange(len(tests)), labels, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("difference (TPR at 1% trajectory FPR; AUROC for H5d-AUC), 95% bootstrap CI")
    ax.legend(frameon=False, fontsize=7, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
    fig.tight_layout()
    fig.savefig(OUT / "fig_hypotheses.pdf")
    plt.close(fig)


def tpr_vs_e(cells, panel, alpha, ax, title, firsts, ref_only=("luna", "jev")):
    d = cells[(cells.panel == panel) & (cells.alpha == alpha) & (cells.convention == "conformal")]
    if d.empty:
        ax.set_visible(False)
        return
    llm = d[(d.kind == "standalone") & (d["first"] == "llm")]
    if len(llm):
        r = llm.iloc[0]
        ax.axhspan(r.tpr_lo, r.tpr_hi, color=GRID, alpha=0.6, lw=0)
        ax.axhline(r.tpr, color=INK, lw=1.5)
        ax.text(31.5, r.tpr, "LLM only", va="center", fontsize=7, color=INK)
    for f in firsts:
        x = d[(d.kind == "cascade") & (d["first"] == f)].sort_values("e")
        if x.empty:
            continue
        ax.errorbar(x.e * 100, x.tpr, yerr=[x.tpr - x.tpr_lo, x.tpr_hi - x.tpr], color=COL[f], lw=2, marker="o",
                    ms=4, capsize=2, label=NAME[f])
        so = d[(d.kind == "standalone") & (d["first"] == f)]
        if len(so) and f in ref_only:
            ax.axhline(so.iloc[0].tpr, color=COL[f], lw=1, ls=":")
    ax.set_xticks([5, 10, 20, 30])
    ax.set_xlim(3, 38)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("escalated share of honest steps e (%)")
    ax.set_ylabel(f"TPR at {alpha:.0%} trajectory FPR")
    ax.set_title(title, fontsize=9, loc="left", color=INK)


def per_setting(R):
    d = R[(R.convention == "conformal") & (R.resampling == "orig") & (R.alpha == 0.01) & (R.e == 0.1)]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4), sharex=True)
    for ax, h, ttl in ((axes[0], "H5a-AK", "Luna − JEV cascade, e = 10%, 1% FPR (full eval)"),
                       (axes[1], "H5b-AK", "Luna − nano cascade, e = 10%, 1% FPR (nano subset)")):
        x = d[d.test.str.startswith(h + " ")]
        order = [t for t in x.test if "akshn_" in t] + [f"{h} pooled", f"{h} leave-SHADE-out", f"{h} equal-weight"]
        x = x.set_index("test").loc[[t for t in order if t in set(x.test)]]
        y = np.arange(len(x))
        for i, (t, r) in enumerate(x.iterrows()):
            c = INK if "akshn_" not in t else MUTED
            ax.plot([r.lo, r.hi], [i, i], color=c, lw=1.5)
            ax.plot(r.est, i, "o", color=c, ms=4)
        ax.set_yticks(y, [t.replace(h + " ", "").replace("akshn_", "") for t in x.index], fontsize=7)
        ax.invert_yaxis()
        ax.axvline(0, color=MUTED, lw=1)
        ax.set_title(ttl, fontsize=8, loc="left", color=INK)
        ax.set_xlabel("ΔTPR, 95% CI")
    fig.tight_layout()
    fig.savefig(OUT / "fig_per_setting.pdf")
    plt.close(fig)


def main():
    H = pd.read_csv(OUT / "hypotheses.csv")
    cells = pd.read_csv(OUT / "cells.csv")
    R = pd.read_csv(OUT / "robustness.csv")
    forest(H)
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.6), sharey=True)
    tpr_vs_e(cells, "mb", 0.01, axes[0], "MonitoringBench (2nd stage gpt-4.1-mini)", ["luna", "jev", "nano"])
    tpr_vs_e(cells, "akshn_full_pooled", 0.01, axes[1], "aksh-n full eval, 6 settings (Gemini)", ["luna", "jev"])
    tpr_vs_e(cells, "akshn_nano_pooled", 0.01, axes[2], "aksh-n nano subset, 6 settings (Gemini)",
             ["luna", "jev", "nano"])
    axes[0].legend(frameon=False, fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / "fig_tpr_vs_e_alpha1.pdf")
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.6), sharey=True)
    tpr_vs_e(cells, "full:akshn_basharena_opus46", 0.01, axes[0], "BashArena-opus-4-6: truncation (H5d)",
             ["luna", "luna_full", "jev", "jev_full"], ref_only=("luna", "luna_full"))
    tpr_vs_e(cells, "nano:akshn_linuxarena", 0.01, axes[1], "LinuxArena nano subset",
             ["luna", "luna_full", "jev", "jev_full"], ref_only=("luna", "luna_full"))
    axes[0].legend(frameon=False, fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / "fig_h5d_truncation.pdf")
    plt.close(fig)
    per_setting(R)


if __name__ == "__main__":
    main()
