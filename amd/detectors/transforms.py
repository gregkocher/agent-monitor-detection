"""Per-unit calibration transforms fit on honest calibration units.

- UnitCalibrator: empirical honest CDF -> conformal p-values (conservative / mid / randomized),
  globally or per context (Mondrian) with hierarchical shrinkage toward coarser levels.
- PValue: unit score -> conformal p-value.
- Whiten: unit score -> z = probit(1 - p) or logit(1 - p) (honest units ~ N(0,1) / Logistic).
- KDELogLR: unit score -> log f_attack(s) / f_honest(s) from KDEs (SUPERVISED), optionally
  clipped (Huberized) and/or made monotone.
"""
from __future__ import annotations

import numpy as np
from scipy.special import logit, ndtri
from scipy.stats import gaussian_kde

from .base import Packed, Transform


class UnitCalibrator:
    """Conformal p-values of unit scores against honest calibration units.

    p_cons = (1 + #{h >= s}) / (n + 1)            super-uniform (valid) under exchangeability
    p_rand = (#{h > s} + U (#{h = s} + 1)) / (n+1)  exactly Uniform(0,1) (randomized tie-breaking)
    p_mid  = (#{h > s} + (#{h = s} + 1)/2) / (n+1)  E[p_rand | s]; in (0, 1), used for whitening

    Mondrian mode: contexts are tuples (coarse -> fine). For a unit with context c, the p-value
    is built level by level: p_0 = global; at level l with n_l >= min_n calibration units in the
    prefix c[:l], p_l = w_l * p_hat(prefix) + (1 - w_l) * p_{l-1}, w_l = n_l / (n_l + n0).
    n0 = 0 gives pure Mondrian (finest prefix with >= min_n units); n0 > 0 shrinks small
    contexts toward their parent (partial pooling). Unknown contexts fall back to the deepest
    known prefix. Only pure Mondrian (n0 = 0) keeps the exact per-context conformal guarantee.
    """

    def __init__(self, mondrian: bool = False, min_n: int = 30, n0: float = 0.0):
        self.mondrian = mondrian
        self.min_n = min_n
        self.n0 = n0

    def fit(self, values: np.ndarray, codes: np.ndarray | None = None, table: list | None = None):
        values = np.asarray(values, float)
        self.global_ = np.sort(values)
        self.refs_: dict = {}
        if self.mondrian:
            if codes is None:
                raise ValueError("Mondrian calibration needs contexts")
            groups: dict = {}
            for c in np.unique(codes):
                vals = values[codes == c]
                ctx = table[c]
                for lvl in range(1, len(ctx) + 1):
                    groups.setdefault(ctx[:lvl], []).append(vals)
            self.refs_ = {k: np.sort(np.concatenate(v)) for k, v in groups.items()}
        return self

    @staticmethod
    def _p(ref: np.ndarray, s: np.ndarray, kind: str, u: np.ndarray | None):
        n = len(ref)
        ge = n - np.searchsorted(ref, s, side="left")
        gt = n - np.searchsorted(ref, s, side="right")
        if kind == "conservative":
            return (1.0 + ge) / (n + 1.0)
        if kind == "mid":
            return (gt + 0.5 * (ge - gt + 1.0)) / (n + 1.0)
        if kind == "randomized":
            return (gt + u * (ge - gt + 1.0)) / (n + 1.0)
        raise ValueError(kind)

    def pvalues(self, s: np.ndarray, kind: str = "conservative", codes=None, table=None,
                rng: np.random.Generator | None = None) -> np.ndarray:
        s = np.asarray(s, float)
        u = None
        if kind == "randomized":
            rng = rng if rng is not None else np.random.default_rng()
            u = rng.random(s.shape)
        p = self._p(self.global_, s, kind, u)
        if not self.mondrian or codes is None:
            return p
        p = p.copy()
        for c in np.unique(codes):
            sel = codes == c
            ctx = table[c]
            pc = p[sel]
            uc = None if u is None else u[sel]
            for lvl in range(1, len(ctx) + 1):
                ref = self.refs_.get(ctx[:lvl])
                if ref is None or len(ref) < self.min_n:
                    break
                w = len(ref) / (len(ref) + self.n0)
                pc = w * self._p(ref, s[sel], kind, uc) + (1 - w) * pc
            p[sel] = pc
        return p


class _CalibratedTransform(Transform):
    def __init__(self, kind: str = "conservative", mondrian: bool = False, min_n: int = 30,
                 n0: float = 0.0, seed: int | None = None):
        self.kind = kind
        self.cal = UnitCalibrator(mondrian=mondrian, min_n=min_n, n0=n0)
        self.rng = np.random.default_rng(seed)

    def fit(self, Ph: Packed, Pa=None, attack_onsets=None):
        m = Ph.mask
        codes = None if Ph.codes is None else Ph.codes[m]
        self.cal.fit(Ph.X[m], codes, Ph.table)
        return self

    def pvals(self, P: Packed) -> np.ndarray:
        return self.cal.pvalues(P.X, self.kind, P.codes, P.table, self.rng)

    def __repr__(self):
        m = f", mondrian(min_n={self.cal.min_n}, n0={self.cal.n0})" if self.cal.mondrian else ""
        return f"{type(self).__name__}({self.kind}{m})"


class PValue(_CalibratedTransform):
    """Unit score -> conformal p-value (small = suspicious)."""

    def apply(self, P: Packed) -> np.ndarray:
        return self.pvals(P)


class Whiten(_CalibratedTransform):
    """Unit score -> z = probit(1 - p) (or logit), with p the mid (default) or randomized p-value.

    With randomized p (or continuous scores) honest z is ~N(0,1) (probit) marginally. z is
    bounded by about +/- probit(1 - 0.5/(n+1)) because the empirical CDF has no tail beyond
    the calibration sample.
    """

    def __init__(self, link: str = "probit", kind: str = "mid", **kw):
        super().__init__(kind=kind, **kw)
        assert link in ("probit", "logit")
        self.link = link

    def apply(self, P: Packed) -> np.ndarray:
        q = 1.0 - self.pvals(P)
        q = np.clip(q, 1e-12, 1 - 1e-12)
        return ndtri(q) if self.link == "probit" else logit(q)

    def __repr__(self):
        return f"Whiten({self.link}, {self.kind}{', mondrian' if self.cal.mondrian else ''})"


class KDELogLR(Transform):
    """SUPERVISED per-unit log-likelihood ratio log f1(s)/f0(s) from 1-D Gaussian KDEs.

    f0 = KDE of honest units, f1 = KDE of attack units at/after each attack stream's onset.
    Densities are mixed with eps * uniform on the grid range so the LLR stays finite.
    clip: clip LLR to [-clip, clip] (Huberized / least-favorable LLR; robust CUSUM).
    monotone: isotonic (non-decreasing in s) fit of the LLR on the grid (removes the
    non-monotonicity Hua et al. call the "winner's curse"; off by default).
    """

    supervised = True

    def __init__(self, clip: float | None = None, bw_method=None, monotone: bool = False,
                 eps: float = 1e-3, grid_size: int = 512, max_fit: int = 20000, seed: int = 0):
        self.clip = clip
        self.bw_method = bw_method
        self.monotone = monotone
        self.eps = eps
        self.grid_size = grid_size
        self.max_fit = max_fit
        self.seed = seed

    def _kde(self, v, grid, rng):
        v = np.asarray(v, float)
        if len(v) > self.max_fit:
            v = rng.choice(v, self.max_fit, replace=False)
        if np.std(v) == 0:
            v = v + rng.normal(0, 1e-3, len(v))
        d = gaussian_kde(v, bw_method=self.bw_method)(grid)
        width = grid[-1] - grid[0]
        return (1 - self.eps) * d + self.eps / width

    def fit(self, Ph: Packed, Pa: Packed | None = None, attack_onsets=None):
        if Pa is None:
            raise ValueError("KDELogLR needs attack units")
        rng = np.random.default_rng(self.seed)
        h = Ph.units()
        a = Pa.X[Pa.onset_mask(attack_onsets)]
        lo, hi = min(h.min(), a.min()), max(h.max(), a.max())
        pad = 0.1 * (hi - lo) + 1e-6
        grid = np.linspace(lo - pad, hi + pad, self.grid_size)
        llr = np.log(self._kde(a, grid, rng)) - np.log(self._kde(h, grid, rng))
        if self.monotone:
            from sklearn.isotonic import IsotonicRegression
            llr = IsotonicRegression().fit_transform(grid, llr)
        if self.clip is not None:
            llr = np.clip(llr, -self.clip, self.clip)
        self.grid_, self.llr_ = grid, llr
        return self

    def apply(self, P: Packed) -> np.ndarray:
        return np.interp(P.X, self.grid_, self.llr_)

    def __repr__(self):
        return f"KDELogLR(clip={self.clip}, monotone={self.monotone})"
