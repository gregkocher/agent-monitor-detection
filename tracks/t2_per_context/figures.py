"""T2 figures from the result CSVs (vector PDF). Run after r1_allocation / r2_poisoning / r2_boiling.

    unset VIRTUAL_ENV; uv run python tracks/t2_per_context/figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import plotstyle as S  # noqa: E402

S.setup()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "results" / "t2"
FIG = OUT / "figures"
MAIN_RULES = ["global", "cfar", "mondrian", "pooled_eb", "pooled_cv", "maxdet", "stackelberg",
              "stackelberg_dw"]
PANEL_LABEL = {
    "la_env_local": "LinuxArena env\n(Gemini local)", "la_env_cum": "LinuxArena env\n(Gemini cumulative)",
    "la_taskcat_local": "LinuxArena task type", "la_model_local": "LinuxArena agent model",
    "akshn_setting": "7 settings\n(Gemini local)", "ca_setting_model": "ControlArena\nsetting x agent",
    "mb_gpt-4.1-nano_trajectory": "BashArena clusters\n(gpt-4.1-nano)",
    "mb_gpt-4.1-mini_trajectory": "BashArena clusters\n(gpt-4.1-mini)",
    "mb_gpt-4.1-mini_full": "BashArena clusters\n(mini per-step, full)",
}


def alloc_dots(summ, B, metrics, path, panels, mode_pair=("nominal", "matched")):
    s = summ[(summ.ncal == -1) & (summ.B == B)]
    fig, axes = plt.subplots(len(panels), len(metrics), figsize=(2.3 * len(metrics) + 1.2, 1.25 * len(panels) + 0.6),
                             sharey=True, squeeze=False)
    for i, pn in enumerate(panels):
        for j, (m, mlab) in enumerate(metrics):
            ax = axes[i, j]
            for k, r in enumerate(MAIN_RULES):
                for mode, off, fill in ((mode_pair[0], -0.17, True), (mode_pair[1], 0.17, False)):
                    row = s[(s.panel == pn) & (s.rule == r) & (s["mode"] == mode)]
                    if row.empty:
                        continue
                    row = row.iloc[0]
                    y = k + off
                    lo, hi = row.get(m + "_lo", np.nan), row.get(m + "_hi", np.nan)
                    sc = 100 if m == "spend" else 1
                    ax.plot([lo * sc, hi * sc], [y, y], color=S.RULE_COLOR[r], lw=1, alpha=0.8)
                    ax.plot(row[m] * sc, y, "o", ms=3.8, color=S.RULE_COLOR[r],
                            mfc=S.RULE_COLOR[r] if fill else "white", mew=1)
            if m == "spend":
                ax.axvline(B * 100, color=S.INK2, lw=0.8, ls="--")
            gl = s[(s.panel == pn) & (s.rule == "global") & (s["mode"] == mode_pair[1])]
            if m != "spend" and not gl.empty:
                ax.axvline(gl.iloc[0][m], color=S.RULE_COLOR["global"], lw=0.6, ls=":")
            ax.set_yticks(range(len(MAIN_RULES)))
            ax.set_yticklabels([S.RULE_LABEL[r] for r in MAIN_RULES], fontsize=6.3)
            ax.invert_yaxis() if j == 0 and i == 0 else None
            ax.grid(axis="y", visible=False)
            if i == 0:
                ax.set_title(mlab)
            if j == len(metrics) - 1:
                ax.text(1.03, 0.5, PANEL_LABEL.get(pn, pn), transform=ax.transAxes, rotation=0,
                        va="center", fontsize=6.8)
    handles = [Line2D([], [], marker="o", ls="", color=S.INK2, label=f"{mode_pair[0]} budget"),
               Line2D([], [], marker="o", ls="", color=S.INK2, mfc="white", label="spend-matched (test spend = B)")]
    fig.legend(handles=handles, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    S.save(fig, path)


def small_sample(summ, path):
    s = summ[summ["mode"] == "nominal"]
    panels = [p for p in ["la_env_local", "akshn_setting", "ca_setting_model", "la_taskcat_local"]
              if p in set(s.panel)]
    rules = ["global", "cfar", "mondrian", "pooled_eb", "pooled_cv"]
    mets = [("spend", "realized spend / B"), ("fpr_sd", "SD of per-context FPR / B"),
            ("tpr_uniform", "TPR (uniform attacker)"), ("sel_informed", "safety vs attack selection")]
    B = 0.01
    fig, axes = plt.subplots(len(panels), len(mets), figsize=(9.2, 1.75 * len(panels) + 0.5), squeeze=False)
    for i, pn in enumerate(panels):
        d = s[(s.panel == pn) & (s.B == B)]
        nfull = None
        for j, (m, lab) in enumerate(mets):
            ax = axes[i, j]
            for r in rules:
                x, y, lo, hi = [], [], [], []
                for nc in (10, 30, 100, -1):
                    row = d[(d.rule == r) & (d.ncal == nc)]
                    if row.empty:
                        continue
                    sc = 1 / B if m in ("spend", "fpr_sd") else 1
                    x.append(nc if nc > 0 else 300)
                    y.append(row.iloc[0][m] * sc)
                    lo.append(row.iloc[0][m + "_lo"] * sc)
                    hi.append(row.iloc[0][m + "_hi"] * sc)
                ax.plot(x, y, "-o", color=S.RULE_COLOR[r], ms=3, label=S.RULE_LABEL[r])
                ax.fill_between(x, lo, hi, color=S.RULE_COLOR[r], alpha=0.10, lw=0)
            ax.set_xscale("log")
            ax.set_xticks([10, 30, 100, 300])
            ax.set_xticklabels(["10", "30", "100", "all"])
            if m == "spend":
                ax.axhline(1, color=S.INK2, lw=0.8, ls="--")
            if i == 0:
                ax.set_title(lab)
            if i == len(panels) - 1:
                ax.set_xlabel("honest calibration runs per context")
            if j == 0:
                ax.set_ylabel(PANEL_LABEL.get(pn, pn).replace("\n", " "), fontsize=7)
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.02), fontsize=7)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    S.save(fig, path)


def poisoning(path, poison="attack_max"):
    f = OUT / "poisoning_summary.csv"
    if not f.exists():
        return
    s = pd.read_csv(f)
    s = s[s.poison == poison]
    panels = [p for p in ["la_env_local", "akshn_setting", "ca_setting_model", "la_taskcat_local",
                          "mb_gpt-4.1-nano_trajectory", "mb_gpt-4.1-mini_trajectory"] if p in set(s.panel)]
    rules = ["global", "cfar", "pooled_eb", "os_shift", "tm_scale", "refmix", "frozen", "cap"]
    fig, axes = plt.subplots(2, (len(panels) + 1) // 2, figsize=(2.7 * ((len(panels) + 1) // 2), 4.6), squeeze=False)
    for ax, pn in zip(axes.flat, panels):
        d = s[s.panel == pn]
        for r in rules:
            q = d[d.rule == r].sort_values("eps")
            x = np.maximum(q.eps.values * 100, 0.2)
            ax.plot(x, q.tpr_t, "-o", ms=2.8, color=S.DEF_COLOR[r], label=S.DEF_LABEL[r])
            ax.fill_between(x, q.tpr_t_lo, q.tpr_t_hi, color=S.DEF_COLOR[r], alpha=0.10, lw=0)
        ax.axvline(1, color=S.INK2, lw=0.7, ls="--")
        ax.set_xscale("log")
        ax.set_xticks([0.2, 1, 5, 30])
        ax.set_xticklabels(["0", "1", "5", "30"])
        ax.set_title(PANEL_LABEL.get(pn, pn).replace("\n", " "), fontsize=8)
        ax.set_xlabel("poisoned share of target's calibration (%)")
        ax.set_ylabel("TPR in poisoned context")
        ax.set_ylim(-0.02, 1.02)
    for ax in list(axes.flat)[len(panels):]:
        ax.axis("off")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.04), fontsize=7)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    S.save(fig, path)


def boiling(path):
    f = OUT / "boiling_frog_rounds.csv"
    if not f.exists():
        return
    s = pd.read_csv(f)
    col = {"cfar": S.DEF_COLOR["cfar"], "cfar_filter": S.SERIES[4], "cfar_cumcap": S.DEF_COLOR["cap"],
           "refmix": S.DEF_COLOR["refmix"], "global": S.DEF_COLOR["global"], "os_shift": S.DEF_COLOR["os_shift"]}
    lab = {"cfar": "CFAR, no filter", "cfar_filter": "CFAR + outlier filter",
           "cfar_cumcap": "CFAR + filter + cumulative cap", "refmix": "50/50 frozen-reference mix + filter",
           "global": "Global + filter", "os_shift": "OS-CFAR (LOCO tail) + filter"}
    panels = sorted(s.panel.unique())
    fig, axes = plt.subplots(len(panels), 3, figsize=(9.0, 2.3 * len(panels) + 0.4), squeeze=False)
    for i, pn in enumerate(panels):
        for j, (scen, eps, met, ylab) in enumerate([("poison", 0.05, "tpr_t", "TPR in target (eps = 5%)"),
                                                     ("poison", 0.02, "tpr_t", "TPR in target (eps = 2%)"),
                                                     ("drift", 0.0, "fpr_t", "FPR in target (genuine drift)")]):
            ax = axes[i, j]
            d = s[(s.panel == pn) & (s.scenario == scen) & (np.isclose(s.eps, eps))]
            for r, c in col.items():
                q = d[d.rule == r].sort_values("round")
                ax.plot(q["round"], q[met], color=c, lw=1.4, label=lab[r])
            if scen == "drift":
                ax.axhline(0.01, color=S.INK2, lw=0.7, ls="--")
                ax.axvline(10, color=S.INK2, lw=0.6, ls=":")
            ax.set_xlabel("recalibration round")
            ax.set_ylabel(ylab, fontsize=7)
            if j == 0:
                ax.set_title(PANEL_LABEL.get(pn, pn).replace("\n", " "), fontsize=8, loc="left")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.03), fontsize=7)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    S.save(fig, path)


def main():
    f = sorted(OUT.glob("allocation_summary_full_*.csv"))
    if f:
        summ = pd.concat([pd.read_csv(x) for x in f], ignore_index=True)
        main_p = [p for p in PANEL_LABEL if p in set(summ.panel)]
        for B in (0.005, 0.01, 0.02, 0.05):
            alloc_dots(summ, B, [("spend", "realized audit spend (%)"), ("tpr_uniform", "TPR, uniform attacker"),
                                 ("sel_informed", "safety vs attack selection"),
                                 ("dmg_informed", "safety, damage-weighted selection")],
                       FIG / f"r1_allocation_B{B * 100:g}pct.pdf", main_p)
        small_sample(summ, FIG / "r1_small_sample.pdf")
    poisoning(FIG / "r2_poisoning_attack_max.pdf", "attack_max")
    poisoning(FIG / "r2_poisoning_honest_max.pdf", "honest_max")
    boiling(FIG / "r2_boiling_frog.pdf")


if __name__ == "__main__":
    main()
