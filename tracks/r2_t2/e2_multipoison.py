"""E2: multi-context baseline poisoning and poisoning-robust tail estimation.

Round 1 poisoned one context. OS-CFAR with a leave-one-context-out (LOCO) tail resisted it,
because a context's own data enter its threshold only through a robust location (p75 order
statistic). But the LOCO tail is estimated from the OTHER contexts' new-window data, so an
attacker who can inject benign-but-suspicious honest runs into several contexts can inflate that
shared tail and raise every threshold, including the target's.

Threat model. Per replicate, honest runs per context are split 1/3 trusted reference (an earlier
clean calibration period), 1/3 new calibration window (poisoned), 1/3 test; attacks 50/50.
For a target context t the attacker places a fraction eps of the new window of each poisoned
context at a high score: v_t = its own maximum calibration attack score in t, and in another
context c the value max(v_t, loc_c + (v_t - loc_t)) (clipped to the panel's maximum score), which
lands above v_t in raw space (beats a global threshold) and above t's offset score in z space
(beats a pooled-tail OS-CFAR). Scenarios: target only; one other context (the largest);
a random half of the others; all others; all contexts. Every context is the target in turn.

Defenses at budget B:
  global, cfar, pooled_eb                       recalibrated on the new window
  os_loco                                       OS-CFAR, p75 offset, LOCO tail (round 1)
  tm_loco                                       TM-CFAR (10% trim), LOCO tail (round 1)
  frozen / refmix                               CFAR on the trusted reference / 50-50 mix
  os_frozen   (proposed) p75 offset from the new window, tail of offset scores from the frozen
              trusted reference (pooled over contexts): poison can only move the offset (needs
              > 25% of a context's window)
  os_median   (proposed) tail = median over the other contexts of their offset-score survival
              functions (new window); level calibrated on the reference
  os_trim     (proposed) tail = mean of the other contexts' survivals after dropping, pointwise,
              the top 25% of contexts; level calibrated on the reference
  os_capped   (proposed) LOCO tail capped at the reference tail + delta (10% of the score range)
  os_lowq     (proposed) tail = 25th percentile over the other contexts of their survival
              functions (resists poison in up to 75% of contexts); level calibrated on reference
  os_guard    (proposed) frozen-reference tail unless the median-of-contexts tail of the new
              window moves by more than 5% of the score range (a deployment-wide change), then
              the median tail: robust to minority poisoning, tracks majority (genuine) drift

Genuine-drift controls (no attacker; drift applied to the new window AND the test honest data):
  drift_tail   in every context a random 3% of honest runs are replaced by values drawn uniformly
               between the pooled honest 95th percentile and the honest maximum + 10% of the
               range (a heavier honest tail deployment-wide, e.g. a new agent version)
  drift_shift  every honest score in every context +10% of the range (location shift)
  drift_target the target context only +10% of the range
A robust rule should keep the realized spend near B under drift (it must adapt) while keeping
the target TPR under poisoning (it must not adapt to poison).

    unset VIRTUAL_ENV; uv run python tracks/r2_t2/e2_multipoison.py [--quick]
"""
from __future__ import annotations

import argparse
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

import r2lib as R

L = R.L
PANELS = ["la_env_local", "la_taskcat_local", "akshn_setting", "ca_setting_model",
          "mb_gpt-4.1-nano_trajectory", "mb_gpt-4.1-mini_trajectory"]
EPS = (0.01, 0.02, 0.05, 0.1, 0.2)
SCEN = ["target", "one_other", "half_others", "all_others", "all"]
DRIFT = ["drift_tail", "drift_shift", "drift_target"]


def three_way(df, rng):
    Hr, Hn, Ht, Ac, At = {}, {}, {}, {}, {}
    for c, g in df.groupby("ctx", sort=True):
        h = g[g.label == "honest"].stat.values[rng.permutation((g.label == "honest").sum())]
        k = len(h) // 3
        Hr[c], Hn[c], Ht[c] = h[:k], h[k:2 * k], h[2 * k:]
        a = g[g.label == "attack"].stat.values[rng.permutation((g.label == "attack").sum())]
        Ac[c], At[c] = a[: len(a) // 2], a[len(a) // 2:]
    return Hr, Hn, Ht, Ac, At


def defenses(Hn, Hr, w, B, delta):
    G = L.Grid(Hn, w)
    out = dict(global_=L.rule_global(G, B), cfar=L.rule_cfar(G, B),
               pooled_eb=L.rule_pooled(G, B, L.eb_n0(G, 0.05)),
               os_loco=R.rule_os_robust_tail(Hn, w, B, "loco"),
               tm_loco=L.rule_tm_scale(Hn, w, B, 0.1, tune=False),
               refmix=L.rule_reference_mix(Hn, Hr, B, 0.5),
               frozen=L.rule_reference_mix(Hn, Hr, B, 1.0),
               os_frozen=R.rule_os_robust_tail(Hn, w, B, "frozen", Hr=Hr),
               os_median=R.rule_os_robust_tail(Hn, w, B, "median", Hr=Hr),
               os_trim=R.rule_os_robust_tail(Hn, w, B, "trim", Hr=Hr),
               os_capped=R.rule_os_robust_tail(Hn, w, B, "capped", Hr=Hr, delta=delta),
               os_lowq=R.rule_os_robust_tail(Hn, w, B, "lowq", Hr=Hr, q=0.25),
               os_guard=R.rule_os_robust_tail(Hn, w, B, "guard", Hr=Hr, delta=0.5 * delta))
    out["global"] = out.pop("global_")
    return out


def run(args):
    name, B, n_rep, seed = args
    df = R.load(name)
    w = L.traffic(df)
    allv = df.stat.values
    smax, rng_ = float(allv.max()), float(allv.max() - allv.min())
    delta = 0.1 * rng_
    hv = df[df.label == "honest"].stat.values
    q95, hmax = float(np.quantile(hv, 0.95)), float(hv.max())
    rng = np.random.default_rng(seed)
    rows = []
    for rep in range(n_rep):
        Hr, Hn, Ht, Ac, At = three_way(df, rng)
        keys = list(Hn)
        wv = np.array([w[k] for k in keys])
        others_order = sorted(keys, key=lambda k: -w[k])
        loc = {k: R._p_loc(Hn[k]) for k in keys}

        def record(th, Ht_, t, scen, eps, eps_tot):
            fpr = L.rates(th, Ht_)
            tpr = L.rates(th, At)
            i = keys.index(t)
            return dict(tpr_t=tpr[i], fpr_t=fpr[i], spend=float(wv @ fpr), tpr_uniform=float(np.mean(tpr)),
                        eps_tot=eps_tot)

        for t in keys:
            vt = float(Ac[t].max())
            zt = vt - loc[t]
            oth = [k for k in others_order if k != t]
            half = list(rng.permutation(oth)[: max(1, len(oth) // 2)])
            sets = dict(target=[t], one_other=oth[:1], half_others=half, all_others=oth, all=[t] + oth)
            # clean baseline (eps = 0)
            for d, th in defenses(Hn, Hr, w, B, delta).items():
                rows.append(dict(panel=name, B=B, rep=rep, target=t, scen="clean", eps=0.0, rule=d,
                                 **record(th, Ht, t, "clean", 0.0, 0.0)))
            for scen in SCEN:
                for eps in EPS:
                    Hp = dict(Hn)
                    npois = 0
                    for c in sets[scen]:
                        m = int(round(eps * len(Hn[c]) / (1 - eps)))
                        v = vt if c == t else min(smax, max(vt, loc[c] + zt))
                        Hp[c] = np.concatenate([Hn[c], np.full(m, v)])
                        npois += m
                    eps_tot = npois / (npois + sum(len(v) for v in Hn.values()))
                    for d, th in defenses(Hp, Hr, w, B, delta).items():
                        rows.append(dict(panel=name, B=B, rep=rep, target=t, scen=scen, eps=eps, rule=d,
                                         **record(th, Ht, t, scen, eps, eps_tot)))
            # genuine drift controls (no attacker), applied to the new window and to test
            for dr in DRIFT:
                if dr != "drift_target" and t != keys[0]:
                    continue  # deployment-wide drifts do not depend on the target: once per rep
                if dr == "drift_tail":
                    def f(v):
                        m = rng.random(len(v)) < 0.03
                        v = v.copy()
                        v[m] = rng.uniform(q95, hmax + 0.1 * rng_, m.sum())
                        return v
                    Hn_d = {k: f(v) for k, v in Hn.items()}
                    Ht_d = {k: f(v) for k, v in Ht.items()}
                elif dr == "drift_shift":
                    Hn_d = {k: v + 0.1 * rng_ for k, v in Hn.items()}
                    Ht_d = {k: v + 0.1 * rng_ for k, v in Ht.items()}
                else:
                    Hn_d = {k: (v + 0.1 * rng_ if k == t else v) for k, v in Hn.items()}
                    Ht_d = {k: (v + 0.1 * rng_ if k == t else v) for k, v in Ht.items()}
                for d, th in defenses(Hn_d, Hr, w, B, delta).items():
                    rows.append(dict(panel=name, B=B, rep=rep, target=t, scen=dr, eps=0.0, rule=d,
                                     **record(th, Ht_d, t, dr, 0.0, 0.0)))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    n_rep = 2 if a.quick else 30
    avail = set(R.P.available())
    # weak MonitoringBench monitors with 10-70 honest per context per window: 5% only
    jobs = [(n, B, n_rep, 7000 + 10 * i + j) for i, n in enumerate(PANELS) if n in avail
            for j, B in enumerate((0.01, 0.05)) if not (n.startswith("mb_") and B < 0.05)]
    t0 = time.time()
    parts = []
    with ProcessPoolExecutor(min(len(jobs), a.workers)) as ex:
        for r in ex.map(run, jobs):
            parts.append(r)
            print(r.panel.iloc[0], r.B.iloc[0], len(r), f"{time.time() - t0:.0f}s", flush=True)
    raw = pd.concat(parts, ignore_index=True)
    tag = "quick" if a.quick else "full"
    R.RAW.mkdir(parents=True, exist_ok=True)
    raw.to_parquet(R.RAW / f"e2_{tag}.parquet")
    g = raw.groupby(["panel", "B", "scen", "eps", "rule"])
    summ = g[["tpr_t", "fpr_t", "spend", "tpr_uniform", "eps_tot"]].mean()
    tt = raw.groupby(["panel", "B", "scen", "eps", "rule", "target"]).tpr_t.mean()
    summ["tpr_t_worst"] = tt.groupby(level=[0, 1, 2, 3, 4]).min()
    rep_mean = raw.groupby(["panel", "B", "scen", "eps", "rule", "rep"])[["tpr_t", "spend"]].mean()
    rng = np.random.default_rng(0)

    def ci(x):
        x = x.values
        bs = np.array([x[rng.integers(0, len(x), len(x))].mean() for _ in range(400)])
        return pd.Series(dict(lo=np.quantile(bs, 0.025), hi=np.quantile(bs, 0.975)))

    for col in ("tpr_t", "spend"):
        c = rep_mean[col].groupby(level=[0, 1, 2, 3, 4]).apply(ci).unstack()
        summ[col + "_lo"], summ[col + "_hi"] = c["lo"], c["hi"]
    summ = summ.reset_index()
    R.OUT.mkdir(parents=True, exist_ok=True)
    summ.to_csv(R.OUT / f"e2_multipoison_{tag}.csv", index=False, float_format="%.4g")
    pd.set_option("display.width", 250)
    print(summ[(summ.B == 0.01) & (summ.eps.isin([0, 0.02, 0.05, 0.1]))].pivot_table(
        index=["panel", "scen", "eps"], columns="rule", values="tpr_t").round(2).to_string())


if __name__ == "__main__":
    main()
