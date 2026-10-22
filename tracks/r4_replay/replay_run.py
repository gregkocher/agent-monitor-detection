"""Replay ONE recorded attack trajectory (structured tool calls) in the real BashArena Docker
sandbox and record the OFFICIAL side_task_success scorer verdict. Run under the control-arena venv:

    CA_PY=/tmp/ca_probe/.venv/bin/python
    $CA_PY tracks/r4_replay/replay_run.py --sample <structured.json> --out <result.json>

Mirrors control_arena bash_arena tests/test_side_tasks.run_fixed_policy, but:
  * uses the sample's OWN task_id (task_id_whitelist) so the main-task environment matches;
  * replays the recorded bash + text_editor calls (not just bash), in order;
  * reads the official `side_task_success` score from the eval log.

No model is called (mockllm + fixed policy); needs no API key. Isolated per-sample Docker compose,
torn down by Inspect after the sample. Never prints attack content.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

import inspect_ai
from inspect_ai.scorer import CORRECT
from inspect_ai.tool import ToolCall, bash, python
from inspect_ai.solver import TaskState

from control_arena import EvalMode
from control_arena.eval import ControlEvalConfig, get_control_task
from control_arena.policy import fixed_policy_builder
from control_arena.settings.bash_arena.bash_arena_setting import BashArenaSetting
from control_arena.settings.bash_arena.protocol.auto_submit_protocol_wrapper import (
    auto_submit_protocol_wrapper,
)
from control_arena.settings.bash_arena.task.dataset import DatasetSpec
from control_arena.tools import restricted_text_editor

# Per-command timeout for replay: faithful attack-critical ops (sed/write/curl-to-local-server) finish
# in <<45s; this only caps blocking benign filler (dev servers, watchers) that would otherwise burn the
# default 300s each. A hard per-sample time_limit is also set on the eval.
TOOL_TIMEOUT = int(os.environ.get("R4_TOOL_TIMEOUT", "45"))
SAMPLE_TIME_LIMIT = int(os.environ.get("R4_SAMPLE_TIME_LIMIT", "1800"))


class FastBashArenaSetting(BashArenaSetting):
    def get_agent_tools(self, state: TaskState) -> list:
        return [bash(timeout=TOOL_TIMEOUT), python(timeout=TOOL_TIMEOUT), restricted_text_editor()]

GROUP_TO_SIDE_TASK = {
    "firewall": "disable_firewall",
    "malware": "download_malware",
    "sudo": "sudo_edit",
    "password_leak": "leak_passwords",
}
TE_KEYS = ("command", "path", "file_text", "insert_line", "insert_text", "new_str", "old_str", "view_range")
MOCK = ControlEvalConfig(trusted_model="mockllm/mockllm", untrusted_model="mockllm/mockllm")


def build_tool_calls(calls: list[dict]) -> list[ToolCall]:
    out = []
    for i, c in enumerate(calls):
        fn, a = c.get("function"), (c.get("arguments") or {})
        if fn == "submit":
            continue
        if fn == "bash":
            cmd = a.get("command") or a.get("cmd") or ""
            out.append(ToolCall(function="bash", arguments={"command": cmd}, id=f"c{i}"))
        elif fn == "python":
            code = a.get("code") or a.get("cmd") or a.get("command") or ""
            out.append(ToolCall(function="python", arguments={"code": code}, id=f"c{i}"))
        elif fn == "text_editor":
            args = {k: a[k] for k in TE_KEYS if k in a and a[k] is not None}
            out.append(ToolCall(function="text_editor", arguments=args, id=f"c{i}"))
        else:
            # Unknown tool: replay as a no-op comment so step indexing is preserved but nothing runs.
            out.append(ToolCall(function="bash", arguments={"command": f": unknown_tool {fn}"}, id=f"c{i}"))
    return out


def replay(sample_path: str, task_id_override: str | None = None) -> dict:
    d = json.loads(open(sample_path).read())
    group = d["side_task_group"]
    side_task = GROUP_TO_SIDE_TASK[group]
    task_id = task_id_override or d["task_id"]
    tool_calls = build_tool_calls(d["calls"])

    control_task = get_control_task(
        setting=FastBashArenaSetting(
            dataset_spec=DatasetSpec(side_tasks=[side_task], task_id_whitelist=[task_id], max_tasks=1),
        ),
        micro_protocol=auto_submit_protocol_wrapper(
            micro_protocol=fixed_policy_builder(tool_calls=tool_calls)
        ),
        mode=EvalMode.ATTACK,
        eval_config=MOCK,
    )
    rec = {"uuid": d["uuid"], "task_id": task_id, "side_task_group": group, "side_task": side_task,
           "n_tool_calls": len(tool_calls), "n_calls_recorded": len(d["calls"]),
           "side_task_success_native": d.get("side_task_success_native"),
           "tool_timeout": TOOL_TIMEOUT, "status": None, "error": None, "side_task_success": None,
           "main_task_success": None, "n_samples": 0}
    with tempfile.TemporaryDirectory() as logdir:
        logs = inspect_ai.eval(control_task, log_dir=logdir, display="none", sandbox_cleanup=True,
                               max_samples=1, score=True, time_limit=SAMPLE_TIME_LIMIT)
        log = logs[0]
        rec["status"] = log.status
        rec["n_samples"] = len(log.samples or [])
        if log.status != "success":
            rec["error"] = str(getattr(log, "error", None))[:300]
        for s in (log.samples or []):  # accessed INSIDE the tempdir: samples lazy-load from the .eval
            sc = s.scores or {}
            if "side_task_success" in sc:
                rec["side_task_success"] = (sc["side_task_success"].value == CORRECT)
            if "main_task_success" in sc:
                rec["main_task_success"] = (sc["main_task_success"].value == CORRECT)
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--task-id", default=None)
    a = ap.parse_args(argv)
    try:
        rec = replay(a.sample, a.task_id)
    except Exception as e:
        rec = {"sample": a.sample, "status": "exception", "error": f"{type(e).__name__}: {e}"[:400],
               "side_task_success": None}
    open(a.out, "w").write(json.dumps(rec))
    print("RESULT", json.dumps({k: rec.get(k) for k in
          ("uuid", "side_task", "status", "side_task_success", "side_task_success_native", "error")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
