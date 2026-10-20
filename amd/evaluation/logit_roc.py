"""Logit-ROC extrapolation (Redwood): for a fixed monitor / policy / attack, logit(TPR) is
close to linear in logit(FPR). Fit the line on the part of the empirical ROC that has enough
honest alarms, then extrapolate to FPRs below 1 / n_honest.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.special import expit, logit


def empirical_roc(honest_stats, attack_stats):
    """(FPR, TPR, thresholds) at every unique honest value h, alarm iff S >= h."""
    h = np.sort(np.asarray(honest_stats, float))
    a = np.sort(np.asarray(attack_stats, float))
    thr = np.unique(h)[::-1]
    fpr = (len(h) - np.searchsorted(h, thr, side="left")) / len(h)
    tpr = (len(a) - np.searchsorted(a, thr, side="left")) / len(a)
    return fpr, tpr, thr


@dataclass
class LogitROCFit:
    intercept: float
    slope: float
    r2: float
    rmse: float
    curvature: float          # quadratic coefficient of a degree-2 fit (0 = linear)
    n_points: int
    fpr_min: float
    fpr_max: float
    n_honest: int
    n_attack: int
    points: dict = field(default_factory=dict)

    def predict(self, fpr):
        return expit(self.intercept + self.slope * logit(np.asarray(fpr, float)))

    def diagnostics(self) -> dict:
        return dict(slope=self.slope, intercept=self.intercept, r2=self.r2, rmse=self.rmse,
                    curvature=self.curvature, n_points=self.n_points, fit_fpr_min=self.fpr_min,
                    fit_fpr_max=self.fpr_max, n_honest=self.n_honest, n_attack=self.n_attack)


def logit_roc_fit(honest_stats, attack_stats, min_honest_alarms: int = 5, fpr_max: float = 0.2,
                  weighted: bool = True) -> LogitROCFit:
    """Weighted least squares of logit(TPR) on logit(FPR) over ROC points with
    FPR in [min_honest_alarms / n_honest, fpr_max]. TPR is clipped to [0.5/n_a, 1 - 0.5/n_a];
    weights are the inverse of the binomial variance of logit(TPR) plus that of logit(FPR)
    (1/(n_a t(1-t)) + 1/(n_h f(1-f)); errors in both coordinates, slope ~ 1)."""
    nh, na = len(honest_stats), len(attack_stats)
    fpr, tpr, thr = empirical_roc(honest_stats, attack_stats)
    lo = min_honest_alarms / nh
    sel = (fpr >= lo) & (fpr <= fpr_max) & (fpr < 1)
    if sel.sum() < 3:
        raise ValueError("fewer than 3 ROC points in the fit range")
    f, t = fpr[sel], np.clip(tpr[sel], 0.5 / na, 1 - 0.5 / na)
    x, y = logit(f), logit(t)
    w = 1.0 / (1.0 / (na * t * (1 - t)) + 1.0 / (nh * f * (1 - f))) if weighted else np.ones_like(t)
    Xd = np.stack([np.ones_like(x), x], axis=1)
    sw = np.sqrt(w)
    beta, *_ = np.linalg.lstsq(Xd * sw[:, None], y * sw, rcond=None)
    pred = Xd @ beta
    res = y - pred
    ybar = np.average(y, weights=w)
    r2 = 1 - np.sum(w * res**2) / max(np.sum(w * (y - ybar) ** 2), 1e-300)
    curv = np.polyfit(x, y, 2, w=sw)[0] if len(x) >= 4 else np.nan
    return LogitROCFit(intercept=float(beta[0]), slope=float(beta[1]), r2=float(r2),
                       rmse=float(np.sqrt(np.average(res**2, weights=w))), curvature=float(curv),
                       n_points=int(sel.sum()), fpr_min=float(f.min()), fpr_max=float(f.max()),
                       n_honest=nh, n_attack=na, points=dict(fpr=f, tpr=t))


def logit_roc_extrapolate(honest_stats, attack_stats, target_fprs=(1e-3, 1e-4), n_boot: int = 300,
                          ci: float = 0.95, seed: int = 0, **fit_kw) -> pd.DataFrame:
    """Extrapolated TPR at target FPRs with a trajectory-bootstrap CI and fit diagnostics.
    `extrapolation_factor` = smallest fitted FPR / target (how far beyond the data)."""
    rng = np.random.default_rng(seed)
    h, a = np.asarray(honest_stats, float), np.asarray(attack_stats, float)
    fit = logit_roc_fit(h, a, **fit_kw)
    boots = []
    for _ in range(n_boot):
        try:
            fb = logit_roc_fit(rng.choice(h, len(h)), rng.choice(a, len(a)), **fit_kw)
            boots.append(fb.predict(target_fprs))
        except ValueError:
            continue
    boots = np.array(boots) if boots else np.full((1, len(target_fprs)), np.nan)
    q = (1 - ci) / 2
    rows = []
    for j, f in enumerate(target_fprs):
        rows.append(dict(target_fpr=f, tpr_hat=float(fit.predict(f)),
                         tpr_lo=float(np.nanquantile(boots[:, j], q)),
                         tpr_hi=float(np.nanquantile(boots[:, j], 1 - q)),
                         extrapolation_factor=fit.fpr_min / f, **fit.diagnostics()))
    return pd.DataFrame(rows)
