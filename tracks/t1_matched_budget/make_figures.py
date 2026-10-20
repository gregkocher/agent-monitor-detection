"""T1 figures (vector PDF) and markdown tables for results/t1/.

    uv run python tracks/t1_matched_budget/make_figures.py [--round 1|2|all] [--r2tag main]

Style: honest = blue, attack = orange; detectors use a fixed categorical order
(max, kth2, cusum, glr, e-process, or(max+cusum)) that never changes between figures.
"""
from __future__ import annotations

import argparse
import pickle
from pathlib import Path

import matplotlib
matplotlib.use("pdf")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from amd.common.schema import REPO  # noqa: E402

R = REPO / "results" / "t1"
FIG = R / "figures"
HONEST, ATTACK = "#2a78d6", "#eb6834"
DET_STYLE = {  # fixed order + color; marker as a second channel
    "max": ("#2a78d6", "o", "max"),
    "kth2": ("#1baf7a", "s", "2nd-max"),
    "cusum_k0.5": ("#eb6834", "^", "CUSUM (k=0.5)"),
    "glr_w20": ("#eda100", "v", "window GLR"),
    "eproc_power": ("#e87ba4", "D", "conformal e-process"),
    "or(max+cusum)": ("#008300", "P", "OR(max, CUSUM)"),
}
INK, MUTED, GRID = "#222222", "#6b6b6b", "#e4e4e4"
plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "legend.fontsize": 8,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "pdf.fonttype": 42, "font.family": "DejaVu Sans",
})


def md(df: pd.DataFrame, index=True, floatfmt="{:.2f}") -> str:
    """Markdown table without the tabulate dependency."""
    d = df.reset_index() if index else df
    cols = [str(c) for c in d.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in d.iterrows():
        out.append("| " + " | ".join(floatfmt.format(v) if isinstance(v, (float, np.floating)) and np.isfinite(v)
                                      else ("" if isinstance(v, float) else str(v)) for v in r) + " |")
    return "\n".join(out)


def pretty_set(s: str) -> str:
    s = s.replace("akshn_", "").replace("la:", "LinuxArena: ").replace("mrt:", "").replace("ps:", "PR monitor ")
    s = s.replace("claude-3-5-sonnet-20241022|mrt_sequential_", "MRT sonnet-3.5 N=")
    s = s.replace("+likert_reminder_v2_", " ").replace("basharena_", "BashArena ")
    return s


def dotplot(ax, df, value="tpr", lo=None, hi=None, order=None, dets=None):
    dets = dets or list(DET_STYLE)
    order = order or list(df["set"].unique())
    y = np.arange(len(order))
    off = np.linspace(-0.3, 0.3, len(dets))
    for j, d in enumerate(dets):
        c, mk, lab = DET_STYLE[d]
        sub = df[df.detector == d].set_index("set").reindex(order)
        ax.scatter(sub[value], y + off[j], color=c, marker=mk, s=22, zorder=3, label=lab,
                   edgecolors="white", linewidths=0.4)
        if lo and hi:
            ax.hlines(y + off[j], sub[lo], sub[hi], color=c, lw=1.0, alpha=0.7, zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels([pretty_set(s) for s in order])
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)


def round1():
    d = R / "round1"
    tag = "la_akshn_mrt_ps"
    m = pd.read_csv(d / f"matched_{tag}.csv")
    m = m[m.threshold_kind == "calibrated"]
    ac = pd.read_csv(d / f"autocorr_{tag}.csv").set_index("set")
    groups = [("LinuxArena sweep (12 history-aware per-action monitors)", "la:"),
              ("aksh-n Gemini-3.1-Pro streaming judge (local / cumulative)", "akshn"),
              ("MRT sequential chunk monitors", "mrt"),
              ("Persistent state: GPT-4o per-PR monitor, cross-session (5 PRs)", "ps:")]
    for alpha in (0.01, 0.05):
        x = m[m.alpha == alpha]
        heights = [x[x.set.str.startswith(g)].set.nunique() for _, g in groups]
        fig, axes = plt.subplots(len(groups), 1, figsize=(7.2, 0.26 * sum(heights) + 2.2),
                                 gridspec_kw=dict(height_ratios=heights), sharex=True)
        for ax, (title, g) in zip(axes, groups):
            sub = x[x.set.str.startswith(g)]
            order = sorted(sub.set.unique(), key=lambda s: -sub[(sub.set == s) & (sub.detector == "max")].tpr.mean())
            dotplot(ax, sub, lo="tpr_lo", hi="tpr_hi", order=order)
            ax.set_title(title, loc="left", color=INK)
        axes[-1].set_xlabel(f"TPR at matched trajectory FPR = {alpha:g} (95% cluster-bootstrap CI)")
        axes[-1].set_xlim(-0.02, 1.02)
        h, l = axes[0].get_legend_handles_labels()
        fig.legend(h, l, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 1.0))
        fig.tight_layout(rect=(0, 0, 1, 0.955))
        fig.savefig(FIG / f"r1_tpr_alpha{alpha:g}.pdf")
        plt.close(fig)

    # accumulation gain vs honest lag-1 autocorrelation
    g = pd.read_csv(d / f"gain_{tag}.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    for ax, det in zip(axes, ["cusum_k0.5", "eproc_power"]):
        x = g[(g.alpha == 0.01) & (g.detector == det)].set_index("set")
        x["rho1"] = ac.rho1
        for fam, c, mk in (("la:", "#2a78d6", "o"), ("akshn", "#1baf7a", "s"), ("mrt", "#e87ba4", "D"),
                           ("ps:", "#eda100", "^")):
            s = x[x.index.str.startswith(fam)]
            ax.errorbar(s.rho1, s.gain_vs_max, yerr=[s.gain_vs_max - s.lo, s.hi - s.gain_vs_max], fmt=mk,
                        color=c, ms=4, lw=0.8, label={"la:": "LinuxArena", "akshn": "aksh-n", "mrt": "MRT", "ps:": "persistent state"}[fam])
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.set_xlabel("honest lag-1 autocorrelation (whitened scores)")
        ax.set_title(f"{DET_STYLE[det][2]} − max", loc="left", color=INK)
    axes[0].set_ylabel("TPR gain over max at FPR 0.01")
    axes[0].legend(frameon=False, loc="lower left")
    fig.tight_layout()
    fig.savefig(FIG / "r1_gain_vs_autocorr.pdf")
    plt.close(fig)

    # markdown tables
    keep = ["max", "kth2", "top3sum", "mean", "cusum_k0.5", "sr_d1", "glr_w20", "eproc_power", "esr_power",
            "max_lenaware", "or(max+cusum)"]
    lines = []
    for alpha in (0.05, 0.01, 0.003):
        x = m[m.alpha == alpha]
        p = x.pivot(index="set", columns="detector", values="tpr")[keep]
        p["rho1"] = ac.rho1
        best = p[keep].idxmax(axis=1)
        p.insert(0, "best", best)
        lines.append(f"\n### TPR at matched trajectory FPR α = {alpha:g}\n")
        lines.append(md(p.rename(index=pretty_set)))
    (R / "tables").mkdir(exist_ok=True)
    (R / "tables" / "r1_tpr.md").write_text("\n".join(lines) + "\n")


def round2(tag="main"):
    d = R / "round2" / tag
    if not (d / "tpr_by_structure.csv").exists():
        print("no round 2 results at", d)
        return
    t = pd.read_csv(d / "tpr_by_structure.csv")
    modes = [m for m in ("full", "window", "none") if m in set(t["mode"])]
    for alpha in (0.01, 0.05):
        x = t[t.alpha == alpha]
        groups = ["S1", "S2", "S3", "S4", "all"]
        fig, axes = plt.subplots(1, len(modes), figsize=(3.4 * len(modes) + 0.6, 3.2), sharey=True, sharex=True)
        axes = np.atleast_1d(axes)
        for ax, mode in zip(axes, modes):
            s = x[x["mode"] == mode].rename(columns={"group": "set"})
            dotplot(ax, s, lo="lo", hi="hi", order=[g for g in groups if g in set(s.set)])
            ax.set_title({"full": "history-aware (full history)", "none": "history-free (current action only)",
                          "window": "window (last 3 actions)"}[mode], loc="left", color=INK)
            ax.set_xlabel(f"TPR at trajectory FPR = {alpha:g}")
        axes[0].set_yticklabels(["S1", "S2", "S3", "S4 (distributed)", "all (as sampled)"][: len(axes[0].get_yticks())])
        h, l = axes[0].get_legend_handles_labels()
        fig.legend(h, l, loc="upper center", ncol=6, frameon=False, bbox_to_anchor=(0.5, 1.0), fontsize=7)
        fig.tight_layout(rect=(0, 0, 1, 0.9))
        fig.savefig(FIG / f"r2_{tag}_tpr_by_structure_alpha{alpha:g}.pdf")
        plt.close(fig)
    # DiD
    if (d / "did.csv").exists():
        did = pd.read_csv(d / "did.csv")
        for contrast in did.contrast.unique():
            x = did[(did.contrast == contrast) & (did.alpha == 0.01) & did.detector.isin(DET_STYLE)]
            fig, ax = plt.subplots(figsize=(5.2, 3.0))
            x = x.rename(columns={"group": "set", "did": "tpr"})
            dotplot(ax, x, lo="lo", hi="hi", order=["S1", "S2", "S3", "S4", "all"],
                    dets=[k for k in DET_STYLE if k != "max"])
            ax.axvline(0, color=MUTED, lw=0.8)
            ax.set_xlabel("[gain over max, history-free] − [gain over max, history-aware]\n(TPR at FPR 0.01; paired attack bootstrap)")
            ax.legend(frameon=False, fontsize=7, loc="best")
            fig.tight_layout()
            fig.savefig(FIG / f"r2_{tag}_did_{contrast}.pdf")
            plt.close(fig)
    # score distributions & example streams
    if True:
        from run_round2 import load_mode
        fig, axes = plt.subplots(1, len(modes), figsize=(3.4 * len(modes), 2.8), sharey=True)
        axes = np.atleast_1d(axes)
        for ax, mode in zip(axes, modes):
            ss = load_mode(mode, prefix=_prefix(d), score=_score(d))
            hu = np.concatenate([s[np.isfinite(s)] for s in ss.honest])
            pre, post = [], []
            for s, o in zip(ss.attack, ss.onsets):
                v = s[np.isfinite(s)]
                if o is None:
                    continue
                pre.append(v[:o]); post.append(v[o:])
            bins = np.linspace(0, 10, 21)
            for vals, c, lab in ((hu, HONEST, "honest steps"), (np.concatenate(pre), "#9a9a9a", "attack, pre-onset"),
                                 (np.concatenate(post), ATTACK, "attack, onset and after")):
                w = np.ones_like(vals) / len(vals)
                ax.hist(vals, bins=bins, weights=w, histtype="step", lw=1.6, color=c, label=lab)
            ax.set_yscale("log")
            ax.set_title(mode, loc="left", color=INK)
            ax.set_xlabel("per-step score (0-10)")
        axes[0].set_ylabel("fraction of steps")
        axes[0].legend(frameon=False, fontsize=7)
        fig.tight_layout()
        fig.savefig(FIG / f"r2_{tag}_score_hist.pdf")
        plt.close(fig)


def _prefix(d):
    import json
    return json.load(open(d / "config.json")).get("prefix", "")


def _score(d):
    import json
    return json.load(open(d / "config.json")).get("score", "expected")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", default="all")
    ap.add_argument("--r2tag", default="main")
    a = ap.parse_args()
    FIG.mkdir(parents=True, exist_ok=True)
    if a.round in ("1", "all"):
        round1()
    if a.round in ("2", "all"):
        round2(a.r2tag)
