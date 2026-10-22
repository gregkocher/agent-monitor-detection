"""Batch-replay a set of structured attack samples (originals or rewrites) in BashArena, each in its
own fresh Docker sandbox, and collect official side_task_success. Runs replay_run.py under the
control-arena venv (CA_PY) once per sample, with a wall-clock cap so a hung command can't stall the
batch. Parallel workers are safe: Inspect gives each eval a uniquely-named compose project.

    uv run python -m tracks.r4_replay.replay_batch --arm orig --samples-file /tmp/r4_base35.json \
        --workers 2 --per-sample-timeout 900

`--arm orig` reads data/raw/r4_replay/structured/<uuid>.json; any other arm reads
data/raw/r4_replay/rewrites/<arm>/<uuid>.json. Results -> results/r4_replay/<arm>/<uuid>.json and a
combined summary.jsonl. Resumable (skips existing result files).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CA_PY = os.environ.get("CA_PY", "/tmp/ca_probe/.venv/bin/python")
STRUCT = REPO / "data" / "raw" / "r4_replay" / "structured"
REWRITES = REPO / "data" / "raw" / "r4_replay" / "rewrites"
RUNNER = REPO / "tracks" / "r4_replay" / "replay_run.py"


def sample_path(arm: str, uuid: str) -> Path:
    return (STRUCT / f"{uuid}.json") if arm == "orig" else (REWRITES / arm / f"{uuid}.json")


def run_one(arm: str, uuid: str, outdir: Path, timeout: int) -> dict:
    out = outdir / f"{uuid}.json"
    if out.exists():
        try:
            return json.loads(out.read_text())
        except Exception:
            pass
    sp = sample_path(arm, uuid)
    if not sp.exists():
        rec = {"uuid": uuid, "arm": arm, "status": "no_sample", "side_task_success": None}
        out.write_text(json.dumps(rec))
        return rec
    env = dict(os.environ)
    hf = Path.home() / ".hf_token"
    if hf.exists():
        env.setdefault("HF_TOKEN", hf.read_text().strip())
    try:
        subprocess.run([CA_PY, str(RUNNER), "--sample", str(sp), "--out", str(out)],
                       env=env, timeout=timeout, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        rec = {"uuid": uuid, "arm": arm, "status": "wallclock_timeout", "side_task_success": None}
        out.write_text(json.dumps(rec))
        return rec
    if out.exists():
        rec = json.loads(out.read_text())
        rec["arm"] = arm
        return rec
    rec = {"uuid": uuid, "arm": arm, "status": "no_output", "side_task_success": None}
    out.write_text(json.dumps(rec))
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--samples-file", required=True, help="JSON list of uuids")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--per-sample-timeout", type=int, default=900)
    a = ap.parse_args(argv)
    uuids = json.loads(Path(a.samples_file).read_text())
    outdir = REPO / "results" / "r4_replay" / a.arm
    outdir.mkdir(parents=True, exist_ok=True)
    print(f"arm={a.arm} n={len(uuids)} workers={a.workers}", flush=True)
    recs = []
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(run_one, a.arm, u, outdir, a.per_sample_timeout): u for u in uuids}
        for fu in as_completed(futs):
            rec = fu.result()
            recs.append(rec)
            print(f"  [{len(recs)}/{len(uuids)}] {rec.get('uuid')} "
                  f"status={rec.get('status')} side_task_success={rec.get('side_task_success')}",
                  flush=True)
    (outdir / "summary.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    ok = sum(1 for r in recs if r.get("side_task_success") is True)
    scored = sum(1 for r in recs if r.get("side_task_success") is not None)
    print(f"DONE arm={a.arm}: side_task_success {ok}/{scored} scored ({len(recs)} total)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
