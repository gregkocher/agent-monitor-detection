"""Probe which providers of a model accept logprobs/top_logprobs (one tiny call each)."""
import asyncio
import sys

from amd.common.openrouter import OpenRouter

M = sys.argv[1] if len(sys.argv) > 1 else "qwen/qwen3-235b-a22b-2507"
MSGS = [{"role": "user", "content": "Say 'SCORE: 3' and nothing else."}]


async def go():
    async with OpenRouter(track="r3t1", concurrency=4, tag="r3t1:probe") as c:
        for prov in ("gmicloud", "parasail", "google-vertex"):
            for k in (20, 5):
                try:
                    r = await c.chat(M, MSGS, max_tokens=10, logprobs=True, top_logprobs=k, retries=1,
                                     extra={"provider": {"order": [prov], "allow_fallbacks": False,
                                                         "require_parameters": True}})
                    print(prov, k, "ok", r["provider"], bool(r["logprobs"]), r["latency"])
                except Exception as e:  # noqa: BLE001
                    print(prov, k, "ERR", str(e)[:160])


asyncio.run(go())
