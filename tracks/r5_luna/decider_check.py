"""Hosted vs self-hosted Perplexity Decider v1.2 (sanity check, not a hypothesis).

Sends a seeded sample of N frozen DEV requests (data/r5_jev/dev_req_A_w3.jsonl, the exact requests the round-1 pod
scored; outputs in data/r5_jev/decider/dev_out_A_w3.jsonl, bf16, one H100) to the hosted model
perplexity/pplx-decider-v1.2 through the OpenRouter Decisions API, and compares P(suspicious) per question
(benign-first `bs`, suspicious-first `sb`, and their mean): Pearson / Spearman, mean and max absolute difference, label
agreement (argmax), agreement of the top-decile flag (within-sample 90th percentile of each), and a stratified view by
source. Track r5luna. Cache data/r5_luna/cache/decider_dev.sqlite (resumable).

    unset VIRTUAL_ENV; uv run python -m tracks.r5_luna.decider_check --n 500
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

from amd.common.schema import DATA, REPO
from amd.scoring.cache import ScoreCache

from . import lunalib as L

OUT = REPO / "results" / "r5_luna"


def ps(ans, q):
    p = (ans.get(q) or {}).get("probabilities") or {}
    s, b = float(p.get("suspicious", np.nan)), float(p.get("benign", np.nan))
    return s / (s + b) if s + b > 0 else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    a = ap.parse_args()
    pod = {}
    for line in open(DATA / "r5_jev" / "decider" / "dev_out_A_w3.jsonl"):
        d = json.loads(line)
        pod[d["key"]] = d
    keys = sorted(random.Random(20261023).sample(sorted(pod), min(a.n, len(pod))))
    want = set(keys)
    reqs = {}
    for line in open(DATA / "r5_jev" / "dev_req_A_w3.jsonl"):
        d = json.loads(line)
        if d["key"] in want:
            reqs[d["key"]] = d
    cache = ScoreCache(L.CACHE_DIR / "decider_dev.sqlite")
    mid = L.MODELS["decider"] + "|r5-A_w3|both-orders|dev"
    todo = [k for k in keys if cache.get(k, 0, mid) is None]
    print(f"{len(keys)} keys, todo {len(todo)}", flush=True)

    async def go():
        from amd.common.openrouter import OpenRouter
        async with OpenRouter(track=L.TRACK, concurrency=24, tag="r5luna:decider_dev") as orc:
            async def one(k):
                try:
                    r = await orc.decisions(L.MODELS["decider"], reqs[k]["state"], reqs[k]["questions"])
                    cache.put(k, 0, mid, "ok", {"answers": r["answers"], "model": r["model"],
                                                "in_tok": r["usage"].get("input_tokens"), "cost": r["cost"]})
                except Exception as e:  # noqa: BLE001
                    print("error", k, str(e)[:200], flush=True)
            await asyncio.gather(*[one(k) for k in todo])
    if todo:
        asyncio.run(go())
    rows = []
    for k in keys:
        c = cache.get(k, 0, mid)
        if c is None:
            continue
        h, p = c[1], pod[k]
        row = dict(key=k, source=k.split("|")[0], version=h["model"], in_tok_hosted=h["in_tok"], in_tok_pod=p["in_tok"])
        for q in ("verdict_bs", "verdict_sb"):
            row[f"pod_{q}"] = ps(p["answers"], q)
            row[f"hosted_{q}"] = ps(h["answers"], q)
        row["pod_avg"] = 0.5 * (row["pod_verdict_bs"] + row["pod_verdict_sb"])
        row["hosted_avg"] = 0.5 * (row["hosted_verdict_bs"] + row["hosted_verdict_sb"])
        rows.append(row)
    cache.close()
    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.drop(columns=["key"]).to_csv(L.ROOT / "decider_check_rows.csv", index=False)   # raw rows stay in data/
    summ = []
    for grp, g in [("all", df)] + list(df.groupby("source")):
        for q in ("verdict_bs", "verdict_sb", "avg"):
            x, y = g[f"pod_{q}"].values, g[f"hosted_{q}"].values
            ok = np.isfinite(x) & np.isfinite(y)
            x, y = x[ok], y[ok]
            if len(x) < 5:
                continue
            qx, qy = np.quantile(x, 0.9), np.quantile(y, 0.9)
            summ.append(dict(group=grp, question=q, n=len(x), pearson=pearsonr(x, y)[0], spearman=spearmanr(x, y)[0],
                             mean_pod=x.mean(), mean_hosted=y.mean(), mean_abs_diff=np.abs(x - y).mean(),
                             median_abs_diff=np.median(np.abs(x - y)), max_abs_diff=np.abs(x - y).max(),
                             label_agree=((x > 0.5) == (y > 0.5)).mean(),
                             top10_agree=((x > qx) == (y > qy)).mean(),
                             identical_to_1e6=(np.abs(x - y) < 1e-6).mean()))
    S = pd.DataFrame(summ)
    S.to_csv(OUT / "decider_hosted_vs_pod.csv", index=False)
    print("versions", df.version.value_counts().to_dict(), "tok hosted/pod", df.in_tok_hosted.sum() / df.in_tok_pod.sum())
    print(S.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
