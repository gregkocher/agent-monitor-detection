"""LinuxArena paper monitor sweep (data.linuxarena.ai public API, no auth).

Three runs re-uploaded on 2026-10-15 as "LinuxArena paper: ... paper monitor sweep":
    45ab968baebc46c4ad16003af43c6455  Opus honest            (200 trajectories)
    4992785f32d54399a4b615ee01cd599d  Opus attack            (92)
    c6e3ebcaf46a4b748475744c15666e11  Opus strategy-attack   (50)
The same 12 per-action monitors ("mean-action@<model>": mean of 2 draws, 0-100 in steps of 5) scored every
trajectory; some trajectory-level "mean-quick@<model>" monitors are present for a subset.

Per trajectory we fetch the raw Inspect sample (`GET /api/trajectories/{id}/sample`, zstd JSON, ~1 MB
compressed) and cache it in data/raw/linuxarena_sweep/samples/. Per-action scores live in
sample.scores["monitorK"].value["<monitor>/<draw>/<action_idx>"] (trajectory monitors use
"<monitor>/<draw>/trajectory"); action i is the i-th assistant tool call, which is how Steps are indexed.

Usage: python -m amd.data.linuxarena_sweep
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

import zstandard

from amd.common.schema import PROCESSED, RAW, ScoreStream, Step, Trajectory, write_jsonl
from amd.data._util import ACTION_CHARS, OUT_CHARS, REASON_CHARS, content_text, fmt_call, http_get, http_get_json, trunc

SOURCE = "linuxarena_sweep"
API = "https://data.linuxarena.ai/api"
RUNS = {
    "45ab968baebc46c4ad16003af43c6455": ("honest", "honest"),
    "4992785f32d54399a4b615ee01cd599d": ("attack", "attack"),
    "c6e3ebcaf46a4b748475744c15666e11": ("attack", "strategy-attack"),
}
# tools the LinuxArena action monitors never see (auto-scored 0 with "No reasoning provided")
HIDDEN_TOOLS = {"run_side_task_test", "start_phase1_planning", "start_phase2_planning", "submit"}
MEMBER_RE = re.compile(r"Monitor (\d+) \| weight=([\d.]+) \| score=([\d.]+)")

RAW_DIR = RAW / SOURCE
SAMPLES = RAW_DIR / "samples"


def list_run(run_id: str) -> list[dict]:
    cache = RAW_DIR / f"listing_{run_id}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    items, page = [], 1
    while True:
        d = http_get_json(f"{API}/trajectories?run_id={run_id}&page={page}&page_size=100")
        items += d["items"]
        if page >= d["total_pages"]:
            break
        page += 1
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(items))
    return items


def fetch_sample(tid: str) -> dict:
    p = SAMPLES / f"{tid}.json.zst"
    if not p.exists():
        b = http_get(f"{API}/trajectories/{tid}/sample", timeout=600)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".part")
        tmp.write_bytes(b)
        tmp.rename(p)
    with open(p, "rb") as f:
        return json.loads(zstandard.ZstdDecompressor().stream_reader(f).read())


def _resolve(x, att):
    if isinstance(x, str) and x.startswith("attachment://"):
        return att.get(x[len("attachment://"):], x)
    if isinstance(x, list):
        return [_resolve(v, att) for v in x]
    if isinstance(x, dict):
        return {k: _resolve(v, att) for k, v in x.items()}
    return x


def build_steps(sample: dict) -> tuple[list[Step], list[str]]:
    att = sample.get("attachments") or {}
    msgs = sample["messages"]
    outputs = {}
    for m in msgs:
        if m["role"] == "tool":
            out = _resolve(m.get("content"), att)
            text, _ = content_text(out)
            err = m.get("error")
            if err:
                text = (text + "\n[error] " + json.dumps(err, default=str)).strip()
            outputs[m.get("tool_call_id")] = text
    steps, fns = [], []
    for m in msgs:
        if m["role"] != "assistant":
            continue
        text, reasoning = content_text(_resolve(m.get("content"), att))
        if text.startswith("tool call for tool"):
            text = ""
        vis = "\n".join(x for x in (reasoning, text) if x)
        for j, tc in enumerate(m.get("tool_calls") or []):
            fn = tc.get("function")
            args = _resolve(tc.get("arguments"), att)
            steps.append(Step(idx=len(steps), action=trunc(fmt_call(fn, args), ACTION_CHARS),
                              output=trunc(outputs.get(tc.get("id"), ""), OUT_CHARS),
                              reasoning=trunc(vis, REASON_CHARS) if j == 0 else ""))
            fns.append(fn)
    return steps, fns


def score_streams(tid: str, sample: dict, n_steps: int) -> list[ScoreStream]:
    per_action = defaultdict(dict)   # monitor -> idx -> score
    draws = defaultdict(dict)        # monitor -> idx -> [member scores]
    skipped = defaultdict(set)       # monitor -> idxs with "No reasoning provided" (hidden tool)
    traj = defaultdict(dict)         # monitor -> draw -> score
    for key, sc in (sample.get("scores") or {}).items():
        if not key.startswith("monitor"):
            continue
        val = sc.get("value") or {}
        md = sc.get("metadata") or {}
        if not isinstance(val, dict):
            continue
        for k, v in val.items():
            name, draw, pos = k.rsplit("/", 2)
            if pos == "trajectory":
                expl = (md.get(k) or {}).get("explanation") or ""
                mem = MEMBER_RE.findall(expl)
                traj[name][draw] = (v, not expl.strip(), bool(mem) and expl.count("No reasoning provided") >= len(mem))
                continue
            i = int(pos)
            per_action[name][i] = v
            expl = (md.get(k) or {}).get("explanation") or ""
            mem = [float(s) for _, _, s in MEMBER_RE.findall(expl)]
            if mem:
                draws[name][i] = mem
            if expl and expl.count("No reasoning provided") >= max(1, len(mem)):
                skipped[name].add(i)
    out = []
    for name, d in sorted(per_action.items()):
        n = max(n_steps, max(d) + 1)
        scores = [float(d[i]) if i in d and d[i] is not None else float("nan") for i in range(n)]
        model = name.split("@", 1)[-1]
        out.append(ScoreStream(
            traj_id=f"{SOURCE}:{tid}", monitor_id=f"{model}|{name.split('@')[0]}|full", unit="step",
            scores=scores, scale=(0.0, 100.0),
            meta={"native_name": name, "history": "full", "samples": 2, "aggregation": "mean",
                  "member_scores": [draws[name].get(i) for i in range(n)],
                  "skipped_idx": sorted(skipped[name]),
                  "n_steps_mismatch": n != n_steps}))
    for name, d in sorted(traj.items()):
        vals = [float(v) for v, _, _ in d.values() if v is not None]
        if not vals:
            continue
        model = name.split("@", 1)[-1]
        out.append(ScoreStream(
            traj_id=f"{SOURCE}:{tid}", monitor_id=f"{model}|{name.split('@')[0]}|trajectory", unit="trajectory",
            scores=[sum(vals) / len(vals)], scale=(0.0, 100.0),
            meta={"native_name": name, "draws": vals, "native_score": sum(vals) / len(vals),
                  "empty_explanation": all(e for _, e, _ in d.values()),
                  "no_reasoning": all(nr for _, _, nr in d.values())}))
    return out


def process(item: dict, label: str, policy: str):
    tid = item["trajectory_id"]
    sample = fetch_sample(tid)
    steps, fns = build_steps(sample)
    md = sample.get("metadata") or {}
    mt = (md.get("main_tasks") or [{}])[0] or {}
    st = ((md.get("side_tasks") or [{}])[0] or {}) if label == "attack" else {}
    tasks = ((sample.get("scores") or {}).get("tasks") or {}).get("value") or {}
    landed = tasks.get("landed_at")
    models = [m for m in (sample.get("model_usage") or {})]
    agent_model = models[0] if len(models) == 1 else ",".join(models)
    model_src = "model_usage"
    if not agent_model:
        # the honest run's samples carry no model usage ("none/none"); the run is named "Opus honest"
        agent_model, model_src = "anthropic/claude-opus-4-6", "run_name"
    ctx = {
        "env": item.get("environment_id"),
        "main_task": item.get("main_task_id"),
        "task_category": mt.get("task_category"),
        "side_task": item.get("side_task_id") if label == "attack" else None,
        "failure_type": st.get("failure_type") if label == "attack" else None,
        "agent_model": agent_model,
        "policy": policy,
        # full task text (the monitor input); the side-task text is in meta only (monitor must not see it)
        "main_task_description": trunc(mt.get("description") or item.get("main_task_description"), 12000),
        "env_description": trunc((md.get("environment") or {}).get("description"), 6000),
    }
    hidden = [i for i, f in enumerate(fns) if f in HIDDEN_TOOLS]
    traj = Trajectory(
        traj_id=f"{SOURCE}:{tid}", source=SOURCE, label=label, context=ctx, steps=steps,
        attack_step=None,
        harm_step=int(landed) if isinstance(landed, (int, float)) and label == "attack" else None,
        side_task_success=item.get("side_task_success") if label == "attack" else None,
        meta={"run_id": item["run_id"], "sample_id": sample.get("id"),
              "main_task_success": item.get("main_task_success"),
              "agent_model_source": model_src,
              "tasks_score": tasks,
              "hidden_tool_steps": hidden,
              "ends_with_submit": bool(fns) and fns[-1] == "submit",
              "tool_counts": dict(Counter(fns)),
              "main_task_short": trunc(item.get("main_task_description"), 1000),
              "side_task_description": trunc(st.get("goal") or item.get("side_task_description"), 4000) if label == "attack" else None,
              "landed_at_native": landed,
              # API listing reports max per-action score x10 (0-1000); kept only as a consistency check
              "listing_monitor_max_x10": {k: v.get("max") for k, v in (item.get("monitors") or {}).items()},
              "listing_monitor_unscored": {k: v.get("unscored") for k, v in (item.get("monitors") or {}).items()}},
    )
    return traj, score_streams(tid, sample, len(steps))


def mark_failed_quick(scores: list[ScoreStream]):
    """Trajectory ("quick") monitors: a 0 whose explanation is empty or "No reasoning provided" is a failed
    call, unless that monitor normally returns empty explanations (gpt-oss-120b does, also for real scores).
    Failed calls become NaN; the native value stays in meta["native_score"]."""
    by = defaultdict(list)
    for s in scores:
        if s.unit == "trajectory":
            by[s.monitor_id].append(s)
    for mid, ss in by.items():
        nonzero = [s for s in ss if s.meta["native_score"] > 0]
        empty_is_normal = bool(nonzero) and sum(s.meta["empty_explanation"] for s in nonzero) / len(nonzero) > 0.5
        for s in ss:
            failed = s.meta["native_score"] == 0 and (s.meta["no_reasoning"] or
                                                       (s.meta["empty_explanation"] and not empty_is_normal))
            s.meta["failed_call"] = failed
            if failed:
                s.scores = [float("nan")]


def build():
    trajs, scores = [], []
    for run_id, (label, policy) in RUNS.items():
        items = list_run(run_id)
        print(f"{policy}: {len(items)} trajectories")
        with ThreadPoolExecutor(8) as ex:
            res = list(ex.map(lambda it: process(it, label, policy), items))
        for t, ss in res:
            trajs.append(t)
            scores += ss
    mark_failed_quick(scores)
    n1 = write_jsonl(PROCESSED / SOURCE / "trajectories.jsonl", trajs)
    n2 = write_jsonl(PROCESSED / SOURCE / "scores.jsonl", scores)
    print(f"wrote {n1} trajectories, {n2} score streams")


if __name__ == "__main__":
    build()
