"""Audit pass 3: r5jev MonitoringBench secondary cells at EQUAL realized test FPR.

    unset VIRTUAL_ENV; uv run python -m tracks.audit3.jev_equalfpr [--splits 20] [--boot 300]

At nominal 5% the JEV / probe cascades at e = 5-10% run at realized test FPR 6.3-6.5% vs 5.8% for mini-only (and
standalone JEV at 1% runs at 2.4% vs 1.5%; JEV probabilities are rounded to 0.01, so its trajectory max ties).
For each configuration we sweep the nominal level and pick the one whose split-mean realized test FPR is closest to
mini-only's at the nominal level, then recompute the contrast vs mini-only (same seed => same splits and
bootstrap replicates).
Uses the independent implementation in tracks/audit3/jev_indep.py. Output results/audit3/jev_equalfpr.csv.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from amd.common.schema import REPO
from tracks.r5_jev import panels as PN

from .jev_indep import run, tpr

OUT = REPO / "results" / "audit3"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=int, default=20)
    ap.add_argument("--boot", type=int, default=300)
    A = ap.parse_args()
    variant, scheme = json.load(open(REPO / "results/r5_jev/dev_choice.json")).values()
    mb = PN.load_mb(variant, scheme)
    cfgs = [("plain", "jev"), ("casc", "jev", 0.05), ("casc", "jev", 0.1), ("casc", "probe", 0.05)]
    rows = []
    for a0, grid in ((0.01, np.round(np.arange(0.002, 0.0121, 0.0005), 4)),
                     (0.05, np.round(np.arange(0.030, 0.0501, 0.001), 4))):
        base = run(mb, [("plain", "llm")], A.splits, A.boot, 101, alphas=(a0,))
        target = np.mean(base[("plain", "llm")][a0]["fpr"])
        tb = tpr([base], ("plain", "llm"), a0)
        G = run(mb, cfgs, A.splits, A.boot, 101, alphas=tuple(grid) + (a0,))
        for c in cfgs:
            fr = np.array([np.mean(G[c][a]["fpr"]) for a in grid])
            k = int(np.argmin(np.abs(fr - target)))
            for tag, a in (("nominal", a0), ("equal_realized_fpr", grid[k])):
                d = tpr([G], c, a) - tb
                rows.append(dict(alpha_nominal=a0, config=str(c), kind=tag, alpha_used=a,
                                 fpr_config=np.mean(G[c][a]["fpr"]), fpr_mini=target, tpr=tpr([G], c, a)[0],
                                 tpr_mini=tb[0], d=d[0], d_lo=np.quantile(d[1:], .025), d_hi=np.quantile(d[1:], .975)))
        print(pd.DataFrame(rows).round(4).to_string(index=False), flush=True)
    pd.DataFrame(rows).to_csv(OUT / "jev_equalfpr.csv", index=False)


if __name__ == "__main__":
    main()
