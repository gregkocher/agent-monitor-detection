"""Overview panel (d), reader-vs-LLM rows from results/wb/mb_paired.csv (kind vs_llm, detector max, alpha 0.01):
FIBS axial follow-up `none` (+0.206 [0.09, 0.32]) and sab `full` (+0.098 [0.015, 0.163]).

Same code path as tracks/wb_whitebox/analyze_paired.py (its `load()` of the analyze_mb raw pickles, and
amd.evaluation.paired.paired_contrast_bootstrap with seed=7, B=1000, task-cluster groups), restricted to these two
rows; run under the plug-in convention (reproduces mb_paired.csv) and the conformal convention. Realized FPR =
split-mean alarm rate of the calibration-half threshold on the held-out honest half (as matched_budget_eval).

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.wb_panel_d
Output results/fixes2/wb_panel_d_thrfix.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from amd.evaluation import calibrate, threshold_convention
from amd.evaluation.paired import paired_contrast_bootstrap
from tracks.wb_whitebox.analyze_paired import load

from .wb_common import OUT_ROOT

ROWS = [("FIBS axial follow-up, none", "none", "fibs_fu_ax"), ("sab, full", "full", "sab")]


def realized(raw, alpha, det="max"):
    return float(np.mean([calibrate(r["cal"], alpha, "randomized").rate(np.asarray(r["test"], float))
                          for r in raw if r["detector"] == det]))


def tpr(raw, alpha, det="max"):
    return float(np.mean([calibrate(r["cal"], alpha, "randomized").rate(np.asarray(r["attack"], float))
                          for r in raw if r["detector"] == det]))


def main(B=1000, alpha=0.01):
    R, meta = load()
    hg, ag = meta["honest_groups"], meta["attack_groups"]
    kw = dict(n_honest=len(hg), n_attack=len(ag), honest_groups=hg, attack_groups=ag, n_boot=B)
    out = []
    for conv in ("plugin", "conformal"):
        with threshold_convention(conv):
            for label, mode, st in ROWS:
                raw, rl = R[(mode, st)], R[(mode, "llm")]
                r = paired_contrast_bootstrap([(1.0, raw, "max"), (-1.0, rl, "max")], alpha=alpha, seed=7, **kw)
                out.append(dict(conv=conv, row=label, mode=mode, stream=st, alpha=alpha, est=r["est"], lo=r["lo"],
                                hi=r["hi"], p_le0=r["p_le0"], n_splits=r["n_splits"], n_boot=B,
                                tpr_reader=tpr(raw, alpha), tpr_llm=tpr(rl, alpha),
                                fpr_reader=realized(raw, alpha), fpr_llm=realized(rl, alpha),
                                n_cal_mean=float(np.mean([len(x["cal"]) for x in raw if x["detector"] == "max"]))))
                print(out[-1], flush=True)
    df = pd.DataFrame(out)
    df.to_csv(OUT_ROOT / "wb_panel_d_thrfix.csv", index=False)
    print(df.round(4).to_string())


if __name__ == "__main__":
    main()
