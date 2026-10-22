"""Audit C1 follow-up for r3_t2 (Watcher-like severity tiers): the tables use r2lib.nominal_and_matched, which
CLAMPS the interpolation when the target spend B is outside a replicate's swept spend range. Re-summarize the
saved replicates (data/processed/r3_t2_runs/watcher.parquet) counting a 'matched' metric only where that
replicate is matched (matched_ok), and compare rule - global only over replicates where BOTH are matched.

    unset VIRTUAL_ENV; uv run python -m tracks.audit2.r3t2_matched_check
"""
from __future__ import annotations

import numpy as np
import pandas as pd

KEYS = ["panel", "B", "rule"]


def main():
    d = pd.read_parquet("data/processed/r3_t2_runs/watcher.parquet")
    d = d[(d["mode"] == "matched") & (d.kind == "plain")]
    if "beta" in d:
        pass
    g = d[d.rule == "global"].set_index(["panel", "B", "rep"])
    rows = []
    for (panel, B, rule), x in d.groupby(KEYS):
        x = x.set_index("rep")
        gg = g.loc[(panel, B)] if (panel, B) in g.index.droplevel(2) else None
        both = x.matched_ok.astype(bool)
        if gg is not None:
            both = both & gg.matched_ok.reindex(x.index).astype(bool)
        rec = dict(panel=panel, B=B, rule=rule, share_matched=x.matched_ok.mean(),
                   spend_all=x.spend.mean(), dmg_uniform_all=x.dmg_uniform.mean(),
                   dmg_uniform_matched_only=x.dmg_uniform[x.matched_ok.astype(bool)].mean(),
                   sel_org_all=x.sel_org.mean(), sel_org_matched_only=x.sel_org[x.matched_ok.astype(bool)].mean())
        if gg is not None and rule != "global":
            dd = x.dmg_uniform - gg.dmg_uniform.reindex(x.index)
            rec.update(d_dmg_vs_global_all=dd.mean(), d_dmg_vs_global_both_matched=dd[both].mean(),
                       n_both_matched=int(both.sum()), n_reps=len(x))
        rows.append(rec)
    out = pd.DataFrame(rows)
    out.to_csv("results/audit2/r3t2_matched_check.csv", index=False)
    pd.set_option("display.width", 250)
    print(out[out.panel.isin(["mb_mini", "mb_strong"])].round(3).to_string())


if __name__ == "__main__":
    main()
