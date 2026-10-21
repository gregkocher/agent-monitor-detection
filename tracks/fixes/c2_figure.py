"""Figure + table for C2: headline gain-over-max estimates with the original (too narrow) and corrected CIs.

    unset VIRTUAL_ENV; uv run python tracks/fixes/c2_figure.py
Writes results/fixes/t1/fig_c2_headline_cis.pdf and results/fixes/t1/c2_headline.md (reads the *_corrected.csv).
"""
from __future__ import annotations

import matplotlib

matplotlib.use("pdf")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from amd.common.schema import REPO  # noqa: E402

F = REPO / "results" / "fixes"


def rows():
    r1 = pd.read_csv(F / "t1" / "gains_r1_corrected.csv")
    g2 = pd.read_csv(F / "t1" / "gains_r2mb_corrected.csv")
    d2 = pd.read_csv(F / "t1" / "did_r2mb_corrected.csv")
    ps = pd.read_csv(F / "r2_t1" / "ps_gains_corrected.csv")
    pd_ = pd.read_csv(F / "r2_t1" / "ps_did_corrected.csv")
    mo = pd.read_csv(F / "r2_t1" / "mole_gains_corrected.csv")
    out = []

    def add(label, r):
        out.append(dict(label=label, est=r.est, lo=r.lo, hi=r.hi, old_lo=r.old_lo, old_hi=r.old_hi,
                        p_le0=r.p_le0))
    q = lambda df, **kw: df.loc[(df[list(kw)] == pd.Series(kw)).all(axis=1)].iloc[0]  # noqa: E731
    add("T1 r1 PS GPT-4o top-3 sum (FPR .05)", q(r1, set_file="ps__diff_current_only__gradual", alpha=0.05, detector="top3sum"))
    add("T1 r1 PS GPT-4o CUSUM k=.5 (FPR .05)", q(r1, set_file="ps__diff_current_only__gradual", alpha=0.05, detector="cusum_k0.5"))
    add("T1 r2 MB full top-3 sum (FPR .01)", q(g2, tag="main", mode="full", alpha=0.01, group="all", detector="top3sum"))
    add("T1 r2 MB DiD CUSUM k=.5 (FPR .01)", q(d2, tag="main", alpha=0.01, group="all", detector="cusum_k0.5"))
    add("T1 r2 MB DiD top-3 sum (FPR .05)", q(d2, tag="main", alpha=0.05, group="all", detector="top3sum"))
    for m, lab in (("gpt-4.1-mini", "gpt-4.1-mini"), ("gpt-4o-orig", "GPT-4o"), ("gemini-2.5-flash", "Gemini 2.5 Flash"),
                   ("qwen3-235b-a22b-2507", "Qwen3-235B")):
        add(f"r2 PS {lab} top-3 sum (FPR .05)", q(ps, set=f"ps2:{m}:current_only:gradual", alpha=0.05, detector="top3sum"))
    for m, lab in (("gpt-4o-orig", "GPT-4o"), ("qwen3-235b-a22b-2507", "Qwen3-235B"), ("gpt-4.1-mini", "gpt-4.1-mini")):
        add(f"r2 PS DiD {lab} top-3 sum (FPR .05)", q(pd_, monitor=m, policy="gradual", alpha=0.05, detector="top3sum"))
    add("MOLE gpt53 LLM 3rd-max (FPR .10)", q(mo, set="mole:single_day:llm", alpha=0.10, detector="kth3"))
    add("MOLE gpt53 peer-fit 3rd-max (FPR .10)", q(mo, set="mole:single_day:peer_fit", alpha=0.10, detector="kth3"))
    return pd.DataFrame(out)


def main():
    D = rows()
    plt.rcParams.update({"font.size": 8, "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    y = range(len(D))[::-1]
    for yy, (_, r) in zip(y, D.iterrows()):
        ax.plot([r.old_lo, r.old_hi], [yy + 0.16] * 2, color="#b0b0b0", lw=2.2, solid_capstyle="butt")
        ax.plot([r.lo, r.hi], [yy - 0.16] * 2, color="#2a78d6", lw=1.4)
        ax.plot(r.est, yy, "o", color="#1a1a1a", ms=3.5, zorder=3)
    ax.axvline(0, color="#999", lw=0.8)
    ax.set_yticks(list(y), D.label)
    ax.set_xlabel("TPR gain (or DiD of gains) over max")
    ax.plot([], [], color="#b0b0b0", lw=2.2, label="original CI (new attack indices per split, averaged; no calibration noise)")
    ax.plot([], [], color="#2a78d6", lw=1.4, label="corrected CI (one joint resample per replicate, calibration noise, task clusters)")
    ax.legend(frameon=False, fontsize=6.5, loc="lower left", bbox_to_anchor=(0, 1.0))
    fig.tight_layout()
    fig.savefig(F / "t1" / "fig_c2_headline_cis.pdf")
    md = ["# C2: headline gains over max, original vs corrected 95% CIs", "",
          "| quantity | estimate | original CI | corrected CI | p(<=0) |", "|---|---|---|---|---|"]
    md += [f"| {r.label} | {r.est:+.3f} | [{r.old_lo:+.3f}, {r.old_hi:+.3f}] | [{r.lo:+.3f}, {r.hi:+.3f}] | {r.p_le0:.3f} |"
           for _, r in D.iterrows()]
    (F / "t1" / "c2_headline.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
