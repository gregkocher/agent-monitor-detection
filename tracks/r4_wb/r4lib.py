"""Shared helpers for the round-4 white-box analyses.

matched_raw()  -- one matched_budget_eval run (detector `max`, randomized thresholds, grouped splits) returning
                  the per-split raw statistics; identical honest universe / groups / seed => identical splits
                  across monitors, which amd.evaluation.paired checks.
contrast()     -- amd.evaluation.paired.paired_contrast_bootstrap with a two-sided p.
contrast_alpha() -- the same paired bootstrap but with a separate nominal level per term (equal realized FPR).
realized_fpr() -- split-mean alarm rate on the held-out honest half (and optional extra honest sets).
"""
from __future__ import annotations

import numpy as np

from amd.detectors import Max
from amd.evaluation import calibrate, matched_budget_eval, paired_contrast_bootstrap
from amd.evaluation.matched import _boot_threshold, bootstrap_weights


def matched_raw(honest, attack, hg, ag, alphas=(0.01, 0.05), n_splits=200, seed=0):
    _, raw = matched_budget_eval({"max": Max()}, honest, attack, alphas=alphas, honest_groups=hg,
                                 attack_groups=ag, group_split=True, n_splits=n_splits, cal_frac=0.5,
                                 n_boot=2, cluster_bootstrap=True, method="randomized", seed=seed,
                                 return_raw=True)
    return raw


def tpr(raw, alpha, mask=None):
    v = []
    for r in raw:
        a = np.asarray(r["attack"], float)
        if mask is not None:
            a = a[np.asarray(mask)[r["attack_idx"]]]
        v.append(calibrate(r["cal"], alpha, "randomized").alarm_prob(a).mean())
    return float(np.mean(v))


def realized_fpr(raw, alpha, extra=None):
    f, fx = [], []
    for r in raw:
        th = calibrate(r["cal"], alpha, "randomized")
        f.append(th.alarm_prob(np.asarray(r["test"], float)).mean())
        if extra is not None:
            fx.append(th.alarm_prob(np.asarray(extra, float)).mean())
    return float(np.mean(f)) if extra is None else (float(np.mean(f)), float(np.mean(fx)))


def two_sided(res):
    res["p_two"] = float(min(1.0, 2 * min(res["p_le0"], res["p_ge0"])))
    return res


def contrast(terms, n_h, n_a, alpha, hg, ag, mask=None, B=2000, seed=0):
    return two_sided(paired_contrast_bootstrap(terms, n_honest=n_h, n_attack=n_a, alpha=alpha, honest_groups=hg,
                                               attack_groups=ag, attack_mask=mask, method="randomized",
                                               n_boot=B, seed=seed, calibration_noise=True))


def contrast_alpha(terms, n_h, n_a, hg, ag, B=2000, seed=0):
    """terms: list of (coef, raw, alpha). Same resampling scheme as paired_contrast_bootstrap."""
    rng = np.random.default_rng(seed)
    Wh = bootstrap_weights(n_h, B, rng, np.asarray(hg))
    Wa = bootstrap_weights(n_a, B, rng, np.asarray(ag))
    splits = sorted({r["split"] for r in terms[0][1]})
    est, boot = [], []
    for sp in splits:
        recs = [next(r for r in raw if r["split"] == sp) for _, raw, _ in terms]
        aidx = recs[0]["attack_idx"]
        wa = Wa[:, aidx]
        den = np.maximum(wa.sum(axis=1), 1e-12)
        pt, bt = 0.0, np.zeros(B)
        for (coef, _, al), r in zip(terms, recs):
            assert np.array_equal(r["cal_idx"], recs[0]["cal_idx"])
            s = np.asarray(r["attack"], float)
            pt += coef * calibrate(r["cal"], al, "randomized").alarm_prob(s).mean()
            cal = np.asarray(r["cal"], float)
            order = np.argsort(cal, kind="stable")
            h, g = _boot_threshold(cal[order], Wh[:, np.asarray(r["cal_idx"])][:, order], al, "randomized")
            A = (s[None, :] > h[:, None]) + g[:, None] * (s[None, :] == h[:, None])
            bt += coef * (A * wa).sum(axis=1) / den
        est.append(pt)
        boot.append(bt)
    b = np.mean(boot, axis=0)
    return two_sided(dict(est=float(np.mean(est)), lo=float(np.quantile(b, 0.025)), hi=float(np.quantile(b, 0.975)),
                          se=float(np.std(b, ddof=1)), p_le0=float((b <= 0).mean()), p_ge0=float((b >= 0).mean()),
                          n_splits=len(est), n_boot=B))


def equalize_level(raw, target_fpr, hi=0.01, iters=30):
    """Largest nominal level whose split-mean realized FPR does not exceed target_fpr (bisection)."""
    lo = 1e-5
    for _ in range(iters):
        mid = (lo + hi) / 2
        if realized_fpr(raw, mid) <= target_fpr:
            lo = mid
        else:
            hi = mid
    return lo


def holm(ps):
    ps = np.asarray(ps, float)
    order = np.argsort(ps)
    m = len(ps)
    adj = np.empty(m)
    run = 0.0
    for i, j in enumerate(order):
        run = max(run, (m - i) * ps[j])
        adj[j] = min(1.0, run)
    return adj


def percontext(h_stat, a_stat, h_task, h_ctx, a_ctx, alpha, n_splits=200, seed=0):
    """Per-context (Mondrian) calibration of trajectory statistics vs one global threshold, on the same random
    50/50 honest splits grouped by task. Returns dict with realized test FPR (overall and per context) and TPR
    for both schemes. Contexts with no calibration trajectory in a split never alarm in that split."""
    from amd.evaluation.matched import _split
    rng = np.random.default_rng(seed)
    h_stat, a_stat = np.asarray(h_stat, float), np.asarray(a_stat, float)
    h_ctx, a_ctx = np.asarray(h_ctx), np.asarray(a_ctx)
    ctxs = sorted(set(h_ctx))
    acc = {k: [] for k in ("g_fpr", "g_tpr", "c_fpr", "c_tpr")}
    per = {c: {"g": [], "c": []} for c in ctxs}
    for _ in range(n_splits):
        ci, ti = _split(len(h_stat), 0.5, rng, np.asarray(h_task))
        thg = calibrate(h_stat[ci], alpha, "randomized")
        acc["g_fpr"].append(thg.alarm_prob(h_stat[ti]).mean())
        acc["g_tpr"].append(thg.alarm_prob(a_stat).mean())
        ft, fa = np.zeros(len(ti)), np.zeros(len(a_stat))
        for c in ctxs:
            cc = ci[h_ctx[ci] == c]
            mt, ma = h_ctx[ti] == c, a_ctx == c
            if len(cc) == 0:
                continue
            th = calibrate(h_stat[cc], alpha, "randomized")
            ft[mt] = th.alarm_prob(h_stat[ti][mt])
            fa[ma] = th.alarm_prob(a_stat[ma])
            if mt.any():
                per[c]["c"].append(ft[mt].mean())
                per[c]["g"].append(thg.alarm_prob(h_stat[ti][mt]).mean())
        acc["c_fpr"].append(ft.mean())
        acc["c_tpr"].append(fa.mean())
    out = {k: float(np.mean(v)) for k, v in acc.items()}
    out["ctx_fpr_global"] = {c: float(np.mean(v["g"])) if v["g"] else np.nan for c, v in per.items()}
    out["ctx_fpr_percontext"] = {c: float(np.mean(v["c"])) if v["c"] else np.nan for c, v in per.items()}
    return out
