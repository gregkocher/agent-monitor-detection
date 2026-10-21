"""Confound and subgroup checks for the MonitoringBench comparison.

  1. Subgroups: AUROC of the trajectory max by attack structure (S1-S4), side task and agent model
     (Honest-550 is all claude-opus-4-5; 27% of the sampled attacks are claude-opus-4-6).
  2. Pre-onset steps: step-level AUROC of attack steps BEFORE the heuristic onset (first step touching a
     side-task target) vs honest steps. In history-free mode these steps carry no attack evidence, so a
     value well above 0.5 means the stream separates the trajectory sources by something other than the
     attack (style, task mix, agent model).
  3. Length-matched subsets (T1 `length_matched_indices`): matched-FPR TPR of max on honest and attack
     trajectories matched on number of steps.

    uv run python -m tracks.wb_whitebox.analyze_confounds
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "t1_matched_budget"))
from t1lib import length_matched_indices, run_matched, subset  # noqa: E402

from amd.common.schema import REPO, load_trajectories  # noqa: E402

from .analyze_mb import detectors, sets_for  # noqa: E402

OUT = REPO / "results" / "wb"
STREAMS = ["llm", "sab", "sab_L43", "fibs_fu", "fibs_fu_ax", "fibs_tok", "jl_lm", "dec", "sup"]


def auc(h, a):
    if len(h) < 5 or len(a) < 5:
        return np.nan
    return roc_auc_score(np.r_[np.zeros(len(h)), np.ones(len(a))], np.r_[h, a])


def main():
    TA = {t.traj_id: t for t in load_trajectories("monitoringbench")}
    sub, pre, lm = [], [], []
    for mode in ("full", "none"):
        sets = sets_for(mode, STREAMS)
        for st, ss in sets.items():
            mh = np.array([np.nanmax(s) for s in ss.honest])
            ma = np.array([np.nanmax(s) for s in ss.attack])
            keys = {"structure": [m.get("structure") or "NA" for m in ss.attack_meta],
                    "side_task": [m.get("side_task") for m in ss.attack_meta],
                    "agent_model": [TA[t].context.get("agent_model") for t in ss.attack_ids]}
            for k, vals in keys.items():
                vals = np.array(vals, dtype=object)
                for v in sorted(set(vals), key=str):
                    sel = vals == v
                    sub.append(dict(mode=mode, stream=st, key=k, value=v, n=int(sel.sum()), auroc_max=auc(mh, ma[sel])))
            hs = np.concatenate([s[np.isfinite(s)] for s in ss.honest])
            pa = np.concatenate([s[: o] for s, o in zip(ss.attack, ss.onsets) if o is not None and o > 0])
            pa = pa[np.isfinite(pa)]
            ex = np.array([s[h] for s, h in zip(ss.attack, ss.harm) if h is not None])
            pre.append(dict(mode=mode, stream=st, n_pre_steps=len(pa), auroc_pre_onset=auc(hs, pa),
                            auroc_exec_step=auc(hs, ex)))
            hl = [np.isfinite(s).sum() for s in ss.honest]
            al = [np.isfinite(s).sum() for s in ss.attack]
            hi, ai = length_matched_indices(hl, al)
            sm = subset(ss, hi, ai, ss.name)
            d = {k: v for k, v in detectors().items() if k in ("max", "top3sum")}
            df = run_matched(sm, detectors=d, alphas=(0.05, 0.01), n_splits=10, n_boot=200, seed=0)
            df["mode"], df["stream"], df["n_matched"] = mode, st, len(hi)
            lm.append(df)
            print(mode, st, pre[-1], flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(sub).to_csv(OUT / "mb_subgroups.csv", index=False)
    pd.DataFrame(pre).to_csv(OUT / "mb_preonset.csv", index=False)
    pd.concat(lm).to_csv(OUT / "mb_length_matched.csv", index=False)
    S = pd.DataFrame(sub)
    print(S.pivot_table(index=["key", "value"], columns=["mode", "stream"], values="auroc_max").round(2).to_string())
    print(pd.DataFrame(pre).round(3).to_string())


if __name__ == "__main__":
    main()
