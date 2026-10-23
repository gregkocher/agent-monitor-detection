"""Pre-specified held-out subset for H5c (generative Luna vs Luna Decisions), chosen on metadata only.

  mb                       every evaluation honest trajectory (511) + a seeded random 400 of the evaluation attacks
  akshn_basharena_opus46   every evaluation trajectory (418 honest / 489 attacks)
  akshn_linuxarena         the round-1 nano subset (500 honest / 300 attacks)

    unset VIRTUAL_ENV; uv run python -m tracks.r5_luna.h5c_subset     -> tracks/r5_luna/h5c_subset.json
"""
import json
import random
from pathlib import Path

from tracks.r5_jev.splits import HERE

SEED = 20261023


def main():
    spl = json.load(open(HERE / "splits.json"))["sources"]
    rng = random.Random(SEED)
    out = {"seed": SEED, "sources": {
        "mb": {"honest": sorted(spl["mb"]["eval_honest"]),
               "attack": sorted(rng.sample(sorted(spl["mb"]["eval_attack"]), 400))},
        "akshn_basharena_opus46": {"honest": sorted(spl["akshn_basharena_opus46"]["eval_honest"]),
                                   "attack": sorted(spl["akshn_basharena_opus46"]["eval_attack"])},
        "akshn_linuxarena": {"honest": sorted(spl["akshn_linuxarena"]["nano_honest"]),
                             "attack": sorted(spl["akshn_linuxarena"]["nano_attack"])}}}
    p = Path(__file__).with_name("h5c_subset.json")
    p.write_text(json.dumps(out, indent=0))
    print({k: (len(v["honest"]), len(v["attack"])) for k, v in out["sources"].items()})


if __name__ == "__main__":
    main()
