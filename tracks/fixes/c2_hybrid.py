"""Audit fix C2 for the r2_t1 length-aware hybrid table (results/r2_t1/hybrid_gains.csv): regenerate the
matched-eval raw outputs with the original call (tracks/r2_t1/hybrid.py: same sets, detectors, seed 0, 10 splits,
100 boot -> same splits) and recompute every per-set gain-over-max CI with amd.evaluation.paired (joint resample,
calibration noise, task clusters where the set is grouped). The hybrid summary (mean gains, win/loss counts) uses
point estimates only and is unchanged; this adds per-set significance and a set-family-level mean-gain CI.

    unset VIRTUAL_ENV; uv run python tracks/fixes/c2_hybrid.py
Writes results/fixes/r2_t1/hybrid_gains_corrected.csv, hybrid_summary_corrected.csv.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
for p in (HERE, HERE.parent / "r2_t1", HERE.parent / "t1_matched_budget"):
    sys.path.insert(0, str(p))

from amd.common.schema import REPO  # noqa: E402
from amd.evaluation import paired_gain_bootstrap  # noqa: E402

OUT = REPO / "results" / "fixes" / "r2_t1"


def job(ss):
    from hybrid import dets
    from r2lib import run_matched
    D = dets()
    hl = np.array([np.isfinite(s).sum() for s in ss.honest]); al = np.array([np.isfinite(s).sum() for s in ss.attack])
    _, raw = run_matched(ss, detectors=D, alphas=(0.05, 0.01), n_splits=10, n_boot=100, return_raw=True)
    rows = []
    for a in (0.05, 0.01):
        for d in D:
            if d == "max":
                continue
            r = paired_gain_bootstrap(raw, a, d, n_honest=ss.n_h, n_attack=ss.n_a, honest_groups=ss.honest_groups,
                                      attack_groups=ss.attack_groups, n_boot=1000, seed=0)
            rows.append(dict(set=ss.name, alpha=a, detector=d, est=r["est"], lo=r["lo"], hi=r["hi"], p_le0=r["p_le0"],
                             len_ratio=al.mean() / hl.mean()))
    return rows


def main():
    from chooser import collect_sets
    from chooser_fixed import family
    sets = [s for s in collect_sets(["r1", "mb"]) if len(s.attack) >= 15 and len(s.honest) >= 40]
    with ProcessPoolExecutor(4) as ex:
        G = pd.DataFrame([r for rr in ex.map(job, sets) for r in rr])
    old = pd.read_csv(REPO / "results" / "r2_t1" / "hybrid_gains.csv").rename(
        columns={"gain_vs_max": "old_est", "lo": "old_lo", "hi": "old_hi"})[["set", "alpha", "detector", "old_est", "old_lo", "old_hi"]]
    G = G.merge(old, on=["set", "alpha", "detector"], how="left")
    G.to_csv(OUT / "hybrid_gains_corrected.csv", index=False, float_format="%.4f")
    rng = np.random.default_rng(0)
    rows = []
    for (a, d), g in G.groupby(["alpha", "detector"]):
        fam = g.set.map(family).to_numpy(); uf = np.unique(fam)
        W = rng.multinomial(len(uf), np.full(len(uf), 1 / len(uf)), size=4000)[:, np.searchsorted(uf, fam)]
        bf = (W * g.est.to_numpy()).sum(1) / W.sum(1)
        rows.append(dict(alpha=a, detector=d, n_sets=len(g), mean_gain=g.est.mean(), family_lo=np.quantile(bf, .025),
                         family_hi=np.quantile(bf, .975), sig_pos_new=int((g.lo > 0).sum()), sig_neg_new=int((g.hi < 0).sum()),
                         sig_pos_old=int((g.old_lo > 0).sum()), sig_neg_old=int((g.old_hi < 0).sum())))
    S = pd.DataFrame(rows)
    S.to_csv(OUT / "hybrid_summary_corrected.csv", index=False, float_format="%.4f")
    print(S.round(3).to_string())


if __name__ == "__main__":
    main()
