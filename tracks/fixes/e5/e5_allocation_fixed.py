"""Corrected r2_t2 E5 allocation (audit issues C1 and M5).

Same signals, contexts, rules and replicate design as tracks/r2_t2/e5_new_streams.allocation
(17 signals; 7 T2 task clusters with >= 20 honest and >= 10 attacks; rules global / cfar /
pooled_cv / maxdet / stack / stack_m0; B = 1%, 5%; 30 plain + 60 bootstrap replicates; attacker
information for sel_informed = the calibration attacks, as in E5), with two corrections:

  C1  spend matching via e5fix_lib.sweep_matched: level swept on B x {0, 0.01..3 log-spaced, 1};
      interpolation only when B lies inside the replicate's realized-spend range, never clamped;
      realized spend of the nominal fit, matched_ok, and the spend floor (level 0) are recorded.
  M5  attacks deduplicated by content hash, and the attack split grouped by base attack
      (orig_traj_id) with a cluster bootstrap over bases (e5fix_lib.grouped_split).

Two designs are run so the two corrections can be separated:
  iid      original t2lib.split_panel (attack variants split iid) + fixed matching   (C1 only)
  grouped  grouped split by base attack + cluster bootstrap + fixed matching       (C1 + M5)
Originals-only allocation is not run (32 originals over 7 clusters, 1-9 per cluster); see
e5_auroc_fixed.py for originals-only AUROCs and honest-only-rule TPRs.

Outputs (results/fixes/r2_t2/): e5_allocation_fixed.csv (summary; spend, matched_ok shares,
spend floor, paired differences vs global), raw/e5_fixed_raw.parquet, raw/e5_fixed_curves.parquet
(plain-replicate sweep curves for the figure).

    unset VIRTUAL_ENV; uv run python tracks/fixes/e5/e5_allocation_fixed.py [--quick] [--workers 12]
"""
from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e5fix_lib as F  # noqa: E402

L, R = F.L, F.R
METRICS = ["spend", "tpr_uniform", "sel_informed", "sel_oracle"]
RULES = ["global", "cfar", "pooled_cv", "maxdet", "stack", "stack_m0"]


def run_signal(args):
    name, df, design, n_plain, n_boot, seed = args
    w = L.traffic(df)
    rng = np.random.default_rng(seed)
    rows, curves = [], []
    for rep in range(n_plain + n_boot):
        kind = "plain" if rep < n_plain else "boot"
        boot = kind == "boot"
        if design == "iid":
            Hc, Ht, Ac, At, _ = L.split_panel(df, rng, bootstrap=boot)
        else:
            Hc, Ht, Ac, At = F.grouped_split(df, rng, bootstrap=boot)
        Gc = L.Grid(Hc, w)
        hl0 = R.hulls_shrunk(Hc, Ac, 0.0)
        hl10 = R.hulls_shrunk(Hc, Ac, 10.0)

        def evalf(t):
            m = L.evaluate(t, Ht, At, w, Ac=Ac)
            return {k: m[k] for k in METRICS}
        for B in (0.01, 0.05):
            n0 = L.cv_n0(Hc, w, B, reps=1)
            fits = dict(global_=lambda b: L.rule_global(Gc, b), cfar=lambda b: L.rule_cfar(Gc, b),
                        pooled_cv=lambda b: L.rule_pooled(Gc, b, n0),
                        maxdet=lambda b: L.rule_maxdet(Hc, Ac, w, b),
                        stack=lambda b: L.rule_stackelberg(Hc, Ac, w, b, hull=hl0),
                        stack_m0=lambda b: L.rule_stackelberg(Hc, Ac, w, b, hull=hl10))
            for r, f in fits.items():
                rule = r.rstrip("_")
                s = F.sweep_matched(f, evalf, B, keep_curve=not boot)
                base = dict(signal=name, design=design, B=B, rule=rule, rep=rep, kind=kind,
                            floor=s["floor"], ceiling=s["ceiling"])
                rows.append(dict(base, mode="nominal", matched_ok=True, **s["nominal"]))
                rows.append(dict(base, mode="matched", **s["matched"]))
                if not boot:
                    for m, met in s["curve"]:
                        curves.append(dict(signal=name, design=design, B=B, rule=rule, rep=rep, mult=m, **met))
    return pd.DataFrame(rows), pd.DataFrame(curves)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--n_plain", type=int, default=30)
    ap.add_argument("--n_boot", type=int, default=60)
    ap.add_argument("--signals", default="")
    a = ap.parse_args()
    t0 = time.time()
    frames, sdf, base, meta, kept, st = F.load_panel()
    print("dedupe:", st, flush=True)
    keep_ids = set(kept.traj_id)
    bmap = dict(zip(meta.traj_id, meta.base))
    n_plain, n_boot = (2, 2) if a.quick else (a.n_plain, a.n_boot)
    sigs = [s for s in frames if not a.signals or s in a.signals.split(",")]
    jobs = []
    for i, name in enumerate(sigs):
        da = frames[name][1]
        da = da[(da.label == "honest") | da.traj_id.isin(keep_ids)].copy()
        da["base"] = da.traj_id.map(bmap)
        for design in ("iid", "grouped"):
            jobs.append((name, da, design, n_plain, n_boot, 13000 + i + (0 if design == "iid" else 500)))
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(run_signal, jobs))
    raw = pd.concat([r[0] for r in res], ignore_index=True)
    cur = pd.concat([r[1] for r in res], ignore_index=True)
    tag = "_quick" if a.quick else ""
    (F.OUT / "raw").mkdir(parents=True, exist_ok=True)
    raw.to_parquet(F.OUT / "raw" / f"e5_fixed_raw{tag}.parquet")
    cur.to_parquet(F.OUT / "raw" / f"e5_fixed_curves{tag}.parquet")
    S = F.summarize(raw, ["signal", "design", "B", "mode", "rule"], METRICS + ["floor"])
    S.to_csv(F.OUT / f"e5_allocation_fixed{tag}.csv", index=False, float_format="%.4g")
    print(f"done in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
