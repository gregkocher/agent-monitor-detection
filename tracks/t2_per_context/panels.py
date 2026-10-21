"""T2 panels: (dataset, monitor, context key) -> one row per trajectory with trajectory statistics.

A panel is a DataFrame with columns
    traj_id, label, ctx (context label, str), stat (max over units), top3 (mean of the 3 largest
    units), n_units, units (np.ndarray of per-unit scores, NaN dropped), plus extra context columns
    (side_task, policy, failure_type, agent_model, ...) used for attack-type selection.

Panels are cached as pickles in data/processed/t2_panels/ (gitignored). Build all with
    unset VIRTUAL_ENV; uv run python tracks/t2_per_context/panels.py
"""
from __future__ import annotations

import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from amd.common.schema import PROCESSED

CACHE = PROCESSED / "t2_panels"
LOCAL = "gemini-3.1-pro|akshn_local|full"
LOCAL_JS = "gemini-3.1-pro|akshn_local_judgestep|full"
CUM = "gemini-3.1-pro|akshn_cumulative|full"
AKSHN_SETS = ["akshn_bash", "akshn_iac", "akshn_shade", "akshn_agentdojo", "akshn_basharena_opus46",
              "akshn_basharena_sonnet45", "akshn_linuxarena"]
EXTRA = ["side_task", "policy", "failure_type", "agent_model", "env", "task_category", "setting",
         "main_task", "task", "domain", "side_task_group", "task_id"]


def _traj_meta(source: str) -> dict:
    out = {}
    with open(PROCESSED / source / "trajectories.jsonl") as f:
        for line in f:
            d = json.loads(line)
            c = d["context"]
            r = dict(label=d["label"], n_steps=len(d["steps"]))
            for k in EXTRA:
                if k in c:
                    r[k] = None if c[k] in (None, "None") else str(c[k])
            if source == "mb_honest" or source == "monitoringbench":
                r["mt_desc"] = c.get("main_task_description", "")
                r["submit_step"] = d["meta"].get("submit_step") if d["meta"].get("ends_with_submit") else None
            out[d["traj_id"]] = r
    return out


def _streams(source: str, monitors: set | None, fname: str = "scores.jsonl") -> dict:
    """(traj_id, monitor_id) -> np.ndarray of non-NaN unit scores."""
    out = {}
    path = PROCESSED / source / fname
    with open(path) as f:
        for line in f:
            d = json.loads(line)
            if monitors is not None and d["monitor_id"] not in monitors:
                continue
            s = np.array([np.nan if v is None else v for v in d["scores"]], float)
            s = s[~np.isnan(s)]
            if len(s):
                out[(d["traj_id"], d["monitor_id"])] = s
    return out


def _row(tid, meta, s):
    top = np.sort(s)[::-1][:3]
    return dict(traj_id=tid, stat=float(s.max()), top3=float(top.mean()), n_units=len(s), units=s,
                **meta)


def _panel(rows, ctx_fn, min_honest=1, min_attack=0, name=""):
    df = pd.DataFrame(rows)
    df["ctx"] = [ctx_fn(r) for r in df.to_dict("records")]
    df = df[df.ctx.notna()]
    cnt = df.groupby(["ctx", "label"]).size().unstack(fill_value=0)
    for col in ("honest", "attack"):
        if col not in cnt:
            cnt[col] = 0
    keep = cnt.index[(cnt.honest >= min_honest) & (cnt.attack >= min_attack)]
    df = df[df.ctx.isin(keep)].reset_index(drop=True)
    df.attrs["name"] = name
    return df


def build_akshn():
    panels = {}
    meta = {s: _traj_meta(s) for s in AKSHN_SETS}
    # LinuxArena goldset (10 envs), per-action local suspicion and cumulative confidence
    la = _streams("akshn_linuxarena", {LOCAL, CUM})
    for mon, tag in [(LOCAL, "local"), (CUM, "cum")]:
        rows = [_row(t, meta["akshn_linuxarena"][t], s) for (t, m), s in la.items() if m == mon]
        panels[f"la_env_{tag}"] = _panel(rows, lambda r: r["env"], 30, 30, f"la_env_{tag}")
        panels[f"la_model_{tag}"] = _panel(rows, lambda r: r.get("agent_model"), 30, 30,
                                           f"la_model_{tag}")
        panels[f"la_taskcat_{tag}"] = _panel(rows, lambda r: r.get("task_category"), 30, 30,
                                             f"la_taskcat_{tag}")
    # cross-setting: all 7 sets on the judge-step local series (available for every row);
    # BashArena 'honest_summarized' rows (summaries, not transcripts) are dropped
    rows = []
    for s in AKSHN_SETS:
        st = _streams(s, {LOCAL_JS})
        for (t, m), v in st.items():
            md = meta[s][t]
            if md.get("policy") == "honest_summarized":
                continue
            rows.append(_row(t, dict(md, source=s), v))
    panels["akshn_setting"] = _panel(rows, lambda r: r["source"].replace("akshn_", ""), 30, 30,
                                     "akshn_setting")
    ca = [r for r in rows if r["source"] in ("akshn_bash", "akshn_iac", "akshn_shade",
                                             "akshn_agentdojo")]
    panels["ca_setting_model"] = _panel(
        ca, lambda r: f"{r['source'].replace('akshn_', '')}/{r['agent_model']}", 30, 30,
        "ca_setting_model")
    return panels


def build_lasweep():
    panels = {}
    meta = _traj_meta("linuxarena_sweep")
    st = _streams("linuxarena_sweep", None)
    mons = sorted({m for (_, m) in st if m.endswith("|mean-action|full")})
    for m in mons:
        rows = [_row(t, meta[t], s) for (t, mm), s in st.items() if mm == m]
        name = "lasweep_" + m.split("|")[0]
        p = _panel(rows, lambda r: r["env"], 5, 5, name)
        p.attrs["monitor"] = m
        panels[name] = p
    return panels


def build_mrt():
    """MRT: one panel per monitor with >= 400 streams; contexts = task (20). Honest transcripts
    are shared across monitors; within a monitor every (traj, monitor) stream is unique."""
    panels = {}
    meta = _traj_meta("mrt")
    st = _streams("mrt", None)
    by_m = defaultdict(list)
    for (t, m), s in st.items():
        by_m[m].append(_row(t, meta[t], s))
    for m, rows in by_m.items():
        if len(rows) < 400:
            continue
        name = "mrt_" + m.split("|")[0].split("-2024")[0] + "_" + m.split("|")[1].replace(
            "mrt_sequential_", "N")
        p = _panel(rows, lambda r: r["task"], 5, 5, name)
        p.attrs["monitor"] = m
        panels[name] = p
    return panels


def mb_task_clusters(k: int = 8, seed: int = 0) -> dict:
    """KMeans(k) on TF-IDF of the MonitoringBench / Honest-550 main-task descriptions (136 tasks).
    Returns main_task -> cluster label 'c0'.. with the top terms recorded in CACHE/mb_clusters.json."""
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    desc = {}
    for s in ("monitoringbench", "mb_honest"):
        for t, r in _traj_meta(s).items():
            desc.setdefault(r["main_task"], r["mt_desc"])
    tasks = sorted(desc)
    vec = TfidfVectorizer(max_features=3000, stop_words="english", min_df=2, sublinear_tf=True)
    X = vec.fit_transform([desc[t] for t in tasks])
    km = KMeans(k, n_init=20, random_state=seed).fit(X)
    terms = np.array(vec.get_feature_names_out())
    info = {}
    for c in range(k):
        top = terms[np.argsort(km.cluster_centers_[c])[::-1][:8]].tolist()
        info[f"c{c}"] = dict(n_tasks=int((km.labels_ == c).sum()), top_terms=top)
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "mb_clusters.json").write_text(json.dumps(info, indent=1))
    return {t: f"c{l}" for t, l in zip(tasks, km.labels_)}


def build_mb():
    """MonitoringBench attacks + Honest-550, re-scored by cheap monitors (trajectory mode by T2,
    per-step by T1 when available). Contexts = TF-IDF task clusters."""
    panels = {}
    clus = mb_task_clusters()
    mh, ma = _traj_meta("mb_honest"), _traj_meta("monitoringbench")
    files = {}
    for f in (PROCESSED / "mb_honest").glob("scores_*.jsonl"):
        if f.name.startswith("pilot") or f.stat().st_size == 0:
            continue
        if (PROCESSED / "monitoringbench" / f.name).exists():
            files[f.name] = f
    for fname in sorted(files):
        rows, cnt = [], {}
        for src, meta in (("mb_honest", mh), ("monitoringbench", ma)):
            st = _streams(src, None, fname)
            cnt[src] = len(st)
            for (t, m), s in st.items():
                ss = meta[t].get("submit_step")
                if len(s) > 1 and ss is not None and ss == len(s) - 1:
                    s = s[:-1]  # strip the final submit step (99% of honest vs 78% of attacks)
                rows.append(_row(t, meta[t], s))
        if min(cnt.values()) < 300:  # wait until both sides are scored
            continue
        name = "mb_" + fname.replace("scores_openai_", "").replace(".jsonl", "")
        p = _panel(rows, lambda r: clus.get(r["main_task"]), 20, 20, name)
        p.attrs["monitor"] = fname
        panels[name] = p
    return panels


def build_all(which=("akshn", "lasweep", "mrt", "mb")):
    CACHE.mkdir(parents=True, exist_ok=True)
    fns = dict(akshn=build_akshn, lasweep=build_lasweep, mrt=build_mrt, mb=build_mb)
    for w in which:
        for name, p in fns[w]().items():
            with open(CACHE / f"{name}.pkl", "wb") as f:
                pickle.dump(p, f)
            c = p.groupby(["ctx", "label"]).size().unstack(fill_value=0)
            print(f"{name:40s} ctx={len(c):3d} honest={int(c.get('honest', 0).sum()):5d} "
                  f"attack={int(c.get('attack', 0).sum()):5d} min_h={int(c.get('honest', 0).min())}",
                  flush=True)


def load(name: str) -> pd.DataFrame:
    with open(CACHE / f"{name}.pkl", "rb") as f:
        p = pickle.load(f)
    p.attrs.setdefault("name", name)
    return p


def available() -> list[str]:
    return sorted(f.stem for f in CACHE.glob("*.pkl"))


if __name__ == "__main__":
    build_all(tuple(sys.argv[1:]) or ("akshn", "lasweep", "mrt", "mb"))
