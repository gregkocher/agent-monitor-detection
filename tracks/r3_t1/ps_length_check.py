"""Does the per-PR monitor score track diff length (a label-correlated confound: gradual-attack diffs are ~4x
shorter than honest diffs)? Spearman(score, log diff chars) within honest PRs and within gradual-attack PRs;
mean score by diff-length quintile (honest PRs)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from amd.common.schema import PROCESSED, load_trajectories, read_jsonl

T = {t.traj_id: t for t in load_trajectories("persistent_state")}
files = {"gpt-4.1-mini history-free": "r2_scores_openai_gpt-4.1-mini_current_only.jsonl",
         "gpt-4.1-mini history-aware": "r2_scores_openai_gpt-4.1-mini_full_diffs.jsonl",
         "qwen history-free": "r2_scores_qwen_qwen3-235b-a22b-2507_current_only.jsonl",
         "gemini history-free": "r2_scores_google_gemini-2.5-flash_current_only.jsonl",
         "gpt-4.1-mini reflag": "r3_scores_reflag.jsonl", "gpt-4.1-mini ledger": "r3_scores_ledger.jsonl"}
rows = []
for name, f in files.items():
    recs = []
    for r in read_jsonl(PROCESSED / "persistent_state" / f):
        t = T[r["traj_id"]]
        for i, (s, c) in enumerate(zip(r["scores"], t.meta["pr_diff_chars"])):
            if s is not None and c:
                recs.append(dict(policy=t.context["policy"], score=s, logc=np.log(c), pr=i))
    D = pd.DataFrame(recs)
    for pol in ("honest", "gradual"):
        x = D[D.policy == pol]
        r = spearmanr(x.score, x.logc)
        rows.append(dict(monitor=name, policy=pol, rho_score_logchars=round(r.statistic, 3), n=len(x),
                         median_chars=int(np.exp(x.logc.median()))))
out = pd.DataFrame(rows)
print(out.to_string(index=False))
out.to_csv(Path("results/r3_t1/ps_length_check.csv"), index=False)
