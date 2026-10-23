"""Shared helpers for the white-box threshold-convention reruns (fixes pass 2, prefix wb_).

Only the randomized threshold rule is switched; every other piece (data loading, splits, bootstrap, seeds) is the
committed track / audit code.

  convention(name)       -- amd threshold convention ("plugin" = every committed result, "conformal" = smoothed
                            conformal p-value rule) AND the matching patches below, as one context manager.
  contrast_alpha_rt      -- drop-in for tracks.r4_wb.r4lib.contrast_alpha (identical arithmetic, but per-replicate
                            thresholds from amd.evaluation.calibration.row_thresholds instead of
                            matched._boot_threshold, which raises under the conformal convention). Under "plugin"
                            row_thresholds returns the same (h, gamma) rows, so the old numbers are reproduced.
  wb_lib / a2lib patches -- the audit libraries carry their own copy of the plug-in rule (wthresh / alarm_rate,
                            rand_threshold / alarm); under "conformal" they are replaced by the smoothed conformal
                            rule with the same call signatures (weights = integer multiplicities, trajectory units).
  redirect_writes(dest)  -- rewrite hard-coded output paths (results/audit2|audit3|r4_wb|wb/...) into dest.
"""
from __future__ import annotations

import builtins
import contextlib
import importlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from amd.common.schema import REPO
from amd.evaluation.calibration import (RowThresholds, conformal_randomized_threshold, row_thresholds,
                                        smoothed_rows_shared, threshold_convention)
from amd.evaluation.matched import bootstrap_weights

OUT_ROOT = REPO / "results" / "fixes2"


# ------------------------------------------------------------------------------------------------
# r4lib.contrast_alpha with row_thresholds
# ------------------------------------------------------------------------------------------------
def contrast_alpha_rt(terms, n_h, n_a, hg, ag, B=2000, seed=0):
    from amd.evaluation import calibrate
    from tracks.r4_wb.r4lib import two_sided
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
            A = row_thresholds(cal[order], Wh[:, np.asarray(r["cal_idx"])][:, order], al, "randomized").alarm(s)
            bt += coef * (A * wa).sum(axis=1) / den
        est.append(pt)
        boot.append(bt)
    b = np.mean(boot, axis=0)
    return two_sided(dict(est=float(np.mean(est)), lo=float(np.quantile(b, 0.025)), hi=float(np.quantile(b, 0.975)),
                          se=float(np.std(b, ddof=1)), p_le0=float((b <= 0).mean()), p_ge0=float((b >= 0).mean()),
                          n_splits=len(est), n_boot=B))


R4WB_IMPORTERS = ("tracks.r4_wb.r4lib", "tracks.r4_wb.analyze_primary", "tracks.r4_wb.analyze_a1_mb")


# ------------------------------------------------------------------------------------------------
# audit3 wb_lib: wthresh / alarm_rate
# ------------------------------------------------------------------------------------------------
class ThrArr(np.ndarray):
    """(B,) array of informational levels carrying the conformal RowThresholds; survives np.repeat."""

    def __array_finalize__(self, obj):
        self.rows = getattr(obj, "rows", None)


def wthresh_conformal(cal, W, alpha):
    rows = smoothed_rows_shared(np.asarray(cal, float), np.atleast_2d(np.asarray(W, float)), alpha)
    h = np.full(len(rows), np.nan).view(ThrArr)
    h.rows = rows
    return h, None


def _rows_rate(rows: RowThresholds, s, W):
    A = rows.alarm(np.asarray(s, float))
    if W is None:
        return A.mean(1)
    W = np.atleast_2d(np.asarray(W, float))
    if A.shape[0] == 1 and W.shape[0] > 1:
        A = np.broadcast_to(A, (W.shape[0], A.shape[1]))
    return (A * W).sum(1) / np.maximum(W.sum(1), 1e-12)


def make_alarm_rate(orig):
    def alarm_rate(s, h, g, W=None):
        if isinstance(h, ThrArr) and h.rows is not None:
            return _rows_rate(h.rows, s, W)
        return orig(s, h, g, W)
    return alarm_rate


# ------------------------------------------------------------------------------------------------
# audit2 a2lib: rand_threshold / alarm (1-D weights)
# ------------------------------------------------------------------------------------------------
class _Conf:
    def __init__(self, thr):
        self.thr = thr


def rand_threshold_conformal(cal, w, alpha):
    return _Conf(conformal_randomized_threshold(np.asarray(cal, float), alpha, weights=np.asarray(w, float))), None


def make_alarm(orig):
    def alarm(s, h, g):
        if isinstance(h, _Conf):
            return h.thr.alarm_prob(np.asarray(s, float))
        return orig(s, h, g)
    return alarm


# ------------------------------------------------------------------------------------------------
# patching
# ------------------------------------------------------------------------------------------------
@contextlib.contextmanager
def patched(targets):
    """targets: list of (module_name, attr, new_value)."""
    saved = []
    try:
        for mod, attr, val in targets:
            m = importlib.import_module(mod)
            saved.append((m, attr, getattr(m, attr)))
            setattr(m, attr, val)
        yield
    finally:
        for m, attr, old in reversed(saved):
            setattr(m, attr, old)


def wb_lib_targets(conv, importers=("tracks.audit3.wb_lib",)):
    """wb_lib functions are looked up through each importer's namespace; patch every importer."""
    if conv != "conformal":
        return []
    lib = importlib.import_module("tracks.audit3.wb_lib")
    ar = make_alarm_rate(lib.alarm_rate)
    t = []
    for mod in importers:
        m = importlib.import_module(mod)
        if hasattr(m, "wthresh"):
            t.append((mod, "wthresh", wthresh_conformal))
        if hasattr(m, "alarm_rate"):
            t.append((mod, "alarm_rate", ar))
    return t


def a2lib_targets(conv, importers=("tracks.audit2.a2lib",)):
    if conv != "conformal":
        return []
    lib = importlib.import_module("tracks.audit2.a2lib")
    al = make_alarm(lib.alarm)
    t = []
    for mod in importers:
        m = importlib.import_module(mod)
        if hasattr(m, "rand_threshold"):
            t.append((mod, "rand_threshold", rand_threshold_conformal))
        if hasattr(m, "alarm"):
            t.append((mod, "alarm", al))
    return t


def r4lib_targets():
    return [(m, "contrast_alpha", contrast_alpha_rt) for m in R4WB_IMPORTERS]


@contextlib.contextmanager
def convention(conv, extra_targets=()):
    with threshold_convention(conv), patched(list(extra_targets)):
        yield


# ------------------------------------------------------------------------------------------------
# output redirection for hard-coded paths
# ------------------------------------------------------------------------------------------------
_PROTECTED = ("results/audit2/", "results/audit3/", "results/r4_wb/", "results/wb/")


def _map(path, dest: Path):
    p = str(path)
    rel = p[len(str(REPO)) + 1:] if p.startswith(str(REPO)) else p
    for pre in _PROTECTED:
        if rel.startswith(pre):
            return dest / rel[len(pre):]
    if rel.startswith("results/") and not rel.startswith("results/fixes2/"):
        raise RuntimeError(f"refusing to write {p}")
    return Path(p)


@contextlib.contextmanager
def redirect_writes(dest: Path, modules=()):
    """Redirect DataFrame.to_csv and open(..., 'w') in the given modules from protected results dirs to dest."""
    dest.mkdir(parents=True, exist_ok=True)
    orig_to_csv = pd.DataFrame.to_csv

    def to_csv(self, path_or_buf=None, *a, **k):
        if isinstance(path_or_buf, (str, Path)):
            path_or_buf = _map(path_or_buf, dest)
        return orig_to_csv(self, path_or_buf, *a, **k)

    def open_(file, mode="r", *a, **k):
        if any(c in mode for c in "wax"):
            file = _map(file, dest)
        return builtins.open(file, mode, *a, **k)

    pd.DataFrame.to_csv = to_csv
    mods = [importlib.import_module(m) for m in modules]
    had = [(m, m.__dict__.get("open", None)) for m in mods]
    for m in mods:
        m.open = open_
    try:
        yield
    finally:
        pd.DataFrame.to_csv = orig_to_csv
        for m, o in had:
            if o is None:
                m.__dict__.pop("open", None)
            else:
                m.open = o


def outdir(name, conv):
    return OUT_ROOT / f"wb_{name}_{conv}_thrfix"


def dump(obj, path):
    with builtins.open(path, "w") as f:
        json.dump(obj, f, indent=1, default=float)
