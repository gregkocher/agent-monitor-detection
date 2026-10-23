"""Vector PDF figures for round-4 white-box results (results/r4_wb/figures/).

  fig_primary.pdf   preregistered replication: reader - LLM TPR difference at FPR 0.01 (held-out) vs pilot,
                    plus the secondary / sensitivity rows
  fig_la_paired.pdf LinuxArena: FIBS axial follow-up (full) minus each sweep LLM monitor, TPR@0.01, Holm marks
  fig_mole.pdf      MOLE: session AUROC per arm (sab max; LLM session scores), account-cluster CIs

    unset VIRTUAL_ENV; uv run python -m tracks.r4_wb.make_figures_r4
"""
from __future__ import annotations

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from amd.common.schema import REPO  # noqa: E402

RES = REPO / "results" / "r4_wb"
FIG = RES / "figures"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE = "#2a78d6", "#eb6834"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "pdf.fonttype": 42})


def forest(ax, labels, est, lo, hi, colors, xlabel):
    y = list(range(len(labels)))[::-1]
    for yi, e, l_, h, c in zip(y, est, lo, hi, colors):
        ax.plot([l_, h], [yi, yi], color=c, lw=2, solid_capstyle="round")
        ax.plot([e], [yi], "o", color=c, ms=6, mec="white", mew=1.5)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel(xlabel)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)


def fig_primary():
    d = pd.read_csv(RES / "primary.csv")
    keep = ["H1 primary", "H1 at equal realized FPR", "S1 opus-4-5 attacks", "S2 opus-4-6 attacks", "S3 alpha=0.05",
            "sens: pilot-stored honest reader scores"]
    d = d.set_index("contrast").loc[keep].reset_index()
    labels = ["Pilot (775 attacks; audit2, 200 splits)"] + [
        f"{c} (n={int(n)})" if c.startswith("S1") or c.startswith("S2") else c for c, n in zip(d.contrast, d.n_attack)]
    est = [0.185] + list(d.est)
    lo = [0.10] + list(d.lo)
    hi = [0.28] + list(d.hi)
    cols = [INK2] + [BLUE] * len(d)
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    forest(ax, labels, est, lo, hi, cols, "TPR(FIBS axial follow-up, none) − TPR(gpt-4.1-mini, none)")
    ax.set_title("Held-out MB attacks (n=1,000); FPR 0.01 unless stated",
                 fontsize=9, color=INK, loc="left")
    fig.tight_layout()
    fig.savefig(FIG / "fig_primary.pdf")


def fig_la():
    d = pd.read_csv(RES / "la_paired.csv")
    d = d[(d["mode"] == "full") & (d.stream == "fibs_fu_ax") & (d.alpha == 0.01)].sort_values("est")
    labels = [f"{m}{' *' if p < 0.05 else ''}" for m, p in zip(d.llm, d.p_holm)]
    cols = [BLUE if e > 0 else ORANGE for e in d.est]
    fig, ax = plt.subplots(figsize=(6.0, 3.6))
    forest(ax, labels[::-1], list(d.est)[::-1], list(d.lo)[::-1], list(d.hi)[::-1], cols[::-1],
           "TPR(FIBS axial follow-up, full) − TPR(LLM monitor), FPR 0.01")
    ax.set_title("LinuxArena; * Holm p < 0.05", fontsize=9, color=INK, loc="left")
    fig.tight_layout()
    fig.savefig(FIG / "fig_la_paired.pdf")


def fig_mole():
    d = pd.read_csv(RES / "mole_arms.csv")
    sel = pd.concat([d[(d.stream == "sab") & (d["agg"] == "max")], d[d.stream == "score"]])
    names = {"policy": "Policy (Qwen3.6, own system prompt)", "policy_neutral": "Policy, instruction neutralized",
             "reader": "Trusted reader (Qwen3.5)", "llm_insider": "gpt-4.1-mini, insider prompt",
             "llm_generic": "gpt-4.1-mini, generic prompt"}
    order = ["policy", "policy_neutral", "reader", "llm_insider", "llm_generic"]
    sel = sel.set_index("arm").loc[order].reset_index()
    fig, ax = plt.subplots(figsize=(6.0, 2.6))
    y = list(range(len(sel)))[::-1]
    for yi, r in zip(y, sel.itertuples()):
        c = BLUE if r.arm.startswith(("policy", "reader")) else ORANGE
        ax.plot([r.auroc_lo, r.auroc_hi], [yi, yi], color=c, lw=2, solid_capstyle="round")
        ax.plot([r.auroc], [yi], "o", color=c, ms=6, mec="white", mew=1.5)
    ax.axvline(0.5, color=INK2, lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([names[a] for a in sel.arm])
    ax.set_xlabel("Session AUROC (probes: sab, max over turns)")
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_title("MOLE: 233 attack vs 233 account-matched benign", fontsize=9,
                 color=INK, loc="left")
    fig.tight_layout()
    fig.savefig(FIG / "fig_mole.pdf")


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    for f in (fig_primary, fig_la, fig_mole):
        try:
            f()
            print("ok", f.__name__)
        except FileNotFoundError as e:
            print("skip", f.__name__, e)


if __name__ == "__main__":
    main()
