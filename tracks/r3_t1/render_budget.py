"""Token budget of compact MOLE renderings (first E events, each line cut to L chars) vs the MOLE default."""
import json
import sys

from amd.common.schema import PROCESSED

c = sys.argv[1]
R = [json.loads(x)["text"] for x in open(PROCESSED / "r2_mole" / c / "renders.jsonl")]
base = sum(len(t) for t in R)
for E, L in ((400, 10**9), (400, 300), (400, 250), (300, 250), (250, 250), (200, 300), (400, 200)):
    tot = sum(sum(len(l[:L]) + 1 for l in t.split("\n")[:E]) for t in R)
    print(c, f"E={E} L={L}", f"{tot / 4 / 1e6:.1f}M tok ({tot / base:.2f} of default)")
