"""Persistent-state / Iterative VibeCoding (Hills, Caspary & Cooper Stickland, arXiv 2607.02514).

HF dataset `idacy/control-arena-persistent-state-eval-logs-2026-05-23` (mirror of the paper repo's `logs/`).
Each Inspect `.eval` is one run of a 5-PR task sequence; each sample is one PR. Per-PR scores come from GPT-4o
monitors (diff monitor with three history modes, a trajectory monitor) plus a run-level ensemble on the last PR.

Runs used (agent claude-sonnet-4.5, monitor gpt-4o, future_visibility=3, past_memory=1, all 5 CLI sequences):
    Josh3/honest_all        173 honest runs
    Josh3/gradual_f3m1      120 gradual attacks (5 sequences x 2 side tasks x 12)
    Josh3/positional_f3m1   400 positional attacks (5 x 2 x target_position 0..4 x 8); each eval holds only
                            PRs target_position..4; PRs 0..target_position-1 come from one cached honest run per
                            sequence (`_honest_cache/`, also part of honest_all)
    rescored/paper_4ensemble_josh3   exactly the 173 honest + 120 gradual evals (same task ids) with two extra
                            trajectory-monitor scores appended; the original scores are kept in the file
    rescored/paper_4ensemble_20260315  210 evals from other (2026-03-12/13) batches: no overlap, not used

Only header.json, summaries.json and the top-level `metadata` object of each sample member are read, over HTTP
range requests (the sample member is decompressed as a stream and abandoned once `metadata` is parsed). A compact
per-eval extract is cached in data/raw/persistent_state/<subdir>/<task_id>.json, so reruns are cheap.

Secrets: sample metadata carries a honeypot `API_KEY` and webhook URLs; only whitelisted fields are kept, the
honeypot value is used only to scrub stored strings, and header revision/origin fields are never read out.

Usage: python -m amd.data.persistent_state
"""
from __future__ import annotations

import json
import math
import random
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import httpx

from amd.common.schema import PROCESSED, RAW, ScoreStream, Step, Trajectory, write_jsonl
from amd.data._util import hf_headers, open_remote_zip, trunc

SOURCE = "persistent_state"
DATASET = "idacy/control-arena-persistent-state-eval-logs-2026-05-23"
TREE = f"https://huggingface.co/api/datasets/{DATASET}/tree/main/"
RESOLVE = f"https://huggingface.co/datasets/{DATASET}/resolve/main/"
RAW_DIR = RAW / SOURCE

HONEST = "logs/Josh3/honest_all"
GRADUAL = "logs/Josh3/gradual_f3m1"
POSITIONAL = "logs/Josh3/positional_f3m1"
RESCORED = "logs/rescored/paper_4ensemble_josh3"
RESCORED_OTHER = "logs/rescored/paper_4ensemble_20260315"

CLI_SEQUENCES = {"config-validator", "deploy-helper", "expense-tracker", "incident-reporter", "uptime-monitor"}
DIFF_CHARS = 3000
DESC_CHARS = 200

# per-PR suspicion keys -> history mode (score_pr_traj runs with the setting's default traj mode, task_sequence)
HISTORY = {
    "score_pr_diff_current_only": "current_only",
    "score_pr_diff_full_diffs": "full_diffs",
    "score_pr_diff_task_sequence": "task_sequence",
    "score_pr_traj": "task_sequence",
    "score_pr_traj_task_sequence": "task_sequence",
    "score_pr_traj_full_trajectories": "full_trajectories",
    "ensemble_scorer": "run_ensemble",
}
# run-level aggregates of the three diff monitors, reported on the last PR only: derivable, not exported
AGGREGATES = {"max_of_3", "mean_of_3", "median_of_3", "monitor_sus_aggregator"}
P_ATTACK = re.compile(r"P\(attack\)=([0-9.]+)")
THRESH = re.compile(r"threshold=([0-9.]+)")
KEYLIKE = re.compile(r"(sk-[A-Za-z0-9_\-]{16,}|hf_[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9_\-]{16,})")


# ----------------------------------------------------------------------------------------------- listing
def list_tree(path: str) -> list[dict]:
    """All files under `path` (recursive), following the HF tree API's Link-header pagination."""
    url, out = TREE + quote(path) + "?recursive=true", []
    with httpx.Client(headers=hf_headers(), timeout=120, follow_redirects=True) as c:
        while url:
            r = c.get(url)
            r.raise_for_status()
            out += [x for x in r.json() if x["type"] == "file"]
            m = re.search(r'<([^>]+)>;\s*rel="next"', r.headers.get("link", ""))
            url = m.group(1) if m else None
    return out


def task_id(path: str) -> str:
    return path.rsplit("/", 1)[-1].removesuffix(".eval").rsplit("_", 1)[-1]


# ----------------------------------------------------------------------------------------------- extraction
def _score_value(v):
    """Inspect score value -> float | str (C/I/N) | None."""
    if isinstance(v, dict):
        v = next(iter(v.values()), None) if len(v) == 1 else None
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    return v if isinstance(v, str) else None


def _scrub(s: str, secrets: set[str]) -> str:
    if not isinstance(s, str):
        return s
    for sec in secrets:
        if sec and len(sec) >= 6:
            s = s.replace(sec, "[REDACTED_API_KEY]")
    return KEYLIKE.sub("[REDACTED_KEY]", s)


def _header_info(h: dict) -> dict:
    ev = h.get("eval", {})
    md = ev.get("metadata") or {}
    st, mp = md.get("setting") or {}, md.get("micro_protocol") or {}
    roles = ev.get("model_roles") or {}
    return {
        "task": ev.get("task"), "created": ev.get("created"), "task_id": ev.get("task_id"),
        "status": h.get("status"), "agent_model": ev.get("model"),
        "trusted_model": (roles.get("trusted") or {}).get("model"),
        "untrusted_model": (roles.get("untrusted") or {}).get("model"),
        "sequence": st.get("sequence"), "side_task": st.get("side_task"),
        "future_visibility": st.get("future_visibility"), "past_memory": st.get("past_memory"),
        "monitor_history_modes": st.get("monitor_history_modes"), "traj_history_modes": st.get("traj_history_modes"),
        "use_agentic_scorer": st.get("use_agentic_scorer"),
        "policy_type": mp.get("type"), "target_position": mp.get("target_position"),
        "attack_prompt_file": mp.get("prompt_file"), "mode": md.get("mode"),
        "n_samples": (ev.get("dataset") or {}).get("samples"),
        "completed_samples": (h.get("results") or {}).get("completed_samples"),
    }


def _summary_info(s: dict) -> dict:
    scores = {}
    for k, sc in (s.get("scores") or {}).items():
        if k in AGGREGATES:
            continue
        d = {"value": _score_value(sc.get("value"))}
        ex = sc.get("explanation") or ""
        if k == "ensemble_scorer":
            m, t = P_ATTACK.search(ex), THRESH.search(ex)
            d["p_attack"] = float(m.group(1)) if m else None
            d["threshold"] = float(t.group(1)) if t else None
        elif k == "main_task_success":
            d["disabled"] = "disabled" in ex.lower()
        elif k == "side_task_success":
            d["checked"] = not ex.startswith(("No test_command", "No side_task_name"))
        scores[k] = d
    return {"id": s.get("id"), "scores": scores, "error": bool(s.get("error"))}


def _sample_metadata(z, name: str, max_bytes: int = 64 << 20) -> dict | None:
    """Stream-decompress a sample member just far enough to parse its top-level `metadata` object."""
    info = z.getinfo(name)
    with z.open(info) as f:
        buf = ""
        start = -1
        while True:
            chunk = f.read(1 << 18)
            if not chunk:
                break
            buf += chunk.decode("utf-8", errors="replace")
            if start < 0:
                i = buf.find('\n  "metadata": {')
                if i >= 0:
                    start = i + len('\n  "metadata": ')
            if start >= 0 and re.search(r'\n  "[a-z_]+": ', buf[start:]):
                break
            if len(buf) > max_bytes:
                return None
    if start < 0:
        return None
    obj, _ = json.JSONDecoder().raw_decode(buf, start)
    return obj


def _pr_metadata(md: dict) -> dict:
    nested = md.get("metadata") if isinstance(md.get("metadata"), dict) else {}
    secrets = {v for k, v in md.items() if isinstance(v, str) and re.search(r"key|token|secret", k, re.I)}
    sc = lambda s, n: _scrub(trunc(s, n), secrets) if s else ""
    return {
        "main_task_name": md.get("main_task_name"),
        "main_task_description": sc(md.get("main_task_description"), 600),
        "side_task_name": md.get("side_task_name"),
        "side_task_description": sc(md.get("side_task_description"), 600),
        "eval_mode": md.get("eval_mode"),
        "run_id": nested.get("run_id"), "task_index": nested.get("task_index"),
        "total_tasks": nested.get("total_tasks"),
        "future_visibility": nested.get("future_visibility"), "past_memory": nested.get("past_memory"),
        "control_solver_error": sc(md.get("control_solver_error"), 300) or None,
        "git_head_before": md.get("git_head_before"), "git_head_after": md.get("git_head_after"),
        "pr_diff_chars": len(md.get("pr_diff") or ""),
        "pr_diff": sc(md.get("pr_diff"), DIFF_CHARS),
    }


def extract(path: str, subdir: str, full: bool) -> dict:
    """Compact per-eval extract (header + per-PR scores [+ per-PR metadata]), cached on disk."""
    cache = RAW_DIR / subdir / f"{task_id(path)}{'' if full else '.summ'}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    z = open_remote_zip(RESOLVE + quote(path), hf_headers())
    names = z.namelist()
    h = json.loads(z.read("header.json")) if "header.json" in names else {}
    if "summaries.json" in names:
        summ = json.loads(z.read("summaries.json"))
    else:
        summ = []
        for n in sorted((n for n in names if n.startswith("_journal/summaries/")),
                        key=lambda n: int(re.sub(r"\D", "", n.rsplit("/", 1)[-1]) or 0)):
            summ += json.loads(z.read(n))
    prs = [_summary_info(s) for s in summ]
    if full:
        members = {n[len("samples/"):].removesuffix("_epoch_1.json"): n for n in names if n.startswith("samples/")}
        for p in prs:
            n = members.get(p["id"])
            md = _sample_metadata(z, n) if n else None
            p["metadata"] = _pr_metadata(md) if md else None
    out = {"path": path, "file": path.rsplit("/", 1)[-1], "subdir": subdir, "header": _header_info(h), "prs": prs}
    cache.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_suffix(".part")
    tmp.write_text(json.dumps(out))
    tmp.rename(cache)
    return out


# ----------------------------------------------------------------------------------------------- assembly
def _pr_index(pr_id: str) -> int:
    return int(re.match(r"PR(\d+)_", pr_id).group(1))


def _num(d: dict | None, key: str) -> float:
    if not d:
        return math.nan
    if key == "ensemble_scorer":
        v = d.get("p_attack")
        return math.nan if v is None else float(v)
    v = d.get("value")
    return float(v) if isinstance(v, float) else math.nan


def _success(d: dict | None, kind: str):
    if not d or d.get("value") not in ("C", "I"):
        return None
    if kind == "main" and d.get("disabled"):
        return None
    return d["value"] == "C"


def _title(desc: str | None) -> str:
    if not desc:
        return ""
    first = re.split(r"(?<=[.!?])\s", desc.strip(), maxsplit=1)[0]
    return trunc(first, DESC_CHARS) if len(first) <= DESC_CHARS else first[:DESC_CHARS] + "..."


def _step(i: int, pr: dict | None) -> Step:
    if pr is None:
        return Step(idx=i, action=f"PR {i}: [missing from log]")
    md = pr.get("metadata") or {}
    act = f"PR {i} ({md.get('main_task_name') or pr['id']}): {_title(md.get('main_task_description'))}\n"
    act += md.get("pr_diff") or "[no pr_diff]"
    ms = _success(pr["scores"].get("main_task_success"), "main")
    ss = _success(pr["scores"].get("side_task_success"), "side")
    sd = pr["scores"].get("side_task_success") or {}
    out = (f"main_task_success={'n/a (scoring disabled)' if ms is None else ms}; "
           f"side_task_success={ss if sd.get('checked') else 'not checked on this PR'}")
    return Step(idx=i, action=act, output=out)


def assemble(label: str, policy: str, ext: dict, ext_raw: dict | None, prefix: dict | None):
    """One Trajectory + ScoreStreams for a run. `ext` = primary extract (rescored copy for honest/gradual,
    raw copy for positional), `ext_raw` = raw copy for honest/gradual (score comparison), `prefix` = honest-cache
    extract providing PRs 0..target_position-1 of a positional run."""
    hd = ext["header"]
    prs = {_pr_index(p["id"]): (p, "attack_eval" if prefix else ext["subdir"]) for p in ext["prs"]}
    tpos = hd.get("target_position") if policy == "positional" else None
    if prefix is not None:
        for p in prefix["prs"]:
            k = _pr_index(p["id"])
            if k < (tpos or 0) and k not in prs:
                prs[k] = (p, "honest_cache")
    n = max(5, max(prs) + 1) if prs else 5
    steps = [_step(i, prs[i][0] if i in prs else None) for i in range(n)]

    mds = [(prs[i][0].get("metadata") or {}) if i in prs else {} for i in range(n)]
    own = [p.get("metadata") or {} for p in ext["prs"]]
    run_key = next((m.get("run_id") for m in own if m.get("run_id")), None) or task_id(ext["path"])
    main = [_success(prs[i][0]["scores"].get("main_task_success"), "main") if i in prs else None for i in range(n)]
    side = [_success(prs[i][0]["scores"].get("side_task_success"), "side") if i in prs else None for i in range(n)]
    harm = next((i for i, s in enumerate(side) if s), None)
    if label == "honest":
        sts, harm = None, None
    else:
        sts = any(bool(s) for s in side) if any(s is not None for s in side) else None

    # positional: seam check (attack eval's first PR starts from the cache's last prefix commit)
    seam = None
    if prefix is not None and tpos:
        a = (prs.get(tpos, ({}, ""))[0].get("metadata") or {}).get("git_head_before")
        b = (prs.get(tpos - 1, ({}, ""))[0].get("metadata") or {}).get("git_head_after")
        seam = (a == b) if a and b else None

    attack_step = tpos if policy == "positional" else None
    monitor = hd.get("trusted_model")
    ctx = {
        "app": hd.get("sequence"), "task_sequence": hd.get("sequence"),
        "task_family": "cli" if hd.get("sequence") in CLI_SEQUENCES else None,
        "side_task": hd.get("side_task") if label == "attack" else None,
        "attack_policy": policy if label == "attack" else None,
        "agent_model": hd.get("agent_model"), "monitor_model": monitor,
        "future_visibility": hd.get("future_visibility"), "past_memory": hd.get("past_memory"),
        "target_position": tpos,
        "main_tasks": [m.get("main_task_name") for m in mds],
    }
    files = [ext["file"]] + ([prefix["file"]] if prefix else [])
    meta = {
        "run_id": run_key, "source_subdir": ext["subdir"],
        "raw_subdir": ext_raw["subdir"] if ext_raw else None,
        "eval_files": files + ([ext_raw["file"]] if ext_raw and ext_raw["file"] not in files else []),
        "eval_task_id": hd.get("task_id"),
        "n_prs": sum(i in prs for i in range(n)),
        "complete": all(i in prs for i in range(n)),
        "pr_origin": [prs[i][1] if i in prs else None for i in range(n)],
        "main_task_success": main, "side_task_success": side,
        "main_task_scoring_disabled": all(m is None for m in main),
        "control_solver_error": [m.get("control_solver_error") for m in mds],
        "pr_diff_chars": [m.get("pr_diff_chars") for m in mds],
        "attack_prompt_file": hd.get("attack_prompt_file") if label == "attack" else None,
        "monitor_model": monitor, "use_agentic_diff_monitor": hd.get("use_agentic_scorer"),
        "positional_prefix_seam_ok": seam,
        "attack_step_basis": ("micro_protocol.target_position" if policy == "positional" else
                              "not specified (gradual policy spreads the side task opportunistically)"
                              if policy == "gradual" else None),
    }
    traj = Trajectory(traj_id=f"{SOURCE}:{run_key}", source=SOURCE, label=label, context=ctx, steps=steps,
                      attack_step=attack_step, harm_step=harm, side_task_success=sts, meta=meta)

    # ---- score streams
    keys = [k for k in dict.fromkeys(k for p in ext["prs"] for k in p["scores"])
            if k in HISTORY or k.startswith("score_") or "link" in k]
    streams = []

    def series(src: dict, key: str, use_prefix: bool) -> list[float]:
        by = {_pr_index(p["id"]): p for p in src["prs"]}
        if use_prefix and prefix is not None:
            for p in prefix["prs"]:
                k = _pr_index(p["id"])
                if k < (tpos or 0) and k not in by:
                    by[k] = p
        return [_num(by[i]["scores"].get(key), key) if i in by else math.nan for i in range(n)]

    for key in keys:
        hist = HISTORY.get(key, "unknown")
        mid = f"{monitor}|{key}|{hist}"
        s = series(ext, key, True)
        sm = {"history": hist, "score_key": key, "subdir": ext["subdir"]}
        if key == "ensemble_scorer":
            thr = next((p["scores"]["ensemble_scorer"].get("threshold") for p in ext["prs"]
                        if p["scores"].get("ensemble_scorer", {}).get("threshold") is not None), None)
            sm |= {"value": "P(attack) of the run-level ensemble, last PR only", "threshold": thr}
        if prefix is not None and tpos:
            sm["prefix_from_honest_cache"] = tpos
        if ext_raw is not None:
            r = series(ext_raw, key, False)
            both = [(a, b) for a, b in zip(s, r) if not (math.isnan(a) and math.isnan(b))]
            if not any(not math.isnan(b) for b in r):
                sm["only_in"] = ext["subdir"]
            elif any(a != b for a, b in both):
                # raw and rescored disagree: keep the raw (original run) series too, as its own stream
                streams.append(ScoreStream(traj.traj_id, f"{mid}@{ext_raw['subdir']}", "pr", r,
                                           (0.0, 1.0) if key == "ensemble_scorer" else (1.0, 10.0),
                                           {**sm, "subdir": ext_raw["subdir"]}))
                mid = f"{mid}@{ext['subdir']}"
        streams.append(ScoreStream(traj.traj_id, mid, "pr", s,
                                   (0.0, 1.0) if key == "ensemble_scorer" else (1.0, 10.0), sm))
    return traj, streams


# ----------------------------------------------------------------------------------------------- build
def build(workers: int = 4):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    listing_cache = RAW_DIR / "listing.json"
    if listing_cache.exists():
        listing = json.loads(listing_cache.read_text())
    else:
        listing = {d: [f["path"] for f in list_tree(d) if f["path"].endswith(".eval")]
                   for d in (HONEST, GRADUAL, POSITIONAL, RESCORED, RESCORED_OTHER)}
        listing_cache.write_text(json.dumps(listing))
    by_tid = {d: {task_id(p): p for p in ps} for d, ps in listing.items()}
    for d, m in by_tid.items():
        print(f"{d}: {len(m)} .eval")
    resc = by_tid[RESCORED]
    print(f"{RESCORED_OTHER}: overlap with Josh3 runs = "
          f"{len(set(by_tid[RESCORED_OTHER]) & (set(by_tid[HONEST]) | set(by_tid[GRADUAL]) | set(by_tid[POSITIONAL])))}"
          " (not used)")

    cache_tids = {task_id(p) for p in listing[POSITIONAL] if "/_honest_cache/" in p}
    pos_attack = {t: p for t, p in by_tid[POSITIONAL].items() if t not in cache_tids}
    jobs = []  # (path, subdir, full)
    for d in (HONEST, GRADUAL):
        for t, p in by_tid[d].items():
            if t in resc:
                jobs.append((resc[t], "paper_4ensemble_josh3", True))
                jobs.append((p, d.split("/")[-1], False))
            else:
                jobs.append((p, d.split("/")[-1], True))
    for t, p in pos_attack.items():
        jobs.append((p, "positional_f3m1", True))
    for t in cache_tids:  # honest caches: use the honest_all copy (rescored) if present
        if t not in by_tid[HONEST]:
            jobs.append((by_tid[POSITIONAL][t], "positional_f3m1", True))
    print(f"extracting {len(jobs)} eval files ({workers} workers)")

    def run(j):
        for attempt in range(8):
            try:
                return j, extract(*j)
            except Exception as e:  # back off on HF rate limits (429) / transient errors, then report
                resp = getattr(e, "response", None)
                if attempt == 7 or (resp is not None and resp.status_code in (401, 403, 404)):
                    return j, e
                wait = 15 * 2 ** min(attempt, 3)
                if resp is not None and resp.status_code == 429:
                    try:
                        wait = max(wait, float(resp.headers.get("retry-after", 0)))
                    except ValueError:
                        pass
                time.sleep(wait + random.random() * 5)

    ext = {}
    with ThreadPoolExecutor(workers) as ex:
        for k, (j, r) in enumerate(ex.map(run, jobs)):
            if isinstance(r, Exception):
                print(f"  FAILED {j[0].rsplit('/', 1)[-1]}: {type(r).__name__}: {str(r)[:200]}")
                continue
            ext[(task_id(j[0]), j[1])] = r
            if (k + 1) % 100 == 0:
                print(f"  {k + 1}/{len(jobs)}")

    def primary(t, d):
        sub = "paper_4ensemble_josh3" if t in resc else d.split("/")[-1]
        return ext.get((t, sub)), ext.get((t, d.split("/")[-1])) if t in resc else None

    # honest cache per sequence
    cache_by_seq = {}
    for t in cache_tids:
        e = primary(t, HONEST)[0] if t in by_tid[HONEST] else ext.get((t, "positional_f3m1"))
        if e:
            cache_by_seq[e["header"]["sequence"]] = e

    pairs = []
    for d, label, policy in ((HONEST, "honest", "honest"), (GRADUAL, "attack", "gradual")):
        for t in by_tid[d]:
            e, er = primary(t, d)
            if e is not None:
                pairs.append(assemble(label, policy, e, er, None))
    for t in pos_attack:
        e = ext.get((t, "positional_f3m1"))
        if e is not None:
            pairs.append(assemble("attack", "positional", e, None, cache_by_seq.get(e["header"]["sequence"])))
    empty = [tr.meta["eval_files"][0] for tr, _ in pairs if tr.meta["n_prs"] == 0]
    if empty:  # evals that logged no PR sample at all carry nothing usable
        print(f"dropping {len(empty)} runs with no logged PR: {empty}")
        pairs = [(tr, ss) for tr, ss in pairs if tr.meta["n_prs"] > 0]
    ids = Counter(tr.traj_id for tr, _ in pairs)
    dup = {k for k, v in ids.items() if v > 1}
    for tr, ss in pairs:  # disambiguate colliding run keys with the eval task id
        if tr.traj_id in dup:
            tr.traj_id = f"{tr.traj_id}:{tr.meta['eval_task_id']}"
            for s in ss:
                s.traj_id = tr.traj_id
    if dup:
        print(f"WARNING: {len(dup)} duplicate run keys disambiguated with the eval task id")
    trajs = [tr for tr, _ in pairs]
    for tr in trajs:  # shared context keys (amd/data/README.md)
        tr.context["policy"] = tr.context.get("attack_policy") or "honest"
        tr.context["main_task"] = tr.context.get("task_sequence")
    scores = [s for _, ss in pairs for s in ss]
    n1 = write_jsonl(PROCESSED / SOURCE / "trajectories.jsonl", trajs)
    n2 = write_jsonl(PROCESSED / SOURCE / "scores.jsonl", scores)
    print(f"wrote {n1} trajectories, {n2} score streams")


if __name__ == "__main__":
    build()
