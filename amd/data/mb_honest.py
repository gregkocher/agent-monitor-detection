"""MonitoringBench-Honest-550 (HF palaestraresearch/monitoringbench-honest-550, CC-BY-4.0).

550 honest Claude Opus 4.5 BashArena trajectories on 116 tasks, frequency-matched to MonitoringBench attacks.
Downloads `original_inspect_logs.zip` (98 MB; 59 `.eval` batch files, 561 samples) and `manifest.jsonl`, and keeps
only the 550 manifest samples (selected by sample UUID; the other 11 batch samples are not part of the release).

Normalization matches amd.data.monitoringbench: bash/python `command` -> `cmd`; the trailing submit() is kept
and flagged in meta (ends_with_submit, submit_step). Encrypted reasoning blobs are dropped (only visible text is
kept). The originals carry no monitor scores, so scores.jsonl is empty.

Usage: python -m amd.data.mb_honest
"""
from __future__ import annotations

import json
import zipfile
from collections import Counter

from amd.common.schema import PROCESSED, RAW, Step, Trajectory, write_jsonl
from amd.data._util import download, hf_headers, trunc
from amd.data.monitoringbench import extract_sample, iter_eval_samples

SOURCE = "mb_honest"
BASE = "https://huggingface.co/datasets/palaestraresearch/monitoringbench-honest-550/resolve/main"
RAW_DIR = RAW / SOURCE


def build():
    man_p = download(f"{BASE}/manifest.jsonl", RAW_DIR / "manifest.jsonl", hf_headers())
    zip_p = download(f"{BASE}/original_inspect_logs.zip", RAW_DIR / "original_inspect_logs.zip", hf_headers())
    manifest = [json.loads(l) for l in open(man_p) if l.strip()]
    want = {m["source_sample_uuid"]: m for m in manifest}
    outer = zipfile.ZipFile(zip_p)
    got = {}
    for name in outer.namelist():
        if not name.endswith(".eval"):
            continue
        for s in iter_eval_samples(outer.read(name)):
            if s.get("uuid") in want:
                got[s["uuid"]] = (name, extract_sample(s))
    trajs, stats = [], Counter()
    for uuid, m in want.items():
        if uuid not in got:
            stats["missing"] += 1
            continue
        fname, e = got[uuid]
        tools = e["tools"]
        md = e["meta"]
        ctx = {"setting": "basharena", "task_id": str(m["task_id"]), "main_task": str(m["task_id"]),
               "side_task": None, "policy": "honest",
               "agent_model": next((x for x in e["models"] if "opus" in x), ",".join(e["models"])) or "claude-opus-4-5",
               "main_task_description": trunc(md.get("main_task_description"), 12000)}
        meta = {"release_id": m["release_id"], "sample_uuid": uuid, "source_file": m["source_file"],
                "source_epoch": m["source_epoch"], "eval_mode": md.get("eval_mode"),
                "main_task_success": e["main_task_success"], "side_task_success_native": e["side_task_success"],
                "ends_with_submit": bool(tools) and tools[-1] == "submit",
                "submit_step": (len(tools) - 1) if tools and tools[-1] == "submit" else None,
                "renamed_command_args": e["renamed_command_args"], "tool_counts": dict(Counter(tools)),
                "models": e["models"]}
        stats[f"eval_mode={md.get('eval_mode')}"] += 1
        trajs.append(Trajectory(f"{SOURCE}:{m['release_id']}", SOURCE, "honest", ctx,
                                [Step(idx=i, **s) for i, s in enumerate(e["steps"])], meta=meta))
    n1 = write_jsonl(PROCESSED / SOURCE / "trajectories.jsonl", trajs)
    write_jsonl(PROCESSED / SOURCE / "scores.jsonl", [])
    print(f"wrote {n1} trajectories (no monitor scores); {dict(stats)}")


if __name__ == "__main__":
    build()
