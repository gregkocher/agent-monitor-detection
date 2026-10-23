"""Audit pass 3: H1-AK (pooled aksh-n, JEV cascade e = 20% vs Gemini only, 1% FPR) with B = 2,000 replicates,
original grouping vs main-task cluster bootstrap (same preregistered splits), so that the non-inferiority p-value
and its Holm adjustment are not limited by replicate resolution. Independent implementation (jev_indep.py).

    unset VIRTUAL_ENV; uv run python -m tracks.audit3.jev_h1ak_task [--splits 20] [--boot 2000]

Output results/audit3/jev_h1ak_task.csv.
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from amd.common.schema import REPO
from tracks.r5_jev import panels as PN
from tracks.r5_jev.splits import AKSHN

from .jev_indep import run, summ, task_groups, tpr

OUT = REPO / "results" / "audit3"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=int, default=20)
    ap.add_argument("--boot", type=int, default=2000)
    A = ap.parse_args()
    variant, scheme = json.load(open(REPO / "results/r5_jev/dev_choice.json")).values()
    cfg = [("plain", "llm"), ("casc", "jev", 0.2)]
    RA, RT = [], []
    for i, src in enumerate(AKSHN):
        if src == "akshn_basharena_sonnet45":      # preregistered 1% exclusion (calibration n < 200)
            continue
        P = PN.load_akshn(src, variant, scheme)
        th, ta = task_groups(P, src)
        RA.append(run(P, cfg, A.splits, A.boot, 500 + i, alphas=(0.01,)))
        RT.append(run(P, cfg, A.splits, A.boot, 500 + i, alphas=(0.01,), hg=th, ag=ta, joint=True))
        print("done", src, flush=True)
    rows = []
    for tag, R in (("orig_grouping", RA), ("task_joint", RT)):
        d = tpr(R, cfg[1], 0.01) - tpr(R, cfg[0], 0.01)
        rows.append(dict(variant=tag, hypothesis="H1-AK", B=A.boot, S=A.splits, **summ(d)))
        de = tpr(R, cfg[1], 0.01, "equal") - tpr(R, cfg[0], 0.01, "equal")
        rows.append(dict(variant=tag, hypothesis="H1-AK equal-weight settings", B=A.boot, S=A.splits, **summ(de)))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "jev_h1ak_task.csv", index=False)
    print(df.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
