"""Classical quickest-change statistics on whitened (or log-LR) unit scores."""
from __future__ import annotations

import numpy as np

from .aggregators import Max
from .base import Detector, Packed, Transform
from .transforms import KDELogLR, Whiten


class CUSUM(Detector):
    """Page CUSUM with reflection at 0:  S_t = max(0, S_{t-1} + u_t - k),  S_0 = 0.

    On whitened scores (u = z ~ N(0,1) honest) and a target shift delta, k = delta/2 is the
    Gaussian LLR design (`CUSUM.design(delta)`). With u = (clipped) log-LR increments use k=0.
    """

    empty_value = 0.0

    def __init__(self, k: float = 0.5, transform: Transform | None = "whiten"):
        super().__init__(Whiten() if transform == "whiten" else transform)
        self.k = k
        self.name = f"cusum_k{k:g}"

    @classmethod
    def design(cls, delta: float, **kw) -> "CUSUM":
        return cls(k=delta / 2.0, **kw)

    def _agg(self, U, lengths):
        n, T = U.shape
        out = np.empty((n, T))
        S = np.zeros(n)
        for t in range(T):
            S = np.maximum(0.0, S + U[:, t] - self.k)
            out[:, t] = S
        return out

    def increments_packed(self, P: Packed):
        return self.transform.apply(P) - self.k


class ShiryaevRoberts(Detector):
    """Shiryaev-Roberts in the log domain: R_t = (1 + R_{t-1}) * LR_t, R_0 = 0.

    log R_t = logaddexp(0, log R_{t-1}) + l_t, with l_t = delta*z_t - delta^2/2 (Gaussian
    mean-shift LR on whitened z) or, if delta is None, the transformed unit value itself (a
    log-LR from a supervised transform). Statistic = log R; threshold log A gives ARL0 >= A
    for a correct LR.
    """

    def __init__(self, delta: float | None = 1.0, transform: Transform | None = "whiten"):
        super().__init__(Whiten() if transform == "whiten" else transform)
        self.delta = delta
        self.name = "sr" + ("" if delta is None else f"_d{delta:g}")

    def _llr(self, U):
        if self.delta is None:
            return U
        return self.delta * U - 0.5 * self.delta**2

    def _agg(self, U, lengths):
        n, T = U.shape
        l = self._llr(U)
        out = np.empty((n, T))
        logR = np.full(n, -np.inf)
        for t in range(T):
            logR = np.logaddexp(0.0, logR) + l[:, t]
            out[:, t] = logR
        return out

    def increments_packed(self, P: Packed):
        return self._llr(self.transform.apply(P))


class WindowGLR(Detector):
    """Window-limited GLR for an unknown positive mean shift of unit-variance whitened scores:

        G_t = max_{1 <= m <= min(W, t)} max(0, sum_{i=t-m+1..t} z_i)^2 / (2 m)

    (the log-GLR maximized over onset in the last W units and shift mu >= 0).
    """

    empty_value = 0.0

    def __init__(self, window: int = 20, transform: Transform | None = "whiten"):
        super().__init__(Whiten() if transform == "whiten" else transform)
        self.window = window
        self.name = f"glr_w{window}"

    def _agg(self, U, lengths):
        n, T = U.shape
        C = np.concatenate([np.zeros((n, 1)), np.cumsum(U, axis=1)], axis=1)
        G = np.zeros((n, T))
        for m in range(1, min(self.window, T) + 1):
            S = C[:, m:] - C[:, :-m]  # sum of last m units ending at t = m-1..T-1
            G[:, m - 1:] = np.maximum(G[:, m - 1:], np.maximum(S, 0.0) ** 2 / (2.0 * m))
        return G

    def onset_packed(self, P: Packed, end=None):
        U = self.transform.apply(P)
        L = P.lengths
        end = np.maximum(L - 1, 0) if end is None else np.asarray(end)
        out = np.full(P.n, -1, dtype=int)
        for i in range(P.n):
            if L[i] == 0:
                continue
            e = end[i]
            ms = np.arange(1, min(self.window, e + 1) + 1)
            C = np.concatenate([[0.0], np.cumsum(U[i, : e + 1])])
            S = C[e + 1] - C[e + 1 - ms]
            g = np.maximum(S, 0) ** 2 / (2 * ms)
            out[i] = P.positions[i][e + 1 - ms[int(np.argmax(g))]]
        return out


class LLRCUSUM(CUSUM):
    """SUPERVISED CUSUM on a clipped (Huberized) KDE log-likelihood ratio, k = 0:
    S_t = max(0, S_{t-1} + clip(log f1(s_t)/f0(s_t), -c, c))."""

    def __init__(self, clip: float = 3.0, **kde_kw):
        super().__init__(k=0.0, transform=KDELogLR(clip=clip, **kde_kw))
        self.name = f"llr_cusum_c{clip:g}"


class LRMax(Max):
    """SUPERVISED Hua-style rule: max over units of the KDE log-likelihood ratio."""

    def __init__(self, monotone: bool = False, **kde_kw):
        super().__init__(KDELogLR(clip=None, monotone=monotone, **kde_kw))
        self.name = "lr_max" + ("_mono" if monotone else "")
