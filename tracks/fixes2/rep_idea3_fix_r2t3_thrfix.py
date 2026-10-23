"""Threshold-convention rerun of the Idea-3 overview row (c) "Pacing - uninformed rewrite (one-shot, strict)"
+0.087 [-0.032, +0.183] = tracks/fixes/t3/fix_r2_t3.py pre-specified primary (pace_max_r0 - rewrite_control, max,
alpha 0.01, strict validity, paired n = 126, joint bootstrap; results/fixes/r2_t3/primary_contrast.csv).

fix_r2_t3 calibrates with amd.evaluation.calibrate(..., method="randomized") (alarm engine and held-out FPR), which
follows the convention flag, so the only change is `threshold_convention(<conv>)`. Its output globals OUT / OUT_T3
are redirected to results/fixes2/rep_fix_r2t3_<conv>_thrfix/{r2_t3,t3}. Same seeds, B = 2000, 200 holdout splits.

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.rep_idea3_fix_r2t3_thrfix --convention plugin
    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.rep_idea3_fix_r2t3_thrfix --convention conformal
"""
from __future__ import annotations

import argparse
import importlib
import sys

from amd.evaluation.calibration import threshold_convention
from tracks.fixes2.rep_thrfix_lib import OUT, REPO


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--convention", choices=("plugin", "conformal"), required=True)
    ap.add_argument("--boot", type=int, default=2000)
    a = ap.parse_args(argv)
    sys.path.insert(0, str(REPO / "tracks" / "fixes" / "t3"))   # the script imports t3fix_common top-level
    fx = importlib.import_module("tracks.fixes.t3.fix_r2_t3")
    base = OUT / f"rep_fix_r2t3_{a.convention}_thrfix"
    fx.OUT, fx.OUT_T3 = base / "r2_t3", base / "t3"
    with threshold_convention(a.convention):
        fx.main(["--boot", str(a.boot)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
