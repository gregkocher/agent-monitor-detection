"""Idea 05, GPT-6 Luna Decisions arm (track r5luna).

Decision-only models scored with the FROZEN round-1 request (tracks/r5_jev/jevlib.py, variant B_w3, score scheme
`bs` = P(suspicious) of the benign-first question, normalized over the two labels):
  luna     openai/gpt-6-luna-decisions   (public beta; the versioned id each response returns is stored per call)
  decider  perplexity/pplx-decider-v1.2  (hosted; the same open model was self-hosted in round 1)
  jev      typesafe/jev-1.14             (only for the full-text arm, H5d)

Two request modes:
  frozen   jevlib.build_request(traj, k, "B_w3") on the processed trajectories, byte-identical to round 1.
  full     the frozen request with ONLY state.current_action.action replaced by the untruncated action text (from the
           untruncated rebuild in data/r5_luna/full/, see build_full.py). Main task, the 3-step window and the output
           keep their frozen caps. When the raw action fits the frozen cap, the full request equals the frozen one
           (same sha) and the frozen record is reused without a call.

Caches: data/r5_luna/cache/<model>_<source>.sqlite (amd.scoring.cache.ScoreCache), key (traj_id, step, monitor_id), the
sha of the exact request stored with every row (stale rows are re-scored). Only task text and step texts are sent.
"""
from __future__ import annotations

import asyncio
import copy
import json
import math
import time
from dataclasses import dataclass

import numpy as np

from amd.common.schema import DATA, Trajectory, read_jsonl
from amd.scoring.cache import ScoreCache
from tracks.r5_jev import jevlib as J

MODELS = {"luna": "openai/gpt-6-luna-decisions", "decider": "perplexity/pplx-decider-v1.2", "jev": "typesafe/jev-1.14"}
PRICE_PER_TOK = {"luna": 0.10e-6, "decider": 0.02e-6, "jev": 0.042e-6}
VARIANT, SCHEME = "B_w3", "bs"          # frozen round-1 choice (results/r5_jev/dev_choice.json)
ROOT = DATA / "r5_luna"
CACHE_DIR = ROOT / "cache"
FULL_DIR = ROOT / "full"
MB_MAX_STEPS = 60
TRACK = "r5luna"


def monitor_id(model: str, mode: str = "frozen") -> str:
    return f"{MODELS[model]}|r5-{VARIANT}|both-orders" + ("" if mode == "frozen" else f"|{mode}")


def cache_for(model: str, source: str) -> ScoreCache:
    return ScoreCache(CACHE_DIR / f"{model}_{source}.sqlite")


# ------------------------------------------------------------------------------------------------ requests
@dataclass
class Job:
    traj_id: str
    step: int
    req: dict
    sha: str
    n_bytes: int
    frozen_sha: str | None = None   # full mode: sha of the frozen request for the same step


def frozen_request(traj: Trajectory, k: int) -> dict:
    return J.build_request(traj, k, VARIANT)


def full_request(traj: Trajectory, full_traj: Trajectory, k: int) -> dict:
    req = copy.deepcopy(frozen_request(traj, k))
    req["state"]["current_action"]["action"] = full_traj.steps[k].action
    return req


def plan(trajs: list[Trajectory], max_steps: int | None = None, mode: str = "frozen",
         full: dict | None = None) -> list[Job]:
    jobs = []
    for t in trajs:
        n = len(t.steps) if max_steps is None else min(len(t.steps), max_steps)
        for k in range(n):
            fr = frozen_request(t, k)
            if mode == "frozen":
                req = fr
            else:
                req = full_request(t, full[t.traj_id], k)
            jobs.append(Job(t.traj_id, k, req, J.request_sha(req), len(json.dumps(req).encode()),
                            J.request_sha(fr)))
    return jobs


def load_full(source: str) -> dict:
    p = FULL_DIR / source / "trajectories.jsonl"
    return {d["traj_id"]: Trajectory(**d) for d in read_jsonl(p)} if p.exists() else {}


def todo_jobs(jobs: list[Job], cache: ScoreCache, mid: str) -> list[Job]:
    out = []
    for j in jobs:
        c = cache.get(j.traj_id, j.step, mid)
        if c is None or c[1].get("sha") != j.sha:
            out.append(j)
    return out


# ------------------------------------------------------------------------------------------------ runner
async def run_jobs(jobs: list[Job], cache: ScoreCache, model: str, mid: str, tag: str, concurrency: int = 48,
                   rps: float = 40.0, progress_every: float = 30.0, track: str = TRACK) -> dict:
    from amd.common.openrouter import OpenRouter, ledger_totals
    stats = {"done": 0, "err": 0, "cost": 0.0, "versions": {}, "errors": {}}
    lim = J.RateLimiter(rps)
    t0 = last = time.time()
    async with OpenRouter(track=track, concurrency=concurrency, tag=tag, timeout=120.0) as orc:
        async def one(j: Job):
            await lim.wait()
            try:
                res = await orc.decisions(MODELS[model], j.req["state"], j.req["questions"])
                return j, res, None
            except Exception as e:  # noqa: BLE001 - failures stay uncached and are retried on the next pass
                return j, None, f"{type(e).__name__}: {str(e)[:300]}"

        tasks = [asyncio.create_task(one(j)) for j in jobs]
        for fut in asyncio.as_completed(tasks):
            j, res, err = await fut
            stats["done"] += 1
            if err:
                stats["err"] += 1
                k = err[:60]
                stats["errors"][k] = stats["errors"].get(k, 0) + 1
                if stats["err"] <= 5:
                    print("  error:", err, flush=True)
            else:
                rec = {"answers": res["answers"], "model": res["model"], "in_tok": res["usage"].get("input_tokens"),
                       "cost": res["cost"], "latency": res["latency"], "provider": res.get("provider"),
                       "sha": j.sha, "bytes": j.n_bytes}
                stats["cost"] += res["cost"]
                stats["versions"][res["model"]] = stats["versions"].get(res["model"], 0) + 1
                cache.put(j.traj_id, j.step, mid, "ok", rec)
            now = time.time()
            if now - last > progress_every or stats["done"] == len(jobs):
                last = now
                _, per = ledger_totals()
                print(f"  [{stats['done']}/{len(jobs)}] err={stats['err']} cost=${stats['cost']:.3f} "
                      f"track_{track}=${per.get(track, 0.0):.2f} {now - t0:.0f}s versions={stats['versions']}",
                      flush=True)
    return stats


# ------------------------------------------------------------------------------------------------ reading
def p_susp(rec: dict | None) -> float:
    return J.step_score(rec, SCHEME)


def load_scores(model: str, source: str, trajs: list[Trajectory], max_steps: int | None = None,
                mode: str = "frozen", full: dict | None = None) -> tuple[dict, dict]:
    """{traj_id: per-step P(suspicious) array (NaN = missing / stale)}, plus summary (versions, cost, n)."""
    cache = cache_for(model, source)
    mid = monitor_id(model, mode)
    out, versions, cost, n_ok = {}, {}, 0.0, 0
    for t in trajs:
        n = len(t.steps) if max_steps is None else min(len(t.steps), max_steps)
        v = np.full(n, np.nan)
        for k in range(n):
            c = cache.get(t.traj_id, k, mid)
            if c is None:
                continue
            req = frozen_request(t, k) if mode == "frozen" else full_request(t, full[t.traj_id], k)
            if c[1].get("sha") != J.request_sha(req):
                continue
            v[k] = p_susp(c[1])
            versions[c[1].get("model")] = versions.get(c[1].get("model"), 0) + 1
            cost += c[1].get("cost") or 0.0
            n_ok += 1
        out[t.traj_id] = v
    cache.close()
    return out, dict(versions=versions, cost=cost, n_ok=n_ok, cost_step=cost / max(n_ok, 1))


def finite_frac(d: dict) -> float:
    a = np.concatenate(list(d.values())) if d else np.zeros(0)
    return float(np.isfinite(a).mean()) if len(a) else math.nan
