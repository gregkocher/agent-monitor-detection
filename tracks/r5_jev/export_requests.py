"""Export the frozen JEV per-step requests (identical state + questions) for the self-hosted decision model.

    unset VIRTUAL_ENV; uv run python -m tracks.r5_jev.export_requests --set eval --variant V --sources mb --out F
Only task text and step texts are exported (data/ is gitignored).
"""
import argparse
import json

from . import jevlib as J
from .score_jev import MB_MAX_STEPS, ids_for, load
from .splits import HERE

ap = argparse.ArgumentParser()
ap.add_argument("--set", required=True)
ap.add_argument("--variant", required=True)
ap.add_argument("--sources", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--subset", choices=["all", "nano"], default="all")
a = ap.parse_args()
spl = json.load(open(HERE / "splits.json"))["sources"]
n = 0
with open(a.out, "w") as f:
    for src in a.sources.split(","):
        ids = ids_for(spl[src], a.set)
        if a.subset == "nano":
            ids = set(spl[src]["nano_honest"]) | set(spl[src]["nano_attack"])
        trajs = sorted(load(src, ids), key=lambda t: t.traj_id)
        for j in J.plan(trajs, a.variant, MB_MAX_STEPS if src == "mb" else None):
            f.write(json.dumps({"key": f"{src}|{j.traj_id}|{j.step}", **j.req}) + "\n")
            n += 1
print("exported", n)
