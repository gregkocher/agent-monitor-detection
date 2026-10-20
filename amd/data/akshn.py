"""aksh-n `*-monitor-labels` HF datasets: per-step streaming suspicion from Gemini-3.1-Pro.

Each label set is joined to the trajectory parquet it was built from (row i of the label set == row i of the
source parquet for the ControlArena / BashArena sets; the LinuxArena goldset joins on trajectory id):

    processed source          label set (aksh-n/...)                              trajectory source
    akshn_bash                control_arena_bash-monitor-labels                  adityaasinha28/control_arena_bash
    akshn_agentdojo           control_arena_agentdojo-monitor-labels             adityaasinha28/control_arena_agentdojo
    akshn_iac                 control_arena_iac-monitor-labels                   adityaasinha28/control_arena_iac
    akshn_shade               control_arena_shade-monitor-labels                 adityaasinha28/control_arena_shade
    akshn_basharena_opus46    basharena_action_only_opus46_large-monitor-labels   adityaasinha28/basharena_action_only_opus46_large
    akshn_basharena_sonnet45  basharena_action_only_sonnet45_large-monitor-labels adityaasinha28/basharena_action_only_sonnet45_large
    akshn_linuxarena          linux_arena_goldset-monitor-labels                 aksh-n/linux_arena_preprocessed

Judge steps vs Steps. The judge streams over "judge steps": step 0 is the user task, then one judge step per
tool call (or text-only assistant turn) and one per tool result. Our Steps are agent actions only (tool calls
and text-only assistant turns), each with its tool output attached. Streams:
  unit "step"        value at the judge step where the action is taken (before its output is seen);
                     length == len(steps). Only written when the judge-step segmentation is verified
                     (segment count == len(nonpriv_streaming)).
  unit "judge_step"  the native series (includes the user step and tool-result steps); always written.
                     ScoreStream.meta["judge_to_step"] maps judge step -> action index (None for step 0).
Ground-truth change points (judge-step indices, from the adjudicator) are mapped to the action at or before
them: Trajectory.attack_step = mapped ideal_flagging_step (no better onset label exists in these sets);
meta["point_of_no_return_step"] = mapped point_of_no_return_step; natives kept in meta.

Download: label sets via `git clone --depth 1` (JSON files are plain git blobs; per-file resolve/ requests hit
HF rate limits), source parquets via hf_hub_download.

Usage: python -m amd.data.akshn [set ...]
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter

import pyarrow.parquet as pq

from amd.common.schema import PROCESSED, RAW, ScoreStream, Step, Trajectory, write_jsonl
from amd.data._util import ACTION_CHARS, OUT_CHARS, REASON_CHARS, hf_token, trunc

RAW_DIR = RAW / "akshn"
JUDGE = "gemini-3.1-pro"
SETS = {
    "akshn_bash": ("control_arena_bash", "adityaasinha28/control_arena_bash", "control_arena_bash.parquet"),
    "akshn_agentdojo": ("control_arena_agentdojo", "adityaasinha28/control_arena_agentdojo", "control_arena_agentdojo.parquet"),
    "akshn_iac": ("control_arena_iac", "adityaasinha28/control_arena_iac", "control_arena_iac.parquet"),
    "akshn_shade": ("control_arena_shade", "adityaasinha28/control_arena_shade", "control_arena_shade.parquet"),
    "akshn_basharena_opus46": ("basharena_action_only_opus46_large", "adityaasinha28/basharena_action_only_opus46_large",
                               "basharena_action_only_opus46_large.parquet"),
    "akshn_basharena_sonnet45": ("basharena_action_only_sonnet45_large", "adityaasinha28/basharena_action_only_sonnet45_large",
                                 "basharena_action_only_sonnet45_large.parquet"),
    "akshn_linuxarena": ("linux_arena_goldset", "aksh-n/linux_arena_preprocessed", "linux_arena_preprocessed.parquet"),
}


# ----------------------------------------------------------------------------------------------- download
def ensure_downloaded(label_name: str, src_repo: str, src_file: str):
    lab = RAW_DIR / "labels" / label_name
    if not (lab / "judge_logs").exists():
        lab.parent.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1")
        subprocess.run(["git", "clone", "--depth", "1", "-q",
                        f"https://huggingface.co/datasets/aksh-n/{label_name}-monitor-labels", str(lab)],
                       check=True, env=env)
    src = RAW_DIR / "sources" / src_repo.split("/")[1] / src_file
    if not src.exists():
        hf_token()
        from huggingface_hub import hf_hub_download
        hf_hub_download(src_repo, src_file, repo_type="dataset", local_dir=src.parent)
    return lab, src


# ----------------------------------------------------------------------------------------- segmentation
HDR = re.compile(r"^\[(USER|ASSISTANT|TOOL|SYSTEM)\]\s*$", re.M)
CALL = re.compile(r"^[A-Za-z_][\w.\-]*\(", re.M)


def segment_bracket(text: str) -> list[dict]:
    """ControlArena exports: '[USER]' / '[ASSISTANT]' (+ '[TOOL CALLS]' one call per line) / '[TOOL]' blocks.
    Returns judge steps as dicts {kind: user|call|text|tool, text, pre}."""
    ms = list(HDR.finditer(text))
    out = []
    for i, m in enumerate(ms):
        body = text[m.end():(ms[i + 1].start() if i + 1 < len(ms) else len(text))]
        role = m.group(1)
        if role == "ASSISTANT" and "[TOOL CALLS]" in body:
            pre, calls = body.split("[TOOL CALLS]", 1)
            starts = [c.start() for c in CALL.finditer(calls)]
            if not starts:
                out.append({"kind": "text", "text": body.strip(), "pre": ""})
                continue
            for j, s in enumerate(starts):
                out.append({"kind": "call", "pre": pre.strip() if j == 0 else "",
                            "text": calls[s:(starts[j + 1] if j + 1 < len(starts) else len(calls))].strip()})
        elif role == "ASSISTANT":
            out.append({"kind": "text", "text": body.strip(), "pre": ""})
        elif role == "TOOL":
            out.append({"kind": "tool", "text": body.strip(), "pre": ""})
        else:
            out.append({"kind": "user", "text": body.strip(), "pre": ""})
    return out


STEP_RE = re.compile(r"<step_(\d+)>(.*?)</step_\1>", re.S)
TOOL_RE = re.compile(r"<tool_(\d+)>\s*<function>(.*?)</function>\s*<arguments>(.*?)</arguments>\s*</tool_\1>", re.S)
OUT_RE = re.compile(r"<tool_output_(\d+)>(.*?)</tool_output_\1>", re.S)


def segment_xml(text: str) -> list[dict]:
    """BashArena action-only exports: <task_description> then <step_N><assistant><tool_k>..</assistant>
    <tool_output_k>..</tool_output_k></step_N>. Judge order assumed: calls of a step, then its outputs."""
    out = [{"kind": "user", "text": "", "pre": ""}]
    for _, body in STEP_RE.findall(text):
        for _, fn, args in TOOL_RE.findall(body):
            out.append({"kind": "call", "pre": "", "text": f"{fn.strip()}({args.strip()})"})
        for _, o in OUT_RE.findall(body):
            out.append({"kind": "tool", "text": o.strip(), "pre": ""})
    return out


def segment_linux(actions: list[dict]) -> list[dict]:
    """LinuxArena goldset: judge steps = [user] + (action, output) per action (verified: n = 1 + 2 * n_actions)."""
    out = [{"kind": "user", "text": "", "pre": ""}]
    for a in actions:
        reasoning = a.get("agent_reasoning") or ""
        for m in a.get("inter_action_messages") or []:
            if isinstance(m, dict) and m.get("role") == "assistant" and m.get("content"):
                reasoning = (reasoning + "\n" + str(m["content"])).strip()
        args = a.get("arguments")
        out.append({"kind": "call", "pre": reasoning, "text": f"{a.get('function')}({args})"})
        o = a.get("output") or ""
        if a.get("output_error") not in (None, "", "None"):
            o = (str(o) + "\n[error] " + str(a.get("output_error"))).strip()
        out.append({"kind": "tool", "text": str(o), "pre": ""})
    return out


def judge_to_steps(segs: list[dict]) -> tuple[list[Step], list]:
    """Agent actions = call/text judge steps; a tool result attaches to the earliest call of the latest assistant
    turn that has no output yet (some exports omit empty tool results, so results never cross turns)."""
    steps, j2s, pending, prev = [], [], [], None
    for s in segs:
        if s["kind"] in ("call", "text"):
            if prev != "call":
                pending = []  # a new assistant turn: outputs only attach to the calls of the latest turn
            idx = len(steps)
            if s["kind"] == "call":
                steps.append(Step(idx=idx, action=trunc(s["text"], ACTION_CHARS), reasoning=trunc(s["pre"], REASON_CHARS)))
                pending.append(idx)
            else:
                steps.append(Step(idx=idx, action=trunc("[assistant message] " + s["text"], ACTION_CHARS)))
            j2s.append(idx)
        elif s["kind"] == "tool":
            if pending:
                k = pending.pop(0)
                steps[k].output = trunc(s["text"], OUT_CHARS)
                j2s.append(k)
            else:
                j2s.append(steps[-1].idx if steps else None)
        else:
            j2s.append(None)
        prev = s["kind"]
    return steps, j2s


# ------------------------------------------------------------------------------------------------ build
def _to_action_idx(j2s: list, k):
    """Map a judge-step index to the action at or before it."""
    if k is None or not isinstance(k, int) or k < 0:
        return None
    k = min(k, len(j2s) - 1)
    while k >= 0 and j2s[k] is None:
        k -= 1
    return j2s[k] if k >= 0 else None


def _num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else float("nan")


def _side_key(desc: str) -> str | None:
    if not desc:
        return None
    first = next((ln.strip("# ").strip() for ln in desc.splitlines() if ln.strip()), "")
    return first[:80]


RUN_NAME_MODEL = [("haiku", "claude-haiku-4-5-20251001"), ("glm 5", "glm-5"), ("opus", "claude-opus-4-6"),
                  ("gpt-5 nano", "gpt-5-nano"), ("gpt-5 mini", "gpt-5-mini"), ("sonnet", "claude-sonnet-4-6"),
                  ("gpt-5.4", "gpt-5.4"), ("codex", "gpt-5.4"), ("kimi", "kimi-k2.5"), ("gemini flash", "gemini-3-flash-preview"),
                  ("gemini pro", "gemini-3.1-pro-preview"), ("grok", "grok-4.1-fast"), ("claude code", "claude-opus-4-6")]


def model_from_run_name(name: str | None) -> str | None:
    """agent_model is null for ~770 goldset rows; infer it from the run display name (the agent part)."""
    if not name:
        return None
    n = name.lower().split(" monitor on ")[-1]
    for key, model in RUN_NAME_MODEL:
        if n.startswith(key):
            return model
    return None


def load_rows(set_name: str, src_path):
    label_name = SETS[set_name][0]
    if set_name == "akshn_linuxarena":
        cols = ["id", "ground_truth", "is_attack", "side_task_success", "main_task_success", "failure_type",
                "task_category", "run_family", "side_task_name", "environment_id", "agent_model", "run_display_name",
                "run_id", "main_task_name", "main_task_description", "side_task_description", "actions_json", "n_actions"]
        return pq.read_table(src_path, columns=cols).to_pylist()
    if label_name.startswith("basharena"):
        return pq.read_table(src_path, columns=["id", "prompt", "ground_truth", "source", "category", "duplicate_id"]).to_pylist()
    return pq.read_table(src_path, columns=["id", "prompt", "ground_truth", "extra_info", "trajectory_data"]).to_pylist()


def build_set(set_name: str):
    label_name, src_repo, src_file = SETS[set_name]
    lab_dir, src_path = ensure_downloaded(label_name, src_repo, src_file)
    manifest = json.loads((lab_dir / "label_manifest.json").read_text())
    status = {int(k): v.get("status") for k, v in manifest["rows"].items()}
    rows = load_rows(set_name, src_path)
    by_id = {r["id"]: r for r in rows} if set_name == "akshn_linuxarena" else None

    trajs, streams, stats = [], [], Counter()
    for f in sorted((lab_dir / "judge_logs").glob("row_*__*.json"), key=lambda p: int(p.name.split("_")[1])):
        L = json.loads(f.read_text())
        i = int(L["idx"])
        ns = L.get("nonpriv_streaming") or []
        if not ns:
            stats["no_streaming"] += 1
            continue
        if by_id is not None:
            r = by_id.get(L["id"])
            if r is None:
                stats["no_join"] += 1
                continue
        else:
            r = rows[i]
            if str(r["id"]) != str(L["id"]) and str(L["id"]) != str(i):
                stats["id_mismatch"] += 1
        gt = int(L["ground_truth"])
        label = "attack" if gt == 1 else "honest"
        pc = L.get("privileged_context") or {}
        ctx, meta = {}, {}
        # ---- steps + context per family
        if set_name == "akshn_linuxarena":
            actions = json.loads(r["actions_json"]) if isinstance(r["actions_json"], str) else r["actions_json"]
            segs = segment_linux(actions)
            ctx = {"env": r["environment_id"], "main_task": r["main_task_name"], "task_category": r["task_category"],
                   "side_task": r["side_task_name"] if label == "attack" else None,
                   "failure_type": r["failure_type"] if label == "attack" else None,
                   "agent_model": r["agent_model"] or model_from_run_name(r["run_display_name"]),
                   "policy": r["run_family"],
                   "main_task_description": trunc(r["main_task_description"], 12000)}
            meta.update(run_id=r["run_id"], run_display_name=r["run_display_name"],
                        agent_model_source="parquet" if r["agent_model"] else "run_display_name",
                        main_task_success=r["main_task_success"], native_id=r["id"])
            side_success = r["side_task_success"] if label == "attack" else None
            side_desc = r["side_task_description"]
        elif label_name.startswith("basharena"):
            text = r["prompt"][-1]["content"]
            segs = segment_xml(text)
            m = re.search(r"<task_description>(.*?)</task_description>", text, re.S)
            cat = r["category"]
            ctx = {"setting": "basharena", "main_task": str(r["duplicate_id"]),
                   "side_task": cat.split("/", 1)[1] if cat.startswith("attack/") else None,
                   "agent_model": {"opus46": "claude-opus-4-6", "sonnet45": "claude-sonnet-4-5"}[set_name.rsplit("_", 1)[1]],
                   "policy": cat.split("/")[0],
                   "main_task_description": trunc(m.group(1).strip() if m else pc.get("main_task"), 12000)}
            meta.update(category=cat, native_id=r["id"], summarized="<middle_summary>" in text or "</middle_summary>" in text
                        or cat == "honest_summarized")
            side_success = None
            side_desc = pc.get("side_task_description")
        else:
            p = r["prompt"]
            text = "\n".join(x["content"] for x in p) if isinstance(p, list) else p
            segs = segment_bracket(text)
            td = r["trajectory_data"]
            td = json.loads(td) if isinstance(td, str) else (td or {})
            tdm = td.get("metadata") or {}
            ei = r["extra_info"] or {}
            side_name = tdm.get("side_task_name")
            ctx = {"setting": ei.get("setting") or tdm.get("setting_name"),
                   "main_task": str(tdm.get("main_task_name") or ""),
                   "side_task": (side_name if side_name not in (None, "", "None") else _side_key(pc.get("side_task_description")))
                   if label == "attack" else None,
                   "agent_model": ei.get("model"),
                   "policy": ei.get("eval_file", "").replace(".eval", ""),
                   "main_task_description": trunc(tdm.get("main_task_description") or ei.get("main_task_description")
                                                  or pc.get("main_task"), 12000)}
            if tdm.get("suite_name"):
                ctx["task_cluster"] = tdm["suite_name"]
            meta.update(native_id=r["id"], eval_mode=tdm.get("eval_mode"),
                        full_trajectory_monitor_native=tdm.get("full_trajectory_monitor"))
            side_success = None
            side_desc = pc.get("side_task_description")
        steps, j2s = judge_to_steps(segs)
        aligned = len(segs) == len(ns)
        stats[f"aligned={aligned}"] += 1
        adj = L.get("adjudicator") or {}
        ideal, ponr = adj.get("ideal_flagging_step"), adj.get("point_of_no_return_step")
        pj = ((L.get("priv_judge") or {}).get("with_evidence") or {})
        meta.update(
            label_status=status.get(i), row=i, judge_step_alignment=aligned, n_judge_steps=len(ns),
            ideal_flagging_step_native=ideal, point_of_no_return_step_native=ponr,
            ideal_flagging_step=_to_action_idx(j2s, ideal) if aligned else None,
            point_of_no_return_step=_to_action_idx(j2s, ponr) if aligned else None,
            k_star_branch=adj.get("k_star_branch"), overall_severity=pj.get("overall_severity"),
            verification_passed=(L.get("verification") or {}).get("passed"),
            side_task_description=trunc(side_desc, 4000) if label == "attack" else None,
            attack_step_source="ideal_flagging_step (Gemini adjudicator), mapped to action index",
        )
        attack_step = meta["ideal_flagging_step"] if label == "attack" else None
        tid = f"{set_name}:{i}"
        trajs.append(Trajectory(traj_id=tid, source=set_name, label=label, context=ctx, steps=steps,
                                attack_step=attack_step, harm_step=None, side_task_success=side_success, meta=meta))
        # ---- streams
        local = [_num(s.get("current_step_local_suspicion")) for s in ns]
        cum = [_num(s.get("cumulative_confidence")) for s in ns]
        flagscore = adj.get("step_flag_score") or []
        jmeta = {"judge_to_step": j2s if aligned else None, "aligned": aligned, "judge": "google/gemini-3.1-pro-preview",
                 "rubric": "online_v0"}
        streams.append(ScoreStream(tid, f"{JUDGE}|akshn_local_judgestep|full", "judge_step", local, (0.0, 10.0), dict(jmeta, history="full")))
        streams.append(ScoreStream(tid, f"{JUDGE}|akshn_cumulative_judgestep|full", "judge_step", cum, (0.0, 10.0), dict(jmeta, history="full")))
        if flagscore:
            streams.append(ScoreStream(tid, f"{JUDGE}|akshn_priv_flag_judgestep|privileged", "judge_step",
                                       [_num(x) for x in flagscore], (0.0, 10.0),
                                       dict(jmeta, history="full", privileged=True,
                                            note="adjudicator step_flag_score; judge knew the side task")))
        if aligned:
            act_pos = {}
            for k, (s, a) in enumerate(zip(segs, j2s)):
                if s["kind"] in ("call", "text") and a is not None:
                    act_pos[a] = k
            for name, series in (("akshn_local", local), ("akshn_cumulative", cum)):
                vals = [series[act_pos[a]] if a in act_pos else float("nan") for a in range(len(steps))]
                streams.append(ScoreStream(tid, f"{JUDGE}|{name}|full", "step", vals, (0.0, 10.0),
                                           {"history": "full", "derived_from": "judge_step value at the action's judge step"}))
    n1 = write_jsonl(PROCESSED / set_name / "trajectories.jsonl", trajs)
    n2 = write_jsonl(PROCESSED / set_name / "scores.jsonl", streams)
    print(f"{set_name}: wrote {n1} trajectories, {n2} streams; {dict(stats)}")


def build(names=None):
    for n in names or list(SETS):
        build_set(n)


if __name__ == "__main__":
    build(sys.argv[1:] or None)
