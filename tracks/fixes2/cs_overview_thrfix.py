"""Threshold-convention rerun of the Idea 1 overview effects (docs/reports/src/make_overview_fig.py, panel a).

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.cs_overview_thrfix <plugin|conformal> [--parts ps,mole,chooser]

Each part calls the committed code that produced the number, with only the threshold convention switched (the
convention is set process-wide AND via AMD_THRESHOLD_CONVENTION so ProcessPool children inherit it):
  ps       results/fixes/corrections.csv rows C2 (t1 r1 GPT-4o; r2_t1 gpt-4.1-mini): tracks/fixes/c2_gains.contrast_row
           on the saved matched-eval raws (data/t1_raw/round1/ps__diff_current_only__gradual.pkl, seed 0;
           data/raw/r2_t1/ps_raw/raws.pkl key ps2:gpt-4.1-mini:current_only:gradual, seed 3), B = 1000, top-3 sum
           - max at FPR 0.05, iid (5 apps < 30 groups) with the app-cluster sensitivity. The raws hold per-split
           cross-fitted calibration / honest-test / attack statistics, which do not depend on the threshold rule.
  mole     results/r3_t1/mole_tables.md meta-analysis row "qwen_int | single-day | 3rd-max": for each of the four
           single-day corpora, tracks/r3_t1/mole_r3_analysis.{load, make_set, run_matched (full suite, 50 splits,
           300 boot, seed 0), gains_table (r3lib.gains_full, B = 2000)} and its DerSimonian-Laird `pooled`.
  chooser  results/fixes/corrections.csv row M6: tracks/fixes/chooser_fixed.main (40 splits, 20 task-drawn labeled
           attacks), nested design, FPR 0.01, `emp` chooser, family-cluster bootstrap CI. Outputs redirected.
Realized FPR = mean held-out honest alarm rate (same splits). Outputs: results/fixes2/cs_overview_<conv>_thrfix/.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import pickle
import sys

import numpy as np
import pandas as pd

from amd.common.schema import REPO
from amd.evaluation.calibration import calibrate, set_threshold_convention

TR = REPO / "tracks"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def realized(raw, alpha, det):
    """Mean over splits of the held-out honest alarm rate and of the attack TPR (active convention)."""
    f, t = [], []
    for r in raw:
        if r["detector"] == det:
            thr = calibrate(r["cal"], alpha, "randomized")
            f.append(thr.rate(np.asarray(r["test"], float)))
            t.append(thr.rate(np.asarray(r["attack"], float)))
    return float(np.mean(f)), float(np.mean(t))


def part_ps(out, boot=1000):
    sys.path.insert(0, str(TR / "fixes"))
    c2 = load(TR / "fixes" / "c2_gains.py", "c2_gains")
    app = c2._ctx_lookup("persistent_state", "app")
    rows = []
    # (1) t1 round 1, GPT-4o history-free current_only, gradual (c2_gains._r1_job, seed 0)
    d = pickle.loads((REPO / "data" / "t1_raw" / "round1" / "ps__diff_current_only__gradual.pkl").read_bytes())
    hgr = np.array([app[i] for i in d["honest_ids"]]); agr = np.array([app[i] for i in d["attack_ids"]])
    r = c2.contrast_row([(1, d["raw"], "top3sum"), (-1, d["raw"], "max")], len(d["honest_ids"]),
                        len(d["attack_ids"]), 0.05, None, None, boot, 0, extra_sens=(hgr, agr))
    rows.append(dict(claim="ps_gpt4o_top3_minus_max_fpr05", **r, **_fpr(d["raw"], 0.05, "top3sum")))
    # (2) r2_t1 gpt-4.1-mini history-free current_only, gradual (c2_gains.part_ps, seed 3)
    from ps_sets import r2_ps_sets
    raws = pickle.loads((REPO / "data" / "raw" / "r2_t1" / "ps_raw" / "raws.pkl").read_bytes())
    name = "ps2:gpt-4.1-mini:current_only:gradual"
    ss = {s.name: s for s in r2_ps_sets()}[name]
    hga = np.array([app[i] for i in ss.honest_ids]); aga = np.array([app[i] for i in ss.attack_ids])
    r = c2.contrast_row([(1, raws[name], "top3sum"), (-1, raws[name], "max")], ss.n_h, ss.n_a, 0.05, None, None,
                        boot, 3, extra_sens=(hga, aga))
    rows.append(dict(claim="ps_gpt41mini_top3_minus_max_fpr05", **r, **_fpr(raws[name], 0.05, "top3sum")))
    df = pd.DataFrame(rows)
    df.to_csv(out / "cs_overview_ps.csv", index=False)
    print(df.round(4).to_string(), flush=True)


def _fpr(raw, alpha, det):
    fm, tm = realized(raw, alpha, "max")
    fd, td = realized(raw, alpha, det)
    return dict(fpr_max=fm, fpr_det=fd, tpr_max=tm, tpr_det=td)


def part_mole(out):
    sys.path.insert(0, str(TR / "r3_t1"))
    m = load(TR / "r3_t1" / "mole_r3_analysis.py", "r3t1_mole_r3_analysis")
    dets = m.suite(extra_topk=True)
    G, M = [], []
    for corpus in [c for c in m.CORPORA if "single" in c]:
        D = m.load(corpus)
        D["qwen_int"] = D["qwen_int"].fillna(D["qwen_int"].median())
        ss = m.make_set(D, corpus, "qwen_int")
        df, raw = m.run_matched(ss, detectors=dets, alphas=m.ALPHAS, n_splits=50, n_boot=300, return_raw=True,
                                seed=0)
        df["corpus"] = corpus
        M.append(df)
        g = m.gains_table(ss, raw, (0.10,), ["max", "kth3"])
        g["corpus"] = corpus
        G.append(g)
        print(f"  {corpus}: n_h={ss.n_h} n_a={ss.n_a} kth3-max {g.gain_vs_max.iloc[0]:+.3f} "
              f"[{g.lo.iloc[0]:+.3f}, {g.hi.iloc[0]:+.3f}]", flush=True)
    G, M = pd.concat(G), pd.concat(M)
    mu, lo, hi, tau = m.pooled(G)
    sub = M[(M.alpha == 0.10) & (M.threshold_kind == "calibrated")]
    res = pd.DataFrame([dict(claim="mole_single_day_pooled_kth3_minus_max_fpr10", est=mu, lo=lo, hi=hi, tau=tau,
                             fpr_max=sub[sub.detector == "max"].fpr.mean(),
                             fpr_det=sub[sub.detector == "kth3"].fpr.mean(),
                             tpr_max=sub[sub.detector == "max"].tpr.mean(),
                             tpr_det=sub[sub.detector == "kth3"].tpr.mean())])
    G.to_csv(out / "cs_overview_mole_per_corpus.csv", index=False)
    M.to_csv(out / "cs_overview_mole_matched.csv", index=False)
    res.to_csv(out / "cs_overview_mole.csv", index=False)
    print(res.round(4).to_string(), flush=True)


def part_chooser(out, conv):
    sys.path.insert(0, str(TR / "fixes"))
    import chooser_fixed as cf  # importable by name so spawned ProcessPool children can unpickle run_set
    cf.OUT = out
    cf.RAW = REPO / "data" / "raw" / "fixes2_cs" / f"chooser_{conv}"
    argv = sys.argv
    sys.argv = [argv[0]]
    cf.main()
    sys.argv = argv
    S = pd.read_csv(out / "chooser_fixed_summary_task_lab20.csv")
    r = S[(S.design == "nested") & (S.alpha == 0.01) & (S.chooser == "emp")].iloc[0]
    res = pd.DataFrame([dict(claim="chooser_emp_vs_always_max_nested_fpr01", est=r.mean_gain_vs_max,
                             lo=r.family_boot_lo, hi=r.family_boot_hi, set_lo=r.set_boot_lo, set_hi=r.set_boot_hi,
                             fpr_det=r.mean_fpr, fpr_max=r.mean_fpr_max, win=r.win, loss=r.loss)])
    res.to_csv(out / "cs_overview_chooser.csv", index=False)
    print(res.round(4).to_string(), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("convention", choices=["plugin", "conformal"])
    ap.add_argument("--parts", default="ps,mole,chooser")
    a = ap.parse_args()
    os.environ["AMD_THRESHOLD_CONVENTION"] = a.convention
    set_threshold_convention(a.convention)
    out = REPO / "results" / "fixes2" / f"cs_overview_{a.convention}_thrfix"
    out.mkdir(parents=True, exist_ok=True)
    for p in a.parts.split(","):
        {"ps": lambda: part_ps(out), "mole": lambda: part_mole(out),
         "chooser": lambda: part_chooser(out, a.convention)}[p]()


if __name__ == "__main__":
    main()
