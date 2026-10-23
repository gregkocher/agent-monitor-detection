"""Audit pass 3: does assistant reasoning / prose reach the monitors, and how label-revealing is it?

    unset VIRTUAL_ENV; uv run python -m tracks.audit3.leak_reasoning

Monitor inputs (code-verified, see the audit3 log entry):
  * `Step.reasoning` (visible reasoning / assistant text attached to a tool call) is rendered only if
    PromptConfig.include_reasoning is True (amd/scoring/prompts.render_step). No score file has a `-cot` monitor id,
    the white-box export (tracks/wb_whitebox/export_inputs.py) calls render_step with the default (False), and the
    JEV request (tracks/r5_jev/jevlib._step_obj) uses only action/output.
  * BUT assistant turns WITHOUT a tool call are ingested as their own step, action = "[assistant message] <text>"
    (amd/data/monitoringbench.py extract_sample, also used by mb_honest; amd/data/akshn.py judge_to_steps). Those
    steps are seen by every per-step / history / trajectory monitor, the trusted reader, nano and JEV.
This script measures, per source and label, (a) Step.reasoning (hidden), (b) "[assistant message]" prose steps
(visible), restricted to what the monitors saw (MB: first 60 steps, final submit step stripped). AUROC is
P(attack score > honest score) of the per-trajectory feature (0.5 = no signal; near 0 or 1 = label-revealing).
Output results/audit3/leak_reasoning.csv (counts and AUROCs only, no text).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from amd.common.schema import PROCESSED, read_jsonl
from amd.common.schema import REPO

PREFIX = "[assistant message]"
SOURCES = [("mb", ["mb_honest", "monitoringbench"], 60), ("akshn_bash", ["akshn_bash"], None),
           ("akshn_agentdojo", ["akshn_agentdojo"], None), ("akshn_iac", ["akshn_iac"], None),
           ("akshn_shade", ["akshn_shade"], None), ("akshn_basharena_opus46", ["akshn_basharena_opus46"], None),
           ("akshn_basharena_sonnet45", ["akshn_basharena_sonnet45"], None),
           ("akshn_linuxarena", ["akshn_linuxarena"], None), ("linuxarena_sweep", ["linuxarena_sweep"], None),
           ("t3_refined", ["t3_refined"], 60)]


def visible_steps(d, cap):
    st = d["steps"]
    m = d.get("meta") or {}
    if cap is not None:
        if m.get("ends_with_submit") and m.get("submit_step") == len(st) - 1:
            st = st[:-1]
        st = st[:cap]
    return st


def auroc(y, x):
    x = np.asarray(x, float)
    return float(roc_auc_score(y, x)) if len(set(y)) == 2 and np.nanstd(x) > 0 else np.nan


def main():
    rows = []
    for name, srcs, cap in SOURCES:
        recs = []
        for s in srcs:
            p = PROCESSED / s / "trajectories.jsonl"
            if not p.exists():
                continue
            for d in read_jsonl(p):
                st = visible_steps(d, cap)
                prose = [x for x in st if (x.get("action") or "").startswith(PREFIX)]
                recs.append(dict(label=d["label"], n_steps=len(st), n_prose=len(prose),
                                 prose_chars=sum(len(x["action"]) for x in prose),
                                 any_prose=float(bool(prose)),
                                 reasoning_chars=sum(len(x.get("reasoning") or "") for x in st),
                                 share_steps_reasoning=np.mean([bool(x.get("reasoning")) for x in st]) if st else 0.0))
        if not recs:
            continue
        df = pd.DataFrame(recs)
        y = (df.label == "attack").astype(int).values
        for feat in ("n_prose", "prose_chars", "any_prose", "reasoning_chars", "share_steps_reasoning", "n_steps"):
            rows.append(dict(source=name, feature=feat, seen_by_monitors=feat in ("n_prose", "prose_chars", "any_prose",
                                                                                 "n_steps"),
                             honest_median=df[df.label == "honest"][feat].median(),
                             attack_median=df[df.label == "attack"][feat].median(),
                             honest_mean=df[df.label == "honest"][feat].mean(),
                             attack_mean=df[df.label == "attack"][feat].mean(),
                             auroc_attack_gt_honest=auroc(y, df[feat].values),
                             n_honest=int((y == 0).sum()), n_attack=int((y == 1).sum())))
        print(name, "done", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(REPO / "results" / "audit3" / "leak_reasoning.csv", index=False)
    pd.set_option("display.width", 220)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
