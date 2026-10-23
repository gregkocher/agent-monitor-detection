"""Threshold calibration at a target trajectory-level false-positive rate.

Alarm rule: alarm if S > h; if S == h (or, for a mixed threshold, h_lo < S <= h) alarm with
probability gamma. Rates are reported as expected alarm probabilities (no coin flips), which
is the exact value of a randomized test and has lower Monte Carlo variance.

Threshold conventions for the randomized rule (method="randomized"):
  "plugin"     (default; every committed result up to 2026-10-23) -- randomized_threshold_plugin: smallest
               observed h with #{S > h} <= alpha n, ties randomized so the IN-SAMPLE rate is alpha. For a new
               exchangeable continuous score the expected FPR is (floor(alpha n) + 1)/(n + 1), which exceeds
               alpha (n = 100 at 1%: 1.98%).
  "conformal"  -- conformal_randomized_threshold: the smoothed conformal p-value test. A new score s alarms
               with probability clip((alpha (n + 1) - #{S_i > s}) / (#{S_i == s} + 1), 0, 1), i.e. alarm iff
               p(s) = (#{S_i > s} + U (#{S_i == s} + 1)) / (n + 1) <= alpha with U ~ Unif(0, 1). For
               exchangeable scores (continuous, tied or discrete) the expected out-of-sample FPR is exactly
               alpha. Equivalently: threshold at the k-th order statistic, k = ceil((1 - alpha)(n + 1)), with
               random tie-breaking and a randomized band one order statistic below it.
Select the convention per call (calibrate(..., method="conformal_randomized")), per block
(`with threshold_convention("conformal"):` makes method="randomized" and randomized_threshold use it), or per
process (environment variable AMD_THRESHOLD_CONVENTION=conformal). Weighted / per-replicate versions:
`row_thresholds`.
"""
from __future__ import annotations

import math
import os
from contextlib import contextmanager
from dataclasses import dataclass

import numpy as np

CONVENTIONS = ("plugin", "conformal")
_CONVENTION = [os.environ.get("AMD_THRESHOLD_CONVENTION", "plugin")]
if _CONVENTION[0] not in CONVENTIONS:  # pragma: no cover
    raise ValueError(f"AMD_THRESHOLD_CONVENTION must be one of {CONVENTIONS}, got {_CONVENTION[0]!r}")


def get_threshold_convention() -> str:
    return _CONVENTION[0]


def set_threshold_convention(name: str) -> str:
    """Set the process-wide convention used by method="randomized"; returns the previous one."""
    if name not in CONVENTIONS:
        raise ValueError(f"convention must be one of {CONVENTIONS}, got {name!r}")
    prev, _CONVENTION[0] = _CONVENTION[0], name
    return prev


@contextmanager
def threshold_convention(name: str):
    prev = set_threshold_convention(name)
    try:
        yield
    finally:
        set_threshold_convention(prev)


def resolve_method(method: str) -> str:
    """Map method="randomized" to the concrete rule of the active convention."""
    if method == "randomized":
        return "randomized" if _CONVENTION[0] == "plugin" else "conformal_randomized"
    return method


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
    """Randomized threshold under the active convention (plug-in by default; see module docstring)."""
    if _CONVENTION[0] == "conformal":
        return conformal_randomized_threshold(cal_stats, alpha)
    return randomized_threshold_plugin(cal_stats, alpha)


def randomized_threshold_plugin(cal_stats, alpha: float) -> Threshold:
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


# ------------------------------------------------------------------------------------------
# conformal randomized (smoothed conformal p-value) rule
# ------------------------------------------------------------------------------------------


def _smoothed_prob(alpha, m, gt, eq):
    """Alarm probability of the smoothed conformal test: calibration mass m, mass strictly above the
    score gt, mass tied with it eq (masses in units of one calibration trajectory)."""
    return np.clip((alpha * (m + 1.0) - gt) / (eq + 1.0), 0.0, 1.0)


@dataclass
class ConformalRandomizedThreshold(Threshold):
    """Smoothed conformal rule; `h` is the value above which alarms are certain (k-th order statistic,
    k = ceil((1 - alpha)(n + 1)); +inf if k > n) and `gamma` the band probability frac(alpha (n + 1)).
    alarm_prob uses the stored calibration distribution (vals ascending, cum = mass at or below vals)."""
    vals: np.ndarray | None = None
    cum: np.ndarray | None = None

    def alarm_prob(self, s: np.ndarray) -> np.ndarray:
        s = np.asarray(s, float)
        cpad = np.r_[0.0, self.cum]
        m = cpad[-1]
        le = cpad[np.searchsorted(self.vals, s, side="right")]
        lt = cpad[np.searchsorted(self.vals, s, side="left")]
        return _smoothed_prob(self.alpha, m, m - le, le - lt)


def conformal_randomized_threshold(cal_stats, alpha: float, weights=None) -> ConformalRandomizedThreshold:
    """Conformally valid randomized threshold: expected out-of-sample FPR exactly alpha for exchangeable
    scores, with or without ties (see module docstring). `weights`: optional nonnegative calibration
    multiplicities (e.g. bootstrap counts); masses are in units of one trajectory."""
    s = np.asarray(cal_stats, float)
    w = np.ones(len(s)) if weights is None else np.asarray(weights, float)
    keep = w > 0
    s, w = s[keep], w[keep]
    vals, inv = np.unique(s, return_inverse=True)
    mass = np.bincount(inv, weights=w, minlength=len(vals))
    cum = np.cumsum(mass)
    m = float(cum[-1]) if len(cum) else 0.0
    # certain-alarm level: smallest value v with mass(> v) <= alpha (m + 1) - 1
    gt = m - cum
    ok = np.flatnonzero(gt <= alpha * (m + 1.0) - 1.0 + 1e-9)
    h = float(vals[ok[0]]) if len(ok) else np.inf
    gamma = float(alpha * (m + 1.0) - math.floor(alpha * (m + 1.0) + 1e-9))
    return ConformalRandomizedThreshold(h=h, gamma=gamma, alpha=alpha, n_cal=len(s),
                                        method="conformal_randomized", vals=vals, cum=cum)


def calibrate(cal_stats, alpha: float, method: str = "conformal") -> Threshold:
    """method: "conformal" (conservative, deterministic), "randomized" (active convention: plug-in by
    default), "randomized_plugin" or "conformal_randomized" (explicit)."""
    method = resolve_method(method)
    if method == "conformal":
        return conformal_threshold(cal_stats, alpha)
    if method in ("randomized", "randomized_plugin"):
        return randomized_threshold_plugin(cal_stats, alpha)
    if method == "conformal_randomized":
        return conformal_randomized_threshold(cal_stats, alpha)
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


# ------------------------------------------------------------------------------------------
# per-replicate thresholds (bootstrap rows), one interface for every rule
# ------------------------------------------------------------------------------------------


class RowThresholds:
    """B per-replicate thresholds. alarm(S) -> (B, n) alarm probabilities for test statistics S of shape
    (n,) (shared by all rows) or (B, n) / (1, n) (per row); rate(S, W) -> (B,) weighted alarm rate.
    Supports row slicing (thr[:1])."""

    def alarm(self, S) -> np.ndarray:  # pragma: no cover - interface
        raise NotImplementedError

    def rate(self, S, W=None) -> np.ndarray:
        A = self.alarm(S)
        if W is None:
            return A.mean(axis=1)
        return (A * W).sum(axis=1) / np.maximum(np.asarray(W).sum(axis=1), 1e-12)


class PluginRows(RowThresholds):
    """(h, gamma) rows: alarm if S > h, with probability gamma if S == h (plug-in and conformal rules)."""

    def __init__(self, h, gamma):
        self.h, self.gamma = np.asarray(h, float), np.asarray(gamma, float)

    def __len__(self):
        return len(self.h)

    def __getitem__(self, k):
        return PluginRows(np.atleast_1d(self.h[k]), np.atleast_1d(self.gamma[k]))

    def alarm(self, S):
        S = np.asarray(S, float)
        S2 = S[None, :] if S.ndim == 1 else S
        return (S2 > self.h[:, None]) + self.gamma[:, None] * (S2 == self.h[:, None])


class SmoothedRows(RowThresholds):
    """Conformal randomized rule per row. Shared calibration values `vals` (U,) ascending with per-row
    cumulative masses `cum` (B, U), or per-row values (`per_row=True`: vals (B, n) ascending per row)."""

    def __init__(self, vals, cum, alpha, per_row=False):
        self.vals, self.cum, self.alpha, self.per_row = vals, np.atleast_2d(cum), float(alpha), per_row
        self.m = self.cum[:, -1] if self.cum.shape[1] else np.zeros(self.cum.shape[0])
        # informational: certain-alarm level and band probability
        self.gamma = self.alpha * (self.m + 1) - np.floor(self.alpha * (self.m + 1) + 1e-9)

    def __len__(self):
        return self.cum.shape[0]

    def __getitem__(self, k):
        cum = np.atleast_2d(self.cum[k])
        vals = np.atleast_2d(self.vals[k]) if self.per_row else self.vals
        return SmoothedRows(vals, cum, self.alpha, self.per_row)

    def _le_lt(self, S):
        B = self.cum.shape[0]
        cpad = np.concatenate([np.zeros((B, 1)), self.cum], axis=1)
        S = np.asarray(S, float)
        if not self.per_row:
            if S.ndim == 1:
                ir = np.searchsorted(self.vals, S, side="right")
                il = np.searchsorted(self.vals, S, side="left")
                return cpad[:, ir], cpad[:, il]
            S = np.broadcast_to(S, (B, S.shape[1]))
            ir = np.searchsorted(self.vals, S, side="right")
            il = np.searchsorted(self.vals, S, side="left")
            r = np.arange(B)[:, None]
            return cpad[r, ir], cpad[r, il]
        # per-row values: rank-code every value, then one flat searchsorted with row offsets
        V = self.vals
        S = np.broadcast_to(S[None, :] if S.ndim == 1 else S, (B, S.shape[-1]))
        allv, codes = np.unique(np.concatenate([V.ravel(), S.ravel()]), return_inverse=True)
        K = len(allv) + 1
        cv = codes[: V.size].reshape(V.shape).astype(np.int64)
        cs = codes[V.size:].reshape(S.shape).astype(np.int64)
        off = (np.arange(B, dtype=np.int64) * K)[:, None]
        flat = (cv + off).ravel()
        n = V.shape[1]
        ir = np.searchsorted(flat, (cs + off).ravel(), side="right").reshape(S.shape) - np.arange(B)[:, None] * n
        il = np.searchsorted(flat, (cs + off).ravel(), side="left").reshape(S.shape) - np.arange(B)[:, None] * n
        r = np.arange(B)[:, None]
        return cpad[r, ir], cpad[r, il]

    def alarm(self, S):
        le, lt = self._le_lt(S)
        m = self.m[:, None]
        return _smoothed_prob(self.alpha, m, m - le, le - lt)


def smoothed_rows_shared(stats, W, alpha) -> SmoothedRows:
    """Conformal randomized rows for calibration statistics `stats` (n,) shared by every row, with
    per-row nonnegative multiplicities W (B, n)."""
    stats = np.asarray(stats, float)
    W = np.atleast_2d(np.asarray(W, float))
    vals, inv = np.unique(stats, return_inverse=True)
    Wu = np.zeros((W.shape[0], len(vals)))
    np.add.at(Wu.T, inv, W.T)
    return SmoothedRows(vals, np.cumsum(Wu, axis=1), alpha)


def smoothed_rows_per_row(S, W, alpha) -> SmoothedRows:
    """Conformal randomized rows when the calibration statistics differ per row: S, W (B, n)."""
    S = np.asarray(S, float)
    W = np.broadcast_to(np.asarray(W, float), S.shape)
    o = np.argsort(S, axis=1, kind="stable")
    Vs = np.take_along_axis(S, o, 1)
    Ws = np.take_along_axis(W, o, 1)
    return SmoothedRows(Vs, np.cumsum(Ws, axis=1), alpha, per_row=True)


def row_thresholds(stats, W, alpha: float, method: str = "randomized") -> RowThresholds:
    """Per-replicate thresholds from weighted calibration statistics under any rule. stats: (n,) shared or
    (B, n) per row; W: (B, n) nonnegative multiplicities. method as in `calibrate` (method="randomized"
    follows the active convention)."""
    method = resolve_method(method)
    S = np.asarray(stats, float)
    W = np.atleast_2d(np.asarray(W, float))
    if method == "conformal_randomized":
        return smoothed_rows_shared(S, W, alpha) if S.ndim == 1 else smoothed_rows_per_row(S, W, alpha)
    if S.ndim == 1:
        order = np.argsort(S, kind="stable")
        from .matched import _boot_threshold  # local import: matched imports this module
        h, g = _boot_threshold(S[order], W[:, order], alpha,
                              "conformal" if method == "conformal" else "randomized_plugin")
        return PluginRows(h, g)
    if method == "conformal":
        raise NotImplementedError("per-row conformal (deterministic) thresholds")
    hs, gs = [], []
    for b in range(S.shape[0]):
        t = randomized_threshold_plugin(np.repeat(S[b], W[b].astype(int)), alpha)
        hs.append(t.h); gs.append(t.gamma)
    return PluginRows(hs, gs)
