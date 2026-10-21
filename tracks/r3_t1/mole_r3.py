"""Round 3, part A: score every MOLE corpus with ONE history-free per-account-day monitor.

    uv run python tracks/r3_t1/mole_r3.py [--corpora a,b,...] [--model qwen/qwen3-235b-a22b-2507] [--pilot N]

Monitor: the round-2 MOLE judge prompt (tracks/r2_t1/mole_score.py: MOLE level-2 system prompt + threat
taxonomy, `SCORE: 0-10`, logprob-expected) on a COMPACT audit-event rendering: the first E=250 events of the
account-day, each rendered line cut to L=250 chars (MOLE's default is 400 events with args <= 600 chars; the
compact form keeps ~0.5-0.6 of the tokens so all 8 corpora fit the budget). Providers are restricted to those
supporting logprobs (`require_parameters`; order GMICloud, Parasail -- both serve logprobs; Google Vertex 404s; the
provider of every call is recorded in the cache).

Per corpus (cheapest first): fetch the needed columns (tracks/r2_t1/mole_fetch.py) if not built, build account-days
+ renders (tracks/r2_t1/mole_build.py), score, write data/processed/r2_mole/<corpus>/llm_<slug>_compact.parquet,
then delete the corpus's raw downloads and its renders.jsonl (only for corpora this script built).
Resumable: content-addressed cache data/raw/r3_t1/mole_cache.sqlite.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "r2_t1"))
from llmcache import PromptCache, prompt_key, score_chains  # noqa: E402
from mole_score import SYSTEM  # noqa: E402

from amd.common.schema import PROCESSED, REPO  # noqa: E402

CACHE = REPO / "data" / "raw" / "r3_t1" / "mole_cache.sqlite"
RAW = REPO / "data" / "raw" / "r2_t1" / "mole"
E_MAX, L_MAX = 250, 250
PROMPT_ID = f"mole-judge-tax-v1-compact{E_MAX}x{L_MAX}"
MAX_TOKENS = 400
ORDER = ["gpt53_single_day", "gpt53_multiday", "deepseek_v4_flash_single_day", "deepseek_v4_flash_multiday",
         "qwen36_27b_multiday", "qwen36_27b_single_day", "kimi_k26_single_day", "kimi_k26_multiday"]
PRE_EXISTING = {"gpt53_single_day", "gpt53_multiday", "deepseek_v4_flash_single_day"}


def compact(text: str) -> str:
    return "\n".join(l[:L_MAX] for l in text.split("\n")[:E_MAX])


def slug(m):
    return m.replace("/", "_").replace(":", "_")


def ensure_built(corpus: str) -> bool:
    d = PROCESSED / "r2_mole" / corpus
    if (d / "accountdays.parquet").exists() and (d / "renders.jsonl").exists():
        return False
    py = [sys.executable]
    subprocess.run(py + [str(HERE.parent / "r2_t1" / "mole_fetch.py"), "--corpus", corpus], check=True)
    subprocess.run(py + [str(HERE.parent / "r2_t1" / "mole_build.py"), "--corpus", corpus], check=True)
    for kind in ("audit", "transcripts"):
        shutil.rmtree(RAW / kind / corpus, ignore_errors=True)
    return True


def score_corpus(corpus, model, concurrency, pilot=0):
    d = PROCESSED / "r2_mole" / corpus
    D = pd.read_parquet(d / "accountdays.parquet")
    R = {(r["account"], r["day"]): r["text"] for r in map(json.loads, open(d / "renders.jsonl"))}
    sel = D if not pilot else pd.concat([D[~D.is_insider].sample(pilot, random_state=0), D[D.attack_day].head(pilot // 2)])
    items, keymap = [], {}
    for r in sel.itertuples():
        msgs = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Activity trace:\n{compact(R[(r.account, r.day)])}"}]
        k = prompt_key(model, msgs, MAX_TOKENS, PROMPT_ID)
        keymap[(r.account, r.day)] = k
        items.append((f"{r.account}|{r.day}", [(k, msgs)]))
    chars = sum(len(m[1]["content"]) for _, c in items for _, m in c)
    print(f"{corpus}: {len(items)} account-days, ~{chars / 4 / 1e6:.1f}M input tokens", flush=True)
    cache = PromptCache(CACHE)
    extra = (lambda cid: {"provider": {"require_parameters": True, "allow_fallbacks": True,
                                       "order": ["gmicloud", "parasail"]}}) \
        if not model.startswith("openai/") else None
    for attempt in range(3):  # resumable passes (network errors / parse failures)
        asyncio.run(score_chains(items, model, cache, track="r3t1", concurrency=concurrency, max_tokens=MAX_TOKENS,
                                 logprobs=True, extra_fn=extra, tag=f"r3t1:mole:{corpus}"))
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
    name = f"llm_{slug(model)}_compact{'_pilot' if pilot else ''}.parquet"
    out.to_parquet(d / name, index=False)
    print(f"wrote {corpus}/{name}: {out.score.notna().sum()}/{len(out)} scored, lp share {out.lp_ok.mean():.2f}",
          flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpora", default=",".join(ORDER))
    ap.add_argument("--model", default="qwen/qwen3-235b-a22b-2507")
    ap.add_argument("--concurrency", type=int, default=96)
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--keep-renders", action="store_true")
    a = ap.parse_args()
    for c in a.corpora.split(","):
        built_here = ensure_built(c)
        score_corpus(c, a.model, a.concurrency, a.pilot)
        if not a.pilot and not a.keep_renders and (built_here or c not in PRE_EXISTING):
            (PROCESSED / "r2_mole" / c / "renders.jsonl").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
