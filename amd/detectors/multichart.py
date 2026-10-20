"""Multi-chart OR detector with a jointly calibrated budget split.

Component i has trajectory statistic S_i and, on the honest fit streams, the conformal tail
function T_i(s) = (1 + #{cal S_i >= s}) / (n + 1). With budget weights w_i (sum 1), the OR
alarm "some component i has T_i(S_i) <= beta * w_i" is the single statistic

    M = max_i [ -log T_i(S_i) + log w_i ]   alarm iff M >= -log beta.

Calibrating ONE threshold on M (by the matched-budget protocol) sets the OR's trajectory FPR
to the target while splitting the budget across components in proportion to w, and accounts
for the dependence between components (unlike a Bonferroni split alpha*w_i per component,
which is conservative). The running path uses each component's running path, so the streaming
alarm time is the first time any component crosses its share.

tail="exp" (opt-in) extends T_i beyond the largest honest fit statistic with an exponential tail,
log T_i(s) = log(1/(n+1)) - (s - max_ref) / scale_i (scale_i = mean excess over the 90% quantile),
so statistics beyond the calibration range keep their order instead of all tying at 1/(n+1).
This matters when alpha is close to 1/n_cal: with the empirical tail, every attack beyond the
honest range ties with the most extreme calibration statistics and is alarmed only with the
randomization probability.
"""
from __future__ import annotations

import numpy as np

from .base import Detector, Packed


class MultiChart(Detector):
    def __init__(self, components: list[Detector], weights=None, name: str | None = None,
                 tail: str = "empirical"):
        super().__init__(None)
        assert tail in ("empirical", "exp"), tail
        self.tail = tail
        self.components = components
        w = np.ones(len(components)) if weights is None else np.asarray(weights, float)
        self.weights = w / w.sum()
        self.name = name or "or(" + "+".join(c.name for c in components) + ")"

    @property
    def supervised(self) -> bool:
        return any(c.supervised for c in self.components)

    def _fit_packed(self, Ph: Packed, Pa: Packed | None = None, attack_onsets=None):
        self.ref_ = []
        for c in self.components:
            c._fit_packed(Ph, Pa if c.supervised else None, attack_onsets if c.supervised else None)
            self.ref_.append(np.sort(c.stats_packed(Ph)))
        self.scale_ = []
        for ref in self.ref_:
            fin = ref[np.isfinite(ref)]
            sc = np.nan
            if len(fin) >= 5:
                q = np.quantile(fin, 0.9)
                ex = fin[fin > q] - q
                sc = ex.mean() if len(ex) else np.nan
                if not np.isfinite(sc) or sc <= 0:
                    sc = fin.std()
            self.scale_.append(sc if np.isfinite(sc) and sc > 0 else 1.0)
        self.fitted_ = True
        return self

    def _logtail(self, i: int, s: np.ndarray) -> np.ndarray:
        ref = self.ref_[i]
        n = len(ref)
        ge = n - np.searchsorted(ref, s, side="left")
        out = np.log((1.0 + ge) / (n + 1.0))
        if self.tail == "exp" and n:
            beyond = s > ref[-1]
            if np.any(beyond):
                out = np.where(beyond, -np.log(n + 1.0) - (s - ref[-1]) / self.scale_[i], out)
        return out

    def component_paths(self, P: Packed) -> list[np.ndarray]:
        out = []
        for i, c in enumerate(self.components):
            path = c.paths_packed(P)
            if c.alarm_type:
                # running max so the component's contribution matches its alarm semantics
                path = np.maximum.accumulate(path, axis=1)
            out.append(-self._logtail(i, path) + np.log(self.weights[i]))
        return out

    def paths_packed(self, P: Packed) -> np.ndarray:
        return np.maximum.reduce(self.component_paths(P))

    def stats_packed(self, P: Packed) -> np.ndarray:
        cols = []
        for i, c in enumerate(self.components):
            cols.append(-self._logtail(i, c.stats_packed(P)) + np.log(self.weights[i]))
        return np.max(np.stack(cols), axis=0)

    def which_component(self, streams, contexts=None) -> np.ndarray:
        """Index of the component attaining the OR statistic for each stream."""
        from .base import pack
        P = pack(streams, contexts)
        cols = [-self._logtail(i, c.stats_packed(P)) + np.log(self.weights[i])
                for i, c in enumerate(self.components)]
        return np.argmax(np.stack(cols), axis=0)
