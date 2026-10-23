"""r5_jev preregistered primary analysis (tracks/r5_jev/analyze_primary.py, unchanged) under a chosen threshold
convention. Outputs redirected to results/fixes2/jev_primary_<convention>_thrfix/ (hypotheses.csv,
cascade_cells.csv, panels.csv) and replicate pickles to data/fixes2/jev_boot_<convention>/ (gitignored).

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.jev_primary --convention plugin     # reproduces results/r5_jev
    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.jev_primary --convention conformal
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from amd.common.schema import DATA, REPO

import tracks.r5_jev.analyze_primary as AP

from .jev_patch import use_convention


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--convention", choices=("plugin", "conformal"), required=True)
    a, rest = ap.parse_known_args()
    use_convention(a.convention)
    AP.OUT = REPO / "results" / "fixes2" / f"jev_primary_{a.convention}_thrfix"
    AP.BOOT = DATA / "fixes2" / f"jev_boot_{a.convention}"
    Path(AP.OUT).mkdir(parents=True, exist_ok=True)
    Path(AP.BOOT).mkdir(parents=True, exist_ok=True)
    AP.frozen = lambda: ("B_w3", "bs")      # = results/r5_jev/dev_choice.json (read-only)
    sys.argv = [sys.argv[0]] + rest
    AP.main()


if __name__ == "__main__":
    main()
