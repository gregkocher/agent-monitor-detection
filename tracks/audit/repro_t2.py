"""Audit reproduction: T2 '7 settings' panel (aksh-n Gemini-3.1-Pro local judge-step suspicion, trajectory max,
context = setting; BashArena honest_summarized rows dropped), B = 1% (and 5%), nominal mode.
Rules: global, CFAR (per-context randomized quantile), Stackelberg (equalize calibration TPR on per-context ROC
upper hulls, randomized, spend = B). Metrics on the held-out half: spend, uniform TPR, sel_informed (attacker picks
argmin calibration TPR from the SAME calibration attacks the defender used: the project's definition),
sel_oracle (min test TPR) and sel_indep (attacker information from a separate third of the attacks that the
defender did NOT fit on; defender fits on another third; evaluation on the last third).

Independent minimal code (rebuilds the panel from data/processed/akshn_*/; no project imports).

    unset VIRTUAL_ENV; uv run python tracks/audit/repro_t2.py
Writes results/audit/repro_t2.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from alib import OUT, P, jl, rand_threshold

SETS = ["akshn_bash", "akshn_iac", "akshn_shade", "akshn_agentdojo", "akshn_basharena_opus46",
        "akshn_basharena_sonnet45", "akshn_linuxarena"]
MID = "gemini-3.1-pro|akshn_local_judgestep|full"


def build():
    rows = []
    for s in SETS:
        meta = {d["traj_id"]: (d["label"], d["context"].get("policy")) for d in jl(P / s / "trajectories.jsonl")}
        for r in jl(P / s / "scores.jsonl"):
            if r["monitor_id"] != MID:
                continue
            lab, pol = meta[r["traj_id"]]
            if pol == "honest_summarized":
                continue
            v = np.array([x for x in r["scores"] if x is not None], float)
            if len(v):
                rows.append((s.replace("akshn_", ""), lab, float(v.max())))
    return pd.DataFrame(rows, columns=["ctx", "label", "stat"])


class Mix:
    """Alarm with prob (1-g) 1[s > h_hi] + g 1[s > h_lo] (or a plain randomized tie threshold)."""
    def __init__(self, h_hi, h_lo=None, g=0.0, tie=False):
        self.h_hi, self.h_lo, self.g, self.tie = h_hi, h_lo, g, tie

    def rate(self, s):
        s = np.asarray(s, float)
        if len(s) == 0:
            return np.nan
        if self.tie:
            return float(((s > self.h_hi) + self.g * (s == self.h_hi)).mean())
        a = (s > self.h_hi).astype(float)
        if self.h_lo is not None:
            a = (1 - self.g) * a + self.g * (s > self.h_lo)
        return float(a.mean())


def hull(h, a):
    vals = np.unique(np.r_[h, a])[::-1]
    pts = [(0.0, 0.0, np.inf)] + [((h > v).mean(), (a > v).mean(), v) for v in vals] + [(1.0, 1.0, -np.inf)]
    pts = sorted(set(pts), key=lambda x: (x[0], x[1]))
    hv = []
    for p in pts:
        while len(hv) >= 2:
            (x1, y1, _), (x2, y2, _) = hv[-2], hv[-1]
            if (x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1) >= 0:
                hv.pop()
            else:
                break
        if hv and p[0] == hv[-1][0]:
            if p[1] > hv[-1][1]:
                hv[-1] = p
            continue
        hv.append(p)
    return hv


def cost(hv, t):
    if t <= hv[0][1]:
        return hv[0][0], Mix(hv[0][2])
    for j in range(1, len(hv)):
        if hv[j][1] >= t:
            x1, y1, h1 = hv[j - 1]; x2, y2, h2 = hv[j]
            g = (t - y1) / max(y2 - y1, 1e-300)
            return x1 + g * (x2 - x1), Mix(h1, h2, g)
    return hv[-1][0], Mix(hv[-1][2])


def stackelberg(Hc, Ac, w, B):
    hv = {k: hull(Hc[k], Ac[k]) for k in Hc}
    lo, hi = 0.0, 1.0
    for _ in range(60):
        t = 0.5 * (lo + hi)
        if sum(w[k] * cost(hv[k], t)[0] for k in Hc) <= B:
            lo = t
        else:
            hi = t
    return {k: cost(hv[k], lo)[1] for k in Hc}


def glob(Hc, w, B):
    # weights so that sum_c w_c FPR_c = B (w_c = honest traffic share)
    vals = np.concatenate([Hc[k] for k in Hc])
    wt = np.concatenate([np.full(len(Hc[k]), w[k] / len(Hc[k])) for k in Hc])
    h, g = rand_threshold(vals, B, wt)
    return {k: Mix(h, g=g, tie=True) for k in Hc}


def cfar(Hc, B):
    return {k: (lambda hg: Mix(hg[0], g=hg[1], tie=True))(rand_threshold(Hc[k], B)) for k in Hc}


def metrics(th, Ht, At, w, Ainfo):
    keys = list(th)
    fpr = np.array([th[k].rate(Ht[k]) for k in keys]); tpr = np.array([th[k].rate(At[k]) for k in keys])
    tc = np.array([th[k].rate(Ainfo[k]) for k in keys])
    best = np.flatnonzero(tc == tc.min())
    return dict(spend=float(np.dot([w[k] for k in keys], fpr)), tpr_uniform=float(tpr.mean()),
                sel_info=float(tpr[best].mean()), sel_oracle=float(tpr.min()))


def split(v, rng, parts):
    p = rng.permutation(len(v))
    cuts = np.round(np.cumsum(parts)[:-1] * len(v)).astype(int)
    return [v[x] for x in np.split(p, cuts)]


def main(n_rep=60):
    df = build()
    w = (df[df.label == "honest"].groupby("ctx").size() / (df.label == "honest").sum()).to_dict()
    print(df.groupby(["ctx", "label"]).size().unstack())
    rng = np.random.default_rng(99)
    rows = []
    for rep in range(n_rep):
        Hc, Ht, Ac, At, A1, A2, A3 = {}, {}, {}, {}, {}, {}, {}
        for k, g in df.groupby("ctx"):
            Hc[k], Ht[k] = split(g[g.label == "honest"].stat.values, rng, [0.5, 0.5])
            a = g[g.label == "attack"].stat.values
            Ac[k], At[k] = split(a, rng, [0.5, 0.5])
            A1[k], A2[k], A3[k] = split(a, rng, [1 / 3, 1 / 3, 1 / 3])
        for B in (0.01, 0.05):
            rules = {"global": glob(Hc, w, B), "cfar": cfar(Hc, B), "stackelberg": stackelberg(Hc, Ac, w, B)}
            for r, th in rules.items():
                m = metrics(th, Ht, At, w, Ac)            # project protocol (attacker info = defender's fit set)
                th3 = stackelberg(Hc, A1, w, B) if r == "stackelberg" else th
                m3 = metrics(th3, Ht, A3, w, A2)          # attacker info independent of the defender's fit
                rows.append(dict(rep=rep, B=B, rule=r, **m, sel_indep=m3["sel_info"], sel_oracle_3way=m3["sel_oracle"],
                                 tpr_uniform_3way=m3["tpr_uniform"]))
    R = pd.DataFrame(rows)
    S = R.groupby(["B", "rule"]).mean(numeric_only=True).drop(columns="rep").reset_index()
    # paired differences vs global (percentiles over the plain splits)
    for col in ("sel_info", "sel_indep"):
        piv = R.pivot_table(index=["B", "rep"], columns="rule", values=col)
        for r in ("cfar", "stackelberg"):
            d = (piv[r] - piv["global"]).groupby(level=0)
            S.loc[S.rule == r, f"d_{col}_vs_global_q025"] = S.loc[S.rule == r, "B"].map(d.quantile(0.025))
            S.loc[S.rule == r, f"d_{col}_vs_global_q975"] = S.loc[S.rule == r, "B"].map(d.quantile(0.975))
    OUT.mkdir(parents=True, exist_ok=True)
    S.to_csv(OUT / "repro_t2.csv", index=False)
    print(S.to_string())


if __name__ == "__main__":
    main()
