"""Per-family breakdown of the chooser results (mean TPR gain over always-max per data family and chooser),
including the CUSUM arm whose k is tuned on the labeled calibration attacks, and which rules the empirical
chooser picks.

    uv run python tracks/r2_t1/chooser_families.py --tag all_lab20
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[2] / "results" / "r2_t1"


def fam(s):
    f = s.split(":")[0]
    return "akshn" if f.startswith("akshn") else f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="all_lab20")
    a = ap.parse_args()
    P = pd.read_csv(OUT / f"chooser_per_set_{a.tag}.csv")
    P["family"] = P.set.map(fam)
    ch = ["emp", "meta", "cusum_tuned", "always_cusum_k1.5", "always_cusum_k0.5", "always_top3sum", "always_kth2", "oracle"]
    T = P[P.chooser.isin(ch)].groupby(["alpha", "family", "chooser"]).agg(gain=("gain", "mean"), n=("set", "nunique"),
                                                                          tpr_max=("tpr_max", "mean"))
    T = T.reset_index().pivot_table(index=["alpha", "family"], columns="chooser", values="gain")[ch]
    n = P.groupby("family").set.nunique()
    picks = pd.read_csv(OUT.parents[1] / "data" / "raw" / "r2_t1" / "chooser_out" / f"chooser_picks_{a.tag}.csv")
    picks["family"] = picks.set.map(fam)
    pk = picks[picks.chooser == "emp"].groupby(["alpha", "family"]).rule.value_counts(normalize=True).unstack(fill_value=0)
    lines = [f"# Chooser by data family ({a.tag}): mean TPR gain over always-max", "",
             "| alpha | family (n sets) | " + " | ".join(c.replace("_", " ") for c in ch) + " |",
             "|" + "---|" * (len(ch) + 2)]
    for (al, f), r in T.iterrows():
        lines.append(f"| {al} | {f} ({n[f]}) | " + " | ".join(f"{v:+.3f}" for v in r.to_numpy()) + " |")
    lines += ["", "## Rules picked by the empirical chooser (share of splits)", "",
              "| alpha | family | " + " | ".join(pk.columns) + " |", "|" + "---|" * (len(pk.columns) + 2)]
    for (al, f), r in pk.iterrows():
        lines.append(f"| {al} | {f} | " + " | ".join(f"{v:.2f}" for v in r.to_numpy()) + " |")
    (OUT / f"chooser_families_{a.tag}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
