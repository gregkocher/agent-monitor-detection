"""Spend of track r5luna by component (from the out-of-repo ledger) -> results/r5_luna/spend.csv.

    unset VIRTUAL_ENV; uv run python -m tracks.r5_luna.spend
"""
import json
from collections import defaultdict

import pandas as pd

from amd.common.openrouter import LEDGER
from amd.common.schema import REPO


def component(tag, model):
    if "probe" in tag or "repeat" in tag:
        return "dev: API probe / repeatability"
    if tag.startswith("r5luna:dev:"):
        return f"dev: {model} {'full-text' if ':full:' in tag else 'frozen'}"
    if tag.startswith("r5luna:gen:dev"):
        return "dev: generative Luna"
    if tag.startswith("r5luna:gen:mb_all"):
        return "addendum: generative Luna, rest of MB (held-out)"
    if tag.startswith("r5luna:gen:h5c"):
        return "H5c: generative Luna (held-out)"
    if "decider_dev" in tag:
        return "hosted Decider check (dev)"
    if tag.startswith("r5luna:eval:full"):
        return f"H5d: {model} full-text (held-out)"
    if tag.startswith("r5luna:eval:frozen"):
        return f"H5a/b: {model} frozen (held-out)"
    return tag


def main():
    agg = defaultdict(lambda: [0, 0.0, 0])
    for line in open(LEDGER):
        r = json.loads(line)
        if r.get("track") != "r5luna":
            continue
        k = component(r.get("tag", ""), r.get("model", ""))
        agg[k][0] += 1
        agg[k][1] += float(r.get("cost") or 0)
        agg[k][2] += int(r.get("in") or 0)
    df = pd.DataFrame([dict(component=k, calls=v[0], cost_usd=round(v[1], 2), input_tokens=v[2]) for k, v in agg.items()])
    df = df.sort_values("component")
    df.to_csv(REPO / "results" / "r5_luna" / "spend.csv", index=False)
    print(df.to_string(index=False))
    print("total", round(df.cost_usd.sum(), 2))


if __name__ == "__main__":
    main()
