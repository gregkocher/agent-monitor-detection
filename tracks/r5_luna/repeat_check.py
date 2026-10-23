"""Repeatability of a decision model on identical requests (dev only): re-send N cached dev requests and compare the
returned P(suspicious) with the cached answer. Matters for the full-text arm, which reuses the frozen answer whenever
the full request equals the frozen one.

    unset VIRTUAL_ENV; uv run python -m tracks.r5_luna.repeat_check --model luna --n 100
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random

import numpy as np

from tracks.r5_jev.score_jev import load
from tracks.r5_jev.splits import HERE

from . import lunalib as L
from .score import select_ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="luna")
    ap.add_argument("--n", type=int, default=100)
    a = ap.parse_args()
    spl = json.load(open(HERE / "splits.json"))["sources"]
    rng = random.Random(7)
    pairs = []
    for src in ["mb", "akshn_linuxarena", "akshn_basharena_opus46", "akshn_shade"]:
        ids = select_ids(spl, src, "dev", "nano", (8, 8))
        trajs = sorted(load(src, ids), key=lambda t: t.traj_id)
        jobs = L.plan(trajs, L.MB_MAX_STEPS if src == "mb" else None)
        cache = L.cache_for(a.model, src)
        mid = L.monitor_id(a.model)
        have = [(j, cache.get(j.traj_id, j.step, mid)) for j in jobs]
        have = [(j, c[1]) for j, c in have if c and c[1].get("sha") == j.sha]
        pairs += [(src, j, c) for j, c in rng.sample(have, min(a.n // 4, len(have)))]
        cache.close()

    async def go():
        from amd.common.openrouter import OpenRouter
        async with OpenRouter(track=L.TRACK, concurrency=16, tag="r5luna:repeat") as orc:
            return await asyncio.gather(*[orc.decisions(L.MODELS[a.model], j.req["state"], j.req["questions"])
                                          for _, j, _ in pairs])
    res = asyncio.run(go())
    p0 = np.array([L.p_susp(c) for _, _, c in pairs])
    p1 = np.array([L.p_susp({"answers": r["answers"]}) for r in res])
    d = np.abs(p1 - p0)
    out = dict(model=a.model, n=len(pairs), identical=float((d < 1e-9).mean()), mean_abs_diff=float(d.mean()),
               max_abs_diff=float(d.max()), pearson=float(np.corrcoef(p0, p1)[0, 1]),
               versions=sorted({r["model"] for r in res}))
    print(json.dumps(out))
    (L.ROOT / f"repeat_check_{a.model}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
