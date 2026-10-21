"""Round-2 persistent-state analysis: does the history-free cross-session accumulation gain replicate across
monitor families and attack types, and does it vanish in the history-aware mode?

    uv run python tracks/r2_t1/ps_analysis.py [--splits 20] [--boot 300]

Per (monitor, history mode, attack policy): matched-budget TPR at trajectory (run-level) FPR alpha in
{0.05, 0.01} for the r2 suite (r2lib.suite), randomized thresholds, 5-fold cross-fitting, 50/50 honest splits
(iid: only 5 apps), bootstrap CIs incl. calibration noise; paired gains over max (attack bootstrap); the
paired difference-in-differences of the gain between current_only and full_diffs on the same runs; streaming
delay for positional attacks (onset = target PR). Writes results/r2_t1/ps_*.csv, ps_tables.md, PDFs.
"""
from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from ps_sets import r2_ps_sets  # noqa: E402
from r2lib import COLORS, LABEL, gains_table, mpl_style, paired_did, run_matched, suite  # noqa: E402

from amd.common.schema import REPO  # noqa: E402

OUT = REPO / "results" / "r2_t1"
RAW = REPO / "data" / "raw" / "r2_t1" / "ps_raw"
ALPHAS = (0.05, 0.01)
KEY = ["kth2", "top2sum", "top3sum", "mean", "cusum_k0.5", "cusum_k1.5", "cusum_k2", "sr_d1", "eproc_power"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=int, default=20)
    ap.add_argument("--boot", type=int, default=300)
    ap.add_argument("--score", default="expected")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    sets = r2_ps_sets(score=a.score)
    dets = suite()
    matched, gains, raws = [], [], {}
    for ss in sets:
        df, raw = run_matched(ss, detectors=dets, alphas=ALPHAS, n_splits=a.splits, n_boot=a.boot,
                              return_raw=True, seed=0)
        matched.append(df)
        gains.append(gains_table(ss, raw, ALPHAS, list(dets)))
        raws[ss.name] = raw
        print(f"  {ss.name}: n_h={ss.n_h} n_a={ss.n_a}", flush=True)
    tag = "" if a.score == "expected" else f"_{a.score}"
    M = pd.concat(matched); G = pd.concat(gains)
    (RAW / f"raws{tag}.pkl").write_bytes(pickle.dumps(raws))
    M.to_csv(OUT / f"ps_matched{tag}.csv", index=False)
    G.to_csv(OUT / f"ps_gains{tag}.csv", index=False)

    # DiD current_only - full_diffs (paired on runs)
    did = []
    for name in raws:
        p = name.split(":")
        if p[2] != "current_only":
            continue
        other = ":".join([p[0], p[1], "full_diffs", p[3]])
        if other not in raws:
            continue
        for al in ALPHAS:
            for d in KEY:
                e, lo, hi = paired_did(raws[name], raws[other], al, d)
                did.append(dict(monitor=p[1], policy=p[3], alpha=al, detector=d, did_none_minus_full=e,
                                lo=lo, hi=hi))
    DD = pd.DataFrame(did)
    DD.to_csv(OUT / f"ps_did{tag}.csv", index=False)

    # markdown tables
    lines = [f"# Persistent-state cross-session accumulation (round 2{', ' + a.score + ' scores' if tag else ''})", ""]
    for al in ALPHAS:
        lines.append(f"## TPR at run-level FPR {al} (95% CI)\n")
        sub = M[(M.alpha == al) & (M.threshold_kind == "calibrated")] if "threshold_kind" in M else M[M.alpha == al]
        cols = ["max"] + KEY
        lines.append("| set | n_h/n_a | realized FPR (max) | " + " | ".join(LABEL.get(c, c) for c in cols) + " |")
        lines.append("|" + "---|" * (len(cols) + 3))
        for s, g in sub.groupby("set", sort=False):
            g = g.set_index("detector")
            best = g.loc[cols].tpr.idxmax()
            cells = []
            for c in cols:
                if c not in g.index:
                    cells.append("")
                    continue
                v = f"{g.loc[c].tpr:.2f} [{g.loc[c].tpr_lo:.2f}, {g.loc[c].tpr_hi:.2f}]"
                cells.append(f"**{v}**" if c == best else v)
            lines.append(f"| {s} | {int(g.n_honest_total.iloc[0])}/{int(g.n_attack_total.iloc[0])} | "
                         f"{g.loc['max'].fpr:.3f} | " + " | ".join(cells) + " |")
        lines.append("")
        lines.append(f"### Paired gain over max at FPR {al} (attack bootstrap, 95% CI)\n")
        gg = G[(G.alpha == al) & G.detector.isin(KEY)]
        piv = gg.assign(cell=gg.apply(lambda r: f"{r.gain_vs_max:+.3f} [{r.lo:+.2f}, {r.hi:+.2f}]", axis=1))
        piv = piv.pivot(index="set", columns="detector", values="cell")[KEY].reindex(sub.set.unique())
        lines.append("| set | " + " | ".join(LABEL.get(c, c) for c in KEY) + " |")
        lines.append("|" + "---|" * (len(KEY) + 1))
        for s, r in piv.iterrows():
            lines.append(f"| {s} | " + " | ".join(str(x) for x in r.to_numpy()) + " |")
        lines.append("")
    lines.append("## Difference-in-differences: gain over max (current_only) - gain over max (full_diffs)\n")
    lines.append("| monitor | policy | alpha | " + " | ".join(LABEL.get(c, c) for c in KEY) + " |")
    lines.append("|" + "---|" * (len(KEY) + 3))
    for (mon, pol, al), g in DD.groupby(["monitor", "policy", "alpha"], sort=False):
        g = g.set_index("detector")
        lines.append(f"| {mon} | {pol} | {al} | " + " | ".join(
            f"{g.loc[c].did_none_minus_full:+.3f} [{g.loc[c].lo:+.2f}, {g.loc[c].hi:+.2f}]" for c in KEY) + " |")
    (OUT / f"ps_tables{tag}.md").write_text("\n".join(lines) + "\n")

    # figure: rows = attack policy, columns = detector, y = monitor; two points (history-free / -aware)
    plt = mpl_style()
    show = ["top3sum", "sr_d1", "eproc_power", "kth2"]
    mons = list(dict.fromkeys(n.split(":")[1] for n in raws))
    for al in ALPHAS:
        fig, axes = plt.subplots(2, len(show), figsize=(7.4, 4.4), sharex=True, sharey=True)
        for i, pol in enumerate(("gradual", "positional")):
            for j, det in enumerate(show):
                ax = axes[i, j]
                for k, mode in enumerate(("current_only", "full_diffs")):
                    for y, mon in enumerate(mons):
                        g = G[(G.alpha == al) & (G.set == f"ps2:{mon}:{mode}:{pol}") & (G.detector == det)]
                        if g.empty:
                            continue
                        r = g.iloc[0]
                        ax.errorbar(r.gain_vs_max, y + (0.15 if k == 0 else -0.15),
                                    xerr=[[r.gain_vs_max - r.lo], [r.hi - r.gain_vs_max]], fmt="o", ms=3.5, lw=1,
                                    color="#1baf7a" if k == 0 else "#7d2a63",
                                    label=(("current PR only (history-free)" if k == 0 else
                                            "all prior diffs (history-aware)") if y == 0 else None))
                ax.axvline(0, color="#999", lw=0.8)
                short = {"gpt-4o-orig": "gpt-4o (orig.)", "qwen3-235b-a22b-2507": "qwen3-235b"}
                ax.set_yticks(range(len(mons)), [short.get(m, m) for m in mons])
                ax.set_title(f"{pol}: {LABEL[det]}", loc="left", fontsize=8)
                if i == 1:
                    ax.set_xlabel("TPR gain over max", fontsize=7.5)
        h, l = axes[0, 0].get_legend_handles_labels()
        fig.legend(h, l, frameon=False, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.0),
                   title=f"run-level FPR {al}; 95% CI: paired attack bootstrap", title_fontsize=7)
        fig.tight_layout(rect=(0, 0.06, 1, 1))
        fig.savefig(OUT / f"fig_ps_gain_alpha{al}{tag}.pdf")
    print((OUT / f"ps_tables{tag}.md").read_text()[:6000])


if __name__ == "__main__":
    main()
