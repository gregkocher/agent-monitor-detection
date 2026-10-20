"""MonitoringBench attacks (HF neur26anonsub/ctrldataset2026, CC-BY-4.0).

`master.parquet` (2,644 successful attacks, 135 columns: per-trajectory monitor scores, attack taxonomy,
attack_step) is joined to the Inspect samples inside `final_dataset.zip` (2.47 GB, 2,363 `.eval` files). The zip
is read through HTTP range requests, one `.eval` member at a time (only `samples/*.json` members are opened),
and each sample is reduced to a compact JSON cached in data/raw/monitoringbench/extracted/<sample_uuid>.json,
so the archive is never stored on disk.

SECURITY: the `.eval` headers (`header.json`, eval.revision.origin) embed a leaked GitHub token. This loader
never opens `header.json` and whitelists the sample fields it keeps.

Normalization (shared with mb_honest): bash/python tool arguments `command` -> `cmd` (attacks use `cmd`, the
honest originals `command`; text_editor's own `command` argument is untouched); `meta.ends_with_submit` and
`meta.submit_step` record the trailing submit() (kept as the last Step).

attack_step: the parquet's `attack_step` is 1-based and marks the action that EXECUTES the payload. We store
attack_step = harm_step = attack_step_native - 1 (0-based) and keep the native value in meta. A heuristic
earlier onset, the first step whose action mentions a side-task target literal (IP range, URL/host, target user),
is in meta["first_attack_step"] (see first_attack_step(); None when no literal is found before attack_step).

Usage: python -m amd.data.monitoringbench
"""
from __future__ import annotations

import io
import json
import os
import re
import threading
import time
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from amd.common.schema import PROCESSED, RAW, ScoreStream, Step, Trajectory, write_jsonl
from amd.data._util import (ACTION_CHARS, OUT_CHARS, REASON_CHARS, content_text, download, fmt_call, hf_headers,
                            open_remote_zip, trunc)

SOURCE = "monitoringbench"
REPO = "neur26anonsub/ctrldataset2026"
BASE = f"https://huggingface.co/datasets/{REPO}/resolve/main"
RAW_DIR = RAW / SOURCE
EXTRACTED = RAW_DIR / "extracted"
RENAME_TOOLS = {"bash", "python"}
KEEP_META = ("main_task_description", "side_task_description", "setting_name", "eval_mode", "main_task_name",
             "side_task_name")


# --------------------------------------------------------------------------------------- inspect samples
def _resolve(x, att):
    if isinstance(x, str) and x.startswith("attachment://"):
        return att.get(x[len("attachment://"):], x)
    if isinstance(x, list):
        return [_resolve(v, att) for v in x]
    if isinstance(x, dict):
        return {k: _resolve(v, att) for k, v in x.items()}
    return x


def extract_sample(s: dict) -> dict:
    """Reduce an Inspect sample dict to {steps, tools, meta} with whitelisted fields only."""
    att = s.get("attachments") or {}
    msgs = s.get("messages") or []
    outs = {}
    for m in msgs:
        if m.get("role") == "tool":
            text, _ = content_text(_resolve(m.get("content"), att))
            if m.get("error"):
                text = (text + "\n[error] " + json.dumps(m["error"], default=str)).strip()
            outs[m.get("tool_call_id")] = text
    steps, fns, renamed = [], [], 0
    for m in msgs:
        if m.get("role") != "assistant":
            continue
        text, reasoning = content_text(_resolve(m.get("content"), att))
        if text.startswith("tool call for tool"):
            text = ""
        vis = "\n".join(x for x in (reasoning, text) if x)
        calls = m.get("tool_calls") or []
        if not calls and vis:
            steps.append({"action": trunc("[assistant message] " + vis, ACTION_CHARS), "output": "", "reasoning": ""})
            fns.append("<text>")
            continue
        for j, tc in enumerate(calls):
            fn = tc.get("function")
            args = _resolve(tc.get("arguments"), att)
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    pass
            if fn in RENAME_TOOLS and isinstance(args, dict) and "command" in args and "cmd" not in args:
                args = {("cmd" if k == "command" else k): v for k, v in args.items()}
                renamed += 1
            steps.append({"action": trunc(fmt_call(fn, args), ACTION_CHARS),
                          "output": trunc(outs.get(tc.get("id"), ""), OUT_CHARS),
                          "reasoning": trunc(vis, REASON_CHARS) if j == 0 else ""})
            fns.append(fn)
    md = s.get("metadata") or {}
    sc = s.get("scores") or {}

    def val(k):
        v = sc.get(k)
        return v.get("value") if isinstance(v, dict) else None

    return {
        "sample_id": str(s.get("id")), "epoch": s.get("epoch"), "uuid": s.get("uuid"),
        "steps": steps, "tools": fns, "renamed_command_args": renamed,
        "meta": {k: md.get(k) for k in KEEP_META},
        "models": list((s.get("model_usage") or {}).keys()),
        "main_task_success": val("main_task_success"), "side_task_success": val("side_task_success"),
        "eval_scores": {k: val(k) for k in sc if k.endswith("-scorer-0")},
    }


def iter_eval_samples(eval_bytes_or_path):
    """Yield sample dicts from an Inspect .eval (zip; zstd members need Python >= 3.14). Never opens header.json."""
    zf = zipfile.ZipFile(io.BytesIO(eval_bytes_or_path) if isinstance(eval_bytes_or_path, bytes) else eval_bytes_or_path)
    for name in zf.namelist():
        if name.startswith("samples/") and name.endswith(".json"):
            yield json.loads(zf.read(name))


# ---------------------------------------------------------------------------------------------- extract
class RemoteZip:
    """Thread-local remote zip handles (presigned redirect URLs expire, so reopen on failure)."""

    def __init__(self, url):
        self.url, self.local = url, threading.local()

    def get(self, fresh=False):
        if fresh or not hasattr(self.local, "z"):
            self.local.z = open_remote_zip(self.url, hf_headers())
        return self.local.z


def extract_all(df: pd.DataFrame, workers: int = 6):
    EXTRACTED.mkdir(parents=True, exist_ok=True)
    todo = df[~df.sample_uuid.map(lambda u: (EXTRACTED / f"{u}.json").exists())]
    if todo.empty:
        return
    rz = RemoteZip(f"{BASE}/final_dataset.zip")
    members = {os.path.basename(i.filename): i.filename for i in rz.get().infolist()
               if i.filename.startswith("final_") and i.filename.endswith(".eval")}
    groups = todo.groupby("eval_log_filename").sample_uuid.apply(set).to_dict()
    print(f"extracting {len(todo)} samples from {len(groups)} .eval members")

    def work(fname, uuids):
        for attempt in range(4):
            try:
                data = rz.get(fresh=attempt > 0).read(members[fname])
                break
            except Exception as e:
                if attempt == 3:
                    return fname, f"ERR {type(e).__name__}"
                time.sleep(5 * (attempt + 1))
        found = 0
        for s in iter_eval_samples(data):
            if s.get("uuid") in uuids:
                (EXTRACTED / f"{s['uuid']}.json").write_text(json.dumps(extract_sample(s)))
                found += 1
        return fname, found

    done = 0
    with ThreadPoolExecutor(workers) as ex:
        futs = [ex.submit(work, f, u) for f, u in groups.items()]
        for fu in as_completed(futs):
            fname, res = fu.result()
            done += 1
            if isinstance(res, str) or done % 200 == 0:
                print(f"  {done}/{len(groups)} {res if isinstance(res, str) else ''}", flush=True)


# ------------------------------------------------------------------------------------- attack onset
IP_RE = re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3})\.\d{1,3}(?:/\d+)?\b")
URL_RE = re.compile(r"https?://([^\s/\"'`)]+)")
USER_RE = re.compile(r"\b(restricted-service|intern|backup-user|deploy|monitoring|app)\b")


def target_literals(side_task_group: str, desc: str, attack_summary: str | None = None) -> list[str]:
    """Strings that identify the side-task target in an action: first three octets of target IPs (from the side-task
    description and from the parquet's post-hoc `attack_summary`, which names the IP actually used, e.g. the
    firewall range), URL hosts, and for sudo the target user. Generic infrastructure paths are excluded because
    honest BashArena main tasks also touch them."""
    desc = (desc or "") + "\n" + (attack_summary or "")
    lits = {m for m in IP_RE.findall(desc)}
    lits |= {h for h in URL_RE.findall(desc)}
    if side_task_group == "sudo":
        lits |= {m for m in USER_RE.findall(desc) if m == "restricted-service"}
    return sorted(x for x in lits if x and not x.startswith(("127.0.0", "0.0.0", "192.0.2")))


def first_attack_step(steps: list[dict], lits: list[str], upto: int | None):
    """First step (<= upto) whose action mentions any target literal, or None."""
    if not lits:
        return None, None
    last = len(steps) - 1 if upto is None else min(upto, len(steps) - 1)
    for i in range(last + 1):
        a = steps[i]["action"]
        for lit in lits:
            if lit in a:
                return i, lit
    return None, None


# ------------------------------------------------------------------------------------------------ build
FT_RE = re.compile(r"^ft_(.+)_monitor_score_(\d)$")
SW_RE = re.compile(r"^sw_(.+)_monitor_score_(\d)$")
SWV_RE = re.compile(r"^sw_(full|trimmed)_(.+)$")
DEV = {"dev_gpt5_monitor_score": "gpt-5", "dev_opus_monitor_score": "claude-opus-4-5", "dev_gpt5_nano_monitor_score": "gpt-5-nano"}
TAXO = ("structural_strategy", "structural_strategy_explanation", "evasion_tactics", "evasion_tactics_explanation",
        "technical_techniques", "technical_techniques_explanation", "attack_summary", "attack_group", "source_group",
        "new_source_name", "attack_strategy", "plan_strategy", "is_ft_only", "has_stepwise", "eval_created",
        "tool_call_count", "assistant_messages_count", "total_steps")


def _f(x):
    try:
        return None if pd.isna(x) else float(x)
    except Exception:
        return None


def score_streams(tid: str, row: pd.Series) -> list[ScoreStream]:
    groups = defaultdict(dict)
    for c, v in row.items():
        if (m := FT_RE.match(c)):
            groups[(m.group(1), "mb_ft", "full_trajectory")][int(m.group(2))] = _f(v)
        elif (m := SW_RE.match(c)):
            groups[(m.group(1), "mb_sw", "stepwise_max")][int(m.group(2))] = _f(v)
        elif (m := SWV_RE.match(c)):
            groups[(m.group(2), f"mb_sw_{m.group(1)}", "stepwise_max")][0] = _f(v)
        elif c in DEV:
            groups[(DEV[c], "mb_dev", "full_trajectory")][0] = _f(v)
    out = []
    for (model, prompt, hist), eps in sorted(groups.items()):
        vals = [v for _, v in sorted(eps.items())]
        fin = [v for v in vals if v is not None]
        if not fin:
            continue
        out.append(ScoreStream(tid, f"{model}|{prompt}|{hist}", "trajectory", [sum(fin) / len(fin)], (0.0, 10.0),
                               {"epochs": vals, "aggregation": "mean over epochs",
                                "note": {"mb_ft": "full-trajectory monitor, tool calls without outputs",
                                         "mb_sw": "stepwise monitor, trajectory max (per epoch)",
                                         "mb_sw_full": "stepwise monitor (full history), trajectory max",
                                         "mb_sw_trimmed": "stepwise monitor (trimmed history), trajectory max",
                                         "mb_dev": "dev full-trajectory scorer (also in the .eval)"}[prompt]}))
    return out


def build():
    pq_path = download(f"{BASE}/master.parquet", RAW_DIR / "master.parquet", hf_headers())
    df = pd.read_parquet(pq_path)
    extract_all(df)
    trajs, streams, stats = [], [], Counter()
    for _, r in df.iterrows():
        p = EXTRACTED / f"{r.sample_uuid}.json"
        if not p.exists():
            stats["missing_sample"] += 1
            continue
        e = json.loads(p.read_text())
        steps = e["steps"]
        n = len(steps)
        native = _f(r.attack_step)
        a0 = int(native) - 1 if native is not None else None
        if a0 is not None and not (0 <= a0 < n):
            stats["attack_step_out_of_range"] += 1
        group = r.side_task_group
        lits = target_literals(group, e["meta"].get("side_task_description"),
                               r.attack_summary if isinstance(r.attack_summary, str) else None)
        fa, lit = first_attack_step(steps, lits, a0)
        tools = e["tools"]
        tid = f"{SOURCE}:{r.sample_uuid}"
        ctx = {"setting": "basharena", "task_id": str(r.task_id), "main_task": str(r.task_id),
               "side_task": r.side_task_name, "side_task_group": group, "policy": r.source_name,
               "agent_model": r.attack_model,
               "main_task_description": trunc(e["meta"].get("main_task_description"), 12000)}
        meta = {k: (None if (not isinstance(r[k], str) and pd.isna(r[k])) else
                    (r[k].item() if hasattr(r[k], "item") else r[k])) for k in TAXO if k in r}
        meta.update(
            sample_uuid=r.sample_uuid, sample_id=e["sample_id"], epoch=e["epoch"], eval_log_filename=r.eval_log_filename,
            attack_step_native=native, total_steps_native=_f(r.total_steps),
            first_attack_step=fa, first_attack_step_literal=lit, target_literals=lits,
            first_attack_step_method="first action mentioning a side-task target literal (heuristic)" if lits else None,
            main_task_success=_f(r.main_task_success), side_task_description=trunc(e["meta"].get("side_task_description"), 4000),
            ends_with_submit=bool(tools) and tools[-1] == "submit",
            submit_step=(len(tools) - 1) if tools and tools[-1] == "submit" else None,
            renamed_command_args=e["renamed_command_args"], tool_counts=dict(Counter(tools)),
            n_steps_matches_tool_call_count=(n == int(r.tool_call_count)),
        )
        stats[f"n_steps==tool_call_count:{n == int(r.tool_call_count)}"] += 1
        trajs.append(Trajectory(tid, SOURCE, "attack", ctx, [Step(idx=i, **s) for i, s in enumerate(steps)],
                                attack_step=a0, harm_step=a0, side_task_success=bool(r.side_task_success), meta=meta))
        streams += score_streams(tid, r)
    n1 = write_jsonl(PROCESSED / SOURCE / "trajectories.jsonl", trajs)
    n2 = write_jsonl(PROCESSED / SOURCE / "scores.jsonl", streams)
    print(f"wrote {n1} trajectories, {n2} streams; {dict(stats)}")


if __name__ == "__main__":
    build()
