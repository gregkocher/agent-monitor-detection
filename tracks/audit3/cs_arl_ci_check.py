"""Audit pass 3 (track r4_cs): how much of the ARL bootstrap width is split noise?

    unset VIRTUAL_ENV; uv run python tracks/audit3/cs_arl_ci_check.py

ps_arl.py reports point = mean over 10 calibration / test splits, CI = percentiles of 200 replicates that each
use ONE random split of a resampled data set. The replicate spread therefore contains the full single-split
calibration-split variance, while the point estimate averages 10 splits. Approximate split-averaged interval:
var_10 ~= var_boot - (1 - 1/10) * var_split, with var_split = variance of the 10 point splits; reported as a
normal interval point ± 1.96 sqrt(var_10). Also: bootstrap mean − point. Reads the committed
results/r4_cs/arl_replicates.csv.gz only.
Output: results/audit3/cs_arl_ci_check.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
POOL = ["gpt-4.1-mini", "gemini-2.5-flash", "qwen3-235b", "gpt-4.1", "claude-haiku-4.5", "gemini-2.5-pro",
        "gpt-5-mini", "claude-haiku-5.5", "gpt-6-luna"]


def main():
    R = pd.read_csv(REPO / "results" / "r4_cs" / "arl_replicates.csv.gz")
    R = R[R.detector != "nested_best_forgetting"]
    piv = R.pivot_table(index=["kind", "rep", "monitor", "alpha"], columns="detector", values="det")
    D = piv.sub(piv["max"], axis=0).drop(columns="max").reset_index()
    meta = pd.read_csv(REPO / "results" / "r4_cs" / "arl_meta.csv")
    rows = []
    for al in (0.05, 0.01):
        for det in ("cusum_k0.5", "wtop3_w5", "ewma_l0.2", "sr_d1", "cusum_k1.5"):
            w = None
            m = meta[(meta.alpha == al) & (meta.detector == det)]
            # recover RE weights as ps_arl does is not stored; use per-monitor inverse variance of iid replicates
            for mon in ["gpt-4.1-mini", "pooled(inv-var of iid reps)"]:
                if mon.startswith("pooled"):
                    P = D[(D.alpha == al)].pivot_table(index=["kind", "rep"], columns="monitor", values=det)[POOL]
                    se = P.loc["iid"].std()
                    w = (1 / se**2) / (1 / se**2).sum()
                    x = (P * w).sum(1)
                    pt, bi = x.loc["point"], x.loc["iid"]
                else:
                    g = D[(D.monitor == mon) & (D.alpha == al)].set_index(["kind", "rep"])[det]
                    pt, bi = g.loc["point"], g.loc["iid"]
                vb, vs = bi.var(ddof=1), pt.var(ddof=1)
                v10 = max(vb - (1 - 1 / len(pt)) * vs, 0)
                rows.append(dict(alpha=al, detector=det, unit=mon, point=pt.mean(), boot_lo=bi.quantile(.025),
                                 boot_hi=bi.quantile(.975), boot_sd=np.sqrt(vb), split_sd=np.sqrt(vs),
                                 boot_mean_minus_point=bi.mean() - pt.mean(), sd_split_avg=np.sqrt(v10),
                                 approx_lo=pt.mean() - 1.96 * np.sqrt(v10), approx_hi=pt.mean() + 1.96 * np.sqrt(v10),
                                 committed_joint_lo=m[m.boot == "iid"].joint_lo.iloc[0] if mon.startswith("pooled") else np.nan,
                                 committed_joint_hi=m[m.boot == "iid"].joint_hi.iloc[0] if mon.startswith("pooled") else np.nan))
    O = pd.DataFrame(rows)
    O.to_csv(REPO / "results" / "audit3" / "cs_arl_ci_check.csv", index=False)
    print(O.round(3).to_string())


if __name__ == "__main__":
    main()
