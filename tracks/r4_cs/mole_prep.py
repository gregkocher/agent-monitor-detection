"""Rebuild MOLE account-day renders for round 4 (the round-2/3 renders were deleted after scoring).

    unset VIRTUAL_ENV; uv run python tracks/r4_cs/mole_prep.py --corpus gpt53_single_day [--corpus ...]

Runs the round-2 fetch + build code unchanged (tracks/r2_t1/mole_fetch.py, mole_build.py) with its input/output
directories redirected to data/raw/r4_cs/mole and data/processed/r4_mole/<corpus>, so the round-2/3 processed files
are never overwritten. Then checks that the rebuilt account-day table matches the round-2/3 one (same accounts,
days, attack-day labels, event counts) and deletes the raw downloads (renders.jsonl is kept until scoring is done).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "r2_t1"))
import mole_build  # noqa: E402
import mole_fetch  # noqa: E402

from amd.common.schema import PROCESSED, REPO  # noqa: E402

RAW4 = REPO / "data" / "raw" / "r4_cs" / "mole"
OUT4 = PROCESSED / "r4_mole"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", action="append", required=True)
    a = ap.parse_args()
    mole_fetch.RAW = RAW4
    mole_build.RAW = RAW4
    mole_build.OUT = OUT4
    from huggingface_hub import HfFileSystem

    from amd.data._util import hf_token
    fs = HfFileSystem(token=hf_token())
    for c in a.corpus:
        if (OUT4 / c / "renders.jsonl").exists() and (OUT4 / c / "accountdays.parquet").exists():
            print(f"{c}: already built", flush=True)
            continue
        print(f"{c}: fetch", flush=True)
        mole_fetch.fetch(fs, "transcripts", c, mole_fetch.T_COLS)
        mole_fetch.fetch(fs, "audit", c, mole_fetch.A_COLS)
        mole_fetch.fetch(fs, "labels", c, None)
        print(f"{c}: build", flush=True)
        mole_build.build(c, renders_on=True)
        new = pd.read_parquet(OUT4 / c / "accountdays.parquet")
        old_p = PROCESSED / "r2_mole" / c / "accountdays.parquet"
        if old_p.exists():
            old = pd.read_parquet(old_p)
            k = ["account", "day"]
            m = old[k + ["attack_day", "n_events", "is_insider"]].merge(
                new[k + ["attack_day", "n_events", "is_insider"]], on=k, how="outer", suffixes=("_old", "_new"),
                indicator=True)
            same = (m._merge == "both").all() and all((m[f"{x}_old"] == m[f"{x}_new"]).all()
                                                       for x in ("attack_day", "n_events", "is_insider"))
            print(f"{c}: rebuilt table matches round 2/3: {same} ({len(old)} vs {len(new)} rows)", flush=True)
        for kind in ("audit", "transcripts", "labels"):
            shutil.rmtree(RAW4 / kind / c, ignore_errors=True)


if __name__ == "__main__":
    main()
