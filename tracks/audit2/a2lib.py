"""Minimal independent helpers for the second-pass audit (no reuse of amd.evaluation / track code).

Estimand used throughout: TPR of a trajectory (or account) statistic at a matched FPR alpha, with the
threshold calibrated on a random half of honest units (split by group when groups are given) using a
randomized plug-in threshold (exact alpha on the calibration half), averaged over many random splits.
CIs: one joint cluster bootstrap per replicate (honest and attack units, by group), SHARED across splits and
terms; thresholds are recomputed on the resampled calibration half.
"""
from __future__ import annotations

import json

import numpy as np


def read_jsonl(p):
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def rand_threshold(cal, w, alpha):
    """Randomized threshold (h, g) on weighted calibration stats so that P(s>h)+g*P(s==h) = alpha."""
    cal = np.asarray(cal, float)
    w = np.asarray(w, float)
    keep = w > 0
    cal, w = cal[keep], w[keep]
    tot = w.sum()
    if tot <= 0:
        return np.inf, 0.0
    u, inv = np.unique(cal, return_inverse=True)       # ascending distinct values
    wu = np.bincount(inv, weights=w)[::-1]               # descending
    u = u[::-1]
    cum = np.cumsum(wu)                                  # weight at or above each value
    j = int(np.searchsorted(cum, alpha * tot - 1e-9))    # first value where cum >= alpha*tot
    j = min(j, len(u) - 1)
    above = cum[j] - wu[j]
    g = (alpha * tot - above) / wu[j]
    return float(u[j]), float(min(max(g, 0.0), 1.0))


def alarm(s, h, g):
    s = np.asarray(s, float)
    return (s > h) + g * (s == h)


def grouped_half(groups, rng):
    """Boolean calibration mask: a random half of the distinct groups."""
    ug = np.unique(groups)
    pick = rng.permutation(len(ug))[: len(ug) // 2]
    return np.isin(groups, ug[pick])


def cluster_counts(groups, rng):
    ug, inv = np.unique(groups, return_inverse=True)
    c = np.bincount(rng.integers(0, len(ug), len(ug)), minlength=len(ug))
    return c[inv].astype(float)


def matched_tpr_contrast(H, A, coefs, hg, ag, alpha, n_splits=200, B=1000, seed=0, amask=None,
                         return_fpr=False):
    """H, A: dict term -> per-unit statistic arrays (honest, attack; same unit order for every term).
    coefs: dict term -> coefficient. Returns (est, lo, hi, p_le0) [, realized test FPR per term]."""
    rng = np.random.default_rng(seed)
    hg, ag = np.asarray(hg), np.asarray(ag)
    amask = np.ones(len(ag), bool) if amask is None else np.asarray(amask, bool)
    masks = [grouped_half(hg, rng) for _ in range(n_splits)]
    Wh = np.array([cluster_counts(hg, rng) for _ in range(B)])
    Wa = np.array([cluster_counts(ag, rng) for _ in range(B)]) * amask[None, :]

    def value(wh, wa, want_fpr=False):
        tot, fprs = 0.0, {k: [] for k in coefs}
        for m in masks:
            for k, c in coefs.items():
                h, g = rand_threshold(H[k][m], wh[m], alpha)
                tot += c * (alarm(A[k], h, g) * wa).sum() / max(wa.sum(), 1e-12)
                if want_fpr:
                    fprs[k].append(alarm(H[k][~m], h, g).mean())
        return (tot / len(masks), {k: float(np.mean(v)) for k, v in fprs.items()}) if want_fpr else tot / len(masks)

    est, fpr = value(np.ones(len(hg)), amask.astype(float), True)
    bs = np.array([value(Wh[b], Wa[b]) for b in range(B)])
    out = (float(est), float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975)), float((bs <= 0).mean()))
    return (out, fpr) if return_fpr else out
