"""Per-step monitor re-scoring runner.

    python -m amd.scoring.run --source dev_fixture --model openai/gpt-4.1-mini --history full --track dev \
        [--limit N] [--labels honest,attack] [--traj-ids a,b] [--max-steps 60] [--concurrency 32] \
        [--out-name scores_x.jsonl] [--dry-run] [--yes]

Reads data/processed/<source>/trajectories.jsonl, scores every step (or the whole trajectory with
--history trajectory) and writes data/processed/<source>/scores_<model-slug>_<history>.jsonl as
ScoreStream records (scores = logprob-expected score per step; meta holds integer scores, per-step
probability vectors over 0..10, coverage, errors, truncation and cost).

Resumable: every successful call is cached in data/processed/<source>/score_cache.sqlite keyed by
(traj_id, step, monitor_id), so re-runs only pay for missing steps. Failed calls are recorded as NaN with
the error and retried on the next run. Before calling the API the runner prints a cost estimate
(chars/4 input tokens x price + ~OUT_TOKENS_EST output tokens per call) and refuses to proceed above
$2 without --yes.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from amd.common.schema import PROCESSED, ScoreStream, Trajectory, read_jsonl, write_jsonl
from amd.scoring.cache import ScoreCache, prompt_sha
from amd.scoring.extract import score_distribution
from amd.scoring.prompts import HISTORY_MODES, PromptConfig, build_messages

MAX_TOKENS = 400
OUT_TOKENS_EST = 180
CONFIRM_ABOVE_USD = 2.0
FALLBACK_PRICES = {  # $/token (input, output); used when the OpenRouter models endpoint is unreachable
    "openai/gpt-4.1-mini": (0.4e-6, 1.6e-6),
    "openai/gpt-4.1-nano": (0.1e-6, 0.4e-6),
    "openai/gpt-4.1": (2.0e-6, 8.0e-6),
    "openai/gpt-4o-mini": (0.15e-6, 0.6e-6),
}


def model_slug(model: str) -> str:
    return model.replace("/", "_").replace(":", "_")


def get_price(model: str) -> tuple[float, float] | None:
    try:
        r = httpx.get("https://openrouter.ai/api/v1/models", timeout=20)
        for m in r.json()["data"]:
            if m["id"] == model:
                return float(m["pricing"]["prompt"]), float(m["pricing"]["completion"])
    except Exception:
        pass
    return FALLBACK_PRICES.get(model)


@dataclass
class Job:
    traj: Trajectory
    step: int            # -1 = trajectory-level
    messages: list
    info: dict
    sha: str


def load_source(source: str, root: Path = PROCESSED) -> list[Trajectory]:
    return [Trajectory(**d) for d in read_jsonl(root / source / "trajectories.jsonl")]


def select(trajs: list[Trajectory], labels: list[str] | None, traj_ids: list[str] | None,
           limit: int | None) -> list[Trajectory]:
    out = [t for t in trajs if (not labels or t.label in labels) and (not traj_ids or t.traj_id in traj_ids)]
    return out[:limit] if limit else out


def plan(trajs: list[Trajectory], cfg: PromptConfig, max_steps: int) -> list[Job]:
    jobs = []
    for t in trajs:
        if cfg.history == "trajectory":
            msgs, info = build_messages(t, None, cfg)
            jobs.append(Job(t, -1, msgs, info, prompt_sha(msgs)))
            continue
        for i in range(min(len(t.steps), max_steps)):
            msgs, info = build_messages(t, i, cfg)
            jobs.append(Job(t, i, msgs, info, prompt_sha(msgs)))
    return jobs


def _sig(x: float, digits: int = 4) -> float:
    return float(f"{x:.{digits}g}")


def _to_cache(text: str, res: dict, job: Job, dt: float) -> dict:
    d = score_distribution(res.get("logprobs"), text)
    usage = res.get("usage") or {}
    return {"text": text, "int_score": d["int_score"], "expected": d["expected"],
            "probs": [_sig(p) for p in d["probs"]] if d["probs"] else None,
            "digit_logprobs": {k: round(v, 4) for k, v in d["digit_logprobs"].items()}
            if d.get("digit_logprobs") else None,
            "coverage": None if d["coverage"] is None else round(d["coverage"], 5),
            "lp_ok": d["lp_ok"], "note": d["note"], "cost": res.get("cost", 0.0),
            "latency": res.get("latency", round(dt, 2)), "wall": round(dt, 2),
            "in_tok": usage.get("prompt_tokens"), "out_tok": usage.get("completion_tokens"),
            "provider": res.get("provider"), "finish_reason": res.get("finish_reason"),
            "prompt_sha": job.sha, "info": job.info}


async def run_jobs(jobs: list[Job], client, model: str, monitor_id: str, cache: ScoreCache,
                   progress_every: float = 15.0) -> dict:
    """Score jobs (assumed uncached); returns {(traj_id, step): result-or-error}."""
    out: dict = {}
    stats = {"done": 0, "err": 0, "cost": 0.0}
    t_start = last = time.time()

    async def one(job: Job):
        t0 = time.time()
        try:
            # prompt_cache_key routes all of a trajectory's steps to one OpenAI cache shard
            # (same ~0.5x list-price discount measured in track 1); it is a routing hint, not
            # part of the prompt, so cached scores are identical.
            res = await client.chat(model, job.messages, max_tokens=MAX_TOKENS, temperature=0.0,
                                    logprobs=True, top_logprobs=20,
                                    extra={"prompt_cache_key": f"amd:{job.traj.traj_id}"})
        except Exception as e:  # noqa: BLE001 - every API failure becomes a NaN step
            return job, None, f"{type(e).__name__}: {str(e)[:300]}", time.time() - t0
        return job, res, None, time.time() - t0

    tasks = [asyncio.create_task(one(j)) for j in jobs]
    for fut in asyncio.as_completed(tasks):
        job, res, err, dt = await fut
        key = (job.traj.traj_id, job.step)
        stats["done"] += 1
        if err is not None:
            stats["err"] += 1
            out[key] = {"error": err}
        else:
            rec = _to_cache(res.get("text") or "", res, job, dt)
            stats["cost"] += rec["cost"] or 0.0
            status = "ok" if rec["int_score"] is not None else "parse_fail"
            cache.put(job.traj.traj_id, job.step, monitor_id, status, rec)
            out[key] = rec
        now = time.time()
        if now - last > progress_every or stats["done"] == len(jobs):
            last = now
            from amd.common.openrouter import ledger_totals
            _, per = ledger_totals()
            track = getattr(client, "track", None)
            print(f"  [{stats['done']}/{len(jobs)}] errors={stats['err']} job_cost=${stats['cost']:.4f} "
                  f"track_{track}_spent=${per.get(track, 0.0):.3f} elapsed={now - t_start:.0f}s", flush=True)
    return out


def assemble(trajs: list[Trajectory], cfg: PromptConfig, model: str, max_steps: int,
             cache: ScoreCache, errors: dict, shas: dict | None = None) -> list[ScoreStream]:
    """Build one ScoreStream per trajectory from the cache. Cached rows whose prompt hash differs from
    `shas[(traj_id, step)]` (stale data) are treated as missing."""
    mid = cfg.monitor_id(model)
    shas = shas or {}
    streams = []
    for t in trajs:
        idxs = [-1] if cfg.history == "trajectory" else list(range(min(len(t.steps), max_steps)))
        scores, ints, probs, cov, lp_ok, omitted, errs, notes = [], [], [], [], [], [], {}, {}
        dlp = []
        cost = 0.0
        for i in idxs:
            c = cache.get(t.traj_id, i, mid)
            rec = c[1] if c else None
            if rec is not None and (t.traj_id, i) in shas and rec.get("prompt_sha") != shas[(t.traj_id, i)]:
                rec = None
                errs[str(i)] = "stale cache entry (prompt changed) and re-score failed"
            if (t.traj_id, i) in errors and "error" in errors[(t.traj_id, i)]:
                rec = None
                errs[str(i)] = errors[(t.traj_id, i)]["error"]
            if rec is None or rec.get("int_score") is None:
                scores.append(math.nan); ints.append(None); probs.append(None); cov.append(None)
                lp_ok.append(False); omitted.append(None); dlp.append(None)
                if rec is not None:
                    errs[str(i)] = "parse_fail: " + rec.get("note", "")
                elif str(i) not in errs:
                    errs[str(i)] = "missing"
                if rec is not None:
                    cost += rec.get("cost") or 0.0
                continue
            scores.append(rec["expected"] if rec["lp_ok"] else float(rec["int_score"]))
            ints.append(rec["int_score"]); probs.append(rec["probs"]); cov.append(rec["coverage"])
            lp_ok.append(rec["lp_ok"]); omitted.append(rec["info"].get("n_omitted", 0))
            dlp.append(rec.get("digit_logprobs"))
            cost += rec.get("cost") or 0.0
            if rec.get("note"):
                notes[str(i)] = rec["note"]
        meta = {"history": cfg.history, "prompt_id": cfg.effective_prompt_id, "model": model,
                "logprob_expected": True, "int_scores": ints, "probs": probs, "digit_logprobs": dlp, "coverage": cov,
                "lp_ok": lp_ok, "n_history_omitted": omitted, "errors": errs, "notes": notes,
                "n_steps_total": len(t.steps), "n_steps_scored": sum(not math.isnan(s) for s in scores),
                "cost_usd": round(cost, 6), "label": t.label, "attack_step": t.attack_step}
        streams.append(ScoreStream(t.traj_id, mid, "trajectory" if cfg.history == "trajectory" else "step",
                                   scores, (0.0, 10.0), meta))
    return streams


def main(argv: list[str] | None = None, client_factory=None, data_root: Path = PROCESSED) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--history", required=True, choices=HISTORY_MODES)
    ap.add_argument("--track", required=True,
                    choices=["t1", "t2", "t3", "dev", "reserve",
                             "wb", "r2t1", "r2t2", "r2t3", "r3t3", "dev2", "reserve2"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--labels", type=lambda s: s.split(","))
    ap.add_argument("--traj-ids", type=lambda s: s.split(","))
    ap.add_argument("--max-steps", type=int, default=60)
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--out-name")
    ap.add_argument("--window", type=int, default=3)
    ap.add_argument("--full-history-tokens", type=int, default=None)
    ap.add_argument("--no-current-output", action="store_true")
    ap.add_argument("--include-reasoning", action="store_true")
    ap.add_argument("--retry-failed", action="store_true", help="re-score cached parse failures")
    ap.add_argument("--dry-run", action="store_true", help="print prompts for 2 steps + estimate; no API")
    ap.add_argument("--yes", action="store_true", help=f"proceed when estimate > ${CONFIRM_ABOVE_USD}")
    a = ap.parse_args(argv)

    kw = {"history": a.history, "window": a.window, "include_current_output": not a.no_current_output,
          "include_reasoning": a.include_reasoning}
    if a.full_history_tokens:
        kw["full_history_tokens"] = a.full_history_tokens
    cfg = PromptConfig(**kw)
    mid = cfg.monitor_id(a.model)
    trajs = select(load_source(a.source, data_root), a.labels, a.traj_ids, a.limit)
    if not trajs:
        print("no trajectories selected"); return 1
    jobs = plan(trajs, cfg, a.max_steps)
    cache = ScoreCache(data_root / a.source / "score_cache.sqlite")

    todo, n_cached, n_stale = [], 0, 0
    for j in jobs:
        c = cache.get(j.traj.traj_id, j.step, mid)
        if c is None or (c[0] == "parse_fail" and a.retry_failed):
            todo.append(j)
        elif c[1].get("prompt_sha") != j.sha:
            todo.append(j); n_stale += 1
        else:
            n_cached += 1
    in_tok = sum(j.info["prompt_chars"] for j in todo) / 4
    price = get_price(a.model)
    est = None if price is None else in_tok * price[0] + len(todo) * OUT_TOKENS_EST * price[1]
    omitted = sum(1 for j in jobs if j.info.get("n_omitted"))
    print(f"monitor_id={mid}\nsource={a.source} trajectories={len(trajs)} calls={len(jobs)} "
          f"cached={n_cached} stale={n_stale} to_score={len(todo)} "
          f"calls_with_truncated_history={omitted}")
    print(f"estimated input tokens={in_tok:,.0f} (chars/4); estimated cost="
          + ("unknown (no price)" if est is None else f"${est:.3f}"))

    if a.dry_run:
        for j in jobs[:2]:
            print(f"\n{'=' * 30} {j.traj.traj_id} step {j.step} ({j.traj.label}) {'=' * 30}")
            for m in j.messages:
                print(f"--- [{m['role']}]\n{m['content']}")
        cache.close()
        return 0
    if todo and (est is None or est > CONFIRM_ABOVE_USD) and not a.yes:
        print(f"estimate above ${CONFIRM_ABOVE_USD} (or unknown); re-run with --yes to proceed")
        cache.close()
        return 2

    errors: dict = {}
    if todo:
        async def go():
            if client_factory is not None:
                client = client_factory(a.track, a.concurrency)
                return await run_jobs(todo, client, a.model, mid, cache)
            from amd.common.openrouter import OpenRouter
            async with OpenRouter(track=a.track, concurrency=a.concurrency,
                                  tag=f"scoring:{a.source}:{a.history}") as client:
                return await run_jobs(todo, client, a.model, mid, cache)
        errors = asyncio.run(go())

    streams = assemble(trajs, cfg, a.model, a.max_steps, cache, errors,
                       {(j.traj.traj_id, j.step): j.sha for j in jobs})
    cache.close()
    name = a.out_name or f"scores_{model_slug(a.model)}_{a.history}.jsonl"
    out = data_root / a.source / name
    write_jsonl(out, streams)
    n = sum(len(s.scores) for s in streams)
    nan = sum(sum(math.isnan(x) for x in s.scores) for s in streams)
    lp = sum(sum(s.meta["lp_ok"]) for s in streams)
    print(f"wrote {out} ({len(streams)} streams, {n} units, {nan} NaN, {lp}/{n} logprob-expected)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
