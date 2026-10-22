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
MODE_COL = {"full": "#1baf7a", "none": "#4a3aa7"}  # history modes (blue/orange are reserved for honest/attack)
LABEL = {"llm": "gpt-4.1-mini (LLM)", "sab": "sabotage probe (mean)", "sab_max": "sabotage probe (max tok)",
         "dec": "Apollo deception probe", "fibs_tok": "FIBS linear on step tokens",
         "fibs_fu": "FIBS follow-up (No−Yes)", "fibs_fu_ax": "FIBS axial follow-up", "jl_lm": "J-lens watch-list mass",
         "jl_lm_max": "J-lens mass (max tok)", "jl_hits": "J-lens top-25 hits", "sup": "supervised probe (cross-fit)",
         "sab_L43": "sabotage probe L43 (post hoc)"}
ORDER = ["llm", "sup", "sab", "sab_max", "sab_L43", "fibs_fu", "fibs_fu_ax", "fibs_tok", "dec", "jl_lm", "jl_lm_max",
         "jl_hits"]
COL = dict(zip(ORDER, ["#0b0b0b", "#4a3aa7", "#eb6834", "#eda100", "#c4521f", "#1baf7a", "#008300", "#2a78d6",
                       "#e87ba4", "#e34948", "#a05a2c", "#7a7a7a"]))


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
                        color=MODE_COL[mode], ecolor=MODE_COL[mode], elinewidth=0.9, capsize=0,
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
    fig, axes = plt.subplots(2, len(probes), figsize=(2.9 * len(probes), 5.6), squeeze=False)
    for i, mode in enumerate(("full", "none")):
        for j, pr in enumerate(probes):
            ax = axes[i, j]
            d = f[(f["mode"] == mode) & (f.probe == pr) & (f.alpha == 0.01)].set_index("rule")
            if d.empty:
                ax.axis("off")
                continue
            cas = d[d.index.str.match(r"cascade_\d")]
            x = cas.calls_steps_honest.values
            ax.plot(x, cas.tpr.values, "-o", color="#e34948", label="cascade (probe triage → LLM)")
            ax.fill_between(x, cas.tpr_lo.values, cas.tpr_hi.values, color="#e34948", alpha=0.15, lw=0)
            for rule, c, ls in (("llm", "#0b0b0b", "-"), ("probe", "#4a3aa7", "--"), ("kde_step", PS.SERIES[2], ":"),
                                ("rank_sum", "#eda100", "-.")):
                if rule in d.index:
                    ax.axhline(d.loc[rule, "tpr"], color=c, ls=ls, lw=1.1, label={"llm": "LLM on every step",
                               "probe": "probe alone", "kde_step": "KDE-LLR fusion", "rank_sum": "rank-sum fusion"}[rule])
            ax.set_title(f"{LABEL.get(pr, pr)} · {mode}", fontsize=8, loc="left")
            ax.set_xlabel("honest steps sent to LLM")
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
    blocks = [("r1", "full", ["original", "max_r0", "max", "cusum_r0", "cusum", "multichart_r0", "multichart"]),
              ("r1", "none", ["original", "max_r0", "max", "cusum_r0", "cusum", "multichart_r0", "multichart"]),
              ("r2", "none", ["original", "rewrite_control_r2_r0", "pace_max_r2_r0", "pace_max_r2", "pace_cusum_r2_r0",
                              "pace_cusum_r2", "pace_multichart_r2_r0", "pace_multichart_r2"])]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6), sharey=True)
    for ax, (blk, mode, arms) in zip(axes, blocks):
        x = np.arange(len(arms))
        dd = d[(d.block == blk) & (d["mode"] == mode)]
        streams = [s for s in ["gpt-4.1-mini", "gpt-4.1", "sab", "fibs_fu_ax", "fibs_fu", "jl_lm", "sup_from_mb"]
                   if s in set(dd.stream)]
        w = 0.8 / max(len(streams), 1)
        cols = {"gpt-4.1-mini": "#0b0b0b", "gpt-4.1": "#52514e", "sup_from_mb": COL["sup"]}
        for k, st in enumerate(streams):
            v = dd[dd.stream == st].set_index("arm").reindex(arms).detect
            ax.bar(x + (k - len(streams) / 2) * w + w / 2, v, w, color=cols.get(st, COL.get(st, "#888")),
                   label=LABEL.get(st, {"sup_from_mb": "supervised probe (cross-fit / MB-trained)",
                                        "gpt-4.1": "gpt-4.1 (strong LLM)"}.get(st, st)))
        ax.set_xticks(x, [a.replace("_r2", "").replace("rewrite_control", "control") for a in arms], rotation=35,
                      ha="right")
        ax.set_title(f"T3 {'round 1' if blk == 'r1' else 'round 2 (pacing)'} · {mode}", loc="left")
    axes[0].set_ylabel("detection at trajectory FPR 0.01 (max)")
    axes[0].legend(fontsize=6.2, loc="upper left")
    PS.save(fig, FIG / "t3_detection.pdf")


def fig_context():
    h = OUT / "context_heterogeneity.csv"
    a = OUT / "context_allocation.csv"
    if not (h.exists() and a.exists()):
        return
    H = pd.read_csv(h)
    H = H[(H.B == 0.05) & H.panel.str.startswith("mb_wb")]
    H["mode"] = H.panel.str.split("_").str[2]
    H["stream"] = H.panel.str.split("_", n=3).str[3]
    A = pd.read_csv(a)
    A = A[(A["mode"] == "matched") & (A.B == 0.10) & A.panel.str.startswith("mb_wb")]
    A["hmode"] = A.panel.str.split("_").str[2]
    A["stream"] = A.panel.str.split("_", n=3).str[3]
    streams = [s for s in ORDER if s in set(H.stream)]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.4))
    y = np.arange(len(streams))
    for k, mode in enumerate(("full", "none")):
        v = H[H["mode"] == mode].set_index("stream").reindex(streams)
        axes[0].barh(y + (k - 0.5) * 0.38, v.tau, 0.38, color=MODE_COL[mode], label=mode)
    axes[0].set_yticks(y, [LABEL.get(s, s) for s in streams])
    axes[0].invert_yaxis()
    axes[0].set_xlabel("between-cluster spread of honest FPR\n(logit-normal tau, global 5% threshold)")
    axes[0].legend()
    for ax, met, ttl in ((axes[1], "tpr_uniform", "uniform-attacker TPR"), (axes[2], "sel_informed", "selection safety")):
        for k, rule in enumerate(("global", "cfar", "stackelberg")):
            for j, mode in enumerate(("full", "none")):
                v = A[(A.hmode == mode) & (A.rule == rule)].set_index("stream").reindex(streams)[met]
                ax.scatter(v, y + (j - 0.5) * 0.3, color=PS.RULE_COLOR[rule], marker="o" if mode == "full" else "s",
                           s=18, label=f"{PS.RULE_LABEL[rule].split(' (')[0]} · {mode}")
        ax.set_yticks(y, [""] * len(streams))
        ax.invert_yaxis()
        ax.set_xlabel(f"{ttl} at 10% spend (matched)")
    axes[2].legend(fontsize=6, loc="lower right")
    fig.suptitle("Per-context thresholds on MonitoringBench task clusters (7 clusters)", x=0.01, ha="left")
    PS.save(fig, FIG / "context_probe_vs_llm.pdf")


def fig_la():
    p = OUT / "la_auroc.csv"
    if not p.exists():
        return
    d = pd.read_csv(p).sort_values("auroc_max")
    d = d[~d.stream.str.contains("sab_max|jl_hits")]
    fig, ax = plt.subplots(figsize=(6.4, 0.18 * len(d) + 1))
    c = ["#0b0b0b" if s.startswith("llm:") else (MODE_COL["full"] if ":full:" in s else MODE_COL["none"]) for s in d.stream]
    ax.barh(np.arange(len(d)), d.auroc_max, color=c)
    ax.set_yticks(np.arange(len(d)), [s.replace("wb:", "reader ").replace("llm:", "LLM ") for s in d.stream], fontsize=6.5)
    ax.set_xlim(0.4, 1)
    ax.set_xlabel("AUROC of trajectory max (LinuxArena: 200 honest / 142 attack)")
    ax.set_title("LinuxArena: reader streams (green full, purple none) vs 12 sweep LLM monitors (black)", loc="left",
                 fontsize=8)
    PS.save(fig, FIG / "la_auroc.pdf")


def fig_mole():
    p = OUT / "mole_policy_vs_reader.csv"
    if not p.exists():
        return
    d = pd.read_csv(p)
    d = d[d["agg"] == "max"]
    streams = list(dict.fromkeys(d.stream))
    fig, ax = plt.subplots(figsize=(5.6, 3))
    x = np.arange(len(streams))
    for k, arm in enumerate(("policy", "reader")):
        v = d[d.arm == arm].set_index("stream").reindex(streams)
        ax.bar(x + (k - 0.5) * 0.38, v.auroc, 0.38, yerr=[v.auroc - v.auroc_lo, v.auroc_hi - v.auroc],
               color=PS.SERIES[k + 2], label={"policy": "policy (Qwen3.6-27B, own activations)",
                                               "reader": "trusted reader (Qwen3.5-27B)"}[arm], error_kw=dict(lw=0.8))
    ax.set_xticks(x, [LABEL.get(s, s) for s in streams], rotation=20, ha="right")
    ax.axhline(0.5, color="#888", lw=0.8)
    ax.set_ylabel("session AUROC (max over turns)")
    ax.set_title("MOLE qwen36_27b single-day: insider vs benign sessions", loc="left")
    ax.legend(fontsize=6.5)
    PS.save(fig, FIG / "mole_policy_vs_reader.pdf")


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
    for f in (tables, fig_tpr, fig_dists, fig_fusion, fig_t3, fig_context, fig_la, fig_mole):
        try:
            f()
            print("ok", f.__name__)
        except FileNotFoundError as e:
            print("skip", f.__name__, e)




def _ci(e, lo, hi, nd=3):
    return f"{e:+.{nd}f} [{lo:+.2f}, {hi:+.2f}]"


def summary_tables():
    """results/wb/tables.md: the headline tables of the write-up."""
    L = ["# White-box pilot — summary tables", "",
         "All CIs: 95%, task-cluster bootstrap with calibration noise (amd.evaluation.paired for MB contrasts).", ""]
    p = pd.read_csv(OUT / "mb_paired.csv")
    L += ["## MonitoringBench: reader stream minus gpt-4.1-mini (same mode), TPR of trajectory max", "",
          "| stream | mode | FPR 0.05 | FPR 0.01 | FPR 0.003 |", "|---|---|---|---|---|"]
    v = p[(p.kind == "vs_llm") & (p.detector == "max")]
    for st in [s for s in ORDER if s in set(v.stream)]:
        for mode in ("full", "none"):
            cells = []
            for a in (0.05, 0.01, 0.003):
                r = v[(v.stream == st) & (v["mode"] == mode) & (v.alpha == a)]
                cells.append(_ci(r.est.iloc[0], r.lo.iloc[0], r.hi.iloc[0]) if len(r) else "–")
            L.append(f"| {LABEL.get(st, st)} | {mode} | " + " | ".join(cells) + " |")
    L += ["", "## Accumulation vs max (TPR difference, FPR 0.01)", "",
          "| stream | mode | 2nd-max | top-3 sum | CUSUM k=0.5 | CUSUM k=1.5 | OR(max+CUSUM) |", "|---|---|---|---|---|---|---|"]
    g = p[(p.kind == "gain_vs_max") & (p.alpha == 0.01)]
    for st in [s for s in ORDER if s in set(g.stream)]:
        for mode in ("full", "none"):
            cells = []
            for d in ("kth2", "top3sum", "cusum_k0.5", "cusum_k1.5", "or(max+cusum)"):
                r = g[(g.stream == st) & (g["mode"] == mode) & (g.detector == d)]
                cells.append(_ci(r.est.iloc[0], r.lo.iloc[0], r.hi.iloc[0]) if len(r) else "–")
            L.append(f"| {LABEL.get(st, st)} | {mode} | " + " | ".join(cells) + " |")
    d = p[(p.kind == "did_none_minus_full")]
    L += ["", "## History-free minus history-aware, gain over max (DiD)", "", "| stream | detector | FPR 0.05 | FPR 0.01 |",
          "|---|---|---|---|"]
    for st in [s for s in ORDER if s in set(d.stream)]:
        for det in ("top3sum", "cusum_k0.5", "cusum_k1.5"):
            cells = []
            for a in (0.05, 0.01):
                r = d[(d.stream == st) & (d.detector == det) & (d.alpha == a)]
                cells.append(_ci(r.est.iloc[0], r.lo.iloc[0], r.hi.iloc[0]) if len(r) else "–")
            L.append(f"| {LABEL.get(st, st)} | {det} | " + " | ".join(cells) + " |")
    s = pd.read_csv(OUT / "mb_strata_agent_model.csv")
    L += ["", "## By attack agent model (Honest-550 is all claude-opus-4-5), FPR 0.01", "",
          "| stream | mode | TPR opus-4-5 attacks | minus LLM | TPR opus-4-6 attacks | minus LLM |", "|---|---|---|---|---|---|"]
    s = s[s.alpha == 0.01]
    for st in [x for x in ORDER if x in set(s.stream)]:
        for mode in ("full", "none"):
            cells = []
            for am in sorted(set(s.agent_model)):
                r = s[(s.stream == st) & (s["mode"] == mode) & (s.agent_model == am)]
                if not len(r):
                    cells += ["–", "–"]
                    continue
                r = r.iloc[0]
                cells.append(f"{r.tpr:.3f} [{r.tpr_lo:.2f}, {r.tpr_hi:.2f}]")
                cells.append(_ci(r.vs_llm, r.vs_llm_lo, r.vs_llm_hi) if np.isfinite(r.get("vs_llm", np.nan)) else "–")
            L.append(f"| {LABEL.get(st, st)} | {mode} | " + " | ".join(cells) + " |")
    f = pd.read_csv(OUT / "fusion.csv")
    L += ["", "## Fusion with gpt-4.1-mini (FPR 0.01): TPR, and difference vs the LLM alone", "",
          "| probe | mode | LLM alone | probe alone | KDE-LLR (traj) | KDE-LLR (step) | rank-sum | cascade 5% | cascade 10% | LLM steps used (cascade 10%) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    f1 = f[f.alpha == 0.01]
    for (mode, pr), x in f1.groupby(["mode", "probe"]):
        x = x.set_index("rule")
        c = lambda r: f"{x.loc[r, 'tpr']:.3f} ({_ci(x.loc[r, 'gain_vs_llm'], x.loc[r, 'gain_lo'], x.loc[r, 'gain_hi'])})"  # noqa: E731
        L.append(f"| {LABEL.get(pr, pr)} | {mode} | {x.loc['llm', 'tpr']:.3f} | {c('probe')} | {c('kde_traj')} | {c('kde_step')} | "
                 f"{c('rank_sum')} | {c('cascade_0.05')} | {c('cascade_0.1')} | {x.loc['cascade_0.1', 'calls_steps_all']:.2f} |")
    if (OUT / "la_matched.csv").exists():
        m = pd.read_csv(OUT / "la_matched.csv")
        m = m[(m.threshold_kind == "calibrated") & (m.detector == "max")]
        au = pd.read_csv(OUT / "la_auroc.csv").set_index("stream")
        L += ["", "## LinuxArena (200 honest / 142 attack): trajectory max", "", "| stream | AUROC | TPR@0.05 | TPR@0.01 |",
              "|---|---|---|---|"]
        for st in au.sort_values("auroc_max", ascending=False).index:
            r5 = m[(m.stream == st) & (m.alpha == 0.05)].iloc[0]
            r1 = m[(m.stream == st) & (m.alpha == 0.01)].iloc[0]
            L.append(f"| {st} | {au.loc[st, 'auroc_max']:.3f} | {r5.tpr:.3f} [{r5.tpr_lo:.2f}, {r5.tpr_hi:.2f}] | "
                     f"{r1.tpr:.3f} [{r1.tpr_lo:.2f}, {r1.tpr_hi:.2f}] |")
    if (OUT / "context_heterogeneity.csv").exists():
        H = pd.read_csv(OUT / "context_heterogeneity.csv")
        A = pd.read_csv(OUT / "context_allocation.csv")
        L += ["", "## Per-context thresholds (MB: 7 task clusters; LA: 10 environments)", "",
              "Heterogeneity at a global 5% threshold: per-cluster honest FPR range and logit-normal tau.", "",
              "| panel | FPR range | tau | p | context share of honest max variance |", "|---|---|---|---|---|"]
        for _, r in H[H.B == 0.05].iterrows():
            L.append(f"| {r.panel} | {r.fpr_min:.3f}–{r.fpr_max:.3f} | {r.tau:.2f} | {r.tau_p:.3f} | {r.icc:.3f} |")
        L += ["", "Allocation at 10% spend, spend-matched (matched_ok = share of replicates whose nominal sweep bracketed "
              "the target; realized spend shown). Differences vs global with 95% bootstrap intervals.", "",
              "| panel | rule | matched_ok | spend | uniform TPR | Δ vs global | selection safety | Δ vs global |",
              "|---|---|---|---|---|---|---|---|"]
        x = A[(A["mode"] == "matched") & (A.B == 0.10) & A.rule.isin(["global", "cfar", "pooled_cv", "stackelberg", "maxdet"])]
        for _, r in x.iterrows():
            dl = "" if r.rule == "global" else f"[{r.tpr_uniform_dlo:+.2f}, {r.tpr_uniform_dhi:+.2f}]"
            ds = "" if r.rule == "global" else f"[{r.sel_informed_dlo:+.2f}, {r.sel_informed_dhi:+.2f}]"
            L.append(f"| {r.panel} | {r.rule} | {r.matched_ok:.2f} | {r.spend:.3f} | {r.tpr_uniform:.3f} | {dl} | "
                     f"{r.sel_informed:.3f} | {ds} |")
    if (OUT / "t3_detection.csv").exists():
        t = pd.read_csv(OUT / "t3_detection.csv")
        t = t[(t.stat == "max") & (t.alpha == 0.01)]
        L += ["", "## T3 refined attacks: detection at FPR 0.01 (max), paired on base attacks", ""]
        piv = t.pivot_table(index=["block", "mode", "stream"], columns="arm", values="detect").round(3)
        try:
            L.append(piv.to_markdown())
        except ImportError:
            L += ["```", piv.to_string(), "```"]
        dd = pd.read_csv(OUT / "t3_detection_diff.csv")
        dd = dd[(dd.stat == "max") & (dd.alpha == 0.01)]
        L += ["", "Paired differences (refined − reference), FPR 0.01, max:", "", "| block | mode | stream | arm | ref | diff [95% CI] |",
              "|---|---|---|---|---|---|"]
        for _, r in dd.iterrows():
            L.append(f"| {r.block} | {r['mode']} | {r.stream} | {r.arm} | {r.get('ref', 'original')} | {_ci(r['diff'], r.lo, r.hi)} |")
    if (OUT / "mole_policy_vs_reader.csv").exists():
        mo = pd.read_csv(OUT / "mole_policy_vs_reader.csv")
        L += ["", "## Stage 2 (MOLE qwen36_27b single-day): policy vs reader activations", "",
              "| arm | stream | agg | AUROC [95% CI] | AUROC (executed) | TPR@0.05 | TPR@0.01 |", "|---|---|---|---|---|---|---|"]
        for _, r in mo.iterrows():
            L.append(f"| {r.arm} | {r.stream} | {r["agg"]} | {r.auroc:.3f} [{r.auroc_lo:.2f}, {r.auroc_hi:.2f}] | "
                     f"{r.auroc_executed:.3f} | {r['tpr@0.05']:.3f} | {r['tpr@0.01']:.3f} |")
    (OUT / "tables.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
    summary_tables()
