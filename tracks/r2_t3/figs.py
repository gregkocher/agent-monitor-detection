"""Figures for round-2 T3 (vector PDF, consistent style)."""
from __future__ import annotations

import numpy as np

ARM_COLOR = {"nothing": "#5B6670", "r1_max": "#8EC6F0", "r1_cusum": "#F0B98E", "r1_multichart": "#9FD4B4",
             "pace_max": "#2F7DD1", "pace_cusum": "#E07B2F", "pace_multichart": "#2E8B57"}
DET_LS = {"max": "-", "cusum0.5": "--", "sr_d1": "-.", "multichart": ":"}


def style():
    import matplotlib as mpl
    mpl.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 120, "font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True, "grid.alpha": .25,
                         "figure.autolayout": True, "pdf.fonttype": 42, "ps.fonttype": 42})
    return plt


def fig_covert(sweeps: dict, out_path):
    """Left: mean attack-critical steps before alarm vs ARL (log-log) with a sqrt(ARL) guide.
    Right: fraction of attacks that complete every attack-critical step without any alarm."""
    sweeps = {k: v for k, v in sweeps.items() if v.get("arls")}
    if not sweeps:
        return
    plt = style()
    fig, (ax1, ax2) = pl