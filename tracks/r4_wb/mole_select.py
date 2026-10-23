"""MOLE qwen36_27b_single_day: attack sessions + ACCOUNT-MATCHED benign sessions (metadata-only selection).

For every account-day with k attack sessions, draw k benign sessions of the same account on the same day
(fixed seed); if that day has fewer than k benign sessions, fill from the same account's nearest days.
Each attack session is paired with one matched benign session; `neutral_system` = the paired benign
session's system prompt (the persona prompt without the insider objective), used by the `policy_neutral` arm.

Input: data/raw/r4_wb/mole/data/transcripts/qwen36_27b_single_day/*.parquet (forgelab/mole), labels parquet.
Output: data/processed/whitebox/inputs/mole_r4_sel.jsonl (one session per line, messages as in pod_policy.prep)
        tracks/r4_wb/mole_sel_ids.json (ids + pairing; committed)

    unset VIRTUAL_ENV; uv run python -m tracks.r4_wb.mole_select
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

from amd.common.schema import PROCESSED, REPO

RAW = REPO / "data" / "raw" / "r4_wb" / "mole" / "data"
SPLIT = "qwen36_27b_single_day"
SEED = 20261022
OUT = PROCESSED / "whitebox" / "inputs" / "mole_r4_sel.jsonl"


def convert(messages):
    """Same message conversion as tracks/wb_whitebox/pod_policy.prep."""
    msgs = []
    for m in messages:
        d = {"role": m["role"], "content": m["content"] if m["content"] is not None else ""}
        tc = m.get("tool_calls")
        if tc not in (None, "None", "") and isinstance(tc, str):
            try:
                calls = json.loads(tc)
                d["tool_calls"] = [{"type": "function", "function": {
                    "name": c["function"]["name"],
                    "arguments": json.loads(c["function"]["arguments"]) if isinstance(c["function"]["arguments"], str)
                    else c["function"]["arguments"]}} for c in calls]
            except Exception:  # noqa: BLE001
                pass
        if m["role"] == "tool" and m.get("name") not in (None, "None"):
            d["name"] = m["name"]
        msgs.append(d)
    return msgs


def main():
    rng = np.random.default_rng(SEED)
    meta_cols = ["account", "task_id", "sim_ts", "session_mode", "turn_count"]
    fs = sorted(glob.glob(str(RAW / "transcripts" / SPLIT / "*.parquet")))
    df = pd.concat([pd.read_parquet(f, columns=meta_cols) for f in fs], ignore_index=True)
    df["day"] = df.sim_ts.str[:10]
    lab = pd.read_parquet(RAW / "labels" / SPLIT / "0000.parquet")
    outcome = {(r.account, r.date): r.outcome for r in lab.itertuples()}
    att = df[df.session_mode == "attack"].sort_values(["account", "day", "task_id"])
    ben = df[df.session_mode == "benign"]
    pairs, used = [], set()
    for (acct, day), g in att.groupby(["account", "day"], sort=True):
        pool = ben[(ben.account == acct) & ~ben.task_id.isin(used)].copy()
        pool["dd"] = (pd.to_datetime(pool.day) - pd.Timestamp(day)).abs().dt.days
        pool = pool.assign(r=rng.random(len(pool))).sort_values(["dd", "r"])
        chosen = pool.head(len(g))
        assert len(chosen) == len(g)
        for a_id, b_row in zip(g.task_id, chosen.itertuples()):
            pairs.append(dict(attack=a_id, benign=b_row.task_id, account=acct, day=day, benign_day=b_row.day,
                              same_day=bool(b_row.dd == 0)))
            used.add(b_row.task_id)
    want = {p["attack"] for p in pairs} | {p["benign"] for p in pairs}
    full = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    full = full[full.task_id.isin(want)].set_index("task_id")
    sysmsg = {t: (r.messages[0]["content"] if r.messages[0]["role"] == "system" else "") for t, r in full.iterrows()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        for p in pairs:
            for kind in ("attack", "benign"):
                t = p[kind]
                r = full.loc[t]
                day = str(r.sim_ts)[:10]
                f.write(json.dumps({"task_id": t, "account": r.account, "day": day,
                                    "label": "attack" if kind == "attack" else "honest",
                                    "pair": p["attack"], "outcome": outcome.get((r.account, day)),
                                    "neutral_system": sysmsg[p["benign"]],
                                    "messages": convert(list(r.messages))}) + "\n")
    Path("tracks/r4_wb/mole_sel_ids.json").write_text(json.dumps({"seed": SEED, "pairs": pairs}, indent=1))
    pdf = pd.DataFrame(pairs)
    print(len(pairs), "pairs; same-day", int(pdf.same_day.sum()), "accounts", pdf.account.nunique())


if __name__ == "__main__":
    main()
