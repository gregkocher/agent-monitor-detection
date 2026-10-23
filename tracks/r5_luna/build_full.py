"""Rebuild aksh-n trajectories with UNTRUNCATED actions for the full-text arm (H5d).

Runs the unchanged loader `amd.data.akshn.build_set` with its action cap lifted (ACTION_CHARS -> 10**9) and its output
directory redirected to data/r5_luna/full/<source>/ (data/processed is not touched). Outputs, reasoning and task text
keep the ingest caps. Then verifies, per trajectory, that the step count equals the processed trajectory's and that
`amd.data._util.trunc(full_action, 4000)` reproduces every processed action exactly (same segmentation, only the
middle of long actions restored). Writes data/r5_luna/full/<source>/verify.json.

    unset VIRTUAL_ENV; uv run python -m tracks.r5_luna.build_full akshn_basharena_opus46 akshn_linuxarena
"""
from __future__ import annotations

import json
import sys

import amd.data.akshn as A
from amd.common.schema import PROCESSED, read_jsonl
from amd.data._util import ACTION_CHARS, trunc

from .lunalib import FULL_DIR


def main(names):
    A.ACTION_CHARS = 10 ** 9
    A.PROCESSED = FULL_DIR
    for src in names:
        A.build_set(src)
        (FULL_DIR / src / "scores.jsonl").unlink(missing_ok=True)   # identical to the processed streams
        proc = {d["traj_id"]: d for d in read_jsonl(PROCESSED / src / "trajectories.jsonl")}
        full = {d["traj_id"]: d for d in read_jsonl(FULL_DIR / src / "trajectories.jsonl")}
        bad_n, bad_txt, n_long, n_steps, lost = 0, 0, 0, 0, []
        for t, d in proc.items():
            f = full.get(t)
            if f is None or len(f["steps"]) != len(d["steps"]):
                bad_n += 1
                continue
            for sp, sf in zip(d["steps"], f["steps"]):
                n_steps += 1
                if trunc(sf["action"], ACTION_CHARS) != sp["action"]:
                    bad_txt += 1
                if len(sf["action"]) > ACTION_CHARS:
                    n_long += 1
                    lost.append(len(sf["action"]))
        v = dict(source=src, n_traj=len(proc), n_steps=n_steps, step_count_mismatch=bad_n, text_mismatch=bad_txt,
                 n_steps_over_cap=n_long, median_full_chars_over_cap=sorted(lost)[len(lost) // 2] if lost else None,
                 max_full_chars=max(lost) if lost else None)
        (FULL_DIR / src / "verify.json").write_text(json.dumps(v, indent=1))
        print(v, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
