"""Threshold-convention rerun (track r4_cs, goal 1): the committed tracks/r4_cs/ps_multi.py, unchanged, under the
plug-in (reproduction) or the conformal randomized threshold convention.

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.cs_ps_multi_thrfix <plugin|conformal> [--splits 40] [--boot 2000]

ps_multi uses t1lib.run_matched -> amd.evaluation.matched_budget_eval(method="randomized") and
amd.evaluation.paired.paired_contrast_bootstrap(method="randomized"); both resolve "randomized" through the active
convention (calibrate / row_thresholds), so the switch is `with threshold_convention(conv)` around main(). Splits,
cross-fitted whitening and bootstrap weights do not depend on the convention (no RNG use in the threshold rule).
Outputs are redirected: tables -> results/fixes2/cs_ps_multi_<conv>_thrfix/, raw pickle -> data/raw/fixes2_cs/.
"""
from __future__ import annotations

import importlib.util
import sys

from amd.common.schema import REPO
from amd.evaluation.calibration import threshold_convention

R4 = REPO / "tracks" / "r4_cs"


def load_r4(name):
    """Import tracks/r4_cs/<name>.py by path (sibling dirs on sys.path hold modules with the same names)."""
    if str(R4) not in sys.path:
        sys.path.insert(0, str(R4))
    spec = importlib.util.spec_from_file_location(f"r4cs_{name}", R4 / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    conv = sys.argv[1]
    assert conv in ("plugin", "conformal"), conv
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    out = REPO / "results" / "fixes2" / f"cs_ps_multi_{conv}_thrfix"
    raw = REPO / "data" / "raw" / "fixes2_cs" / f"ps_multi_{conv}"
    out.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(R4))
    import r4lib
    r4lib.OUT, r4lib.RAW = out, raw
    m = load_r4("ps_multi")
    m.OUT, m.RAW = out, raw
    with threshold_convention(conv):
        m.main()


if __name__ == "__main__":
    main()
