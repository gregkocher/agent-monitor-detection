"""gpt-4.1-mini history-free (`none`) per-step scoring of the round-4 held-out sets, track r4wb.

Same monitor as the pilot comparator (monitor_id openai/gpt-4.1-mini|ctrl-basic-v1|none, logprob-expected
score, first 60 steps; the final submit step is stripped at analysis time exactly as in the pilot). Thin
wrapper around amd.scoring.run (whose CLI does not list the r4wb track); writes to NEW files so no earlier
score file is touched:

  data/processed/monitoringbench/r4wb_scores_openai_gpt-4.1-mini_none.jsonl          (held-out attacks)
  data/processed/akshn_basharena_opus46/r4wb_scores_openai_gpt-4.1-mini_none.jsonl   (external honest)

    unset VIRTUAL_ENV; uv run python -m tracks.r4_wb.score_llm --set attack [--dry-run] [--yes]
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

MODEL = "openai/gpt-4.1-mini"
SETS = {"attack": ("monitoringbench", "attack"), "ext": ("akshn_basharena_opus46", "ext_honest")}
OUT_NAME = "r4wb_scores_openai_gpt-4.1-mini_none.jsonl"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=list(SETS))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    source, key = SETS[a.set]
    ids = json.load(open("tracks/r4_wb/heldout.json"))[key]
    cfg = PromptConfig(history="none")
    mid = cfg.monitor_id(MODEL)
    trajs = R.select(R.load_source(source), None, ids, a.limit)
    assert len(trajs) == (a.limit or len(ids)), (len(trajs), len(ids))
    jobs = R.plan(trajs, cfg, 60)
    cache = ScoreCache(PROCESSED / source / "score_cache.sqlite")
    todo = [j for j in jobs if (c := cache.get(j.traj.traj_id, j.step, mid)) is None or c[1].get("prompt_sha") != j.sha]
    price = R.get_price(MODEL) or R.FALLBACK_PRICES[MODEL]
    est = sum(j.info["prompt_chars"] for j in todo) / 4 * price[0] + len(todo) * R.OUT_TOKENS_EST * price[1]
    print(f"{mid} {source}: trajectories={len(trajs)} calls={len(jobs)} to_score={len(todo)} est=${est:.2f}")
    if a.dry_run:
        return
    if todo and est > 2 and not a.yes:
        print("re-run with --yes"); return
    errors = {}
    if todo:
        async def go():
            from amd.common.openrouter import OpenRouter
            async with OpenRouter(track="r4wb", concurrency=a.concurrency, tag=f"r4wb:scoring:{source}:none") as c:
                return await R.run_jobs(todo, c, MODEL, mid, cache)
        errors = asyncio.run(go())
    streams = R.assemble(trajs, cfg, MODEL, 60, cache, errors, {(j.traj.traj_id, j.step): j.sha for j in jobs})
    cache.close()
    out = PROCESSED / source / OUT_NAME
    write_jsonl(out, streams)
    n = sum(len(s.scores) for s in streams)
    nan = sum(sum(math.isnan(x) for x in s.scores) for s in streams)
    print(f"wrote {out}: {len(streams)} streams, {n} steps, {nan} NaN")


if __name__ == "__main__":
    main()
