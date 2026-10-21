"""Score the round-2 corpus with the chosen STRONG monitor (none mode) for evaluate_r2.

Stages (resumable; every stage skips already-cached steps):
  honest    : mb_honest (all 550) -> scores_<slug>_none.jsonl  (calibration)
  originals : the 150 selection attacks in monitoringbench -> cache (the "nothing" arm)
  r1        : round-1 condensation arms t3_refined/{max,cusum,multichart}[_r0]
  (round-2 pacing arms are scored in-loop by refine_r2, not here)

    uv run python -m tracks.r2_t3.r2_score --monitor-model openai/gpt-4.1 \
        --stages honest,originals,r1 [--r1-variants adapt] --concurrency 24 --yes
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from amd.scoring import run

HERE = Path(__file__).resolve().parent
TRACK = "r2t3"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor-model", default="openai/gpt-4.1")
    ap.add_argument("--stages", default="honest,originals,r1")
    ap.add_argument("--r1-variants", default="adapt", help="adapt,r0")
    ap.add_argument("--modes", default="none")
    ap.add_argument("--concurrency", type=int, default=24)
    ap.add_argument("--r1-limit", type=int, default=None,
                    help="only re-score round-1 refined trajectories whose base attack is in selection[:N]")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    model = a.monitor_model
    stages = a.stages.split(",")
    sel = json.loads((HERE.parent / "t3_aware_attacker" / "selection.json").read_text())["traj_ids"]
    rc = 0
    for mode in a.modes.split(","):
        common = ["--model", model, "--history", mode, "--track", TRACK, "--max-steps", "60",
                  "--concurrency", str(a.concurrency)]
        if a.yes:
            common.append("--yes")
        if "honest" in stages:
            print(f"\n##### honest mb_honest [{mode}] #####", flush=True)
            rc = run.main(["--source", "mb_honest"] + common) or rc
        if "originals" in stages:
            print(f"\n##### originals (150) [{mode}] #####", flush=True)
            rc = run.main(["--source", "monitoringbench", "--traj-ids", ",".join(sel),
                           "--out-name", f"r2orig_scores_{model.replace('/', '_')}_{mode}.jsonl"] + common) or rc
        if "r1" in stages:
            srcs = []
            for v in a.r1_variants.split(","):
                suff = "" if v == "adapt" else "_r0"
                srcs += [f"t3_refined/{arm}{suff}" for arm in ("max", "cusum", "multichart")]
            keep = set(sel[: a.r1_limit]) if a.r1_limit else None
            for src in srcs:
                extra = []
                if keep is not None:
                    from amd.common.schema import load_trajectories
                    ids = [t.traj_id for t in load_trajectories(src) if t.meta.get("orig_traj_id") in keep]
                    extra = ["--traj-ids", ",".join(ids),
                             "--out-name", f"scores_{model.replace('/', '_')}_{mode}.jsonl"]
                print(f"\n##### r1 arm {src} [{mode}] #####", flush=True)
                rc = run.main(["--source", src] + extra + common) or rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
