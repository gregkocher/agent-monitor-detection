"""Audit pass 3 (r4_wb Part 2, A1 table on the pilot MonitoringBench data): reader vs gpt-4.1-mini (same mode) at
nominal 1% and at TRULY equal realized FPR, plus a bootstrap-bias diagnostic for the percentile CIs.

Data loaders reused from tracks/audit2/repro_wb_mb.py (independent of the track code). Versions:
  nominal      -- both at 1%
  reader_floor -- reader nominal level bisected down to the LLM's realized FPR (or its floor)
  llm_raised   -- LLM nominal level raised until its realized FPR equals the reader's realized FPR at 1%
  both_exact   -- both bisected to realized FPR = 1.00%
Also the H1 replication data (held-out) for the bootstrap-bias diagnostic: bootstrap mean - point estimate and a
basic (pivotal) interval next to the percentile interval.
Outputs results/audit3/wb_a1_mb.csv.

    unset VIRTUAL_ENV; uv run python -m tracks.audit3.wb_a1
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tracks.audit2.repro_wb_mb import llm, reader, traj_meta

from .wb_la import level_for
from .wb_lib import boot_weights, contrast, halves, realized_fpr


def main():
    M = traj_meta()
    rows = []
    for mode in ("full", "none"):
        R, L = reader(mode), llm(mode, M)
        ids = sorted(set(R) & set(L))
        hid = [t for t in ids if M[t]["label"] == "honest"]
        aid = [t for t in ids if M[t]["label"] == "attack"]
        hg = np.array([M[t]["task"] for t in hid])
        ag = np.array([M[t]["task"] for t in aid])
        masks = halves(hg, 200, np.random.default_rng(31))
        Wh, Wa = boot_weights(hg, ag, 2000, np.random.default_rng(32), "indep")
        for st in ("fibs_fu_ax", "sab"):
            if mode == "none" and st == "sab":
                continue
            H = {"r": np.array([R[t][st] for t in hid]), "l": np.array([L[t][0] for t in hid])}
            A = {"r": np.array([R[t][st] for t in aid]), "l": np.array([L[t][0] for t in aid])}
            a = 0.01
            fr, fl = realized_fpr(H["r"], masks, a), realized_fpr(H["l"], masks, a)
            vers = {"nominal": (a, a), "reader_floor": (level_for(H["r"], masks, fl, hi=a), a),
                    "llm_raised": (a, level_for(H["l"], masks, fr)),
                    "both_exact": (level_for(H["r"], masks, a), level_for(H["l"], masks, a))}
            for v, (lr, ll) in vers.items():
                res = contrast(H, A, [(1.0, "r", lr), (-1.0, "l", ll)], masks, a, Wh, Wa)
                b = res["boot"]
                rows.append(dict(mode=mode, stream=st, version=v, n_h=len(hid), n_a=len(aid), level_reader=lr,
                                 level_llm=ll, fpr_reader=res["fpr"][("r", lr)], fpr_llm=res["fpr"][("l", ll)],
                                 tpr_reader=contrast(H, A, [(1.0, "r", lr)], masks, a)["est"],
                                 tpr_llm=contrast(H, A, [(1.0, "l", ll)], masks, a)["est"],
                                 est=res["est"], lo=res["lo"], hi=res["hi"], p_two=res["p_two"],
                                 boot_mean_minus_est=float(b.mean() - res["est"]),
                                 basic_lo=float(2 * res["est"] - np.quantile(b, .975)),
                                 basic_hi=float(2 * res["est"] - np.quantile(b, .025))))
                print({k: (round(x, 4) if isinstance(x, float) else x) for k, x in rows[-1].items()}, flush=True)
    pd.DataFrame(rows).to_csv("results/audit3/wb_a1_mb.csv", index=False)


if __name__ == "__main__":
    main()
