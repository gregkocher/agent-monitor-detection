"""Paired comparisons on MonitoringBench with the corrected joint bootstrap
(`amd.evaluation.paired.paired_contrast_bootstrap`: one task-cluster resample per replicate shared by every
split and term; honest calibration resampled and thresholds recomputed; attacks clustered by task).

  gain_vs_max  TPR(detector) - TPR(max) per stream and mode (accumulation vs max)
  vs_llm       TPR(stream, det) - TPR(gpt-4.1-mini, det), same mode, det in {max, top3sum, OR(max+CUSUM)}
  did          [gain(det over max) in none] - [same in full], per stream (history-aware vs history-free)
  strata       absolute TPR of max, and stream - LLM, by attack agent model (Honest-550 is all
               claude-opus-4-5; 36% of the attacks are claude-opus-4-6; audit M9)

Requires analyze_mb raw pickles (identical splits for every stream/mode; checked by the bootstrap).

    uv run python -m tracks.wb_whitebox.analyze_paired [--B 1000]
"""
from __future__ import annotations

import argparse
import pickle

import numpy as np
import pandas as pd

from amd.common.schema import REPO, load_trajectories
from amd.evaluation.paired import paired_contrast_bootstrap

from .wblib import WB

OUT = REPO / "results" / "wb"
ALPHAS = (0.05, 0.01, 0.003)
DETS = ["kth2", "top3sum", "cusum_k0.5", "cusum_k1", "cusum_k1.5", "cusum_k2", "eproc_power", "or(max+cusum)",
        "max_lenaware"]
MAIN = ["llm", "sab", "sab_max", "dec", "fibs_tok", "fibs_fu", "fibs_fu_ax", "jl_lm", "jl_lm_max", "jl_hits", "sup"]


def load(tag="mb"):
    R, meta = {}, None
    for p in sorted((WB / "raw").glob(f"{tag}_*.pkl")):
        _, mode, stream = p.stem.split("_", 2)
        d = pickle.load(open(p, "rb"))
        R[(mode, stream)] = d["raw"]
        if meta is None:
            meta = d
        else:
            assert d["honest_ids"] == meta["honest_ids"] and d["attack_ids"] == meta["attack_ids"], p
    return R, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--B", type=int, default=1000)
    a = ap.parse_args()
    R, meta = load()
    hg, ag = meta["honest_groups"], meta["attack_groups"]
    nh, na = len(hg), len(ag)
    kw = dict(n_honest=nh, n_attack=na, honest_groups=hg, attack_groups=ag, n_boot=a.B)
    dets_of = {k: {r["detector"] for r in raw} for k, raw in R.items()}
    rows = []

    def add(kind, alpha, mode, stream, det, ref, terms, **extra):
        r = paired_contrast_bootstrap(terms, alpha=alpha, seed=7, **kw, **extra)
        rows.append(dict(kind=kind, alpha=alpha, mode=mode, stream=stream, detector=det, ref=ref,
                         est=r["est"], lo=r["lo"], hi=r["hi"], p_le0=r["p_le0"]))

    streams = sorted({st for _, st in R})
    for alpha in ALPHAS:
        for mode in ("full", "none"):
            for st in streams:
                raw = R.get((mode, st))
                if raw is None:
                    continue
                for d in DETS:
                    if d in dets_of[(mode, st)]:
                        add("gain_vs_max", alpha, mode, st, d, "max", [(1.0, raw, d), (-1.0, raw, "max")])
                if st != "llm" and (mode, "llm") in R:
                    for d in ("max", "top3sum", "or(max+cusum)"):
                        add("vs_llm", alpha, mode, st, d, f"llm:{d}", [(1.0, raw, d), (-1.0, R[(mode, "llm")], d)])
                add("tpr", alpha, mode, st, "max", "", [(1.0, raw, "max")])
        for st in streams:
            if (("none", st) in R) and (("full", st) in R):
                for d in ("top3sum", "cusum_k0.5", "cusum_k1.5"):
                    rn, rf = R[("none", st)], R[("full", st)]
                    add("did_none_minus_full", alpha, "both", st, d, "max",
                        [(1.0, rn, d), (-1.0, rn, "max"), (-1.0, rf, d), (1.0, rf, "max")])
                add("none_minus_full_max", alpha, "both", st, "max", "", [(1.0, R[("none", st)], "max"),
                                                                       (-1.0, R[("full", st)], "max")])
        print("alpha", alpha, len(rows), flush=True)
        pd.DataFrame(rows).to_csv(OUT / "mb_paired.csv", index=False)
    # agent-model strata (audit M9)
    TA = {t.traj_id: t.context.get("agent_model") for t in load_trajectories("monitoringbench")}
    am = np.array([TA[t] for t in meta["attack_ids"]])
    strata = []
    for alpha in (0.05, 0.01):
        for model in sorted(set(am)):
            mask = am == model
            for mode in ("full", "none"):
                for st in MAIN:
                    raw = R.get((mode, st))
                    if raw is None:
                        continue
                    r = paired_contrast_bootstrap([(1.0, raw, "max")], alpha=alpha, seed=7, attack_mask=mask, **kw)
                    rec = dict(alpha=alpha, agent_model=model, n_attacks=int(mask.sum()), mode=mode, stream=st,
                               tpr=r["est"], tpr_lo=r["lo"], tpr_hi=r["hi"])
                    if st != "llm":
                        d = paired_contrast_bootstrap([(1.0, raw, "max"), (-1.0, R[(mode, "llm")], "max")],
                                                      alpha=alpha, seed=7, attack_mask=mask, **kw)
                        rec.update(vs_llm=d["est"], vs_llm_lo=d["lo"], vs_llm_hi=d["hi"])
                    strata.append(rec)
    pd.DataFrame(strata).to_csv(OUT / "mb_strata_agent_model.csv", index=False)
    d = pd.DataFrame(rows)
    print(d.query("alpha == 0.01 and kind == 'vs_llm' and detector == 'max'").round(3).to_string())


if __name__ == "__main__":
    main()
