"""Score trajectories per step with a decision-only model (Luna Decisions / hosted Decider / JEV) on the frozen
round-1 request (or its full-action variant), via the OpenRouter Decisions API. Resumable (sqlite cache).

    unset VIRTUAL_ENV
    uv run python -m tracks.r5_luna.score --model luna --set dev --dev-n 10,10 [--dry-run] [--yes]
    uv run python -m tracks.r5_luna.score --model luna --set eval --subset nano --sources mb,akshn_bash --yes
    uv run python -m tracks.r5_luna.score --model luna --set eval --subset all --sources akshn_basharena_opus46 --yes
    uv run python -m tracks.r5_luna.score --model luna --set eval --mode full --sources akshn_basharena_opus46 --yes

Sets (tracks/r5_jev/splits.json, unchanged): dev = a seeded sample of dev_honest_sample / dev_attack_sample
(--dev-n per source); eval --subset nano = MonitoringBench: every evaluation trajectory; aksh-n: the preregistered
round-1 nano subset (nano_honest + nano_attack); eval --subset all = every evaluation trajectory.
MonitoringBench is scored on its first 60 steps (as the LLM monitors were); every other source on all steps.
Full mode: steps whose full request equals the frozen one copy the frozen record (no call).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random

from tracks.r5_jev.score_jev import load
from tracks.r5_jev.splits import HERE

from . import lunalib as L

QUESTION_TOK = 320


def select_ids(spl: dict, src: str, which: str, subset: str, dev_n: tuple[int, int], seed: int = 20261023) -> set:
    d = spl[src]
    if which == "dev":
        rng = random.Random(f"{seed}:{src}")
        h, a = sorted(d["dev_honest_sample"]), sorted(d["dev_attack_sample"])
        return set(rng.sample(h, min(dev_n[0], len(h)))) | set(rng.sample(a, min(dev_n[1], len(a))))
    if subset == "nano" and src != "mb":
        return set(d["nano_honest"]) | set(d["nano_attack"])
    return set(d["eval_honest"]) | set(d["eval_attack"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(L.MODELS))
    ap.add_argument("--set", required=True, choices=["dev", "eval"])
    ap.add_argument("--subset", choices=["nano", "all"], default="nano")
    ap.add_argument("--mode", choices=["frozen", "full"], default="frozen")
    ap.add_argument("--sources")
    ap.add_argument("--dev-n", default="10,10")
    ap.add_argument("--limit-traj", type=int)
    ap.add_argument("--only-truncated", action="store_true", help="full mode: plan only steps that differ from frozen")
    ap.add_argument("--max-bytes", type=int, help="skip requests larger than this (reported)")
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--rps", type=float, default=40.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    spl = json.load(open(HERE / "splits.json"))["sources"]
    srcs = a.sources.split(",") if a.sources else ["mb"] + [s for s in spl if s.startswith("akshn_")]
    dev_n = tuple(int(x) for x in a.dev_n.split(","))
    mid = L.monitor_id(a.model, a.mode)
    price = L.PRICE_PER_TOK[a.model]
    grand, plans = 0.0, []
    for src in srcs:
        ids = select_ids(spl, src, a.set, a.subset, dev_n)
        trajs = sorted(load(src, ids), key=lambda t: t.traj_id)
        if a.limit_traj:
            trajs = trajs[:a.limit_traj]
        full = L.load_full(src) if a.mode == "full" else None
        if a.mode == "full":
            missing = [t.traj_id for t in trajs if t.traj_id not in full]
            assert not missing, f"{src}: {len(missing)} trajectories missing from the full rebuild"
        jobs = L.plan(trajs, L.MB_MAX_STEPS if src == "mb" else None, a.mode, full)
        cache = L.cache_for(a.model, src)
        todo = L.todo_jobs(jobs, cache, mid)
        n_copy = 0
        if a.mode == "full":
            fcache = L.cache_for(a.model, src)
            fmid = L.monitor_id(a.model, "frozen")
            rest = []
            for j in todo:
                if j.sha == j.frozen_sha:
                    c = fcache.get(j.traj_id, j.step, fmid)
                    if c is not None and c[1].get("sha") == j.sha:
                        cache.put(j.traj_id, j.step, mid, "ok", {**c[1], "copied_from_frozen": True})
                        n_copy += 1
                        continue
                    if a.only_truncated:
                        continue
                rest.append(j)
            todo = rest
        skipped = 0
        if a.max_bytes:
            skipped = sum(j.n_bytes > a.max_bytes for j in todo)
            todo = [j for j in todo if j.n_bytes <= a.max_bytes]
        est = sum(j.n_bytes / 3.6 + QUESTION_TOK for j in todo) * price
        grand += est
        print(f"{src:26s} trajs={len(trajs)} steps={len(jobs)} copied={n_copy} todo={len(todo)} "
              f"skipped_bytes={skipped} max_bytes={max((j.n_bytes for j in todo), default=0)} est=${est:.2f}",
              flush=True)
        plans.append((src, cache, todo))
    print(f"total est ${grand:.2f}")
    if a.dry_run:
        return
    if grand > 2 and not a.yes:
        print("re-run with --yes")
        return
    for src, cache, todo in plans:
        if not todo:
            cache.close()
            continue
        print(f"== {src}: scoring {len(todo)} steps", flush=True)
        # long requests first: their latency dominates the tail
        todo.sort(key=lambda j: -j.n_bytes)
        st = asyncio.run(L.run_jobs(todo, cache, a.model, mid, f"r5luna:{a.set}:{a.mode}:{src}",
                                    concurrency=a.concurrency, rps=a.rps))
        print(f"== {src}: done {json.dumps(st)}", flush=True)
        cache.close()


if __name__ == "__main__":
    main()
