"""Shared figure style for T2 (vector PDF, one categorical order for every figure)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

# fixed color per allocation rule (color follows the entity across all figures)
RULE_COLOR = {
    "global": SERIES[0], "cfar": SERIES[1], "mondrian": SERIES[2], "pooled_eb": SERIES[3],
    "pooled_cv": SERIES[4], "maxdet": SERIES[5], "stackelberg": SERIES[6], "stackelberg_dw": SERIES[7],
}
RULE_LABEL = {
    "global": "Global", "cfar": "CFAR (per-context quantile)", "mondrian": "Mondrian conformal",
    "pooled_eb": "Partial pooling (EB n0)", "pooled_cv": "Partial pooling (CV n0)",
    "maxdet": "Max-detection allocation", "stackelberg": "Stackelberg (equal damage)",
    "stackelberg_dw": "Stackelberg (damage-weighted)",
}
DEF_COLOR = {  # poisoning defenses
    "global": SERIES[0], "cfar": SERIES[1], "pooled_eb": SERIES[3], "os_shift": SERIES[2],
    "tm_scale": SERIES[4], "refmix": SERIES[5], "frozen": SERIES[6], "cap": SERIES[7],
}
DEF_LABEL = {
    "global": "Global", "cfar": "CFAR (plain)", "pooled_eb": "Partial pooling (EB)",
    "os_shift": "OS-CFAR (p75 offset, LOCO tail)", "tm_scale": "TM-CFAR (10% trim, LOCO tail)",
    "refmix": "CFAR on 50/50 trusted-reference mix", "frozen": "Frozen trusted reference",
    "cap": "CFAR + drift cap",
}


def setup():
    plt.rcParams.update({
        "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5, "legend.fontsize": 7.5,
        "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "axes.edgecolor": INK2,
        "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
        "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.6,
        "lines.markersize": 4.5, "legend.frameon": False, "pdf.fonttype": 42, "ps.fonttype": 42,
        "figure.dpi": 150, "savefig.bbox": "tight", "font.family": "DejaVu Sans",
    })


def save(fig, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
