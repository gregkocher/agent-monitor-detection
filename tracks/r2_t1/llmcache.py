"""Content-addressed LLM monitor calls for round-2 track 1 (persistent state, MOLE).

- `PromptCache`: sqlite cache keyed by sha256(model | messages | max_tokens | extra-signature), so identical
  prompts (e.g. the honest-cache PR prefix shared by positional runs) are scored once, re-runs never re-pay,
  and any change to the prompt text is a new key.
- `score_chains(chains, ...)`: each chain is a list of (key, messages) scored strictly in order (chained
  scheduling keeps the provider's prompt-prefix cache warm for history-aware prompts), many chains in
  parallel. Results are parsed by `amd.scoring.extract.score_distribution` (logprob-expected 0-10 score when
  the provider returns token logprobs, else the generated integer).
- Spend goes through `amd.common.openrouter.OpenRouter` (ledger + per-track cap; track "r2t1").
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
import time
from pathlib import Path

from amd.scoring.extract import score_distribution


def prompt_key(model: str, messages: list[dict], max_tokens: int, sig: str = "") -> str:
    h = hashlib.sha256()
    h.update(json.dumps([model, messages, max_tokens, sig], sort_keys=True).encode())
    return h.hexdigest()[:24]


class PromptCache:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=60)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS r (k TEXT PRIMARY KEY, model TEXT, rec TEXT, t REAL)")
        self.db.commit()

    def get(self, k: str) -> dict | None:
        r = self.db.execute("SELECT rec FROM r WHERE k=?", (k,)).fetchone()
        return json.loads(r[0]) if r else None

    def has(self, keys) -> set:
        out = set()
        keys = list(keys)
        for i in range(0, len(keys), 500):
            ch = keys[i:i + 500]
            q = "SELECT k FROM r WHERE k IN (%s)" % ",".join("?" * len(ch))
            out.update(x[0] for x in self.db.execute(q, ch))
        return out

    def put(self, k: str, model: str, rec: dict) -> None:
        self.db.execute("INSERT OR REPLACE INTO r VALUES (?,?,?,?)", (k, model, json.dumps(rec), time.time()))
        self.db.commit()


def parse(res: dict) -> dict:
    text = res.get("text") or ""
    d = score_distribution(res.get("logprobs"), text)
    usage = res.get("usage") or {}
    det = usage.get("completion_tokens_details") or {}
    pdet = usage.get("prompt_tokens_details") or {}
    return {"int_score": d["int_score"], "expected": d["expected"], "lp_ok": d["lp_ok"],
            "probs": [float(f"{p:.4g}") for p in d["probs"]] if d["probs"] else None,
            "coverage": d["coverage"], "note": d["note"], "text": text[-1500:],
            "cost": res.get("cost", 0.0), "in_tok": usage.get("prompt_tokens"),
            "cached_tok": pdet.get("cached_tokens"), "out_tok": usage.get("completion_tokens"),
            "reasoning_tok": det.get("reasoning_tokens"), "provider": res.get("provider"),
            "finish_reason": res.get("finish_reason")}


async def score_chains(chains: list[tuple[str, list[tuple[str, list[dict]]]]], model: str, cache: PromptCache, *,
                       track: str = "r2t1", concurrency: int = 32, max_tokens: int = 400,
                       logprobs: bool = True, extra_fn=None, tag: str = "", progress_s: float = 30.0,
                       max_parse_retries: int = 1) -> dict:
    """Score every (key, messages) not yet cached. chains: list of (chain_id, ordered [(key, messages)]).
    extra_fn(chain_id) -> dict of extra body fields (e.g. prompt_cache_key, reasoning) or None."""
    from amd.common.openrouter import OpenRouter, ledger_totals
    todo_keys = {k for _, ch in chains for k, _ in ch}
    done = cache.has(todo_keys)
    chains = [(cid, [(k, m) for k, m in ch if k not in done]) for cid, ch in chains]
    chains = [c for c in chains if c[1]]
    chains.sort(key=lambda c: len(c[1]), reverse=True)
    total = sum(len(c) for _, c in chains)
    st = {"done": 0, "err": 0, "cost": 0.0, "t0": time.time(), "last": time.time()}
    gate = asyncio.Semaphore(concurrency)
    print(f"[{tag}] {model}: {total} calls in {len(chains)} chains ({len(todo_keys) - total} cached)", flush=True)
    if not total:
        return st

    async with OpenRouter(track=track, concurrency=concurrency, tag=tag) as client:
        async def run_chain(cid, ch):
            async with gate:
                for k, msgs in ch:
                    rec = None
                    for attempt in range(1 + max_parse_retries):
                        try:
                            res = await client.chat(model, msgs, max_tokens=max_tokens, temperature=0.0,
                                                    logprobs=logprobs, top_logprobs=20 if logprobs else None,
                                                    extra=extra_fn(cid) if extra_fn else None)
                        except Exception as e:  # noqa: BLE001
                            if type(e).__name__ == "BudgetExceeded":
                                raise
                            st["err"] += 1
                            rec = None
                            break
                        rec = parse(res)
                        st["cost"] += rec["cost"] or 0.0
                        if rec["int_score"] is not None:
                            break
                    if rec is not None and rec["int_score"] is not None:
                        cache.put(k, model, rec)
                    elif rec is not None:
                        st["err"] += 1
                    st["done"] += 1
                    now = time.time()
                    if now - st["last"] > progress_s or st["done"] == total:
                        st["last"] = now
                        _, per = ledger_totals()
                        print(f"  [{st['done']}/{total}] err={st['err']} job=${st['cost']:.2f} "
                              f"{track}=${per.get(track, 0.0):.2f} {now - st['t0']:.0f}s", flush=True)

        await asyncio.gather(*(run_chain(cid, c) for cid, c in chains))
    return st
