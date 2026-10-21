"""Audit fixes M9 / m1 / m9 (track 1 and r2_t1 persistent state), from the saved matched-eval raw outputs ($0).

M9  MonitoringBench absolute TPRs stratified by the ATTACK agent model (claude-opus-4-5 vs claude-opus-4-6). The
    honest set (Honest-550) is 100% opus-4-5, so the agent model is label-correlated: report opus-4-5-only TPRs
    (the like-for-like comparison) next to the pooled ones. CIs: joint bootstrap (task clusters for honest
    calibration AND attacks, thresholds recomputed), amd.evaluation.paired.
m1  Realized FPR next to every headline TPR (from the matched tables) and its ratio to the target alpha.
m9  Persistent state, gradual attacks: TPR and top-3-sum/SR gains over max on side-task-SUCCESSFUL attacks only
    (66/120 gradual attacks failed their side task but count as positives in the original tables).

    unset VIRTUAL_ENV; uv run python tracks/fixes/t1_extras.py
Writes results/fixes/t1/m9_tpr_by_agent_model.csv, m1_realized_fpr.csv and
results/fixes/r2_t1/m9_ps_success_conditioned.csv.
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
for p in (HERE.parent / "t1_matched_budget", HERE.parent / "r2_t1"):
    sys.path.insert(0, str(p))

from amd.common.schema import REPO, load_trajectories  # noqa: E402
from amd.evaluation import paired_contrast_bootstrap  # noqa: E402

RES = REPO / "results"
OUT_T1, OUT_R2 = RES / "fixes" / "t1", RES / "fixes" / "r2_t1"
DETS = ["max", "top3sum", "kth2", "cusum_k0.5", "or(max+cusum)"]


def tpr(raw, det, n_h, n_a, alpha, hg, ag, mask, boot=1000, seed=0):
    r = paired_contrast_bootstrap([(1, raw, det)], n_honest=n_h, n_attack=n_a, alpha=alpha, honest_groups=hg,
                                  attack_groups=ag, attack_mask=mask, n_boot=boot, seed=seed)
    return r["est"], r["lo"], r["hi"]


def m9_agent_model():
    look = {t.traj_id: str(t.context.get("task_id")) for s in ("monitoringbench", "mb_honest") for t in load_trajectories(s)}
    model = {t.traj_id: str(t.context.get("agent_model")) for t in load_trajectories("monitoringbench")}
    rows = []
    for tag, modes in (("main", ("full", "none")), ("nano", ("none",))):
        for mode in modes:
            d = pickle.loads((REPO / "data" / "t1_raw" / "round2" / tag / f"raw_{mode}.pkl").read_bytes())
            hg = np.array([look[i] for i in d["honest_ids"]]); ag = np.array([look[i] for i in d["attack_ids"]])
            am = np.array([model[i] for i in d["attack_ids"]])
            st = np.asarray(d["struct"])
            masks = {"all": None, "opus-4-5": np.char.find(am, "4-5") >= 0, "opus-4-6": np.char.find(am, "4-6") >= 0}
            for S in ("S4",):
                masks[f"{S} opus-4-5"] = masks["opus-4-5"] & (st == S)
                masks[f"{S} opus-4-6"] = masks["opus-4-6"] & (st == S)
            for alpha in (0.05, 0.01):
                for g, m in masks.items():
                    n = len(ag) if m is None else int(m.sum())
                    for det in DETS:
                        e, lo, hi = tpr(d["raw"], det, len(hg), len(ag), alpha, hg, ag, m)
                        rows.append(dict(monitor="gpt-4.1-nano" if tag == "nano" else "gpt-4.1-mini", mode=mode,
                                         alpha=alpha, attack_subset=g, n_attack=n, detector=det, tpr=e, lo=lo, hi=hi))
    D = pd.DataFrame(rows)
    D.to_csv(OUT_T1 / "m9_tpr_by_agent_model.csv", index=False, float_format="%.4f")
    print(D[D.detector.isin(["max", "top3sum"])].pivot_table(index=["monitor", "mode", "alpha", "detector"],
                                                              columns="attack_subset", values="tpr").round(3))
    # T1 composition of attack sample by structure x agent model
    comp = pd.crosstab(st, am)
    comp.to_csv(OUT_T1 / "m9_attack_sample_structure_by_agent_model.csv")
    return D


def m1_fpr():
    rows = []
    for tag in ("main", "nano"):
        M = pd.read_csv(RES / "t1" / "round2" / tag / "matched.csv")
        M = M[(M.threshold_kind == "calibrated") & M.detector.isin(DETS + ["max_lenaware", "eproc_power"])]
        for _, r in M.iterrows():
            rows.append(dict(source=f"t1 round2 {tag}", mode=r["mode"], detector=r.detector, alpha=r.alpha, tpr=r.tpr,
                             fpr=r.fpr, fpr_lo=r.fpr_lo, fpr_hi=r.fpr_hi, fpr_over_alpha=r.fpr / r.alpha))
    P = pd.read_csv(RES / "r2_t1" / "ps_matched.csv")
    P = P[(P.threshold_kind == "calibrated") & P.detector.isin(["max", "top3sum", "sr_d1"]) & P.set.str.contains("current_only")]
    for _, r in P.iterrows():
        rows.append(dict(source="r2_t1 " + r["set"], mode="", detector=r.detector, alpha=r.alpha, tpr=r.tpr, fpr=r.fpr,
                         fpr_lo=r.fpr_lo, fpr_hi=r.fpr_hi, fpr_over_alpha=r.fpr / r.alpha))
    D = pd.DataFrame(rows)
    D.to_csv(OUT_T1 / "m1_realized_fpr.csv", index=False, float_format="%.4f")
    print(D.groupby(["source", "alpha"]).fpr_over_alpha.agg(["min", "max", "mean"]).round(2))
    return D


def m9_ps_success():
    from ps_sets import r2_ps_sets
    raws = pickle.loads((REPO / "data" / "raw" / "r2_t1" / "ps_raw" / "raws.pkl").read_bytes())
    rows = []
    for ss in r2_ps_sets():
        if not ss.name.endswith(":gradual") or ss.name not in raws:
            continue
        succ = np.array([bool(m.get("side_task_success")) for m in ss.attack_meta])
        for alpha in (0.05, 0.01):
            for sub, mask in (("all", None), ("side-task success", succ), ("side-task failed", ~succ)):
                n = ss.n_a if mask is None else int(mask.sum())
                for det in ("max", "top3sum", "sr_d1"):
                    e, lo, hi = tpr(raws[ss.name], det, ss.n_h, ss.n_a, alpha, None, None, mask)
                    rows.append(dict(set=ss.name, alpha=alpha, subset=sub, n_attack=n, detector=det, tpr=e, lo=lo, hi=hi))
                for det in ("top3sum", "sr_d1"):
                    r = paired_contrast_bootstrap([(1, raws[ss.name], det), (-1, raws[ss.name], "max")], n_honest=ss.n_h,
                                                  n_attack=ss.n_a, alpha=alpha, attack_mask=mask, n_boot=1000, seed=1)
                    rows.append(dict(set=ss.name, alpha=alpha, subset=sub, n_attack=n, detector=f"{det} - max",
                                     tpr=r["est"], lo=r["lo"], hi=r["hi"], p_le0=r["p_le0"]))
    D = pd.DataFrame(rows)
    D.to_csv(OUT_R2 / "m9_ps_success_conditioned.csv", index=False, float_format="%.4f")
    print(D[D.set.str.contains("current_only") & (D.alpha == 0.05) & D.detector.str.contains("-")].round(3).to_string())
    return D


if __name__ == "__main__":
    OUT_T1.mkdir(parents=True, exist_ok=True); OUT_R2.mkdir(parents=True, exist_ok=True)
    m1_fpr()
    m9_ps_success()
    m9_agent_model()
