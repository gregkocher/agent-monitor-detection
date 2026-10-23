"""Re-run the committed r4_wb / wb_whitebox / audit white-box analyses with only the threshold convention switched.

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.wb_rerun <job> --conv {plugin,conformal} [--B N]

Jobs (committed code, outputs redirected to results/fixes2/wb_<job>_<conv>_thrfix/):
  r4primary   tracks/r4_wb/analyze_primary.py            (H1 and secondaries; contrast_alpha via row_thresholds)
  r4a1        tracks/r4_wb/analyze_a1_mb.py              (A1 nominal / equal-FPR table on the pilot MB data)
  r4la        tracks/r4_wb/analyze_la_r4.py              (LinuxArena paired contrasts, Holm over 12 monitors)
  r4mole      tracks/r4_wb/analyze_mole_r4.py            (MOLE arms incl. TPR@5% session FPR)
  a3primary   tracks/audit3/wb_primary.py                (H1 at exactly 1.00% realized FPR for both)
  a3la        tracks/audit3/wb_la.py                     (LinuxArena nominal / equal-FPR versions)
  a3a1        tracks/audit3/wb_a1.py                     (A1 FIBS-axial-full at equal realized FPR)
  a3mole      tracks/audit3/wb_mole.py                   (MOLE TPR@5% contrasts M1-M5)
  wbfusion    tracks/wb_whitebox/analyze_fusion.py --probes sab --modes full   (track cascade, panel d)
  a2fusion    tracks/audit2/repro_wb_fusion.py main()    (audit-2 cascade reproduction, panel d value)
The plug-in run reproduces the committed numbers; the conformal run differs only in the threshold rule.
"""
from __future__ import annotations

import argparse
import importlib
import sys
import time

from .wb_common import a2lib_targets, convention, outdir, r4lib_targets, redirect_writes, wb_lib_targets

A3_IMPORTERS = ("tracks.audit3.wb_lib", "tracks.audit3.wb_primary", "tracks.audit3.wb_la", "tracks.audit3.wb_a1",
                "tracks.audit3.wb_mole")


def run(job, conv, B=None):
    dest = outdir(job, conv)
    t0 = time.time()
    if job.startswith("r4"):
        mod = importlib.import_module({"r4primary": "tracks.r4_wb.analyze_primary", "r4a1": "tracks.r4_wb.analyze_a1_mb",
                                       "r4la": "tracks.r4_wb.analyze_la_r4",
                                       "r4mole": "tracks.r4_wb.analyze_mole_r4"}[job])
        old = mod.OUT
        mod.OUT = dest
        try:
            with convention(conv, r4lib_targets()), redirect_writes(dest, [mod.__name__]):
                mod.main()
        finally:
            mod.OUT = old
    elif job.startswith("a3"):
        name = {"a3primary": "wb_primary", "a3la": "wb_la", "a3a1": "wb_a1", "a3mole": "wb_mole"}[job]
        mod = importlib.import_module(f"tracks.audit3.{name}")
        sys.argv = [name] + ([f"--B={B}"] if B and name in ("wb_primary", "wb_la") else [])
        with convention(conv, wb_lib_targets(conv, A3_IMPORTERS)), redirect_writes(dest, [mod.__name__]):
            mod.main()
    elif job == "wbfusion":
        mod = importlib.import_module("tracks.wb_whitebox.analyze_fusion")
        old = mod.OUT
        mod.OUT = dest
        sys.argv = ["analyze_fusion", "--probes", "sab", "--modes", "full"] + ([f"--n-boot={B}"] if B else [])
        try:
            with convention(conv), redirect_writes(dest, [mod.__name__]):
                mod.main()
        finally:
            mod.OUT = old
    elif job == "a2fusion":
        mod = importlib.import_module("tracks.audit2.repro_wb_fusion")
        with convention(conv, a2lib_targets(conv, ("tracks.audit2.a2lib", mod.__name__))), \
                redirect_writes(dest, [mod.__name__]):
            mod.main(**({"B": B} if B else {}))
    else:
        raise SystemExit(f"unknown job {job}")
    print(f"[{job} {conv}] done in {time.time() - t0:.0f}s -> {dest}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--conv", default="conformal", choices=("plugin", "conformal"))
    ap.add_argument("--B", type=int, default=None)
    a = ap.parse_args()
    run(a.job, a.conv, a.B)
