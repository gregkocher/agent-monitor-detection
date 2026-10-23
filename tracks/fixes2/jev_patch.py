"""Threshold-convention switch for the r5_jev analysis code (track files are not edited).

tracks/r5_jev/cascade.py and tracks/audit3/jev_indep.py carry their own weighted plug-in randomized thresholds
(`rand_threshold_rows` / `rthr` returning (h, gamma), applied by `alarm(S, h, g)`), which the
amd.evaluation.calibration convention flag does not reach. `use_convention("conformal")` monkeypatches both modules:
the threshold functions return (thr, thr) with thr = row_thresholds(Sc, Wc, alpha, "conformal_randomized") (smoothed
conformal p-value rule, masses = bootstrap multiplicities in trajectory units), and `alarm(S, h, g)` returns
h.alarm(S) when h is a RowThresholds (slicing h[:1] keeps working for the test-honest realized FPR).
`use_convention("plugin")` leaves the committed code untouched (reproduction of the old numbers).

Not switched (deliberately): the escalation threshold (cascade.escalation_rank / jev_indep.Casc.esc_thr). It is a
step-level escalation BUDGET (weighted share of calibration-honest steps escalated <= e), not a trajectory-level
false-positive-rate guarantee, and both compared arms in every contrast use the same rule.
"""
from __future__ import annotations

import numpy as np

from amd.evaluation.calibration import RowThresholds, row_thresholds

import tracks.audit3.jev_indep as JI
import tracks.r5_jev.cascade as C

_ORIG = dict(c_thr=C.rand_threshold_rows, c_alarm=C.alarm, i_thr=JI.rthr, i_alarm=JI.alarm)


def conformal_rows(S, W, alpha):
    S = np.asarray(S, float)
    W = np.asarray(W, float)
    if S.ndim == 2 and S.shape[0] > 1 and S.strides[0] == 0:      # broadcast (plain monitor): shared statistics
        thr = row_thresholds(S[0], W, alpha, "conformal_randomized")
    else:
        thr = row_thresholds(S, W, alpha, "conformal_randomized")
    return thr, thr


def _alarm_factory(orig):
    def alarm(S, h, g):
        if isinstance(h, RowThresholds):
            return h.alarm(S)
        return orig(S, h, g)
    return alarm


def use_convention(name: str):
    if name == "plugin":
        C.rand_threshold_rows, C.alarm = _ORIG["c_thr"], _ORIG["c_alarm"]
        JI.rthr, JI.alarm = _ORIG["i_thr"], _ORIG["i_alarm"]
    elif name == "conformal":
        C.rand_threshold_rows, C.alarm = conformal_rows, _alarm_factory(_ORIG["c_alarm"])
        JI.rthr, JI.alarm = conformal_rows, _alarm_factory(_ORIG["i_alarm"])
    else:
        raise ValueError(name)
