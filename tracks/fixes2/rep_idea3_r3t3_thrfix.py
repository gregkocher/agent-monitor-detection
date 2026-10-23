"""Threshold-convention rerun of the Idea-3 overview rows (a) and (b) (docs/reports/src/make_overview_fig.py panel c):
  (a) "Uninformed rewrite - original (gemini, strict)" -0.37 [-0.55, -0.19]
      = tracks/r3_t3/paired_contrasts.py, control/gemini - original, max, alpha 0.01 (results/r3_t3/paired_contrasts.md),
        also reproduced by tracks/audit2/repro_t3r3.py (strict_US row, results/audit2/repro_t3r3.csv);
  (b) "same, detection only (valid rewrites)" -0.143 [-0.300, -0.027]
      = tracks/audit2/repro_t3r3.py, detection_only row (audit2 corrections A4).

Part 1 (r3_t3 track code): paired_contrast_bootstrap(method="randomized") follows the convention flag; output dir
(paired_contrasts.RESULTS) redirected to results/fixes2/rep_r3t3_<conv>_thrfix/. Seeds/B as committed (B = 2000).
Part 2 (audit2 code): its private plug-in copy (a2lib rand_threshold / alarm) is swapped for the conformal
randomized rule in the module namespace; its hardcoded CSV path is redirected via rep_thrfix_lib.RedirectPD to
results/fixes2/rep_audit2_t3r3_<conv>_thrfix/. Seeds/B as committed (B = 2000).

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.rep_idea3_r3t3_thrfix --convention plugin
    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.rep_idea3_r3t3_thrfix --convention conformal
"""
from __future__ import annotations

import argparse

import tracks.audit2.repro_t3r3 as a2
import tracks.r3_t3.paired_contrasts as pc
from amd.evaluation.calibration import threshold_convention
from tracks.fixes2.rep_thrfix_lib import OUT, RedirectPD, conformal_a2lib


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--convention", choices=("plugin", "conformal"), required=True)
    ap.add_argument("--part", choices=("both", "r3t3", "audit2"), default="both")
    a = ap.parse_args(argv)
    if a.part in ("both", "r3t3"):
        out1 = OUT / f"rep_r3t3_{a.convention}_thrfix"
        out1.mkdir(parents=True, exist_ok=True)
        pc.RESULTS = out1
        with threshold_convention(a.convention):
            pc.main([])
    if a.part in ("both", "audit2"):
        a2.pd = RedirectPD(OUT / f"rep_audit2_t3r3_{a.convention}_thrfix")
        with conformal_a2lib(a2, enabled=(a.convention == "conformal")):
            a2.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
