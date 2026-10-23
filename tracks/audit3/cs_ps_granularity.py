"""Audit pass 3 (track r4_cs): score read-out confound (logprob-expected vs generated integer) on persistent state.

    unset VIRTUAL_ENV; uv run python tracks/audit3/cs_ps_granularity.py [--splits 40] [--boot 1000]

Three of the 9 "identical-input" monitors (gpt-4.1-mini, Qwen3-235B, gpt-4.1) are read out as the
logprob-expected 0-10 score (continuous, ~1,000+ distinct values); the other six as the generated integer
(<= 10 values). The r4cs entry lists only reasoning budgets / completion caps as differences. The same calls also
stored the generated integer (meta.int_scores), so the three logprob monitors can be re-analysed on integer
read-outs at $0. Contrast as in cs_indep_ps.py (whitened top-3 sum − max, iid 50/50 splits, randomized
thresholds, bootstrap with app clusters drawn independently for honest / attack = amd.evaluation.paired scheme).
Output: results/audit3/cs_ps_granularity.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from cs_indep_ps import FILES, OUT, PS, alarm, draw, load, rand_thr, split_stats  # noqa: E402


def ints(f):
    out = {}
    for line in open(PS / f):
        r = json.loads(line)
        out[r["traj_id"]] = np.array([np.nan if v is None else float(v) for v in r["meta"]["int_scores"]])
    return out


def run(Sm, hon, att, happ, aapp, splits, B, al, seed=2026):
    rng = np.random.default_rng(seed)
    Wh, Wa = draw(happ, aapp, B, rng, "app_indep")
    Whi, Wai = draw(happ, aapp, B, rng, "iid")
    H = np.vstack([Sm[i] for i in hon]); A = np.vstack([Sm[i] for i in att])
    srng = np.random.default_rng(7)
    pt = {"max": [], "top3": []}; fp = {"max": [], "top3": []}
    bt = {k: {"max": np.zeros(B), "top3": np.zeros(B)} for k in ("app", "iid")}
    for _ in range(splits):
        cal = np.sort(rng.permutation(len(H))[: len(H) // 2]); test = np.setdiff1d(np.arange(len(H)), cal)
        st = split_stats(H[cal], H[test], A, srng)
        for d in ("max", "top3"):
            c, t, s = st[d]
            h, g = rand_thr(c, np.ones((1, len(c))), al)
            pt[d].append(alarm(s, h, g).mean()); fp[d].append(alarm(t, h, g).mean())
            for k, (wh, wa) in (("app", (Wh, Wa)), ("iid", (Whi, Wai))):
                hb, gb = rand_thr(c, wh[:, cal], al)
                bt[k][d] += (alarm(s, hb, gb) * wa).sum(1) / wa.sum(1)
    est = np.mean(pt["top3"]) - np.mean(pt["max"])
    res = dict(tpr_max=np.mean(pt["max"]), tpr_top3=np.mean(pt["top3"]), fpr_max=np.mean(fp["max"]),
               fpr_top3=np.mean(fp["top3"]), est=est)
    for k in ("app", "iid"):
        b = (bt[k]["top3"] - bt[k]["max"]) / splits
        res[f"{k}_lo"], res[f"{k}_hi"] = np.quantile(b, .025), np.quantile(b, .975)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=int, default=40)
    ap.add_argument("--boot", type=int, default=1000)
    a = ap.parse_args()
    S, hon, att, happ, aapp = load()
    rows = []
    for mon in ("gpt-4.1-mini", "qwen3-235b", "gpt-4.1"):
        I = ints(FILES[mon])
        n_distinct = len(np.unique(np.concatenate([I[i] for i in hon + att])))
        for al in (0.05, 0.01):
            for kind, Sm in (("logprob-expected (as reported)", S[mon]), ("generated integer", I)):
                r = run(Sm, hon, att, happ, aapp, a.splits, a.boot, al)
                rows.append(dict(monitor=mon, alpha=al, readout=kind,
                                 n_distinct=n_distinct if kind.startswith("gen") else np.nan, **r))
                print(mon, al, kind, {k: round(v, 3) for k, v in r.items()}, flush=True)
    pd.DataFrame(rows).to_csv(OUT / "cs_ps_granularity.csv", index=False)


if __name__ == "__main__":
    main()
