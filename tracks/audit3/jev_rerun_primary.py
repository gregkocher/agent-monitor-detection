"""Audit pass 3: rerun of the preregistered r5jev primary analysis from committed code + cached scores.

    unset VIRTUAL_ENV; uv run python -m tracks.audit3.jev_rerun_primary [--splits 50] [--boot 1000]

Runs tracks.r5_jev.analyze_primary.main() unchanged, but redirects its outputs to results/audit3/jev_rerun/ and its
replicate pickle to data/audit3/ (gitignored), so the original results are untouched. The comparison with the
committed results/r5_jev tables is done in tracks/audit3/jev_checks.py.
"""
from pathlib import Path

from amd.common.schema import DATA, REPO

import tracks.r5_jev.analyze_primary as AP

AP.OUT = REPO / "results" / "audit3" / "jev_rerun"
AP.BOOT = DATA / "audit3" / "r5_jev_boot"
Path(AP.BOOT).mkdir(parents=True, exist_ok=True)
Path(AP.OUT).mkdir(parents=True, exist_ok=True)
AP.frozen = lambda: ("B_w3", "bs")   # = results/r5_jev/dev_choice.json (read-only)

if __name__ == "__main__":
    AP.main()
