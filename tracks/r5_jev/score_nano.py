"""gpt-4.1-nano per-step first stage (`ctrl-basic-v1`, history `none`: the same per-step prompt as the cached
gpt-4.1-mini `none` monitor), track r5jev. Thin wrapper around amd.scoring.run.

Sets (tracks/r5_jev/splits.json):
  mb     : every MonitoringBench evaluation trajectory (first 60 steps; cached nano steps of the T1 sample are reused)
  akshn  : the preregistered nano subset of each aksh-n setting (nano_honest + nano_attack), all steps

Writes data/processed/<source>/r5_scores_openai_gpt-4.1-nano_none.jsonl (MonitoringBench: honest and attacks are
written to mb_honest/ and monitoringbench/ respectively).

    unset VIRTUAL_ENV; uv run python -m tracks.r5_jev.score_nano --set mb [--dry-run] [--yes]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math

from amd.common.schema import PROCESSED, write_jsonl
from amd.scoring import run as R
from amd.scoring.cache import ScoreCache
from amd.scoring.prompts import PromptConfig

from .splits import AKSHN, HERE

MODEL = "openai/gpt-4.1-nano"
OUT_NAME = "r5_scores_openai_gpt-4.1-nano_none.jsonl"


def targets(which: str, spl: dict):
    if which == "mb":
        ids = set(spl["mb"]["eval_honest"]) | set(spl["mb"]["eval_attack"])
        return [("mb_honest", ids, 60), ("monitoringbench", ids, 60)]
    return [(s, set(spl[s]["nano_honest"]) | set(spl[s]["nano_attack"]), 10_000) for s in AKSHN]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["mb", "akshn"])
    ap.add_argument("--sources")
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    spl = json.load(open(HERE / "splits.json"))["sources"]
    cfg = PromptConfig(history="none")
    mid = cfg.monitor_id(MODEL)
    price = R.get_price(MODEL) or R.FALLBACK_PRICES[MODEL]
    plans, grand = [], 0.0
    for src, ids, max_steps in targets(a.set, spl):
        if a.sources and src not in a.sources.split(","):
            continue
        trajs = [t for t in R.load_source(src) if t.traj_id in ids]
        jobs = R.plan(trajs, cfg, max_steps)
        cache = ScoreCache(PROCESSED / src / "score_cache.sqlite")
        todo = [j for j in jobs if (c := cache.get(j.traj.traj_id, j.step, mid)) is None
                or c[1].get("prompt_sha") != j.sha]
        est = sum(j.info["prompt_chars"] for j in todo) / 4 * price[0] + len(todo) * R.OUT_TOKENS_EST * price[1]
        grand += est
        print(f"{src:26s} trajs={len(trajs)} steps={len(jobs)} todo={len(todo)} est=${est:.2f}", flush=True)
        plans.append((src, trajs, jobs, todo, cache, max_steps))
    print(f"total est ${grand:.2f}")
    if a.dry_run or (grand > 2 and not a.yes):
        print("dry run" if a.dry_run else "re-run with --yes")
        return
    for src, trajs, jobs, todo, cache, max_steps in plans:
        errors = {}
        if todo:
            # one trajectory's steps in order, many trajectories in parallel: better prompt-cache reuse
            todo.sort(key=lambda j: (j.traj.traj_id, j.step))

            async def go():
                from amd.common.openrouter import OpenRouter
                async with OpenRouter(track="r5jev", concurrency=a.concurrency, tag=f"r5:nano:{src}") as c:
                    return await R.run_jobs(todo, c, MODEL, mid, cache)
            errors = asyncio.run(go())
        streams = R.assemble(trajs, cfg, MODEL, max_steps, cache, errors,
                             {(j.traj.traj_id, j.step): j.sha for j in jobs})
        cache.close()
        write_jsonl(PROCESSED / src / OUT_NAME, streams)
        n = sum(len(s.scores) for s in streams)
        nan = sum(sum(math.isnan(x) for x in s.scores) for s in streams)
        print(f"wrote {src}/{OUT_NAME}: {len(streams)} streams, {n} steps, {nan} NaN", flush=True)


if __name__ == "__main__":
    main()
