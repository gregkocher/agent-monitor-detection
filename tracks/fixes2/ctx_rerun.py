"""Re-run of the per-context allocation headlines under the conformal randomized-threshold convention.

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.ctx_rerun [--part r4|t2|all] [--R 200] [--workers 14]

Part r4 -- r4_ctx primary (akshn_setting, B = 1%, in-distribution, exact test-spend matching): selection safety
Stackelberg (equal damage, m0 = 10) - global, with the committed trajectory-level cluster bootstrap and with the
audit-3 main-task cluster bootstrap (tracks/audit3/ctx_checks.py). Same splits, seeds and code as
tracks/r4_ctx/run_r4.py / tracks/audit3/ctx_checks.py; only the threshold rule is switched (tracks/fixes2/ctx_lib.py).

Part t2 -- Idea 2 overview (track t2_per_context round 1, `main5` job: B = 5%, 60 plain + 150 bootstrap splits,
spend matched by interpolation over the level sweep B x MULTS on the test half): selection safety
Stackelberg - global and CFAR - global on akshn_setting (7 settings) and ControlArena (ca_setting_model). Same seeds
(1500 + index in r1_allocation.MAIN) and code (r1_allocation.run_panel / summarize); rules restricted to
global / cfar / stackelberg (no other rule draws randomness, so the restriction does not change these rows).

Variants (ctx_lib.apply): plugin (committed; reproduces the old numbers), conformal (randomized-quantile rules
switched), conformal_hull (also the Stackelberg ROC-hull FPRs).
Outputs results/fixes2/ctx_*_thrfix.csv.
"""
from __future__ import annotations

import argparse
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from tracks.fixes2 import ctx_lib as C

ROOT = C.ROOT
OUT = ROOT / "results" / "fixes2"
_G: dict = {}


# ------------------------------------------------------------------------------------------------
# part r4
# ------------------------------------------------------------------------------------------------


def _init_r4(variant, U, splits, W):
    C.apply(variant)
    _G.update(U=U, splits=splits, W=W)


def _task_r4(args):
    import r4lib as X
    s, reps = args
    U, sp, W = _G["U"], _G["splits"][s], _G["W"]
    out = []
    for r in reps:
        rows = X.run_cell(U, sp, None if r < 0 else W[r], (0.01,), rules=("global", "stack"), seed=1000 * s + r + 1)
        for row in rows:
            row.update(split=s, rep=r)
        out.extend(rows)
    return out


def run_r4(variant, boot, S, R_, workers):
    import panels_r4 as P
    import r4lib as X
    from tracks.audit3.ctx_checks import task_boot_weights
    df = P.load("akshn_setting")
    U = X.Universe(df)
    seed = zlib.crc32(b"akshn_setting|indist")  # = run_r4.run_job seed
    rng = np.random.default_rng(seed)
    splits = [X.make_split(U, rng, None) for _ in range(S)]
    brng = np.random.default_rng(seed + 1)
    W = U.boot_weights(R_, brng) if boot == "trajectory" else task_boot_weights(U, R_, brng)
    tasks = [(s, [-1]) for s in range(S)] + [(s, list(range(i, min(i + 10, R_)))) for s in range(S)
                                             for i in range(0, R_, 10)]
    rows = []
    with ProcessPoolExecutor(workers, initializer=_init_r4, initargs=(variant, U, splits, W)) as ex:
        for res in ex.map(_task_r4, tasks):
            rows.extend(res)
    raw = pd.DataFrame(rows)
    raw.insert(0, "boot", boot)
    raw.insert(0, "variant", variant)
    return raw


def summarize_r4(raw):
    out = []
    for (variant, boot), x in raw.groupby(["variant", "boot"], sort=False):
        piv = x.pivot_table(index=["split", "rep"], columns="rule", values="sel_informed")
        d = (piv["stack"] - piv["global"]).reset_index()
        pt = d[d.rep < 0][0].mean()
        rb = d[d.rep >= 0].groupby("rep")[0].mean()
        row = dict(variant=variant, boot=boot, contrast="stack - global", metric="sel_informed", est=pt,
                   lo=rb.quantile(.025), hi=rb.quantile(.975), p_pos=float((rb > 0).mean()), replicate_mean=rb.mean())
        for r in ("global", "stack"):
            y = x[x.rule == r]
            pl = y[y.rep < 0]
            row[f"{r}_sel"] = pl.sel_informed.mean()
            row[f"{r}_share_matched"] = y.matched_ok.mean()
            row[f"{r}_floor_mean"] = y.floor.mean()
            row[f"{r}_realized_spend_mean"] = pl.realized.mean()   # matched policy, test honest half
            row[f"{r}_realized_dev_max"] = float(np.nanmax(np.abs(y.realized - 0.01)))
            row[f"{r}_nominal_spend_mean"] = pl.nom_spend.mean()   # deployable fit at level B, no matching
            row[f"{r}_nominal_sel"] = pl.nom_sel_informed.mean()
        piv = x.pivot_table(index=["split", "rep"], columns="rule", values="nom_sel_informed")
        d = (piv["stack"] - piv["global"]).reset_index()
        rb = d[d.rep >= 0].groupby("rep")[0].mean()
        row.update(nominal_d=d[d.rep < 0][0].mean(), nominal_dlo=rb.quantile(.025), nominal_dhi=rb.quantile(.975))
        out.append(row)
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------
# part t2 (round 1, main5)
# ------------------------------------------------------------------------------------------------

T2_RULES = ["global", "cfar", "stackelberg"]


def _init_t2(variant):
    C.apply(variant)
    import r1_allocation as A1
    A1.RULES = list(T2_RULES)


def _task_t2(args):
    import r1_allocation as A1
    return A1.run_panel(args)


def run_t2(variant, workers):
    import r1_allocation as A1
    jobs = [(n, (0.05,), 60, 150, [None], 1500 + A1.MAIN.index(n)) for n in ("akshn_setting", "ca_setting_model")]
    # split each panel's 210 replicates is not possible without changing its rng stream: one job per panel
    with ProcessPoolExecutor(min(workers, len(jobs)), initializer=_init_t2, initargs=(variant,)) as ex:
        parts = list(ex.map(_task_t2, jobs))
    raw = pd.concat(parts, ignore_index=True)
    summ = A1.summarize(raw)
    summ.insert(0, "variant", variant)
    raw.insert(0, "variant", variant)
    return raw, summ


def contrasts_t2(summ):
    rows = []
    s = summ[summ.ncal == -1]
    for variant in s.variant.unique():
        for panel in ("akshn_setting", "ca_setting_model"):
            for mode in ("matched", "nominal"):
                x = s[(s.variant == variant) & (s.panel == panel) & (s["mode"] == mode)].set_index("rule")
                for r in ("stackelberg", "cfar"):
                    rows.append(dict(variant=variant, panel=panel, mode=mode, contrast=f"{r} - global",
                                     est=x.loc[r, "sel_informed"] - x.loc["global", "sel_informed"],
                                     lo=x.loc[r, "sel_informed_dlo"], hi=x.loc[r, "sel_informed_dhi"],
                                     p_pos=x.loc[r, "sel_informed_pgt"], rule_sel=x.loc[r, "sel_informed"],
                                     global_sel=x.loc["global", "sel_informed"],
                                     rule_spend=x.loc[r, "spend"], global_spend=x.loc["global", "spend"],
                                     rule_matched_ok=x.loc[r].get("matched_ok", np.nan),
                                     global_matched_ok=x.loc["global"].get("matched_ok", np.nan)))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="all")
    ap.add_argument("--S", type=int, default=10)
    ap.add_argument("--R", type=int, default=200)
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--variants", default=",".join(C.VARIANTS))
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    variants = a.variants.split(",")
    t0 = time.time()
    if a.part in ("r4", "all"):
        raws = []
        for v in variants:
            for boot in ("trajectory", "main_task"):
                raws.append(run_r4(v, boot, a.S, a.R, a.workers))
                print(f"r4 {v} {boot} done {time.time() - t0:.0f}s", flush=True)
        raw = pd.concat(raws, ignore_index=True)
        (ROOT / "data" / "processed" / "fixes2").mkdir(parents=True, exist_ok=True)
        raw.to_pickle(ROOT / "data" / "processed" / "fixes2" / "ctx_r4_primary_raw_thrfix.pkl")
        summ = summarize_r4(raw)
        summ.to_csv(OUT / "ctx_r4_primary_thrfix.csv", index=False, float_format="%.6g")
        print(summ.round(4).T.to_string(), flush=True)
    if a.part in ("t2", "all"):
        summs = []
        for v in variants:
            _, s = run_t2(v, a.workers)
            summs.append(s)
            print(f"t2 {v} done {time.time() - t0:.0f}s", flush=True)
        summ = pd.concat(summs, ignore_index=True)
        summ.to_csv(OUT / "ctx_t2r1_main5_summary_thrfix.csv", index=False, float_format="%.6g")
        con = contrasts_t2(summ)
        con.to_csv(OUT / "ctx_t2r1_overview_contrasts_thrfix.csv", index=False, float_format="%.6g")
        print(con.round(4).to_string(), flush=True)


if __name__ == "__main__":
    main()
