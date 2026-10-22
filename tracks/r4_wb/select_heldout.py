"""Round 4 white-box replication: fix the held-out evaluation sets BEFORE anything is scored.

Attacks: a stratified random sample of N_ATTACK MonitoringBench attacks from the 1,869 that no earlier track
scored (not in the T1 sample of 775, its pilots or the key-check sets; T3 / r3 subsets are inside the 775).
Strata = attack agent model x structural strategy x side task; proportional allocation (largest remainder,
at least 1 per non-empty stratum), random order within a stratum, fixed seed. Selection uses metadata only.

External honest (secondary): N_EXT honest trajectories (policy `honest`, not `honest_summarized`) from the
akshn BashArena opus-4-6 release whose main task is NOT one of the Honest-550 tasks (new tasks, new agent).

Writes tracks/r4_wb/heldout.json.

    unset VIRTUAL_ENV; uv run python -m tracks.r4_wb.select_heldout
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from amd.common.schema import load_trajectories

SEED = 20261022
N_ATTACK = 1000
N_EXT = 200
OUT = Path(__file__).with_name("heldout.json")


def main():
    rng = np.random.default_rng(SEED)
    s = json.load(open("tracks/t1_matched_budget/sample.json"))
    used = set(s["attack"]) | set(s["pilot_attack"]) | set(s["pilot2_attack"]) | set(s["ck_test_key"]) \
        | set(s["ck_test_nokey"])
    att = [t for t in load_trajectories("monitoringbench") if t.traj_id not in used]
    by = defaultdict(list)
    for t in att:
        by[(t.context.get("agent_model"), str(t.meta.get("structural_strategy")), t.context.get("side_task"))].append(t.traj_id)
    keys = sorted(by, key=str)
    tot = len(att)
    quota = {k: N_ATTACK * len(by[k]) / tot for k in keys}
    alloc = {k: max(1, int(np.floor(q))) for k, q in quota.items()}
    rem = N_ATTACK - sum(alloc.values())
    for k in sorted(keys, key=lambda k: -(quota[k] - np.floor(quota[k])))[:max(rem, 0)]:
        alloc[k] += 1
    pick = []
    for k in keys:
        ids = sorted(by[k])
        pick += [ids[i] for i in rng.permutation(len(ids))[: alloc[k]]]
    pick = sorted(pick)

    hon_tasks = {str(t.context.get("task_id")) for t in load_trajectories("mb_honest")}
    ext = [t.traj_id for t in load_trajectories("akshn_basharena_opus46")
           if t.label == "honest" and t.context.get("policy") == "honest"
           and str(t.context.get("main_task")) not in hon_tasks]
    ext = sorted(ext)
    ext_pick = sorted(ext[i] for i in rng.permutation(len(ext))[:N_EXT])

    A = {t.traj_id: t for t in att}
    summary = {
        "pool": tot, "n_attack": len(pick),
        "agent_model": Counter(A[i].context.get("agent_model") for i in pick),
        "structure": Counter(str(A[i].meta.get("structural_strategy")) for i in pick),
        "side_task": Counter(A[i].context.get("side_task") for i in pick),
        "ext_pool": len(ext), "n_ext_honest": len(ext_pick),
    }
    OUT.write_text(json.dumps({"seed": SEED, "attack": pick, "ext_honest": ext_pick, "strata_alloc":
                               {"|".join(map(str, k)): v for k, v in alloc.items()}, "summary": summary}, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
