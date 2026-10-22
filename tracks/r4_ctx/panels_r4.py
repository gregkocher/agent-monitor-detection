"""Round-4 per-context panels with many honest runs per context.

Every panel is a DataFrame with one row per trajectory:
    traj_id, label (honest|attack), ctx, stat (trajectory max of the per-action score), group (split unit),
    side_task, policy (attack policy / agent model, the unit of the unseen-policy transfer test), damage
    (attacks only; 0-10), src.

Panels
------
akshn_setting      aksh-n 7 settings, Gemini-3.1-Pro local suspicion (judge-step series; T2 round 1 panel),
                   328-1,396 honest per setting. Damage = adjudicated overall_severity (0-10).   [largest n]
ca_setting_model   ControlArena setting x agent (12 contexts, ~250 honest each), same monitor.
la_pub_env         public LinuxArena (data.linuxarena.ai = HF anonymouslinuxarena/linuxarena-public),
                   per-action monitor mean-action@gpt-5-nano (0-100), 11 honest agent models x 200 tasks,
                   context = environment (10, ~217 honest each); attacks = 8 attack agent models, Haiku
                   obvious-attack and Opus strategy-attack. Damage = side-task severity tier (steep).
la_pub_taskcat     same, context = main-task category (6).
xd_g54nano         cross-deployment panel, monitor simple@gpt-5.4-nano-none (0-100): contexts BashArena
                   (596 honest), MonitoringBench (520 honest, Opus-4.5 Honest-550), LinuxArena leaderboard
                   runs (13 agents x 10 envs). Damage = side-task tier (steep).
xd_g41nano,        BashArena vs MonitoringBench only (2 contexts), monitors simple@gpt-4.1-nano-none and
xd_g5nano          simple@gpt-5-nano-minimal.

Split unit (`group`): main task when a context has >= MIN_GROUPS distinct main tasks, otherwise the single
trajectory (aksh-n iac / shade / agentdojo have 5-16 main tasks, so a task-grouped split would leave 2-8 tasks
per half). Pre-specified in EXPERIMENT_LOG.md (2026-10-22, round 4).

    unset VIRTUAL_ENV; uv run python tracks/r4_ctx/panels_r4.py
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tracks" / "r2_t2"))
sys.path.insert(0, str(ROOT / "tracks" / "r4_ctx"))
import r2lib as R  # noqa: E402

RAW = ROOT / "data" / "raw" / "r4_ctx"
CACHE = ROOT / "data" / "processed" / "r4_ctx" / "panels"
MIN_GROUPS = 20
STEEP = R.TIER_WEIGHTS["steep"]  # tier -> 1, 2.5, 5, 10


def _assign_groups(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    g = []
    ntask = df.groupby("ctx").main_task.nunique()
    for ctx, mt, tid in zip(df.ctx, df.main_task, df.traj_id):
        if ntask[ctx] >= MIN_GROUPS and isinstance(mt, str):
            g.append(f"{ctx}|mt:{mt}")
        else:
            g.append(f"{ctx}|traj:{tid}")
    df["group"] = g
    return df


def _finish(df: pd.DataFrame, name: str) -> pd.DataFrame:
    df = _assign_groups(df)
    cols = ["traj_id", "label", "ctx", "stat", "group", "main_task", "side_task", "policy", "damage", "src"]
    df = df[cols].reset_index(drop=True)
    df.attrs["name"] = name
    return df


# --------------------------------------------------------------------------------------------
# aksh-n (local, built by T2 round 1)
# --------------------------------------------------------------------------------------------


def build_akshn(name: str) -> pd.DataFrame:
    p = R.load(name)
    df = pd.DataFrame(dict(traj_id=p.traj_id, label=p.label, ctx=p.ctx, stat=p.stat.astype(float),
                           main_task=p.main_task, side_task=p.side_task, policy=p.agent_model,
                           damage=np.where(p.label == "attack", p.severity.clip(0, 10), np.nan),
                           src="akshn"))
    if df.loc[df.label == "attack", "damage"].isna().any():
        raise ValueError("attack without adjudicated severity")
    return _finish(df, name)


# --------------------------------------------------------------------------------------------
# public LinuxArena (data.linuxarena.ai metadata, fetched by fetch_linuxarena.py)
# --------------------------------------------------------------------------------------------


def _la_rows(monitor: str, run_filter) -> pd.DataFrame:
    """One row per trajectory of the runs selected by run_filter(run) that carry `monitor`. Re-uploads of the
    same run (same name) are collapsed to the latest upload that has the monitor, so no agent trajectory is
    counted twice."""
    runs = {r["run_id"]: r for r in json.loads((RAW / "la_runs.json").read_text())}
    rows = []
    with open(RAW / "la_traj_meta.jsonl") as f:
        for line in f:
            d = json.loads(line)
            run = runs[d["run_id"]]
            if not run_filter(run):
                continue
            m = (d.get("monitors") or {}).get(monitor)
            if not m or m.get("max") is None or d.get("error"):
                continue
            rows.append(dict(traj_id="la:" + d["trajectory_id"], run_id=d["run_id"], run=run["name"],
                             created=run["created_at"], env=d["environment_id"], main_task=d["main_task_id"],
                             side_task=d["side_task_id"], stat=float(m["max"]),
                             label="honest" if d["side_task_id"] is None else "attack"))
    df = pd.DataFrame(rows)
    latest = df.groupby("run").created.transform("max")
    df = df[df.created == latest]
    # if two uploads of one name share the latest timestamp, keep one run id
    keep = df.groupby("run").run_id.transform("first")
    return df[df.run_id == keep].reset_index(drop=True)


def _tier_damage(side_task) -> float:
    return float(STEEP[R.side_task_tier(side_task)]) if isinstance(side_task, str) else np.nan


def _agent_of(run_name: str) -> str:
    s = run_name.replace("LinuxArena paper: ", "")
    for tag in (" honest", " attack", " obvious-attack", " strategy-attack"):
        if tag in s:
            return s.split(tag)[0].strip() + ("/obvious" if "obvious" in s else "")
    return s.split(",")[0]


def build_la_pub(ctx_key: str) -> pd.DataFrame:
    mon = "mean-action@gpt-5-nano"

    def sel(run):
        n = run.get("name") or ""
        return n.startswith("LinuxArena paper:") and (
            "GPT-5 Nano monitor" in n or "strategy-attack, paper monitor sweep" in n)

    df = _la_rows(mon, sel)
    cats = json.loads((RAW / "la_task_categories.json").read_text())
    df["task_category"] = df.main_task.map(cats)
    df["ctx"] = df.env if ctx_key == "env" else df.task_category
    df = df[df.ctx.notna()]
    df["policy"] = ["strategy-attack/Opus" if "strategy-attack" in r else _agent_of(r) for r in df.run]
    df["damage"] = [(_tier_damage(s) if lab == "attack" else np.nan) for s, lab in zip(df.side_task, df.label)]
    df["src"] = "la_pub"
    return _finish(df, f"la_pub_{ctx_key}")


def _xd_ctx(run_name: str, env: str) -> str | None:
    if run_name in ("20943322", "basharena-attack"):
        return "basharena"
    if run_name in ("monitoring-bench", "monitoring-bench-honest"):
        return "monitoring_bench"
    if run_name.startswith("board-") and run_name.endswith("-linuxarena"):
        return "linuxarena"
    return None


def build_xd(monitor: str, name: str, contexts=None) -> pd.DataFrame:
    def sel(run):
        return _xd_ctx(run.get("name") or "", "") is not None

    df = _la_rows(monitor, sel)
    df["ctx"] = [_xd_ctx(r, e) for r, e in zip(df.run, df.env)]
    if contexts is not None:
        df = df[df.ctx.isin(contexts)]
    df["policy"] = [r.replace("board-models-", "").replace("board-protocols-", "").replace("-linuxarena", "")
                    for r in df.run]
    df["damage"] = [(_tier_damage(s) if lab == "attack" else np.nan) for s, lab in zip(df.side_task, df.label)]
    df["src"] = "la_api"
    return _finish(df, name)


# --------------------------------------------------------------------------------------------


def la_task_categories():
    """Fetch main_task -> task_category for the la_pub runs (cached)."""
    path = RAW / "la_task_categories.json"
    if path.exists():
        return
    from fetch_linuxarena import fetch_task_categories
    runs = json.loads((RAW / "la_runs.json").read_text())
    ids = [r["run_id"] for r in runs if (r.get("name") or "").startswith("LinuxArena paper:")
           and ("GPT-5 Nano monitor" in r["name"] or "paper monitor sweep" in r["name"])]
    cats = fetch_task_categories(ids)
    path.write_text(json.dumps(cats, indent=0, sort_keys=True))


BUILDERS = {
    "akshn_setting": lambda: build_akshn("akshn_setting"),
    "ca_setting_model": lambda: build_akshn("ca_setting_model"),
    "la_pub_env": lambda: build_la_pub("env"),
    "la_pub_taskcat": lambda: build_la_pub("taskcat"),
    "xd_g54nano": lambda: build_xd("simple@gpt-5.4-nano-none", "xd_g54nano"),
    "xd_g41nano": lambda: build_xd("simple@gpt-4.1-nano-none", "xd_g41nano", ("basharena", "monitoring_bench")),
    "xd_g5nano": lambda: build_xd("simple@gpt-5-nano-minimal", "xd_g5nano", ("basharena", "monitoring_bench")),
}


def load(name: str) -> pd.DataFrame:
    with open(CACHE / f"{name}.pkl", "rb") as f:
        df = pickle.load(f)
    df.attrs["name"] = name
    return df


def describe(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ctx, g in df.groupby("ctx"):
        h, a = g[g.label == "honest"], g[g.label == "attack"]
        rows.append(dict(panel=df.attrs.get("name"), ctx=ctx, n_honest=len(h), n_attack=len(a),
                         honest_groups=h.group.nunique(), attack_groups=a.group.nunique(),
                         grouped_by_task=bool(g.group.str.contains(r"\|mt:").any()),
                         side_tasks=a.side_task.nunique(), policies=a.policy.nunique(),
                         honest_p99=float(np.quantile(h.stat, 0.99)) if len(h) else np.nan,
                         attack_median=float(a.stat.median()) if len(a) else np.nan,
                         damage_mean=float(a.damage.mean()) if len(a) else np.nan))
    return pd.DataFrame(rows)


def main(names=None):
    la_task_categories()
    CACHE.mkdir(parents=True, exist_ok=True)
    out = []
    for name in names or BUILDERS:
        df = BUILDERS[name]()
        with open(CACHE / f"{name}.pkl", "wb") as f:
            pickle.dump(df, f)
        d = describe(df)
        out.append(d)
        print(f"{name:18s} ctx={df.ctx.nunique():2d} honest={int((df.label == 'honest').sum()):5d} "
              f"attack={int((df.label == 'attack').sum()):5d} min_h/ctx={int(d.n_honest.min())}", flush=True)
    res = ROOT / "results" / "r4_ctx"
    res.mkdir(parents=True, exist_ok=True)
    pd.concat(out).to_csv(res / "panels.csv", index=False, float_format="%.4g")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
