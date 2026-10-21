"""Fetch only what mole_build needs for one MOLE corpus, keeping disk use small.

- transcripts: only the columns account, task_id, sim_ts, session_mode (read remotely with column projection
  via huggingface_hub.HfFileSystem; the multi-GB `messages` column is never downloaded), saved as one small parquet.
- audit: the per-event columns used by mole_build (args included, needed by the rollup), saved as parquet.
- labels.

    uv run python tracks/r2_t1/mole_fetch.py --corpus deepseek_v4_flash_single_day
"""
from __future__ import annotations

import argparse

import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem

from amd.common.schema import REPO
from amd.data._util import hf_token

RAW = REPO / "data" / "raw" / "r2_t1" / "mole"
BASE = "datasets/forgelab/mole/data"
T_COLS = ["account", "task_id", "sim_ts", "session_mode"]
A_COLS = ["event_id", "ts", "account", "service", "action", "resource_id", "args", "exit_code", "bytes",
          "dest_domain", "is_external", "task_id"]


def fetch(fs, kind, corpus, cols):
    files = sorted(fs.glob(f"{BASE}/{kind}/{corpus}/*.parquet"))
    out = RAW / kind / corpus
    out.mkdir(parents=True, exist_ok=True)
    tabs = []
    for f in files:
        with fs.open(f, "rb", block_size=8 << 20) as fh:
            tabs.append(pq.read_table(fh, columns=cols))
        print(f"  {f}: {tabs[-1].num_rows} rows", flush=True)
    import pyarrow as pa
    t = pa.concat_tables(tabs)
    pq.write_table(t, out / "0000.parquet")
    return t.num_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    a = ap.parse_args()
    fs = HfFileSystem(token=hf_token())
    print("transcripts", fetch(fs, "transcripts", a.corpus, T_COLS))
    print("audit", fetch(fs, "audit", a.corpus, A_COLS))
    print("labels", fetch(fs, "labels", a.corpus, None))


if __name__ == "__main__":
    main()
