"""One-off API probe: send one dev request (data/r5_jev/dev_req_A_w3.jsonl, line 1) to each model given and print
the response (answers, versioned model id, usage, cost). Track r5luna.

    unset VIRTUAL_ENV; uv run python -m tracks.r5_luna.probe openai/gpt-6-luna-decisions perplexity/pplx-decider-v1.2
"""
import asyncio
import json
import sys

from amd.common.openrouter import OpenRouter
from amd.common.schema import DATA

req = json.loads(open(DATA / "r5_jev" / "dev_req_A_w3.jsonl").readline())


async def go():
    async with OpenRouter(track="r5luna", concurrency=2, tag="r5luna:probe") as orc:
        for m in sys.argv[1:]:
            try:
                r = await orc.decisions(m, req["state"], req["questions"])
                print(m, json.dumps(r, indent=1)[:2500])
            except Exception as e:  # noqa: BLE001
                print(m, "ERR", str(e)[:600])

asyncio.run(go())
