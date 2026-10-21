"""(b) Per-context calibration of white-box reader thresholds vs gpt-4.1-mini (Track 2 machinery).

Contexts: MonitoringBench task clusters (TF-IDF k-means k=8 on the main-task descriptions, the same
clustering as T2; clusters with >= 20 honest and >= 20 attack trajectories kept), and LinuxArena
environments (10 envs, 20 honest each). Statistic = trajectory max of the per-step stream.

1. Heterogeneity: per-context FPR of one global threshold at 5% (and 10%) honest budget; between-context
   logit-normal tau (T2 `logitnormal_re`), plus the share of honest trajectory-max variance explained by
   context (one-way variance components on normal scores).
2. Allocation at a fixed global audit budget (T2 `r1_allocation.run_panel`, 60 plain + 150 bootstrap
   replicates): global, CFAR, Mondrian, partial pooling (EB / CV), max-detection, Stackelberg; metrics:
   uniform-attacker TPR and informed attack-selection safety (attacker picks the context with the lowest
   estimated detection), nominal and spend-matched.

    uv run python -m tracks.wb_whitebox.analyze_context [--quick]
"""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "t2_per_context"))
import panels as P  # noqa: E402
import r1_allocation as RA  # noqa: E402
import t2lib as L  # noqa: E402

from amd.common.schema import REPO, load_trajectories, read_jsonl  # noqa: E402

from .wblib import load_inputs_meta, load_reader  # noqa: E402

OUT = REPO / "results" / "wb"
PANELS: dict = {}


def mb_clusters(k=8, seed=0) -> dict:
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    desc = {}
    for s in ("monitoringbench", "mb_honest"):
        for t in load_trajectories(s):
            desc.setdefault(t.context.get("main_task"), t.context.get("main_task_description", ""))
    tasks = sorted(desc)
    X = TfidfVectorizer(max_features=3000, stop_words="english", min_df=2, sublinear_tf=True).fit_transform(
        [desc[t] for t in tasks])
    km = KMeans(k, n_init=20, random_state=seed).fit(X)
    return {str(t): f"c{l}" for t, l in zip(tasks, km.labels_)}


def llm_streams_mb(mode):
    from tracks.t1_matched_budget.run_round2 import load_mode  # noqa: F401
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "t1_matched_budget"))
    from run_round2 import load_mode as lm
    ss = lm(mode)
    return {**dict(zip(ss.honest_ids, ss.honest)), **dict(zip(ss.attack_ids, ss.attack))}


def mb_panels(streams, modes=("full", "none")):
    meta = load_inputs_meta("mb")
    clus = mb_clusters()
    for mode in modes:
        R = load_reader("mb", mode)
        llm = llm_streams_mb(mode)
        for st in streams:
            rows = []
            for tid, m in meta.items():
                if tid not in R:
                    continue
                s = llm.get(tid) if st == "llm" else R[tid].get(st)
                if s is None:
                    continue
                s = np.asarray(s, float)
                s = s[np.isfinite(s)]
                if not len(s):
                    continue
                rows.append(dict(P._row(tid, {"label": m["label"], "side_task": m.get("side_task"),
                                              "main_task": str(m.get("task_id"))}, s)))
            PANELS[f"mb_wb_{mode}_{st}"] = P._panel(rows, lambda r: clus.get(r["main_task"]), 20, 20,
                                                    f"mb_wb_{mode}_{st}")


def la_panels(streams, modes=("full", "none")):
    meta = load_inputs_meta("la")
    llm = {}
    for d in read_jsonl(REPO / "data" / "processed" / "linuxarena_sweep" / "scores.jsonl"):
        if d["unit"] == "step" and d["monitor_id"].split("|")[0] in ("gpt-4.1-nano", "gpt-5-nano", "gpt-5-mini",
                                                                      "claude-opus-4-6", "gpt-oss-120b"):
            llm[(d["monitor_id"].split("|")[0], d["traj_id"])] = np.array(
                [np.nan if v is None else v for v in d["scores"]], float)
    for mode in modes:
        R = load_reader("la", mode)
        for st in streams:
            rows = []
            for tid, m in meta.items():
                if tid not in R or st not in R[tid]:
                    continue
                s = np.asarray(R[tid][st], float).copy()
                s[[i for i in m.get("hidden_tool_steps", []) if i < len(s)]] = np.nan
                s = s[np.isfinite(s)]
                if len(s):
                    rows.append(P._row(tid, {"label": m["label"], "side_task": m.get("side_task"),
                                             "failure_type": None}, s) | {"env": m.get("env")})
            PANELS[f"la_wb_{mode}_{st}"] = P._panel(rows, lambda r: r["env"], 10, 5, f"la_wb_{mode}_{st}")
    for mon in sorted({k[0] for k in llm}):
        rows = []
        for tid, m in meta.items():
            s = llm.get((mon, tid))
            if s is None:
                continue
            s = s[np.isfinite(s)]
            if len(s):
                rows.append(P._row(tid, {"label": m["label"], "side_task": m.get("side_task")}, s) | {"env": m.get("env")})
        PANELS[f"la_wb_llm_{mon}"] = P._panel(rows, lambda r: r["env"], 10, 5, f"la_wb_llm_{mon}")


def heterogeneity(name, df, B=0.05):
    H = {c: g[g.label == "honest"].stat.values for c, g in df.groupby("ctx")}
    allh = np.concatenate(list(H.values()))
    q = np.quantile(allh, 1 - B)
    ctx = sorted(H)
    x = np.array([(H[c] > q).sum() for c in ctx])
    n = np.array([len(H[c]) for c in ctx])
    re = L.logitnormal_re(x, n)
    y = L.normal_scores(allh)
    grp = np.concatenate([[c] * len(H[c]) for c in ctx])
    vc = L.varcomp_oneway(y, grp)
    A = {c: g[g.label == "attack"].stat.values for c, g in df.groupby("ctx")}
    tpr = [np.mean(A[c] > q) if len(A.get(c, [])) else np.nan for c in ctx]
    return dict(panel=name, B=B, n_ctx=len(ctx), fpr_min=float((x / n).min()), fpr_max=float((x / n).max()),
                tau=re.get("tau"), tau_p=re.get("p_lrt", re.get("p")), icc=vc.get("icc", vc.get("share")),
                tpr_min=float(np.nanmin(tpr)), tpr_max=float(np.nanmax(tpr)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--streams", default="sab,sab_max,dec,fibs_tok,fibs_fu,jl_lm,sup,llm")
    ap.add_argument("--which", default="mb,la")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    streams = a.streams.split(",")
    if "mb" in a.which:
        mb_panels(streams)
    if "la" in a.which:
        la_panels([s for s in streams if s != "llm"])
    P.load = lambda name: PANELS[name]
    het = []
    for name, df in PANELS.items():
        for B in (0.05, 0.10):
            try:
                het.append(heterogeneity(name, df, B))
            except Exception as e:  # noqa: BLE001
                print("het fail", name, e)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(het).to_csv(OUT / "context_heterogeneity.csv", index=False)
    print(pd.DataFrame(het).round(3).to_string())
    n_plain, n_boot = (4, 6) if a.quick else (60, 150)
    jobs = [(n, (0.02, 0.05), n_plain, n_boot, [None], 5000 + i) for i, n in enumerate(sorted(PANELS))]
    parts = []
    RA.P.load = P.load
    with ProcessPoolExecutor(a.workers, initializer=_init, initargs=(PANELS,)) as ex:
        for res in ex.map(RA.run_panel, jobs):
            parts.append(res)
            print("done", res.panel.iloc[0], flush=True)
    raw = pd.concat(parts, ignore_index=True)
    summ = RA.summarize(raw)
    summ.to_csv(OUT / f"context_allocation{'_quick' if a.quick else ''}.csv", index=False, float_format="%.4g")
    for mode in ("nominal", "matched"):
        print(mode)
        print(summ[summ["mode"] == mode].pivot_table(index=["panel", "B"], columns="rule",
                                                     values=["tpr_uniform", "sel_informed"]).round(3).to_string())


def _init(panels):
    PANELS.update(panels)
    P.load = lambda name: PANELS[name]
    RA.P.load = P.load


if __name__ == "__main__":
    main()
