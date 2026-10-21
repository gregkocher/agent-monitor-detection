"""Stream sets for the round-2 persistent-state re-scoring (one per monitor x history mode x attack policy).

Each run is a stream of 5 per-PR scores. Honest = 171 honest runs; attacks = gradual (120) or positional (400).
Runs with any unscored PR in EITHER history mode of a monitor are dropped from both modes, so the two modes of
a monitor are compared on exactly the same runs (paired). The original GPT-4o streams are included for
reference under the same filter.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "t1_matched_budget"))
from t1lib import StreamSet  # noqa: E402

from amd.common.schema import PROCESSED, load_trajectories, read_jsonl  # noqa: E402

MODES = ("current_only", "full_diffs")
SHORT = {"openai/gpt-4.1-mini": "gpt-4.1-mini", "google/gemini-2.5-flash": "gemini-2.5-flash",
         "openai/gpt-4o": "gpt-4o(orig)"}


def available_models():
    out = []
    for f in sorted((PROCESSED / "persistent_state").glob("r2_scores_*_current_only.jsonl")):
        slug = f.name[len("r2_scores_"):-len("_current_only.jsonl")]
        if (PROCESSED / "persistent_state" / f"r2_scores_{slug}_full_diffs.jsonl").exists():
            out.append(slug)
    return out


def _streams(path, score="expected"):
    out = {}
    for r in read_jsonl(path):
        s = np.array([np.nan if v is None else float(v) for v in r["scores"]], float)
        if score == "int":
            s = np.array([np.nan if v is None else float(v) for v in r["meta"]["int_scores"]], float)
        out[r["traj_id"]] = s
    return out


def _orig_streams(key):
    out = {}
    for r in read_jsonl(PROCESSED / "persistent_state" / "scores.jsonl"):
        if r["monitor_id"] == f"openai/gpt-4o|{key}":
            out[r["traj_id"]] = np.array([np.nan if v is None else float(v) for v in r["scores"]], float)
    return out


def make_sets(by_mode: dict, label: str, T: dict, policies=("gradual", "positional"), require_complete=True):
    """by_mode: {mode: {traj_id: stream}} -> list of StreamSets (same runs across modes)."""
    ids = set.intersection(*(set(d) for d in by_mode.values()))
    if require_complete:
        ids = {i for i in ids if all(np.isfinite(d[i]).all() for d in by_mode.values())}
    out = []
    for mode, d in by_mode.items():
        for pol in policies:
            H, A, hid, aid, on, hm, am = [], [], [], [], [], [], []
            for tid in sorted(ids):
                t = T[tid]
                if t.label == "honest":
                    H.append(d[tid]); hid.append(tid)
                elif t.context["policy"] == pol:
                    A.append(d[tid]); aid.append(tid)
                    on.append(t.attack_step); hm.append(t.harm_step)
                    am.append({"policy": pol, "side_task": t.context.get("side_task"),
                               "side_task_success": t.side_task_success, "app": t.context.get("app"),
                               "target_position": t.context.get("target_position")})
            out.append(StreamSet(f"ps2:{label}:{mode}:{pol}", H, A, hid, aid, None, None, on, hm, am, [], "pr",
                                 "iid split (5 apps)"))
    return out


def r2_ps_sets(score="expected", include_orig=True, policies=("gradual", "positional")):
    T = {t.traj_id: t for t in load_trajectories("persistent_state")}
    sets = []
    for slug in available_models():
        bm = {m: _streams(PROCESSED / "persistent_state" / f"r2_scores_{slug}_{m}.jsonl", score) for m in MODES}
        lab = slug.split("_", 1)[1] if "_" in slug else slug
        sets += make_sets(bm, lab + ("" if score == "expected" else "-int"), T, policies)
    if include_orig and score == "expected":
        bm = {"current_only": _orig_streams("score_pr_diff_current_only|current_only"),
              "full_diffs": _orig_streams("score_pr_diff_full_diffs|full_diffs")}
        sets += make_sets(bm, "gpt-4o-orig", T, policies)
    return sets
