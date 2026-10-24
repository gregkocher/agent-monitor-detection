"""Cost and latency per 1k trajectories for each first stage of the r5watch cascades (preregistered formula).

  cost_1k(first, e)    = 1000 * steps_per_traj * (c_first + esc_h(first, e) * c_second)
  latency_step(first, e) = l_first + esc_h(first, e) * l_second      (serial: triage then the second stage)
  compute_h_1k(first, e) = 1000 * steps_per_traj * latency_step / 3600

esc_h = realized escalated share of test-honest steps (conformal, task resampling, from results/r5_watch/cells.csv);
steps_per_traj = mean steps per evaluation trajectory of the panel. c = mean billed $ per step; l = median per-call
latency (s). Sources:
  watch    this track's cache (OpenAI standard tier via OpenRouter, prompt caching as billed)
  jev      round-1 cache (data/r5_jev/cache)            luna  r5luna cache (Decisions API)
  decider  hosted perplexity/pplx-decider-v1.2 dev check (data/r5_luna/cache/decider_dev.sqlite; the cascade scores
           themselves are from the self-hosted pod: one H100 at $3.99/h and ~4 req/s = $0.00028/step, also reported)
  gen      generative GPT-6 Luna (r5luna cache cost; latency = median of the spend-ledger rows tagged r5luna:gen)
  mini     gpt-4.1-mini `none` (panel cost per step; latency = median ledger latency of gpt-4.1-mini rows of track t1)
  gemini   aksh-n Gemini scores are dataset-provided: no cost or latency available (reported as NaN)

    unset VIRTUAL_ENV; uv run python -m tracks.r5_watch.cost
"""
from __future__ import annotations

import json
import sqlite3

import numpy as np
import pandas as pd

from amd.common.openrouter import LEDGER
from amd.common.schema import DATA

from .analyze import OUT

POD_DECIDER = 3.99 / 3600 / 4.0


def _cache_stats(path, like="%"):
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    c, l = [], []
    for (r,) in db.execute("select result from scores where monitor_id like ?", (like,)):
        d = json.loads(r)
        if d.get("cost") is not None:
            c.append(d["cost"])
        if d.get("latency") is not None:
            l.append(d["latency"])
    db.close()
    return (float(np.mean(c)) if c else np.nan), (float(np.median(l)) if l else np.nan), len(c)


def _ledger_latency(pred, limit=200000):
    lat = []
    with open(LEDGER) as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if pred(r) and r.get("latency") is not None:
                lat.append(r["latency"])
    return float(np.median(lat)) if lat else np.nan


def main():
    panels = pd.read_csv(OUT / "panels.csv")
    cells = pd.read_csv(OUT / "cells.csv")
    cells = cells[(cells.convention == "conformal") & (cells.alpha == 0.01)]
    first = {}
    for src in ("mb", "akshn_linuxarena"):
        w = _cache_stats(DATA / "r5_watch" / "cache" / f"{src}.sqlite", "%watcher-sev-r1%")
        j = _cache_stats(DATA / "r5_jev" / "cache" / f"{src}.sqlite", "typesafe/jev-1.14|r5-B_w3|both-orders")
        lu = _cache_stats(DATA / "r5_luna" / "cache" / f"luna_{src}.sqlite", "%r5-B_w3|both-orders")
        first[src] = {"watch": w, "watch_exp": w, "jev": j, "luna": lu}
    dh = _cache_stats(DATA / "r5_luna" / "cache" / "decider_dev.sqlite")
    gen_c = _cache_stats(DATA / "r5_luna" / "cache" / "gen_mb.sqlite")[0]
    gen_l = _ledger_latency(lambda r: str(r.get("tag", "")).startswith("r5luna:gen"))
    mini_l = _ledger_latency(lambda r: r.get("track") == "t1" and r.get("model") == "openai/gpt-4.1-mini")
    p = panels.set_index("panel")
    second = {"mb:gen": (gen_c, gen_l), "mb:mini": (float(p.loc["mb:mini", "llm_cost_step"]), mini_l),
              "la_nano:gemini": (np.nan, np.nan)}
    rows = []
    for _, r in cells[cells.kind.isin(["cascade", "fixed_cutoff", "standalone"])].iterrows():
        pn = r.panel
        src = "mb" if pn.startswith("mb") else "akshn_linuxarena"
        f = r.first
        if f in ("rand", "oracle") or (r.kind == "standalone" and f not in first[src] and f != "decider"):
            continue
        steps = p.loc[pn, "steps"] / (p.loc[pn, "n_honest"] + p.loc[pn, "n_attack"])
        cf, lf = (dh[0], dh[1]) if f == "decider" else first[src].get(f, (np.nan, np.nan))[:2]
        cs, ls = second[pn]
        esc = 0.0 if r.kind == "standalone" else r.esc_honest
        rows.append(dict(panel=pn, first=f, kind=r.kind, e=r.e, config=r.config, esc_honest_steps=esc,
                         steps_per_traj=steps, c_first=cf, c_first_pod=POD_DECIDER if f == "decider" else np.nan,
                         c_second=cs, l_first=lf, l_second=ls,
                         cost_1k=1000 * steps * (cf + esc * cs) if np.isfinite(cs) or esc == 0 else np.nan,
                         cost_1k_first_only=1000 * steps * cf,
                         latency_step=lf + esc * ls if np.isfinite(ls) else np.nan,
                         compute_h_1k=1000 * steps * (lf + esc * ls) / 3600 if np.isfinite(ls) else np.nan))
    D = pd.DataFrame(rows)
    D.to_csv(OUT / "cost_latency.csv", index=False)
    print(D[D.kind != "standalone"].round(5).to_string(index=False))


if __name__ == "__main__":
    main()
