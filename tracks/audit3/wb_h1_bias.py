"""Audit pass 3 (r4_wb Part 1): bootstrap-bias diagnostic for H1 / S3 on the held-out data (independent code).
Reports bootstrap mean - point estimate and basic (pivotal) intervals next to the percentile intervals, for the
independent-cluster and joint-cluster schemes. Output results/audit3/wb_h1_bias.csv.

    unset VIRTUAL_ENV; uv run python -m tracks.audit3.wb_h1_bias
"""
import glob
import json

import numpy as np
import pandas as pd

from .wb_lib import boot_weights, contrast, halves
from .wb_primary import P, R4, llm, reader, traj_meta


def main():
    held = json.load(open("tracks/r4_wb/heldout.json"))
    S = json.load(open("tracks/t1_matched_budget/sample.json"))
    MA, MH = traj_meta("monitoringbench"), traj_meta("mb_honest")
    Rn = reader(sorted(glob.glob(f"{R4}/mbr4_none_s*.jsonl")))
    Lh = llm(f"{P}/mb_honest/scores_openai_gpt-4.1-mini_none.jsonl", MH)
    La = llm(f"{P}/monitoringbench/r4wb_scores_openai_gpt-4.1-mini_none_prereg_snapshot.jsonl", MA)
    hid = [t for t in S["honest"] if t in Rn and t in Lh]
    aid = [t for t in held["attack"] if t in Rn and t in La]
    hg = np.array([MH[t]["task"] for t in hid]); ag = np.array([MA[t]["task"] for t in aid])
    H = {"r": np.array([Rn[t][0] for t in hid]), "l": np.array([Lh[t][0] for t in hid])}
    A = {"r": np.array([Rn[t][0] for t in aid]), "l": np.array([La[t][0] for t in aid])}
    masks = halves(hg, 200, np.random.default_rng(12345))
    rows = []
    for scheme in ("indep", "joint"):
        Wh, Wa = boot_weights(hg, ag, 2000, np.random.default_rng(777), scheme)
        for alpha in (0.01, 0.05):
            r = contrast(H, A, [(1.0, "r"), (-1.0, "l")], masks, alpha, Wh, Wa)
            b = r["boot"]
            rows.append(dict(scheme=scheme, alpha=alpha, est=r["est"], pct_lo=r["lo"], pct_hi=r["hi"],
                             boot_mean_minus_est=float(b.mean() - r["est"]), boot_median_minus_est=float(np.median(b) - r["est"]),
                             basic_lo=float(2 * r["est"] - np.quantile(b, .975)),
                             basic_hi=float(2 * r["est"] - np.quantile(b, .025)), se=r["se"]))
            print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv("results/audit3/wb_h1_bias.csv", index=False)


if __name__ == "__main__":
    main()
