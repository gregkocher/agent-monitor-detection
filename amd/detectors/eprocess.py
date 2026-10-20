"""Conformal test martingales / e-processes and the Shiryaev-Roberts e-detector.

Each unit's score s_t is mapped to a conformal p-value p_t against honest calibration units
(conservative by default; randomized optional), and then to an e-value e_t = f(p_t) with a
calibrator f that satisfies int_0^1 f(u) du = 1 and is non-increasing (so E[f(p)] <= 1 for any
super-uniform p):

  power   f_k(p) = k p^(k-1),             mixture over a grid of k (average of products)
  powerint f(p) = int_0^1 k p^(k-1) dk = (1 - p + p ln p) / (p ln^2 p)   (per-unit mixture)
  linear  f_l(p) = 1 + l (1 - 2p),         mixture over a grid of l in (0, 1)
  jumper  Vovk's composite jumper on f_eps(p) = 1 + eps (p - 1/2), eps in {-1, 0, 1}

E-process: E_t = mean_l prod_{i<=t} f_l(p_i). Under the null (honest units i.i.d. and
exchangeable with the calibration units, so the p-values are i.i.d. super-uniform given the
calibration set up to its O(1/sqrt(n)) training-conditional fluctuation) E_t is a test
(super)martingale and Ville's inequality gives P(sup_t E_t >= 1/alpha) <= alpha: the alarm
threshold log(1/alpha) is anytime-valid for any trajectory length and any stopping rule.
It is NOT valid under within-stream dependence of honest scores (e.g. history-aware monitors);
use an empirically calibrated threshold then.

E-detector (SR): M_t = sum_{j<=t} prod_{i=j..t} e_i = e_t (1 + M_{t-1}), mixed over l.
Alarm at M_t >= 1/alpha gives ARL0 >= 1/alpha (not a per-trajectory type-I bound).

Statistics are reported on the log scale.
"""
from __future__ import annotations

import numpy as np
from scipy.special import logsumexp

from .base import Detector, Packed
from .transforms import PValue

_DEFAULT_GRIDS = {
    "power": np.array([0.02, 0.05, 0.1, 0.2, 0.35, 0.5]),
    "linear": np.array([0.1, 0.25, 0.5, 0.75, 0.9]),
}


def log_evalues(p: np.ndarray, calibrator: str, lam: float | None = None) -> np.ndarray:
    """log f(p) for one calibrator / parameter."""
    p = np.clip(p, 1e-300, 1.0)
    if calibrator == "power":
        return np.log(lam) + (lam - 1.0) * np.log(p)
    if calibrator == "linear":
        return np.log1p(lam * (1.0 - 2.0 * p))
    if calibrator == "powerint":
        lp = np.log(p)
        with np.errstate(divide="ignore", invalid="ignore"):
            e = (1.0 - p + p * lp) / (p * lp**2)
        e = np.where(p >= 1.0 - 1e-12, 0.5, e)
        return np.log(e)
    raise ValueError(calibrator)


class ConformalEProcess(Detector):
    """Conformal test martingale (mixture e-process). Statistic = sup_t log E_t."""

    empty_value = 0.0

    def __init__(self, calibrator: str = "power", lambdas=None, randomize: bool = False,
                 mondrian: bool = False, min_n: int = 30, n0: float = 0.0, jump: float = 0.01,
                 seed: int | None = None):
        super().__init__(PValue("randomized" if randomize else "conservative", mondrian=mondrian,
                                min_n=min_n, n0=n0, seed=seed))
        assert calibrator in ("power", "linear", "powerint", "jumper")
        self.calibrator = calibrator
        self.lambdas = (np.asarray(lambdas, float) if lambdas is not None
                        else _DEFAULT_GRIDS.get(calibrator, np.array([np.nan])))
        self.jump = jump
        self.name = f"eproc_{calibrator}" + ("_rand" if randomize else "")

    def analytic_threshold(self, alpha: float) -> float:
        """Ville threshold log(1/alpha): anytime-valid FPR <= alpha under i.i.d. honest units."""
        return float(np.log(1.0 / alpha))

    def _agg(self, P_, lengths):
        p = P_
        if self.calibrator == "jumper":
            return self._jumper(p)
        if self.calibrator == "powerint":
            return np.cumsum(log_evalues(p, "powerint"), axis=1)
        acc = None
        for lam in self.lambdas:
            path = np.cumsum(log_evalues(p, self.calibrator, lam), axis=1)
            acc = path if acc is None else np.logaddexp(acc, path)
        return acc - np.log(len(self.lambdas))

    def _jumper(self, p):
        n, T = p.shape
        eps = np.array([-1.0, 0.0, 1.0])
        C = np.full((n, 3), 1.0 / 3.0)
        logW = np.zeros(n)
        out = np.empty((n, T))
        J = self.jump
        for t in range(T):
            C = (1 - J) * C + J / 3.0  # rows of C sum to 1
            m = C * (1.0 + eps[None, :] * (p[:, t:t + 1] - 0.5))
            s = m.sum(axis=1)
            logW += np.log(s)
            C = m / s[:, None]
            out[:, t] = logW
        return out

    def increments_packed(self, P: Packed):
        p = self.transform.apply(P)
        if self.calibrator in ("powerint", "jumper"):
            return log_evalues(p, "powerint")
        lam = self.lambdas[len(self.lambdas) // 2]
        return log_evalues(p, self.calibrator, lam)


class EDetectorSR(ConformalEProcess):
    """Shiryaev-Roberts e-detector: log of mean_l M_t(l), M_t = e_t (1 + M_{t-1}).
    `analytic_threshold(alpha)` = log(1/alpha) controls ARL0 >= 1/alpha (anytime ARL), not FPR."""

    def __init__(self, calibrator: str = "power", **kw):
        assert calibrator in ("power", "linear", "powerint")
        super().__init__(calibrator=calibrator, **kw)
        self.name = f"esr_{calibrator}"

    def _agg(self, p, lengths):
        n, T = p.shape
        lams = [None] if self.calibrator == "powerint" else list(self.lambdas)
        logs = []
        for lam in lams:
            le = log_evalues(p, self.calibrator, lam)
            out = np.empty((n, T))
            logM = np.full(n, -np.inf)
            for t in range(T):
                logM = le[:, t] + np.logaddexp(0.0, logM)
                out[:, t] = logM
            logs.append(out)
        return logsumexp(np.stack(logs), axis=0) - np.log(len(lams))
