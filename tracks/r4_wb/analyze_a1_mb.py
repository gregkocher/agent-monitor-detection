"""Audit A1 fix on the pilot MonitoringBench data (775 attacks + Honest-550, stored pilot streams).

For FIBS axial follow-up, FIBS linear follow-up and sab (full and none) vs gpt-4.1-mini (same mode), trajectory max:
  1. nominal alpha: TPR and realized test FPR (200 grouped 50/50 splits), paired contrast (amd.evaluation.paired);
  2. equal realized FPR: the reader's nominal level is lowered by bisection until its split-mean realized FPR is
     at most the LLM's, then the same paired bootstrap with per-term levels;
  3. per-task-cluster calibration (the 8 TF-IDF clusters of analyze_context.mb_clusters): one randomized
     threshold per cluster at alpha vs one global threshold, realized FPR overall and per cluster, TPR.

    unset VIRTUAL_ENV; uv run python -m tracks.r4_wb.analyze_a1_mb
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from amd.common.schema import REPO
from tracks.wb_whitebox.analyze_context import mb_clusters
from tracks.wb_whitebox.analyze_mb import sets_for

from .r4lib import contrast, contrast_alpha, equalize_level, matched_raw, percontext, realized_fpr, tpr

OUT = REPO / "results" / "r4_wb"
STREAMS = ["fibs_fu_ax", "fibs_fu", "sab"]


def main():
    clus = mb_clusters()
    rows, crows = [], []
    for mode in ("full", "none"):
        sets = sets_for(mode, STREAMS + ["llm"])
        L = sets["llm"]
        hg, ag = np.asarray(L.honest_groups), np.asarray(L.attack_groups)
        Rl = matched_raw(L.honest, L.attack, hg, ag)
        for st in STREAMS:
            S = sets[st]
            Rr = matched_raw(S.honest, S.attack, hg, ag)
            for alpha in (0.01, 0.05):
                fr, fl = realized_fpr(Rr, alpha), realized_fpr(Rl, alpha)
                res = contrast([(1.0, Rr, "max"), (-1.0, Rl, "max")], L.n_h, L.n_a, alpha, hg, ag)
                lev = equalize_level(Rr, fl, hi=alpha) if fr > fl else alpha
                req = contrast_alpha([(1.0, Rr, lev), (-1.0, Rl, alpha)], L.n_h, L.n_a, hg, ag)
                rows.append(dict(mode=mode, stream=st, alpha=alpha, tpr_reader=tpr(Rr, alpha), tpr_llm=tpr(Rl, alpha),
                                 fpr_reader=fr, fpr_llm=fl, est=res["est"], lo=res["lo"], hi=res["hi"],
                                 p_two=res["p_two"], eq_level=lev, eq_fpr_reader=realized_fpr(Rr, lev),
                                 eq_tpr_reader=tpr(Rr, lev), eq_est=req["est"], eq_lo=req["lo"], eq_hi=req["hi"],
                                 eq_p_two=req["p_two"]))
                print(rows[-1], flush=True)
        for st in STREAMS + ["llm"]:
            S = sets[st]
            hs = [np.nanmax(s) for s in S.honest]
            as_ = [np.nanmax(s) for s in S.attack]
            hc = [clus.get(str(g), "other") for g in S.honest_groups]
            ac = [clus.get(str(g), "other") for g in S.attack_groups]
            for alpha in (0.05, 0.01):
                r = percontext(hs, as_, S.honest_groups, hc, ac, alpha)
                cg = np.array(list(r["ctx_fpr_global"].values()))
                cc = np.array(list(r["ctx_fpr_percontext"].values()))
                crows.append(dict(mode=mode, stream=st, alpha=alpha, global_fpr=r["g_fpr"], global_tpr=r["g_tpr"],
                                  percluster_fpr=r["c_fpr"], percluster_tpr=r["c_tpr"],
                                  global_cluster_fpr_min=np.nanmin(cg), global_cluster_fpr_max=np.nanmax(cg),
                                  percluster_cluster_fpr_min=np.nanmin(cc), percluster_cluster_fpr_max=np.nanmax(cc),
                                  n_clusters=len(cg)))
                print(crows[-1], flush=True)
    pd.DataFrame(rows).to_csv(OUT / "a1_mb_equalfpr.csv", index=False)
    pd.DataFrame(crows).to_csv(OUT / "a1_mb_percluster.csv", index=False)


if __name__ == "__main__":
    main()
