"""Threshold calibration at a target trajectory-level false-positive rate.

Alarm rule: alarm if S > h; if S == h (or, for a mixed threshold, h_lo < S <= h) alarm with
probability gamma. Rates are reported as expected alarm probabilities (no coin flips), which
is the exact value of a randomized test and has lower Monte Carlo variance.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class Threshold:
    h: float
    gamma: float = 0.0        # alarm probability in the randomization band
    h_lo: float | None = None  # band is (h_lo, h]; None = ties S == h only
    alpha: float | None = None
    n_cal: int = 0
    method: str = ""

    def alarm_prob(self, s: np.ndarray) -> np.ndarray:
        s = np.asarray(s, float)
        p = (s > self.h).astype(float)
        if self.gamma > 0:
            band = (s == self.h) if self.h_lo is None else ((s > self.h_lo) & (s <= self.h))
            p = p + self.gamma * band
        return p

    def rate(self, s: np.ndarray) -> float:
        s = np.asarray(s)
        return float(self.alarm_prob(s).mean()) if len(s) else float("nan")


def conformal_threshold(cal_stats, alpha: float) -> Threshold:
    """Finite-sample conservative threshold: h = k-th smallest calibration statistic with
    k = ceil((1 - alpha)(n + 1)); alarm iff S > h. For a new exchangeable honest statistic,
    P(S > h) <= (n + 1 - k)/(n + 1) <= alpha (ties only make it smaller). If k > n, h = +inf
    (alpha is below the resolution 1/(n+1) of the calibration set: no alarms)."""
    s = np.sort(np.asarray(cal_stats, float))
    n = len(s)
    k = math.ceil((1 - alpha) * (n + 1) - 1e-12)
    h = np.inf if k > n else float(s[k - 1])
    return Threshold(h=h, alpha=alpha, n_cal=n, method="conformal")


def randomized_threshold(cal_stats, alpha: float) -> Threshold:
    """Plug-in randomized threshold whose expected FPR on the calibration sample is exactly
    alpha: choose the smallest observed h with #{S > h}/n <= alpha, then alarm on ties S == h
    with probability gamma = (alpha n - #{S > h}) / #{S == h}. Removes discreteness (e.g. for
    integer scores or k-strikes counts) at the cost of the finite-sample conservativeness of
    the conformal rule (expected FPR ~ alpha rather than <= alpha)."""
    s = np.sort(np.asarray(cal_stats, float))
    n = len(s)
    target = alpha * n
    vals = np.unique(s)
    gt = n - np.searchsorted(s, vals, side="right")
    ok = np.flatnonzero(gt <= target + 1e-9)
    if len(ok) == 0:  # pragma: no cover - cannot happen (largest value has gt = 0)
        return Threshold(h=np.inf, alpha=alpha, n_cal=n, method="randomized")
    j = ok[0]
    h = float(vals[j])
    eq = int(np.sum(s == h))
    gamma = float(np.clip((target - gt[j]) / eq, 0.0, 1.0))
    return Threshold(h=h, gamma=gamma, alpha=alpha, n_cal=n, method="randomized")


def calibrate(cal_stats, alpha: float, method: str = "conformal") -> Threshold:
    if method == "conformal":
        return conformal_threshold(cal_stats, alpha)
    if method == "randomized":
        return randomized_threshold(cal_stats, alpha)
    raise ValueError(method)


# ------------------------------------------------------------------------------------------
# weighted (bootstrap) versions, vectorized over B replicate weight vectors
# ------------------------------------------------------------------------------------------


def weighted_conformal_h(sorted_stats: np.ndarray, W: np.ndarray, alpha: float) -> np.ndarray:
    """Conformal threshold for each row of integer multiplicity weights W (B, n) over
    `sorted_stats` (ascending): the k-th smallest of the resampled set."""
    m = W.sum(axis=1)
    k = np.ceil((1 - alpha) * (m + 1) - 1e-12)
    cw = np.cumsum(W, axis=1)
    idx = (cw < k[:, None]).sum(axis=1)  # first position where cumsum >= k
    h = np.full(W.shape[0], np.inf)
    ok = k <= m
    h[ok] = sorted_stats[np.minimum(idx[ok], len(sorted_stats) - 1)]
    return h


def weighted_rate(stats: np.ndarray, W: np.ndarray, h: np.ndarray) -> np.ndarray:
    """Weighted alarm rate (S > h_b) for each replicate b."""
    A = (stats[None, :] > h[:, None]).astype(float)
    return (A * W).sum(axis=1) / np.maximum(W.sum(axis=1), 1)
