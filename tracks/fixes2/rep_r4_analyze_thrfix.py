"""Threshold-convention rerun of tracks/r4_replay/analyze.py (committed code, cached scores + replay verdicts).

The track's contrasts go through amd.evaluation.paired.paired_contrast_bootstrap(method="randomized"), which
follows the active threshold convention, so the only change is `threshold_convention(<conv>)` around main().
Outputs are redirected (an.RESULTS) to results/fixes2/rep_r4_analyze_<conv>_thrfix/; replay JSONs are still read
from results/r4_replay/<arm>/ (an.RAWRES), nothing there is written. Same seeds and B (4000) as the track.
The track's own `realized_fpr` column uses an np.quantile threshold on 50/50 splits (not the procedure used);
the realized FPR of the actual rule is computed separately in rep_r4_fpr_thrfix.

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.rep_r4_analyze_thrfix --convention plugin
    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.rep_r4_analyze_thrfix --convention conformal
"""
from __future__ import annotations

import argparse

import tracks.r4_replay.analyze as an
from amd.evaluation.calibration import threshold_convention
from tracks.fixes2.rep_thrfix_lib import OUT


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--convention", choices=("plugin", "conformal"), required=True)
    ap.add_argument("--n-boot", type=int, default=4000)
    a = ap.parse_args(argv)
    out = OUT / f"rep_r4_analyze_{a.convention}_thrfix"
    out.mkdir(parents=True, exist_ok=True)
    an.RESULTS = out
    assert an.RAWRES != out
    with threshold_convention(a.convention):
        return an.main(["--arms", "rewrite_control,pace_max", "--n-boot", str(a.n_boot)])


if __name__ == "__main__":
    raise SystemExit(main())
