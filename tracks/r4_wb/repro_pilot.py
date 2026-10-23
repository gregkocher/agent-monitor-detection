"""Re-run the pilot's LinuxArena and T3-r1 analyses on the regenerated reader streams (audit A2), writing to
results/r4_wb/repro/ instead of results/wb/, and compare with the published pilot tables.

Before running: the merged regenerated streams must be at data/processed/whitebox/scores/{la,t3}_{full,none}.jsonl
(install_regenerated() copies them from scores/r4/ only over EMPTY files - never over a non-empty file).

    unset VIRTUAL_ENV; uv run python -m tracks.r4_wb.repro_pilot
"""
from __future__ import annotations

import shutil

import pandas as pd

from amd.common.schema import REPO
from tracks.wb_whitebox import analyze_la, analyze_t3
from tracks.wb_whitebox.wblib import WB

OUT = REPO / "results" / "r4_wb" / "repro"
PILOT = REPO / "results" / "wb"


def install_regenerated():
    for src in ("la", "t3"):
        for mode in ("full", "none"):
            new = WB / "scores" / "r4" / f"{src}_{mode}.jsonl"
            old = WB / "scores" / f"{src}_{mode}.jsonl"
            assert new.exists() and new.stat().st_size > 0, new
            if old.exists() and old.stat().st_size > 0:
                print("kept existing non-empty", old)
                continue
            shutil.copyfile(new, old)
            print("installed", old, old.stat().st_size)


def main():
    install_regenerated()
    OUT.mkdir(parents=True, exist_ok=True)
    analyze_la.OUT = OUT
    analyze_la.main()
    analyze_t3.OUT = OUT
    analyze_t3.main()
    a_new = pd.read_csv(OUT / "la_auroc.csv").set_index("stream")
    a_old = pd.read_csv(PILOT / "la_auroc.csv").set_index("stream")
    cmp = a_old[["auroc_max"]].join(a_new[["auroc_max"]], rsuffix="_regen").dropna()
    cmp["diff"] = cmp.auroc_max_regen - cmp.auroc_max
    m_new = pd.read_csv(OUT / "la_matched.csv")
    m_old = pd.read_csv(PILOT / "la_matched.csv")
    k = ["stream", "detector", "alpha", "threshold_kind"]
    mm = m_old[k + ["tpr"]].merge(m_new[k + ["tpr"]], on=k, suffixes=("", "_regen"))
    mm = mm[(mm.detector == "max") & (mm.threshold_kind == "calibrated") & mm.stream.str.startswith("wb:")]
    mm["diff"] = mm.tpr_regen - mm.tpr
    t_new = pd.read_csv(OUT / "t3_detection.csv")
    t_old = pd.read_csv(PILOT / "t3_detection.csv")
    k = ["block", "mode", "stream", "stat", "alpha", "arm"]
    tt = t_old[k + ["detect"]].merge(t_new[k + ["detect"]], on=k, suffixes=("", "_regen"))
    tt = tt[tt.block == "r1"]
    tt["diff"] = tt.detect_regen - tt.detect
    cmp.to_csv(OUT / "cmp_la_auroc.csv")
    mm.to_csv(OUT / "cmp_la_tpr.csv", index=False)
    tt.to_csv(OUT / "cmp_t3r1_detect.csv", index=False)
    print(cmp.round(3).to_string())
    print(mm.round(3).to_string())
    print("T3 r1 rows", len(tt), "max |diff|", tt["diff"].abs().max(), "mean |diff|", tt["diff"].abs().mean())


if __name__ == "__main__":
    main()
