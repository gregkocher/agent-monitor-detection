"""Realized session FPR behind the audit-3 MOLE TPR@5% contrasts (tracks/audit3/wb_mole.py), which report TPR only.

Same sessions, streams and the same 200 account splits (benign sessions of a random half of the benign accounts,
rng seeds 1000+i) as wb_mole; realized FPR = split-mean alarm rate on the benign sessions of the other accounts.
Threshold rule: audit wb_lib plug-in (wthresh / alarm_rate, = the committed audit numbers) vs the conformal
randomized rule (amd.evaluation.calibration.conformal_randomized_threshold).

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.wb_mole_fpr
Output results/fixes2/wb_mole_fpr_thrfix.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from amd.evaluation.calibration import conformal_randomized_threshold
from tracks.audit3.wb_lib import alarm_rate, read_jsonl, wthresh
from tracks.audit3.wb_mole import W4, streams

from .wb_common import OUT_ROOT

ARMS = [("policy", "sab", "max"), ("policy_neutral", "sab", "max"), ("reader", "sab", "max")]


def main(alpha=0.05):
    sel = list(read_jsonl("data/processed/whitebox/inputs/mole_r4_sel.jsonl"))
    meta = {s["task_id"]: s for s in sel}
    arms = {a: {d["task_id"]: streams(d["feats"]) for d in read_jsonl(f"{W4}/r4/mole_{a}.jsonl") if d["n_steps"]}
            for a in ("policy", "policy_neutral", "reader")}
    llm = {p: {d["task_id"]: d["score"] for d in read_jsonl(f"{W4}/r4_mole_llm_{p}.jsonl") if d["score"] is not None}
           for p in ("insider", "generic")}
    ids = sorted(set(meta).intersection(*[set(a) for a in arms.values()], *[set(v) for v in llm.values()]))
    y = np.array([meta[t]["label"] == "attack" for t in ids])
    acct = np.array([meta[t]["account"] for t in ids])
    S = {k: np.array([np.nanmax(arms[k[0]][t][k[1]]) for t in ids]) for k in ARMS}
    S[("llm_insider", "score", "session")] = np.array([llm["insider"][t] for t in ids], float)
    benign_acc = np.unique(acct[~y])
    splits = [np.isin(acct, np.random.default_rng(1000 + i).permutation(benign_acc)[: len(benign_acc) // 2]) & ~y
              for i in range(200)]
    rows = []
    for k, s in S.items():
        for conv in ("plugin", "conformal"):
            f, t, ncal = [], [], []
            for m in splits:
                test = (~y) & ~m
                if conv == "plugin":
                    h, g = wthresh(s[m], np.ones((1, m.sum())), alpha)
                    f.append(alarm_rate(s[test], h, g)[0])
                    t.append(alarm_rate(s[y], h, g)[0])
                else:
                    th = conformal_randomized_threshold(s[m], alpha)
                    f.append(th.rate(s[test]))
                    t.append(th.rate(s[y]))
                ncal.append(m.sum())
            rows.append(dict(arm="/".join(k), conv=conv, alpha=alpha, realized_fpr=float(np.mean(f)),
                             tpr=float(np.mean(t)), n_cal_mean=float(np.mean(ncal))))
            print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(OUT_ROOT / "wb_mole_fpr_thrfix.csv", index=False)


if __name__ == "__main__":
    main()
