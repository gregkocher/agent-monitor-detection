"""Round 4, goal 2: score MOLE single-day corpora (30 workdays per account, 3-4 attack days per solo insider) with a
stronger history-free account-day monitor.

    unset VIRTUAL_ENV; uv run python tracks/r4_cs/mole_score_r4.py --monitor gpt-6-luna [--corpora a,b] [--pilot N]

Input is identical to the round-3 common monitor (tracks/r3_t1/mole_r3.py): the round-2 MOLE judge prompt (MOLE
level-2 system prompt + threat taxonomy, `SCORE: 0-10`) on the compact audit rendering (first 250 events, lines cut
to 250 chars) of the account-day. Renders are rebuilt by tracks/r4_cs/mole_prep.py. Collusive accounts (excluded
from every MOLE accumulation analysis) are not scored. API settings per monitor come from ps_score_r4.MONITORS
(same reasoning settings as on persistent state). Resumable cache data/raw/r4_cs/mole_cache.sqlite.
Output: data/processed/r4_mole/<corpus>/llm_<slug>_compact.parquet (account, day, score, int_score, lp_ok).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
for p in (HERE.parent / "r2_t1", HERE.parent / "r3_t1", HERE):
    sys.path.insert(0, str(p))
from llmcache import PromptCache, prompt_key, score_chains  # noqa: E402
from mole_r3 import MAX_TOKENS, PROMPT_ID, compact, slug  # noqa: E402
from mole_score import SYSTEM  # noqa: E402
from ps_score_r4 import MONITORS  # noqa: E402

from amd.common.schema import PROCESSED, REPO  # noqa: E402

CACHE = REPO / "data" / "raw" / "r4_cs" / "mole_cache.sqlite"
OUT = PROCESSED / "r4_mole"
CORPORA = ["gpt53_single_day", "deepseek_v4_flash_single_day", "qwen36_27b_single_day", "kimi_k26_single_day"]


def subset_accounts(D, n_routine, seed=4):
    """Budget-aware subset: every solo insider + n_routine routine accounts drawn at random (fixed seed)."""
    rout = sorted(D.account[~D.is_insider].unique())
    keep = set(np.random.default_rng(seed).choice(rout, n_routine, replace=False)) | set(D.account[D.is_insider])
    return D[D.account.isin(keep)]


def score_corpus(corpus, name, concurrency, pilot=0, dry=False, subset=0):
    cfg = MONITORS[name]
    model = cfg["model"]
    d = OUT / corpus
    D = pd.read_parquet(d / "accountdays.parquet")
    D = D[~D.collusive]
    if subset:
        D = subset_accounts(D, subset)
    R = {}
    with open(d / "renders.jsonl") as fh:
        for line in fh:
            r = json.loads(line)
            R[(r["account"], r["day"])] = r["text"]
    sel = D if not pilot else pd.concat([D[~D.is_insider].sample(pilot, random_state=0), D[D.attack_day].head(pilot // 2)])
    sig = PROMPT_ID + "|r4|" + json.dumps(cfg["extra"], sort_keys=True) + ("" if cfg["logprobs"] else "|nolp")
    items, keymap = [], {}
    for r in sel.itertuples():
        msgs = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Activity trace:\n{compact(R[(r.account, r.day)])}"}]
        k = prompt_key(model, msgs, MAX_TOKENS, sig)
        keymap[(r.account, r.day)] = k
        items.append((f"{r.account}|{r.day}", [(k, msgs)]))
    chars = sum(len(m[1]["content"]) + len(m[0]["content"]) for _, c in items for _, m in c)
    print(f"{corpus}: {len(items)} account-days, ~{chars / 4 / 1e6:.1f}M input tokens (chars/4)", flush=True)
    if dry:
        return chars
    cache = PromptCache(CACHE)
    is_openai = model.startswith("openai/")

    def extra(cid):
        e = dict(cfg["extra"])
        if is_openai:
            e["prompt_cache_key"] = "r4mole"
        return e or None
    for _ in range(3):
        asyncio.run(score_chains(items, model, cache, track="r4cs", concurrency=concurrency,
                                 max_tokens=cfg["call_max_tokens"] or MAX_TOKENS, logprobs=cfg["logprobs"],
                                 extra_fn=extra, tag=f"r4cs:mole:{corpus}:{name}"))
        if all(cache.get(k) for k in keymap.values()):
            break
    rows = []
    for (acct, day), k in keymap.items():
        rec = cache.get(k)
        rows.append(dict(account=acct, day=day, score=np.nan if rec is None else
                         (rec["expected"] if rec["lp_ok"] else float(rec["int_score"])),
                         int_score=None if rec is None else rec["int_score"],
                         lp_ok=None if rec is None else rec["lp_ok"]))
    out = pd.DataFrame(rows)
    fn = f"llm_{slug(model)}_compact{'_pilot' if pilot else ''}{f'_sub{subset}' if subset else ''}.parquet"
    out.to_parquet(d / fn, index=False)
    print(f"wrote {corpus}/{fn}: {out.score.notna().sum()}/{len(out)} scored", flush=True)
    return chars


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor", required=True, choices=list(MONITORS))
    ap.add_argument("--corpora", default=",".join(CORPORA))
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--subset-routine", type=int, default=0,
                    help="budget-aware subset: all solo insiders + this many random routine accounts (seed 4)")
    a = ap.parse_args()
    tot = 0
    for c in a.corpora.split(","):
        tot += score_corpus(c, a.monitor, a.concurrency, a.pilot, a.dry_run, a.subset_routine)
    print(f"total ~{tot / 4 / 1e6:.1f}M input tokens (chars/4)")


if __name__ == "__main__":
    main()
