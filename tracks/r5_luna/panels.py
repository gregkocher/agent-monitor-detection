"""Panels for the r5luna analysis: the round-1 panels (tracks/r5_jev/panels.py, unchanged) plus the new streams.

Added streams (aligned exactly like round-1 `jev`: MonitoringBench first 60 steps with the submit step stripped;
aksh-n all steps; NaN where missing):
  luna       GPT-6 Luna Decisions on the frozen request (P(suspicious), scheme bs)
  luna_full  Luna Decisions, full untruncated current action (opus-4-6 evaluation set, LinuxArena nano subset)
  jev_full   JEV with the same full-action request (truncated steps re-scored; other steps = round-1 JEV)
  gen        generative GPT-6 Luna, ctrl-basic-v1 window W=3, integer score (H5c subset only)
"""
from __future__ import annotations

import json

import numpy as np

from amd.common.schema import PROCESSED, read_jsonl
from tracks.r5_jev import jevlib as J
from tracks.r5_jev import panels as PN
from tracks.r5_jev.panels import _fit, _strip
from tracks.r5_jev.score_jev import load
from tracks.r5_jev.splits import HERE

from . import lunalib as L
from .score_gen import SUBSET_FILE, load_gen

VARIANT, SCHEME = L.VARIANT, L.SCHEME


def _add(P, name, per_traj: dict, T: dict, strip: bool):
    arrs, miss, nan = [], 0, 0
    for j, t in enumerate(P.hid + P.aid):
        n = len(P.streams[P.second][j])
        s = per_traj.get(t)
        if s is None:
            arrs.append(np.full(n, np.nan))
            miss += 1
            continue
        s = np.asarray(s, float)
        if strip:
            s = _strip(T[t], s)
        miss += len(s) != n
        a = _fit(s, n)
        nan += int(np.isnan(a).sum())
        arrs.append(a)
    P.streams[name] = arrs
    P.meta.setdefault("added", {})[name] = dict(traj_missing_or_len_mismatch=miss, nan_steps=nan)


def full_stream(model: str, src: str, trajs: list, frozen: dict) -> tuple[dict, dict]:
    """Full-action stream: frozen value where the full request equals the frozen one, else the full-mode answer."""
    full = L.load_full(src)
    cache = L.cache_for(model, src)
    mid = L.monitor_id(model, "full")
    out, n_diff, n_miss = {}, 0, 0
    for t in trajs:
        v = np.array(frozen[t.traj_id], float).copy()
        for k in range(len(t.steps)):
            fr = L.frozen_request(t, k)
            if full[t.traj_id].steps[k].action == t.steps[k].action:
                continue
            fu = L.full_request(t, full[t.traj_id], k)
            s_fu = J.request_sha(fu)
            if s_fu == J.request_sha(fr):
                continue
            n_diff += 1
            c = cache.get(t.traj_id, k, mid)
            if c is not None and c[1].get("sha") == s_fu:
                v[k] = L.p_susp(c[1])
            else:
                v[k] = np.nan
                n_miss += 1
        out[t.traj_id] = v
    cache.close()
    return out, dict(n_diff_steps=n_diff, n_missing=n_miss)


def h5c_ids(src):
    sub = json.load(open(SUBSET_FILE))["sources"].get(src)
    return set(sub["honest"]) | set(sub["attack"]) if sub else set()


def load_mb():
    spl = json.load(open(HERE / "splits.json"))["sources"]["mb"]
    P = PN.load_mb(VARIANT, SCHEME, probe=False)
    T = {t.traj_id: t for t in load("mb", set(P.hid) | set(P.aid))}
    luna, info = L.load_scores("luna", "mb", list(T.values()), L.MB_MAX_STEPS)
    _add(P, "luna", luna, T, strip=True)
    hc = h5c_ids("mb")
    gen = load_gen("mb", [T[t] for t in sorted(hc) if t in T], L.MB_MAX_STEPS)
    _add(P, "gen", gen, T, strip=True)
    P.meta["luna_info"] = info
    P.meta["main_task_h"], P.meta["main_task_a"] = P.hg, P.ag
    assert len(spl["eval_honest"]) >= P.nh
    return P


def load_akshn(src):
    P = PN.load_akshn(src, VARIANT, SCHEME)
    T = {t.traj_id: t for t in load(src, set(P.hid) | set(P.aid))}
    luna, info = L.load_scores("luna", src, list(T.values()))
    _add(P, "luna", luna, T, strip=False)
    P.meta["luna_info"] = info
    if src in ("akshn_basharena_opus46", "akshn_linuxarena"):
        spl = json.load(open(HERE / "splits.json"))["sources"][src]
        ids = (set(P.hid) | set(P.aid)) if src == "akshn_basharena_opus46" else \
            (set(spl["nano_honest"]) | set(spl["nano_attack"]))
        sub = [T[t] for t in sorted(ids) if t in T]
        lf, i1 = full_stream("luna", src, sub, luna)
        _add(P, "luna_full", lf, T, strip=False)
        jev_frozen, _ = PN.jev_scores(src, sub, VARIANT, SCHEME)
        jf, i2 = full_stream("jev", src, sub, jev_frozen)
        _add(P, "jev_full", jf, T, strip=False)
        P.meta["full_info"] = dict(luna=i1, jev=i2)
        hc = h5c_ids(src)
        gen = load_gen(src, [T[t] for t in sorted(hc) if t in T])
        _add(P, "gen", gen, T, strip=False)
    mt = {t: str(T[t].context.get("main_task")) for t in T}
    P.meta["main_task_h"] = np.array([mt[t] for t in P.hid])
    P.meta["main_task_a"] = np.array([mt[t] for t in P.aid])
    return P


def subset(P, keep):
    """PN.subset that also carries the main-task arrays."""
    Q = PN.subset(P, keep, name=P.name)
    hk = [j for j, t in enumerate(P.hid) if t in keep]
    ak = [j for j, t in enumerate(P.aid) if t in keep]
    Q.meta["main_task_h"] = P.meta["main_task_h"][hk]
    Q.meta["main_task_a"] = P.meta["main_task_a"][ak]
    return Q


def truncation_share(src, ids):
    """Share of steps whose action was truncated at ingest (for the H5d description)."""
    n = k = 0
    for d in read_jsonl(PROCESSED / src / "trajectories.jsonl"):
        if d["traj_id"] in ids:
            for s in d["steps"]:
                n += 1
                k += "chars]..." in s["action"] and "...[truncated" in s["action"]
    return k / max(n, 1)
