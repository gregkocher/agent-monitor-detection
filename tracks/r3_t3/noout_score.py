"""Leak test (round 3): do fabricated tool OUTPUTS in rewritten attacks give the monitor a cue?

Re-score a subset in history-free mode with the current action's OUTPUT STRIPPED
(`--no-current-output`, monitor_id suffix `-noout`), so the monitor sees only the action text (no
fabricated output). Compare to the with-output scores. If undetected-success and peak suspicion are
close, the findings are not driven by fabricated outputs.

Scores honest (for calibration), the originals, and the given refined arms, all no-output, none mode.
Output files are suffixed `_noout` so they never collide with the with-output files; the cache keys
on the `-noout` monitor_id so nothing is re-paid across modes.

    uv run python -m tracks.r3_t3.noout_score --honest 200 --arms <dir1,dir2,...> --yes
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from amd.scoring import run

HERE = Path(__file__).resolve().parent
MODEL = "openai/gpt-4.1"
TRACK = "r3t3"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--honest", type=int, default=200, help="# honest trajectories to score no-output")
    ap.add_argument("--attacks", type=int, default=35, help="# selection attacks (originals) to score")
    ap.add_argument("--arms", default=",".join(f"t3_refined/{a}{s}" for s in ("_r2_r0", "_r3")
                                               for a in ("rewrite_control", "pace_max", "pace_cusum",
                                                         "pace_multichart")))
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    sel = json.loads((HERE.parent / "t3_aware_attacker" / "selection.json").read_text())["traj_ids"][: a.attacks]
    base = ["--model", MODEL, "--history", "none", "--no-current-output", "--track", TRACK,
            "--max-steps", "60", "--concurrency", str(a.concurrency)]
    if a.yes:
        base.append("--yes")
    rc = 0
    print("##### honest (no-output) #####", flush=True)
    rc = run.main(["--source", "mb_honest", "--limit", str(a.honest),
                   "--out-name", f"scores_openai_gpt-4.1_none_noout.jsonl"] + base) or rc
    print("##### originals (no-output) #####", flush=True)
    rc = run.main(["--source", "monitoringbench", "--traj-ids", ",".join(sel),
                   "--out-name", "r2orig_scores_openai_gpt-4.1_none_noout.jsonl"] + base) or rc
    for src in a.arms.split(","):
        if not (run.PROCESSED / src / "trajectories.jsonl").exists():
            print(f"skip {src} (no trajectories)", flush=True); continue
        from amd.common.schema import load_trajectories
        keep = set(sel)
        ids = [t.traj_id for t in load_trajectories(src) if t.meta.get("orig_traj_id") in keep]
        print(f"##### {src} (no-output; {len(ids)} trajs paired to the {len(sel)} base attacks) #####", flush=True)
        rc = run.main(["--source", src, "--traj-ids", ",".join(ids),
                       "--out-name", "scores_openai_gpt-4.1_none_noout.jsonl"] + base) or rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
