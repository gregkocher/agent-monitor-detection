"""Per-model r4cs spend from the private ledger (calls, $, $/call, mean in / out tokens).

    unset VIRTUAL_ENV; uv run python tracks/r4_cs/spend.py
"""
from __future__ import annotations

import collections
import json

from amd.common.openrouter import LEDGER


def main():
    c = collections.defaultdict(lambda: [0, 0.0, 0, 0])
    with open(LEDGER) as f:
        for line in f:
            if '"r4cs"' not in line:
                continue
            r = json.loads(line)
            x = c[(r.get("tag", "").split(":")[1] if ":" in r.get("tag", "") else "", r["model"])]
            x[0] += 1; x[1] += r["cost"]; x[2] += r.get("in") or 0; x[3] += r.get("out") or 0
    tot = 0.0
    for (part, m), v in sorted(c.items()):
        tot += v[1]
        print(f"{part:6s} {m:34s} n={v[0]:5d} ${v[1]:8.3f} ${v[1] / v[0]:.5f}/call in={v[2] // v[0]} out={v[3] // v[0]}")
    print(f"r4cs total ${tot:.2f}")


if __name__ == "__main__":
    main()
