"""Trajectory decision statistics over per-unit monitor score streams.

Every detector: `fit(honest_streams, contexts=None, attack_streams=None, ...)`,
`stat_path(stream)`, `stat(stream)`, and vectorized `stats(streams)` / `stat_paths(streams)`.
See docs/detectors.md.
"""
from .aggregators import CountAbove, KthLargest, LengthAwareMax, Max, Mean, TopKSum
from .base import Detector, Identity, Packed, Transform, concat_packed, pack
from .eprocess import ConformalEProcess, EDetectorSR, log_evalues
from .multichart import MultiChart
from .sequential import CUSUM, LLRCUSUM, LRMax, ShiryaevRoberts, WindowGLR
from .transforms import KDELogLR, PValue, UnitCalibrator, Whiten

__all__ = [
    "Detector", "Transform", "Identity", "Packed", "pack", "concat_packed",
    "Max", "Mean", "KthLargest", "TopKSum", "CountAbove", "LengthAwareMax",
    "CUSUM", "ShiryaevRoberts", "WindowGLR", "LLRCUSUM", "LRMax",
    "ConformalEProcess", "EDetectorSR", "log_evalues", "MultiChart",
    "UnitCalibrator", "PValue", "Whiten", "KDELogLR",
    "default_suite",
]


def default_suite(supervised: bool = False, mondrian: bool = False) -> dict:
    """The standard set of detectors for matched-budget comparisons (name -> unfitted detector).

    mondrian=True whitens / computes p-values per context (requires contexts).
    """
    wk = dict(mondrian=mondrian)
    suite = [
        Max(), Mean(), KthLargest(2), KthLargest(3), TopKSum(3, transform=Whiten(**wk)),
        TopKSum(5, transform=Whiten(**wk)), CountAbove(0.95),
        CUSUM(k=0.5, transform=Whiten(**wk)), CUSUM(k=0.25, transform=Whiten(**wk)),
        ShiryaevRoberts(delta=1.0, transform=Whiten(**wk)),
        WindowGLR(window=20, transform=Whiten(**wk)),
        ConformalEProcess("power", **wk), ConformalEProcess("jumper", **wk),
        EDetectorSR("power", **wk),
        LengthAwareMax(),
    ]
    if mondrian:
        suite.insert(1, Max(transform=Whiten(mondrian=True)))
        suite[1].name = "max_mondrian"
    suite.append(MultiChart([Max(transform=Whiten(**wk)), CUSUM(k=0.5, transform=Whiten(**wk)),
                             ConformalEProcess("power", **wk)], name="or(max+cusum+eproc)"))
    if supervised:
        suite += [LRMax(), LLRCUSUM(clip=3.0)]
    out = {}
    for d in suite:
        assert d.name not in out, d.name
        out[d.name] = d
    return out
