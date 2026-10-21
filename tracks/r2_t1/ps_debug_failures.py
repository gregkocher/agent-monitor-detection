"""Show why some PRs never get a parseable score from a model: re-send 3 uncached prompts and print the raw
completion tail, finish reason and token counts.

    uv run python tracks/r2_t1/ps_debug_failures.py --model google/gemini-2.5-flash --no-logprobs --reasoning-off
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from llmcache import PromptCache, prompt_key  # noqa: E402
from ps_score import CACHE, MAX_TOKENS, PROMPT_ID, build_messages, load_runs  # noqa: E402

from amd.common.openrouter import OpenRouter  # noqa: E402


async def go(a, todo):
    async with OpenRouter(track="r2t1", concurrency=3, tag="r2t1:debug") as c:
        for mode, i, m in todo:
            ex = {"reasoning": {"enabled": False}} if a.reasoning_off else None
            r = await c.chat(a.model, m, max_tokens=MAX_TOKENS, logprobs=not a.no_logprobs, extra=ex)
            print(f"--- {mode} PR{i} finish={r['finish_reason']} usage={r['usage'].get('completion_tokens')} "
                  f"in={r['usage'].get('prompt_tokens')}\n{r['text'][-600:]!r}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--no-logprobs", action="store_true")
    ap.add_argument("--reasoning-off", action="store_true")
    a = ap.parse_args()
    sig = PROMPT_ID + ("|nolp" if a.no_logprobs else "") + ("|reasoff" if a.reasoning_off else "")
    cache = PromptCache(CACHE)
    todo = []
    for r in load_runs():
        for mode in ("current_only", "full_diffs"):
            for i in range(5):
                m = build_messages(r["prs"], i, mode)
                if m is not None and cache.get(prompt_key(a.model, m, MAX_TOKENS, sig)) is None:
                    todo.append((mode, i, m))
    print(f"{len(todo)} uncached prompts; lengths (chars):",
          sorted(len(m[1]["content"]) for _, _, m in todo)[:: max(1, len(todo) // 10)])
    asyncio.run(go(a, todo[:3]))


if __name__ == "__main__":
    main()
