"""LinuxArena (regenerated reader streams, audit A2): paired reader-vs-LLM contrasts with Holm, realized FPR,
per-environment calibration (PREREG Part 2).

Reader streams: data/processed/whitebox/scores/r4/la_{full,none}.jsonl (re-scored 2026-10-22, unchanged
pod_reader.py and probes.pt). LLM: the 12 per-action sweep monitors (data/processed/linuxarena_sweep/scores.jsonl).
Hidden-tool steps are NaN for every stream (as in the pilot). Trajectory statistic = max.

For each LLM monitor: the trajectories both streams scored (honest / attack), 200 random 50/50 honest splits
grouped by main task, randomized threshold at alpha on the calibration half, TPR on all attacks, realized FPR
on the other half; paired cluster bootstrap (task clusters, calibration noise, B=2000); Holm over the 12
monitors per (reader stream, alpha). Primary: FIBS axial follow-up (full) at alpha 0.01.
Also: per-environment (10 envs) calibration vs a global threshold for every stream.

    unset VIRTUAL_ENV; uv run python -m tracks.r4_wb.analyze_la_r4
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from amd.common.schema import PROCESSED, REPO, read_jsonl
from tracks.wb_whitebox.wblib import WB, derived, load_inputs_meta

from .r4lib import contrast, holm, matched_raw, percontext, realized_fpr, tpr

OUT = REPO / "results" / "r4_wb"
STREAMS = ["fibs_fu_ax", "fibs_fu", "sab"]


def masked(meta, d):
    out = {}
    for t, m in meta.items():
        if t not in d:
            continue
        s = np.asarray(d[t], float).copy()
        hidden = [i for i in m.get("hidden_tool_steps", []) if i < len(s)]
        s[hidden] = np.nan
        if np.isfinite(s).any():
            out[t] = s
    return out


def main():
    meta = load_inputs_meta("la")
    llm = {}
    for d in read_jsonl(PROCESSED / "linuxarena_sweep" / "scores.jsonl"):
        if d["unit"] == "step":
            llm.setdefault(d["monitor_id"].split("|")[0], {})[d["traj_id"]] = [np.nan if v is None else v
                                                                               for v in d["scores"]]
    llm = {k: masked(meta, v) for k, v in llm.items()}
    rd = {}
    for mode in ("full", "none"):
        R = {}
        for d in read_jsonl(WB / "scores" / "r4" / f"la_{mode}.jsonl"):
            if d["n_steps"]:
                R[d["traj_id"]] = derived(d["feats"])
        for st in STREAMS:
            rd[(mode, st)] = masked(meta, {t: v[st] for t, v in R.items()})
    rows, au, ctx_rows = [], [], []
    for (mode, st), D in rd.items():
        for mon, Lm in sorted(llm.items()):
            ids = sorted(set(D) & set(Lm))
            hid = [t for t in ids if meta[t]["label"] == "honest"]
            aid = [t for t in ids if meta[t]["label"] == "attack"]
            hg = np.array([str(meta[t]["task_id"]) for t in hid])
            ag = np.array([str(meta[t]["task_id"]) for t in aid])
            Pr = matched_raw([D[t] for t in hid], [D[t] for t in aid], hg, ag)
            Pl = matched_raw([Lm[t] for t in hid], [Lm[t] for t in aid], hg, ag)
            for alpha in (0.01, 0.05):
                res = contrast([(1.0, Pr, "max"), (-1.0, Pl, "max")], len(hid), len(aid), alpha, hg, ag)
                rows.append(dict(mode=mode, stream=st, llm=mon, alpha=alpha, n_h=len(hid), n_a=len(aid),
                                 tpr_reader=tpr(Pr, alpha), tpr_llm=tpr(Pl, alpha),
                                 fpr_reader=realized_fpr(Pr, alpha), fpr_llm=realized_fpr(Pl, alpha),
                                 **{k: res[k] for k in ("est", "lo", "hi", "p_two")}))
                print(rows[-1], flush=True)
        y = [meta[t]["label"] == "attack" for t in D]
        au.append(dict(stream=f"wb:{mode}:{st}", n=len(D),
                       auroc_max=roc_auc_score(y, [np.nanmax(D[t]) for t in D])))
    df = pd.DataFrame(rows)
    for (mode, st, alpha), g in df.groupby(["mode", "stream", "alpha"]):
        df.loc[g.index, "p_holm"] = holm(g.p_two.values)
    df.to_csv(OUT / "la_paired.csv", index=False)
    for mon, Lm in llm.items():
        y = [meta[t]["label"] == "attack" for t in Lm]
        au.append(dict(stream=f"llm:{mon}", n=len(Lm), auroc_max=roc_auc_score(y, [np.nanmax(Lm[t]) for t in Lm])))
    pd.DataFrame(au).to_csv(OUT / "la_auroc_r4.csv", index=False)
    # per-environment calibration
    allsets = {f"wb:{m}:{s}": D for (m, s), D in rd.items()} | {f"llm:{k}": v for k, v in llm.items()}
    for name, D in allsets.items():
        hid = [t for t in D if meta[t]["label"] == "honest"]
        aid = [t for t in D if meta[t]["label"] == "attack"]
        for alpha in (0.05, 0.01):
            r = percontext([np.nanmax(D[t]) for t in hid], [np.nanmax(D[t]) for t in aid],
                           [str(meta[t]["task_id"]) for t in hid], [meta[t]["env"] for t in hid],
                           [meta[t]["env"] for t in aid], alpha)
            cg, cc = np.array(list(r["ctx_fpr_global"].values())), np.array(list(r["ctx_fpr_percontext"].values()))
            ctx_rows.append(dict(set=name, alpha=alpha, global_fpr=r["g_fpr"], global_tpr=r["g_tpr"],
                                 perenv_fpr=r["c_fpr"], perenv_tpr=r["c_tpr"],
                                 global_env_fpr_max=np.nanmax(cg), global_env_fpr_min=np.nanmin(cg),
                                 perenv_env_fpr_max=np.nanmax(cc), perenv_env_fpr_min=np.nanmin(cc)))
    pd.DataFrame(ctx_rows).to_csv(OUT / "la_percontext.csv", index=False)
    print(df[df.alpha == 0.01].round(3).to_string())
    json.dump({"n_llm": len(llm)}, open(OUT / "la_info.json", "w"))


if __name__ == "__main__":
    main()
