"""Fetch per-trajectory metadata (monitor maxima, environment, tasks, success flags) for every public
LinuxArena run from the public data API (https://data.linuxarena.ai, no auth; the same CC-BY data as the HF
mirror anonymouslinuxarena/linuxarena-public). Only small metadata fields are kept: no transcripts, no
descriptions. Output: data/raw/r4_ctx/la_runs.json and data/raw/r4_ctx/la_traj_meta.jsonl (one row per
trajectory, `run_id` attached).

Note: the list endpoint (no documents) reports monitor maxima x10 relative to the documents endpoint
(0-1000 vs 0-100); checked on 5 trajectories. We divide by 10 and keep the documents scale (0-100).

    unset VIRTUAL_ENV; uv run python tracks/r4_ctx/fetch_linuxarena.py
"""
from __future__ import annotations

import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "raw" / "r4_ctx"
API = "https://data.linuxarena.ai/api"
KEEP = ["trajectory_id", "run_id", "environment_id", "main_task_id", "side_task_id", "main_task_success",
        "side_task_success", "monitors", "actions_count", "attempts_mt", "attempts_st", "attempts_sneaky", "error",
        "tags", "time_started"]


def get(url, tries=5):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def fetch_run(run):
    rid, rows, page = run["run_id"], [], 1
    while True:
        d = get(f"{API}/trajectories?run_id={rid}&page={page}&page_size=500")
        for it in d["items"]:
            r = {k: it.get(k) for k in KEEP}
            r["run_id"] = rid
            if r["monitors"]:
                r["monitors"] = {m: {"max": (None if v.get("max") is None else v["max"] / 10.0),
                                     "unscored": v.get("unscored")} for m, v in r["monitors"].items()}
            rows.append(r)
        if page >= d.get("total_pages", 1):
            return rows
        page += 1


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    runs = get(f"{API}/runs?page=1&page_size=1000")["items"]
    (OUT / "la_runs.json").write_text(json.dumps(runs))
    print(len(runs), "runs", flush=True)
    n = 0
    with ThreadPoolExecutor(4) as ex, open(OUT / "la_traj_meta.jsonl", "w") as f:
        for rows in ex.map(fetch_run, runs):
            for r in rows:
                f.write(json.dumps(r) + "\n")
            n += len(rows)
    print(n, "trajectories", flush=True)



def fetch_task_categories(run_ids):
    """main_task_id -> task_category from the documents endpoint (descriptions are discarded)."""
    out = {}

    def one(rid):
        res, page = {}, 1
        while True:
            d = get(f"{API}/trajectories?run_id={rid}&documents=true&page={page}&page_size=200")
            for it in d["items"]:
                mt = it.get("main_task") or {}
                if mt.get("id"):
                    res[mt["id"]] = mt.get("task_category")
            if page >= d.get("total_pages", 1):
                return res
            page += 1

    with ThreadPoolExecutor(4) as ex:
        for res in ex.map(one, run_ids):
            out.update(res)
    return out


if __name__ == "__main__":
    main()
