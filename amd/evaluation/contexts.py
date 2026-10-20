"""Per-context threshold allocation under one global audit budget (track 2).

Inputs are generic: dicts context -> 1-D array of honest (and attack) trajectory statistics
from any detector. Notation: w_c = share of honest traffic in context c (default: honest
sample share), so the global audit budget used is sum_c w_c FPR_c; a_c = attack prior over
contexts for a non-strategic attacker (default uniform).

Rules:
  global_threshold             one pooled threshold (traffic-weighted honest quantile)
  cfar_thresholds              constant FPR per context (per-context conformal quantile)
  partially_pooled_thresholds  per-context quantile of the shrunk CDF
                               (n_c F_c + n0 F_global)/(n_c + n0), FPR level tuned so the
                               realized calibration budget matches
  max_detection_allocation     maximize sum_c a_c TPR_c subject to sum_c w_c FPR_c <= budget
                               (fractional knapsack over per-context ROC concave hulls; one
                               context gets a randomized threshold to use the budget exactly)
  stackelberg_thresholds       minimize the attacker's best payoff max_c s_c D_c (1 - TPR_c)
                               subject to the budget (attacker sees thresholds and picks the
                               context; Ghafouri et al.-style damage equalization)
  evaluate_thresholds          realized budget, per-context FPR/TPR, uniform-attacker TPR and
                               the attack-selection (Stackelberg) payoff on held-out data
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .calibration import Threshold, calibrate


def _norm(d: dict | None, keys, default: dict) -> dict:
    if d is None:
        d = default
    s = sum(d[k] for k in keys)
    return {k: d[k] / s for k in keys}


def _traffic(honest_by_ctx, weights):
    keys = list(honest_by_ctx)
    return keys, _norm(weights, keys, {k: len(honest_by_ctx[k]) for k in keys})


def _tail(sorted_vals: np.ndarray, h) -> np.ndarray:
    """Fraction of values strictly greater than h."""
    n = len(sorted_vals)
    return (n - np.searchsorted(sorted_vals, h, side="right")) / max(n, 1)


def context_curve(honest, attack=None) -> pd.DataFrame:
    """Candidate thresholds (alarm iff S > h) for one context with their FPR / TPR.
    Candidates: -inf (alarm everything) and every unique honest value."""
    hs = np.sort(np.asarray(honest, float))
    cand = np.concatenate([[-np.inf], np.unique(hs)])
    df = pd.DataFrame(dict(h=cand, fpr=_tail(hs, cand)))
    if attack is not None:
        df["tpr"] = _tail(np.sort(np.asarray(attack, float)), cand)
    return df


def global_threshold(honest_by_ctx: dict, budget: float, weights=None) -> dict:
    """Smallest pooled honest value h with sum_c w_c FPR_c(h) <= budget (plug-in)."""
    keys, w = _traffic(honest_by_ctx, weights)
    sv = {k: np.sort(np.asarray(honest_by_ctx[k], float)) for k in keys}
    cand = np.unique(np.concatenate(list(sv.values())))
    cost = sum(w[k] * _tail(sv[k], cand) for k in keys)
    ok = np.flatnonzero(cost <= budget + 1e-12)
    h = float(cand[ok[0]]) if len(ok) else np.inf
    return {k: Threshold(h=h, alpha=budget, method="global") for k in keys}


def cfar_thresholds(honest_by_ctx: dict, budget: float, method: str = "conformal") -> dict:
    """Constant FPR per context (Mondrian conformal quantile; h = +inf when the context has
    fewer than ~1/budget samples under the conformal rule)."""
    return {k: calibrate(v, budget, method) for k, v in honest_by_ctx.items()}


def partially_pooled_thresholds(honest_by_ctx: dict, budget: float, n0: float = 50.0,
                                weights=None, match_budget: bool = True) -> dict:
    keys, w = _traffic(honest_by_ctx, weights)
    sv = {k: np.sort(np.asarray(honest_by_ctx[k], float)) for k in keys}
    pooled = np.sort(np.concatenate(list(sv.values())))
    cand = np.unique(pooled)
    gtail = _tail(pooled, cand)
    mix = {k: (len(sv[k]) * _tail(sv[k], cand) + n0 * gtail) / (len(sv[k]) + n0) for k in keys}

    def at_level(f):
        out = {}
        for k in keys:
            ok = np.flatnonzero(mix[k] <= f + 1e-12)
            out[k] = float(cand[ok[0]]) if len(ok) else np.inf
        return out

    def used(hd):
        return sum(w[k] * float(_tail(sv[k], hd[k])) for k in keys)

    f = budget
    if match_budget:
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if used(at_level(mid)) <= budget + 1e-12:
                lo = mid
            else:
                hi = mid
        f = lo
    return {k: Threshold(h=h, alpha=f, method=f"pooled_n0={n0:g}") for k, h in at_level(f).items()}


def _upper_hull(fpr: np.ndarray, tpr: np.ndarray):
    """Indices of the upper concave hull of ROC points, sorted by FPR ascending."""
    order = np.lexsort((-tpr, fpr))
    hull: list[int] = []
    for i in order:
        if hull and fpr[i] == fpr[hull[-1]]:
            continue  # same FPR, lower or equal TPR
        while len(hull) >= 2:
            i1, i2 = hull[-2], hull[-1]
            cross = (fpr[i2] - fpr[i1]) * (tpr[i] - tpr[i1]) - (tpr[i2] - tpr[i1]) * (fpr[i] - fpr[i1])
            if cross >= 0:  # i2 is on or below the chord i1 -> i
                hull.pop()
            else:
                break
        if hull and tpr[i] <= tpr[hull[-1]]:
            continue  # dominated
        hull.append(i)
    return hull


def max_detection_allocation(honest_by_ctx: dict, attack_by_ctx: dict, budget: float,
                             weights=None, attack_weights=None) -> dict:
    keys, w = _traffic(honest_by_ctx, weights)
    a = _norm(attack_weights, keys, {k: 1.0 for k in keys})
    hulls, segs = {}, []
    for k in keys:
        cur = context_curve(honest_by_ctx[k], attack_by_ctx[k])
        idx = _upper_hull(cur.fpr.values, cur.tpr.values)
        hv = cur.iloc[idx].reset_index(drop=True)
        hulls[k] = hv
        for j in range(1, len(hv)):
            dc = w[k] * (hv.fpr[j] - hv.fpr[j - 1])
            dg = a[k] * (hv.tpr[j] - hv.tpr[j - 1])
            segs.append((dg / max(dc, 1e-300), k, j, dc))
    segs.sort(key=lambda s: -s[0])
    pos = {k: 0 for k in keys}  # hull vertex index currently chosen (0 = lowest FPR)
    left = budget - sum(w[k] * hulls[k].fpr[0] for k in keys)
    frac = {}
    for eff, k, j, dc in segs:
        if left <= 1e-15 or eff <= 0:
            break
        if j != pos[k] + 1:
            continue  # concave hull => segments of one context arrive in order
        if dc <= left:
            pos[k] = j
            left -= dc
        else:
            frac[k] = (j, left / dc)
            left = 0
            break
    out = {}
    for k in keys:
        hv = hulls[k]
        h_hi = float(hv.h[pos[k]])
        if k in frac:
            j, g = frac[k]
            out[k] = Threshold(h=h_hi, gamma=g, h_lo=float(hv.h[j]), alpha=budget, method="maxdet")
        else:
            out[k] = Threshold(h=h_hi, alpha=budget, method="maxdet")
    return out


def stackelberg_thresholds(honest_by_ctx: dict, attack_by_ctx: dict, budget: float, weights=None,
                           damage=None, success=None) -> dict:
    """Deterministic thresholds minimizing max_c s_c D_c (1 - TPR_c) within the budget."""
    keys, w = _traffic(honest_by_ctx, weights)
    D = damage or {k: 1.0 for k in keys}
    S = success or {k: 1.0 for k in keys}
    curves = {k: context_curve(honest_by_ctx[k], attack_by_ctx[k]) for k in keys}
    pay = {k: S[k] * D[k] * (1 - c.tpr.values) for k, c in curves.items()}
    vals = np.unique(np.concatenate(list(pay.values())))

    def plan(v):
        hd, cost = {}, 0.0
        for k in keys:
            c = curves[k]
            ok = np.flatnonzero(pay[k] <= v + 1e-12)  # candidates sorted by h ascending
            j = ok[-1]  # largest h (cheapest) meeting the payoff cap
            hd[k] = float(c.h.values[j])
            cost += w[k] * c.fpr.values[j]
        return hd, cost

    lo, hi = 0, len(vals) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if plan(vals[mid])[1] <= budget + 1e-12:
            hi = mid
        else:
            lo = mid + 1
    hd, _ = plan(vals[lo])
    return {k: Threshold(h=h, alpha=budget, method="stackelberg") for k, h in hd.items()}


def evaluate_thresholds(thresholds: dict, honest_by_ctx: dict, attack_by_ctx: dict | None = None,
                        weights=None, attack_weights=None, damage=None, success=None) -> dict:
    keys, w = _traffic(honest_by_ctx, weights)
    rows = []
    for k in keys:
        thr = thresholds[k]
        r = dict(context=k, w=w[k], n_honest=len(honest_by_ctx[k]), h=thr.h,
                 fpr=thr.rate(np.asarray(honest_by_ctx[k], float)))
        if attack_by_ctx is not None:
            r["tpr"] = thr.rate(np.asarray(attack_by_ctx[k], float))
        rows.append(r)
    df = pd.DataFrame(rows)
    out = dict(per_context=df, budget_used=float((df.w * df.fpr).sum()),
               fpr_spread=float(df.fpr.max() - df.fpr.min()))
    if attack_by_ctx is not None:
        a = _norm(attack_weights, keys, {k: 1.0 for k in keys})
        D = damage or {k: 1.0 for k in keys}
        S = success or {k: 1.0 for k in keys}
        df["attacker_payoff"] = [S[k] * D[k] * (1 - t) for k, t in zip(df.context, df.tpr)]
        j = int(df.attacker_payoff.idxmax())
        out.update(uniform_tpr=float(sum(a[k] * t for k, t in zip(df.context, df.tpr))),
                   attacker_context=df.context[j], attacker_payoff=float(df.attacker_payoff[j]),
                   selection_safety=float(1 - df.attacker_payoff[j]))
    return out
