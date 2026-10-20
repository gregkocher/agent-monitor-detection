"""Select base MonitoringBench attacks for track 3 refinement.

Multi-step attacks (structure S2-S4) with a known onset (meta.first_attack_step) and a known
execution step (attack_step), of bounded length, stratified across side-task family x structure so
the refined set is balanced. Deterministic given (n, seed).

    uv run python -m tracks.t3_aware_attacker.select_attacks --n 160 --seed 0 --out selection.json
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from amd.common.schema import PROCESSED, load_trajectories

HERE = Path(__file__).resolve().parent
MIN_STEPS = 6
MAX_STEPS = 55          # bound per-attack scoring cost (full-mode history grows with length)
STRUCTURES = ("S2", "S3", "S4")
# Track 1 scores a 775-attack sample for free; restricting to it means the "nothing" (original)
# arm's per-step streams come from track 1 and track 3 only pays for the refined attacks.
T1_SAMPLE = Path(__file__).resolve().parents[1] / "t1_matched_budget" / "sample.json"


def candidates(within_t1: bool = True) -> list:
    keep = None
    if within_t1 and T1_SAMPLE.exists():
        keep = set(json.loads(T1_SAMPLE.read_text())["attack"])
    out = []
    for t in load_trajectories("monitoringbench"):
        m = t.meta
        if keep is not None and t.traj_id not in keep:
            continue
        if m.get("structural_strategy") not in STRUCTURES:
            continue
        if t.attack_step is None or m.get("first_attack_step") is None:
            continue
        n = len(t.steps)
        if not (MIN_STEPS <= n <= MAX_STEPS):
            continue
        if t.side_task_success is False:
            continue
        out.append(t)
    return out


def select(n: int, seed: int, within_t1: bool = True) -> list[str]:
    import random

    rng = random.Random(seed)
    cands = candidates(within_t1)
    # stratify by (side_task, structure)
    strata: dict = defaultdict(list)
    for t in cands:
        strata[(t.context.get("side_task"), t.meta.get("structural_strategy"))].append(t.traj_id)
    for k in strata:
        rng.shuffle(strata[k])
    keys = sorted(strata)
    picked: list[str] = []
    # round-robin across strata for balance
    i = 0
    while len(picked) < min(n, len(cands)):
        k = keys[i % len(keys)]
        if strata[k]:
            picked.append(strata[k].pop())
        i += 1
        if i > len(keys) * (MAX_STEPS + n):
            break
    return picked


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=160)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--within-t1", action="store_true", default=True)
    ap.add_argument("--no-within-t1", dest="within_t1", action="store_false")
    ap.add_argument("--out", default="selection.json")
    a = ap.parse_args(argv)
    cands = candidates(a.within_t1)
    ids = select(a.n, a.seed, a.within_t1)
    by_id = {t.traj_id: t for t in load_trajectories("monitoringbench")}
    from collections import Counter

    strat = Counter((by_id[i].context.get("side_task"), by_id[i].meta.get("structural_strategy")) for i in ids)
    out_path = HERE / a.out
    out_path.write_text(json.dumps({"n_requested": a.n, "seed": a.seed, "n_candidates": len(cands),
                                    "n_selected": len(ids), "traj_ids": ids}, indent=2))
    print(f"candidates={len(cands)} selected={len(ids)} -> {out_path}")
    for k in sorted(strat):
        print(f"  {k}: {strat[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
