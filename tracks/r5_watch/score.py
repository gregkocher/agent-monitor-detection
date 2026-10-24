"""Score trajectories per step with the Watcher-style GPT-5.6 Luna severity triage (track r5watch). Resumable.

    unset VIRTUAL_ENV
    uv run python -m tracks.r5_watch.score --set dev --config none_score --dev-n 10,10 --sources mb,akshn_linuxarena
    uv run python -m tracks.r5_watch.score --set eval --config <frozen> --sources mb --yes
    uv run python -m tracks.r5_watch.score --set eval --config <frozen> --sources akshn_linuxarena --yes   # nano subset

Sets (tracks/r5_jev/splits.json, unchanged): dev = the seeded dev sample of tracks.r5_luna.score.select_ids
(--dev-n per source, dev groups only); eval = MonitoringBench: every evaluation trajectory (first 60 steps); aksh-n:
the round-1 nano subset (nano_honest + nano_attack, all steps). Steps are scored in trajectory order.
"""
from __future__ import annotations

import argparse
import asyncio
import json

from tracks.r5_jev.score_jev import load
from tracks.r5_jev.splits import HERE
from tracks.r5_luna.score import select_ids

from . import watchlib as W


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["dev", "eval"])
    ap.add_argument("--config", required=True, choices=list(W.CONFIGS))
    ap.add_argument("--sources", default="mb")
    ap.add_argument("--dev-n", default="10,10")
    ap.add_argument("--retry-parse-fail", action="store_true")
    ap.add_argument("--concurrency", type=int, default=64)
    ap.add_argument("--max-usd", type=float, default=5.0, help="refuse if the projected cost of the todo exceeds this")
    ap.add_argument("--usd-per-step", type=float, default=0.0008, help="cost projection per step (from the dev pilot)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    spl = json.load(open(HERE / "splits.json"))["sources"]
    dev_n = tuple(int(x) for x in a.dev_n.split(","))
    plans, grand = [], 0.0
    for src in a.sources.split(","):
        ids = select_ids(spl, src, a.set, "nano", dev_n)
        trajs = sorted(load(src, ids), key=lambda t: t.traj_id)
        jobs = W.plan(trajs, a.config, W.MB_MAX_STEPS if src == "mb" else None)
        cache = W.cache_for(src)
        td = W.todo(jobs, cache, a.config, a.retry_parse_fail)
        est = len(td) * a.usd_per_step
        grand += est
        print(f"{src:24s} trajs={len(trajs)} steps={len(jobs)} todo={len(td)} est=${est:.2f}", flush=True)
        plans.append((src, cache, td))
    print(f"total est ${grand:.2f}")
    if a.dry_run:
        j = plans[0][2][0] if plans[0][2] else None
        if j:
            print(json.dumps(j.msgs, indent=1)[-3000:])
        return
    if grand > a.max_usd and not a.yes:
        print(f"projected ${grand:.2f} > --max-usd {a.max_usd}; re-run with --yes")
        return
    for src, cache, td in plans:
        if td:
            td.sort(key=lambda j: (j.traj.traj_id, j.step))
            st = asyncio.run(W.run_jobs(td, cache, a.config, f"r5watch:{a.set}:{a.config}:{src}", a.concurrency))
            print(f"== {src}: {json.dumps(st)}", flush=True)
        cache.close()


if __name__ == "__main__":
    main()
