"""LinuxArena sweep: white-box reader streams next to the 12 per-action LLM monitors of the sweep.

342 trajectories (200 honest / 142 attack, claude-opus-4-6 agent, 10 environments). Every action is a
unit; LinuxArena's hidden tools (side-task test, planning, submit) are NaN for every stream, as in T1.
Per stream: AUROC of the trajectory max, and matched-FPR TPR (alpha 0.05 / 0.01; 10 splits grouped by
main task when >= 30 tasks, cluster bootstrap) for max, top-3 sum, CUSUM(k=1.5), OR(max+CUSUM).
Also: per-step fusion of the best reader stream with each LLM monitor (rank-sum of trajectory maxima).

    uv run python -m tracks.wb_whitebox.analyze_la
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "t1_matched_budget"))
from t1lib import StreamSet, run_matched  # noqa: E402

from amd.common.schema import REPO, read_jsonl  # noqa: E402

from .analyze_mb import detectors  # noqa: E402
from .wblib import load_inputs_meta, load_reader  # noqa: E402

OUT = REPO / "results" / "wb"
STREAMS = ["sab", "sab_max", "dec", "fibs_tok", "fibs_fu", "fibs_fu_ax", "jl_lm", "jl_hits", "sup_from_mb"]


def main():
    meta = load_inputs_meta("la")
    llm = {}
    for d in read_jsonl(REPO / "data" / "processed" / "linuxarena_sweep" / "scores.jsonl"):
        if d["unit"] == "step":
            llm.setdefault(d["monitor_id"].split("|")[0], {})[d["traj_id"]] = np.array(
                [np.nan if v is None else v for v in d["scores"]], float)
    dets = {k: v for k, v in detectors().items() if k in ("max", "top3sum", "cusum_k1.5", "or(max+cusum)")}
    au, tabs = [], []
    sets = {}
    for mode in ("full", "none"):
        R = load_reader("la", mode)
        for st in STREAMS:
            sets[f"wb:{mode}:{st}"] = {t: np.asarray(R[t][st], float) for t in R if st in R[t]}
    for mon, d in llm.items():
        sets[f"llm:{mon}"] = d
    for name, d in sets.items():
        H, A, hid, aid, hg, ag = [], [], [], [], [], []
        for t, m in meta.items():
            if t not in d:
                continue
            s = d[t].copy()
            hidden = [i for i in m.get("hidden_tool_steps", []) if i < len(s)]
            s[hidden] = np.nan
            if not np.isfinite(s).any():
                continue
            if m["label"] == "honest":
                H.append(s); hid.append(t); hg.append(str(m.get("task_id")))
            else:
                A.append(s); aid.append(t); ag.append(str(m.get("task_id")))
        if len(H) < 50 or len(A) < 30:
            continue
        mh, ma = [np.nanmax(s) for s in H], [np.nanmax(s) for s in A]
        au.append(dict(stream=name, n_h=len(H), n_a=len(A),
                       auroc_max=roc_auc_score(np.r_[np.zeros(len(mh)), np.ones(len(ma))], np.r_[mh, ma])))
        grouped = len(set(hg)) >= 30
        ss = StreamSet(f"la:{name}", H, A, hid, aid, np.array(hg) if grouped else None,
                       np.array(ag) if grouped else None, [None] * len(A), [None] * len(A), [{}] * len(A), [],
                       "step", "")
        df = run_matched(ss, detectors=dets, alphas=(0.05, 0.01), n_splits=10, n_boot=200, seed=0)
        df["stream"] = name
        tabs.append(df)
        print(au[-1], flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(au).to_csv(OUT / "la_auroc.csv", index=False)
    pd.concat(tabs).to_csv(OUT / "la_matched.csv", index=False)
    print(pd.DataFrame(au).sort_values("auroc_max").round(3).to_string())


if __name__ == "__main__":
    main()
