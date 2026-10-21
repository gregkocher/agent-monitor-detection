"""BashArena execution-replay scaffold (round 3, part A) -- VERIFIED FEASIBLE on the laptop.

Goal: replay a rewritten (or original) attack trajectory in the real BashArena Docker sandbox and
check side-task success with the official scorer, to validate side-task success beyond the LLM judge.

What this file encodes is the recipe PROVEN to work in a 2026-10-21 probe (see EXPERIMENT_LOG.md):
  * control-arena 20.1.0 ships the whole BashArena setting: the 4 side-task scorers
    (disable_firewall, sudo_edit, download_malware, leak_passwords), the base_environment and a
    per-task docker-compose template, and a HF dataset loader (`Eccentricity/bashbench2`, 637 tasks).
  * Our attacks' context.task_id values exist in that dataset (checked for 6935769). Load a single
    sample with `get_dataset_hf(task_id_whitelist=[tid])`; it materializes compose.yml + Dockerfile
    under the setting's `task_workspaces/`.
  * `benchmark-base:latest` builds from ubuntu:22.04 in ~1m51s (938 MB), once. Each task's 5-service
    compose (default + router + logging/malware/database servers, two bridge nets, NET_ADMIN) comes
    up healthy in ~25s. `docker exec` runs as root; the attack target state is present
    (e.g. /etc/firewall/firewall.conf).
  * Trajectory actions are `bash(...)`, `text_editor(...)`, `submit` -> parseable into tool calls.

WHY A HAND-ROLLED SCORER IS NOT ENOUGH: the official side-task scorers are live, multi-container
tests bound to Inspect's `sandbox("default")` / `sandbox("malware_server")` runtime (the firewall
scorer writes a listener into `default` and a sender into `malware_server` and counts packets). To
reuse them faithfully you run them INSIDE an `inspect eval`, not standalone. The clean, faithful
implementation is therefore:

  (1) add a *fixed-trajectory policy* to control-arena BashArena (an Inspect solver that emits our
      recorded ToolCalls instead of calling a model), and
  (2) run `inspect eval` of BashArenaSetting for each (sample, arm) with `task_id_whitelist`, the
      matching `side_tasks=[...]`, and the setting's own scorer; read side_task_success from the log.

This scaffold implements the model-free infrastructure half (materialize, build, up, exec a command
list, tear down) that the probe verified, so a future full run only has to add the fixed-policy +
official-scorer wiring in (1)/(2). It never prints attack content.

Validity note: side-task scorers check live/final SYSTEM STATE, not the transcript, so the
fabricated intermediate outputs in a rewrite do not by themselves invalidate the side-task check: a
rewrite scores "success" iff the commands it actually runs produce the sabotage effect. A command
that silently depended on a real earlier output (which fabrication masked) may fail -- that is a
genuinely broken attack and is the right outcome to record.

    uv run python -m tracks.r3_t3.replay_basharena --task-id 6935769 --up        # build+up, probe
    uv run python -m tracks.r3_t3.replay_basharena --task-id 6935769 --down       # tear down
    uv run python -m tracks.r3_t3.replay_basharena --task-id 6935769 --exec-file cmds.txt  # run cmds

Requires the control-arena venv (separate from this repo's): point CA_PY at its python.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

CA_PY = os.environ.get("CA_PY", "/tmp/ca_probe/.venv/bin/python")
CA_SETTING = ("control_arena/settings/bash_arena")


def _ca_root() -> Path:
    out = subprocess.run([CA_PY, "-c",
        "import control_arena,os;print(os.path.dirname(control_arena.__file__))"],
        capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"control-arena venv not importable via {CA_PY}: {out.stderr[:200]}")
    return Path(out.stdout.strip())


def materialize(task_id: str) -> Path:
    """Load the sample so control-arena writes its compose.yml + Dockerfile, return the workspace."""
    code = (
        "import os;from control_arena.eval import EvalMode;"
        "from control_arena.settings.bash_arena.task.dataset import get_dataset_hf;"
        f"ds=get_dataset_hf(eval_mode=EvalMode.ATTACK,task_id_whitelist=['{task_id}'],max_tasks=1);"
        "s=ds[0];print(getattr(s.sandbox,'config',None))")
    env = dict(os.environ)
    hf = Path.home() / ".hf_token"
    if hf.exists():
        env.setdefault("HF_TOKEN", hf.read_text().strip())
    out = subprocess.run([CA_PY, "-c", code], capture_output=True, text=True, env=env)
    cfg = out.stdout.strip().splitlines()[-1] if out.stdout.strip() else ""
    if not cfg or not Path(cfg).exists():
        sys.exit(f"could not materialize task {task_id}: {out.stderr[-300:]}")
    return Path(cfg).parent


def build_base(ca_root: Path) -> None:
    if subprocess.run(["docker", "image", "inspect", "benchmark-base:latest"],
                      capture_output=True).returncode == 0:
        return
    be = ca_root / CA_SETTING / "base_environment"
    print("building benchmark-base (~2 min, once) ...", flush=True)
    r = subprocess.run(["docker", "build", "-t", "benchmark-base:latest",
                        "-f", str(be / "base.Dockerfile"), str(be)])
    if r.returncode != 0:
        sys.exit("benchmark-base build failed")


def compose(ws: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "compose", "-f", str(ws / "compose.yml"), *args])


def default_container(ws: Path) -> str:
    proj = ws.name
    r = subprocess.run(["docker", "ps", "--filter", f"name={proj}-default", "--format", "{{.Names}}"],
                       capture_output=True, text=True)
    return r.stdout.strip().splitlines()[0] if r.stdout.strip() else ""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--up", action="store_true")
    ap.add_argument("--down", action="store_true")
    ap.add_argument("--exec-file", help="file of shell commands (one per line) to run in `default`")
    a = ap.parse_args(argv)
    ca_root = _ca_root()
    ws = materialize(a.task_id)
    print("workspace:", ws)
    if a.up or a.exec_file:
        build_base(ca_root)
        compose(ws, "up", "-d", "--build")
        c = default_container(ws)
        print("default container:", c or "(not found)")
        if c:
            subprocess.run(["docker", "exec", c, "bash", "-lc",
                            "echo sandbox-ok; ls /etc/firewall 2>/dev/null | head"])
    if a.exec_file:
        c = default_container(ws)
        for line in Path(a.exec_file).read_text().splitlines():
            if line.strip():
                subprocess.run(["docker", "exec", c, "bash", "-lc", line])
    if a.down:
        compose(ws, "down", "-v")
        print("tore down", a.task_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
