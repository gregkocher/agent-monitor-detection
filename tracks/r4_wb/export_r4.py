"""Reader inputs for the round-4 replication (rendered exactly as the pilot: export_inputs.record).

  data/processed/whitebox/inputs/mbr4.jsonl  Honest-550 (records identical to the pilot's mb.jsonl) + the 1,000
                                             held-out attacks of tracks/r4_wb/heldout.json
  data/processed/whitebox/inputs/akh.jsonl   200 external honest (akshn BashArena opus-4-6), final submit stripped

    unset VIRTUAL_ENV; uv run python -m tracks.r4_wb.export_r4
"""
from __future__ import annotations

import json

from amd.common.schema import PROCESSED, load_trajectories, read_jsonl
from tracks.wb_whitebox.export_inputs import OUT, record, write


def main():
    H = json.load(open("tracks/r4_wb/heldout.json"))
    hon = [r for r in read_jsonl(OUT / "mb.jsonl") if r["label"] == "honest"]
    assert len(hon) == 550
    # the pilot honest records must be reproduced exactly by the current renderer
    T = {t.traj_id: t for t in load_trajectories("mb_honest")}
    for r in hon[:50]:
        assert record(T[r["traj_id"]]) == r, r["traj_id"]
    att_ids = set(H["attack"])
    att = [record(t) for t in load_trajectories("monitoringbench") if t.traj_id in att_ids]
    assert len(att) == 1000
    write("mbr4", hon + att)

    ext_ids = set(H["ext_honest"])
    ext = []
    for t in load_trajectories("akshn_basharena_opus46"):
        if t.traj_id not in ext_ids:
            continue
        if t.steps and t.steps[-1].action.startswith("submit("):
            t.meta = {**t.meta, "ends_with_submit": True, "submit_step": len(t.steps) - 1}
        t.context = {**t.context, "task_id": t.context.get("main_task")}
        ext.append(record(t))
    assert len(ext) == 200
    write("akh", ext)


if __name__ == "__main__":
    main()
