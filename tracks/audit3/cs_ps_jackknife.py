"""Audit pass 3 (track r4_cs): leave-one-app-out jackknife for the persistent-state accumulation contrast.

    unset VIRTUAL_ENV; uv run python tracks/audit3/cs_ps_jackknife.py [--splits 40]

The app-cluster bootstrap resamples only G = 5 clusters (percentile intervals with G = 5 are known to be
unreliable). As a sensitivity check, the contrast TPR(whitened top-3 sum) − TPR(max) is recomputed with each app
(its honest AND attack runs) removed, using the independent implementation in cs_indep_ps.py; jackknife
SE = sqrt((G-1)/G * sum (theta_i - mean)^2), interval = full estimate ± t_{0.975, G-1} * SE. Pooled = RE mean
with the DL weights fixed at their full-data values (read from cs_indep_ps.csv, app_indep scheme).
Outputs: results/audit3/cs_ps_jackknife.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

sys.path.insert(0, str(Path(__file__).parent))
from cs_indep_ps import FILES, OUT, alarm, dl, load, rand_thr, split_stats  # noqa: E402


def contrast(S, hon, att, keep_h, keep_a, splits, al, mon):
    H = np.vstack([S[mon][i] for i in np.array(hon)[keep_h]])
    A = np.vstack([S[mon][i] for i in np.array(att)[keep_a]])
    rng = np.random.default_rng(7)
    srng = np.random.default_rng(11)
    out = []
    for _ in range(splits):
        cal = np.sort(rng.permutation(len(H))[: len(H) // 2])
        test = np.setdiff1d(np.arange(len(H)), cal)
        st = split_stats(H[cal], H[test], A, srng)
        v = {}
        for d in ("max", "top3"):
            c, _, s = st[d]
            h, g = rand_thr(c, np.ones((1, len(c))), al)
            v[d] = alarm(s, h, g).mean()
        out.append(v["top3"] - v["max"])
    return float(np.mean(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=int, default=40)
    a = ap.parse_args()
    S, hon, att, happ, aapp = load()
    apps = np.unique(happ)
    full = pd.read_csv(OUT / "cs_indep_ps.csv")
    rows = []
    for al in (0.05, 0.01):
        sub = full[(full.alpha == al) & (full.scheme == "app_indep")].set_index("monitor").loc[list(FILES)]
        w = dl(sub.est, sub.se)["w"]
        th = {}
        for mon in FILES:
            th[mon] = [contrast(S, hon, att, happ != ap_, aapp != ap_, a.splits, al, mon) for ap_ in apps]
        th_full = {mon: contrast(S, hon, att, np.ones(len(hon), bool), np.ones(len(att), bool), a.splits, al, mon)
                   for mon in FILES}
        th["RE pooled (fixed weights)"] = list(np.array([th[m] for m in FILES]).T @ w)
        th_full["RE pooled (fixed weights)"] = float(np.array([th_full[m] for m in FILES]) @ w)
        G = len(apps)
        t = sps.t.ppf(0.975, G - 1)
        for k, v in th.items():
            v = np.array(v)
            se = np.sqrt((G - 1) / G * ((v - v.mean()) ** 2).sum())
            rows.append(dict(alpha=al, monitor=k, est_full=th_full[k], jk_se=se, lo=th_full[k] - t * se,
                             hi=th_full[k] + t * se, **{f"drop_{x}": y for x, y in zip(apps, v)}))
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "cs_ps_jackknife.csv", index=False)
    print(R.round(3).to_string())


if __name__ == "__main__":
    main()
