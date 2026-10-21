"""Inspect cached persistent-state scores for a model (pilot or full): coverage, logprob share, cost, mean
score per policy x PR, per-PR AUROC (attack PR vs honest PR) for each history mode.

    uv run python tracks/r2_t1/ps_inspect.py --model openai/gpt-4.1-mini [--no-logprobs] [--reasoning-off] [--require-params]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from llmcache import PromptCache, prompt_key  # noqa: E402
from ps_score import CACHE, MAX_TOKENS, PROMPT_ID, build_messages, load_runs  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--no-logprobs", action="store_true")
    ap.add_argument("--reasoning-off", action="store_true")
    a = ap.parse_args()
    sig = PROMPT_ID + ("|nolp" if a.no_logprobs else "") + ("|reasoff" if a.reasoning_off else "")
    cache = PromptCache(CACHE)
    rows = []
    for r in load_runs():
        t = r["traj"]
        for mode in ("current_only", "full_diffs"):
            for i in range(5):
                m = build_messages(r["prs"], i, mode)
                if m is None:
                    continue
                rec = cache.get(prompt_key(a.model, m, MAX_TOKENS, sig))
                if rec is None:
                    continue
                rows.append(dict(run=t.traj_id, policy=t.context["policy"], mode=mode, pr=i,
                                 tpos=t.context.get("target_position"), score=rec["expected"] if rec["lp_ok"]
                                 else rec["int_score"], int_score=rec["int_score"], lp=rec["lp_ok"],
                                 cost=rec["cost"], in_tok=rec["in_tok"], cached=rec.get("cached_tok") or 0,
                                 out_tok=rec["out_tok"]))
    D = pd.DataFrame(rows)
    if D.empty:
        print("nothing cached"); return
    print(f"{len(D)} cached PR scores; logprob share {D.lp.mean():.2f}; cost ${D.cost.sum():.2f}; "
          f"mean in_tok {D.in_tok.mean():.0f}, cached share {D.cached.sum() / max(D.in_tok.sum(), 1):.2f}, "
          f"out_tok {D.out_tok.mean():.0f}")
    print(D.pivot_table(index=["mode", "policy"], columns="pr", values="score", aggfunc="mean").round(2))
    print(D.groupby(["mode", "policy"]).int_score.value_counts().unstack(fill_value=0))
    from sklearn.metrics import roc_auc_score
    for mode, g in D.groupby("mode"):
        mx = g.groupby(["run", "policy"]).score.max().reset_index()
        for pol in ("gradual", "positional"):
            s = mx[mx.policy.isin(["honest", pol])]
            if s.policy.nunique() == 2:
                print(mode, pol, "run-max AUROC", round(roc_auc_score(s.policy == pol, s.score), 3), "n", len(s))


if __name__ == "__main__":
    main()
