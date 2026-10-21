"""Minimal, independent re-implementation of the pieces needed to re-check headline numbers.

Deliberately does NOT import amd.evaluation / amd.detectors / track libraries.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import norm

REPO = Path(__file__).resolve().parents[2]
P = REPO / "data" / "processed"
OUT = REPO / "results" / "audit"


def jl(path):
    with open(path) as f:
        for line in f:
            yield json.loads(line)


def arr(v):
    return np.array([np.nan if x is None else float(x) for x in v], float)


# ---------------- thresholds -----------------------------------------------------------------

def rand_threshold(cal, alpha, w=None):
    """Plug-in randomized threshold on (optionally weighted) calibration statistics:
    smallest observed h with share{S > h} <= alpha; ties at h alarm with prob gamma so that the
    calibration alarm share is exactly alpha. Returns (h, gamma)."""
    cal = np.asarray(cal, float)
    w = np.ones_like(cal) if w is None else np.asarray(w, float)
    vals = np.unique(cal)
    tot = w.sum()
    # weight strictly above each unique value
    order = np.argsort(cal)
    cs, cw = cal[order], w[order]
    cum = np.cumsum(cw)
    idx_last = np.searchsorted(cs, vals, side="right") - 1
    above = tot - cum[idx_last]
    ok = np.flatnonzero(above <= alpha * tot + 1e-12)
    j = ok[0]
    h = vals[j]
    at_h = w[cal == h].sum()
    gamma = float(np.clip((alpha * tot - above[j]) / max(at_h, 1e-300), 0, 1))
    return h, gamma


def alarm_prob(stats, h, gamma):
    s = np.asarray(stats, float)
    return (s > h).astype(float) + gamma * (s == h)


# ---------------- per-unit whitening (mid-p probit) -----------------------------------------

class MidPWhiten:
    def __init__(self, units):
        u = np.asarray(units, float)
        self.u = np.sort(u[np.isfinite(u)])
        self.n = len(self.u)

    def __call__(self, s):
        s = np.asarray(s, float)
        gt = self.n - np.searchsorted(self.u, s, side="right")
        eq = np.searchsorted(self.u, s, side="right") - np.searchsorted(self.u, s, side="left")
        p = (gt + (eq + 1) / 2) / (self.n + 1)
        z = norm.ppf(1 - p)
        z[~np.isfinite(s)] = np.nan
        return z


def topk_sum(z, k=3, fill=0.0):
    z = z[np.isfinite(z)]
    top = np.sort(z)[::-1][:k]
    if len(top) < k:
        top = np.r_[top, np.full(k - len(top), fill)]
    return float(top.sum())


def stat_max(s):
    s = s[np.isfinite(s)]
    return float(s.max()) if len(s) else np.nan


def group_split(groups, rng, frac=0.5):
    g = np.asarray(groups)
    ug = rng.permutation(np.unique(g))
    m = int(round(frac * len(ug)))
    sel = np.isin(g, ug[:m])
    return np.flatnonzero(sel), np.flatnonzero(~sel)


def cluster_weights(groups, rng):
    g = np.asarray(groups)
    ug, inv = np.unique(g, return_inverse=True)
    wg = rng.multinomial(len(ug), np.full(len(ug), 1 / len(ug))).astype(float)
    return wg[inv]
