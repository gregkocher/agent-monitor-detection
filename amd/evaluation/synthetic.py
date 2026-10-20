"""Synthetic score streams with known ground truth (for tests and method sanity checks)."""
from __future__ import annotations

import numpy as np


def _lengths(n, length, rng):
    if isinstance(length, (tuple, list)):
        return rng.integers(length[0], length[1] + 1, size=n)
    return np.full(n, int(length))


def noise_streams(n: int, length, rng: np.random.Generator, ar: float = 0.0, sd: float = 1.0,
                  mean: float = 0.0) -> list[np.ndarray]:
    """Gaussian streams; ar > 0 gives stationary AR(1) noise with marginal sd `sd`."""
    out = []
    for L in _lengths(n, length, rng):
        e = rng.normal(size=L)
        if ar:
            x = np.empty(L)
            prev = rng.normal()
            c = np.sqrt(1 - ar**2)
            for t in range(L):
                prev = ar * prev + c * e[t]
                x[t] = prev
            e = x
        out.append(mean + sd * e)
    return out


def inject(streams: list[np.ndarray], rng: np.random.Generator, kind: str = "shift",
           magnitude: float = 1.0, onset="uniform", ramp_len: int = 10, min_post: int = 1):
    """Add an attack signal starting at an onset index. Returns (streams, onsets).

    kind: 'shift' (+magnitude for t >= onset), 'spike' (+magnitude at the onset only),
          'ramp'  (+magnitude * min(1, (t - onset + 1) / ramp_len) for t >= onset).
    onset: 'uniform' (uniform over [0, L - min_post]), an int, or a float fraction of L.
    """
    out, onsets = [], []
    for s in streams:
        L = len(s)
        if onset == "uniform":
            a = int(rng.integers(0, max(1, L - min_post + 1)))
        elif isinstance(onset, float):
            a = int(onset * L)
        else:
            a = int(onset)
        a = min(a, L - 1)
        x = np.array(s, float)
        t = np.arange(L)
        if kind == "shift":
            x[t >= a] += magnitude
        elif kind == "spike":
            x[a] += magnitude
        elif kind == "ramp":
            x[t >= a] += magnitude * np.minimum(1.0, (t[t >= a] - a + 1) / ramp_len)
        else:
            raise ValueError(kind)
        out.append(x)
        onsets.append(a)
    return out, np.array(onsets)


def quantize(streams, lo: int = 0, hi: int = 10, scale: float = 1.5, offset: float = 1.0):
    """Integer 0-10 style scores with heavy ties at the low end: clip(round(offset + scale*x))."""
    return [np.clip(np.round(offset + scale * np.asarray(s)), lo, hi) for s in streams]


def cumulative_judgment(streams, rho: float = 0.9):
    """History-aware monitor model: h_t = rho h_{t-1} + sqrt(1 - rho^2) x_t (h_0 = x_0).

    The monitor integrates evidence over the history (an EWMA), so honest scores keep N(0,1)
    marginals but are strongly autocorrelated, and a sustained shift mu in the innovations
    x appears as a level ~ mu * sqrt((1 + rho) / (1 - rho)).
    """
    c = np.sqrt(1 - rho**2)
    out = []
    for s in streams:
        s = np.asarray(s, float)
        h = np.empty_like(s)
        prev = s[0] if len(s) else 0.0
        for t in range(len(s)):
            prev = s[t] if t == 0 else rho * prev + c * s[t]
            h[t] = prev
        out.append(h)
    return out
