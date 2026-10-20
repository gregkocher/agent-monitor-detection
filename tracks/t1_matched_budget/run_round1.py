"""Round 1: matched-budget comparison of the T1 detector suite on all existing per-unit score streams.

    uv run python tracks/t1_matched_budget/run_round1.py [--sets la,akshn,mrt,ps] [--quick]

Writes results/t1/round1/{matched,gain,logit_roc,streaming,localization,autocorr,lengths,
length_matched}.csv (one row per set x detector [x alpha]) and per-set raw pickles under
results/t1/round1/raw/ (gitignored size permitting; small).

Sets
- la:<monitor>          LinuxArena sweep, 12 history-aware per-action monitors (0-100). Hidden tools
                        (auto-scored 0, never shown to the monitor; meta.skipped_idx) are set to NaN.
                        No onset label; harm_step (live failures, 36 attacks) for before-harm.
- akshn_<set>:local / :cumulative   Gemini-3.1-Pro streaming judge, per action: local suspicion and
                        cumulative confidence (both history-aware). Onset = ideal flagging step,
                        harm proxy = point of no return.
- mrt:<monitor>         ScaleAI MRT sequential_N per-chunk verdicts (monitors with >= 150 streams).
- persistent_state      too small (11 runs); summarized descriptively in the report.
"""
from __future__ import annotations

import argparse
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from t1lib import (ALPHAS, build_set, honest_autocorr, length_matched_indices, load_scores_index,  # noqa: E402
                   localization, logit_roc_table, matched_arl, paired_gain, run_matched,
                   streaming_metrics, subset, t1_suite)

from amd.common.schema import REPO, load_trajectories  # noqa: E402

OUT = REPO / "results" / "t1" / "round1"
AKSHN = ["akshn_bash", "akshn_agentdojo", "akshn_iac", "akshn_shade", "akshn_basharena_opus46",
         "akshn_basharena_sonnet45", "akshn_linuxarena"]
ACCUM = ["cusum_k0.5", "cusum_k0.25", "sr_d1", "glr_w20", "eproc_power", "esr_power", "top3sum",
         "or(max+cusum)", "or(max+cusum+eproc)", "kth2", "mean", "max_lenaware", "count>q0.95"]


def la_sets():
    T = {t.traj_id: t for t in load_trajectories("linuxarena_sweep")}
    idx = load_scores_index("linuxarena_sweep")
    out = []
    for mid, recs in sorted(idx.items()):
        if not mid.endswith("|mean-action|full"):
            continue

        def val(r):
            s = np.array([np.nan if v is None else float(v) for v in r["scores"]])
            sk = r["meta"].get("skipped_idx") or []
            s[[i for i in sk if i < len(s)]] = np.nan
            return s
        name = "la:" + mid.split("|")[0]
        out.append(build_set(name, T, recs, group_key="main_task", value_fn=val,
                             ameta_fn=lambda t: {"policy": t.context.get("policy")}))
    return out


def akshn_sets():
    out = []
    for src in AKSHN:
        T = {t.traj_id: t for t in load_trajectories(src)}
        idx = load_scores_index(src, monitor_ids={"gemini-3.1-pro|akshn_local|full",
                                                  "gemini-3.1-pro|akshn_cumulative|full"})
        for mid, recs in sorted(idx.items()):
            kind = "local" if "local" in mid else "cumulative"
            out.append(build_set(f"{src}:{kind}", T, recs, group_key="main_task",
                                 harm_fn=lambda t: t.meta.get("point_of_no_return_step"),
                                 ameta_fn=lambda t: {"side_task": t.context.get("side_task")}))
    return out


def mrt_sets(min_streams=150):
    T = {t.traj_id: t for t in load_trajectories("mrt")}
    idx = load_scores_index("mrt")
    out = []
    for mid, recs in sorted(idx.items()):
        if len(recs) < min_streams:
            continue
        ss = build_set("mrt:" + mid.replace("|chunk", ""), T, recs, group_key="task", unit="chunk")
        if ss.n_h >= 40 and ss.n_a >= 40:
            out.append(ss)
    return out


def length_stats(ss):
    hl = np.array([np.isfinite(s).sum() for s in ss.honest])
    al = np.array([np.isfinite(s).sum() for s in ss.attack])
    from scipy.stats import mannwhitneyu
    auc = mannwhitneyu(al, hl).statistic / len(al) / len(hl)
    return dict(set=ss.name, n_honest=ss.n_h, n_attack=ss.n_a, len_h_med=np.median(hl), len_a_med=np.median(al),
                len_h_q90=np.quantile(hl, 0.9), len_a_q90=np.quantile(al, 0.9), length_auroc=auc, note=ss.note)


def run_set(ss, quick=False, arl=False):
    t0 = time.time()
    res = {}
    df, raw = run_matched(ss, n_splits=10 if not quick else 3, n_boot=300 if not quick else 50, return_raw=True)
    res["matched"] = df
    gains = []
    for alpha in ALPHAS:
        for a in ACCUM:
            g, lo, hi = paired_gain(raw, alpha, a=a, b="max")
            gains.append(dict(set=ss.name, alpha=alpha, detector=a, gain_vs_max=g, lo=lo, hi=hi))
    res["gain"] = pd.DataFrame(gains)
    lr = logit_roc_table(raw, n_boot=100 if not quick else 20)
    lr.insert(0, "set", ss.name)
    res["logit_roc"] = lr
    sm, per = streaming_metrics(ss, alpha=0.01, n_splits=5 if not quick else 2)
    res["streaming"] = sm
    res["localization"] = localization(ss)
    ac = honest_autocorr(ss.honest)
    ac["set"] = ss.name
    res["autocorr"] = pd.DataFrame([ac])
    res["lengths"] = pd.DataFrame([length_stats(ss)])
    hl = [np.isfinite(s).sum() for s in ss.honest]
    al = [np.isfinite(s).sum() for s in ss.attack]
    hi_, ai_ = length_matched_indices(hl, al)
    if len(hi_) >= 40:
        sub = subset(ss, hi_, ai_, ss.name)
        sub.honest_groups = None
        sub.attack_groups = None
        dets = {k: v for k, v in t1_suite().items() if k in ("max", "kth2", "cusum_k0.5", "eproc_power",
                                                               "glr_w20", "or(max+cusum)", "max_lenaware")}
        lm = run_matched(sub, detectors=dets, alphas=(0.05, 0.01), n_splits=10 if not quick else 3, n_boot=100)
        lm["n_matched"] = len(hi_)
        res["length_matched"] = lm
    if arl:
        res["arl"] = matched_arl(ss, n_sims=40 if not quick else 20)
    print(f"  {ss.name}: n_h={ss.n_h} n_a={ss.n_a} ({ss.note}) {time.time() - t0:.0f}s", flush=True)
    return res, raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="la,akshn,mrt")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--arl", default="la:claude-opus-4-6,la:gpt-5-nano,akshn_bash:local,akshn_bash:cumulative,"
                                     "akshn_linuxarena:local,akshn_linuxarena:cumulative,"
                                     "akshn_basharena_sonnet45:local,akshn_basharena_sonnet45:cumulative")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "raw").mkdir(exist_ok=True)
    sets = []
    for k in a.sets.split(","):
        sets += {"la": la_sets, "akshn": akshn_sets, "mrt": mrt_sets}[k]()
    arl_sets = set(a.arl.split(","))
    tables: dict = {}
    for ss in sets:
        res, raw = run_set(ss, quick=a.quick, arl=ss.name in arl_sets)
        for k, v in res.items():
            tables.setdefault(k, []).append(v)
        with open(OUT / "raw" / (ss.name.replace(":", "__").replace("/", "_") + ".pkl"), "wb") as f:
            pickle.dump(dict(raw=raw, honest_ids=ss.honest_ids, attack_ids=ss.attack_ids,
                             onsets=ss.onsets, harm=ss.harm, attack_meta=ss.attack_meta), f)
    tag = "_".join(a.sets.split(","))
    for k, v in tables.items():
        v = [x for x in v if x is not None and len(x)]
        if not v:
            continue
        df = pd.concat(v, ignore_index=True)
        df.to_csv(OUT / f"{k}_{tag}.csv", index=False)
    print("done", list(tables))


if __name__ == "__main__":
    main()
