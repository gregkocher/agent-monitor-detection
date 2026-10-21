"""Length-aware + top-k hybrid: calibrate an order-statistic / top-k detector separately by stream length.

LengthBinned(inner, n_bins): the inner detector's running statistic S_t (max over its path so far) is turned
into -log of its honest tail probability among honest calibration streams in the same length bin as the
current length t (bins = quantiles of honest lengths; conformal tail (1 + #{S_cal >= s}) / (n_bin + 1) with a
mid-rank tie split). Final-value statistic, so one global threshold on it gives ~ equal FPR across length
bins. This generalizes the length-aware max (analytic power-law null) to any order statistic / top-k sum.

    uv run python tracks/r2_t1/hybrid.py [--sets r1,mb] [--splits 10]
Writes results/r2_t1/hybrid_matched.csv, hybrid_summary.md.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "t1_matched_budget"))

from amd.common.schema import REPO  # noqa: E402
from amd.detectors import KthLargest, LengthAwareMax, Max, TopKSum, Whiten  # noqa: E402
from amd.detectors.base import Detector, Packed  # noqa: E402

OUT = REPO / "results" / "r2_t1"


class LengthBinned(Detector):
    alarm_type = False

    def __init__(self, inner: Detector, n_bins: int = 3):
        super().__init__(None)
        self.inner = inner
        self.n_bins = n_bins
        self.name = f"lenbin({inner.name})"

    def _fit_packed(self, Ph: Packed, Pa=None, attack_onsets=None):
        self.inner = self.inner.clone()._fit_packed(Ph, Pa, attack_onsets)
        st = self.inner.stats_packed(Ph)
        L = Ph.lengths
        ok = L > 0
        self.edges_ = np.unique(np.quantile(L[ok], np.linspace(0, 1, self.n_bins + 1)[1:-1]))
        b = np.digitize(L[ok], self.edges_, right=True)
        self.cal_ = [np.sort(st[ok][b == k]) for k in range(len(self.edges_) + 1)]
        self.fitted_ = True
        return self

    def paths_packed(self, P: Packed) -> np.ndarray:
        ip = self.inner.paths_packed(P)
        if self.inner.alarm_type:
            ip = np.maximum.accumulate(np.where(P.mask, ip, -np.inf), axis=1)
        t = np.arange(1, ip.shape[1] + 1)
        bins = np.digitize(t, self.edges_, right=True)
        out = np.empty_like(ip, dtype=float)
        for k, cal in enumerate(self.cal_):
            cols = np.flatnonzero(bins == k)
            if not len(cols):
                continue
            x = ip[:, cols]
            n = len(cal)
            ge = n - np.searchsorted(cal, x, side="left")
            gt = n - np.searchsorted(cal, x, side="right")
            tail = (1 + 0.5 * (ge + gt)) / (n + 1)
            out[:, cols] = -np.log(tail)
        return out


def dets():
    d = {"max": Max(), "max_lenaware": LengthAwareMax(), "kth2": KthLargest(2), "top3sum": TopKSum(3, transform=Whiten())}
    for k in ("max", "kth2", "top3sum"):
        d[f"lenbin({k})"] = LengthBinned(d[k])
    return d


def main():
    from chooser import collect_sets
    from r2lib import gains_table, run_matched
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="r1,mb")
    ap.add_argument("--splits", type=int, default=10)
    a = ap.parse_args()
    rows, gains = [], []
    D = dets()
    for ss in collect_sets(a.sets.split(",")):
        if len(ss.attack) < 15 or len(ss.honest) < 40:
            continue
        hl = np.array([np.isfinite(s).sum() for s in ss.honest]); al = np.array([np.isfinite(s).sum() for s in ss.attack])
        df, raw = run_matched(ss, detectors=D, alphas=(0.05, 0.01), n_splits=a.splits, n_boot=100, return_raw=True)
        df["len_ratio"] = al.mean() / hl.mean()
        rows.append(df)
        g = gains_table(ss, raw, (0.05, 0.01), list(D))
        g["len_ratio"] = al.mean() / hl.mean()
        gains.append(g)
        print(f"  {ss.name} len_ratio={al.mean() / hl.mean():.2f}", flush=True)
    M, G = pd.concat(rows), pd.concat(gains)
    M.to_csv(OUT / "hybrid_matched.csv", index=False)
    G.to_csv(OUT / "hybrid_gains.csv", index=False)
    lines = ["# Length-aware hybrids: mean TPR gain over max across stream sets", "",
             "| alpha | detector | all sets: mean gain | sets with |log len ratio| > 0.2: mean gain (n) | win/loss (>0.01) |",
             "|---|---|---|---|---|"]
    for (al, d), g in G.groupby(["alpha", "detector"]):
        big = g[np.abs(np.log(g.len_ratio)) > 0.2]
        lines.append(f"| {al} | {d} | {g.gain_vs_max.mean():+.3f} | {big.gain_vs_max.mean():+.3f} ({len(big)}) | "
                     f"{(g.gain_vs_max > 0.01).sum()}/{(g.gain_vs_max < -0.01).sum()} |")
    sub = M[M.threshold_kind == "calibrated"]
    lines += ["", "Realized FPR (mean over sets) at alpha: " + ", ".join(
        f"{d}@{al}: {g.fpr.mean():.3f}" for (al, d), g in sub.groupby(["alpha", "detector"]))]
    (OUT / "hybrid_summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
