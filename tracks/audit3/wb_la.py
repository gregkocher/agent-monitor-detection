"""Audit pass 3 (r4_wb Part 2): LinuxArena reader (FIBS axial follow-up, `full`) vs the 12 sweep monitors at
nominal AND equal realized FPR, independent of the track code.

Reader stream recomputed from data/processed/whitebox/scores/r4/la_full.jsonl (fu_ax_no - fu_ax_yes); LLM streams
from data/processed/linuxarena_sweep/scores.jsonl (unit step); hidden-tool steps NaN for both; trajectory max.
Per comparator: trajectories both scored; 200 random halves of the honest tasks (1 honest per task => iid).
Versions per alpha in {0.01, 0.05}:
  nominal        -- both at nominal alpha (as committed)
  llm_raised     -- LLM nominal level raised (bisection) until its split-mean realized FPR equals the reader's
                    realized FPR at nominal alpha (equal realized FPR at the reader's budget)
  reader_floor   -- reader lowered toward its realized-FPR floor (bisection to the LLM's realized FPR; reported with
                    the FPR actually achieved)
  both_exact     -- both monitors' nominal levels bisected so each realized FPR equals alpha exactly
  both_2pct      -- (alpha 0.01 family only) both bisected to realized FPR 2.0%, the operating point the committed
                    plug-in rule actually gave the reader (2/101 at n_cal = 100; see wb_convention.py)
Holm over the 12 comparators within each (version, alpha). Bootstrap: independent honest / attack task clusters,
calibration noise, B replicates. Outputs results/audit3/wb_la_equalfpr.csv.

    unset VIRTUAL_ENV; uv run python -m tracks.audit3.wb_la [--B 2000]
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from .wb_lib import boot_weights, contrast, halves, holm, read_jsonl, realized_fpr

P = "data/processed"


def level_for(hs, masks, target, lo=1e-6, hi=0.3, iters=40):
    """Largest nominal level with split-mean realized FPR <= target."""
    if realized_fpr(hs, masks, lo) > target:
        return lo
    for _ in range(iters):
        mid = (lo + hi) / 2
        if realized_fpr(hs, masks, mid) <= target + 1e-12:
            lo = mid
        else:
            hi = mid
    return lo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--splits", type=int, default=200)
    a = ap.parse_args()
    meta = {d["traj_id"]: dict(label=d["label"], task=str(d["meta"]["task_id"]),
                               hidden=d["meta"].get("hidden_tool_steps", [])) for d in read_jsonl(f"{P}/whitebox/inputs/la.jsonl")}

    def tmax(t, s):
        s = np.asarray([np.nan if v is None else v for v in s], float).copy()
        hid = [i for i in meta[t]["hidden"] if i < len(s)]
        s[hid] = np.nan
        return np.nanmax(s) if np.isfinite(s).any() else np.nan

    R = {}
    for d in read_jsonl(f"{P}/whitebox/scores/r4/la_full.jsonl"):
        if d["n_steps"]:
            x = np.asarray(d["feats"]["fu_ax_no"], float) - np.asarray(d["feats"]["fu_ax_yes"], float)
            R[d["traj_id"]] = tmax(d["traj_id"], x)
    L = {}
    for d in read_jsonl(f"{P}/linuxarena_sweep/scores.jsonl"):
        if d["unit"] == "step":
            L.setdefault(d["monitor_id"].split("|")[0], {})[d["traj_id"]] = tmax(d["traj_id"], d["scores"])
    rows = []
    for mon in sorted(L):
        ids = sorted(t for t in R if t in L[mon] and np.isfinite(R[t]) and np.isfinite(L[mon][t]))
        hid = [t for t in ids if meta[t]["label"] == "honest"]
        aid = [t for t in ids if meta[t]["label"] == "attack"]
        hg = np.array([meta[t]["task"] for t in hid])
        ag = np.array([meta[t]["task"] for t in aid])
        H = {"r": np.array([R[t] for t in hid]), "l": np.array([L[mon][t] for t in hid])}
        A = {"r": np.array([R[t] for t in aid]), "l": np.array([L[mon][t] for t in aid])}
        masks = halves(hg, a.splits, np.random.default_rng(2026))
        Wh, Wa = boot_weights(hg, ag, a.B, np.random.default_rng(99), "indep")
        for alpha in (0.01, 0.05):
            fr = realized_fpr(H["r"], masks, alpha)
            fl = realized_fpr(H["l"], masks, alpha)
            versions = {
                "nominal": (alpha, alpha),
                "llm_raised": (alpha, level_for(H["l"], masks, fr)),
                "reader_floor": (level_for(H["r"], masks, fl), alpha),
                "both_exact": (level_for(H["r"], masks, alpha), level_for(H["l"], masks, alpha)),
            }
            if alpha == 0.01:  # the realized FPR the committed rule gave the reader (about 2/101)
                versions["both_2pct"] = (level_for(H["r"], masks, 0.02), level_for(H["l"], masks, 0.02))
            for v, (lr, ll) in versions.items():
                res = contrast(H, A, [(1.0, "r", lr), (-1.0, "l", ll)], masks, alpha, Wh, Wa)
                tr = contrast(H, A, [(1.0, "r", lr)], masks, alpha)["est"]
                tl = contrast(H, A, [(1.0, "l", ll)], masks, alpha)["est"]
                rows.append(dict(llm=mon, alpha=alpha, version=v, n_h=len(hid), n_a=len(aid), level_reader=lr,
                                 level_llm=ll, fpr_reader=res["fpr"][("r", lr)], fpr_llm=res["fpr"][("l", ll)],
                                 tpr_reader=tr, tpr_llm=tl, est=res["est"], lo=res["lo"], hi=res["hi"],
                                 p_two=res["p_two"], n_cal_mean=float(np.mean([m.sum() for m in masks])),
                                 reader_fpr_floor=realized_fpr(H["r"], masks, 1e-6),
                                 llm_fpr_floor=realized_fpr(H["l"], masks, 1e-6)))
                print({k: (round(x, 4) if isinstance(x, float) else x) for k, x in rows[-1].items()}, flush=True)
    df = pd.DataFrame(rows)
    for _, g in df.groupby(["version", "alpha"]):
        df.loc[g.index, "p_holm"] = holm(g.p_two.values)
    df.to_csv("results/audit3/wb_la_equalfpr.csv", index=False)


if __name__ == "__main__":
    main()
