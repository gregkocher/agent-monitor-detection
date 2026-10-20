"""Quality checks and inventory over data/processed/<source>/.

    python -m amd.data.qc                     # QC every processed source, write results/data_inventory.md
    python -m amd.data.qc linuxarena_sweep    # QC one source (prints only)
    python -m amd.data.qc --spot 2 akshn_bash # also spot-print N records per source

Checks: counts by label x context key; steps per trajectory quantiles; NaN fraction per monitor;
honest trajectories have attack_step None; per-step stream length == number of steps (other units are
reported, not enforced); AUROC of max-over-units (attack vs honest) per monitor as a sanity check.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict

import numpy as np

from amd.common.schema import PROCESSED, REPO, read_jsonl

CTX_KEYS = ("env", "setting", "domain", "task", "task_cluster", "task_category", "side_task_group", "side_task",
            "failure_type", "policy", "agent_model", "attack_policy", "main_task")
COUNT_ONLY = ("main_task",)  # too many values to list; only the number of distinct values is reported


def _auroc(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    allv = np.concatenate([pos, neg])
    ranks = np.argsort(np.argsort(allv, kind="mergesort"), kind="mergesort").astype(float)
    # average ranks for ties
    order = np.argsort(allv, kind="mergesort")
    sv = allv[order]
    i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2
        i = j + 1
    rp = ranks[: len(pos)].sum()
    return float((rp - len(pos) * (len(pos) - 1) / 2) / (len(pos) * len(neg)))


def _q(xs):
    if not xs:
        return "-"
    a = np.asarray(xs, float)
    return "/".join(f"{np.quantile(a, q):.0f}" for q in (0.1, 0.5, 0.9)) + f" (max {a.max():.0f})"


def qc_source(source: str, spot: int = 0, verbose: bool = True) -> dict:
    d = PROCESSED / source
    trajs = {t["traj_id"]: t for t in read_jsonl(d / "trajectories.jsonl")}
    streams = list(read_jsonl(d / "scores.jsonl")) if (d / "scores.jsonl").exists() else []
    out = {"source": source, "n_traj": len(trajs), "n_streams": len(streams)}
    out["by_label"] = dict(Counter(t["label"] for t in trajs.values()))
    ctx_counts = {}
    for k in CTX_KEYS:
        c = Counter((t["label"], t["context"].get(k)) for t in trajs.values() if k in t["context"])
        if c:
            ctx_counts[k] = c
    out["n_contexts"] = {k: len({v for (_, v) in c}) for k, c in ctx_counts.items()}
    steps = defaultdict(list)
    for t in trajs.values():
        steps[t["label"]].append(len(t["steps"]))
    out["steps_q"] = {lab: _q(v) for lab, v in steps.items()}
    out["honest_attack_step_violations"] = sum(
        1 for t in trajs.values() if t["label"] == "honest" and t["attack_step"] is not None)
    out["attack_with_attack_step"] = sum(1 for t in trajs.values() if t["label"] == "attack" and t["attack_step"] is not None)
    out["attack_with_harm_step"] = sum(1 for t in trajs.values() if t["label"] == "attack" and t["harm_step"] is not None)
    out["side_success"] = dict(Counter(str(t["side_task_success"]) for t in trajs.values() if t["label"] == "attack"))

    per_mon = defaultdict(lambda: {"n": 0, "nan": 0, "tot": 0, "len_mismatch": 0, "unit": None, "scale": None,
                                   "max_h": [], "max_a": []})
    orphan = 0
    for s in streams:
        t = trajs.get(s["traj_id"])
        if t is None:
            orphan += 1
            continue
        m = per_mon[s["monitor_id"]]
        m["n"] += 1
        m["unit"], m["scale"] = s["unit"], tuple(s.get("scale") or ())
        vals = s["scores"]
        m["tot"] += len(vals)
        m["nan"] += sum(v is None or (isinstance(v, float) and math.isnan(v)) for v in vals)
        if s["unit"] == "step" and len(vals) != len(t["steps"]):
            m["len_mismatch"] += 1
        fin = [v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
        if fin:
            (m["max_a"] if t["label"] == "attack" else m["max_h"]).append(max(fin))
    out["orphan_streams"] = orphan
    out["monitors"] = {}
    for mid, m in sorted(per_mon.items()):
        out["monitors"][mid] = {
            "unit": m["unit"], "scale": m["scale"], "n_streams": m["n"],
            "nan_frac": round(m["nan"] / m["tot"], 4) if m["tot"] else None,
            "len_mismatch": m["len_mismatch"],
            "auroc_max": round(_auroc(m["max_a"], m["max_h"]), 3),
            "n_h": len(m["max_h"]), "n_a": len(m["max_a"]),
        }
    if verbose:
        print(f"===== {source}: {len(trajs)} trajectories, {len(streams)} score streams, orphans {orphan}")
        print("label:", out["by_label"], "| steps q10/50/90:", out["steps_q"])
        print("honest with attack_step (must be 0):", out["honest_attack_step_violations"],
              "| attacks with attack_step:", out["attack_with_attack_step"],
              "| with harm_step:", out["attack_with_harm_step"], "| side success:", out["side_success"])
        for k, c in ctx_counts.items():
            vals = sorted({v for (_, v) in c}, key=str)
            if k in COUNT_ONLY:
                hv = len({v for (lab, v) in c if lab == "honest"})
                av = len({v for (lab, v) in c if lab == "attack"})
                print(f"  ctx {k}: {len(vals)} distinct (honest {hv}, attack {av})")
                continue
            show = ", ".join(f"{v}: h{c.get(('honest', v), 0)}/a{c.get(('attack', v), 0)}" for v in vals[:25])
            more = f" ... (+{len(vals) - 25})" if len(vals) > 25 else ""
            print(f"  ctx {k} ({len(vals)}): {show}{more}")
        for mid, m in out["monitors"].items():
            print(f"  mon {mid:55s} unit={m['unit']:10s} scale={m['scale']} n={m['n_streams']:5d} "
                  f"nan={m['nan_frac']} len_mismatch={m['len_mismatch']} auroc(max)={m['auroc_max']} "
                  f"(h{m['n_h']}/a{m['n_a']})")
        if spot:
            labs = defaultdict(list)
            for t in trajs.values():
                labs[t["label"]].append(t)
            picks = [labs[lab][0] for lab in ("honest", "attack") if labs[lab]][:spot]
            for t in picks:
                short = dict(t)
                short["steps"] = [{k: (v[:200] if isinstance(v, str) else v) for k, v in st.items()}
                                  for st in t["steps"][:2]] + ([f"... {len(t['steps'])} steps"] if len(t["steps"]) > 2 else [])
                short["meta"] = {k: (v if len(json.dumps(v, default=str)) < 300 else "<long>") for k, v in t["meta"].items()}
                print("  SPOT traj:", json.dumps(short, default=str)[:2500])
                ss = [s for s in streams if s["traj_id"] == t["traj_id"]][:2]
                for s in ss:
                    s2 = dict(s, scores=s["scores"][:30], meta={k: v for k, v in s["meta"].items()
                                                                if len(json.dumps(v, default=str)) < 200})
                    print("  SPOT stream:", json.dumps(s2, default=str)[:800])
    out["ctx_counts"] = ctx_counts
    return out


def write_inventory(results: list[dict]):
    L = ["# Data inventory", "",
         "Generated by `python -m amd.data.qc` from `data/processed/<source>/`. Counts are trajectories.",
         "Steps per trajectory: q10/q50/q90 (max). AUROC = max-over-units (attack vs honest), sanity check only.", ""]
    L += ["## Overview", "", "| source | honest | attack | steps honest | steps attack | attacks w/ attack_step | attacks w/ harm_step | monitors (streams) | units |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        units = sorted({m["unit"] for m in r["monitors"].values()})
        L.append(f"| {r['source']} | {r['by_label'].get('honest', 0)} | {r['by_label'].get('attack', 0)} | "
                 f"{r['steps_q'].get('honest', '-')} | {r['steps_q'].get('attack', '-')} | {r['attack_with_attack_step']} | "
                 f"{r['attack_with_harm_step']} | {len(r['monitors'])} ({r['n_streams']}) | {', '.join(units)} |")
    for r in results:
        L += ["", f"## {r['source']}", ""]
        for k, c in r["ctx_counts"].items():
            vals = sorted({v for (_, v) in c}, key=str)
            if k in COUNT_ONLY:
                hv = len({v for (lab, v) in c if lab == "honest"})
                av = len({v for (lab, v) in c if lab == "attack"})
                L.append(f"- **{k}**: {len(vals)} distinct (honest {hv}, attack {av})")
                continue
            cells = ", ".join(f"{v} {c.get(('honest', v), 0)}/{c.get(('attack', v), 0)}" for v in vals[:40])
            more = f", ... (+{len(vals) - 40} more)" if len(vals) > 40 else ""
            L.append(f"- **{k}** ({len(vals)} values; honest/attack): {cells}{more}")
        L += ["", "| monitor_id | unit | scale | streams (h/a) | NaN frac | AUROC(max) |", "|---|---|---|---|---|---|"]
        for mid, m in r["monitors"].items():
            sc = f"{m['scale'][0]:g}–{m['scale'][1]:g}" if m["scale"] else "?"
            L.append(f"| `{mid}` | {m['unit']} | {sc} | {m['n_streams']} ({m['n_h']}/{m['n_a']}) | {m['nan_frac']} | {m['auroc_max']} |")
    p = REPO / "results" / "data_inventory.md"
    p.parent.mkdir(exist_ok=True)
    p.write_text("\n".join(L) + "\n")
    print("wrote", p)


def main(argv):
    spot = 0
    if "--spot" in argv:
        i = argv.index("--spot")
        spot = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    skip = {"dev_fixture"}  # built by the scoring harness, not a data source
    sources = argv or sorted(p.name for p in PROCESSED.iterdir()
                             if (p / "trajectories.jsonl").exists() and p.name not in skip)
    res = [qc_source(s, spot=spot) for s in sources]
    if not argv:
        write_inventory(res)


if __name__ == "__main__":
    main(sys.argv[1:])
