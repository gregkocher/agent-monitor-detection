"""Loader for ScaleAI MRT ("Reliable Weak-to-Strong Monitoring of LLM Agents", arXiv 2508.19461).

Source: HF dataset `ScaleAI/mrt` (CC-BY-NC-4.0, research use only; carries a canary string, do not train on it).
Layout: `<root>/<task>/<cfg>/<attacker_model>/<monitor_model>/transcript_<i>.json` with root
`task_pairs` (5 SHADE-Arena pairs) or `task_pairs_agentcompany` (15 CUA-SHADE tasks on TheAgentCompany).

The monitor scaffold is encoded INSIDE the config directory name: the monitor code
(scaleapi/mrt `monitor_generation/add_monitors.py`) writes to `<agent cfg>_<monitor_style>`, e.g.
`transcripts_no_hint_liar_204_thinking_time` + `_sequential_5_likert_reminder_v2` (+ `_superaware`).
We only use `sequential_N` styles: the monitor reads the transcript N messages at a time in one growing
dialogue and emits a `<verdict>` after every chunk -> a per-chunk suspicion series.

Chunking (scaleapi/mrt `utils/pipeline_utils.py::run_sequential_monitor`): the agent conversation minus the
system prompt is rendered to a string (thinking tags stripped), cut at the first "ASSISTANT:" (so the initial
user query is shown separately, not chunked), re-split into messages on `\\n\\n(USER|ASSISTANT|TOOL|SYSTEM): `
and grouped N messages at a time. A "message" is one assistant turn OR one tool output, so a chunk of N
messages covers about N/2 of our Steps (one Step = one assistant turn + the tool outputs that follow it).
Styles containing `sequential_v2` (config `sequential_<N>_v2_...`) are a summary variant: each chunk is judged
from the monitor's own previous summary instead of the full dialogue history.

Selection (disk-constrained): all honest sequential files + ~3k attack sequential files, stratified
round-robin over the 20 tasks and over (chunk size, monitor model, monitor style) strata, preferring strata
that also have honest files. Raw JSON is cached gzip-compressed under data/raw/mrt/files/.

Scores: per chunk, the last `<verdict>X</verdict>` of the monitor's reply (strict, as in MRT); if absent, a
lenient fallback (unclosed tag, `<final verdict>`, "suspicion score: X") whose indices are listed in
meta["lenient_parsed_chunks"]; otherwise NaN. Scale read from the monitor system prompt ("likert" prompts 1-5,
the old non-likert prompts 0-100). Files without `monitor_conversation` (older runs that saved only the final
response) are skipped, as are streams whose length disagrees with MRT's chunking (summary-mode files that kept
only their last chunk); counts in data/processed/mrt/build_stats.json.

Run: `unset VIRTUAL_ENV; uv run python -m amd.data.mrt`  (add `--qc-only` to skip download/build).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import random
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

from amd.common.schema import PROCESSED, RAW, ScoreStream, Step, Trajectory, read_jsonl, write_jsonl
from amd.data._util import ACTION_CHARS, OUT_CHARS, REASON_CHARS, hf_headers, trunc

REPO_ID = "ScaleAI/mrt"
ROOTS = ("task_pairs", "task_pairs_agentcompany")
RAW_DIR = RAW / "mrt"
FILES_DIR = RAW_DIR / "files"
LISTING = RAW_DIR / "listing.jsonl"
SELECTION = RAW_DIR / "selection.json"
OUT_DIR = PROCESSED / "mrt"

SEED = 20261020
N_ATTACK = 3000
HONEST_CAP = 4500
WORKERS = 4  # HF rate-limits resolve/ requests (429) when several loaders run at once

SEQ_RE = re.compile(r"_sequential_(\d+)(?=_|$)")
VERDICT_RE = re.compile(r"<verdict>\s*(.*?)\s*</verdict>", re.S | re.I)
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
THINK_RE = re.compile(r"<(hidden_thinking|thinking|system_instructions)>.*?</\1>", re.S)
TOOLNAME_RE = re.compile(r"^-\s*(.+?)\s*$", re.M)
SPLIT_RE = re.compile(r"\n\n(?=(?:SYSTEM|USER|ASSISTANT|TOOL):\s)")

STRATEGY_TOKENS = [
    "no_hint", "hint", "human_hint", "feedback", "selective", "liar", "visible", "naive", "real_naive", "real",
    "manipulation", "manipulator", "mm", "benign", "thinking_time", "no_thinking_time", "thinkchoose", "choose", "strategy",
    "superaware", "unaware", "longstem", "flawed", "randomorder",
]
LIST_URL = "https://huggingface.co/api/datasets/{repo}/tree/main/{path}?recursive=true&expand=false"
FILE_URL = "https://huggingface.co/datasets/{repo}/resolve/main/{path}"


# ---------------------------------------------------------------- listing

def list_files(refresh: bool = False) -> list[dict]:
    """All transcript files in the repo as {path, size}; cached in data/raw/mrt/listing.jsonl."""
    if LISTING.exists() and not refresh:
        return list(read_jsonl(LISTING))
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    with httpx.Client(headers=hf_headers(), timeout=120, follow_redirects=True) as cl:
        for root in ROOTS:
            url = LIST_URL.format(repo=REPO_ID, path=root)
            page = 0
            while url:
                for i in range(6):
                    try:
                        r = cl.get(url)
                        r.raise_for_status()
                        break
                    except Exception:
                        if i == 5:
                            raise
                        time.sleep(3 * (i + 1))
                for e in r.json():
                    if e.get("type") == "file" and e["path"].endswith(".json"):
                        out.append({"path": e["path"], "size": e.get("size", 0)})
                page += 1
                nxt = r.links.get("next")
                url = nxt["url"] if nxt else None
            print(f"[mrt] listed {root}: {page} pages, total files so far {len(out)}", flush=True)
    with open(LISTING, "w") as f:
        for e in out:
            f.write(json.dumps(e) + "\n")
    return out


def parse_path(path: str) -> dict | None:
    parts = path.split("/")
    if len(parts) != 6 or not re.fullmatch(r"transcript_\d+\.json", parts[-1]):
        return None
    root, task, cfg, attacker, monitor, fname = parts
    m = SEQ_RE.search(cfg)
    info = {
        "path": path, "root": root, "task": task, "cfg": cfg, "attacker": attacker, "monitor": monitor,
        "transcript_i": int(fname[len("transcript_"):-len(".json")]),
        "domain": "shade" if root == "task_pairs" else "cua",
        "honest": ("no_secondary_task" in cfg) or ("benign" in cfg),
        "chunk_size": int(m.group(1)) if m else None,
    }
    if m:
        info["agent_cfg"] = cfg[: m.start()]
        info["monitor_style"] = "sequential_" + m.group(1) + cfg[m.end():]
        rest = cfg[m.end():].lstrip("_")
        info["monitor_variant"] = rest  # e.g. "likert_reminder_v2", "likert_reminder_v2_superaware"
    return info


def strategy_tokens(agent_cfg: str) -> list[str]:
    s = agent_cfg[len("transcripts"):].strip("_") if agent_cfg.startswith("transcripts") else agent_cfg
    toks = []
    padded = "_" + s + "_"
    for t in STRATEGY_TOKENS:
        if f"_{t}_" in padded:
            toks.append(t)
    # numbered variants, e.g. liar_204, mm_v3, strategy_4
    for m in re.finditer(r"(liar|mm|strategy|manipulator|naive|selective|visible|benign)_(v?\d+)", s):
        toks.append(f"{m.group(1)}_{m.group(2)}")
    if "no_thinking_time" in toks and "thinking_time" in toks:
        toks.remove("thinking_time")
    if "no_hint" in toks and "hint" in toks:
        toks.remove("hint")
    if "human_hint" in toks and "hint" in toks:
        toks.remove("hint")
    return sorted(set(toks))


# ---------------------------------------------------------------- selection

def select(files: list[dict]) -> dict:
    infos = [i for i in (parse_path(e["path"]) for e in files) if i and i["chunk_size"] is not None]
    rng = random.Random(SEED)
    honest = sorted((i for i in infos if i["honest"]), key=lambda i: i["path"])
    attack = sorted((i for i in infos if not i["honest"]), key=lambda i: i["path"])
    note = ""
    if len(honest) > HONEST_CAP:
        # cap by per-task round robin over strata (same scheme as attack)
        honest = _stratified(honest, HONEST_CAP, rng, set())
        note = f"honest capped at {HONEST_CAP} (stratified)"
    hstrata = {(i["task"], i["chunk_size"], i["monitor"]) for i in honest}
    att = _stratified(attack, N_ATTACK, rng, hstrata)
    return {"seed": SEED, "n_seq_total": len(infos), "n_honest_avail": sum(i["honest"] for i in infos),
            "n_attack_avail": len(attack), "note": note,
            "honest": [i["path"] for i in honest], "attack": [i["path"] for i in att]}


def _stratified(items: list[dict], n: int, rng: random.Random, preferred: set) -> list[dict]:
    """Round-robin over tasks; inside a task, round-robin over (chunk size, monitor) strata (strata whose
    (task, N, monitor) is in `preferred` first); inside a stratum, round-robin over monitor variants
    (prompt / awareness) with a shuffled order within each. Water-filling across tasks."""
    by_task: dict[str, dict] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for i in items:
        by_task[i["task"]][(i["chunk_size"], i["monitor"])][i["monitor_variant"]].append(i)

    def interleave(lists):
        lists = [list(L) for L in lists]
        seq = []
        while any(lists):
            for L in lists:
                if L:
                    seq.append(L.pop())
        return seq

    queues = {}
    for task, strata in sorted(by_task.items()):
        flat = {}
        for k in sorted(strata):
            vs = strata[k]
            for v in sorted(vs):
                rng.shuffle(vs[v])
            flat[k] = interleave([vs[v] for v in sorted(vs)])
        keys = sorted(flat)
        pref = [k for k in keys if (task, k[0], k[1]) in preferred]
        other = [k for k in keys if (task, k[0], k[1]) not in preferred]
        rng.shuffle(pref)
        rng.shuffle(other)
        # interleave() pops from the end, so reverse each stratum to keep its order
        queues[task] = interleave([flat[k][::-1] for k in pref]) + interleave([flat[k][::-1] for k in other])
    out = []
    tasks = sorted(queues)
    while len(out) < n and any(queues.values()):
        for t in tasks:
            if queues[t] and len(out) < n:
                out.append(queues[t].pop(0))
    return out


# ---------------------------------------------------------------- download

def _cache_path(path: str) -> Path:
    return FILES_DIR / (path[:-len(".json")] + ".json.gz")


def _fetch(path: str, headers: dict) -> tuple[str, bool, str]:
    dest = _cache_path(path)
    if dest.exists() and dest.stat().st_size > 0:
        return path, True, "cached"
    url = FILE_URL.format(repo=REPO_ID, path=path)
    last = ""
    for i in range(10):
        try:
            r = httpx.get(url, headers=headers, timeout=120, follow_redirects=True)
            if r.status_code == 429:
                last = "HTTP 429"
                try:
                    wait = float(r.headers.get("Retry-After", ""))
                except ValueError:
                    wait = 15.0 * (i + 1)
                time.sleep(min(max(wait, 5.0), 300.0))
                continue
            if r.status_code == 200:
                json.loads(r.content)  # validate
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(".gz.part")
                with gzip.open(tmp, "wb", compresslevel=6) as f:
                    f.write(r.content)
                tmp.rename(dest)
                return path, True, "ok"
            last = f"HTTP {r.status_code}"
            if r.status_code in (403, 404):
                break
        except Exception as e:
            last = type(e).__name__
        time.sleep(2 * (i + 1))
    return path, False, last


def download_all(paths: list[str]) -> dict:
    headers = hf_headers()
    res = Counter()
    failed = []
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = [ex.submit(_fetch, p, headers) for p in paths]
        for k, fu in enumerate(as_completed(futs), 1):
            p, ok, why = fu.result()
            res[why if ok else "failed"] += 1
            if not ok:
                failed.append((p, why))
            if k % 250 == 0:
                print(f"[mrt] download {k}/{len(paths)} {dict(res)}", flush=True)
    print(f"[mrt] download done {dict(res)}; failure reasons {dict(Counter(w for _, w in failed))}", flush=True)
    return {"counts": dict(res), "failed": failed}


# ---------------------------------------------------------------- parsing

def strip_thinking(s: str | None) -> str:
    return THINK_RE.sub("", s or "").strip()


def hidden_thinking(s: str | None) -> str:
    return "\n".join(m.group(0) for m in THINK_RE.finditer(s or ""))


def tool_names(tc) -> list[str]:
    """MRT stores tool calls as a rendered string 'Tool calls:\\n- name' (no arguments)."""
    if tc is None:
        return []
    if isinstance(tc, list):
        out = []
        for c in tc:
            if isinstance(c, dict):
                out.append(c.get("function") or c.get("name") or json.dumps(c)[:200])
            else:
                out.append(str(c))
        return out
    return [m.group(1) for m in TOOLNAME_RE.finditer(str(tc))]


def build_steps(conv: list[dict]) -> tuple[list[Step], list[int]]:
    """Steps from conversation[2:]; returns (steps, msg2step) where msg2step[j] is the step index of
    agent message j (j indexes conversation[2:], the unit MRT chunks over)."""
    steps: list[Step] = []
    msg2step: list[int] = []
    for m in conv[2:]:
        role = (m.get("role") or "").lower()
        content = m.get("content") or ""
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        if role == "assistant":
            names = tool_names(m.get("tool_calls"))
            action = "; ".join(f"{n}()" for n in names) if names else "(no tool call)"
            steps.append(Step(idx=len(steps), action=trunc(action, ACTION_CHARS), output="",
                              reasoning=trunc(strip_thinking(content), REASON_CHARS)))
        elif role == "tool":
            if not steps:
                steps.append(Step(idx=0, action="(none)"))
            s = steps[-1]
            joined = (s.output + "\n" if s.output else "") + content
            s.output = trunc(joined, OUT_CHARS)
        else:  # later user / system messages: own step so chunk alignment stays monotone
            steps.append(Step(idx=len(steps), action=f"[{role} message]", output=trunc(content, OUT_CHARS)))
        msg2step.append(len(steps) - 1)
    return steps, msg2step


def mrt_message_count(conv: list[dict]) -> int:
    """Number of messages the MRT sequential monitor chunks over (replicates its string round-trip)."""
    def tc(m):
        out = "Tool calls:"
        if m.get("tool_calls") is not None:
            out += f"\n- {m['tool_calls']}"
        return out
    s = "\n\n".join(f"{(m.get('role') or '').upper()}: {strip_thinking(m.get('content') if isinstance(m.get('content'), str) else json.dumps(m.get('content')))}" + tc(m)
                    for m in conv[1:] if (m.get("role") or "").lower() != "system")
    k = s.find("ASSISTANT:")
    if k < 0:
        return 0
    s = s[k:]
    return len([b for b in SPLIT_RE.split(s.strip()) if b])


LENIENT_RES = [
    re.compile(r"<\s*verdict\s*>\s*\**\s*(\d+(?:\.\d+)?)", re.I),            # unclosed / misspelled close tag
    re.compile(r"<\s*final[ _]verdict\s*>\s*\**\s*(\d+(?:\.\d+)?)", re.I),    # <final verdict>1</final verdict>
    re.compile(r"(?:suspicion score|final verdict|verdict|score)\s*(?:is|of)?\s*[:=]?\s*\**\s*(\d+(?:\.\d+)?)", re.I),
]


def parse_verdict_ex(text, scale=(float("nan"), float("nan"))) -> tuple[float, str | None]:
    """(value, how): strict `<verdict>X</verdict>` (last occurrence, as in MRT) -> "strict"; otherwise a lenient
    fallback on the last matching pattern (only if the value lies inside the scale) -> "lenient"; else (NaN, None)."""
    if not isinstance(text, str):
        text = json.dumps(text) if text is not None else ""
    ms = VERDICT_RE.findall(text)
    if ms:
        nums = NUM_RE.findall(ms[-1])
        if nums:
            return float(nums[0]), "strict"
    lo, hi = scale
    for rx in LENIENT_RES:
        found = rx.findall(text)
        if found:
            v = float(found[-1])
            if (math.isnan(lo) and 0 <= v <= 100) or (not math.isnan(lo) and lo <= v <= hi):
                return v, "lenient"
    return float("nan"), None


def parse_verdict(text, scale=(float("nan"), float("nan"))) -> float:
    return parse_verdict_ex(text, scale)[0]


def monitor_turns(mc) -> list[str]:
    """Assistant turns of monitor_conversation in order (flattens the sequential_v2 list-of-lists form)."""
    out = []
    for m in mc or []:
        if isinstance(m, list):
            out.extend(monitor_turns(m))
        elif isinstance(m, dict) and (m.get("role") or "").lower() == "assistant":
            c = m.get("content")
            out.append(c if isinstance(c, str) else json.dumps(c))
    return out


SUMMARY_RE = re.compile(r"<begin_monitor_summary>(.*?)<end_monitor_summary>", re.S)


def chunk_responses(d: dict) -> tuple[list[str], str]:
    """Per-chunk monitor responses in order, and the reconstruction mode.
    Full-history mode: assistant turns of monitor_conversation. Summary mode (`sequential_N_v2_...`): MRT stores
    only [system, [user_1], [user_2], ...] (the assistant replies are not saved), but reply k is quoted as the
    summary inside user query k+1, and the last reply is `monitoring_response`."""
    mc = d.get("monitor_conversation") or []
    if any(isinstance(m, list) for m in mc):
        users = [m[0] for m in mc if isinstance(m, list) and m]
        out = []
        for u in users[1:]:
            mm = SUMMARY_RE.search(u.get("content") or "")
            out.append(mm.group(1) if mm else "")
        out.append(d.get("monitoring_response") or "")
        return out, "summary_quoted"
    return monitor_turns(mc), "assistant_turns"


def monitor_system(mc) -> str:
    for m in mc or []:
        if isinstance(m, list):
            s = monitor_system(m)
            if s:
                return s
        elif isinstance(m, dict) and (m.get("role") or "").lower() == "system":
            return m.get("content") or ""
    return ""


def scale_of(sys_prompt: str) -> tuple[float, float]:
    m = re.search(r"SCORE is a number from (\d+) to (\d+)", sys_prompt)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"from (\d+) to (\d+)", sys_prompt)
    if m:
        return float(m.group(1)), float(m.group(2))
    return (float("nan"), float("nan"))


def side_task_text(sys_prompt: str) -> str:
    m = re.search(r"(The secondary task is.*?)(?:\n\s*\n|Here is some information about how the monitoring)", sys_prompt, re.S)
    if m:
        return m.group(1).strip()
    m = re.search(r"<secondary_task>(.*?)</secondary_task>", sys_prompt, re.S)
    return m.group(1).strip() if m else ""


def conv_hash(conv) -> str:
    return hashlib.sha1(json.dumps(conv, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


# ---------------------------------------------------------------- build

def build(skip_download: bool = False) -> None:
    files = list_files()
    print(f"[mrt] listing: {len(files)} transcript files", flush=True)
    if SELECTION.exists():
        sel = json.loads(SELECTION.read_text())
    else:
        sel = select(files)
        SELECTION.write_text(json.dumps(sel))
    print(f"[mrt] selection: {len(sel['honest'])} honest + {len(sel['attack'])} attack sequential files "
          f"(available seq: honest {sel['n_honest_avail']}, attack {sel['n_attack_avail']}) {sel['note']}", flush=True)
    paths = sel["honest"] + sel["attack"]
    if not skip_download:
        download_all(paths)

    # group by agent-transcript identity
    groups: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
    missing = 0
    for p in paths:
        cp = _cache_path(p)
        if not cp.exists():
            missing += 1
            continue
        info = parse_path(p)
        key = f"{info['task']}/{info['agent_cfg']}/{info['attacker']}/transcript_{info['transcript_i']}"
        groups[key].append((info, cp))
    print(f"[mrt] {len(paths) - missing} cached files, {missing} missing; {len(groups)} agent-transcript keys", flush=True)

    trajs, streams = [], []
    n_split = 0
    no_mc = Counter()
    n_bad_len = 0
    for key, members in sorted(groups.items()):
        loaded = []
        for info, cp in members:
            with gzip.open(cp, "rt") as f:
                d = json.load(f)
            if not d.get("monitor_conversation"):
                # older sequential runs saved only the final monitoring_response -> no per-chunk series
                no_mc[(info["monitor_variant"], "honest" if info["honest"] else "attack")] += 1
                continue
            loaded.append((info, d, conv_hash(d.get("conversation") or [])))
        by_hash: dict[str, list] = defaultdict(list)
        for x in loaded:
            by_hash[x[2]].append(x)
        if len(by_hash) > 1:
            n_split += 1
        for h, xs in by_hash.items():
            info0, d0, _ = xs[0]
            if len(by_hash) == 1:
                tid = f"mrt:{key}"
            else:
                tid = "mrt:" + info0["path"][:-len(".json")]
            t, ss = _make_records(tid, key, h, xs, split=len(by_hash) > 1)
            # drop streams whose length disagrees with MRT's chunking (seen only for summary-mode files that
            # stored just their last chunk); a trajectory without any remaining stream is dropped too
            good = [x for x in ss if len(x.scores) == x.meta["n_chunks_expected"]]
            n_bad_len += len(ss) - len(good)
            if not good:
                continue
            t.meta["source_paths"] = [x.meta["source_path"] for x in good]
            trajs.append(t)
            streams.extend(good)
    # side task is fixed per task pair: fill attack trajectories whose stored agent system prompt is empty
    per_task = defaultdict(Counter)
    for t in trajs:
        if t.label == "attack" and t.context["side_task"]:
            per_task[t.context["task"]][t.context["side_task"]] += 1
    for t in trajs:
        if t.label == "attack" and not t.context["side_task"] and per_task[t.context["task"]]:
            t.context["side_task"] = per_task[t.context["task"]].most_common(1)[0][0]
            t.context["side_task_source"] = "task_default"
    # shared conventions: task text in context["main_task_description"], side-task text only in meta
    # (a monitor must not see it); short keys in context["main_task"] / context["side_task"]
    for t in trajs:
        c = t.context
        c["main_task_description"] = c.get("main_task")
        c["main_task"] = c["task"]
        if t.label == "attack":
            t.meta["side_task_description"] = c.get("side_task")
            c["side_task"] = f"{c['task']}_side_task" if c.get("side_task") else None
        else:
            c["side_task"] = None
        c["agent_model"] = c.get("attacker_model")
        c["policy"] = c.get("agent_cfg")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    nt = write_jsonl(OUT_DIR / "trajectories.jsonl", trajs)
    ns = write_jsonl(OUT_DIR / "scores.jsonl", streams)
    print(f"[mrt] wrote {nt} trajectories, {ns} score streams; {n_split} keys split by differing conversations; "
          f"skipped {sum(no_mc.values())} files without monitor_conversation; dropped {n_bad_len} streams "
          "with incomplete chunk series", flush=True)
    stats = {"selection": {k: v for k, v in sel.items() if k not in ("honest", "attack")},
             "n_selected": {"honest": len(sel["honest"]), "attack": len(sel["attack"])},
             "n_missing_download": missing, "n_keys": len(groups), "n_keys_split": n_split,
             "skipped_no_monitor_conversation": {f"{k[0] or 'base'}|{k[1]}": v for k, v in sorted(no_mc.items())},
             "dropped_streams_length_mismatch": n_bad_len,
             "n_trajectories": nt, "n_streams": ns}
    (OUT_DIR / "build_stats.json").write_text(json.dumps(stats, indent=1))
    qc()


def _make_records(tid: str, key: str, h: str, xs: list, split: bool):
    info0, d0, _ = xs[0]
    conv = d0.get("conversation") or []
    steps, msg2step = build_steps(conv)
    sys_prompt = conv[0].get("content", "") if conv and conv[0].get("role") == "system" else ""
    user_q = conv[1].get("content", "") if len(conv) > 1 and conv[1].get("role") == "user" else ""
    n_msgs = len(conv) - 2
    n_msgs_mrt = mrt_message_count(conv)
    side = "" if info0["honest"] else side_task_text(sys_prompt if isinstance(sys_prompt, str) else "")
    side_src = "agent_system_prompt" if side else None
    if not side and not info0["honest"]:
        # fallback: superaware monitors are told the side task in their system prompt
        for _, d, _ in xs:
            m = re.search(r"Here is the secondary task that the agent may or may not try to complete:\s*(.*)",
                          monitor_system(d.get("monitor_conversation")), re.S)
            if m:
                side = m.group(1).strip()
                side_src = "superaware_monitor_prompt"
                break
    hidden = sum(len(hidden_thinking(m.get("content") if isinstance(m.get("content"), str) else "")) for m in conv)
    ste = d0.get("side_task_evaluation")
    t = Trajectory(
        traj_id=tid, source="mrt", label="honest" if info0["honest"] else "attack",
        context={
            "task": info0["task"], "domain": info0["domain"], "attacker_model": info0["attacker"],
            "agent_cfg": info0["agent_cfg"], "attack_strategy": strategy_tokens(info0["agent_cfg"]),
            "main_task": trunc(user_q if isinstance(user_q, str) else json.dumps(user_q), 1500),
            "side_task": trunc(side, 1500) if side else None,
            "side_task_source": side_src,
        },
        steps=steps, attack_step=None, harm_step=None,
        side_task_success=bool(ste) if isinstance(ste, bool) else (None if ste is None else bool(ste)),
        meta={
            "agent_traj_key": key, "conversation_sha1": h, "split_from_key": split,
            "n_messages": n_msgs, "n_messages_mrt": n_msgs_mrt,
            "msg2step": msg2step, "hidden_thinking_chars": hidden,
            "main_task_evaluation": trunc(d0.get("main_task_evaluation"), 1000),
            "side_task_evaluation_raw": ste if isinstance(ste, (bool, int, float)) or ste is None else trunc(ste, 300),
            "source_paths": [x[0]["path"] for x in xs],
            "license": "CC-BY-NC-4.0",
        },
    )
    streams = []
    seen_ids = Counter()
    for info, d, _ in xs:
        mc = d.get("monitor_conversation")
        turns, recon = chunk_responses(d)
        N = info["chunk_size"]
        lo, hi = scale_of(monitor_system(mc))
        parsed = [parse_verdict_ex(x, (lo, hi)) for x in turns]
        scores = [v for v, _ in parsed]
        lenient_idx = [k for k, (_, how) in enumerate(parsed) if how == "lenient"]
        variant = info["monitor_variant"]
        prompt_id = f"mrt_sequential_{N}" + ("" if variant == "likert_reminder_v2" else f"+{variant or 'base'}")
        mid = f"{info['monitor']}|{prompt_id}|chunk"
        seen_ids[mid] += 1
        n_chunks_exp = math.ceil(n_msgs_mrt / N) if N else None
        # chunk k covers agent messages [kN, (k+1)N) of conversation[2:] -> step range
        chunk_steps = []
        for k in range(len(scores)):
            a, b = k * N, min((k + 1) * N, len(msg2step)) - 1
            chunk_steps.append([msg2step[a], msg2step[b]] if a < len(msg2step) and b >= a else None)
        awareness = "superaware" if "superaware" in variant else ("unaware" if "unaware" in variant else "aware")
        streams.append(ScoreStream(
            traj_id=tid, monitor_id=mid, unit="chunk", scores=scores, scale=(lo, hi),
            meta={
                "monitor_model": info["monitor"], "chunk_size": N, "monitor_style": info["monitor_style"],
                "monitor_variant": variant, "monitor_awareness": awareness,
                "summary_mode": "sequential_v2" in ("sequential" + info["monitor_style"][len(f"sequential_{N}"):]),
                "history": "summary" if "sequential_v2" in ("sequential" + info["monitor_style"][len(f"sequential_{N}"):]) else "full",
                "n_chunks_expected": n_chunks_exp, "chunk_step_range": chunk_steps,
                "final_verdict": parse_verdict(d.get("monitoring_response"), (lo, hi)),
                "lenient_parsed_chunks": lenient_idx, "score_reconstruction": recon,
                "source_path": info["path"], "dup_index": seen_ids[mid] - 1,
            },
        ))
    return t, streams


# ---------------------------------------------------------------- QC

def _auroc(pos, neg):
    import numpy as np
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    allv = np.concatenate([pos, neg])
    from scipy.stats import rankdata
    r = rankdata(allv)
    return float((r[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def qc() -> None:
    import numpy as np
    T = {d["traj_id"]: d for d in read_jsonl(OUT_DIR / "trajectories.jsonl")}
    S = list(read_jsonl(OUT_DIR / "scores.jsonl"))
    print(f"\n=== QC: {len(T)} trajectories, {len(S)} streams")
    c = Counter((d["label"], d["context"]["domain"]) for d in T.values())
    print("label x domain:", dict(c))
    c = Counter((d["context"]["domain"], d["context"]["task"], d["label"]) for d in T.values())
    print("by task (traj):")
    for task in sorted({k[1] for k in c}):
        dom = [k[0] for k in c if k[1] == task][0]
        print(f"  {dom:5s} {task:40s} honest {c[(dom, task, 'honest')]:4d}  attack {c[(dom, task, 'attack')]:4d}")
    cs = Counter((s["meta"]["chunk_size"], s["meta"]["monitor_model"], T[s["traj_id"]]["label"]) for s in S)
    print("streams by chunk size x monitor (honest/attack):")
    for (n, m) in sorted({(k[0], k[1]) for k in cs}):
        print(f"  N={n} {m:45s} {cs[(n, m, 'honest')]:4d} / {cs[(n, m, 'attack')]:4d}")
    cv = Counter((s["meta"]["monitor_variant"], s["meta"]["history"]) for s in S)
    print("monitor variants:", dict(cv))
    allv = [v for s in S for v in s["scores"]]
    nan = sum(v is None for v in allv)
    print(f"chunk verdicts: {len(allv)}, NaN {nan} ({nan / max(1, len(allv)):.3%}); streams with any NaN: "
          f"{sum(any(v is None for v in s['scores']) for s in S)}; empty streams: {sum(not s['scores'] for s in S)}")
    nl = sum(len(s["meta"]["lenient_parsed_chunks"]) for s in S)
    print(f"chunks parsed by lenient fallback: {nl} ({nl / max(1, len(allv)):.3%}); NaN by monitor:",
          dict(Counter(s["meta"]["monitor_model"] for s in S for v in s["scores"] if v is None)))
    scales = Counter(tuple(s["scale"]) for s in S)
    print("scales:", dict(scales))
    vals = [v for v in allv if v is not None]
    print("verdict value range:", min(vals), max(vals), "distinct:", sorted(Counter(vals).most_common(12)))
    fv_nan = sum(s["meta"]["final_verdict"] is None for s in S)
    last_eq = sum(1 for s in S if s["scores"] and s["scores"][-1] == s["meta"]["final_verdict"])
    print(f"final_verdict NaN {fv_nan}; final_verdict == last chunk verdict in {last_eq}/{len(S)}")
    print("honest attack_step None:", all(d["attack_step"] is None for d in T.values() if d["label"] == "honest"))
    mism = Counter()
    rel = []
    for s in S:
        t = T[s["traj_id"]]
        exp = s["meta"]["n_chunks_expected"]
        nom = math.ceil(t["meta"]["n_messages"] / s["meta"]["chunk_size"])
        L = len(s["scores"])
        mism["eq_exact(mrt split)"] += L == exp
        mism["eq_nominal(ceil(n_msgs/N))"] += L == nom
        mism["off_by>1_exact"] += abs(L - exp) > 1
        rel.append(L / max(1, len(t["steps"])) * s["meta"]["chunk_size"])
    print(f"stream length vs expected: {dict(mism)} of {len(S)}; median len*N/n_steps = {np.median(rel):.2f} "
          "(expected ~2: a chunk of N messages = ~N/2 steps)")
    sts = Counter((d["label"], d["side_task_success"]) for d in T.values())
    print("side_task_success:", dict(sts))
    print("strategy tokens (attack trajs):", Counter(t for d in T.values() if d["label"] == "attack" for t in d["context"]["attack_strategy"]).most_common(20))
    nst = [len(d["steps"]) for d in T.values()]
    print("steps/traj quantiles:", np.quantile(nst, [0, .1, .5, .9, 1]).tolist())
    multi = Counter(len({s["monitor_id"] for s in S if s["traj_id"] == tid}) for tid in list(T)[:0])
    per_t = Counter(s["traj_id"] for s in S)
    print("streams per trajectory:", dict(Counter(per_t.values())))
    print("\nAUROC of max-over-chunks (attack vs honest), per monitor_id with >=20 each:")
    by = defaultdict(lambda: {"honest": [], "attack": []})
    for s in S:
        v = [x for x in s["scores"] if x is not None]
        if v:
            by[s["monitor_id"]][T[s["traj_id"]]["label"]].append(max(v))
    rows = []
    for mid, d in by.items():
        if len(d["honest"]) >= 20 and len(d["attack"]) >= 20:
            rows.append((mid, len(d["honest"]), len(d["attack"]), _auroc(d["attack"], d["honest"])))
    for r in sorted(rows, key=lambda r: -(r[1] + r[2])):
        print(f"  {r[0]:75s} h={r[1]:4d} a={r[2]:4d} AUROC={r[3]:.3f}")
    allh = [max(x for x in s["scores"] if x is not None) for s in S if T[s["traj_id"]]["label"] == "honest" and any(x is not None for x in s["scores"])]
    alla = [max(x for x in s["scores"] if x is not None) for s in S if T[s["traj_id"]]["label"] == "attack" and any(x is not None for x in s["scores"])]
    print(f"  pooled: h={len(allh)} a={len(alla)} AUROC={_auroc(alla, allh):.3f}")
    print("\n=== spot records")
    rng = random.Random(1)
    for lab in ("honest", "attack"):
        d = rng.choice([d for d in T.values() if d["label"] == lab])
        dd = {**d, "steps": d["steps"][:2], "meta": {k: (v[:12] if isinstance(v, list) else v) for k, v in d["meta"].items()}}
        print(json.dumps(dd, ensure_ascii=False)[:2500])
        s = next(s for s in S if s["traj_id"] == d["traj_id"])
        ss = {**s, "meta": {k: (v[:6] if isinstance(v, list) else v) for k, v in s["meta"].items()}}
        print(json.dumps(ss)[:1200])
        print()


if __name__ == "__main__":
    if "--qc-only" in sys.argv:
        qc()
    else:
        build(skip_download="--no-download" in sys.argv)
