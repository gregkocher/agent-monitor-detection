"""Round 2b: slow ("boiling frog") baseline poisoning over sequential recalibration rounds, and the
mirror case of genuine drift.

Each round every context receives a batch of fresh honest runs (bootstrap from a stream pool,
batch size proportional to traffic); thresholds are recalibrated at B = 1% on a sliding window of
the last W rounds. In the target context the attacker contributes a fraction eps of each batch at
score h_{r-1} + step (just above the current threshold: these runs alarm, audits clear them as
benign, so they enter the honest window), capped at the score maximum.

Defenses (target-context threshold):
  cfar          plain sliding-window CFAR (no filter): with eps > B the attacker can jump at once,
                so it uses step = full range
  cfar_filter   new calibration points above h_{r-1} + delta are rejected as outliers; the attacker
                steps at delta per round (the classic boiling frog)
  cfar_cumcap   filter + cumulative cap: h <= h_0 + delta (h_0 = threshold of the initial clean
                window)
  refmix        filter + CFAR on a 50/50 mix of the frozen initial window and the sliding window
  global        one pooled threshold over all contexts (filter applied)
  os_shift      filter + p75 offset from the window, tail from the other contexts (LOCO)
Genuine drift: no attacker; from round R/3 on, the target's fresh honest runs are drawn from a
hotter distribution (each score + `shift` points, clipped to the scale). The same defenses then
either track the change (FPR stays near B) or refuse to (FPR rises).

    unset VIRTUAL_ENV; uv run python tracks/t2_per_context/r2_boiling.py
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import panels as P  # noqa: E402
import t2lib as L  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "results" / "t2"
B = 0.01
R, W = 30, 10
BATCH = 40  # per context per round at equal traffic
DEFS = ["cfar", "cfar_filter", "cfar_cumcap", "refmix", "global", "os_shift"]


def simulate(args):
    name, target, scenario, eps, shift, rep, seed = args
    df = P.load(name)
    rng = np.random.default_rng(seed)
    w = L.traffic(df)
    keys = sorted(df.ctx.unique())
    lo_s, hi_s = df.stat.min(), df.stat.max()
    delta = 0.1 * (hi_s - lo_s)
    pool, test = {}, {}
    for c in keys:
        h = df[(df.ctx == c) & (df.label == "honest")].stat.values
        h = h[rng.permutation(len(h))]
        k = len(h) // 2
        pool[c], test[c] = h[:k], h[k:]
    att = df[(df.ctx == target) & (df.label == "attack")].stat.values
    nb = {c: max(5, int(round(BATCH * len(keys) * w[c]))) for c in keys}
    hot = lambda v: np.clip(v + shift, lo_s, hi_s)  # noqa: E731

    def batch(c, r):
        v = pool[c][rng.integers(0, len(pool[c]), nb[c])]
        if scenario == "drift" and c == target and r >= R // 3:
            v = hot(v)
        return v

    # initial clean window (rounds -W..-1)
    hist = {c: [batch(c, -1) for _ in range(W)] for c in keys}
    init = {c: np.concatenate(hist[c]) for c in keys}
    state = {d: {c: list(hist[c]) for c in keys} for d in DEFS}
    th0 = L.rule_cfar(L.Grid(init, w), B)
    h_prev = {d: th0[target].h for d in DEFS}
    h_prev["global"] = L.rule_global(L.Grid(init, w), B)[target].h
    rows = []
    for r in range(R):
        fresh = {c: batch(c, r) for c in keys}
        for d in DEFS:
            st = state[d]
            for c in keys:
                new = fresh[c]
                if c == target and scenario == "poison":
                    m = int(round(eps * nb[c] / (1 - eps)))
                    step = (hi_s - lo_s) if d == "cfar" else delta
                    new = np.concatenate([new, np.full(m, min(h_prev[d] + step, hi_s))])
                if d != "cfar" and c == target:
                    new = new[new <= h_prev[d] + delta + 1e-9]  # outlier filter
                st[c].append(new)
                st[c] = st[c][-W:]
            win = {c: np.concatenate(st[c]) for c in keys}
            G = L.Grid(win, w)
            if d in ("cfar", "cfar_filter"):
                th = L.rule_cfar(G, B)
            elif d == "cfar_cumcap":
                th = L.rule_capped(L.rule_cfar(G, B), th0, delta)
            elif d == "refmix":
                th = L.rule_reference_mix(win, init, B, 0.5)
            elif d == "global":
                th = L.rule_global(G, B)
            elif d == "os_shift":
                th = L.rule_os_shift(win, w, B, 0.75, tune=False)
            t = th[target]
            h_prev[d] = t.h
            ht = hot(test[target]) if (scenario == "drift" and r >= R // 3) else test[target]
            rows.append(dict(panel=name, target=target, scenario=scenario, eps=eps, shift=shift, rep=rep,
                             round=r, rule=d, h=t.h, tpr_t=t.rate(att), fpr_t=t.rate(ht)))
    return pd.DataFrame(rows)


def main():
    jobs = []
    seed = 7000
    for name in ("akshn_setting", "la_env_local"):
        df = P.load(name)
        rng_t = sorted(df.ctx.unique())
        for target in rng_t:
            for rep in range(4):
                for eps in (0.02, 0.05, 0.1):
                    jobs.append((name, target, "poison", eps, 0.0, rep, seed))
                    seed += 1
                jobs.append((name, target, "drift", 0.0, 2.0, rep, seed))
                seed += 1
    with ProcessPoolExecutor(8) as ex:
        raw = pd.concat(list(ex.map(simulate, jobs, chunksize=4)), ignore_index=True)
    g = raw.groupby(["panel", "scenario", "eps", "shift", "rule", "round"])[["h", "tpr_t", "fpr_t"]].mean()
    g = g.reset_index()
    OUT.mkdir(parents=True, exist_ok=True)
    g.to_csv(OUT / "boiling_frog_rounds.csv", index=False, float_format="%.4g")
    last = g[g["round"] == R - 1].pivot_table(index=["panel", "scenario", "eps"], columns="rule",
                                             values=["tpr_t", "fpr_t"])
    last.round(3).to_csv(OUT / "boiling_frog_final.csv")
    print(last.round(3).to_string())


if __name__ == "__main__":
    main()
