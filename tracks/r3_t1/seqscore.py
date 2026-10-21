"""Sequential per-stream monitor scoring where unit i's prompt may depend on the monitor's OWN outputs for units
< i (e.g. an evidence ledger carried forward). Content-addressed cache (tracks/r2_t1/llmcache.PromptCache):
the key covers model, exact messages, max_tokens and a signature (prompt id, temperature, sample index), so
re-runs never re-pay and a ledger chain replays deterministically from cached outputs.

run_streams(streams, build, model, cache, ...):
    streams: list of (stream_id, n_units, payload)
    build(payload, i, prev_recs) -> messages | None     (prev_recs: cached records of units < i, or None)
Returns {(stream_id, i): rec}. Streams run in parallel (bounded), units within a stream strictly in order.
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "r2_t1"))
from llmcache import PromptCache, parse, prompt_key  # noqa: E402,F401


async def _run(streams, build, model, cache, *, track, concurrency, max_tokens, temperature, sig, logprobs,
               extra_fn, tag, progress_s=30.0):
    from amd.common.openrouter import OpenRouter, ledger_totals
    out = {}
    st = {"calls": 0, "err": 0, "cost": 0.0, "t0": time.time(), "last": time.time(), "done": 0}
    gate = asyncio.Semaphore(concurrency)
    async with OpenRouter(track=track, concurrency=concurrency, tag=tag) as client:
        async def one(sid, n, payload):
            async with gate:
                prev = []
                for i in range(n):
                    msgs = build(payload, i, prev)
                    if msgs is None:
                        prev.append(None)
                        continue
                    k = prompt_key(model, msgs, max_tokens, sig)
                    rec = cache.get(k)
                    tries = 0
                    while rec is None and tries < 3:
                        tries += 1
                        try:
                            res = await client.chat(model, msgs, max_tokens=max_tokens, temperature=temperature,
                                                    logprobs=logprobs, top_logprobs=20 if logprobs else None,
                                                    extra=extra_fn(sid) if extra_fn else None)
                        except Exception as e:  # noqa: BLE001
                            if type(e).__name__ == "BudgetExceeded":
                                raise
                            st["err"] += 1
                            break
                        st["calls"] += 1
                        r = parse(res)
                        st["cost"] += r["cost"] or 0.0
                        if r["int_score"] is not None:
                            cache.put(k, model, r)
                            rec = r
                    out[(sid, i)] = rec
                    prev.append(rec)
                    if rec is None:  # a chain cannot continue past an unscored unit
                        for j in range(i + 1, n):
                            out[(sid, j)] = None
                        break
                st["done"] += 1
                now = time.time()
                if now - st["last"] > progress_s:
                    st["last"] = now
                    _, per = ledger_totals()
                    print(f"  [{tag}] streams {st['done']}/{len(streams)} calls={st['calls']} err={st['err']} "
                          f"job=${st['cost']:.2f} {track}=${per.get(track, 0.0):.2f} {now - st['t0']:.0f}s", flush=True)

        await asyncio.gather(*(one(*s) for s in streams))
    print(f"  [{tag}] done: streams={len(streams)} calls={st['calls']} err={st['err']} job=${st['cost']:.2f}", flush=True)
    return out


def run_streams(streams, build, model, cache, *, track="r3t1", concurrency=24, max_tokens=450, temperature=0.0,
                sig="", logprobs=True, extra_fn=None, tag=""):
    return asyncio.run(_run(streams, build, model, cache, track=track, concurrency=concurrency,
                            max_tokens=max_tokens, temperature=temperature, sig=sig, logprobs=logprobs,
                            extra_fn=extra_fn, tag=tag))


def value(rec):
    if rec is None:
        return float("nan")
    return rec["expected"] if rec["lp_ok"] else float(rec["int_score"])
