"""Numerical check (pod): do the incremental (cached, chunked) reader passes give the same per-step pooled
features as plain single forward passes? bf16 kernels make individual deep-layer tokens chunk-boundary
sensitive, so this checks that pooled step features — what every analysis uses — are unaffected.

For N MonitoringBench trajectories (half honest, half attack): full mode = one forward over prefix + all
steps, features sliced per step; none mode = one forward of prefix + step per step (no cache). Compared
with the production values in out/mb_{mode}.jsonl: Pearson r, median / max absolute difference relative to
the honest per-step SD, and agreement of the trajectory max.

    python pod_check.py --n 24
"""
from __future__ import annotations

import argparse
import json

import numpy as np

import pod_reader as PR

KEYS = ["sab_L43_mean", "sab_L19_mean", "sab_L58_mean", "fibs_L35_mean", "dec_L27_mean", "jl_L35_lm_mean",
        "sab_L43_max", "jl_L43_lm_max"]


def main(n):
    rd = PR.Reader()
    rd.set_probes(f"{PR.WORK}/probes.pt")
    recs = [json.loads(l) for l in open(f"{PR.WORK}/inputs/mb.jsonl")]
    rng = np.random.default_rng(0)
    hon = [r for r in recs if r["label"] == "honest"]
    att = [r for r in recs if r["label"] == "attack"]
    pick = [hon[i] for i in rng.choice(len(hon), n // 2, replace=False)] + \
           [att[i] for i in rng.choice(len(att), n // 2, replace=False)]
    out = {}
    for mode in ("full", "none"):
        prod = {}
        for l in open(f"{PR.WORK}/out/mb_{mode}.jsonl"):
            d = json.loads(l)
            prod[d["traj_id"]] = d["feats"]
        A, B = {k: [] for k in KEYS}, {k: [] for k in KEYS}
        tmaxA, tmaxB = [], []
        for r in pick:
            if r["traj_id"] not in prod:
                continue
            pre = rd.ids(r[f"prefix_{mode}"])
            steps = [rd.ids(s) for s in r["steps"]]
            vals = []
            if mode == "full":
                ids = pre + sum(steps, [])
                rd.fwd(ids)
                caps = dict(rd.caps)
                pos = len(pre)
                for s in steps:
                    rd.caps = {l: v[:, : pos + len(s)] for l, v in caps.items()}
                    vals.append(PR.step_record(rd, len(s)))
                    pos += len(s)
            else:
                for s in steps:
                    rd.fwd(pre + s)
                    vals.append(PR.step_record(rd, len(s)))
            for k in KEYS:
                A[k] += list(prod[r["traj_id"]][k])
                B[k] += [v[k] for v in vals]
            tmaxA.append(max(prod[r["traj_id"]]["sab_L43_mean"]))
            tmaxB.append(max(v["sab_L43_mean"] for v in vals))
        res = {}
        for k in KEYS:
            a, b = np.array(A[k]), np.array(B[k])
            sd = np.std(a) + 1e-9
            res[k] = dict(n=len(a), pearson=float(np.corrcoef(a, b)[0, 1]),
                          med_abs_diff_sd=float(np.median(np.abs(a - b)) / sd), max_abs_diff_sd=float(np.max(np.abs(a - b)) / sd))
        res["traj_max_sab_L43_pearson"] = float(np.corrcoef(tmaxA, tmaxB)[0, 1])
        out[mode] = res
        print(mode, json.dumps(res, indent=1), flush=True)
    json.dump(out, open(f"{PR.WORK}/out/numerical_check.json", "w"), indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=24)
    main(ap.parse_args().n)
