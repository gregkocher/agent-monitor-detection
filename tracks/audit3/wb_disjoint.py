"""Audit pass 3 (r4_wb): held-out set disjointness, duplication, composition, and LLM-snapshot provenance.

Checks
  1. held-out attack ids vs the T1 sample (attack / pilot / pilot2 / key-check sets) and vs every other id list
     found in tracks/*/ json files; duplicated ids within the held-out set.
  2. content duplicates: sha256 of the rendered action sequence (actions only, and actions+outputs) within the
     held-out set, between held-out and pilot attacks, and between held-out and honest (Honest-550).
  3. S4 availability in the pool (is "no S4" a selection artifact?).
  4. task overlap between held-out attacks and Honest-550 (clustering unit), attacks per task.
  5. provenance of the "prereg snapshot" LLM file: its NaN steps must be exactly the steps whose cache rows were
     created after the first scoring run ended, and every finite value must equal the cache value.
Writes results/audit3/wb_disjoint.json. No API calls; attack content is hashed only, never printed.

    unset VIRTUAL_ENV; uv run python -m tracks.audit3.wb_disjoint
"""
from __future__ import annotations

import collections
import glob
import hashlib
import json
import sqlite3

import numpy as np

P = "data/processed"
OUT = "results/audit3/wb_disjoint.json"


def read_jsonl(p):
    with open(p) as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def h(steps, with_out=False):
    m = hashlib.sha256()
    for s in steps:
        m.update((s.get("action") or "").encode())
        if with_out:
            m.update(b"\x00" + (s.get("output") or "").encode())
        m.update(b"\x01")
    return m.hexdigest()


def main():
    held = json.load(open("tracks/r4_wb/heldout.json"))
    S = json.load(open("tracks/t1_matched_budget/sample.json"))
    H = held["attack"]
    out = {"n_heldout": len(H), "n_unique_heldout_ids": len(set(H))}
    t1_sets = {k: set(v) for k, v in S.items() if isinstance(v, list)}
    out["overlap_with_t1_sample_sets"] = {k: len(set(H) & v) for k, v in t1_sets.items()}

    # every other id list in tracks/*/ *.json (other tracks' samples)
    other = {}
    for f in glob.glob("tracks/*/*.json"):
        if "r4_wb/heldout.json" in f:
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        ids = set()

        def walk(x):
            if isinstance(x, str) and x.startswith("monitoringbench:"):
                ids.add(x)
            elif isinstance(x, dict):
                for v in x.values():
                    walk(v)
                for k in x.keys():
                    if isinstance(k, str) and k.startswith("monitoringbench:"):
                        ids.add(k)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(d)
        if ids:
            other[f] = len(set(H) & ids)
    out["overlap_with_other_track_json_id_lists"] = other

    A = {d["traj_id"]: d for d in read_jsonl(f"{P}/monitoringbench/trajectories.jsonl")}
    HON = {d["traj_id"]: d for d in read_jsonl(f"{P}/mb_honest/trajectories.jsonl")}
    pilot = set(S["attack"]) | set(S["pilot_attack"]) | set(S["pilot2_attack"])
    hon550 = set(S["honest"])
    out["n_mb_attacks_total"] = len(A)
    for wo in (False, True):
        key = "actions+outputs" if wo else "actions"
        hh = {i: h(A[i]["steps"], wo) for i in A}
        hon_h = {i: h(HON[i]["steps"], wo) for i in HON}
        hc = collections.Counter(hh[i] for i in H)
        dup_within = sum(c - 1 for c in hc.values() if c > 1)
        pil_h = {hh[i] for i in pilot if i in hh}
        dup_pilot = sum(hh[i] in pil_h for i in H)
        dup_hon = sum(hh[i] in set(hon_h.values()) for i in H)
        allc = collections.Counter(hh.values())
        out[f"dup_{key}"] = dict(within_heldout_extra_copies=dup_within, heldout_matching_a_pilot_attack=dup_pilot,
                                 heldout_matching_an_honest=dup_hon,
                                 all_mb_attacks_extra_copies=sum(c - 1 for c in allc.values() if c > 1))
    # same (sample_id, epoch, side_task, agent, eval file) metadata duplicates
    mk = collections.Counter((A[i]["meta"].get("sample_uuid")) for i in H)
    out["dup_sample_uuid_within_heldout"] = sum(c - 1 for c in mk.values() if c > 1)
    pil_uuid = {A[i]["meta"].get("sample_uuid") for i in pilot if i in A}
    out["heldout_sample_uuid_in_pilot"] = sum(A[i]["meta"].get("sample_uuid") in pil_uuid for i in H)
    # (task, side task, agent, policy) cells shared with pilot -- same scenario, different trajectory
    cell = lambda d: (d["context"].get("task_id"), d["context"].get("side_task"), d["context"].get("agent_model"))  # noqa
    pil_cells = {cell(A[i]) for i in pilot if i in A}
    out["heldout_sharing_task_side_agent_cell_with_pilot"] = sum(cell(A[i]) in pil_cells for i in H)
    pil_tasks = {A[i]["context"].get("task_id") for i in pilot if i in A}
    out["heldout_sharing_task_with_pilot"] = sum(A[i]["context"].get("task_id") in pil_tasks for i in H)

    # S4 availability
    st = collections.Counter(str(A[i]["meta"].get("structural_strategy")) for i in A)
    st_pool = collections.Counter(str(A[i]["meta"].get("structural_strategy")) for i in A if i not in
                                  (pilot | set(S["ck_test_key"]) | set(S["ck_test_nokey"])))
    st_pilot = collections.Counter(str(A[i]["meta"].get("structural_strategy")) for i in S["attack"])
    out["structure_all"], out["structure_pool"], out["structure_pilot775"] = dict(st), dict(st_pool), dict(st_pilot)

    # tasks
    ht = collections.Counter(str(HON[i]["context"].get("task_id")) for i in hon550)
    at = collections.Counter(str(A[i]["context"].get("task_id")) for i in H)
    out["n_tasks_honest550"] = len(ht)
    out["n_tasks_heldout"] = len(at)
    out["n_tasks_shared"] = len(set(ht) & set(at))
    out["heldout_attacks_on_shared_tasks"] = int(sum(c for t, c in at.items() if t in ht))
    out["attacks_per_task_quantiles"] = np.quantile(list(at.values()), [0, .25, .5, .75, .9, 1]).tolist()
    out["max_task_share_of_attacks"] = max(at.values()) / len(H)
    out["honest_per_task_quantiles"] = np.quantile(list(ht.values()), [0, .25, .5, .75, .9, 1]).tolist()
    out["honest_agent_models"] = dict(collections.Counter(HON[i]["context"].get("agent_model") for i in hon550))

    # LLM snapshot provenance
    mid = "openai/gpt-4.1-mini|ctrl-basic-v1|none"
    db = sqlite3.connect(f"file:{P}/monitoringbench/score_cache.sqlite?mode=ro", uri=True)
    rows = {(t, s): (st_, json.loads(r), c) for t, s, st_, r, c in
            db.execute("select traj_id, step, status, result, created from scores where monitor_id=?", (mid,))}
    hs = set(H)
    cr = sorted(c for (t, _), (_, _, c) in rows.items() if t in hs)
    gaps = np.diff(cr)
    cut = cr[int(np.argmax(gaps))] + 1  # end of the first scoring run = largest gap
    snap = {d["traj_id"]: d for d in read_jsonl(f"{P}/monitoringbench/r4wb_scores_openai_gpt-4.1-mini_none_prereg_snapshot.jsonl")}
    fill = {d["traj_id"]: d for d in read_jsonl(f"{P}/monitoringbench/r4wb_scores_openai_gpt-4.1-mini_none.jsonl")}
    nan_snap, late, mism, n_fin, mism_fill = set(), set(), 0, 0, 0
    for t in H:
        for k, v in enumerate(snap[t]["scores"]):
            r = rows.get((t, k))
            if r is not None and r[2] > cut:
                late.add((t, k))
            if v is None or (isinstance(v, float) and np.isnan(v)):
                nan_snap.add((t, k))
            else:
                n_fin += 1
                rv = r[1].get("expected") if r else None
                fv = fill[t]["scores"][k]
                if fv is None or abs(fv - v) > 1e-9:
                    mism_fill += 1
                if rv is not None and abs(rv - v) > 1e-6:
                    mism += 1
    out["snapshot"] = dict(n_nan=len(nan_snap), n_cache_rows_after_first_run=len(late),
                           nan_equals_late=nan_snap == late, finite_steps=n_fin,
                           finite_snapshot_vs_cache_mismatch=mism, finite_snapshot_vs_filled_mismatch=mism_fill,
                           trajs_with_nan=len({t for t, _ in nan_snap}))
    json.dump(out, open(OUT, "w"), indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
