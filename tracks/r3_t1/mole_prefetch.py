"""Fetch + build MOLE corpora ahead of the scorer (tracks/r3_t1/mole_r3.py), one at a time, under a lock file
data/processed/r2_mole/.building_<corpus> that the scorer waits on. Skips corpora already built or started by
the scorer (raw download directory present). Deletes the raw downloads after building.

    uv run python tracks/r3_t1/mole_prefetch.py kimi_k26_multiday kimi_k26_single_day ...
"""
import shutil
import subprocess
import sys
from pathlib import Path

from amd.common.schema import PROCESSED, REPO

RAW = REPO / "data" / "raw" / "r2_t1" / "mole"
HERE = Path(__file__).parent

for c in sys.argv[1:]:
    d = PROCESSED / "r2_mole" / c
    if (d / "accountdays.parquet").exists() and (d / "renders.jsonl").exists():
        print("already built", c, flush=True); continue
    if (RAW / "transcripts" / c).exists() or (RAW / "audit" / c).exists():
        print("scorer already fetching", c, flush=True); continue
    lock = PROCESSED / "r2_mole" / f".building_{c}"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.touch()
    try:
        for attempt in range(3):
            r1 = subprocess.run([sys.executable, str(HERE.parent / "r2_t1" / "mole_fetch.py"), "--corpus", c])
            r2 = subprocess.run([sys.executable, str(HERE.parent / "r2_t1" / "mole_build.py"), "--corpus", c]) \
                if r1.returncode == 0 else r1
            if r2.returncode == 0:
                break
    finally:
        for kind in ("audit", "transcripts"):
            shutil.rmtree(RAW / kind / c, ignore_errors=True)
        lock.unlink(missing_ok=True)
    print("prebuilt", c, flush=True)
