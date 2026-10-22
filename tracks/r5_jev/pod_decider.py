"""Pod-side scorer: Perplexity Decider v1.2 (perplexity-ai/pplx-decider-v1.2, Apache-2.0) on exported requests.

Input JSONL: {"key", "state", "questions"} (the frozen JEV request, unchanged). Output JSONL: {"key", "answers",
"in_tok"}; resumable (keys already in the output are skipped). bf16, fast path (packing + compile), one request
per item (no grouping across steps).

    python pod_decider.py --inp req.jsonl --out out.jsonl [--limit N] [--chunk 512]
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, "/root/decider/source/src")
from pplx_decider import Decider  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--inp", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--limit", type=int)
ap.add_argument("--chunk", type=int, default=512)
ap.add_argument("--no-fast", action="store_true")
a = ap.parse_args()

done = set()
if os.path.exists(a.out):
    for line in open(a.out):
        try:
            done.add(json.loads(line)["key"])
        except Exception:
            pass
reqs = [json.loads(l) for l in open(a.inp)]
reqs = [r for r in reqs if r["key"] not in done][: a.limit]
print(f"todo {len(reqs)} (done {len(done)})", flush=True)
t0 = time.time()
dec = Decider.from_pretrained("/root/decider", device="cuda", fast=not a.no_fast)
if not a.no_fast:
    dec.warmup()
print(f"loaded in {time.time() - t0:.0f}s", flush=True)
t0 = time.time()
n = 0
with open(a.out, "a") as f:
    for i in range(0, len(reqs), a.chunk):
        batch = reqs[i:i + a.chunk]
        res = dec.decide([{"state": r["state"], "questions": r["questions"]} for r in batch])
        for r, x in zip(batch, res):
            f.write(json.dumps({"key": r["key"], "answers": x["answers"],
                                "in_tok": x.get("usage", {}).get("input_tokens")}) + "\n")
        f.flush()
        n += len(batch)
        el = time.time() - t0
        print(f"{n}/{len(reqs)} {el:.0f}s {n / el:.2f} req/s", flush=True)
print("DONE", flush=True)
