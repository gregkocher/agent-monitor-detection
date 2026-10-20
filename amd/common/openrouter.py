"""OpenRouter client with a hard, process-safe spend ledger.

Every call appends one JSON line to results/spend_ledger.jsonl with the cost OpenRouter reports
(`usage.cost`, requested via `usage: {include: true}`). Before each call the client checks the
cumulative cost for its track and for all tracks against the caps below and refuses to call once a
cap would be exceeded. The ledger is shared by all processes (fcntl lock), so parallel tracks
cannot jointly overspend.

Key: the MATS `weekly1000` key by default (path in KEY_PATH). The key is read from disk at call
time and never logged.
"""
from __future__ import annotations

import asyncio
import fcntl
import json
import os
import random
import time
from pathlib import Path

import httpx

from .schema import REPO

KEY_PATH = Path(os.environ.get(
    "AMD_OPENROUTER_KEY_PATH",
    "/Users/gkocher/Desktop/RESEARCH/MATS_SUMMER_2026/openrouter_api_key_weekly1000.txt"))
LEDGER = REPO / "results" / "spend_ledger.jsonl"
URL = "https://openrouter.ai/api/v1/chat/completions"

GLOBAL_CAP_USD = 500.0
TRACK_CAPS_USD = {"t1": 130.0, "t2": 70.0, "t3": 200.0, "dev": 15.0, "reserve": 100.0}


class BudgetExceeded(RuntimeError):
    pass


def _key() -> str:
    return KEY_PATH.read_text().strip()


_LEDGER_STATE: dict = {"path": None, "ino": None, "offset": 0, "tot": 0.0, "per": {}}


def ledger_totals() -> tuple[float, dict]:
    """(total, per-track) spend. Reads only lines appended since the previous call (the ledger is
    append-only), so per-call budget checks stay O(new lines) over long jobs."""
    st = _LEDGER_STATE
    if not LEDGER.exists():
        return 0.0, {}
    fs = LEDGER.stat()
    if st["path"] != str(LEDGER) or st["ino"] != fs.st_ino or fs.st_size < st["offset"]:
        st.update(path=str(LEDGER), ino=fs.st_ino, offset=0, tot=0.0, per={})
    with open(LEDGER, "rb") as f:
        f.seek(st["offset"])
        data = f.read()
    end = data.rfind(b"\n") + 1  # only complete lines
    for line in data[:end].splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        c = float(r.get("cost") or 0.0)
        st["tot"] += c
        st["per"][r["track"]] = st["per"].get(r["track"], 0.0) + c
    st["offset"] += end
    return st["tot"], dict(st["per"])


def _check_budget(track: str, reserve_usd: float) -> None:
    tot, per = ledger_totals()
    if tot + reserve_usd > GLOBAL_CAP_USD:
        raise BudgetExceeded(f"global cap ${GLOBAL_CAP_USD} reached (spent ${tot:.2f})")
    cap = TRACK_CAPS_USD.get(track)
    if cap is not None and per.get(track, 0.0) + reserve_usd > cap:
        raise BudgetExceeded(f"track {track} cap ${cap} reached (spent ${per.get(track, 0.0):.2f})")


def _append(rec: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(rec) + "\n")
        fcntl.flock(f, fcntl.LOCK_UN)


class OpenRouter:
    """Async client. Usage:

        async with OpenRouter(track="t1", concurrency=32) as orc:
            res = await orc.chat(model, messages, max_tokens=300, temperature=0, logprobs=True, top_logprobs=20)
            res["text"], res["logprobs"], res["cost"]
    """

    def __init__(self, track: str, concurrency: int = 16, timeout: float = 120.0,
                 provider_order: list[str] | None = None, tag: str = ""):
        assert track in TRACK_CAPS_USD, track
        self.track, self.tag = track, tag
        self.sem = asyncio.Semaphore(concurrency)
        self.timeout = timeout
        self.provider_order = provider_order
        self._budget_checked_at = 0.0

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=self.timeout, http2=False)
        return self

    async def __aexit__(self, *a):
        await self.client.aclose()

    async def chat(self, model: str, messages: list[dict], max_tokens: int = 512,
                   temperature: float = 0.0, logprobs: bool = False, top_logprobs: int | None = None,
                   reserve_usd: float = 0.05, retries: int = 6, extra: dict | None = None) -> dict:
        body = {"model": model, "messages": messages, "max_tokens": max_tokens,
                "temperature": temperature, "usage": {"include": True}}
        if logprobs:
            body["logprobs"] = True
            if top_logprobs:
                body["top_logprobs"] = top_logprobs
        if self.provider_order:
            body["provider"] = {"order": self.provider_order, "allow_fallbacks": False}
        if extra:
            body.update(extra)
        async with self.sem:
            _check_budget(self.track, reserve_usd)
            last = None
            for attempt in range(retries):
                t0 = time.time()
                try:
                    r = await self.client.post(URL, json=body, headers={
                        "Authorization": f"Bearer {_key()}",
                        "HTTP-Referer": "https://github.com/gregkocher/agent-monitor-detection",
                        "X-Title": "agent-monitor-detection"})
                    if r.status_code in (429, 500, 502, 503, 504, 408):
                        raise httpx.HTTPStatusError(f"status {r.status_code}", request=r.request, response=r)
                    r.raise_for_status()
                    d = r.json()
                    if "error" in d:
                        raise RuntimeError(str(d["error"])[:300])
                    ch = d["choices"][0]
                    usage = d.get("usage") or {}
                    cost = float(usage.get("cost") or 0.0)
                    _append({"t": time.time(), "track": self.track, "tag": self.tag, "model": model,
                             "provider": d.get("provider"), "in": usage.get("prompt_tokens"),
                             "out": usage.get("completion_tokens"), "cost": cost,
                             "latency": round(time.time() - t0, 2)})
                    return {"text": (ch.get("message") or {}).get("content") or "",
                            "logprobs": (ch.get("logprobs") or {}).get("content"),
                            "cost": cost, "provider": d.get("provider"), "usage": usage,
                            "finish_reason": ch.get("finish_reason"),
                            "latency": round(time.time() - t0, 2)}
                except (httpx.HTTPError, RuntimeError, KeyError, json.JSONDecodeError) as e:
                    last = e
                    await asyncio.sleep(min(60, 2 ** attempt + random.random()))
            raise RuntimeError(f"OpenRouter call failed after {retries} tries: {str(last)[:300]}")


def spend_report() -> str:
    tot, per = ledger_totals()
    lines = [f"total ${tot:.2f} / ${GLOBAL_CAP_USD:.0f}"]
    for k, cap in TRACK_CAPS_USD.items():
        lines.append(f"  {k:8s} ${per.get(k, 0.0):7.2f} / ${cap:.0f}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(spend_report())
