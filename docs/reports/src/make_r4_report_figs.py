"""Vector PDF figures for reports 03 and 04 (round 4, conformal threshold rule), drawn from result CSV/JSON files.

Outputs go to docs/reports/src/figs/. Every plotted number is read from a file under results/; nothing is typed in.

    uv run python docs/reports/src/make_r4_report_figs.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
RES = REPO / "results"
FX = RES / "fixes2"
OUT = Path(__file__).resolve().parent / "figs"

INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, GREEN = "#2a78d6", "#eb6834", "#1a9e77"
plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "pdf.fonttype": 42})


def forest(ax, rows, xlabel, ref=0.0, offset=0.0, color=BLUE, marker="o", fill=True, label=None):
    """rows: list of (label, est, lo, hi) top to bottom."""
    n = len(rows)
    ys = [n - 1 - i + offset for i in range(n)]
    for y, (_, e, lo, hi) in zip(ys, rows):
        ax.plot([lo, hi], [y, y], color=color, lw=1.8, solid_capstyle="round")
        ax.plot([e], [y], marker, color=color, ms=5.5, mec=color if fill else color,
                mfc=color if fill else "white", mew=1.3)
    if label:
        ax.plot([], [], marker, color=color, mfc=color if fill else "white", label=label)
    ax.axvline(ref, color=INK2, lw=0.8)
    ax.set_yticks([n - 1 - i for i in range(n)])
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlabel(xlabel)
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------- report 03
def fig_r3_forest():
    us = pd.DataFrame(json.load(open(FX / "rep_r3t3_conformal_thrfix" / "paired_contrasts.json")))
    us = us[(us.detector == "max") & (us.alpha == 0.01)].set_index("contrast")
    dec = pd.read_csv(FX / "rep_audit2_t3r3_conformal_thrfix" / "repro_t3r3.csv")
    dec = dec[dec.kind == "detection_only"].set_index("contrast")
    pairs = [  # (label, key in paired_contrasts.json, key in repro_t3r3.csv)
        ("control/gpt-4.1 − original", "control/gpt41 − original", "control/gpt41 - original"),
        ("control/gemini − original", "control/gemini − original", "control/gemini - original"),
        ("control: gpt-4.1 − gemini", "rewrite_control: gpt-4.1 − gemini", "control: gpt41 - gemini"),
        ("pace_max/gpt-4.1 − control", "pace_max/gpt41 − control/gpt41", "pace_max/gpt41 - control/gpt41"),
        ("pace_cusum/gpt-4.1 − control", "pace_cusum/gpt41 − control/gpt41", "pace_cusum/gpt41 - control/gpt41"),
        ("pace_multichart/gpt-4.1 − control", "pace_multichart/gpt41 − control/gpt41",
         "pace_multichart/gpt41 - control/gpt41"),
        ("pace_max/gemini − control", "pace_max/gemini − control/gemini", "pace_max/gemini - control/gemini"),
        ("pace_cusum/gemini − control", "pace_cusum/gemini − control/gemini", "pace_cusum/gemini - control/gemini"),
        ("pace_multichart/gemini − control", "pace_multichart/gemini − control/gemini",
         "pace_multichart/gemini - control/gemini"),
    ]
    a = [(lab, us.loc[k].est, us.loc[k].lo, us.loc[k].hi) for lab, k, _ in pairs]
    b = [(lab, dec.loc[k].est, dec.loc[k].lo, dec.loc[k].hi) for lab, _, k in pairs]
    fig, ax = plt.subplots(figsize=(6.3, 4.0))
    forest(ax, a, "Δ undetected success (max, α = 0.01, one-shot)", offset=0.15, color=BLUE,
           label="strict undetected success")
    forest(ax, b, "Δ undetected success (max, α = 0.01, one-shot)", offset=-0.15, color=ORANGE, fill=False,
           label="detection only (validity ignored; every rewrite counted)")
    ax.axhline(5.5, color=GRID, lw=0.8, ls="--")
    ax.legend(loc="upper center", bbox_to_anchor=(0.4, -0.16), ncol=2, frameon=False, fontsize=7.5)
    fig.tight_layout()
    fig.savefig(OUT / "r3_forest_conformal.pdf")


def fig_r4_replay():
    tr = pd.DataFrame(json.load(open(FX / "rep_r4_analyze_conformal_thrfix" / "paired_contrasts.json")))
    tr = tr[(tr.detector == "max") & (tr.alpha == 0.01)]
    ind = pd.read_csv(FX / "rep_r4_indep_conformal_thrfix" / "rep_r4_contrasts.csv")
    ind = ind[ind.alpha == 0.01]

    def t(validity, contrast):
        r = tr[(tr.validity == validity) & (tr.contrast == contrast)].iloc[0]
        return r.est, r.lo, r.hi

    def i(set_, contrast, va, vb, kind):
        r = ind[(ind.set == set_) & (ind.contrast == contrast) & (ind.validity_a == va) & (ind.validity_b == vb)
                & (ind.kind == kind)].iloc[0]
        return r.est, r.lo, r.hi

    rows = [
        ("rewrite − original, execution (primary, n=28)", *t("exec", "rewrite_control − original")),
        ("  all 33 pairs", *i("n33_orig_ctrl", "rewrite_control - original", "exec", "exec", "US")),
        ("  33 pairs without firewall (n=24)",
         *i("n33_orig_ctrl_nofirewall", "rewrite_control - original", "exec", "exec", "US")),
        ("  28 pairs without firewall (n=20)",
         *i("n28_track_nofirewall", "rewrite_control - original", "exec", "exec", "US")),
        ("  judge validity, originals assumed valid", *t("judge", "rewrite_control − original")),
        ("  detection only (validity ignored)",
         *i("n28_track", "rewrite_control - original", "one", "one", "detection_only")),
        ("pace_max − original, execution", *t("exec", "pace_max − original")),
        ("  validity part", *i("n28_track", "pace_max - original", "exec", "exec", "validity_part")),
        ("  detection part", *i("n28_track", "pace_max - original", "exec", "exec", "detection_part")),
        ("pace_max − rewrite, execution", *t("exec", "pace_max − rewrite_control")),
    ]
    fig, ax = plt.subplots(figsize=(6.3, 3.5))
    forest(ax, rows, "Δ undetected success (max, α = 0.01, conformal threshold)")
    ax.axhline(3.5, color=GRID, lw=0.8, ls="--")
    ax.axhline(0.5, color=GRID, lw=0.8, ls="--")
    fig.tight_layout()
    fig.savefig(OUT / "r4_replay_forest_conformal.pdf")


# ---------------------------------------------------------------- report 04
def fig_wb_primary():
    d = pd.read_csv(FX / "wb_r4primary_conformal_thrfix" / "primary.csv").set_index("contrast")
    a3 = pd.read_csv(FX / "wb_a3primary_conformal_thrfix" / "wb_primary.csv")
    a3 = a3[a3.scheme == "joint"].set_index("contrast")
    pil = pd.read_csv(FX / "wb_r4a1_conformal_thrfix" / "a1_mb_equalfpr.csv")
    pil = pil[(pil["mode"] == "none") & (pil.stream == "fibs_fu_ax") & (pil.alpha == 0.01)].iloc[0]
    rows = [
        ("Pilot, 775 attacks (200 splits)", pil.est, pil.lo, pil.hi),
        ("H1 primary (1,000 held-out attacks)", *d.loc["H1 primary", ["est", "lo", "hi"]]),
        ("H1, both monitors at exactly 1.00% FPR", *a3.loc["H1 both at realized 1.00%", ["est", "lo", "hi"]]),
        ("S1: opus-4-5 attacks (n=771)", *d.loc["S1 opus-4-5 attacks", ["est", "lo", "hi"]]),
        ("S2: opus-4-6 attacks (n=229)", *d.loc["S2 opus-4-6 attacks", ["est", "lo", "hi"]]),
        ("S3: FPR 0.05", *d.loc["S3 alpha=0.05", ["est", "lo", "hi"]]),
        ("sens.: pilot-stored honest reader scores", *d.loc["sens: pilot-stored honest reader scores",
                                                            ["est", "lo", "hi"]]),
    ]
    fig, ax = plt.subplots(figsize=(6.3, 2.8))
    n = len(rows)
    for k, (lab, e, lo, hi) in enumerate(rows):
        y = n - 1 - k
        c = INK2 if k == 0 else BLUE
        ax.plot([lo, hi], [y, y], color=c, lw=1.8, solid_capstyle="round")
        ax.plot([e], [y], "o", color=c, ms=5.5, mec="white", mew=1.2)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in rows][::-1])
    ax.set_xlabel("TPR(FIBS axial follow-up, none) − TPR(gpt-4.1-mini, none)")
    ax.grid(axis="x", color=GRID, lw=0.6)
    fig.tight_layout()
    fig.savefig(OUT / "wb_primary_conformal.pdf")


def fig_wb_la():
    nom = pd.read_csv(FX / "wb_r4la_conformal_thrfix" / "la_paired.csv")
    nom = nom[(nom["mode"] == "full") & (nom.stream == "fibs_fu_ax") & (nom.alpha == 0.01)].set_index("llm")
    eq = pd.read_csv(FX / "wb_a3la_conformal_thrfix" / "wb_la_equalfpr.csv")
    eq = eq[(eq.version == "both_2pct") & (eq.alpha == 0.01)].set_index("llm")
    order = nom.sort_values("est").index.tolist()
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.4), sharey=True)
    for ax, df, title in [(axes[0], nom, "nominal 1% (realized ≈1%)"), (axes[1], eq, "both at exactly 2.0%")]:
        df = df.loc[order]
        n = len(df)
        for k, (m, r) in enumerate(df.iterrows()):
            y = k
            c = BLUE if r.est > 0 else ORANGE
            ax.plot([r.lo, r.hi], [y, y], color=c, lw=1.8, solid_capstyle="round")
            ax.plot([r.est], [y], "o" if r.p_holm < 0.05 else "o", color=c, ms=5.5,
                    mfc=c if r.p_holm < 0.05 else "white", mew=1.3)
        ax.axvline(0, color=INK2, lw=0.8)
        ax.set_yticks(range(n))
        ax.set_yticklabels(order)
        ax.grid(axis="x", color=GRID, lw=0.6)
        ax.set_title(title, fontsize=8.5, loc="left")
        ax.set_xlabel("TPR(reader, FIBS axial f-u, full) − TPR(LLM)")
    fig.text(0.01, 0.01, "filled: Holm p < 0.05 over 12 monitors; open: not significant", fontsize=7, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "wb_la_paired_conformal.pdf")


def fig_wb_mole():
    d = pd.read_csv(FX / "wb_a3mole_conformal_thrfix" / "wb_mole.csv").set_index("contrast")
    labs = ["M1 policy − reader", "M2 policy_neutral − reader", "M3 policy − policy_neutral",
            "M4 reader − LLM (insider prompt)", "M5 policy_neutral − LLM (insider prompt)"]
    au = [d.loc[k, ["est", "lo", "hi"]].tolist() for k in
          ["M1 policy - reader", "M2 policy_neutral - reader", "M3 policy - policy_neutral",
           "M4 reader - LLM(insider)", "M5 policy_neutral - LLM(insider)"]]
    tp = [d.loc[k, ["est", "lo", "hi"]].tolist() for k in
          ["M1 tpr5", "M2 tpr5", "M3 tpr5", "M4 tpr5", "M5 tpr5"]]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.7), sharey=True)
    forest(axes[0], [(l_, *v) for l_, v in zip(labs, au)], "Δ session AUROC")
    forest(axes[1], [(l_, *v) for l_, v in zip(labs, tp)], "Δ TPR at 5% session FPR")
    axes[0].set_title("AUROC", fontsize=8.5, loc="left")
    axes[1].set_title("TPR at 5% session FPR", fontsize=8.5, loc="left")
    fig.tight_layout()
    fig.savefig(OUT / "wb_mole_conformal.pdf")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in (fig_r3_forest, fig_r4_replay, fig_wb_primary, fig_wb_la, fig_wb_mole):
        f()
        print("ok", f.__name__)


if __name__ == "__main__":
    main()
