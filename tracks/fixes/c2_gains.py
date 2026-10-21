"""Audit fix C2: recompute every 'gain over max' CI (T1 round 1 + round 2 MonitoringBench incl. DiD, r2_t1
persistent state incl. DiD, r2_t1 MOLE) with a correct paired bootstrap (amd.evaluation.paired):
one joint resample per replicate shared by all splits and all terms of the contrast, honest calibration resampled
with thresholds recomputed (calibration noise), clustered by task / account where the original split was grouped.

Point estimates are unchanged (same per-split statistics: the saved matched-eval raw outputs of the original runs;
MOLE's raw outputs were not saved and are regenerated with the original call and seed, which reproduces the
original split sequence). Old CIs are merged in for comparison.

    unset VIRTUAL_ENV; uv run python tracks/fixes/c2_gains.py [--parts r1,r2mb,ps,mole] [--boot 1000]

Writes results/fixes/t1/gains_r1_corrected.csv, gains_r2mb_corrected.csv, did_r2mb_corrected.csv and
results/fixes/r2_t1/ps_gains_corrected.csv, ps_did_corrected.csv, mole_gains_corrected.csv.
Raw per-split statistics of the regenerated MOLE runs go to data/raw/fixes/ (not committed).
"""
from __future__ import annotations

import argparse
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
for p in (HERE, HERE.parent / "t1_matched_budget", HERE.parent / "r2_t1"):
    sys.path.insert(0, str(p))

from amd.common.schema import REPO, load_trajectories  # noqa: E402
from amd.evaluation import paired_contrast_bootstrap  # noqa: E402

RES = REPO / "results"
OUT_T1 = RES / "fixes" / "t1"
OUT_R2 = RES / "fixes" / "r2_t1"
RAWFIX = REPO / "data" / "raw" / "fixes"
T1_ALPHAS = (0.05, 0.01, 0.003)
R1_ACCUM = ["cusum_k0.5", "cusum_k0.25", "sr_d1", "glr_w20", "eproc_power", "esr_power", "top3sum",
            "or(max+cusum)", "or(max+cusum+eproc)", "kth2", "mean", "max_lenaware", "count>q0.95"]


def _ctx_lookup(source, key):
    return {t.traj_id: str(t.context.get(key)) for t in load_trajectories(source)}


def contrast_row(terms, n_h, n_a, alpha, hg, ag, boot, seed, mask=None, extra_sens=None):
    """Corrected CI (clustered if groups) + attack-only shared-index CI (no calibration noise) for reference."""
    kw = dict(n_honest=n_h, n_attack=n_a, alpha=alpha, n_boot=boot, seed=seed, attack_mask=mask)
    full = paired_contrast_bootstrap(terms, honest_groups=hg, attack_groups=ag, **kw)
    att = paired_contrast_bootstrap(terms, calibration_noise=False, **kw)
    row = dict(est=full["est"], lo=full["lo"], hi=full["hi"], p_le0=full["p_le0"], p_ge0=full["p_ge0"],
               se=full["se"], att_only_lo=att["lo"], att_only_hi=att["hi"], n_splits=full["n_splits"],
               clustered=hg is not None)
    if extra_sens is not None:  # e.g. app-cluster sensitivity for persistent state
        s = paired_contrast_bootstrap(terms, honest_groups=extra_sens[0], attack_groups=extra_sens[1], **kw)
        row.update(sens_lo=s["lo"], sens_hi=s["hi"], sens_p_le0=s["p_le0"])
    row["sig"] = bool(row["lo"] > 0 or row["hi"] < 0)
    return row


# --------------------------------------------------------------------------- round 1 (40 stream sets)
R1_GROUP = {"la": ("linuxarena_sweep", "main_task"), "mrt": ("mrt", "task"), "ps": ("persistent_state", "app")}


def _r1_job(args):
    f, boot = args
    d = pickle.loads(f.read_bytes())
    name = f.stem.replace("__", ":")
    fam = name.split(":")[0]
    src, key = R1_GROUP.get(fam, (fam, "main_task")) if not fam.startswith("akshn") else (fam, "main_task")
    look = _ctx_lookup(src, key)
    hgr = np.array([look[i] for i in d["honest_ids"]])
    agr = np.array([look[i] for i in d["attack_ids"]])
    grouped = len(set(hgr)) >= 30          # same rule as t1lib.build_set (MIN_GROUPS)
    hg, ag = (hgr, agr) if grouped else (None, None)
    sens = (hgr, agr) if fam == "ps" else None
    n_h, n_a = len(d["honest_ids"]), len(d["attack_ids"])
    rows = []
    for alpha in T1_ALPHAS:
        for det in R1_ACCUM:
            if not any(r["detector"] == det for r in d["raw"]):
                continue
            r = contrast_row([(1, d["raw"], det), (-1, d["raw"], "max")], n_h, n_a, alpha, hg, ag, boot, 0,
                             extra_sens=sens)
            rows.append(dict(set_file=f.stem, alpha=alpha, detector=det, **r))
    return rows


def part_r1(boot, workers):
    files = sorted((REPO / "data" / "t1_raw" / "round1").glob("*.pkl"))
    with ProcessPoolExecutor(workers) as ex:
        rows = [r for rr in ex.map(_r1_job, [(f, boot) for f in files]) for r in rr]
    G = pd.DataFrame(rows)
    old = pd.read_csv(RES / "t1" / "round1" / "gain_la_akshn_mrt_ps.csv")
    old["set_file"] = old["set"].str.replace(":", "__").str.replace("/", "_")
    G = G.merge(old.rename(columns={"gain_vs_max": "old_est", "lo": "old_lo", "hi": "old_hi"})[
        ["set_file", "set", "alpha", "detector", "old_est", "old_lo", "old_hi"]], on=["set_file", "alpha", "detector"],
        how="left")
    G.to_csv(OUT_T1 / "gains_r1_corrected.csv", index=False, float_format="%.4f")
    return G


# --------------------------------------------------------------------------- round 2 MonitoringBench
R2_KEY = ["kth2", "top3sum", "mean", "cusum_k0.5", "cusum_k0.25", "sr_d1", "glr_w20", "eproc_power",
          "eproc_jumper_rand", "esr_power", "count>q0.95", "max_lenaware", "or(max+cusum)", "or(max+cusum+eproc)"]


def _r2_job(args):
    tag, boot = args
    base = REPO / "data" / "t1_raw" / "round2" / tag
    look = _ctx_lookup("monitoringbench", "task_id") | _ctx_lookup("mb_honest", "task_id")
    model = {t.traj_id: str(t.context.get("agent_model")) for t in load_trajectories("monitoringbench")}
    D = {m: pickle.loads((base / f"raw_{m}.pkl").read_bytes()) for m in ("full", "none")
         if (base / f"raw_{m}.pkl").exists()}
    gains, dids = [], []
    for mode, d in D.items():
        hg = np.array([look[i] for i in d["honest_ids"]]); ag = np.array([look[i] for i in d["attack_ids"]])
        n_h, n_a = len(hg), len(ag)
        groups = {"all": None}
        for s in sorted(set(d["struct"])):
            groups[s] = np.asarray(d["struct"]) == s
        am = np.array([model[i] for i in d["attack_ids"]])
        groups["opus-4-5"] = np.char.find(am.astype(str), "4-5") >= 0
        groups["opus-4-6"] = np.char.find(am.astype(str), "4-6") >= 0
        for alpha in T1_ALPHAS:
            for g, mask in groups.items():
                for det in R2_KEY:
                    r = contrast_row([(1, d["raw"], det), (-1, d["raw"], "max")], n_h, n_a, alpha, hg, ag, boot,
                                     1, mask=mask)
                    gains.append(dict(tag=tag, mode=mode, alpha=alpha, group=g, detector=det, **r))
    if len(D) == 2:
        df, dn = D["full"], D["none"]
        assert df["attack_ids"] == dn["attack_ids"] and df["honest_ids"] == dn["honest_ids"]
        hg = np.array([look[i] for i in df["honest_ids"]]); ag = np.array([look[i] for i in df["attack_ids"]])
        groups = {"all": None} | {s: np.asarray(df["struct"]) == s for s in sorted(set(df["struct"]))}
        for alpha in T1_ALPHAS:
            for g, mask in groups.items():
                for det in R2_KEY:
                    terms = [(1, dn["raw"], det), (-1, dn["raw"], "max"), (-1, df["raw"], det), (1, df["raw"], "max")]
                    r = contrast_row(terms, len(hg), len(ag), alpha, hg, ag, boot, 2, mask=mask)
                    dids.append(dict(tag=tag, contrast="none-full", alpha=alpha, group=g, detector=det, **r))
    return gains, dids


def part_r2(boot, workers, tags=("main", "nano", "score_int")):
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(_r2_job, [(t, boot) for t in tags]))
    G = pd.DataFrame([r for g, _ in res for r in g]); D = pd.DataFrame([r for _, d in res for r in d])
    olds = []
    for t in tags:
        f = RES / "t1" / "round2" / t / "gains_by_structure.csv"
        if f.exists():
            o = pd.read_csv(f).assign(tag=t)
            olds.append(o)
    O = pd.concat(olds).rename(columns={"gain_vs_max": "old_est", "lo": "old_lo", "hi": "old_hi", "p_le0": "old_p_le0"})
    G = G.merge(O[["tag", "mode", "alpha", "group", "detector", "old_est", "old_lo", "old_hi"]],
                on=["tag", "mode", "alpha", "group", "detector"], how="left")
    G.to_csv(OUT_T1 / "gains_r2mb_corrected.csv", index=False, float_format="%.4f")
    if len(D):
        od = []
        for t in tags:
            f = RES / "t1" / "round2" / t / "did.csv"
            if f.exists():
                od.append(pd.read_csv(f).assign(tag=t))
        OD = pd.concat(od).rename(columns={"did": "old_est", "lo": "old_lo", "hi": "old_hi"})
        D = D.merge(OD[["tag", "alpha", "group", "detector", "old_est", "old_lo", "old_hi"]],
                    on=["tag", "alpha", "group", "detector"], how="left")
        D.to_csv(OUT_T1 / "did_r2mb_corrected.csv", index=False, float_format="%.4f")
    return G, D


# --------------------------------------------------------------------------- r2_t1 persistent state
PS_KEY = ["kth2", "top2sum", "top3sum", "mean", "cusum_k0.5", "cusum_k1.5", "cusum_k2", "sr_d1", "eproc_power"]


def part_ps(boot):
    from ps_sets import r2_ps_sets
    raws = pickle.loads((REPO / "data" / "raw" / "r2_t1" / "ps_raw" / "raws.pkl").read_bytes())
    sets = {s.name: s for s in r2_ps_sets()}
    app = _ctx_lookup("persistent_state", "app")
    gains, dids = [], []
    for name, raw in raws.items():
        ss = sets[name]
        hga = np.array([app[i] for i in ss.honest_ids]); aga = np.array([app[i] for i in ss.attack_ids])
        for alpha in (0.05, 0.01):
            for det in PS_KEY:
                r = contrast_row([(1, raw, det), (-1, raw, "max")], ss.n_h, ss.n_a, alpha, None, None, boot, 3,
                                 extra_sens=(hga, aga))
                gains.append(dict(set=name, alpha=alpha, detector=det, **r))
        p = name.split(":")
        if p[2] == "current_only":
            other = ":".join([p[0], p[1], "full_diffs", p[3]])
            if other in raws:
                assert sets[other].attack_ids == ss.attack_ids and sets[other].honest_ids == ss.honest_ids
                for alpha in (0.05, 0.01):
                    for det in PS_KEY:
                        terms = [(1, raw, det), (-1, raw, "max"), (-1, raws[other], det), (1, raws[other], "max")]
                        r = contrast_row(terms, ss.n_h, ss.n_a, alpha, None, None, boot, 4, extra_sens=(hga, aga))
                        dids.append(dict(monitor=p[1], policy=p[3], alpha=alpha, detector=det, **r))
        print(f"  ps {name}", flush=True)
    G = pd.DataFrame(gains).merge(pd.read_csv(RES / "r2_t1" / "ps_gains.csv").rename(
        columns={"gain_vs_max": "old_est", "lo": "old_lo", "hi": "old_hi"}), on=["set", "alpha", "detector"], how="left")
    D = pd.DataFrame(dids).merge(pd.read_csv(RES / "r2_t1" / "ps_did.csv").rename(
        columns={"did_none_minus_full": "old_est", "lo": "old_lo", "hi": "old_hi"}),
        on=["monitor", "policy", "alpha", "detector"], how="left")
    G.to_csv(OUT_R2 / "ps_gains_corrected.csv", index=False, float_format="%.4f")
    D.to_csv(OUT_R2 / "ps_did_corrected.csv", index=False, float_format="%.4f")
    return G, D


# --------------------------------------------------------------------------- r2_t1 MOLE
MOLE_SHOW = ["kth2", "kth3", "top2sum", "top3sum", "top4sum", "mean", "cusum_k0.5", "cusum_k1", "cusum_k1.5",
             "cusum_k2", "sr_d1", "eproc_power"]


def _mole_job(args):
    corpus, mon, exec_only, drop, boot = args
    from mole_sets import account_sets, load_days
    from r2lib import run_matched, suite
    D = load_days(corpus)
    if mon not in D or D[mon].isna().mean() > 0.02:
        return []
    D[mon] = D[mon].fillna(D[mon].median())
    ss = account_sets(corpus, mon, exec_only, D, drop_attack_days=drop)
    f = RAWFIX / f"mole_raw__{ss.name.replace(':', '__')}.pkl"
    if f.exists():
        raw = pickle.loads(f.read_bytes())
    else:  # identical call to tracks/r2_t1/mole_analysis.py (seed 0, 50 splits, 300 boot): same splits
        _, raw = run_matched(ss, detectors=suite(extra_topk=True), alphas=(0.10, 0.05), n_splits=50, n_boot=300,
                             return_raw=True, seed=0)
        f.write_bytes(pickle.dumps(raw))
    rows = []
    for alpha in (0.10, 0.05):
        for det in MOLE_SHOW:
            r = contrast_row([(1, raw, det), (-1, raw, "max")], ss.n_h, ss.n_a, alpha, None, None, boot, 5)
            rows.append(dict(set=ss.name, alpha=alpha, detector=det, n_h=ss.n_h, n_a=ss.n_a, **r))
    return rows


def part_mole(boot, workers):
    from mole_sets import CORPORA, MONITORS
    RAWFIX.mkdir(parents=True, exist_ok=True)
    jobs = [(c, m, e, d, boot) for c in CORPORA for m in MONITORS for e, d in ((False, False), (True, False),
                                                                               (False, True))]
    with ProcessPoolExecutor(workers) as ex:
        rows = [r for rr in ex.map(_mole_job, jobs) for r in rr]
    G = pd.DataFrame(rows).merge(pd.read_csv(RES / "r2_t1" / "mole_gains.csv").rename(
        columns={"gain_vs_max": "old_est", "lo": "old_lo", "hi": "old_hi"}), on=["set", "alpha", "detector"], how="left")
    G.to_csv(OUT_R2 / "mole_gains_corrected.csv", index=False, float_format="%.4f")
    return G


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", default="r1,r2mb,ps,mole")
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    OUT_T1.mkdir(parents=True, exist_ok=True); OUT_R2.mkdir(parents=True, exist_ok=True)
    for p in a.parts.split(","):
        t0 = time.time()
        if p == "r1":
            part_r1(a.boot, a.workers)
        elif p == "r2mb":
            part_r2(a.boot, a.workers)
        elif p == "ps":
            part_ps(a.boot)
        elif p == "mole":
            part_mole(a.boot, a.workers)
        print(f"{p} done in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
