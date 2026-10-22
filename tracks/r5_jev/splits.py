"""Fixed dev / evaluation split for track r5jev, chosen on metadata only (no scores are read).

    unset VIRTUAL_ENV; uv run python -m tracks.r5_jev.splits

Writes tracks/r5_jev/splits.json:
  sources[src] = {group_key, dev_groups, eval_honest, eval_attack, dev_honest_sample, dev_attack_sample,
                  nano_honest, nano_attack}
- Groups: main task when the setting has >= 20 distinct main tasks, else the trajectory.
- Dev = a seeded random 10% of the groups. Every trajectory of a dev group is excluded from evaluation.
- Dev JEV pilot sample: up to 40 honest + 40 attack trajectories of dev groups per source.
- MonitoringBench: honest = Honest-550; evaluation attacks = the 1,775 attacks that have gpt-4.1-mini `none`
  per-step scores (775 T1 sample + 1,000 r4_wb held-out) minus dev groups; dev attacks may come from any of
  the 2,644.
- aksh-n: honest trajectories without a Gemini step-unit stream (BashArena `honest_summarized`) are not
  eligible (no second-stage score per step).
- nano subset (H2 on aksh-n): per setting a seeded random min(400, n) honest and min(300, n) attack evaluation
  trajectories, plus up to 100 more honest from a second seeded draw (min(500, n) honest in total). MonitoringBench nano uses every evaluation trajectory.
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

from amd.common.schema import PROCESSED, read_jsonl

SEED = 20261022
HERE = Path(__file__).resolve().parent
AKSHN = ["akshn_bash", "akshn_agentdojo", "akshn_iac", "akshn_shade", "akshn_basharena_opus46",
         "akshn_basharena_sonnet45", "akshn_linuxarena"]
GEMINI = "gemini-3.1-pro|akshn_local|full"


def _meta(src):
    return [(d["traj_id"], d["label"], (d.get("context") or {}).get("main_task")) for d in
            read_jsonl(PROCESSED / src / "trajectories.jsonl")]


def _step_ids(src, mid=None, name="scores.jsonl"):
    ids = set()
    for d in read_jsonl(PROCESSED / src / name):
        if mid is None or d["monitor_id"] == mid:
            ids.add(d["traj_id"])
    return ids


def _split(rows, eligible_h, eligible_a, rng, n_dev=40, nano=(400, 300)):
    tasks = {t for _, _, t in rows if t is not None}
    by_task = len(tasks) >= 20
    gid = {tid: (f"task:{t}" if by_task else f"traj:{tid}") for tid, _, t in rows}
    groups = sorted(set(gid.values()))
    rng.shuffle(groups)
    dev = set(groups[:max(1, round(0.10 * len(groups)))])
    eh = sorted(t for t, lab, _ in rows if lab == "honest" and gid[t] not in dev and t in eligible_h)
    ea = sorted(t for t, lab, _ in rows if lab == "attack" and gid[t] not in dev and t in eligible_a)
    dh = sorted(t for t, lab, _ in rows if lab == "honest" and gid[t] in dev)
    da = sorted(t for t, lab, _ in rows if lab == "attack" and gid[t] in dev)
    dhs, das = sorted(rng.sample(dh, min(n_dev, len(dh)))), sorted(rng.sample(da, min(n_dev, len(da))))
    out = dict(group_key="main_task" if by_task else "traj_id", n_groups=len(groups), dev_groups=sorted(dev),
               group_of={t: gid[t] for t, _, _ in rows if t in set(eh) | set(ea) | set(dhs) | set(das)},
               eval_honest=eh, eval_attack=ea, dev_honest_sample=dhs, dev_attack_sample=das)
    if nano:
        out["nano_honest"] = sorted(rng.sample(eh, min(nano[0], len(eh))))
        out["nano_attack"] = sorted(rng.sample(ea, min(nano[1], len(ea))))
    return out


def main():
    rng = random.Random(SEED)
    res = {"seed": SEED, "sources": {}}
    # MonitoringBench: honest from mb_honest, attacks from monitoringbench (one task universe)
    rows = _meta("mb_honest") + _meta("monitoringbench")
    scored = (_step_ids("monitoringbench", name="scores_openai_gpt-4.1-mini_none.jsonl")
              | _step_ids("monitoringbench", name="r4wb_scores_openai_gpt-4.1-mini_none.jsonl"))
    honest = {t for t, lab, _ in rows if lab == "honest"}
    res["sources"]["mb"] = _split(rows, honest, scored, rng, nano=None)
    for src in AKSHN:
        rows = _meta(src)
        elig = _step_ids(src, GEMINI)
        res["sources"][src] = _split(rows, elig, elig, rng)
    # LinuxArena sweep (secondary): no dev; every trajectory is evaluation
    rows = _meta("linuxarena_sweep")
    res["sources"]["linuxarena_sweep"] = dict(
        group_key="main_task", eval_honest=sorted(t for t, l, _ in rows if l == "honest"),
        eval_attack=sorted(t for t, l, _ in rows if l == "attack"), dev_groups=[], dev_honest_sample=[],
        dev_attack_sample=[], group_of={t: f"task:{m}" for t, _, m in rows})
    # nano honest extension (separate seeded draw, so the dev samples above are unchanged): up to 100 more
    # evaluation honest per aksh-n setting, giving ~250 calibration honest per split at 1% FPR
    rng2 = random.Random(SEED + 1)
    for src in AKSHN:
        d = res["sources"][src]
        rest = sorted(set(d["eval_honest"]) - set(d["nano_honest"]))
        d["nano_honest"] = sorted(set(d["nano_honest"]) | set(rng2.sample(rest, min(100, len(rest)))))
    (HERE / "splits.json").write_text(json.dumps(res, indent=0))
    for s, d in res["sources"].items():
        print(f"{s:26s} groups={d.get('n_groups')} by={d['group_key']:9s} dev_groups={len(d['dev_groups']):4d} "
              f"eval h/a={len(d['eval_honest'])}/{len(d['eval_attack'])} dev sample h/a="
              f"{len(d['dev_honest_sample'])}/{len(d['dev_attack_sample'])} "
              f"nano h/a={len(d.get('nano_honest', []))}/{len(d.get('nano_attack', []))}")


if __name__ == "__main__":
    main()
