"""Threshold-convention rerun of the audit-3 independent re-implementation of the r4_cs pooled contrast
(tracks/audit3/cs_indep_ps.py: pooled top-3 sum - max at FPR 0.05, reported -0.074 [-0.151, +0.010], app_indep).

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.cs_indep_ps_thrfix <plugin|conformal> [--splits 40] [--boot 2000]

cs_indep_ps has its OWN vectorized plug-in rule (rand_thr -> (h, g); alarm = (S > h) + g (S == h)), which the
convention flag does not reach. Under "conformal" both module functions are monkeypatched with the smoothed
conformal rule from amd.evaluation.calibration (smoothed_rows_shared over the same integer bootstrap multiplicities,
masses in trajectory units); under "plugin" the module runs unchanged. Outputs (OUT) are redirected to
results/fixes2/cs_indep_ps_<conv>_thrfix/.
"""
from __future__ import annotations

import importlib.util
import sys

import numpy as np

from amd.common.schema import REPO
from amd.evaluation.calibration import RowThresholds, smoothed_rows_shared


def main():
    conv = sys.argv[1]
    assert conv in ("plugin", "conformal"), conv
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    spec = importlib.util.spec_from_file_location("audit3_cs_indep_ps", REPO / "tracks" / "audit3" / "cs_indep_ps.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    m.OUT = REPO / "results" / "fixes2" / f"cs_indep_ps_{conv}_thrfix"
    m.OUT.mkdir(parents=True, exist_ok=True)
    if conv == "conformal":
        plug_alarm = m.alarm

        def rand_thr(cal, W, alpha):
            return smoothed_rows_shared(np.asarray(cal, float), np.asarray(W, float), alpha), None

        def alarm(s, h, g):
            return h.alarm(np.asarray(s, float)) if isinstance(h, RowThresholds) else plug_alarm(s, h, g)

        m.rand_thr, m.alarm = rand_thr, alarm
    m.main()


if __name__ == "__main__":
    main()
