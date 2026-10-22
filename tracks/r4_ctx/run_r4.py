"""Round-4 driver: global vs CFAR vs pooled vs Stackelberg at B in {0.5, 1, 2, 5}% with exact spend matching,
grouped three-way splits and the joint cluster bootstrap (r4lib). Design pre-specified in EXPERIMENT_LOG.md
(2026-10-22, round 4).

Raw rows (one per panel x mode x split x replicate x rule x B) go to data/processed/r4_ctx/runs/; summaries
are written by make_report.py.

    unset VIRTUAL_ENV; uv run python tracks/r4_ctx/run_r4.py [--quick] [--only panel:mode ...]
"""
from __future__ import annotations

import argparse
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import panels_r4 as P  # noqa: E402
import r4lib as X  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "data" / "processed" / "r4_ctx" / "runs"
BS = (0.005, 0.01, 0.02, 0.05)
JOBS = [  # (panel, mode)
    ("akshn_setting", "indist"), ("akshn_setting", "xfer_side"), ("akshn_setting", "xfer_policy"),
    ("akshn_setting", "indist_iid"),
    ("ca_setting_model", "indist"), ("ca_setting_model", "xfer_side"),
    ("la_pub_env", "indist"), ("la_pub_env", "xfer_side"), ("la_pub_env", "xfer_policy"),
]
TRANSFER = {"indist": None, "indist_iid": None, "xfer_side": "side_task", "xfer_policy": "policy"}

_G: dict = {}


def _init(U, splits, W):
    _G.update(U=U, splits=splits, W=W)


def _task(args):
    s, reps, Bs = args
    U, sp, W = _G["U"], _G["splits"][s], _G["W"]
    out = []
    for r in reps:
        rows = X.run_cell(U, sp, None if r < 0 else W[r], Bs, seed=1000 * s + r + 1)
        for row in rows:
            row.update(split=s, rep=r)
        out.extend(rows)
    return out


def run_job(panel: str, mode: str, S: int, R_: int, Bs, workers: int) -> pd.DataFrame:
    df = P.load(panel)
    U = X.Universe(df, iid=(mode == "indist_iid"))
    seed = zlib.crc32(f"{panel}|{mode}".encode())
    rng = np.random.default_rng(seed)
    splits = [X.make_split(U, rng, TRANSFER[mode]) for _ in range(S)]
    W = U.boot_weights(R_, np.random.default_rng(seed + 1))
    chunk = 10
    tasks = [(s, list(range(-1, 0)), Bs) for s in range(S)]
    tasks += [(s, list(range(i, min(i + chunk, R_))), Bs) for s in range(S) for i in range(0, R_, chunk)]
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(workers, initializer=_init, initargs=(U, splits, W)) as ex:
        for i, res in enumerate(ex.map(_task, tasks)):
            rows.extend(res)
    raw = pd.DataFrame(rows)
    raw.insert(0, "mode", mode)
    raw.insert(0, "panel", panel)
    # split-level sizes (for the record)
    print(f"{panel}:{mode} S={S} R={R_} rows={len(raw)} {time.time() - t0:.0f}s", flush=True)
    return raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--S", type=int, default=10)
    ap.add_argument("--R", type=int, default=200)
    ap.add_argument("--workers", type=int, default=14)
    a = ap.parse_args()
    S, R_ = (2, 4) if a.quick else (a.S, a.R)
    RUNS.mkdir(parents=True, exist_ok=True)
    jobs = JOBS if not a.only else [tuple(x.split(":")) for x in a.only]
    for panel, mode in jobs:
        raw = run_job(panel, mode, S, R_, BS, a.workers)
        tag = "_quick" if a.quick else ""
        raw.to_pickle(RUNS / f"{panel}__{mode}{tag}.pkl")


if __name__ == "__main__":
    main()
