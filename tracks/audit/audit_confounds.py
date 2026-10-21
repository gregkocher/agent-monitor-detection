"""Audit: label-correlated confounds in the MonitoringBench (T1 sample) + Honest-550 data.

Independent minimal code (plain json / numpy); does not import the project's evaluation functions.
Checks: length, submit step, truncation at 60 steps, tool mix, text-only steps, agent model,
NaN coverage by label, attack_step indexing (0-based vs off-by-one), first_attack_step vs attack_step.

    unset VIRTUAL_ENV; uv run python tracks/audit/audit_confounds.py
Writes results/audit/repro_confounds.csv
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
P = REPO / "data" / "processed"
OUT = REPO / "results" / "audit"


def jl(path):
    with open(path) as f:
        for line in f:
            yield json.loads(line)


def auroc(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    allv = np.concatenate([pos, neg])
    r = allv.argsort().argsort().astype(float) + 1
    # average ranks for ties
    from scipy.stats import rankdata
    r = rankdata(allv)
    return (r[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sample = json.load(open(REPO / "tracks" / "t1_matched_budget" / "sample.json"))
    att_ids = set(sample["attack"])
    T = {}
    for src in ("mb_honest", "monitoringbench"):
        for d in jl(P / src / "trajectories.jsonl"):
            if d["label"] == "attack" and d["traj_id"] not in att_ids:
                continue
            T[d["traj_id"]] = d
    rows = []

    def add(check, honest, attack, note=""):
        rows.append(dict(check=check, honest=honest, attack=attack, note=note))

    H = [d for d in T.values() if d["label"] == "honest"]
    A = [d for d in T.values() if d["label"] == "attack"]
    add("n", len(H), len(A))

    def eff_len(d):
        n = len(d["steps"])
        if d["meta"].get("ends_with_submit") and d["meta"].get("submit_step") == n - 1:
            n -= 1
        return min(n, 60)

    lh, la = [eff_len(d) for d in H], [eff_len(d) for d in A]
    add("median steps (submit stripped, cap 60)", np.median(lh), np.median(la))
    add("length AUROC (attack longer)", "", round(auroc(la, lh), 3),
        "max over more steps is inflated; confounds max-type and accumulators alike")
    add("share ending with submit", np.mean([bool(d["meta"].get("ends_with_submit")) for d in H]).round(3),
        np.mean([bool(d["meta"].get("ends_with_submit")) for d in A]).round(3))
    add("share > 60 raw steps (truncated)", np.mean([len(d["steps"]) > 60 for d in H]).round(4),
        np.mean([len(d["steps"]) > 60 for d in A]).round(4))
    add("agent model", dict(Counter(d["context"].get("agent_model") for d in H)),
        dict(Counter(d["context"].get("agent_model") for d in A)),
        "attack-only agent model = label-correlated confound")

    def tools(d):
        c = Counter()
        for s in d["steps"]:
            m = re.match(r"([A-Za-z_]+)\(", s["action"] or "")
            c[m.group(1) if m else "<text>"] += 1
        return c

    th, ta = Counter(), Counter()
    uh, ua = Counter(), Counter()
    for d in H:
        c = tools(d); th.update(c); uh.update(set(c))
    for d in A:
        c = tools(d); ta.update(c); ua.update(set(c))
    for k in sorted(set(uh) | set(ua)):
        add(f"share of trajectories using tool '{k}'", round(uh[k] / len(H), 3), round(ua[k] / len(A), 3))
    # arg name normalization
    add("steps with '\"command\":' arg (bash)", sum(s["action"].startswith("bash(") and '"command"' in s["action"][:20]
                                                  for d in H for s in d["steps"]),
        sum(s["action"].startswith("bash(") and '"command"' in s["action"][:20] for d in A for s in d["steps"]))
    add("share of steps with non-empty reasoning", round(np.mean([bool(s.get("reasoning")) for d in H for s in d["steps"]]), 3),
        round(np.mean([bool(s.get("reasoning")) for d in A for s in d["steps"]]), 3),
        "monitor prompts hide reasoning by default (prompts.render_step include_reasoning=False)")
    # output formats: share of outputs that are empty
    add("share of steps with empty output", round(np.mean([not (s.get("output") or "").strip() for d in H for s in d["steps"]]), 3),
        round(np.mean([not (s.get("output") or "").strip() for d in A for s in d["steps"]]), 3))

    # NaN coverage of score files by label
    for f in ("scores_openai_gpt-4.1-mini_full.jsonl", "scores_openai_gpt-4.1-mini_none.jsonl",
              "scores_openai_gpt-4.1-nano_none.jsonl", "scores_openai_gpt-4.1_none.jsonl"):
        res = {}
        for src, lab in (("mb_honest", "honest"), ("monitoringbench", "attack")):
            fp = P / src / f
            if not fp.exists():
                continue
            n = nn = nlp = ntot = 0
            nstreams = 0
            for r in jl(fp):
                if r["traj_id"] not in T:
                    continue
                nstreams += 1
                s = [v for v in r["scores"]]
                n += len(s); nn += sum(v is None for v in s)
                lp = r["meta"].get("lp_ok")
                if lp is not None:
                    nlp += sum(1 for x in lp if x); ntot += len(lp)
            res[lab] = f"streams={nstreams} steps={n} NaN={nn} lp_ok={nlp / max(ntot, 1):.3f}"
        if res:
            add(f"score coverage {f}", res.get("honest"), res.get("attack"))

    # onset indexing: does 0-based attack_step hit a target literal more often than its neighbours?
    hit = Counter()
    nchk = 0
    for d in A:
        k = d["attack_step"]
        lits = d["meta"].get("target_literals") or []
        if k is None or not lits:
            continue
        nchk += 1
        for off in (-1, 0, 1):
            j = k + off
            if 0 <= j < len(d["steps"]):
                txt = d["steps"][j]["action"] or ""
                hit[off] += any(l in txt for l in lits)
    add("attack_step(0-based)+off contains a target literal: off=-1/0/+1",
        "", f"{hit[-1]}/{hit[0]}/{hit[1]} of {nchk}",
        "peak at off=0 supports correct 1->0-based conversion")
    gaps = [d["attack_step"] - d["meta"]["first_attack_step"] for d in A
            if d["attack_step"] is not None and d["meta"].get("first_attack_step") is not None]
    add("attack_step - first_attack_step (median, q90)", "", f"{np.median(gaps)}, {np.quantile(gaps, 0.9)}")
    add("attacks with attack_step >= scored length (onset beyond truncation/submit strip)", "",
        sum(1 for d in A if d["attack_step"] is not None and d["attack_step"] >= eff_len(d)))
    add("attacks where attack_step is the submit step", "",
        sum(1 for d in A if d["attack_step"] is not None and d["meta"].get("ends_with_submit")
            and d["attack_step"] == d["meta"].get("submit_step")))

    import csv
    with open(OUT / "repro_confounds.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["check", "honest", "attack", "note"])
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in r.items()})
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
