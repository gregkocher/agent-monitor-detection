"""Environment agreement: honest trajectories re-scored on the round-4 pods vs the pilot-stored streams.

Only HONEST trajectories are compared (no attack scores are looked at). For each stream: Pearson r of
per-step values, r of per-trajectory maxima, median |diff| of maxima in units of the honest per-trajectory-max
SD, and the share of trajectories whose max differs by more than 0.1 SD.

    unset VIRTUAL_ENV; uv run python -m tracks.r4_wb.check_agreement --new data/processed/whitebox/scores/r4/mbr4_none*.jsonl --old mb_none
"""
from __future__ import annotations

import argparse
import glob
import json

import numpy as np
import pandas as pd

from amd.common.schema import REPO, read_jsonl
from tracks.wb_whitebox.wblib import WB, derived

STREAMS = ["fibs_fu_ax", "fibs_fu", "sab", "sab_max", "dec", "fibs_tok", "jl_lm", "jl_hits"]


def load(paths, honest_ids=None):
    out = {}
    for p in paths:
        for d in read_jsonl(p):
            if d["n_steps"] == 0 or (honest_ids is not None and d["traj_id"] not in honest_ids):
                continue
            out[d["traj_id"]] = derived(d["feats"])
    return out


def compare(new, old, tag):
    ids = sorted(set(new) & set(old))
    rows = []
    for st in STREAMS:
        if st not in new[ids[0]] or st not in old[ids[0]]:
            continue
        a = np.concatenate([np.asarray(new[t][st], float) for t in ids])
        b = np.concatenate([np.asarray(old[t][st], float) for t in ids])
        ma = np.array([np.nanmax(new[t][st]) for t in ids])
        mb = np.array([np.nanmax(old[t][st]) for t in ids])
        sd = np.nanstd(mb)
        d = np.abs(ma - mb) / sd
        rows.append(dict(set=tag, stream=st, n_traj=len(ids), r_step=np.corrcoef(a, b)[0, 1],
                         r_max=np.corrcoef(ma, mb)[0, 1], med_absdiff_max_sd=np.median(d),
                         p95_absdiff_max_sd=np.quantile(d, 0.95), share_gt_0p1sd=float((d > 0.1).mean())))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", nargs="+", required=True)
    ap.add_argument("--old", required=True, help="pilot stored source_mode, e.g. mb_none")
    ap.add_argument("--tag", default="")
    ap.add_argument("--out")
    a = ap.parse_args()
    hon = {json.loads(l)["traj_id"] for l in open(REPO / "data/processed/mb_honest/trajectories.jsonl")}
    new = load(sum((glob.glob(p) for p in a.new), []), hon)
    old = load([WB / "scores" / f"{a.old}.jsonl"], hon)
    df = compare(new, old, a.tag or a.old)
    print(df.round(4).to_string())
    if a.out:
        df.to_csv(a.out, index=False)


if __name__ == "__main__":
    main()
