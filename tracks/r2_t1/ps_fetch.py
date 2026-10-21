"""Re-extract the FULL per-PR diffs and task descriptions of the persistent-state runs.

The processed persistent_state trajectories keep only 3,000 chars of each PR diff (median full diff 39k chars),
which is not enough to re-score PRs with new monitors. This script re-reads, over HTTP range requests, the
top-level `metadata` of every PR sample of every eval file used by data/processed/persistent_state and stores
the untruncated `pr_diff` and `main_task_description` (secrets scrubbed exactly as the loader does) in
data/raw/r2_t1/ps_full/<eval task id>.json  ->  {"file": ..., "prs": {pr_idx: {name, desc, diff}}}

    uv run python tracks/r2_t1/ps_fetch.py [--workers 4]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

from amd.common.schema import REPO, load_trajectories
from amd.data._util import hf_headers, open_remote_zip
from amd.data.persistent_state import (RESOLVE, _pr_index, _sample_metadata, _scrub, task_id)

OUT = REPO / "data" / "raw" / "r2_t1" / "ps_full"
LISTING = REPO / "data" / "raw" / "persistent_state" / "listing.json"


def fetch(path: str) -> dict:
    tid = task_id(path)
    dest = OUT / f"{tid}.json"
    if dest.exists():
        return json.loads(dest.read_text())
    z = open_remote_zip(RESOLVE + quote(path), hf_headers())
    prs = {}
    for n in z.namelist():
        if not n.startswith("samples/"):
            continue
        sid = n[len("samples/"):].removesuffix("_epoch_1.json")
        try:
            k = _pr_index(sid)
        except AttributeError:
            continue
        md = _sample_metadata(z, n)
        if not md:
            continue
        secrets = {v for kk, v in md.items() if isinstance(v, str) and re.search(r"key|token|secret", kk, re.I)}
        prs[k] = {"sample_id": sid, "name": md.get("main_task_name"),
                  "desc": _scrub(md.get("main_task_description") or "", secrets),
                  "diff": _scrub(md.get("pr_diff") or "", secrets),
                  "n_secret_hits": sum((md.get("pr_diff") or "").count(s) for s in secrets if s and len(s) >= 6)}
    out = {"path": path, "file": path.rsplit("/", 1)[-1], "prs": prs}
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    tmp.write_text(json.dumps(out))
    tmp.rename(dest)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    listing = json.loads(LISTING.read_text())
    by_file = {p.rsplit("/", 1)[-1]: p for ps in listing.values() for p in ps}
    files = set()
    for t in load_trajectories("persistent_state"):
        files.update(t.meta["eval_files"][:2] if t.context["policy"] == "positional" else t.meta["eval_files"][:1])
    paths = sorted(by_file[f] for f in files)
    print(f"{len(paths)} eval files", flush=True)

    def run(p):
        for attempt in range(8):
            try:
                return p, fetch(p)
            except Exception as e:  # noqa: BLE001
                resp = getattr(e, "response", None)
                if attempt == 7:
                    return p, e
                wait = 15 * 2 ** min(attempt, 3)
                if resp is not None and resp.status_code == 429:
                    try:
                        wait = max(wait, float(resp.headers.get("retry-after", 0)))
                    except ValueError:
                        pass
                time.sleep(wait + random.random() * 5)

    bad = 0
    with ThreadPoolExecutor(a.workers) as ex:
        for k, (p, r) in enumerate(ex.map(run, paths)):
            if isinstance(r, Exception):
                bad += 1
                print(f"  FAILED {p}: {type(r).__name__}: {str(r)[:200]}", flush=True)
            if (k + 1) % 50 == 0:
                print(f"  {k + 1}/{len(paths)}", flush=True)
    print(f"done; failed={bad}")


if __name__ == "__main__":
    main()
