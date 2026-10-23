"""Build aligned per-step panels (evaluation split only) for the r5jev analyses.

Streams per trajectory, all aligned to the second-stage steps:
  MonitoringBench (`mb`): llm = gpt-4.1-mini `none` (ctrl-basic-v1, logprob-expected), first 60 steps, final submit
      step stripped (as T1 / r4_wb); jev; nano = gpt-4.1-nano `none` (same prompt); probe = FIBS axial follow-up
      (`fibs_fu_ax`, trusted reader, none mode; honest + r4 attacks from the round-4 pod, T1-sample attacks from the
      pilot pod); len = characters of the action; plus `llm_full` (gpt-4.1-mini full history, T1 sample only).
  aksh-n settings: llm = Gemini-3.1-Pro local per-step suspicion (`akshn_local`, step unit); jev; nano (subset only);
      len. All steps.
  linuxarena_sweep (secondary): one stream per sweep monitor (`la:<model>`); hidden-tool steps removed.
Common reference first stages added for every panel: rand (seeded uniform), oracle (= the second-stage score), and
oracle_label (attack steps at/after onset ranked first; everything else random).
Missing steps are NaN (a NaN first stage is always escalated; a NaN second stage contributes nothing).
"""
from __future__ import annotations

import glob
import json
import math

import numpy as np

from amd.common.schema import PROCESSED, Trajectory, read_jsonl

from . import jevlib as J
from .cascade import Panel
from .splits import AKSHN, HERE

WB = PROCESSED / "whitebox" / "scores"
GEMINI = "gemini-3.1-pro|akshn_local|full"


def _arr(v):
    return np.array([np.nan if x is None else x for x in v], float)


def _strip(t: Trajectory, s: np.ndarray) -> np.ndarray:
    if t.meta.get("ends_with_submit") and t.meta.get("submit_step") == len(t.steps) - 1 \
            and t.meta["submit_step"] < len(s):
        return s[: t.meta["submit_step"]]
    return s


def _fit(a, n):
    a = np.asarray(a, float)[:n]
    return np.r_[a, np.full(n - len(a), np.nan)] if len(a) < n else a


def jev_scores(src, trajs, variant, scheme, max_steps=None):
    recs = J.load_records(src, trajs, variant, max_steps)
    sc = {t: np.array([J.step_score(r, scheme) for r in v], float) for t, v in recs.items()}
    cost = [r.get("cost", 0.0) for v in recs.values() for r in v if r]
    return sc, float(np.mean(cost)) if cost else math.nan


def _llm_file(path):
    return {d["traj_id"]: (_arr(d["scores"]), d.get("meta", {}).get("cost_usd")) for d in read_jsonl(path)} \
        if path.exists() else {}


def _probe(paths, stream="fibs_fu_ax"):
    from tracks.wb_whitebox.wblib import derived
    out = {}
    for p in paths:
        for d in read_jsonl(p):
            if d["n_steps"]:
                out[d["traj_id"]] = np.asarray(derived(d["feats"])[stream], float)
    return out


def _refs(P: Panel, onsets, seed=0):
    rng = np.random.default_rng(seed)
    second = P.streams[P.second]
    P.streams["rand"] = [rng.random(len(a)) for a in second]
    P.streams["oracle"] = [np.where(np.isfinite(a), a, -np.inf) for a in second]
    lab = []
    for j, a in enumerate(second):
        u = rng.random(len(a))
        if j >= P.nh:
            o = onsets[j - P.nh] or 0
            u[o:] += 1.0
        lab.append(u)
    P.streams["oracle_label"] = lab


def load_mb(variant, scheme, probe=True):
    spl = json.load(open(HERE / "splits.json"))["sources"]["mb"]
    TH = {d["traj_id"]: Trajectory(**d) for d in read_jsonl(PROCESSED / "mb_honest" / "trajectories.jsonl")
          if d["traj_id"] in set(spl["eval_honest"])}
    TA = {d["traj_id"]: Trajectory(**d) for d in read_jsonl(PROCESSED / "monitoringbench" / "trajectories.jsonl")
          if d["traj_id"] in set(spl["eval_attack"])}
    llm_h = _llm_file(PROCESSED / "mb_honest" / "scores_openai_gpt-4.1-mini_none.jsonl")
    llm_a = {**_llm_file(PROCESSED / "monitoringbench" / "r4wb_scores_openai_gpt-4.1-mini_none.jsonl"),
             **_llm_file(PROCESSED / "monitoringbench" / "scores_openai_gpt-4.1-mini_none.jsonl")}
    full_h = _llm_file(PROCESSED / "mb_honest" / "scores_openai_gpt-4.1-mini_full.jsonl")
    full_a = _llm_file(PROCESSED / "monitoringbench" / "scores_openai_gpt-4.1-mini_full.jsonl")
    nano = {**_llm_file(PROCESSED / "mb_honest" / "r5_scores_openai_gpt-4.1-nano_none.jsonl"),
            **_llm_file(PROCESSED / "monitoringbench" / "r5_scores_openai_gpt-4.1-nano_none.jsonl")}
    jh, c1 = jev_scores("mb", list(TH.values()), variant, scheme, 60)
    ja, c2 = jev_scores("mb", list(TA.values()), variant, scheme, 60)
    jev = {**jh, **ja}
    pr = {}
    if probe:
        pilot = _probe([WB / "mb_none.jsonl"])
        r4 = _probe(sorted(glob.glob(str(WB / "r4" / "mbr4_none_s*.jsonl"))))
        pr = {**{t: v for t, v in pilot.items() if t.startswith("monitoringbench:")}, **r4}
    T = {**TH, **TA}
    hid = sorted(t for t in TH if t in llm_h and np.isfinite(llm_h[t][0]).any())
    aid = sorted(t for t in TA if t in llm_a and np.isfinite(llm_a[t][0]).any())
    streams = {k: [] for k in ["llm", "jev", "nano", "probe", "len", "llm_full"]}
    mism = {k: 0 for k in streams}
    for t in hid + aid:
        tr = T[t]
        L = _strip(tr, (llm_h if t in TH else llm_a)[t][0])
        n = len(L)
        streams["llm"].append(L)
        for k, src in [("jev", jev.get(t)), ("nano", (nano.get(t) or (None,))[0]), ("probe", pr.get(t)),
                       ("llm_full", ((full_h if t in TH else full_a).get(t) or (None,))[0])]:
            if src is None:
                streams[k].append(np.full(n, np.nan))
                mism[k] += 1
                continue
            a = src if k == "probe" else _strip(tr, np.asarray(src, float))
            if len(a) != n:
                mism[k] += 1
            streams[k].append(_fit(a, n))
        streams["len"].append(np.array([len(s.action) for s in tr.steps[:n]], float))
    P = Panel("mb", hid, aid, np.array([str(T[t].context.get("main_task")) for t in hid]),
              np.array([str(T[t].context.get("main_task")) for t in aid]), streams, "llm",
              attack_onset=[T[t].attack_step for t in aid],
              meta=dict(mismatch=mism, jev_cost_step=np.nanmean([c1, c2]),
                        side=[T[t].context.get("side_task_group") for t in aid],
                        struct=[str(T[t].meta.get("structural_strategy")) for t in aid],
                        agent=[T[t].context.get("agent_model") for t in aid],
                        t1_sample=[t in full_a for t in aid],
                        llm_cost_step=_cost_per_step(llm_h, llm_a, hid, aid),
                        nano_cost_step=_cost_per_step(nano, nano, hid, aid)))
    _refs(P, P.attack_onset)
    return P


def _cost_per_step(dh, da, hid, aid):
    c, n = 0.0, 0
    for t in hid + aid:
        d = dh.get(t) or da.get(t)
        if d and d[1] is not None:
            c += d[1]
            n += len(d[0])
    return c / n if n else math.nan


def load_akshn(src, variant, scheme):
    spl = json.load(open(HERE / "splits.json"))["sources"][src]
    ev = set(spl["eval_honest"]) | set(spl["eval_attack"])
    T = {d["traj_id"]: Trajectory(**d) for d in read_jsonl(PROCESSED / src / "trajectories.jsonl")
         if d["traj_id"] in ev}
    gem = {d["traj_id"]: _arr(d["scores"]) for d in read_jsonl(PROCESSED / src / "scores.jsonl")
           if d["monitor_id"] == GEMINI and d["unit"] == "step" and d["traj_id"] in ev}
    nano = _llm_file(PROCESSED / src / "r5_scores_openai_gpt-4.1-nano_none.jsonl")
    jev, cj = jev_scores(src, list(T.values()), variant, scheme)
    hid = sorted(t for t in spl["eval_honest"] if t in gem)
    aid = sorted(t for t in spl["eval_attack"] if t in gem)
    streams = {k: [] for k in ["llm", "jev", "nano", "len"]}
    mism = {k: 0 for k in streams}
    for t in hid + aid:
        L = gem[t]
        n = len(L)
        streams["llm"].append(L)
        for k, s in [("jev", jev.get(t)), ("nano", (nano.get(t) or (None,))[0])]:
            if s is None:
                streams[k].append(np.full(n, np.nan))
                mism[k] += 1
            else:
                mism[k] += len(s) != n
                streams[k].append(_fit(s, n))
        streams["len"].append(np.array([len(s.action) for s in T[t].steps[:n]], float))
    g = spl["group_of"]
    P = Panel(src, hid, aid, np.array([g[t] for t in hid]), np.array([g[t] for t in aid]), streams, "llm",
              attack_onset=[T[t].attack_step for t in aid],
              meta=dict(mismatch=mism, jev_cost_step=cj, side=[T[t].context.get("side_task") for t in aid],
                        nano_ids=set(spl.get("nano_honest", [])) | set(spl.get("nano_attack", [])),
                        nano_cost_step=_cost_per_step(nano, nano, hid, aid)))
    _refs(P, P.attack_onset)
    return P


def subset(P: Panel, keep_ids: set, name=None) -> Panel:
    hk = [j for j, t in enumerate(P.hid) if t in keep_ids]
    ak = [j for j, t in enumerate(P.aid) if t in keep_ids]
    rows = hk + [P.nh + j for j in ak]
    Q = Panel(name or P.name, [P.hid[j] for j in hk], [P.aid[j] for j in ak], P.hg[hk], P.ag[ak],
              {k: [v[r] for r in rows] for k, v in P.streams.items()}, P.second,
              attack_onset=[P.attack_onset[j] for j in ak],
              meta={k: ([v[j] for j in ak] if isinstance(v, list) and len(v) == len(P.aid) else v)
                    for k, v in P.meta.items()})
    return Q


def attack_subset(P: Panel, mask) -> Panel:
    keep = set(P.hid) | {t for t, m in zip(P.aid, mask) if m}
    return subset(P, keep)


def load_la_sweep(variant, scheme, monitors=None):
    spl = json.load(open(HERE / "splits.json"))["sources"]["linuxarena_sweep"]
    T = {d["traj_id"]: Trajectory(**d) for d in read_jsonl(PROCESSED / "linuxarena_sweep" / "trajectories.jsonl")}
    S = {}
    for d in read_jsonl(PROCESSED / "linuxarena_sweep" / "scores.jsonl"):
        if d["unit"] == "step":
            S.setdefault(d["monitor_id"].split("|")[0], {})[d["traj_id"]] = _arr(d["scores"])
    monitors = monitors or sorted(m for m in S if len(S[m]) >= 330)
    jev, cj = jev_scores("linuxarena_sweep", list(T.values()), variant, scheme)
    ids = [t for t in spl["eval_honest"] + spl["eval_attack"] if all(t in S[m] for m in monitors)]
    hid = [t for t in ids if T[t].label == "honest"]
    aid = [t for t in ids if T[t].label == "attack"]
    streams = {f"la:{m}": [] for m in monitors}
    streams.update(jev=[], len=[])
    for t in hid + aid:
        hidden = set(T[t].meta.get("hidden_tool_steps") or [])
        keep = np.array([k for k in range(len(T[t].steps)) if k not in hidden], int)
        for m in monitors:
            streams[f"la:{m}"].append(_fit(S[m][t], len(T[t].steps))[keep])
        streams["jev"].append(_fit(jev[t], len(T[t].steps))[keep])
        streams["len"].append(np.array([len(T[t].steps[k].action) for k in keep], float))
    P = Panel("linuxarena_sweep", hid, aid, np.array([f"task:{T[t].context.get('main_task')}" for t in hid]),
              np.array([f"task:{T[t].context.get('main_task')}" for t in aid]), streams, f"la:{monitors[0]}",
              attack_onset=[None for _ in aid], meta=dict(monitors=monitors, jev_cost_step=cj))
    _refs(P, P.attack_onset)
    return P
