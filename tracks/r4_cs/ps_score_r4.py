"""Round 4 (track r4cs): score persistent-state PRs with additional monitor families, history-free only.

    unset VIRTUAL_ENV; uv run python tracks/r4_cs/ps_score_r4.py --monitor gpt-4.1 [--pilot 8] [--dry-run]

Identical inputs to round 2: the prompt is built by tracks/r2_t1/ps_score.build_messages(..., "current_only")
(the paper's PR-review prompt, `SCORE: <1-10>`, current diff head+tail truncated to 60k chars). No prompt text
is changed per monitor; only API-side settings differ (reasoning budget where a model cannot disable it,
logprobs where the provider returns them). Runs: honest + gradual only (the pre-specified target of round 4;
positional runs are not scored). Each run is scored as one ordered chain.

Outputs: data/raw/r4_cs/ps_cache.sqlite (content-addressed, resumable) and
data/processed/persistent_state/r4_scores_<slug>_current_only.jsonl (one 5-PR stream per honest/gradual run).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "r2_t1"))
from llmcache import PromptCache, prompt_key, score_chains  # noqa: E402
from ps_score import MAX_TOKENS, PROMPT_ID, build_messages, load_runs  # noqa: E402

from amd.common.schema import PROCESSED, REPO  # noqa: E402

CACHE = REPO / "data" / "raw" / "r4_cs" / "ps_cache.sqlite"
MODE = "current_only"
POLICIES = ("honest", "gradual")

# Per-monitor API settings. Prompt text is never changed. `call_max_tokens` only raises the completion cap for
# models whose hidden reasoning counts against it; `extra` holds request fields outside the prompt.
MONITORS = {
    "gpt-4.1": dict(model="openai/gpt-4.1", logprobs=True, extra={}, call_max_tokens=None),
    "claude-haiku-4.5": dict(model="anthropic/claude-haiku-4.5", logprobs=False, extra={}, call_max_tokens=1500),
    "gemini-2.5-pro": dict(model="google/gemini-2.5-pro", logprobs=False,
                           extra={"reasoning": {"max_tokens": 1024}}, call_max_tokens=3000),
    "gpt-5-mini": dict(model="openai/gpt-5-mini", logprobs=False, extra={"reasoning": {"effort": "low"}},
                       call_max_tokens=4000),
    "claude-haiku-5.5": dict(model="anthropic/claude-haiku-5.5", logprobs=False, extra={}, call_max_tokens=1500),
    "gpt-6-luna": dict(model="openai/gpt-6-luna", logprobs=False, extra={"reasoning": {"effort": "low"}},
                       call_max_tokens=4000),
}


def slug(m: str) -> str:
    return m.replace("/", "_").replace(":", "_")


def select_runs(runs, pilot: int):
    runs = [r for r in runs if r["traj"].context["policy"] in POLICIES]
    if not pilot:
        return runs
    rng = random.Random(4)
    sel = []
    for pol in POLICIES:
        rr = sorted([r for r in runs if r["traj"].context["policy"] == pol], key=lambda r: r["traj"].traj_id)
        sel += rng.sample(rr, min(pilot, len(rr)))
    return sel


def plan(runs, model, sig):
    chains, seen, keymap = [], set(), {}
    for r in runs:
        ch = []
        for i in range(5):
            msgs = build_messages(r["prs"], i, MODE)
            if msgs is None:
                continue
            k = prompt_key(model, msgs, MAX_TOKENS, sig)
            keymap[(r["traj"].traj_id, i)] = k
            if k not in seen:
                seen.add(k)
                ch.append((k, msgs))
        if ch:
            chains.append((r["traj"].traj_id, ch))
    return chains, keymap


def assemble(runs, keymap, cache, name, model, pilot):
    from amd.common.schema import ScoreStream, write_jsonl
    out = []
    for r in runs:
        t = r["traj"]
        sc, ints, lp = [], [], []
        for i in range(5):
            k = keymap.get((t.traj_id, i))
            rec = cache.get(k) if k else None
            if rec is None:
                sc.append(math.nan); ints.append(None); lp.append(False)
            else:
                sc.append(rec["expected"] if rec["lp_ok"] else float(rec["int_score"]))
                ints.append(rec["int_score"]); lp.append(rec["lp_ok"])
        out.append(ScoreStream(t.traj_id, f"{model}|{PROMPT_ID}|{MODE}", "pr", sc, (1.0, 10.0),
                               {"int_scores": ints, "lp_ok": lp, "history": MODE, "label": t.label,
                                "policy": t.context["policy"], "monitor": name}))
    path = PROCESSED / "persistent_state" / f"r4_{'pilot_' if pilot else ''}scores_{slug(model)}_{MODE}.jsonl"
    write_jsonl(path, out)
    n = sum(len(s.scores) for s in out)
    nan = sum(math.isnan(x) for s in out for x in s.scores)
    print(f"wrote {path.name}: {len(out)} runs, {n - nan}/{n} PRs scored", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor", required=True, choices=list(MONITORS))
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--concurrency", type=int, default=16)
    a = ap.parse_args()
    cfg = MONITORS[a.monitor]
    model = cfg["model"]
    runs = select_runs(load_runs(), a.pilot)
    print(f"{a.monitor}: {len(runs)} runs ({'pilot' if a.pilot else 'full'})", flush=True)
    cache = PromptCache(CACHE)
    sig = PROMPT_ID + "|r4|" + json.dumps(cfg["extra"], sort_keys=True) + ("" if cfg["logprobs"] else "|nolp")
    chains, keymap = plan(runs, model, sig)
    n = sum(len(c) for _, c in chains)
    chars = sum(len(m[1]["content"]) + len(m[0]["content"]) for _, c in chains for _, m in c)
    print(f"{n} unique calls, ~{chars / 4 / 1e6:.2f}M input tokens (chars/4)", flush=True)
    if a.dry_run:
        return
    is_openai = model.startswith("openai/")

    def extra(cid):
        e = dict(cfg["extra"])
        if is_openai:
            e["prompt_cache_key"] = ("r4ps-" + cid)[-60:]
        return e or None

    asyncio.run(score_chains(chains, model, cache, track="r4cs", concurrency=a.concurrency,
                             max_tokens=cfg["call_max_tokens"] or MAX_TOKENS, logprobs=cfg["logprobs"],
                             extra_fn=extra, tag=f"r4cs:ps:{a.monitor}"))
    assemble(runs, keymap, cache, a.monitor, model, a.pilot)


if __name__ == "__main__":
    main()
