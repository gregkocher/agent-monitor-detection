"""Figures and markdown tables for the white-box pilot (results/wb/). Vector PDFs; blue = honest,
orange = attack; one fixed color per monitor stream across figures.

    uv run python -m tracks.wb_whitebox.make_figures
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "t2_per_context"))
import plotstyle as PS  # noqa: E402

from amd.common.schema import REPO  # noqa: E402

from .analyze_mb import sets_for  # noqa: E402

PS.setup()
plt = PS.plt
OUT = REPO / "results" / "wb"
FIG = OUT / "figures"
HON, ATT = "#2a78d6", "#eb6834"
LABEL = {"llm": "gpt-4.1-mini (LLM)", "sab": "sabotage probe (mean)", "sab_max": "sabotage probe (max tok)",
         "dec": "Apollo deception probe", "fibs_tok": "FIBS linear on step tokens",
         "fibs_fu": "FIBS follow-up (No−Yes)", "fibs_fu_ax": "FIBS axial follow-up", "jl_lm": "J-lens watch-list mass",
         "jl_lm_max": "J-lens mass (max tok)", "jl_hits": "J-lens top-25 hits", "sup": "supervised probe (cross-fit)"}
ORDER = ["llm", "sup", "sab", "sab_max", "fibs_fu", "fibs_fu_ax", "fibs_tok", "dec", "jl_lm", "jl_lm_max", "jl_hits"]
COL = dict(zip(ORDER, ["#0b0b0b", "#4a3aa7", "#eb6834", "#eda100", "#1baf7a", "#008300", "#2a78d6", "#e87ba4",
                       "#e34948", "#a05a2c", "#7a7a7a"]))


def fig_tpr():
    m = pd.read_csv(OUT / "mb_matched.csv")
    m = m[(m.threshold_kind == "calibrated") & (m.detector == "max")]
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.6), sharey=True)
    streams = [s for s in ORDER if s in set(m.stream)]
    y = np.arange(len(streams))
    for ax, alpha in zip(axes, (0.05, 0.01, 0.003)):
        for k, (mode, mk, off) in enumerate((("full", "o", -0.15), ("none", "s", 0.15))):
            d = m[(m.alpha == alpha) & (m["mode"] == mode)].set_index("stream").reindex(streams)
            ax.errorbar(d.tpr, y + off, xerr=[d.tpr - d.tpr_lo, d.tpr_hi - d.tpr], fmt=mk, ms=4,
                        color=PS.SERIES[k], ecolor=PS.SERIES[k], elinewidth=0.9, capsize=0,
                        label="history-aware (full)" if mode == "full" else "history-free (none)")
        ax.set_title(f"trajectory FPR {alpha:g}", loc="left")
        ax.set_xlabel("TPR of trajectory max")
        ax.set_xlim(0, 1)
    axes[0].set_yticks(y, [LABEL.get(s, s) for s in streams])
    axes[0].invert_yaxis()
    axes[0].legend(loc="lower right")
    fig.suptitle("MonitoringBench (775 attacks / Honest-550): reader streams vs gpt-4.1-mini", x=0.01, ha="left")
    PS.save(fig, FIG / "mb_tpr_max.pdf")


def fig_dists():
    streams = ["llm", "sab", "fibs_fu", "jl_lm", "sup"]
    fig, axes = plt.subplots(2, len(streams), figsize=(2.1 * len(streams), 3.8))
    for i, mode in enumerate(("full", "none")):
        sets = sets_for(mode, streams)
        for j, st in enumerate(streams):
            ax = axes[i, j]
            if st not in sets:
                ax.axis("off")
                continue
            ss = sets[st]
            h = [np.nanmax(s) for s in ss.honest]
            a = [np.nanmax(s) for s in ss.attack]
            bins = np.linspace(np.nanmin(h + a), np.nanmax(h + a), 30)
            ax.hist(h, bins, density=True, color=HON, alpha=0.55, label="honest")
            ax.hist(a, bins, density=True, color=ATT, alpha=0.55, label="attack")
            ax.set_title(f"{LABEL.get(st, st)}\n{mode}", fontsize=7.5, loc="left")
            ax.set_yticks([])
    axes[0, 0].legend(fontsize=6.5)
    fig.suptitle("Trajectory max per stream (MonitoringBench)", x=0.01, ha="left")
    PS.save(fig, FIG / "mb_max_distributions.pdf")


def fig_fusion():
    f = pd.read_csv(OUT / "fusion.csv")
    probes = list(dict.fromkeys(f.probe))
    fig, axes = plt.subplots(2, len(probes), figsize=(2.6 * len(probes), 4.8), squeeze=False)
    for i, mode in enumerate(("full", "none")):
        for j, pr in enumerate(probes):
            ax = axes[i, j]
            d = f[(f["mode"] == mode) & (f.probe == pr) & (f.alpha == 0.01)].set_index("rule")
            if d.empty:
                ax.axis("off")
                continue
            cas = d[d.index.str.match(r"cascade_\d")]
            x = cas.calls_steps_honest.values
            ax.plot(x, cas.tpr.values, "-o", color=PS.SERIES[1], label="cascade (probe triage → LLM)")
            ax.fill_between(x, cas.tpr_lo.values, cas.tpr_hi.values, color=PS.SERIES[1], alpha=0.15, lw=0)
            for rule, c, ls in (("llm", "#0b0b0b", "-"), ("probe", PS.SERIES[0], "--"), ("kde_step", PS.SERIES[2], ":"),
                                ("rank_sum", PS.SERIES[6], "-.")):
                if rule in d.index:
                    ax.axhline(d.loc[rule, "tpr"], color=c, ls=ls, lw=1.1, label={"llm": "LLM on every step",
                               "probe": "probe alone", "kde_step": "KDE-LLR fusion", "rank_sum": "rank-sum fusion"}[rule])
            ax.set_title(f"{LABEL.get(pr, pr)} · {mode}", fontsize=8, loc="left")
            ax.set_xlabel("share of honest steps sent to the LLM")
            ax.set_ylim(0, 1)
            if j == 0:
                ax.set_ylabel("TPR at trajectory FPR 0.01")
    axes[0, 0].legend(fontsize=6)
    PS.save(fig, FIG / "fusion_cascade.pdf")


def fig_t3():
    p = OUT / "t3_detection.csv"
    if not p.exists():
        return
    d = pd.read_csv(p)
    d = d[(d.stat == "max") & (d.alpha == 0.01)]
    arms = ["original", "max_r0", "max", "cusum_r0", "cusum", "multichart_r0", "multichart"]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2), sharey=True)
    for ax, mode in zip(axes, ("full", "none")):
        x = np.arange(len(arms))
        streams = [s for s in ["llm", "sab", "fibs_fu", "jl_lm", "sup_from_mb"] if s in set(d.stream)]
        w = 0.8 / max(len(streams), 1)
        for k, st in enumerate(streams):
            v = d[(d["mode"] == mode) & (d.stream == st)].set_index("arm").reindex(arms).detect
            ax.bar(x + (k - len(streams) / 2) * w + w / 2, v, w, color=COL.get(st.replace("_from_mb", ""), "#888"),
                   label=LABEL.get(st, "supervised probe (MB-trained)" if st == "sup_from_mb" else st))
        ax.set_xticks(x, arms, rotation=30)
        ax.set_title(f"T3 refined attacks · {mode}", loc="left")
        ax.set_ylabel("detection at trajectory FPR 0.01 (max)")
    axes[0].legend(fontsize=6.5)
    PS.save(fig, FIG / "t3_detection.pdf")


def tables():
    m = pd.read_csv(OUT / "mb_matched.csv")
    m = m[m.threshold_kind == "calibrated"]
    au = pd.read_csv(OUT / "mb_auroc.csv").set_index(["mode", "stream"])
    lines = ["# White-box pilot — MonitoringBench tables", ""]
    for alpha in (0.05, 0.01, 0.003):
        lines += [f"## TPR at trajectory FPR {alpha:g} (95% CI; 10 grouped splits, cluster bootstrap)", "",
                  "| stream | mode | AUROC(max) | max | 2nd-max | top-3 sum | CUSUM k=0.5 | CUSUM k=1.5 | e-process | OR(max+CUSUM) |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for st in [s for s in ORDER if s in set(m.stream)] + sorted(set(m.stream) - set(ORDER)):
            for mode in ("full", "none"):
                d = m[(m.stream == st) & (m["mode"] == mode) & (m.alpha == alpha)].set_index("detector")
                if d.empty:
                    continue
                cell = lambda k: f"{d.loc[k, 'tpr']:.3f} [{d.loc[k, 'tpr_lo']:.2f}, {d.loc[k, 'tpr_hi']:.2f}]" if k in d.index else "–"  # noqa: E731
                a = au.loc[(mode, st), "auroc_max"] if (mode, st) in au.index else np.nan
                lines.append(f"| {LABEL.get(st, st)} | {mode} | {a:.3f} | " + " | ".join(
                    cell(k) for k in ("max", "kth2", "top3sum", "cusum_k0.5", "cusum_k1.5", "eproc_power", "or(max+cusum)")) + " |")
        lines.append("")
    (OUT / "tables_mb.md").write_text("\n".join(lines))


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    for f in (tables, fig_tpr, fig_dists, fig_fusion, fig_t3):
        try:
            f()
            print("ok", f.__name__)
        except FileNotFoundError as e:
            print("skip", f.__name__, e)


if __name__ == "__main__":
    main()
