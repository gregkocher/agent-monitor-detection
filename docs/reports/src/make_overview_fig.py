"""Overview forest plot for the summary report: audit-verified effects with corrected 95% CIs.

Values are copied from results/fixes/corrections.csv, results/audit2/corrections.csv and the per-track
tables (cited in the summary report). Effects without a corrected CI are not plotted.
"""
import matplotlib as mpl
import matplotlib.pyplot as plt

BLUE, ORANGE, AQUA, RED, GRAY, INK2 = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#898781", "#52514e"
mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
                     "font.size": 8.2, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
                     "xtick.color": GRAY, "ytick.color": GRAY, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
                     "axes.grid": True, "grid.color": "#e1e0d9", "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
                     "pdf.fonttype": 42, "savefig.bbox": "tight"})

panels = [
    ("(a) Idea 1: accumulation (top-3 / 3rd-max) minus max", "TPR difference", [
        ("Persistent state, GPT-4o, history-free (5% FPR)", 0.146, 0.025, 0.226),
        ("Persistent state, gpt-4.1-mini, history-free", 0.145, -0.001, 0.228),
        ("MOLE pooled single-day, 3rd-max (10% FPR)", -0.066, -0.156, 0.023),
        ("Rule chooser vs always-max (nested, 1% FPR)", 0.001, -0.014, 0.013),
    ]),
    ("(b) Idea 2: per-context allocation vs global", "selection-safety difference", [
        ("Stackelberg − global, 7 settings, 5% spend-matched", 0.075, 0.03, 0.12),
        ("CFAR − global, 7 settings, 5% spend-matched", -0.137, -0.30, 0.01),
        ("CFAR − global, ControlArena, 5% spend-matched", -0.347, -0.63, -0.06),
    ]),
    ("(c) Idea 3: rewriting and detector-aware pacing", "undetected-success difference", [
        ("Uninformed rewrite − original (gemini, strict)", -0.37, -0.55, -0.19),
        ("  same, detection only (valid rewrites)", -0.143, -0.300, -0.027),
        ("Pacing − uninformed rewrite (one-shot, strict)", 0.087, -0.032, 0.183),
    ]),
    ("(d) White-box reader (Qwen3.5-27B) vs gpt-4.1-mini", "TPR difference at 1% FPR", [
        ("FIBS axial follow-up probe, per-step reading", 0.206, 0.09, 0.32),
        ("Sabotage probe, full-history reading", 0.098, 0.015, 0.163),
        ("Sabotage-probe triage + LLM (13% of steps)", 0.129, 0.07, 0.23),
    ]),
]

fig, axes = plt.subplots(2, 2, figsize=(10.5, 5.6))
for ax, (title, xlabel, rows) in zip(axes.ravel(), panels):
    for i, (lab, est, lo, hi) in enumerate(rows):
        y = len(rows) - 1 - i
        sig = lo > 0 or hi < 0
        col = (BLUE if est > 0 else RED) if sig else GRAY
        ax.plot([lo, hi], [y, y], color=col, lw=2, solid_capstyle="butt")
        ax.plot([est], [y], "o", color=col, ms=6, mec="white", mew=1)
        ax.text(hi + 0.012, y, f"{est:+.3f} [{lo:+.2f}, {hi:+.2f}]", va="center", fontsize=7, color=INK2)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows][::-1], fontsize=7.4)
    ax.set_xlabel(xlabel)
    lo_all = min(r[2] for r in rows); hi_all = max(r[3] for r in rows)
    ax.set_xlim(min(lo_all - 0.05, -0.1), hi_all + 0.32)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_title(title, loc="left", fontsize=8.6)
fig.text(0.01, -0.01, "Colored = 95% CI excludes 0 (blue positive, red negative); gray = not significant. "
         "CIs from the corrected paired bootstrap (clustered, calibration noise included).", fontsize=7, color=INK2)
fig.tight_layout()
fig.savefig("figs/overview.pdf")
print("ok")
