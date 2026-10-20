"""Round 3 robustness checks on the Round 2 MonitoringBench streams (no API cost).

    uv run python tracks/t1_matched_budget/run_round3.py [--modes full,none] [--model openai_gpt-4.1-mini]
        [--tag robust]

Checks (each: TPR at matched FPR per mode, pooled and by structure S1-S4):
  kgrid      CUSUM reference k in {0.25, 0.5, 1.0, 1.5, 2.0}; top-k sum k in {2, 3, 5}; GLR window {5, 10, 20}
  mondrian   per-task whitening (Mondrian by task_id with partial pooling n0) for max / CUSUM / top-3 sum
  conformal  conservative conformal thresholds instead of randomized
  (score variants and --keep-submit are run with run_round2.py --score int|lpge1 / --keep-submit)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from run_round2 import load_mode, subgroup_tpr  # noqa: E402
from t1lib import run_matched  # noqa: E402

from amd.common.schema import REPO  # noqa: E402
from amd.detectors import CUSUM, KthLargest, Max, MultiChart, TopKSum, WindowGLR, Whiten  # noqa: E402

OUT = REPO / "results" / "t1" / "round3"


def kgrid():
    d = {"max": Max(), "kth2": KthLargest(2)}
    for k in (0.25, 0.5, 1.0, 1.5, 2.0):
        c = CUSUM(k=k, transform=Whiten()); c.name = f"cusum_k{k:g}"; d[c.name] = c
    for k in (2, 3, 5):
        t = TopKSum(k, transform=Whiten()); t.name = f"top{k}sum"; d[t.name] = t
    for w in (5, 10, 20):
        g = WindowGLR(window=w, transform=Whiten()); g.name = f"glr_w{w}"; d[g.name] = g
    d["or(max+cusum_k1)"] = MultiChart([Max(), CUSUM(k=1.0, transform=Whiten())], name="or(max+cusum_k1)", tail="exp")
    return d


def mondrian(n0=20, min_n=30):
    d = {}
    for name, det in (("max_task", Max(transform=Whiten(mondrian=True, min_n=min_n, n0=n0))),
                      ("cusum_k0.5_task", CUSUM(k=0.5, transform=Whiten(mondrian=True, min_n=min_n, n0=n0))),
                      ("top3sum_task", TopKSum(3, transform=Whiten(mondrian=True, min_n=min_n, n0=n0)))):
        det.name = name
        d[name] = det
    d["max"] = Max()
    c = CUSUM(k=0.5, transform=Whiten()); d["cusum_k0.5"] = c
    t = TopKSum(3, transform=Whiten()); d["top3sum"] = t
    return d


def run(ss, dets, contexts=None, method="randomized", alphas=(0.05, 0.01, 0.003)):
    from amd.evaluation import matched_budget_eval
    df, raw = matched_budget_eval(dets, ss.honest, ss.attack, alphas=alphas, honest_contexts=contexts[0] if contexts else None,
                                  attack_contexts=contexts[1] if contexts else None,
                                  honest_groups=ss.honest_groups, attack_groups=ss.attack_groups, group_split=True,
                                  n_splits=10, n_boot=200, cluster_bootstrap=True, method=method, seed=0,
                                  return_raw=True)
    struct = np.array([x["structure"] or "NA" for x in ss.attack_meta])
    rows = []
    for a in alphas:
        sg, _, _ = subgroup_tpr(raw, struct, a, method=method)
        sgp, _, _ = subgroup_tpr(raw, np.array(["all"] * ss.n_a), a, method=method)
        rows += [sg, sgp]
    return df, pd.concat(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", default="full,none")
    ap.add_argument("--model", default="openai_gpt-4.1-mini")
    ap.add_argument("--tag", default="robust")
    ap.add_argument("--checks", default="kgrid,mondrian,conformal")
    a = ap.parse_args()
    out = OUT / a.tag
    out.mkdir(parents=True, exist_ok=True)
    for mode in a.modes.split(","):
        ss = load_mode(mode, model=a.model)
        for check in a.checks.split(","):
            if check == "kgrid":
                df, sg = run(ss, kgrid())
            elif check == "mondrian":
                ctx = ([str(g) for g in ss.honest_groups], [str(g) for g in ss.attack_groups])
                df, sg = run(ss, mondrian(), contexts=ctx)
            elif check == "conformal":
                from t1lib import t1_suite
                dets = {k: v for k, v in t1_suite().items()
                        if k in ("max", "kth2", "top3sum", "cusum_k0.5", "glr_w20", "eproc_power", "or(max+cusum)")}
                df, sg = run(ss, dets, method="conformal")
            else:
                raise ValueError(check)
            df["mode"], sg["mode"], df["check"], sg["check"] = mode, mode, check, check
            df.to_csv(out / f"matched_{check}_{mode}.csv", index=False)
            sg.to_csv(out / f"tpr_by_structure_{check}_{mode}.csv", index=False)
            print(mode, check, "done", flush=True)


if __name__ == "__main__":
    main()
