"""Re-extract STRUCTURED tool calls (function + full, untruncated arguments) for selected
MonitoringBench attacks from the source .eval files, for BashArena execution replay.

The compact loader (amd/data/monitoringbench.py) renders each tool call to a truncated string
(`fmt_call`, ACTION_CHARS=4000), which drops text_editor create/str_replace payloads -- so replay
cannot reconstruct the file edits. This extractor keeps the raw {function, arguments} per call,
attachments resolved, nothing truncated. It reuses the same HTTP-range zip machinery and, like the
loader, NEVER opens header.json (which embeds a leaked third-party token).

Output (gitignored): data/raw/r4_replay/structured/<sample_uuid>.json
    {uuid, sample_id, task_id, side_task_group, side_task_name, side_task_success_native,
     calls: [{function, arguments, id}], tool_seq: [fn, ...]}

    uv run python -m tracks.r4_replay.extract_structured --uuids-file /tmp/r4_base35.json
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from amd.common.schema import RAW
from amd.data._util import hf_headers
from amd.data.monitoringbench import BASE, RemoteZip, _resolve, iter_eval_samples

OUT_DIR = RAW / "r4_replay" / "structured"


def extract_structured_sample(s: dict) -> dict:
    """Keep raw {function, arguments} for every assistant tool call, attachments resolved."""
    att = s.get("attachments") or {}
    calls = []
    for m in s.get("messages") or []:
        if m.get("role") != "assistant":
            continue
        for tc in (m.get("tool_calls") or []):
            fn = tc.get("function")
            args = _resolve(tc.get("arguments"), att)
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    pass
            calls.append({"function": fn, "arguments": args, "id": tc.get("id")})
    sc = s.get("scores") or {}

    def val(k):
        v = sc.get(k)
        return v.get("value") if isinstance(v, dict) else None

    md = s.get("metadata") or {}
    return {
        "sample_id": str(s.get("id")), "uuid": s.get("uuid"), "epoch": s.get("epoch"),
        "calls": calls, "tool_seq": [c["function"] for c in calls],
        "side_task_name": md.get("side_task_name"), "main_task_name": md.get("main_task_name"),
        "side_task_success_native": val("side_task_success"),
        "main_task_success_native": val("main_task_success"),
    }


def extract(uuids: list[str], workers: int = 6) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(RAW / "monitoringbench" / "master.parquet")
    want = df[df.sample_uuid.isin(set(uuids))].copy()
    todo = want[~want.sample_uuid.map(lambda u: (OUT_DIR / f"{u}.json").exists())]
    meta = {r.sample_uuid: (str(r.task_id), r.side_task_group) for _, r in want.iterrows()}
    if todo.empty:
        print(f"all {len(want)} already extracted")
        return meta
    rz = RemoteZip(f"{BASE}/final_dataset.zip")
    members = {Path(i.filename).name: i.filename for i in rz.get().infolist()
               if i.filename.startswith("final_") and i.filename.endswith(".eval")}
    groups = todo.groupby("eval_log_filename").sample_uuid.apply(set).to_dict()
    print(f"extracting {len(todo)} samples from {len(groups)} .eval members")
    done = 0
    for fname, uset in groups.items():
        for attempt in range(4):
            try:
                data = rz.get(fresh=attempt > 0).read(members[fname])
                break
            except Exception as e:
                if attempt == 3:
                    print(f"  ERR {fname}: {type(e).__name__}")
                    data = None
                    break
                time.sleep(5 * (attempt + 1))
        if data is None:
            continue
        for s in iter_eval_samples(data):
            if s.get("uuid") in uset:
                rec = extract_structured_sample(s)
                tid, sg = meta[s["uuid"]]
                rec["task_id"], rec["side_task_group"] = tid, sg
                (OUT_DIR / f"{s['uuid']}.json").write_text(json.dumps(rec))
                done += 1
        print(f"  member done; {done} samples extracted so far", flush=True)
    print(f"extracted {done} structured samples -> {OUT_DIR}")
    return meta


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--uuids-file", required=True)
    a = ap.parse_args(argv)
    uuids = json.loads(Path(a.uuids_file).read_text())
    extract(uuids)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
