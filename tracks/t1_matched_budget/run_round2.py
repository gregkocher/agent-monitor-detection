"""Round 2: the controlled double-counting experiment on MonitoringBench + Honest-550.

Same monitor (gpt-4.1-mini, ctrl-basic-v1), same prompt, different history mode (full = history-aware,
none = history-free "innovation" monitor, window = last 3 actions). For each mode:
  matched-FPR TPR of the T1 suite, per attack structure S1-S4 (paired across detectors and modes:
  one set of honest splits), paired gains vs max, difference-in-differences across modes,
  honest autocorrelation, threshold inflation, streaming (delay from onset, alarm before the
  execution step), localization, Logit-ROC extrapolation, length checks.

    uv run python tracks/t1_matched_budget/run_round2.py [--prefix pilot_] [--modes full,none]
        [--score expected|int|lpge1] [--keep-submit] [--model openai_gpt-4.1-mini] [--tag NAME]

Conventions
- Submit: the final submit step is removed from both classes (78% of attacks vs 99% of honest end
  with submit; the submit step is a uniform near-zero unit that would differ in count by class).
  --keep-submit keeps it (robustness check).
- Onset: meta.first_attack_step (first action touching a side-task target; heuristic) when present,
  else attack_step (the execution step). Harm: attack_step (MonitoringBench's execution step), so
  before_harm = alarm at or before the payload executes.
- Scores: `expected` = logprob-expected 0-10 score (harness default); `int` = generated integer;
  `lpge1` = log P(score >= 1) from the digit logprobs (continuous; breaks gpt-4.1-mini's ties at 0).
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from t1lib import (ALPHAS, StreamSet, family, honest_autocorr, length_matched_indices, localization,  # noqa: E402
                   logit_roc_table, matched_arl, run_matched, streaming_metrics, subset, t1_suite)

from amd.common.schema import REPO, load_trajectories, read_jsonl, PROCESSED  # noqa: E402
from amd.evaluation import calibrate  # noqa: E402

OUT = REPO / "results" / "t1" / "round2"
RAW = REPO / "data" / "t1_raw" / "round2"   # per-split statistics (not committed)
KEY = ["max", "kth2", "top3sum", "mean", "cusum_k0.5", "cusum_k0.25", "sr_d1", "glr_w20", "eproc_power",
       "eproc_jumper_rand", "esr_power", "count>q0.95", "max_lenaware", "or(max+cusum)", "or(max+cusum+eproc)"]


def score_values(rec, kind):
    if kind == "expected":
        return np.array([np.nan if v is None else float(v) for v in rec["scores"]])
    if kind == "int":
        return np.array([np.nan if v is None else float(v) for v in rec["meta"]["int_scores"]])
    if kind == "lpge1":
        out = []
        for d, v in zip(rec["meta"]["digit_logprobs"], rec["scores"]):
            if d is None or v is None:
                out.append(np.nan); continue
            lp = {int(k): float(x) for k, x in d.items()}
            tot = np.logaddexp.reduce(list(lp.values()))
            ge1 = [x for k, x in lp.items() if k >= 1]
            out.append((np.logaddexp.reduce(ge1) - tot) if ge1 else -50.0)
        return np.maximum(np.array(out), -50.0)
    raise ValueError(kind)


def load_mode(mode, prefix="", score="expected", keep_submit=False, model="openai_gpt-4.1-mini",
              attack_ids=None):
    TA = {t.traj_id: t for t in load_trajectories("monitoringbench")}
    TH = {t.traj_id: t for t in load_trajectories("mb_honest")}
    H, A, hid, aid, hg, ag, on, hm, am = [], [], [], [], [], [], [], [], []
    for src, T in (("mb_honest", TH), ("monitoringbench", TA)):
        f = PROCESSED / src / f"{prefix}scores_{model}_{mode}.jsonl"
        for r in read_jsonl(f):
            t = T[r["traj_id"]]
            if attack_ids is not None and t.label == "attack" and t.traj_id not in attack_ids:
                continue
            s = score_values(r, score)
            if not keep_submit and t.meta.get("ends_with_submit") and t.meta.get("submit_step") == len(t.steps) - 1:
                if t.meta["submit_step"] < len(s):
                    s = s[: t.meta["submit_step"]]
            if not np.isfinite(s).any():
                continue
            g = str(t.context.get("task_id"))
            if t.label == "honest":
                H.append(s); hid.append(t.traj_id); hg.append(g)
            else:
                A.append(s); aid.append(t.traj_id); ag.append(g)
                fa = t.meta.get("first_attack_step")
                onset = fa if fa is not None else t.attack_step
                on.append(onset if onset is not None and onset < len(s) else None)
                hm.append(t.attack_step if t.attack_step is not None and t.attack_step < len(s) else None)
                am.append(dict(structure=t.meta.get("structural_strategy"), side_task=t.context.get("side_task"),
                               policy=t.context.get("policy"), n_steps=len(s), attack_step=t.attack_step,
                               first_attack_step=fa))
    order_h = np.argsort(hid)
    order_a = np.argsort(aid)
    pick = lambda xs, o: [xs[i] for i in o]  # noqa: E731
    return StreamSet(f"mb:{mode}", pick(H, order_h), pick(A, order_a), pick(hid, order_h), pick(aid, order_a),
                     np.array(pick(hg, order_h)), np.array(pick(ag, order_a)), pick(on, order_a),
                     pick(hm, order_a), pick(am, order_a), [], "step", "grouped by task_id")


def subgroup_tpr(raw, groups, alpha, method="randomized", n_boot=500, seed=0, dets=None):
    """TPR per (detector, attack subgroup) from the matched-eval raw output (thresholds from each split's
    cross-fitted calibration statistics). CI: bootstrap of attack trajectories within the subgroup,
    with the same resampled indices for every detector (paired), averaged over splits."""
    rng = np.random.default_rng(seed)
    groups = np.asarray(groups)
    by = {}
    for r in raw:
        if dets is None or r["detector"] in dets:
            by.setdefault(r["detector"], []).append(r)
    ug = sorted(set(groups))
    n_split = len(next(iter(by.values())))
    # resample indices per split per group (shared across detectors)
    idx_cache = {}
    for sp in range(n_split):
        aidx = next(iter(by.values()))[sp]["attack_idx"]
        for g in ug:
            m = np.flatnonzero(groups[aidx] == g)
            idx_cache[(sp, g)] = (m, rng.integers(len(m), size=(n_boot, len(m))) if len(m) else None)
    alarms = {}
    rows = []
    for det, rs in by.items():
        for g in ug:
            pts, boots = [], []
            for sp, r in enumerate(rs):
                thr = calibrate(r["cal"], alpha, method)
                p = thr.alarm_prob(r["attack"])
                m, bi = idx_cache[(sp, g)]
                if not len(m):
                    continue
                pts.append(p[m].mean())
                boots.append(p[m][bi].mean(axis=1))
                alarms[(det, g, sp)] = p[m]
            if not pts:
                continue
            b = np.mean(boots, axis=0)
            rows.append(dict(detector=det, group=g, alpha=alpha, tpr=np.mean(pts), lo=np.quantile(b, 0.025),
                             hi=np.quantile(b, 0.975), n=len(idx_cache[(0, g)][0])))
    return pd.DataFrame(rows), alarms, idx_cache


def paired_gains(alarms, idx_cache, dets, groups, ref="max", n_boot=500):
    rows = []
    for g in groups:
        for d in dets:
            if d == ref:
                continue
            pts, boots = [], []
            for sp in range(100):
                if (d, g, sp) not in alarms or (ref, g, sp) not in alarms:
                    continue
                diff = alarms[(d, g, sp)] - alarms[(ref, g, sp)]
                _, bi = idx_cache[(sp, g)]
                pts.append(diff.mean()); boots.append(diff[bi].mean(axis=1))
            if pts:
                b = np.mean(boots, axis=0)
                rows.append(dict(group=g, detector=d, gain_vs_max=np.mean(pts), lo=np.quantile(b, 0.025),
                                 hi=np.quantile(b, 0.975), p_le0=float((b <= 0).mean())))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="")
    ap.add_argument("--modes", default="full,none")
    ap.add_argument("--score", default="expected")
    ap.add_argument("--keep-submit", action="store_true")
    ap.add_argument("--model", default="openai_gpt-4.1-mini")
    ap.add_argument("--tag", default="main")
    ap.add_argument("--n-splits", type=int, default=10)
    ap.add_argument("--no-extras", action="store_true", help="skip streaming / ARL / localization / logit-ROC")
    ap.add_argument("--common-attacks", action="store_true", default=True)
    a = ap.parse_args()
    out = OUT / a.tag
    out.mkdir(parents=True, exist_ok=True)
    modes = a.modes.split(",")
    sets = {m: load_mode(m, a.prefix, a.score, a.keep_submit, a.model) for m in modes}
    # restrict every mode to the attacks / honest trajectories present in all modes (paired comparison)
    common_a = set.intersection(*[set(s.attack_ids) for s in sets.values()])
    common_h = set.intersection(*[set(s.honest_ids) for s in sets.values()])
    for m, s in sets.items():
        hi = [i for i, t in enumerate(s.honest_ids) if t in common_h]
        ai = [i for i, t in enumerate(s.attack_ids) if t in common_a]
        sets[m] = subset(s, hi, ai, s.name)
    tables: dict = {}
    meta = {}
    for m, ss in sets.items():
        print(f"== {m}: honest {ss.n_h}, attack {ss.n_a}", flush=True)
        struct = np.array([x["structure"] or "NA" for x in ss.attack_meta])
        df, raw = run_matched(ss, n_splits=a.n_splits, n_boot=300, return_raw=True, seed=0)
        df["mode"] = m
        tables.setdefault("matched", []).append(df)
        sg_all = []
        for alpha in ALPHAS:
            sg, alarms, idx = subgroup_tpr(raw, struct, alpha)
            sg["mode"] = m
            sg_all.append(sg)
            pg = paired_gains(alarms, idx, KEY, sorted(set(struct)))
            pg["mode"], pg["alpha"] = m, alpha
            tables.setdefault("gains_by_structure", []).append(pg)
            # pooled (all attacks)
            sgp, alp, idxp = subgroup_tpr(raw, np.array(["all"] * ss.n_a), alpha)
            sgp["mode"] = m
            sg_all.append(sgp)
            pgp = paired_gains(alp, idxp, KEY, ["all"])
            pgp["mode"], pgp["alpha"] = m, alpha
            tables.setdefault("gains_by_structure", []).append(pgp)
            meta[(m, alpha)] = (alarms, idx, alp, idxp)
        tables.setdefault("tpr_by_structure", []).append(pd.concat(sg_all))
        ac = honest_autocorr(ss.honest)
        ac.update(set=ss.name, mode=m)
        # attack-side structure: units above the honest unit 95% quantile, before / after onset
        hu = np.concatenate([s[np.isfinite(s)] for s in ss.honest])
        q95 = np.quantile(hu, 0.95)
        hi_counts = [np.sum(s[np.isfinite(s)] > q95) for s in ss.honest]
        ac["honest_units_gt_q95_per_traj"] = np.mean(hi_counts)
        ac["honest_traj_ge2_gt_q95"] = np.mean(np.array(hi_counts) >= 2)
        for S in sorted(set(struct)):
            ix = np.flatnonzero(struct == S)
            c = [np.sum(ss.attack[i][np.isfinite(ss.attack[i])] > q95) for i in ix]
            ac[f"attack_units_gt_q95_{S}"] = np.mean(c)
            ac[f"attack_ge2_gt_q95_{S}"] = np.mean(np.array(c) >= 2)
        tables.setdefault("autocorr", []).append(pd.DataFrame([ac]))
        thr = df[(df.threshold_kind == "calibrated")][["detector", "alpha", "threshold"]].copy()
        thr["mode"] = m
        tables.setdefault("thresholds", []).append(thr)
        hl = [np.isfinite(s).sum() for s in ss.honest]
        al = [np.isfinite(s).sum() for s in ss.attack]
        from scipy.stats import mannwhitneyu
        tables.setdefault("lengths", []).append(pd.DataFrame([dict(
            mode=m, n_honest=ss.n_h, n_attack=ss.n_a, len_h_med=np.median(hl), len_a_med=np.median(al),
            length_auroc=mannwhitneyu(al, hl).statistic / len(al) / len(hl))]))
        if not a.no_extras:
            sm, per = streaming_metrics(ss, alpha=0.01, n_splits=5)
            sm["mode"] = m
            tables.setdefault("streaming", []).append(sm)
            per["structure"] = np.tile(struct, len(per) // len(struct))
            g = per.groupby(["detector", "structure"])
            st = pd.DataFrame({"detection_rate": g.alarm.mean(), "early_rate": g.early.mean(),
                               "median_delay": g.delay.median(), "before_harm_rate": g.before_harm.mean()}).reset_index()
            st["mode"] = m
            tables.setdefault("streaming_by_structure", []).append(st)
            lo = localization(ss)
            lo["mode"] = m
            tables.setdefault("localization", []).append(lo)
            lr = logit_roc_table(raw, n_boot=100)
            lr["mode"] = m
            tables.setdefault("logit_roc", []).append(lr)
            ar = matched_arl(ss, n_sims=40)
            ar["mode"] = m
            tables.setdefault("arl", []).append(ar)
            # length-matched subsets (pooled attacks)
            hi_, ai_ = length_matched_indices(hl, al)
            sub = subset(ss, hi_, ai_, ss.name)
            dets = {k: v for k, v in t1_suite().items() if k in ("max", "kth2", "cusum_k0.5", "eproc_power",
                                                                   "glr_w20", "or(max+cusum)", "max_lenaware")}
            lm = run_matched(sub, detectors=dets, alphas=(0.05, 0.01), n_splits=a.n_splits, n_boot=100)
            lm["mode"], lm["n_matched"] = m, len(hi_)
            tables.setdefault("length_matched", []).append(lm)
        (RAW / a.tag).mkdir(parents=True, exist_ok=True)
        with open(RAW / a.tag / f"raw_{m}.pkl", "wb") as f:
            pickle.dump(dict(raw=raw, attack_ids=ss.attack_ids, honest_ids=ss.honest_ids, struct=struct,
                             onsets=ss.onsets, harm=ss.harm), f)
    # difference-in-differences: [gain(none) - gain(full)] paired over attacks (same attack ids in
    # both modes, same split seeds -> same attack test sets)
    if "full" in modes and len(modes) > 1:
        rows = []
        for other in [m for m in modes if m != "full"]:
            for alpha in ALPHAS:
                al_f, idx_f, alp_f, idxp_f = meta[("full", alpha)]
                al_o, idx_o, alp_o, idxp_o = meta[(other, alpha)]
                for grp, (A_f, A_o, I) in {**{g: (al_f, al_o, idx_f) for g in sorted(set(struct))},
                                           "all": (alp_f, alp_o, idxp_f)}.items():
                    for d in KEY:
                        if d == "max":
                            continue
                        pts, boots = [], []
                        for sp in range(100):
                            k = (d, grp, sp)
                            kr = ("max", grp, sp)
                            if k not in A_f or k not in A_o:
                                continue
                            dd = (A_o[k] - A_o[kr]) - (A_f[k] - A_f[kr])
                            _, bi = I[(sp, grp)]
                            pts.append(dd.mean()); boots.append(dd[bi].mean(axis=1))
                        if pts:
                            b = np.mean(boots, axis=0)
                            rows.append(dict(contrast=f"{other}-full", alpha=alpha, group=grp, detector=d,
                                             did=np.mean(pts), lo=np.quantile(b, 0.025), hi=np.quantile(b, 0.975),
                                             p_le0=float((b <= 0).mean())))
        tables["did"] = [pd.DataFrame(rows)]
    for k, v in tables.items():
        pd.concat(v, ignore_index=True).to_csv(out / f"{k}.csv", index=False)
    json.dump(dict(prefix=a.prefix, modes=modes, score=a.score, keep_submit=a.keep_submit, model=a.model,
                   n_honest=len(common_h), n_attack=len(common_a)), open(out / "config.json", "w"), indent=1)
    print("wrote", out, list(tables))


if __name__ == "__main__":
    main()
