"""Packed stream representation and the Detector base class.

A *stream* is a 1-D sequence of per-unit monitor scores (floats; NaN = unscored unit).
Detectors work on a padded matrix of the valid (non-NaN) units of many streams at once,
so every statistic is vectorized across trajectories and loops only over time.

Contexts (for Mondrian calibration) are given per stream, either as one label for the
whole stream (str / int / tuple, a tuple meaning a coarse-to-fine hierarchy such as
(env, task)) or as a list / ndarray of per-unit labels of the stream's length.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

import numpy as np


def _ctx_tuple(c) -> tuple:
    if c is None:
        return ()
    if isinstance(c, tuple):
        return tuple(str(x) for x in c)
    return (str(c),)


@dataclass
class Packed:
    """Valid units of n streams, left-aligned in an (n, T) matrix (tail padded with 0)."""

    X: np.ndarray            # (n, T) float64
    lengths: np.ndarray      # (n,) number of valid units per stream
    positions: list          # per stream: original indices of the valid units
    orig_lengths: np.ndarray  # (n,) original stream lengths (including NaN units)
    codes: np.ndarray | None = None  # (n, T) int context codes, or None
    table: list = field(default_factory=list)  # code -> context tuple

    @property
    def n(self) -> int:
        return self.X.shape[0]

    @property
    def T(self) -> int:
        return self.X.shape[1]

    @property
    def mask(self) -> np.ndarray:
        return np.arange(self.T)[None, :] < self.lengths[:, None]

    def units(self, X: np.ndarray | None = None) -> np.ndarray:
        X = self.X if X is None else X
        return X[self.mask]

    def onset_mask(self, onsets) -> np.ndarray:
        """Mask of valid units whose original index is >= the stream's onset (None = all)."""
        m = self.mask.copy()
        if onsets is None:
            return m
        for i, (pos, a) in enumerate(zip(self.positions, onsets)):
            if a is None or (isinstance(a, float) and np.isnan(a)):
                continue
            m[i, : len(pos)] &= pos >= a
        return m

    def subset(self, idx) -> "Packed":
        idx = np.asarray(idx)
        return Packed(
            X=self.X[idx],
            lengths=self.lengths[idx],
            positions=[self.positions[i] for i in idx],
            orig_lengths=self.orig_lengths[idx],
            codes=None if self.codes is None else self.codes[idx],
            table=self.table,
        )


def pack(streams, contexts=None) -> Packed:
    """Pack a list of streams (or a 2-D array, one row per stream) into a Packed matrix."""
    if isinstance(streams, Packed):
        return streams
    if isinstance(streams, np.ndarray) and streams.ndim == 2:
        arrs = [row for row in streams.astype(float)]
    else:
        arrs = [np.asarray(s, dtype=float).ravel() for s in streams]
    n = len(arrs)
    valid = [~np.isnan(a) for a in arrs]
    lengths = np.array([int(v.sum()) for v in valid], dtype=int)
    orig = np.array([len(a) for a in arrs], dtype=int)
    T = max(1, int(lengths.max()) if n else 1)
    X = np.zeros((n, T))
    positions = []
    for i, (a, v) in enumerate(zip(arrs, valid)):
        L = lengths[i]
        X[i, :L] = a[v] if L < len(a) else a
        positions.append(np.flatnonzero(v))
    codes, table = None, []
    if contexts is not None:
        assert len(contexts) == n, "one context entry per stream"
        lookup: dict = {}
        codes = np.zeros((n, T), dtype=np.int32)

        def code(c):
            t = _ctx_tuple(c)
            if t not in lookup:
                lookup[t] = len(table)
                table.append(t)
            return lookup[t]

        for i, c in enumerate(contexts):
            if isinstance(c, (list, np.ndarray)):
                assert len(c) == orig[i], "per-unit contexts must match the stream length"
                cs = [code(c[j]) for j in positions[i]]
                codes[i, : len(cs)] = cs
            else:
                codes[i, :] = code(c)
    return Packed(X, lengths, positions, orig, codes, table)


def concat_packed(P: Packed, order_rows: list[np.ndarray], length: int) -> Packed:
    """Concatenate rows of P (valid units only) into long streams truncated to `length`.

    order_rows[r] lists the stream indices concatenated into long stream r.
    """
    n = len(order_rows)
    X = np.zeros((n, length))
    codes = None if P.codes is None else np.zeros((n, length), dtype=np.int32)
    lengths = np.zeros(n, dtype=int)
    for r, idx in enumerate(order_rows):
        xs = np.concatenate([P.X[i, : P.lengths[i]] for i in idx])[:length]
        X[r, : len(xs)] = xs
        lengths[r] = len(xs)
        if codes is not None:
            cs = np.concatenate([P.codes[i, : P.lengths[i]] for i in idx])[:length]
            codes[r, : len(cs)] = cs
    positions = [np.arange(L) for L in lengths]
    return Packed(X, lengths, positions, lengths.copy(), codes, P.table)


# ---------------------------------------------------------------------------------------
# transforms (per-unit maps, fit on honest calibration units)
# ---------------------------------------------------------------------------------------


class Transform:
    """Per-unit map applied before aggregation. Identity by default."""

    supervised = False

    def fit(self, Ph: Packed, Pa: Packed | None = None, attack_onsets=None) -> "Transform":
        return self

    def apply(self, P: Packed) -> np.ndarray:
        return P.X

    def __repr__(self):
        return type(self).__name__ + "()"


Identity = Transform


# ---------------------------------------------------------------------------------------
# detector base
# ---------------------------------------------------------------------------------------


class Detector:
    """Base class: transform (per unit) -> running statistic path -> trajectory statistic.

    Subclasses implement `_agg(U, lengths) -> (n, T)` returning the running statistic after
    each valid unit (values in the padded tail are ignored). `alarm_type=True` means the
    detector alarms when the path first exceeds a threshold, so the trajectory statistic is
    the max over the path; otherwise it is the final value.
    """

    name = "detector"
    alarm_type = True
    empty_value = -np.inf  # statistic of a stream with no valid units

    def __init__(self, transform: Transform | None = None):
        self.transform = transform if transform is not None else Transform()
        self.fitted_ = False

    # -- properties -----------------------------------------------------------------
    @property
    def supervised(self) -> bool:
        return bool(getattr(self.transform, "supervised", False))

    def __repr__(self):
        return f"{type(self).__name__}({self.name})"

    def clone(self) -> "Detector":
        d = copy.deepcopy(self)
        d.fitted_ = False
        return d

    # -- fitting --------------------------------------------------------------------
    def fit(self, honest_streams, contexts=None, attack_streams=None, attack_contexts=None,
            attack_onsets=None) -> "Detector":
        """Fit on honest calibration streams (and attack streams for supervised detectors).

        attack_onsets: per attack stream, the original index of the first attack unit (units
        before it are excluded from the attack reference distribution); None = all units.
        """
        Ph = pack(honest_streams, contexts)
        Pa = None if attack_streams is None else pack(attack_streams, attack_contexts)
        return self._fit_packed(Ph, Pa, attack_onsets)

    def _fit_packed(self, Ph: Packed, Pa: Packed | None = None, attack_onsets=None):
        if self.supervised and Pa is None:
            raise ValueError(f"{self.name} is supervised: fit() needs attack_streams")
        self.transform.fit(Ph, Pa, attack_onsets)
        self._fit_agg(self.transform.apply(Ph), Ph)
        self.fitted_ = True
        return self

    def _fit_agg(self, U: np.ndarray, P: Packed) -> None:
        """Hook for aggregators that learn from transformed honest units."""

    # -- core computation -------------------------------------------------------------
    def _agg(self, U: np.ndarray, lengths: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def paths_packed(self, P: Packed) -> np.ndarray:
        return self._agg(self.transform.apply(P), P.lengths)

    def stats_packed(self, P: Packed) -> np.ndarray:
        paths = self.paths_packed(P)
        L = P.lengths
        if self.alarm_type:
            out = np.where(P.mask, paths, -np.inf).max(axis=1)
        else:
            out = paths[np.arange(P.n), np.maximum(L - 1, 0)].astype(float)
        out = np.asarray(out, dtype=float)
        out[L == 0] = self.empty_value
        return out

    # -- public API -----------------------------------------------------------------
    def stats(self, streams, contexts=None) -> np.ndarray:
        """Trajectory statistic for each stream (vectorized)."""
        return self.stats_packed(pack(streams, contexts))

    def stat(self, stream, context=None) -> float:
        return float(self.stats([stream], None if context is None else [context])[0])

    def stat_paths(self, streams, contexts=None) -> list[np.ndarray]:
        """Running statistic after each unit, aligned to the original (NaN-including) index.

        NaN units leave the statistic unchanged; before the first valid unit the value is
        `empty_value`.
        """
        P = pack(streams, contexts)
        paths = self.paths_packed(P)
        return [_expand(paths[i, : P.lengths[i]], P.positions[i], P.orig_lengths[i], self.empty_value)
                for i in range(P.n)]

    def stat_path(self, stream, context=None) -> np.ndarray:
        return self.stat_paths([stream], None if context is None else [context])[0]

    def first_alarm_packed(self, P: Packed, h: float) -> np.ndarray:
        """Original index of the first unit after which path > h (-1 = never)."""
        paths = self.paths_packed(P)
        hit = (paths > h) & P.mask
        any_hit = hit.any(axis=1)
        t = hit.argmax(axis=1)
        out = np.full(P.n, -1, dtype=int)
        for i in np.flatnonzero(any_hit):
            out[i] = P.positions[i][t[i]]
        return out

    def first_alarm(self, streams, h: float, contexts=None) -> np.ndarray:
        return self.first_alarm_packed(pack(streams, contexts), h)

    # -- change-point localization ------------------------------------------------------
    def increments_packed(self, P: Packed) -> np.ndarray | None:
        """Per-unit log-evidence increments g_t (for onset estimation), or None."""
        return None

    def onset_packed(self, P: Packed, end: np.ndarray | None = None) -> np.ndarray:
        """Estimated change point (original index) per stream, using units up to `end`.

        end: per-stream compressed index of the last unit to use (default: last unit).
        Increment-based detectors return argmax_j sum_{i=j..end} g_i (the CUSUM / maximum-
        likelihood onset; ties broken toward the latest j). Others return the first argmax of
        the transformed unit score.
        """
        L = P.lengths
        end = np.maximum(L - 1, 0) if end is None else np.asarray(end)
        g = self.increments_packed(P)
        out = np.full(P.n, -1, dtype=int)
        if g is None:
            U = self.transform.apply(P)
            for i in range(P.n):
                if L[i] == 0:
                    continue
                j = int(np.argmax(U[i, : end[i] + 1]))
                out[i] = P.positions[i][j]
            return out
        for i in range(P.n):
            if L[i] == 0:
                continue
            C = np.concatenate([[0.0], np.cumsum(g[i, : end[i] + 1])])
            # onset j maximizes C[end+1] - C[j]  <=> minimizes C[j], j in [0, end]
            seg = C[: end[i] + 1]
            j = len(seg) - 1 - int(np.argmin(seg[::-1]))
            out[i] = P.positions[i][j]
        return out


def _expand(path: np.ndarray, positions: np.ndarray, orig_len: int, empty_value: float) -> np.ndarray:
    valid = np.zeros(orig_len, dtype=bool)
    valid[positions] = True
    cnt = np.cumsum(valid)
    out = np.full(orig_len, empty_value, dtype=float)
    has = cnt > 0
    out[has] = path[cnt[has] - 1]
    return out
