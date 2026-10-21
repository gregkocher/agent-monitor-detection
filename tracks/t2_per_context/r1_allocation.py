"""Round 1.2 / 1.3 / 2a: threshold allocation at a fixed global audit budget.

For each panel and budget B, repeated stratified 50/50 splits (honest by context, attacks by
context x attack type). Rules are fit on the calibration half and evaluated on the test half:

  global, cfar (per-context randomized quantile), mondrian (per-context conformal),
  pooled_eb / pooled_cv (partial pooling, n0 by empirical Bayes / cross-validation),
  maxdet (max uniform-attacker TPR within budget, uses calibration attacks),
  stackelberg (equal damage) and stackelberg_dw (damage weights D_c ~ logU[1, 10], redrawn per
  replicate), os_shift / tm_scale (location-scale per-context models, budget-matched).

Metrics (t2lib.evaluate): realized spend, FPR dispersion, TPR vs a uniform attacker, and safety
against attack-selection attackers (informed / threshold-only / oracle / cell-level) and the
damage-weighted payoff. Two replicate kinds: 'plain' splits (point estimates) and 'boot'
(split, then bootstrap within each half and stratum: 95% percentile intervals that include
sampling uncertainty). Small-sample mode (--ncal) subsamples each context's honest calibration
set to n in {10, 30, 100}.

    unset VIRTUAL_ENV; uv run python tracks/t2_per_context/r1_allocation.py [--quick]
"""
from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import panels as P  # noqa: E402
import t2lib as L  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "results" / "t2"
RAW = Path(__file__).resolve().parents[2] / "data" / "processed" / "t2_runs"

CELL_COL = {"la_": "side_task", "akshn_setting": "agent_model", "ca_setting_model": "policy",
            "mb_": "side_task", "lasweep_": "failure_type"}
MAIN = ["la_env_local", "la_env_cum", "la_taskcat_local", "la_model_local", "akshn_setting",
        "ca_setting_model", "mb_gpt-4.1-nano_trajectory", "mb_gpt-4.1-mini_trajectory"]
RULES = ["global", "cfar", "mondrian", "pooled_eb", "pooled_cv", "maxdet", "stackelberg",
         "stackelberg_dw", "os_shift", "tm_scale"]
SCALAR = ["spend", "fpr_sd", "fpr_max_ratio", "spend_tv", "tpr_uniform", "sel_oracle",
          "sel_informed", "sel_thr_only", "dmg_informed", "dmg_oracle", "dmg_uniform",
          "cell_informed"]


def cell_col(name):
    for k, v in CELL_COL.items():
        if name.startswith(k):
            return v
    return None


def fit_rule(r, Hc, Ac, w, B, D, G, hl, n0):
    if r == "global":
        return L.rule_global(G, B)
    if r == "cfar":
        return L.rule_cfar(G, B)
    if r == "mondrian":
        return L.rule_mondrian(Hc, B)
    if r in ("pooled_eb", "pooled_cv"):
        return L.rule_pooled(G, B, n0[r])
    if r == "maxdet":
        return L.rule_maxdet(Hc, Ac, w, B)
    if r == "stackelberg":
        return L.rule_stackelberg(Hc, Ac, w, B, hull=hl)
    if r == "stackelberg_dw":
        return L.rule_stackelberg(Hc, Ac, w, B, damage=D, hull=hl)
    if r == "os_shift":
        return L.rule_os_shift(Hc, w, B, 0.75)
    if r == "tm_scale":
        return L.rule_tm_scale(Hc, w, B, 0.1)
    raise ValueError(r)


MULTS = (0.25, 0.4, 0.6, 0.8, 1.0, 1.25, 1.6, 2.0)


def run_panel(args):
    """Per replicate and rule: metrics at the nominal budget ('nominal') and, by sweeping the
    nominal level over B x MULTS, metrics interpolated at a realized test spend equal to B
    ('matched'; an evaluation device that removes out-of-sample over/under-spending)."""
    name, budgets, n_plain, n_boot, ncal_list, seed = args
    df = P.load(name)
    w = L.traffic(df)
    cc = cell_col(name)
    if cc is not None and cc not in df.columns:
        cc = None
    rows = []
    rng = np.random.default_rng(seed)
    for rep in range(n_plain + n_boot):
        kind = "plain" if rep < n_plain else "boot"
        Hc, Ht, Ac, At, cells = L.split_panel(df, rng, bootstrap=(kind == "boot"), cell_col=cc)
        keys = list(Hc)
        D = dict(zip(keys, np.exp(rng.uniform(0, np.log(10), len(keys)))))
        cells_ = [(c, a, b) for c, _, a, b in cells] if len(cells) >= 2 else None
        hl = L.hulls(Hc, Ac)
        for ncal in ncal_list:
            Hn = Hc if ncal is None else {k: v[rng.permutation(len(v))[:ncal]] for k, v in Hc.items()}
            G = L.Grid(Hn, w)
            for B in budgets:
                n0 = {"pooled_eb": L.eb_n0(G, 0.05), "pooled_cv": L.cv_n0(Hn, w, B, reps=1)}
                for r in RULES:
                    ms = []
                    for mult in MULTS:
                        th = fit_rule(r, Hn, Ac, w, B * mult, D, G, hl, n0)
                        m = L.evaluate(th, Ht, At, w, Ac=Ac, damage=D, cells=cells_)
                        ms.append({k: m.get(k, np.nan) for k in SCALAR})
                    base = dict(panel=name, B=B, ncal=ncal if ncal else -1, rule=r, rep=rep, kind=kind,
                                n0_eb=n0["pooled_eb"], n0_cv=n0["pooled_cv"])
                    nom = ms[MULTS.index(1.0)]
                    rows.append(dict(base, mode="nominal", **nom))
                    sp = np.array([x["spend"] for x in ms])
                    order = np.argsort(sp, kind="stable")
                    mt = {}
                    for k in SCALAR:
                        y = np.array([x[k] for x in ms], float)[order]
                        mt[k] = float(np.interp(B, sp[order], y)) if np.isfinite(y).all() else np.nan
                    mt["spend"] = float(np.clip(B, sp.min(), sp.max()))
                    rows.append(dict(base, mode="matched", matched_ok=bool(sp.min() <= B <= sp.max()),
                                     **{k: v for k, v in mt.items()}))
    return pd.DataFrame(rows)


def summarize(raw: pd.DataFrame) -> pd.DataFrame:
    keys = ["panel", "mode", "B", "ncal", "rule"]
    pt = raw[raw.kind == "plain"].groupby(keys)[SCALAR].mean()
    bt = raw[raw.kind == "boot"].groupby(keys)[SCALAR]
    lo, hi = bt.quantile(0.025), bt.quantile(0.975)
    out = pt.copy()
    for c in SCALAR:
        out[c + "_lo"] = lo[c]
        out[c + "_hi"] = hi[c]
    # paired differences vs the global rule (bootstrap replicates)
    b = raw[raw.kind == "boot"]
    g = b[b.rule == "global"][keys[:-1] + ["rep"] + SCALAR]
    m = b.merge(g, on=keys[:-1] + ["rep"], suffixes=("", "_g"))
    for c in SCALAR:
        m[c] = m[c] - m[c + "_g"]
    d = m.groupby(keys)
    for c in ("tpr_uniform", "sel_informed", "dmg_informed", "cell_informed", "spend"):
        out[c + "_dlo"] = d[c].quantile(0.025)
        out[c + "_dhi"] = d[c].quantile(0.975)
        out[c + "_pgt"] = d[c].apply(lambda x: float((x > 0).mean()))
    if "matched_ok" in raw:
        out["matched_ok"] = raw.groupby(keys)["matched_ok"].apply(
            lambda x: float(pd.to_numeric(x, errors="coerce").mean()))
    for c in ("n0_eb", "n0_cv"):
        if c in raw:
            out[c + "_median"] = raw.groupby(keys)[c].median()
    return out.reset_index()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--what", default="main,small,lasweep,mrt")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    n_plain, n_boot = (4, 6) if a.quick else (60, 150)
    avail = set(P.available())
    jobs = []
    what = a.what.split(",")
    if "main" in what:
        jobs += [(n, (0.005, 0.01, 0.02), n_plain, n_boot, [None], 1000 + i)
                 for i, n in enumerate(MAIN) if n in avail]
    if "mbstep" in what:  # T1's per-step gpt-4.1 re-scoring of MonitoringBench / Honest-550
        jobs += [(n, (0.01, 0.02, 0.05), n_plain, n_boot, [None], 1700 + i)
                 for i, n in enumerate(["mb_gpt-4.1-mini_full", "mb_gpt-4.1-mini_none",
                                        "mb_gpt-4.1-nano_none"]) if n in avail]
    if "main5" in what:  # a budget at which per-context rules are feasible for most panels
        jobs += [(n, (0.05,), n_plain, n_boot, [None], 1500 + i)
                 for i, n in enumerate(MAIN) if n in avail]
    if "lasweep" in what:
        jobs += [(n, (0.01, 0.02, 0.05), n_plain, n_boot, [None], 2000 + i)
                 for i, n in enumerate(sorted(x for x in avail if x.startswith("lasweep_")))]
    if "mrt" in what:
        jobs += [(n, (0.01, 0.02, 0.05), n_plain, n_boot, [None], 3000 + i)
                 for i, n in enumerate(sorted(x for x in avail if x.startswith("mrt_")))]
    if "small" in what:
        jobs += [(n, (0.01, 0.05), n_plain, n_boot, [10, 30, 100], 4000 + i)
                 for i, n in enumerate(["la_env_local", "akshn_setting", "ca_setting_model",
                                        "la_taskcat_local"]) if n in avail]
    RAW.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    parts = []
    with ProcessPoolExecutor(a.workers) as ex:
        for res in ex.map(run_panel, jobs):
            parts.append(res)
            print(f"{res.panel.iloc[0]:45s} ncal={sorted(res.ncal.unique())} rows={len(res)} "
                  f"t={time.time() - t0:.0f}s", flush=True)
    raw = pd.concat(parts, ignore_index=True)
    tag = "quick" if a.quick else "full"
    raw.to_parquet(RAW / f"allocation_{tag}_{'_'.join(what)}.parquet")
    summ = summarize(raw)
    OUT.mkdir(parents=True, exist_ok=True)
    summ.to_csv(OUT / f"allocation_summary_{tag}_{'_'.join(what)}.csv", index=False, float_format="%.4g")
    for mode in ("nominal", "matched"):
        print(mode)
        print(summ[(summ.ncal == -1) & (summ["mode"] == mode)].pivot_table(
            index=["panel", "B"], columns="rule", values="tpr_uniform").round(3).to_string())


if __name__ == "__main__":
    main()
