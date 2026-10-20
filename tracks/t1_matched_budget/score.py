"""Drive amd.scoring.run on the T1 sample (sample.json).

    uv run python tracks/t1_matched_budget/score.py --set pilot|honest|attack|pilot2 --history full|none|window
        [--model openai/gpt-4.1-mini] [--dry-run] [--yes] [--concurrency 48] [--no-chain]

- honest: all 550 mb_honest -> data/processed/mb_honest/scores_<model>_<history>.jsonl (harness default name)
- attack: the attack sample -> data/processed/monitoringbench/scores_<model>_<history>.jsonl
- pilot: the 20+20 pilot, written under pilot_* names so the default files always hold the full sets.

Scheduling (default "chain"): each trajectory's steps are scored strictly in order (step i is sent after
step i-1 returns), with up to --concurrency trajectories in flight. In full / window mode consecutive
prompts share almost their whole prefix (system + task + history), so the provider's automatic prompt
cache bills most input tokens at the cached rate (gpt-4.1-mini: 25% of list). The calls, prompts, cache
keys and records are exactly those of amd.scoring.run (same monitor_id and prompt hash); after the API
pass, amd.scoring.run.main is invoked on the same selection, finds every step cached (0 calls) and
writes the ScoreStream file. --no-chain uses the harness's own all-at-once scheduler.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from amd.common.schema import PROCESSED
from amd.scoring import run
from amd.scoring.cache import ScoreCache
from amd.scoring.prompts import PromptConfig

HERE = Path(__file__).parent


async def chain_jobs(jobs_by_traj: list[list], model: str, mid: str, cache: ScoreCache, track: str,
                     concurrency: int, tag: str, cache_key: bool = True) -> dict:
    from amd.common.openrouter import OpenRouter, ledger_totals
    stats = {"done": 0, "err": 0, "cost": 0.0, "t0": time.time(), "last": time.time()}
    total = sum(len(j) for j in jobs_by_traj)
    gate = asyncio.Semaphore(concurrency)
    out: dict = {}

    async with OpenRouter(track=track, concurrency=concurrency, tag=tag) as client:
        async def one_traj(jobs):
            async with gate:
                for job in jobs:
                    t0 = time.time()
                    try:
                        # prompt_cache_key: OpenAI routing hint (not part of the prompt). All T1 prompts
                        # share the same first ~256 tokens (system prompt), so without a per-trajectory
                        # key the prefix-hash routing overflows and most cache lookups miss.
                        extra = {"prompt_cache_key": job.traj.traj_id[-60:]} if cache_key else None
                        res = await client.chat(model, job.messages, max_tokens=run.MAX_TOKENS, temperature=0.0,
                                                logprobs=True, top_logprobs=20, extra=extra)
                        rec = run._to_cache(res.get("text") or "", res, job, time.time() - t0)
                        stats["cost"] += rec["cost"] or 0.0
                        cache.put(job.traj.traj_id, job.step, mid,
                                  "ok" if rec["int_score"] is not None else "parse_fail", rec)
                        out[(job.traj.traj_id, job.step)] = rec
                    except Exception as e:  # noqa: BLE001 - becomes NaN, retried next run
                        if type(e).__name__ == "BudgetExceeded":
                            raise
                        stats["err"] += 1
                        out[(job.traj.traj_id, job.step)] = {"error": f"{type(e).__name__}: {str(e)[:300]}"}
                    stats["done"] += 1
                    now = time.time()
                    if now - stats["last"] > 30 or stats["done"] == total:
                        stats["last"] = now
                        _, per = ledger_totals()
                        print(f"  [{stats['done']}/{total}] errors={stats['err']} job_cost=${stats['cost']:.3f} "
                              f"track_{track}_spent=${per.get(track, 0.0):.2f} elapsed={now - stats['t0']:.0f}s",
                              flush=True)

        await asyncio.gather(*(one_traj(j) for j in jobs_by_traj))
    return out


def chained_pass(src, ids, model, history, concurrency, yes, max_steps=60, cache_key=True, tag_suffix=""):
    cfg = PromptConfig(history=history)
    mid = cfg.monitor_id(model)
    trajs = run.select(run.load_source(src), None, ids, None)
    jobs = run.plan(trajs, cfg, max_steps)
    cache = ScoreCache(PROCESSED / src / "score_cache.sqlite")
    todo = []
    for j in jobs:
        c = cache.get(j.traj.traj_id, j.step, mid)
        if c is None or c[1].get("prompt_sha") != j.sha:
            todo.append(j)
    by: dict = {}
    for j in todo:
        by.setdefault(j.traj.traj_id, []).append(j)
    chains = [sorted(v, key=lambda j: j.step) for v in by.values()]
    chains.sort(key=len, reverse=True)  # longest first, so the tail of the job is short
    price = run.get_price(model)
    est = sum(j.info["prompt_chars"] for j in todo) / 4 * price[0] + len(todo) * run.OUT_TOKENS_EST * price[1]
    print(f"[chain] {src} {mid}: calls={len(jobs)} to_score={len(todo)} in {len(chains)} chains; "
          f"list-price estimate ${est:.2f}", flush=True)
    if todo and est > run.CONFIRM_ABOVE_USD and not yes:
        print("estimate above threshold; re-run with --yes"); cache.close(); return 2
    if todo:
        asyncio.run(chain_jobs(chains, model, mid, cache, "t1", concurrency,
                               f"scoring:{src}:{history}:chain{tag_suffix}", cache_key=cache_key))
    cache.close()
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["pilot", "honest", "attack", "pilot2"])
    ap.add_argument("--no-cache-key", action="store_true")
    ap.add_argument("--tag-suffix", default="")
    ap.add_argument("--history", required=True)
    ap.add_argument("--model", default="openai/gpt-4.1-mini")
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--no-chain", action="store_true")
    ap.add_argument("--out-name")
    ap.add_argument("--subset", help="key in sample.json to use instead of the default list")
    a = ap.parse_args()
    s = json.loads((HERE / "sample.json").read_text())
    slug = run.model_slug(a.model)
    if a.set == "pilot":
        jobs = [("monitoringbench", s["pilot_attack"], f"pilot_scores_{slug}_{a.history}.jsonl"),
                ("mb_honest", s["pilot_honest"], f"pilot_scores_{slug}_{a.history}.jsonl")]
    elif a.set == "pilot2":  # small chained-scheduling cost check on unscored trajectories
        jobs = [("monitoringbench", s["pilot2_attack"], f"pilot2_scores_{slug}_{a.history}.jsonl")]
    elif a.set == "honest":
        jobs = [("mb_honest", s[a.subset] if a.subset else None, a.out_name)]
    else:
        jobs = [("monitoringbench", s[a.subset] if a.subset else s["attack"], a.out_name)]
    rc = 0
    for src, ids, out in jobs:
        print(f"### {src} {a.history} n={len(ids) if ids else 'all'}", flush=True)
        if not a.no_chain and not a.dry_run and a.history != "trajectory":
            r = chained_pass(src, ids, a.model, a.history, a.concurrency, a.yes,
                             cache_key=not a.no_cache_key, tag_suffix=a.tag_suffix)
            if r:
                return r
        argv = ["--source", src, "--model", a.model, "--history", a.history, "--track", "t1",
                "--max-steps", "60", "--concurrency", str(min(a.concurrency, 32))]
        if ids:
            argv += ["--traj-ids", ",".join(ids)]
        if out:
            argv += ["--out-name", out]
        if a.dry_run:
            argv.append("--dry-run")
        if a.yes:
            argv.append("--yes")
        rc = run.main(argv) or rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
