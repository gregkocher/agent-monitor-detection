"""Audit 3 (r4_replay): rerun tracks/r4_replay/analyze.py unchanged from committed code + cached data,
with its OUTPUT directory redirected to results/audit3/rep_r4_rerun/ (the replay result JSONs are still read
from results/r4_replay/<arm>/; nothing under results/r4_replay is written). No API calls, no Docker.

    unset VIRTUAL_ENV; uv run python -m tracks.audit3.rep_r4_rerun
"""
from __future__ import annotations

from pathlib import Path

import tracks.r4_replay.analyze as an

OUT = Path(__file__).resolve().parents[2] / "results" / "audit3" / "rep_r4_rerun"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    an.RESULTS = OUT            # outputs only; an.RAWRES still points at results/r4_replay (replay JSONs)
    assert an.RAWRES != OUT
    return an.main(["--arms", "rewrite_control,pace_max", "--n-boot", "4000"])


if __name__ == "__main__":
    raise SystemExit(main())
