"""Overview forest plot for the summary report: headline effects with corrected 95% CIs.

Every plotted number is read from a result file; nothing is typed in.
- Ideas 1-4 and the round-1 Idea 05 rows: results/fixes2/headline_threshold_rerun.csv (conformal randomized
  threshold rule; column new_estimate_ci), matched by the start of the `claim` text.
- Idea 05 rounds 2-3: results/r5_luna/hypotheses.csv, results/r5_luna/mb_strong_hypotheses.csv and
  results/r5_watch/hypotheses.csv (conformal rule, which is primary there).

    unset VIRTUAL_ENV; uv run python docs/reports/src/make_overview_fig.py
"""
import re
from pathlib import Path

import matplotlib as mpl

mpl.use("pdf")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
RES = REPO / "results"
OUT = Path(__file__).resolve().parent / "figs"

BLUE, RED, GRAY, INK2 = "#2a78d6", "#e34948", "#898781", "#52514e"
mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
                     "font.size": 8.2, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
                     "xtick.color": GRAY, "ytick.color": GRAY, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
                     "axes.grid": True, "grid.color": "#e1e0d9", "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
                     "pdf.fonttype": 42, "savefig.bbox": "tight"})

HEAD = pd.read_csv(RES / "fixes2" / "headline_threshold_rerun.csv")
NUM = r"([+-]?\d*\.\d+|[+-]?\d+)"


def head(prefix):
    """(est, lo, hi) of the unique headline row whose claim starts with `prefix` (corrected threshold rule)."""
    m = HEAD[HEAD.claim.str.startswith(prefix)]
    assert len(m) == 1, (prefix, len(m))
    g = re.match(rf"\s*{NUM}\s*\[\s*{NUM}\s*,\s*{NUM}\s*\]", m.iloc[0].new_estimate_ci)
    assert g, m.iloc[0].new_estimate_ci
    return tuple(float(x) for x in g.groups())


def luna(test):
    d = pd.read_csv(RES / "r5_luna" / "hypotheses.csv")
    r = d[(d.test == test) & (d.convention == "conformal") & (d.resampling == "orig")].iloc[0]
    return r.est, r.lo, r.hi


def mbstrong(test):
    d = pd.read_csv(RES / "r5_luna" / "mb_strong_hypotheses.csv")
    r = d[(d.test == test) & (d.convention == "conformal") & (d.resampling == "orig")].iloc[0]
    return r.est, r.lo, r.hi


def watch(test):
    d = pd.read_csv(RES / "r5_watch" / "hypotheses.csv")
    r = d[(d.test == test) & (d.convention == "conformal") & (d.resampling == "task") & (d.panel == "mb:gen")].iloc[0]
    return r.est, r.lo, r.hi


panels = [
    ("(a) Idea 1: accumulation (top-3 / 3rd-max) minus max", "TPR difference", [
        ("Top-3 sum − max, 9 PR monitors pooled, 5% [C]", head("r4_cs pooled top-3 sum - max, 9 identical-input")),
        ("GPT-4o, persistent state, history-free, 5%", head("Idea 1 overview: persistent state GPT-4o")),
        ("gpt-4.1-mini, same (logprob read-out only)", head("Idea 1 overview: persistent state gpt-4.1-mini")),
        ("MOLE pooled single-day 3rd-max, 10% [C]", head("Idea 1 overview: MOLE pooled")),
        ("Rule chooser vs always-max (nested), 1%", head("Idea 1 overview: rule chooser")),
    ]),
    ("(b) Idea 2: per-context allocation vs global", "selection-safety difference", [
        ("Stackelberg − global, 7 settings, 1% [C]", head("r4_ctx primary: Stackelberg - global")),
        ("  same, main-task resampling", head("r4_ctx primary, main-task cluster bootstrap")),
        ("Stackelberg − global, 7 settings, 5%", head("Idea 2 overview: Stackelberg - global")),
        ("CFAR − global, 7 settings, 5%", head("Idea 2 overview: CFAR - global, 7 settings")),
        ("CFAR − global, ControlArena, 5%", head("Idea 2 overview: CFAR - global, ControlArena")),
    ]),
    ("(c) Idea 3: rewriting and detector-aware pacing (1%)", "undetected-success difference", [
        ("Rewrite − original, execution validity (n=28) [C]", head("r4_replay PRIMARY (track analyze.py)")),
        ("Uninformed rewrite − original (gemini, strict)", head("Idea 3 overview (c1)")),
        ("  same, detection only (validity ignored)", head("Idea 3 overview (c2)")),
        ("Pacing − uninformed rewrite (one-shot, strict)", head("Idea 3 overview (c3)")),
    ]),
    ("(d) White-box reader (Qwen3.5-27B) vs gpt-4.1-mini (1%)", "TPR difference", [
        ("FIBS axial follow-up, held-out replication [C]", head("r4_wb H1 (prereg)")),
        ("  same probe, pilot (775 attacks)", head("Overview (d): FIBS axial follow-up probe")),
        ("  full-history reading, equal FPR (dropped)", head("r4_wb A1: FIBS axial follow-up `full`")),
        ("Sabotage probe, full-history reading", head("Overview (d): sabotage probe, full-history")),
        ("Sabotage-probe triage + LLM (13% of steps)", head("Overview (d): sabotage-probe triage")),
    ]),
    ("(e) Idea 05: decision-only first stages (1% trajectory FPR; all preregistered except the audit row)",
     "TPR difference", [
        ("JEV − nano triage, aksh-n (e=10%; first-stage designs)", head("H2-AK (1% FPR")),
        ("JEV$\\rightarrow$Gemini − Gemini only, aksh-n pooled (e=20%; NI test)", head("H1-AK (1% FPR")),
        ("  same, leave SHADE out (audit)", head("H1-AK leave SHADE out")),
        ("JEV$\\rightarrow$generative Luna − Luna only, MB (e=20%; NI test)", mbstrong("H1-MB-strong")),
        ("JEV − Watcher-style triage into Luna, MB (e=10%)", watch("W1@e=10")),
        ("  same, e=20%", watch("W1@e=20")),
        ("Luna Decisions − JEV triage, aksh-n (e=10%)", luna("H5a-AK")),
        ("Luna Decisions − generative Luna, standalone", luna("H5c")),
        ("Full − truncated action, Luna$\\rightarrow$Gemini, opus-4-6", luna("H5d-CAS")),
    ]),
]


def draw(ax, title, xlabel, rows):
    for i, (lab, (est, lo, hi)) in enumerate(rows):
        y = len(rows) - 1 - i
        sig = lo > 0 or hi < 0
        col = (BLUE if est > 0 else RED) if sig else GRAY
        ax.plot([lo, hi], [y, y], color=col, lw=2, solid_capstyle="butt")
        ax.plot([est], [y], "o", color=col, ms=6, mec="white", mew=1)
        ax.text(hi + 0.012, y, f"{est:+.3f} [{lo:+.3f}, {hi:+.3f}]", va="center", fontsize=6.8, color=INK2)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows][::-1], fontsize=7.3)
    ax.set_xlabel(xlabel)
    lo_all = min(r[1][1] for r in rows)
    hi_all = max(r[1][2] for r in rows)
    ax.set_xlim(min(lo_all - 0.05, -0.1), hi_all + 0.32)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_title(title, loc="left", fontsize=8.6)


fig = plt.figure(figsize=(10.5, 8.6))
gs = fig.add_gridspec(3, 2, height_ratios=[5, 5, 9])
axes = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1]),
        fig.add_subplot(gs[2, :])]
for ax, (title, xlabel, rows) in zip(axes, panels):
    draw(ax, title, xlabel, rows)
fig.text(0.01, -0.01, "Colored = 95% CI excludes 0 (blue positive, red negative); gray = not significant. For the two "
         "non-inferiority (NI) tests in (e), a CI above −0.03 is the supported result. [C] = preregistered. "
         "Conformal randomized threshold rule throughout.", fontsize=7, color=INK2)
fig.tight_layout()
OUT.mkdir(exist_ok=True)
fig.savefig(OUT / "overview.pdf")
print("ok")
