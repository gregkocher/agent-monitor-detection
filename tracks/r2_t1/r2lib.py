"""Shared round-2 track-1 helpers: detector suite, matched-budget runs with paired gains, paired
difference-in-differences across two score sets of the same streams, and plotting style."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "t1_matched_budget"))
from t1lib import paired_gain, run_matched  # noqa: E402,F401

from amd.detectors import (CUSUM, ConformalEProcess, EDetectorSR, KthLargest, Max, Mean,  # noqa: E402
                           ShiryaevRoberts, TopKSum, Whiten)
from amd.evaluation import calibrate  # noqa: E402

LABEL = {"max": "max", "kth2": "2nd-max", "kth3": "3rd-max", "top2sum": "top-2 sum", "top3sum": "top-3 sum",
         "top4sum": "top-4 sum", "mean": "mean", "cusum_k0.5": "CUSUM k=0.5", "cusum_k1": "CUSUM k=1",
         "cusum_k1.5": "CUSUM k=1.5", "cusum_k2": "CUSUM k=2", "sr_d1": "Shiryaev-Roberts",
         "eproc_power": "e-process", "esr_power": "SR e-detector"}


def suite(extra_topk=False) -> dict:
    s = [Max(), KthLargest(2), TopKSum(2, transform=Whiten()), TopKSum(3, transform=Whiten()), Mean(),
         CUSUM(k=0.5, transform=Whiten()), CUSUM(k=1.0, transform=Whiten()), CUSUM(k=1.5, transform=Whiten()),
         CUSUM(k=2.0, transform=Whiten()), ShiryaevRoberts(delta=1.0, transform=Whiten()),
         ConformalEProcess("power"), EDetectorSR("power")]
    if extra_topk:
        s += [KthLargest(3), TopKSum(4, transform=Whiten())]
    return {d.name: d for d in s}


def gains_table(ss, raw, alphas, dets, base="max"):
    rows = []
    for a in alphas:
        for d in dets:
            if d == base:
                continue
            g, lo, hi = paired_gain(raw, a, a=d, b=base)
            rows.append(dict(set=ss.name, alpha=a, detector=d, gain_vs_max=g, lo=lo, hi=hi))
    return pd.DataFrame(rows)


def _alarm_by_split(raw, alpha, det, method="randomized"):
    out = {}
    for r in raw:
        if r["detector"] == det:
            out[r["split"]] = calibrate(r["cal"], alpha, method).alarm_prob(r["attack"]).astype(float)
    return out


def paired_did(raw1, raw2, alpha, det, base="max", n_boot=2000, seed=0):
    """[TPR1(det) - TPR1(base)] - [TPR2(det) - TPR2(base)] for two score sets of the SAME attack streams
    (same order), thresholds from each split's own calibration. Paired bootstrap over attack streams."""
    rng = np.random.default_rng(seed)
    a1, b1 = _alarm_by_split(raw1, alpha, det), _alarm_by_split(raw1, alpha, base)
    a2, b2 = _alarm_by_split(raw2, alpha, det), _alarm_by_split(raw2, alpha, base)
    sp = sorted(set(a1) & set(a2))
    diffs = [(a1[s] - b1[s]) - (a2[s] - b2[s]) for s in sp]
    est = float(np.mean([d.mean() for d in diffs]))
    n = len(diffs[0])
    idx = rng.integers(n, size=(n_boot, n))
    bs = np.mean([d[idx].mean(1) for d in diffs], axis=0)
    return est, float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))


def mpl_style():
    import matplotlib
    matplotlib.use("pdf")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titlesize": 9, "axes.labelsize": 8.5, "legend.fontsize": 7.5,
                         "pdf.fonttype": 42, "font.family": "sans-serif"})
    return plt


COLORS = {"max": "#4a4a4a", "kth2": "#2a78d6", "top2sum": "#7aa7e6", "top3sum": "#1baf7a", "mean": "#b0b0b0",
          "cusum_k0.5": "#e87ba4", "cusum_k1": "#d4579a", "cusum_k1.5": "#b23a80", "cusum_k2": "#7d2a63",
          "sr_d1": "#eda100", "eproc_power": "#eb6834", "esr_power": "#c4502a", "kth3": "#5b8fd6",
          "top4sum": "#0f7a55"}
