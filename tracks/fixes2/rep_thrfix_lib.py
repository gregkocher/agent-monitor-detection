"""Shared helpers for the r4_replay / Idea-3 threshold-convention reruns (prefix rep_, outputs *_thrfix).

* `conformal_a2lib(module)`: context manager that swaps a module's imported a2lib-style `rand_threshold(cal, w,
  alpha) -> (h, g)` / `alarm(s, h, g)` pair (tracks/audit2/a2lib.py, a private copy of the plug-in rule that the
  AMD_THRESHOLD_CONVENTION switch does not reach) for the conformal randomized rule
  (amd.evaluation.calibration.conformal_randomized_threshold, integer-multiplicity weights). `h` stays a float
  (the certain-alarm level) so code that prints or compares it keeps working; `g` becomes a float subclass
  carrying the threshold object, which the patched `alarm` dispatches on.
* `RedirectPD`: stand-in for a module's `pd` whose DataFrame(...).to_csv(path) writes into a redirect directory
  (for scripts with hardcoded output paths).
* `loo_fpr(H, alpha, convention)`: leave-one-out out-of-sample FPR of a threshold calibrated on all honest runs
  (exact estimate of the expected FPR of the n-1 procedure; for the conformal rule it is alpha by construction
  when the statistics are distinct).
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

from amd.evaluation.calibration import conformal_randomized_threshold, randomized_threshold_plugin

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "results" / "fixes2"


class _G(float):
    """Band probability that also carries the conformal threshold object."""

    def __new__(cls, gamma, thr):
        o = super().__new__(cls, gamma)
        o.thr = thr
        return o


def conf_rand_threshold(cal, w, alpha):
    cal = np.asarray(cal, float)
    w = np.asarray(w, float)
    thr = conformal_randomized_threshold(cal, alpha, weights=w)
    return float(thr.h), _G(thr.gamma, thr)


def make_alarm(orig_alarm):
    def alarm(s, h, g):
        if isinstance(g, _G):
            return g.thr.alarm_prob(np.asarray(s, float))
        return orig_alarm(s, h, g)
    return alarm


@contextmanager
def conformal_a2lib(module, enabled=True):
    if not enabled:
        yield
        return
    old_t, old_a = module.rand_threshold, module.alarm
    module.rand_threshold = conf_rand_threshold
    module.alarm = make_alarm(old_a)
    try:
        yield
    finally:
        module.rand_threshold, module.alarm = old_t, old_a


class _W:
    """DataFrame wrapper whose to_csv writes into a redirect directory (same file name)."""

    def __init__(self, df, redirect):
        self._df, self._redirect = df, redirect

    def to_csv(self, path=None, *a, **kw):
        tgt = self._redirect / Path(path).name
        print(f"  [redirect] {path} -> {tgt}", flush=True)
        return self._df.to_csv(tgt, *a, **kw)

    def __getattr__(self, k):
        return getattr(self._df, k)


class RedirectPD:
    """Proxy for the pandas module: DataFrame(...) writes its CSV into `redirect`."""

    def __init__(self, redirect: Path):
        self._redirect = Path(redirect)
        self._redirect.mkdir(parents=True, exist_ok=True)

    def DataFrame(self, *a, **kw):  # noqa: N802
        return _W(pd.DataFrame(*a, **kw), self._redirect)

    def __getattr__(self, k):
        return getattr(pd, k)


def loo_fpr(H, alpha, convention):
    """Mean over i of P(alarm on H_i | threshold calibrated on H without i)."""
    H = np.asarray(H, float)
    n = len(H)
    out = np.empty(n)
    for i in range(n):
        cal = np.delete(H, i)
        thr = (conformal_randomized_threshold(cal, alpha) if convention == "conformal"
               else randomized_threshold_plugin(cal, alpha))
        out[i] = float(thr.alarm_prob(H[i:i + 1])[0])
    return float(out.mean())


def split_fpr(H, alpha, convention, groups=None, R=500, seed=3):
    """Mean held-out FPR over random 50/50 honest splits (task-grouped when groups given)."""
    H = np.asarray(H, float)
    rng = np.random.default_rng(seed)
    v = []
    for _ in range(R):
        if groups is None:
            idx = rng.permutation(len(H))
            m = np.zeros(len(H), bool)
            m[idx[: len(H) // 2]] = True
        else:
            g = np.asarray(groups)
            ug = np.unique(g)
            m = np.isin(g, ug[rng.permutation(len(ug))[: len(ug) // 2]])
        thr = (conformal_randomized_threshold(H[m], alpha) if convention == "conformal"
               else randomized_threshold_plugin(H[m], alpha))
        v.append(float(thr.alarm_prob(H[~m]).mean()))
    return float(np.mean(v))
