"""Order-statistic and counting aggregators: max, mean, k-th largest, top-k sum, k strikes,
and the length-aware max (analytic per-trajectory null)."""
from __future__ import annotations

import numpy as np

from .base import Detector, Packed, Transform
from .transforms import UnitCalibrator


class Max(Detector):
    """S_t = max_{i<=t} u_i (the standard rule)."""

    name = "max"

    def _agg(self, U, lengths):
        return np.maximum.accumulate(U, axis=1)


class Mean(Detector):
    """S_t = mean_{i<=t} u_i. Final value (not an alarm-type statistic)."""

    name = "mean"
    alarm_type = False

    def _agg(self, U, lengths):
        return np.cumsum(U, axis=1) / np.arange(1, U.shape[1] + 1)[None, :]


class KthLargest(Detector):
    """S_t = k-th largest of u_1..u_t (-inf until k units). k=2 is Kutasov's 2nd-highest rule."""

    def __init__(self, k: int = 2, transform: Transform | None = None):
        super().__init__(transform)
        self.k = k
        self.name = f"kth{k}"

    def _agg(self, U, lengths):
        n, T = U.shape
        buf = np.full((n, self.k), -np.inf)  # ascending; buf[:, 0] = k-th largest
        out = np.empty((n, T))
        for t in range(T):
            x = U[:, t]
            repl = x > buf[:, 0]
            buf[repl, 0] = x[repl]
            buf.sort(axis=1)
            out[:, t] = buf[:, 0]
        return out


class TopKSum(Detector):
    """S_t = sum of the k largest of u_1..u_t; while t < k, missing slots count as `fill`."""

    def __init__(self, k: int = 3, fill: float = 0.0, transform: Transform | None = None):
        super().__init__(transform)
        self.k = k
        self.fill = fill
        self.name = f"top{k}sum"

    def _agg(self, U, lengths):
        n, T = U.shape
        buf = np.full((n, self.k), -np.inf)
        out = np.empty((n, T))
        for t in range(T):
            x = U[:, t]
            repl = x > buf[:, 0]
            buf[repl, 0] = x[repl]
            buf.sort(axis=1)
            filled = np.isfinite(buf)
            out[:, t] = np.where(filled, buf, self.fill).sum(axis=1)
        return out


class CountAbove(Detector):
    """'k strikes': S_t = #{i <= t: u_i > q-quantile of honest units}. Integer-valued; use
    randomized thresholds or report realized FPR."""

    def __init__(self, q: float = 0.95, transform: Transform | None = None):
        super().__init__(transform)
        self.q = q
        self.name = f"count>q{q:g}"

    def _fit_agg(self, U, P):
        self.u_ = float(np.quantile(U[P.mask], self.q))

    def _agg(self, U, lengths):
        return np.cumsum(U > self.u_, axis=1).astype(float)


class LengthAwareMax(Detector):
    """Max with an analytic, length-aware per-trajectory null.

    F = honest per-unit CDF (mid-p empirical). Model: P_honest(max of L units <= m) =
    F(m)^{L_eff(L)}, L_eff = theta * L^beta (beta = 1 for model='linear'). theta, beta are fit
    by maximum likelihood on the maxima of honest calibration streams (theta < 1 / beta < 1
    capture positive within-stream dependence). Statistic (final value, not alarm-type):
        S = -log(1 - F(max)^{L_eff(L)})   = -log(per-trajectory tail probability)
    so `analytic_threshold(alpha) = -log(alpha)` gives per-trajectory FPR ~ alpha at every
    length, provided the model fits. Resolution is limited to p >= ~0.5/(n_units + 1).
    """

    name = "max_lenaware"
    alarm_type = False

    def __init__(self, model: str = "power", betas=None):
        super().__init__(None)
        assert model in ("linear", "power")
        self.model = model
        self.betas = np.linspace(0.1, 1.0, 46) if betas is None else np.asarray(betas)
        self.cal = UnitCalibrator()

    def _logF(self, X):
        return np.log1p(-self.cal.pvalues(X, "mid"))

    def _fit_agg(self, U, P):
        self.cal.fit(P.units())
        ok = P.lengths > 0
        logF = np.where(P.mask, self._logF(P.X), -np.inf)
        lFmax = logF.max(axis=1)[ok]
        L = P.lengths[ok].astype(float)
        best = (-np.inf, 1.0, 1.0)
        betas = [1.0] if self.model == "linear" else self.betas
        for b in betas:
            a = L**b
            theta = len(L) / np.sum(-a * lFmax)
            ll = np.sum(np.log(theta * a) + (theta * a - 1) * lFmax)
            if ll > best[0]:
                best = (ll, theta, b)
        _, self.theta_, self.beta_ = best

    def _agg(self, U, lengths):
        lF = np.maximum.accumulate(self._logF(U), axis=1)
        t = np.arange(1, U.shape[1] + 1)[None, :]
        Leff = self.theta_ * t**self.beta_
        tail = -np.expm1(Leff * lF)
        return -np.log(np.clip(tail, 1e-300, 1.0))

    def analytic_threshold(self, alpha: float) -> float:
        return float(-np.log(alpha))
