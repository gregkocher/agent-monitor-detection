"""SQLite cache of per-call monitor results, so re-runs never re-pay.

Key: (traj_id, step, monitor_id); step = -1 for trajectory-level scores. Each row stores the parsed result
and a hash of the exact prompt. A row whose prompt hash differs from the current prompt (the trajectory
data or the rendering changed) is treated as stale and re-scored. API failures are never cached; parse
failures (no `SCORE:` line) are cached with status "parse_fail" and re-tried only with --retry-failed.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path


def prompt_sha(messages: list[dict]) -> str:
    return hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()[:16]


class ScoreCache:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS scores (
            traj_id TEXT, step INTEGER, monitor_id TEXT, status TEXT, result TEXT, created REAL,
            PRIMARY KEY (traj_id, step, monitor_id))""")
        self.db.commit()

    def get(self, traj_id: str, step: int, monitor_id: str) -> tuple[str, dict] | None:
        r = self.db.execute("SELECT status, result FROM scores WHERE traj_id=? AND step=? AND monitor_id=?",
                            (traj_id, step, monitor_id)).fetchone()
        return (r[0], json.loads(r[1])) if r else None

    def put(self, traj_id: str, step: int, monitor_id: str, status: str, result: dict) -> None:
        self.db.execute("INSERT OR REPLACE INTO scores VALUES (?,?,?,?,?,?)",
                        (traj_id, step, monitor_id, status, json.dumps(result), time.time()))
        self.db.commit()

    def close(self):
        self.db.close()
