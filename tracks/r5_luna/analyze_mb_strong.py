"""r5luna addendum (EXPERIMENT_LOG.md, "r5luna addendum: a strong second stage and baseline on MonitoringBench"):
generative GPT-6 Luna as the MB second stage and standalone baseline. Round-1 MB panel and cascade machinery,
conformal threshold rule primary (tracks/fixes2/jev_patch), plug-in also reported.

    unset VIRTUAL_ENV; uv run python -m tracks.r5_luna.analyze_mb_strong [--splits 50] [--boot 1000] [--quick] [--blind]

Outputs results/r5_luna/mb_strong_{hypotheses,cells}.csv.
"""
from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd

from tracks.fixes2.jev_patch import use_convention
from tracks.r5_jev import cascade as C
from tracks.r5_jev import panels as PN
from tracks.r5_jev.analyze_explore import load_decider

from . import lunalib as L
from . import panels as LP
from .analyze import OUT, BOOT, wauc, task_design, summ
from .score_gen import load_gen
from tracks.r5_jev.score_jev import load

ALPHAS = (0.01, 0.05)
E_LEVELS = (0.05, 0.10, 0.20, 0.30)
FIRSTS = ("jev", "luna", "probe", "nano", "decider", "len", "rand", "oracle")
PLAINS = ("gen", "jev", "luna", "decider", "probe", "nano", "llm")
MARGIN = 0.03


def load_panel(blind=False):
    P = PN.load_mb(L.VARIANT, L.SCHEME, probe=True)
    T = {t.traj_id: t for t in load("mb", set(P.hid) | set(P.aid))}
    luna, _ = L.load_scores("luna", "mb", list(T.values()), L.MB_MAX_STEPS)
    LP._add(P, "luna", luna, T, strip=True)
    gen = load_gen("mb", list(T.values()), L.MB_MAX_STEPS)
    LP._add(P, "gen", gen, T, strip=True)
    load_decider(P, "mb")
    if blind:
        rng = np.random.default_rng(0)
        for s in ("gen", "luna"):
            P.streams[s] = [np.round(10 * np.clip(np.asarray(j) + rng.normal(0, .05, len(j)), 0, 1)) if s == "gen"
                            else np.clip(np.asarray(j) + rng.normal(0, .05, len(j)), 0, 1) for j in P.streams["jev"]]
    P.second = "gen"
    PN._refs(P, P.attack_onset)          # rand / oracle / oracle_label re-derived for the new second stage
    P.meta["main_task_h"], P.meta["main_task_a"] = P.hg, P.ag
    return P


def run(P, S, B, seed, design):
    R = {("plain", s): C.evaluate(P, design, {"kind": "plain", "stream": s}, ALPHAS) for s in PLAINS}
    for f in FIRSTS:
        cfg = {"kind": "cascade", "first": f, "seed": seed + 17}
        for e in E_LEVELS:
            cfg["e"] = e
            R[(f, e)] = C.evaluate(P, design, cfg, ALPHAS)
        cfg.pop("_prep", None)
    return R


def row(name, R, k1, k2, a, ni=False):
    t1, t2 = C.tpr_boot([R[k1]], a), C.tpr_boot([R[k2]], a)
    d = t1 - t2
    s = C.summarize(d, MARGIN if ni else None)
    out = dict(test=name, arm1=str(k1), arm2=str(k2), alpha=a, tpr1=float(t1[0]), tpr2=float(t2[0]),
               fpr1=float(np.mean(R[k1][a]["fpr"])), fpr2=float(np.mean(R[k2][a]["fpr"])),
               est=s["est"], lo=s["lo"], hi=s["hi"], p_two=s["p_two"])
    if ni:
        out["p_ni"] = s["p_ni"]
    out["p_family"] = min(1.0, 2 * s["p_ni"]) if ni else s["p_two"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=int, default=50)
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--blind", action="store_true")
    a = ap.parse_args()
    S, B = (8, 60) if (a.quick or a.blind) else (a.splits, a.boot)
    out = (BOOT.parent / "blind_codecheck") if a.blind else OUT
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    P = load_panel(a.blind)
    cov = {s: float(np.mean(np.concatenate([np.isfinite(x) for x in P.streams[s]]))) for s in PLAINS}
    print("coverage", cov, f"{time.time() - t0:.0f}s", flush=True)
    H, cells = [], []
    for conv in ("conformal", "plugin"):
        use_convention(conv)
        for rs in ("orig", "task"):
            if rs == "task" and conv == "plugin":
                continue
            D = C.make_design(P, S, B, 1) if rs == "orig" else task_design(P, S, B, 1)
            R = run(P, S, B, 1, D)
            a1 = 0.01
            rows = [row("H1-MB-strong", R, ("jev", 0.2), ("plain", "gen"), a1, ni=True)]
            for i, s in enumerate(("jev", "luna", "decider", "probe"), 1):
                rows.append(row(f"S{i}", R, ("plain", "gen"), ("plain", s), a1))
            k = 1
            for f in ("luna", "probe", "nano"):
                for e in (0.10, 0.20):
                    rows.append(row(f"T{k}", R, (f, e), ("jev", e), a1))
                    k += 1
            Hd = pd.DataFrame(rows)
            Hd["p_holm"] = C.holm(Hd["p_family"].values)
            Hd["supported_or_significant"] = Hd["p_holm"] < 0.05
            Hd["convention"], Hd["resampling"] = conv, rs
            H.append(Hd)
            print(Hd[["test", "tpr1", "tpr2", "fpr1", "fpr2", "est", "lo", "hi", "p_family", "p_holm"]].round(4)
                  .to_string(index=False), flush=True)
            if rs == "orig":
                for key, res in R.items():
                    for al in ALPHAS:
                        t = C.tpr_boot([res], al)
                        s_ = summ(t)
                        cells.append(dict(first=key[1] if key[0] == "plain" else key[0],
                                          kind="standalone" if key[0] == "plain" else "cascade",
                                          e=None if key[0] == "plain" else key[1], alpha=al, tpr=s_["est"],
                                          tpr_lo=s_["lo"], tpr_hi=s_["hi"], fpr=float(np.mean(res[al]["fpr"])),
                                          esc_attack=float(np.nanmean(res[al]["esc_a"])) if key[0] != "plain"
                                          else np.nan, convention=conv))
                if conv == "conformal":
                    for s in PLAINS:
                        b = wauc(P, s, D)
                        cells.append(dict(first=s, kind="auroc", alpha=np.nan, tpr=float(b[0]),
                                          tpr_lo=float(np.quantile(b[1:], .025)), tpr_hi=float(np.quantile(b[1:], .975)),
                                          convention=conv))
            print(f"  {conv}/{rs} {time.time() - t0:.0f}s", flush=True)
    pd.concat(H).to_csv(out / "mb_strong_hypotheses.csv", index=False)
    pd.DataFrame(cells).to_csv(out / "mb_strong_cells.csv", index=False)
    pd.DataFrame([dict(stream=k, coverage=v) for k, v in cov.items()]).to_csv(out / "mb_strong_coverage.csv",
                                                                              index=False)
    print(f"done {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
