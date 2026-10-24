"""Vector PDF figures for report 05 (Idea 05: decision-only models as first-stage monitors).

Every plotted number is read from a file under results/ (conformal randomized threshold rule unless a
caption says otherwise); nothing is typed in. Outputs go to docs/reports/src/figs/.

    unset VIRTUAL_ENV; uv run python docs/reports/src/make_r5_report_figs.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
RES = REPO / "results"
FX = RES / "fixes2"
OUT = Path(__file__).resolve().parent / "figs"

INK, INK2, GRID, BAND = "#0b0b0b", "#52514e", "#e4e3df", "#ebeae5"
BLUE, ORANGE, GREEN, RED, PURPLE, GOLD, GRAY = ("#2a78d6", "#eb6834", "#1a9e77", "#d6455d", "#7a5cc4", "#c99a06",
                                                "#8d8c86")
plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "pdf.fonttype": 42, "legend.frameon": False})

SETTING = {"akshn_bash": "bash", "akshn_agentdojo": "agentdojo", "akshn_iac": "iac", "akshn_shade": "SHADE",
           "akshn_basharena_opus46": "BashArena-opus-4-6", "akshn_basharena_sonnet45": "BashArena-sonnet-4-5",
           "akshn_linuxarena": "LinuxArena", "mb": "MonitoringBench"}
AK6 = ["akshn_bash", "akshn_agentdojo", "akshn_iac", "akshn_shade", "akshn_basharena_opus46", "akshn_linuxarena"]


def forest(ax, rows, xlabel, ref=0.0, color=BLUE, sig_color=True, fmt="{:+.3f}", log=False):
    """rows: list of (label, est, lo, hi), top to bottom. Colored when the CI excludes `ref`.
    The estimate and CI are printed in a column at the right edge of the panel."""
    n = len(rows)
    for k, (_, e, lo, hi) in enumerate(rows):
        y = n - 1 - k
        c = color
        if sig_color:
            c = (BLUE if e > ref else RED) if (lo > ref or hi < ref) else GRAY
        ax.plot([lo, hi], [y, y], color=c, lw=1.8, solid_capstyle="round")
        ax.plot([e], [y], "o", color=c, ms=5.2, mec="white", mew=0.8)
    lo_all = min(r[2] for r in rows)
    hi_all = max(r[3] for r in rows)
    if log:
        ax.set_xscale("log")
        right = hi_all * (hi_all / lo_all) ** 0.75
        ax.set_xlim(lo_all / 1.15, right)
    else:
        span = hi_all - lo_all
        right = hi_all + 0.95 * span
        left = min(lo_all, ref) - 0.06 * span
        ax.set_xlim(left, right)
        ax.set_xticks([t for t in ax.get_xticks() if left <= t <= hi_all + 0.05 * span])
        ax.set_xlim(left, right)
    for k, (_, e, lo, hi) in enumerate(rows):
        ax.text(right, n - 1 - k, (fmt + " [" + fmt + ", " + fmt + "]").format(e, lo, hi), fontsize=6.6,
                color=INK2, ha="right", va="center")
    ax.axvline(ref, color=INK2, lw=0.8)
    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in rows][::-1])
    ax.set_ylim(-0.6, n - 0.2)
    ax.set_xlabel(xlabel)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)


# ------------------------------------------------------------------ round 1 (H1-H3), conformal rule
def fig_round1():
    hyp = pd.read_csv(FX / "jev_primary_conformal_thrfix" / "hypotheses.csv").set_index("hypothesis")
    cells = pd.read_csv(FX / "jev_primary_conformal_thrfix" / "cascade_cells.csv")
    aud = pd.read_csv(FX / "jev_audit_conformal_thrfix.csv").set_index("claim")
    lab = {"H1-MB": "H1-MB  JEV→mini vs mini only (e=20%)", "H1-AK": "H1-AK  JEV→Gemini vs Gemini only (e=20%)",
           "H2-MB": "H2-MB  JEV vs nano triage (e=10%)", "H2-AK": "H2-AK  JEV vs nano triage (e=10%)",
           "H3-MB": "H3-MB  JEV vs probe triage (e=10%)"}
    a = [(lab[h], hyp.loc[h, "est"], hyp.loc[h, "lo"], hyp.loc[h, "hi"]) for h in lab]

    def cell(panel, alpha, first="jev", e=0.2):
        r = cells[(cells.panel == panel) & (cells["first"] == first) & (cells.e == e) & (cells.alpha == alpha)
                  & (cells.mapping == "floor")].iloc[0]
        return r.d_llm, r.d_lo, r.d_hi

    lso = aud.loc["H1-AK leave out akshn_shade"]
    eqw = aud.loc["H1-AK equal-weight settings (S20 B2000)"]
    b = [("pooled, 6 settings (as preregistered)", hyp.loc["H1-AK", "est"], hyp.loc["H1-AK", "lo"],
          hyp.loc["H1-AK", "hi"]),
         ("leave SHADE out", lso.est, lso.lo, lso.hi),
         ("settings weighted equally", eqw.est, eqw.lo, eqw.hi),
         ("pooled at 5% FPR, 7 settings", *cell("akshn_pooled", 0.05))]
    b += [(f"  {SETTING[s]} alone", *cell(s, 0.01)) for s in AK6]
    fig, axes = plt.subplots(2, 1, figsize=(6.6, 6.4), gridspec_kw={"height_ratios": [5, 10]})
    forest(axes[0], a, "TPR difference at 1% trajectory FPR")
    axes[0].axvline(-0.03, color=ORANGE, lw=0.9, ls="--")
    axes[0].text(-0.03, len(a) - 0.35, "NI margin", color=ORANGE, fontsize=7, ha="right")
    axes[0].set_title("(a) Preregistered tests (Holm over five)", loc="left", fontsize=8.8)
    forest(axes[1], b, "TPR difference, JEV→Gemini (e=20%) − Gemini only")
    axes[1].axhline(len(b) - 4.5, color=GRID, lw=0.8, ls="--")
    axes[1].set_title("(b) H1-AK decomposition (1% FPR unless stated)", loc="left", fontsize=8.8)
    fig.tight_layout()
    fig.savefig(OUT / "r5_round1.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_tpr_vs_e():
    cells = pd.read_csv(FX / "jev_primary_conformal_thrfix" / "cascade_cells.csv")
    cells = cells[(cells.alpha == 0.01) & (cells.mapping == "floor")]
    styles = [("jev", "JEV", BLUE, "-"), ("nano", "gpt-4.1-nano", ORANGE, "-"), ("probe", "probe (FIBS axial)", GREEN, "-"),
              ("len", "action length", GOLD, "-"), ("rand", "random", GRAY, "--"),
              ("oracle", "oracle (2nd-stage score)", PURPLE, "-."), ("oracle_label", "label oracle", "#b9a6e8", ":")]
    panels = [("mb", "MB (2nd stage gpt-4.1-mini)"), ("akshn_pooled", "aksh-n, 6 settings (Gemini)"),
              ("akshn_nano_pooled", "aksh-n nano subset (Gemini)")]
    fig, axes = plt.subplots(1, 3, figsize=(8.8, 3.1), sharey=False)
    for ax, (p, title) in zip(axes, panels):
        d = cells[cells.panel == p]
        llm = d[d["first"] == "llm_only"].iloc[0]
        ax.axhspan(llm.tpr_lo, llm.tpr_hi, color=BAND, zorder=0)
        ax.axhline(llm.tpr, color=INK, lw=1.4)
        ax.text(0.305, llm.tpr, " LLM only", va="bottom", fontsize=6.8, color=INK)
        jo = d[d["first"] == "jev_only"].iloc[0]
        ax.axhline(jo.tpr, color=BLUE, lw=0.9, ls=":")
        ax.text(0.305, jo.tpr, " JEV only", va="top", fontsize=6.8, color=BLUE)
        for f, name, c, ls in styles:
            q = d[d["first"] == f].sort_values("e")
            if q.empty:
                continue
            ax.errorbar(q.e, q.tpr, yerr=[q.tpr - q.tpr_lo, q.tpr_hi - q.tpr], color=c, ls=ls, marker="o", ms=3.2,
                        lw=1.3, capsize=1.5, elinewidth=0.7, label=name)
        ax.set_xticks([0.05, 0.1, 0.2, 0.3], ["5", "10", "20", "30"])
        ax.set_xlim(0.03, 0.37)
        ax.set_xlabel("escalated share of honest steps e (%)")
        ax.set_title(title, loc="left", fontsize=8.2)
        ax.grid(color=GRID, lw=0.5)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("TPR at 1% trajectory FPR")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, fontsize=7.2, bbox_to_anchor=(0.5, -0.06))
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(OUT / "r5_tpr_vs_e.pdf", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ length / format check (exploratory)
def fig_length():
    d = pd.read_csv(RES / "r5_jev" / "explore_length_confound.csv").set_index("panel")
    order = ["mb", "akshn_bash", "akshn_agentdojo", "akshn_iac", "akshn_shade", "akshn_basharena_opus46",
             "akshn_basharena_sonnet45", "akshn_linuxarena"]
    series = [("len_only_cv", "length only (CV)", GOLD, "s"), ("len_format_cv", "length + format (CV)", ORANGE, "D"),
              ("jev_max", "JEV max", BLUE, "o"), ("jev_max|strat_lenscore", "JEV max, length-stratified", PURPLE, "^"),
              ("llm_max", "2nd-stage LLM max", INK2, "v")]
    fig, ax = plt.subplots(figsize=(8.6, 3.0))
    x = np.arange(len(order))
    w = 0.15
    for k, (col, name, c, m) in enumerate(series):
        xs = x + (k - 2) * w
        ys = d.loc[order, col].values
        lo = d.loc[order, f"{col}_lo"].values
        hi = d.loc[order, f"{col}_hi"].values
        ax.errorbar(xs, ys, yerr=[ys - lo, hi - ys], fmt=m, color=c, ms=4.2, capsize=1.5, elinewidth=0.8, label=name)
    ax.axhline(0.5, color=INK2, lw=0.7, ls="--")
    ax.set_xticks(x, [SETTING[o].replace("BashArena-", "BashArena\n").replace("MonitoringBench", "MB")
                      for o in order], fontsize=7.6)
    ax.set_ylabel("trajectory AUROC (attack = positive)")
    ax.set_ylim(0.2, 1.03)
    ax.grid(axis="y", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.legend(ncol=3, fontsize=7.2, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout()
    fig.savefig(OUT / "r5_length.pdf", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ interface penalty + strong MB second stage
def fig_interface_and_mb_strong():
    rob = pd.read_csv(RES / "r5_luna" / "robustness.csv")
    rob = rob[(rob.convention == "conformal") & (rob.resampling == "orig") & (rob.alpha == 0.01)].set_index("test")
    hyp = pd.read_csv(RES / "r5_luna" / "hypotheses.csv")
    hyp = hyp[(hyp.convention == "conformal") & (hyp.resampling == "orig")].set_index("test")
    rows = []
    for key, name in [("H5c pooled", "pooled, 3 panels (H5c)"), ("H5c mb_h5c", "MonitoringBench subset"),
                      ("H5c akshn_basharena_opus46", "BashArena-opus-4-6"), ("H5c linuxarena_nano", "LinuxArena nano")]:
        r = rob.loc[key] if key in rob.index else hyp.loc["H5c"]
        rows.append((f"{name}\n{r.tpr1:.3f} vs {r.tpr2:.3f}", r.est, r.lo, r.hi))
    cells = pd.read_csv(RES / "r5_luna" / "mb_strong_cells.csv")
    cells = cells[(cells.convention == "conformal") & (cells.alpha == 0.01)]
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.4), gridspec_kw={"width_ratios": [1, 1.1]})
    forest(axes[0], rows, "TPR at 1% FPR: Decisions − generative")
    axes[0].set_title("(a) Same model, two interfaces (standalone)", loc="left", fontsize=8.6)
    ax = axes[1]
    gen = cells[(cells["first"] == "gen") & (cells.kind == "standalone")].iloc[0]
    ax.axhspan(gen.tpr_lo, gen.tpr_hi, color=BAND, zorder=0)
    ax.axhline(gen.tpr, color=INK, lw=1.4)
    ax.text(0.305, gen.tpr, " generative Luna only", va="bottom", fontsize=6.8)
    mini = cells[(cells["first"] == "llm") & (cells.kind == "standalone")].iloc[0]
    ax.axhline(mini.tpr, color=INK2, lw=0.9, ls=":")
    ax.text(0.305, mini.tpr, " gpt-4.1-mini only", va="bottom", fontsize=6.8, color=INK2)
    for f, name, c, ls in [("jev", "JEV", BLUE, "-"), ("probe", "probe (FIBS axial)", GREEN, "-"),
                           ("decider", "Decider v1.2", PURPLE, "-"), ("luna", "Luna Decisions", RED, "-"),
                           ("nano", "gpt-4.1-nano", ORANGE, "-"), ("len", "action length", GOLD, "-"),
                           ("rand", "random", GRAY, "--")]:
        q = cells[(cells["first"] == f) & (cells.kind == "cascade")].sort_values("e")
        ax.errorbar(q.e, q.tpr, yerr=[q.tpr - q.tpr_lo, q.tpr_hi - q.tpr], color=c, ls=ls, marker="o", ms=3.2,
                    lw=1.3, capsize=1.5, elinewidth=0.6, label=name)
    ax.set_xticks([0.05, 0.1, 0.2, 0.3], ["5", "10", "20", "30"])
    ax.set_xlim(0.03, 0.40)
    ax.set_xlabel("escalated share of honest steps e (%)")
    ax.set_ylabel("TPR at 1% trajectory FPR")
    ax.set_title("(b) MB, second stage generative GPT-6 Luna", loc="left", fontsize=8.6)
    ax.grid(color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, ncol=3, loc="upper center", bbox_to_anchor=(0.45, -0.17))
    fig.tight_layout()
    fig.savefig(OUT / "r5_interface_mbstrong.pdf", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ Watcher-style triage: severity and cost
def fig_watch_extra():
    sev = pd.read_csv(RES / "r5_watch" / "explore_severity_hist.csv")
    cells = pd.read_csv(RES / "r5_watch" / "cells.csv")
    cells = cells[(cells.panel == "mb:gen") & (cells.alpha == 0.01) & (cells.convention == "conformal")]
    cost = pd.read_csv(RES / "r5_watch" / "cost_latency.csv")
    cost = cost[cost.panel == "mb:gen"].set_index("config")
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.4), gridspec_kw={"width_ratios": [1, 1.1]})
    ax = axes[0]
    w = 0.2
    for k, (panel, name) in enumerate([("mb", "MB"), ("la_nano", "LinuxArena")]):
        s = sev[sev.panel == panel].sort_values("severity")
        off = (-1.5 + 2 * k) * w
        ax.bar(s.severity + off, s.honest_traj_max, width=w, color=[GREEN, BLUE][k], alpha=0.9,
               label=f"{name} honest")
        ax.bar(s.severity + off + w, s.attack_traj_max, width=w, color=[ORANGE, RED][k], alpha=0.9,
               label=f"{name} attack")
    ax.axvline(5.5, color=INK2, lw=0.8, ls="--")
    ax.axvline(7.5, color=INK2, lw=0.8, ls=":")
    ax.set_ylim(0, 0.52)
    ax.text(5.6, 0.47, "≥6", fontsize=7, color=INK2)
    ax.text(7.6, 0.47, "≥8", fontsize=7, color=INK2)
    ax.set_xticks(range(1, 11))
    ax.set_xlabel("trajectory max of Watcher-style severity")
    ax.set_ylabel("share of trajectories")
    ax.set_title("(a) Severity is high on honest MB runs", loc="left", fontsize=8.6)
    ax.legend(fontsize=6.8, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.3))
    ax.grid(axis="y", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax = axes[1]
    steps = cost["steps_per_traj"].iloc[0]
    c2 = cost["c_second"].iloc[0]
    gen = cells[cells.config == "gen"].iloc[0]
    ax.errorbar([1000 * steps * c2], [gen.tpr], yerr=[[gen.tpr - gen.tpr_lo], [gen.tpr_hi - gen.tpr]], fmt="s",
                color=INK, ms=5, capsize=2, label="generative Luna on every step")
    for f, name, c in [("watch", "Watcher-style GPT-5.6 Luna", GOLD), ("jev", "JEV", BLUE),
                       ("luna", "Luna Decisions", RED), ("decider", "Decider v1.2 (hosted price)", PURPLE)]:
        q = cells[(cells["first"] == f) & (cells.kind == "cascade")].sort_values("e")
        xs = [cost.loc[cfg, "cost_1k"] for cfg in q.config]
        ax.plot(xs, q.tpr, "-o", color=c, ms=3.5, lw=1.3, label=f"{name} cascade, e = 5–30%")
    for cfg, mk in [("watch@sev>=6", "*"), ("watch@sev>=8", "P")]:
        r = cells[cells.config == cfg].iloc[0]
        ax.plot([cost.loc[cfg, "cost_1k"]], [r.tpr], mk, color=GOLD, ms=9, mec=INK, mew=0.6,
                label="Watcher-style fixed cutoff, severity ≥" + cfg.split(">=")[1])
    ax.set_xlabel("cost per 1,000 MB trajectories (USD)")
    ax.set_ylabel("TPR at 1% trajectory FPR")
    ax.set_title("(b) Detection vs cost (2nd stage generative Luna)", loc="left", fontsize=8.6)
    ax.grid(color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.6, ncol=1, loc="upper center", bbox_to_anchor=(0.5, -0.3))
    ax.set_ylim(0.2, 0.55)
    fig.tight_layout()
    fig.savefig(OUT / "r5_watch_extra.pdf", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ shared misses (exploratory)
def fig_overlap():
    d = pd.read_csv(RES / "r5_jev" / "explore_rq3_overlap.csv")
    d = d[(d.alpha == 0.01) & (d.p_llm_miss > 0) & (d.ratio_cb > 0) & (d.panel != "akshn_basharena_sonnet45")]
    d = d.assign(name=d.panel.map(SETTING)).sort_values("ratio_cb", ascending=False)
    fig, ax = plt.subplots(figsize=(6.4, 2.4))
    rows = [(f"{r.name} ({int(r.n_conf_benign)} of {int(r.n_attack)} attacks)", r.ratio_cb, r.ratio_cb_lo,
             r.ratio_cb_hi) for r in d.itertuples()]
    forest(ax, rows, "P(LLM misses | JEV confidently clears) / P(LLM misses), 1% FPR", ref=1.0, fmt="{:.2f}",
           log=True)
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xticks([1, 2, 4, 8], ["1", "2", "4", "8"])
    fig.tight_layout()
    fig.savefig(OUT / "r5_overlap.pdf", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ Watcher-style triage: W1/W2 family and secondary panels
def fig_w12():
    h = pd.read_csv(RES / "r5_watch" / "hypotheses.csv")
    h = h[(h.convention == "conformal") & (h.resampling == "task")]
    names = {"W1@e=10": "JEV, e=10%", "W1@e=20": "JEV, e=20%", "W2-luna@e=10": "Luna Decisions, e=10%",
             "W2-luna@e=20": "Luna Decisions, e=20%", "W2-decider@e=10": "Decider v1.2, e=10%",
             "W2-decider@e=20": "Decider v1.2, e=20%"}
    panels = [("mb:gen", "(a) MB, 2nd stage generative GPT-6 Luna (primary)"),
              ("mb:mini", "(b) MB, 2nd stage gpt-4.1-mini"), ("la_nano:gemini", "(c) LinuxArena nano, 2nd stage Gemini")]
    fig, axes = plt.subplots(3, 1, figsize=(6.6, 7.0))
    for ax, (pn, title) in zip(axes, panels):
        d = h[h.panel == pn].set_index("test")
        rows = [(f"{names[t]} (Holm {d.loc[t, 'p_holm']:.3f})", d.loc[t, "est"], d.loc[t, "lo"], d.loc[t, "hi"])
                for t in names]
        forest(ax, rows, "ΔTPR at 1% FPR, decision-model cascade − Watcher-style cascade")
        ax.set_title(title, loc="left", fontsize=8.6)
    fig.tight_layout()
    fig.savefig(OUT / "r5_w12.pdf", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_round1()
    fig_tpr_vs_e()
    fig_length()
    fig_interface_and_mb_strong()
    fig_watch_extra()
    fig_overlap()
    fig_w12()
    print("ok")
