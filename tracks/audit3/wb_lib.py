"""Audit pass 3 (r4_wb): independent, vectorized matched-FPR helpers (no amd.evaluation, no track code).

Estimand: TPR of a per-unit statistic at nominal FPR alpha, threshold = randomized plug-in on a random half of
the honest units (half of the distinct honest groups), averaged over many random splits.
Bootstrap: one cluster resample per replicate, shared across splits and terms; thresholds are recomputed from
the resampled calibration half (calibration noise). Two schemes:
  'indep' -- honest clusters and attack clusters resampled independently (what amd.evaluation.paired does);
  'joint' -- ONE resample over the union of cluster labels; honest and attack units of the same task share the
             multiplicity (accounts for honest/attack task overlap).
"""
from __future__ import annotations

import json

import numpy as np


def read_jsonl(p):
    with open(p) as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def wthresh(cal, W, alpha):
    """Vectorized weighted randomized threshold. cal (n,), W (B, n) nonneg weights.
    Returns h (B,), g (B,) with sum_w[s>h] + g * sum_w[s==h] = alpha * sum_w."""
    cal = np.asarray(cal, float)
    u, inv = np.unique(cal, return_inverse=True)
    u = u[::-1]
    inv = len(u) - 1 - inv
    W = np.atleast_2d(W)
    Wu = np.zeros((W.shape[0], len(u)))
    np.add.at(Wu.T, inv, W.T)
    tot = Wu.sum(1)
    cum = np.cumsum(Wu, 1)                       # weight at or above u[j]
    tgt = alpha * tot
    j = (cum < tgt[:, None] - 1e-9).sum(1)       # first j with cum >= tgt
    j = np.minimum(j, len(u) - 1)
    r = np.arange(W.shape[0])
    above = cum[r, j] - Wu[r, j]
    g = np.clip((tgt - above) / np.maximum(Wu[r, j], 1e-12), 0, 1)
    return u[j], g


def alarm_rate(s, h, g, W=None):
    """Weighted alarm rate per replicate. s (n,), h,g (B,), W (B,n) or None."""
    s = np.asarray(s, float)
    A = (s[None, :] > h[:, None]) + g[:, None] * (s[None, :] == h[:, None])
    if W is None:
        return A.mean(1)
    return (A * W).sum(1) / np.maximum(W.sum(1), 1e-12)


def halves(hg, n_splits, rng):
    ug = np.unique(hg)
    out = []
    for _ in range(n_splits):
        pick = rng.permutation(len(ug))[: int(round(len(ug) / 2))]
        out.append(np.isin(hg, ug[pick]))
    return out


def boot_weights(hg, ag, B, rng, scheme):
    hg, ag = np.asarray(hg), np.asarray(ag)
    if scheme == "indep":
        uh, ih = np.unique(hg, return_inverse=True)
        ua, ia = np.unique(ag, return_inverse=True)
        Ch = rng.multinomial(len(uh), np.full(len(uh), 1 / len(uh)), size=B).astype(float)
        Ca = rng.multinomial(len(ua), np.full(len(ua), 1 / len(ua)), size=B).astype(float)
        return Ch[:, ih], Ca[:, ia]
    if scheme == "joint":
        u, inv = np.unique(np.r_[hg, ag], return_inverse=True)
        C = rng.multinomial(len(u), np.full(len(u), 1 / len(u)), size=B).astype(float)
        return C[:, inv[: len(hg)]], C[:, inv[len(hg):]]
    if scheme == "iid":
        nh, na = len(hg), len(ag)
        return (rng.multinomial(nh, np.full(nh, 1 / nh), size=B).astype(float),
                rng.multinomial(na, np.full(na, 1 / na), size=B).astype(float))
    raise ValueError(scheme)


def contrast(H, A, terms, masks, alpha, Wh=None, Wa=None, amask=None, Xh=None):
    """terms: list of (coef, key[, alpha_override]). H/A: dict key -> per-unit statistic.
    Returns point (scalar) and, if Wh given, bootstrap replicate array; also split-mean realized FPR per key and
    split-level contrast values."""
    na = len(next(iter(A.values())))
    amask = np.ones(na, bool) if amask is None else np.asarray(amask, bool)
    pt, sp_vals, fpr, fprx = 0.0, np.zeros(len(masks)), {}, {}
    bt = None if Wh is None else np.zeros(Wh.shape[0])
    for t in terms:
        c, k = t[0], t[1]
        al = t[2] if len(t) > 2 else alpha
        hs, as_ = np.asarray(H[k], float), np.asarray(A[k], float)[amask]
        f, fx = [], []
        for i, m in enumerate(masks):
            h, g = wthresh(hs[m], np.ones((1, m.sum())), al)
            v = alarm_rate(as_, h, g)[0]
            sp_vals[i] += c * v
            f.append(alarm_rate(hs[~m], h, g)[0])
            if Xh is not None:
                fx.append(alarm_rate(np.asarray(Xh[k], float), h, g)[0])
            if Wh is not None:
                hb, gb = wthresh(hs[m], Wh[:, m], al)
                bt += c * alarm_rate(as_, hb, gb, Wa[:, amask])
        fpr[(k, al)] = float(np.mean(f))
        if Xh is not None:
            fprx[(k, al)] = float(np.mean(fx))
    pt = float(sp_vals.mean())
    out = dict(est=pt, split_sd=float(sp_vals.std(ddof=1)), fpr=fpr, fprx=fprx)
    if Wh is not None:
        bt = bt / len(masks)
        out.update(lo=float(np.quantile(bt, .025)), hi=float(np.quantile(bt, .975)),
                   p_two=float(min(1, 2 * min((bt <= 0).mean(), (bt >= 0).mean()))), se=float(bt.std(ddof=1)))
        out["boot"] = bt
    return out


def realized_fpr(hs, masks, alpha, extra=None):
    hs = np.asarray(hs, float)
    f, fx = [], []
    for m in masks:
        h, g = wthresh(hs[m], np.ones((1, m.sum())), alpha)
        f.append(alarm_rate(hs[~m], h, g)[0])
        if extra is not None:
            fx.append(alarm_rate(extra, h, g)[0])
    return (float(np.mean(f)), float(np.mean(fx))) if extra is not None else float(np.mean(f))


def equal_level(hs, masks, target, hi=0.05, iters=40):
    """Largest nominal level whose split-mean realized FPR <= target (bisection). Returns (level, achieved)."""
    lo = 1e-6
    if realized_fpr(hs, masks, lo) > target:
        return lo, realized_fpr(hs, masks, lo)
    for _ in range(iters):
        mid = (lo + hi) / 2
        if realized_fpr(hs, masks, mid) <= target:
            lo = mid
        else:
            hi = mid
    return lo, realized_fpr(hs, masks, lo)


def holm(ps):
    ps = np.asarray(ps, float)
    o = np.argsort(ps)
    adj = np.empty(len(ps))
    run = 0.0
    for i, j in enumerate(o):
        run = max(run, (len(ps) - i) * ps[j])
        adj[j] = min(1.0, run)
    return adj


def clopper_pearson(k, n, a=0.05):
    from scipy.stats import beta
    lo = 0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k)
    return float(lo), float(hi)
