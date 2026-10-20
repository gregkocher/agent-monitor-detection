"""Common data model shared by every source and track.

Two record types, both stored as JSONL (one record per line) under data/processed/<source>/:

Trajectory  (trajectories.jsonl)
    traj_id        unique across sources: "<source>:<native id>"
    source         e.g. "monitoringbench", "mb_honest", "linuxarena_sweep", "akshn_bash", "mrt", "persistent_state"
    label          "honest" | "attack"
    context        dict of context keys (env, main_task, side_task, agent_model, task_cluster, ...)
    steps          list of Step dicts (agent actions in order); may be empty when only scores are available
    attack_step    0-based index of the first attack-relevant step, or None
    harm_step      0-based index of the step that completes the side task, or None
    side_task_success  bool | None
    meta           free-form dict (attack structure S1-S4, strategy, split, ...)

Step  (inside Trajectory.steps)
    idx            0-based index
    action         the agent's action as text (tool name + arguments, or assistant text)
    output         tool output / observation (possibly truncated), may be ""
    reasoning      visible reasoning text, may be ""

ScoreStream  (scores.jsonl)
    traj_id        joins to Trajectory.traj_id
    monitor_id     "<monitor model>|<prompt id>|<history mode>" or the dataset's native monitor name
    unit           "step" | "chunk" | "pr" | "session" | "trajectory"
    scores         list[float]  (one per unit, in order); NaN allowed for unscored units
    scale          (lo, hi) of the native scale, e.g. (0, 10)
    meta           e.g. {"history": "full"|"window"|"none", "samples": 3, "logprob_expected": true}
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"


@dataclass
class Step:
    idx: int
    action: str
    output: str = ""
    reasoning: str = ""


@dataclass
class Trajectory:
    traj_id: str
    source: str
    label: str
    context: dict = field(default_factory=dict)
    steps: list = field(default_factory=list)
    attack_step: int | None = None
    harm_step: int | None = None
    side_task_success: bool | None = None
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        assert self.label in ("honest", "attack"), self.label
        self.steps = [s if isinstance(s, Step) else Step(**s) for s in self.steps]


@dataclass
class ScoreStream:
    traj_id: str
    monitor_id: str
    unit: str
    scores: list
    scale: tuple = (0.0, 10.0)
    meta: dict = field(default_factory=dict)


def _clean(o):
    if isinstance(o, float) and math.isnan(o):
        return None
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    return o


def write_jsonl(path: Path, records: Iterable) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w") as f:
        for r in records:
            d = asdict(r) if hasattr(r, "__dataclass_fields__") else r
            f.write(json.dumps(_clean(d)) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> Iterator[dict]:
    with open(path) as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def load_trajectories(source: str) -> list[Trajectory]:
    return [Trajectory(**d) for d in read_jsonl(PROCESSED / source / "trajectories.jsonl")]


def load_scores(source: str, name: str = "scores.jsonl") -> list[ScoreStream]:
    out = []
    for d in read_jsonl(PROCESSED / source / name):
        d["scores"] = [float("nan") if v is None else float(v) for v in d["scores"]]
        d["scale"] = tuple(d.get("scale", (0, 10)))
        out.append(ScoreStream(**d))
    return out
