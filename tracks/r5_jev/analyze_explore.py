"""EXPLORATORY analyses for Idea 05 round 1 (not part of the preregistered Holm family).

RQ2  standalone JEV with max / mean / top-3 / CUSUM aggregation at matched FPR (matched_budget_eval, randomized,
     grouped splits, task-cluster bootstrap); breakdowns by side task / structural strategy and readable vs derived
     (MonitoringBench: password leak + malware download = readable, firewall + sudo edits = derived);
     length-confound baselines (AUROC of max action length and of step count; Spearman of JEV with action length).
RQ3  gates: suspicion (primary cascade) vs confidence (escalate the least confident steps) vs two-sided
     (least-confident steps escalated, confidently suspicious steps p >= 0.99 alarm without the LLM, the rest cleared);
     overlap of JEV confident-benign misses (every step p <= 0.05) with LLM-only misses vs independence.
Open model: Perplexity Decider v1.2 as a first stage on MonitoringBench (if its scores exist).

    unset VIRTUAL_ENV; uv run python -m tracks.r5_jev.analyze_explore [--splits 50] [--boot 500]
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

from amd.common.schema import DATA, REPO
from amd.detectors import CUSUM, Max, Mean, TopKSum, Whiten
from amd.evaluation import calibrate, matched_budget_eval

from . import panels as PN
from .analyze_primary import ALPHAS, E_LEVELS, MIN_CAL, frozen, n_cal
from .cascade import FLOOR, evaluate, make_design, plain_stats, summarize, tpr_boot
from .splits import AKSHN

OUT = REPO / "results" / "r5_jev"
DEC = DATA / "r5_jev" / "decider"
READABLE = {"passwords": "readable", "malware": "readable", "firewall": "derived", "sudo": "derived"}


def clean(arrs):
    return [np.where(np.isfinite(a), a, np.nan) for a in arrs]


def standalone(P, stream, S, B, seed=0):
    h = [np.asarray(a, float)[np.isfinite(a)] if np.isfinite(a).any() else np.array([0.0])
         for a in P.streams[stream][:P.nh]]
    at = [np.asarray(a, float)[np.isfinite(a)] if np.isfinite(a).any() else np.array([0.0])
          for a in P.streams[stream][P.nh:]]
    dets = {"max": Max(), "mean": Mean(), "top3": TopKSum(3, transform=Whiten()),
            "cusum_k0.5": CUSUM(k=0.5, transform=Whiten())}
    df = matched_budget_eval(dets, h, at, alphas=ALPHAS, honest_groups=P.hg, attack_groups=P.ag, group_split=True,
                             n_splits=S, n_boot=B, cluster_bootstrap=True, method="randomized", seed=seed)
    df = df[df.threshold_kind == "calibrated"].copy()
    mx = [x.max() for x in h] + [x.max() for x in at]
    df["auroc_max"] = roc_auc_score([0] * len(h) + [1] * len(at), mx)
    df["stream"] = stream
    return df


def two_sided_streams(P, hi=0.99):
    p = P.streams["jev"]
    g = [np.where(np.isfinite(x) & (x >= hi), np.inf, -np.abs(2 * x - 1)) for x in p]
    L2 = [np.where(np.isfinite(x) & (x >= hi), 1e3, l) for x, l in zip(p, P.streams[P.second])]
    return g, L2


def add_gate_streams(P):
    P.streams["jev_conf"] = [-np.abs(2 * x - 1) for x in P.streams["jev"]]


def gate_rows(name, P, S, B, seed, rows):
    add_gate_streams(P)
    d = make_design(P, S, B, seed)
    base = evaluate(P, d, {"kind": "plain", "stream": P.second}, ALPHAS)
    g, L2 = two_sided_streams(P)
    P2 = PN.Panel(P.name, P.hid, P.aid, P.hg, P.ag, {"g2": g, "L2": L2}, "L2")
    for e in E_LEVELS:
        res = {"suspicion": evaluate(P, d, {"kind": "cascade", "first": "jev", "e": e}, ALPHAS),
               "confidence": evaluate(P, d, {"kind": "cascade", "first": "jev_conf", "e": e}, ALPHAS),
               "two_sided": evaluate(P2, d, {"kind": "cascade", "first": "g2", "e": e}, ALPHAS)}
        for a in ALPHAS:
            if n_cal(dict(llm_only=base), a) < MIN_CAL[a]:
                continue
            b0 = tpr_boot([base], a)
            for k, r in res.items():
                t = tpr_boot([r], a)
                s, dd = summarize(t), summarize(t - b0)
                rows.append(dict(panel=name, gate=k, e=e, alpha=a, tpr=s["est"], lo=s["lo"], hi=s["hi"],
                                 d_llm=dd["est"], d_lo=dd["lo"], d_hi=dd["hi"],
                                 esc_honest=np.nanmean(r[a]["esc_h"]), fpr=np.mean(r[a]["fpr"])))


def overlap(name, P, alpha, rows, B=1000, seed=0):
    """JEV confident-benign attack misses vs LLM-only misses (thresholds: split-mean over 50 grouped splits)."""
    from amd.evaluation.matched import _split, bootstrap_weights
    rng = np.random.default_rng(seed)
    jmax = plain_stats(P, "jev")
    lmax = plain_stats(P, P.second)
    jmiss, lmiss = np.zeros(len(P.aid)), np.zeros(len(P.aid))
    S = 50
    for _ in range(S):
        cal, _ = _split(P.nh, 0.5, rng, P.hg)
        jmiss += 1 - calibrate(jmax[cal], alpha, "randomized").alarm_prob(jmax[P.nh:])
        lmiss += 1 - calibrate(lmax[cal], alpha, "randomized").alarm_prob(lmax[P.nh:])
    jmiss, lmiss = jmiss / S, lmiss / S
    cb = (jmax[P.nh:] <= 0.05).astype(float)          # every step confidently benign (conf >= 0.9)
    W = np.vstack([np.ones(len(P.aid)), bootstrap_weights(len(P.aid), B, rng, P.ag)])

    def stat(w):
        pl = (w * lmiss).sum() / w.sum()
        pcb = (w * cb * lmiss).sum() / max((w * cb).sum(), 1e-12)
        pj = (w * jmiss * lmiss).sum() / max((w * jmiss).sum(), 1e-12)
        return pl, pcb, pj
    v = np.array([stat(w) for w in W])
    rows.append(dict(panel=name, alpha=alpha, n_attack=len(P.aid), n_conf_benign=int(cb.sum()),
                     share_conf_benign=float(cb.mean()), p_llm_miss=v[0, 0],
                     p_llm_miss_given_jev_cb=v[0, 1], p_llm_miss_given_jev_miss=v[0, 2],
                     ratio_cb=v[0, 1] / max(v[0, 0], 1e-12),
                     ratio_cb_lo=float(np.quantile(v[1:, 1] / np.maximum(v[1:, 0], 1e-12), 0.025)),
                     ratio_cb_hi=float(np.quantile(v[1:, 1] / np.maximum(v[1:, 0], 1e-12), 0.975)),
                     ratio_miss=v[0, 2] / max(v[0, 0], 1e-12),
                     ratio_miss_lo=float(np.quantile(v[1:, 2] / np.maximum(v[1:, 0], 1e-12), 0.025)),
                     ratio_miss_hi=float(np.quantile(v[1:, 2] / np.maximum(v[1:, 0], 1e-12), 0.975))))


def length_rows(name, P, rows):
    y = [0] * P.nh + [1] * len(P.aid)
    lm = [np.nanmax(x) if len(x) else 0 for x in P.streams["len"]]
    ns = [len(x) for x in P.streams["len"]]
    hj = np.concatenate([x for x in P.streams["jev"][:P.nh]])
    hl = np.concatenate([x for x in P.streams["len"][:P.nh]])
    ok = np.isfinite(hj)
    rows.append(dict(panel=name, auroc_max_action_len=roc_auc_score(y, lm), auroc_n_steps=roc_auc_score(y, ns),
                     auroc_jev_max=roc_auc_score(y, plain_stats(P, "jev")),
                     auroc_llm_max=roc_auc_score(y, plain_stats(P, P.second)),
                     spearman_jev_len_honest_steps=spearmanr(hj[ok], hl[ok]).statistic,
                     spearman_jevmax_nsteps_honest=spearmanr(plain_stats(P, "jev")[:P.nh], ns[:P.nh]).statistic))


def breakdown(name, P, labels, S, B, rows, seed=0, keys=("jev_only", "llm_only", ("jev", 0.1), ("jev", 0.2))):
    d = make_design(P, S, B, seed)
    labels = np.asarray(labels, dtype=object)
    for lab in sorted(set(labels.tolist()), key=str):
        m = labels == lab
        if m.sum() < 15:
            continue
        for k in keys:
            cfg = ({"kind": "plain", "stream": "jev" if k == "jev_only" else P.second} if isinstance(k, str)
                   else {"kind": "cascade", "first": k[0], "e": k[1]})
            r = evaluate(P, d, cfg, ALPHAS, attack_mask=m)
            for a in ALPHAS:
                if np.mean(r[a]["n_cal"]) < MIN_CAL[a]:
                    continue
                s = summarize(tpr_boot([r], a))
                rows.append(dict(panel=name, label=lab, n_attack=int(m.sum()), config=str(k), alpha=a,
                                 tpr=s["est"], lo=s["lo"], hi=s["hi"]))


def load_decider(P):
    """Add the Decider P(suspicious) (benign-first question) to a MonitoringBench panel; returns coverage."""
    import glob
    from amd.common.schema import read_jsonl
    sc = {}
    for f in glob.glob(str(DEC / "*.jsonl")):
        for d in read_jsonl(f):
            src, tid, k = d["key"].split("|")
            pr = d["answers"]["verdict_bs"]["probabilities"]
            sc.setdefault(tid, {})[int(k)] = pr["suspicious"] / (pr["suspicious"] + pr["benign"])
    if not sc:
        return 0.0
    from amd.common.schema import PROCESSED, Trajectory
    T = {}
    for src in ("mb_honest", "monitoringbench"):
        for d in read_jsonl(PROCESSED / src / "trajectories.jsonl"):
            if d["traj_id"] in set(P.hid) | set(P.aid):
                T[d["traj_id"]] = Trajectory(**d)
    out, cov = [], []
    for t, L in zip(P.hid + P.aid, P.streams[P.second]):
        n = len(L)
        raw = np.array([sc.get(t, {}).get(k, np.nan) for k in range(min(len(T[t].steps), 60))], float)
        a = PN._fit(PN._strip(T[t], raw), n)
        cov.append(np.isfinite(a).mean())
        out.append(a)
    P.streams["decider"] = out
    return float(np.mean(cov))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=int, default=50)
    ap.add_argument("--boot", type=int, default=500)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    S, B = a.splits, a.boot
    variant, scheme = frozen()
    mb = PN.load_mb(variant, scheme)
    panels = [mb] + [PN.load_akshn(s, variant, scheme) for s in AKSHN]
    only = set(a.only.split(",")) if a.only else None

    if not only or "decider" in only:
        cov = load_decider(mb)
        if cov > 0:
            d = make_design(mb, S, 1000, 1)        # same seed as the primary mb design
            rows = []
            res = {"llm_only": evaluate(mb, d, {"kind": "plain", "stream": "llm"}, ALPHAS),
                   "decider_only": evaluate(mb, d, {"kind": "plain", "stream": "decider"}, ALPHAS),
                   "jev_only": evaluate(mb, d, {"kind": "plain", "stream": "jev"}, ALPHAS)}
            for e in E_LEVELS:
                for f in ("decider", "jev"):
                    res[(f, e)] = evaluate(mb, d, {"kind": "cascade", "first": f, "e": e}, ALPHAS)
            for al in ALPHAS:
                b0 = tpr_boot([res["llm_only"]], al)
                for k, r in res.items():
                    t = tpr_boot([r], al)
                    s, dd = summarize(t), summarize(t - b0)
                    vj = summarize(t - tpr_boot([res[("jev", k[1])] if isinstance(k, tuple) else res["jev_only"]], al))
                    rows.append(dict(config=str(k), alpha=al, tpr=s["est"], lo=s["lo"], hi=s["hi"], d_llm=dd["est"],
                                     d_llm_lo=dd["lo"], d_llm_hi=dd["hi"], d_vs_jev=vj["est"], d_vs_jev_lo=vj["lo"],
                                     d_vs_jev_hi=vj["hi"], coverage=cov))
            P_ = [x for x in mb.streams["decider"]]
            y = [0] * mb.nh + [1] * len(mb.aid)
            auc = roc_auc_score(y, plain_stats(mb, "decider"))
            pd.DataFrame(rows).assign(auroc_decider_max=auc).to_csv(OUT / "explore_decider_mb.csv", index=False)
            print("decider coverage", cov, "auroc", auc, flush=True)
            del P_

    if not only or "rq2" in only:
        dfs = []
        for P in panels:
            for st in ["jev", P.second] + (["nano"] if P.name == "mb" else []):
                df = standalone(P, st, S, B)
                df["panel"] = P.name
                dfs.append(df)
            print("rq2 standalone", P.name, flush=True)
        pd.concat(dfs).to_csv(OUT / "explore_rq2_standalone.csv", index=False)
        lrows = []
        for P in panels:
            length_rows(P.name, P, lrows)
        pd.DataFrame(lrows).to_csv(OUT / "explore_rq2_length.csv", index=False)
        brows = []
        breakdown("mb", mb, mb.meta["side"], S, B, brows)
        breakdown("mb", mb, [READABLE.get(s, "other") for s in mb.meta["side"]], S, B, brows)
        breakdown("mb", mb, mb.meta["struct"], S, B, brows)
        breakdown("mb", mb, mb.meta["agent"], S, B, brows)
        for P in panels[1:]:
            breakdown(P.name, P, P.meta["side"], S, B, brows)
        pd.DataFrame(brows).to_csv(OUT / "explore_rq2_breakdown.csv", index=False)

    if not only or "rq3" in only:
        grows, orows = [], []
        for i, P in enumerate(panels):
            gate_rows(P.name, P, S, B, 100 + i, grows)
            for al in ALPHAS:
                if True:
                    overlap(P.name, P, al, orows)
            print("rq3", P.name, flush=True)
        pd.DataFrame(grows).to_csv(OUT / "explore_rq3_gates.csv", index=False)
        pd.DataFrame(orows).to_csv(OUT / "explore_rq3_overlap.csv", index=False)


if __name__ == "__main__":
    main()
