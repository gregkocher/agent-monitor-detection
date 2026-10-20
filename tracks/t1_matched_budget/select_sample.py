"""Round 2 sample: which MonitoringBench attacks / Honest-550 trajectories T1 re-scores per step.

- Attacks: all S4 (distributed) + a stratified sample of S1, S2, S3 (N_PER_S each, round-robin over
  side tasks so every side task is represented), fixed seed.
- Honest: all 550 of mb_honest.
- Pilot: PILOT_ATTACK attacks (half S4, rest spread over S1-S3) + PILOT_HONEST honest.

Writes tracks/t1_matched_budget/sample.json with traj_id lists. Run:
    unset VIRTUAL_ENV; uv run python tracks/t1_matched_budget/select_sample.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from amd.common.schema import load_trajectories

SEED = 20261020
N_PER_S = 100
PILOT_ATTACK = 20
PILOT_HONEST = 20
OUT = Path(__file__).with_name("sample.json")


def stratified(trajs, n, rng):
    """Round-robin over side tasks, random order within each side task."""
    by = defaultdict(list)
    for t in trajs:
        by[t.context.get("side_task")].append(t)
    pools = [list(rng.permutation(v)) for _, v in sorted(by.items())]
    out = []
    while len(out) < n and any(pools):
        for p in pools:
            if p and len(out) < n:
                out.append(p.pop())
    return out


def main():
    rng = np.random.default_rng(SEED)
    att = load_trajectories("monitoringbench")
    hon = load_trajectories("mb_honest")
    by_s = defaultdict(list)
    for t in att:
        by_s[t.meta.get("structural_strategy")].append(t)
    sample = {"S4": [t.traj_id for t in by_s["S4"]]}
    for s in ("S1", "S2", "S3"):
        sample[s] = [t.traj_id for t in stratified(by_s[s], N_PER_S, rng)]
    attacks = [i for s in ("S1", "S2", "S3", "S4") for i in sample[s]]
    honest = [t.traj_id for t in hon]
    # pilot: 10 S4 + 10 spread over S1-S3; 20 honest
    pa = list(rng.choice(sample["S4"], PILOT_ATTACK // 2, replace=False))
    for j, s in enumerate(("S1", "S2", "S3", "S1", "S3", "S2", "S3", "S1", "S3", "S2")[:PILOT_ATTACK - len(pa)]):
        pa.append(sample[s][j])
    ph = list(rng.choice(honest, PILOT_HONEST, replace=False))
    # pilot2: 8 more S4 attacks (not in the pilot) to measure the cost of chained scheduling
    rest = [x for x in sample["S4"] if x not in set(pa)]
    p2 = [str(x) for x in rng.choice(rest, 8, replace=False)]
    OUT.write_text(json.dumps({"seed": SEED, "attack_by_structure": sample, "attack": attacks,
                               "honest": honest, "pilot_attack": [str(x) for x in pa],
                               "pilot_honest": [str(x) for x in ph], "pilot2_attack": p2}, indent=1))
    steps = {t.traj_id: min(len(t.steps), 60) for t in att + hon}
    print({k: len(v) for k, v in sample.items()}, "attacks", len(attacks), "honest", len(honest))
    print("steps: attack", sum(steps[i] for i in attacks), "honest", sum(steps[i] for i in honest),
          "pilot", sum(steps[i] for i in pa + ph))


if __name__ == "__main__":
    main()
