"""Threshold-convention switch for the per-context allocation tracks (t2_per_context round 1 and r4_ctx).

Neither track calls amd.evaluation.calibration.randomized_threshold: both build their thresholds with their own
copies of the plug-in rule, so the AMD_THRESHOLD_CONVENTION flag does not reach them. `apply(variant)` monkeypatches
the track modules in the current process (call it in every worker process too):

  "plugin"         no patch (committed pipeline; used to reproduce the old numbers).
  "conformal"      the randomized-quantile rules are replaced by the smoothed conformal rule
                   (amd conformal_randomized_threshold):
                     t2lib.rule_global  pooled traffic-weighted calibration distribution, masses in trajectory units
                                        (mass of value u = N * sum_c w_c P_c(u), N = total calibration count);
                     t2lib.rule_cfar    per-context conformal rule on that context's calibration counts.
                   The Stackelberg rules do not use the randomized quantile (they mix ROC-hull vertices) and are
                   left unchanged.
  "conformal_hull" "conformal" plus the Stackelberg ROC hulls re-built with the conformal FPR of each
                   candidate threshold, (#{H > h} + 1)/(n + 1), and an extra no-alarm vertex (h = +inf, FPR 0,
                   TPR 0) (t2lib.hulls and r2lib.hull_w). The hull's in-sample FPR #{H > h}/n is the same
                   plug-in estimate as the randomized quantile's, so this variant switches the convention in every
                   rule of the contrast.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / "tracks" / "t2_per_context", ROOT / "tracks" / "r2_t2", ROOT / "tracks" / "r4_ctx", ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import r2lib as R  # noqa: E402
import t2lib as L  # noqa: E402

from amd.evaluation.calibration import conformal_randomized_threshold  # noqa: E402
from amd.evaluation.contexts import _upper_hull  # noqa: E402

VARIANTS = ("plugin", "conformal", "conformal_hull")
_ORIG = dict(rule_global=L.rule_global, rule_cfar=L.rule_cfar, hulls=L.hulls, hull_w=R.hull_w)
STATE = {"variant": "plugin"}


def rule_global_conformal(G, B):
    N = float(G.n.sum())
    mass = G.g * N
    t = conformal_randomized_threshold(G.U, B, weights=mass)
    t.method = "global"
    return {k: t for k in G.keys}


def rule_cfar_conformal(G, B):
    out = {}
    for i, k in enumerate(G.keys):
        counts = np.round(G.P[i] * G.n[i])
        t = conformal_randomized_threshold(G.U, B, weights=counts)
        t.method = "cfar"
        out[k] = t
    return out


def hull_conformal(h, a, wa=None):
    """r2lib.hull_w with conformal FPR coordinates (#{H > c} + 1)/(n + 1) and a no-alarm vertex at c = +inf."""
    hs = np.sort(np.asarray(h, float))
    n = len(hs)
    cand = np.concatenate([[-np.inf], np.unique(hs), [np.inf]])
    gt = n - np.searchsorted(hs, cand, side="right")
    fpr = (gt + 1.0) / (n + 1.0)
    fpr[0] = 1.0
    fpr[-1] = 0.0
    a = np.asarray(a, float)
    wa = np.full(len(a), 1.0 / len(a)) if wa is None else np.asarray(wa, float) / np.sum(wa)
    o = np.argsort(a)
    cw = np.concatenate([[0.0], np.cumsum(wa[o])])
    tpr = 1.0 - cw[np.searchsorted(a[o], cand, side="right")]
    tpr[-1] = 0.0
    idx = _upper_hull(fpr, tpr)
    return fpr[idx], np.clip(tpr[idx], 0, 1), cand[idx]


def hulls_conformal(H, A):
    return {k: hull_conformal(H[k], A[k]) for k in H}


def apply(variant: str):
    if variant not in VARIANTS:
        raise ValueError(variant)
    L.rule_global, L.rule_cfar, L.hulls, R.hull_w = (_ORIG["rule_global"], _ORIG["rule_cfar"], _ORIG["hulls"],
                                                     _ORIG["hull_w"])
    if variant in ("conformal", "conformal_hull"):
        L.rule_global, L.rule_cfar = rule_global_conformal, rule_cfar_conformal
    if variant == "conformal_hull":
        L.hulls, R.hull_w = hulls_conformal, hull_conformal
    STATE["variant"] = variant
