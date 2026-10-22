"""Score trajectories per step with JEV (typesafe/jev-1.14) via the OpenRouter Decisions API.

    unset VIRTUAL_ENV
    uv run python -m tracks.r5_jev.score_jev --set dev --variant A_w3 --track r5dev [--dry-run] [--yes]
    uv run python -m tracks.r5_jev.score_jev --set eval --variant <frozen> --track r5jev --sources mb,akshn_bash

Sets (tracks/r5_jev/splits.json): dev = dev_honest_sample + dev_attack_sample; eval = eval_honest + eval_attack.
MonitoringBench is scored on its first 60 steps (as the LLM monitors were); every other source on all steps.
"""
from __future__ import annotations

import argparse
import asyncio
import json

from amd.common.schema import PROCESSED, Trajectory, read_jsonl

from . import jevlib as J
from .splits import HERE

PRICE_PER_TOK = 0.042e-6
QUESTION_TOK = 320  # measured overhead of the two Choice questions + template, approx.
MB_MAX_STEPS = 60


def load(src: str, ids: set[str]) -> list[Trajectory]:
    files = ["mb_honest", "monitoringbench"] if src == "mb" else [src]
    out = []
    for f in files:
        for d in read_jsonl(PROCESSED / f / "trajectories.jsonl"):
            if d["traj_id"] in ids:
                out.append(Trajectory(**d))
    return out


def ids_for(spl: dict, which: str) -> set[str]:
    if which == "dev":
        return set(spl["dev_honest_sample"]) | set(spl["dev_attack_sample"])
    if which == "eval":
        return set(spl["eval_honest"]) | set(spl["eval_attack"])
    raise ValueError(which)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["dev", "eval"])
    ap.add_argument("--variant", required=True, choices=list(J.VARIANTS))
    ap.add_argument("--track", required=True, choices=["r5dev", "r5jev"])
    ap.add_argument("--sources")
    ap.add_argument("--limit-traj", type=int)
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--rps", type=float, default=40.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    splits = json.load(open(HERE / "splits.json"))["sources"]
    srcs = a.sources.split(",") if a.sources else list(splits)
    mid = J.monitor_id(a.variant)
    grand = 0.0
    plans = []
    for src in srcs:
        ids = ids_for(splits[src], a.set)
        trajs = sorted(load(src, ids), key=lambda t: t.traj_id)
        if a.limit_traj:
            trajs = trajs[:a.limit_traj]
        jobs = J.plan(trajs, a.variant, MB_MAX_STEPS if src == "mb" else None)
        cache = J.cache_for(src)
        todo = J.todo_jobs(jobs, cache, mid)
        est = sum(j.n_bytes / 3.6 + QUESTION_TOK for j in todo) * PRICE_PER_TOK
        grand += est
        print(f"{src:26s} trajs={len(trajs)} steps={len(jobs)} todo={len(todo)} est=${est:.2f}", flush=True)
        plans.append((src, cache, todo))
    print(f"total est ${grand:.2f}")
    if a.dry_run:
        if plans and plans[0][2]:
            print(json.dumps(plans[0][2][0].req, indent=1)[:4000])
        return
    if grand > 2 and not a.yes:
        print("re-run with --yes")
        return
    for src, cache, todo in plans:
        if not todo:
            continue
        print(f"== {src}: scoring {len(todo)} steps", flush=True)
        st = asyncio.run(J.run_jobs(todo, cache, mid, a.track, f"r5:{a.set}:{src}:{a.variant}",
                                    concurrency=a.concurrency, rps=a.rps))
        print(f"== {src}: done {st}", flush=True)
        cache.close()


if __name__ == "__main__":
    main()
