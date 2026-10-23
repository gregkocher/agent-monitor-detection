"""Generative GPT-6 Luna per-step monitor (H5c): the existing per-step monitor prompt (amd.scoring.prompts,
`ctrl-basic-v1`, history `window`, W = 3: main task + the 3 previous actions + the current action with its output),
model openai/gpt-6-luna via chat completions, API settings as the round-4 r4cs Luna monitor (reasoning effort `low`,
completion cap 4,000 tokens because hidden reasoning counts against it; no logprobs are offered, so the step score is
the generated integer 0-10). Track r5luna. Resumable cache data/r5_luna/cache/gen_<source>.sqlite.

Sets: dev (--dev-n per source from dev_attack/honest samples) or the preregistered H5c subset (h5c_subset.json).

    unset VIRTUAL_ENV; uv run python -m tracks.r5_luna.score_gen --set dev --sources mb,akshn_basharena_opus46 --dev-n 3,3
    unset VIRTUAL_ENV; uv run python -m tracks.r5_luna.score_gen --set h5c --yes
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import time

from amd.scoring.extract import score_distribution
from amd.scoring.prompts import PromptConfig
from amd.scoring.run import plan as plan_steps
from tracks.r5_jev.score_jev import load
from tracks.r5_jev.splits import HERE

from . import lunalib as L
from .score import select_ids

MODEL = "openai/gpt-6-luna"
EXTRA = {"reasoning": {"effort": "low"}}
MAX_TOKENS = 4000
CFG = PromptConfig(history="window")
MID = CFG.monitor_id(MODEL) + "|effort-low"
PRICE = (0.10e-6, 0.50e-6)
SUBSET_FILE = L.ROOT.parent.parent / "tracks" / "r5_luna" / "h5c_subset.json"


def cache_for(src):
    from amd.scoring.cache import ScoreCache
    return ScoreCache(L.CACHE_DIR / f"gen_{src}.sqlite")


async def run(jobs, cache, tag, concurrency):
    from amd.common.openrouter import OpenRouter, ledger_totals
    st = {"done": 0, "err": 0, "parse_fail": 0, "cost": 0.0, "out_tok": 0}
    t0 = last = time.time()
    async with OpenRouter(track=L.TRACK, concurrency=concurrency, tag=tag, timeout=300.0) as orc:
        async def one(j):
            try:
                return j, await orc.chat(MODEL, j.messages, max_tokens=MAX_TOKENS, temperature=0.0, extra=EXTRA,
                                         reserve_usd=0.01), None
            except Exception as e:  # noqa: BLE001
                return j, None, f"{type(e).__name__}: {str(e)[:300]}"
        tasks = [asyncio.create_task(one(j)) for j in jobs]
        for fut in asyncio.as_completed(tasks):
            j, res, err = await fut
            st["done"] += 1
            if err:
                st["err"] += 1
                if st["err"] <= 5:
                    print("  error:", err, flush=True)
            else:
                d = score_distribution(None, res["text"])
                u = res.get("usage") or {}
                rec = {"text": res["text"][-600:], "int_score": d["int_score"], "cost": res["cost"],
                       "in_tok": u.get("prompt_tokens"), "out_tok": u.get("completion_tokens"),
                       "reasoning_tok": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                       "finish_reason": res.get("finish_reason"), "provider": res.get("provider"),
                       "model": MODEL, "prompt_sha": j.sha}
                st["cost"] += res["cost"]
                st["out_tok"] += u.get("completion_tokens") or 0
                if d["int_score"] is None:
                    st["parse_fail"] += 1
                cache.put(j.traj.traj_id, j.step, MID, "ok" if d["int_score"] is not None else "parse_fail", rec)
            now = time.time()
            if now - last > 30 or st["done"] == len(jobs):
                last = now
                _, per = ledger_totals()
                print(f"  [{st['done']}/{len(jobs)}] err={st['err']} parse_fail={st['parse_fail']} "
                      f"cost=${st['cost']:.3f} ${st['cost'] / max(st['done'] - st['err'], 1):.5f}/step "
                      f"out_tok/step={st['out_tok'] / max(st['done'] - st['err'], 1):.0f} "
                      f"track=${per.get(L.TRACK, 0.0):.2f} {now - t0:.0f}s", flush=True)
    return st


def load_gen(src, trajs, max_steps=None):
    """{traj_id: per-step generated integer (NaN = missing / parse failure / stale)}."""
    import numpy as np
    cache = cache_for(src)
    shas = {(j.traj.traj_id, j.step): j.sha for j in plan_steps(trajs, CFG, max_steps or 10 ** 6)}
    out = {}
    for t in trajs:
        n = len(t.steps) if max_steps is None else min(len(t.steps), max_steps)
        v = np.full(n, np.nan)
        for k in range(n):
            c = cache.get(t.traj_id, k, MID)
            if c and c[1].get("prompt_sha") == shas[(t.traj_id, k)] and c[1].get("int_score") is not None:
                v[k] = float(c[1]["int_score"])
        out[t.traj_id] = v
    cache.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["dev", "h5c"])
    ap.add_argument("--sources")
    ap.add_argument("--dev-n", default="3,3")
    ap.add_argument("--max-steps-per-traj", type=int)
    ap.add_argument("--retry-parse-fail", action="store_true")
    ap.add_argument("--concurrency", type=int, default=48)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    spl = json.load(open(HERE / "splits.json"))["sources"]
    sub = json.load(open(SUBSET_FILE)) if a.set == "h5c" else None
    srcs = a.sources.split(",") if a.sources else (list(sub["sources"]) if sub else ["mb"])
    plans, grand = [], 0.0
    for src in srcs:
        if a.set == "dev":
            ids = select_ids(spl, src, "dev", "nano", tuple(int(x) for x in a.dev_n.split(",")))
        else:
            ids = set(sub["sources"][src]["honest"]) | set(sub["sources"][src]["attack"])
        trajs = sorted(load(src, ids), key=lambda t: t.traj_id)
        ms = L.MB_MAX_STEPS if src == "mb" else 10 ** 6
        if a.max_steps_per_traj:
            ms = min(ms, a.max_steps_per_traj)
        jobs = plan_steps(trajs, CFG, ms)
        cache = cache_for(src)
        todo = []
        for j in jobs:
            c = cache.get(j.traj.traj_id, j.step, MID)
            if c is None or c[1].get("prompt_sha") != j.sha or (a.retry_parse_fail and c[0] == "parse_fail"):
                todo.append(j)
        est = sum(j.info["prompt_chars"] / 3.6 * PRICE[0] + 450 * PRICE[1] for j in todo)
        grand += est
        print(f"{src:26s} trajs={len(trajs)} steps={len(jobs)} todo={len(todo)} est=${est:.2f}", flush=True)
        plans.append((src, cache, todo))
    print(f"total est ${grand:.2f} (assumes ~450 completion tokens per call; check the dev pilot)")
    if a.dry_run or (grand > 2 and not a.yes):
        print("dry run" if a.dry_run else "re-run with --yes")
        return
    for src, cache, todo in plans:
        if todo:
            todo.sort(key=lambda j: (j.traj.traj_id, j.step))
            st = asyncio.run(run(todo, cache, f"r5luna:gen:{a.set}:{src}", a.concurrency))
            print(f"== {src}: {json.dumps(st)}", flush=True)
        cache.close()


if __name__ == "__main__":
    main()
