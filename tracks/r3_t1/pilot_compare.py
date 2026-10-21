"""Compare pilot monitors on the same MOLE pilot account-days (per-day AUROC attack vs routine)."""
import sys

import pandas as pd
from sklearn.metrics import roc_auc_score

from amd.common.schema import PROCESSED

c = sys.argv[1] if len(sys.argv) > 1 else "gpt53_single_day"
d = PROCESSED / "r2_mole" / c
D = pd.read_parquet(d / "accountdays.parquet")[["account", "day", "attack_day"]]
full = pd.read_parquet(d / "llm_openai_gpt-4.1-mini.parquet")[["account", "day", "score"]].rename(columns={"score": "mini_full"})
for f in sorted(d.glob("llm_*_pilot.parquet")):
    P = pd.read_parquet(f).merge(D, on=["account", "day"]).merge(full, on=["account", "day"], how="left").dropna(subset=["score"])
    print(f.name, len(P), "AUROC", round(roc_auc_score(P.attack_day, P.score), 3),
          "| gpt-4.1-mini on same days", round(roc_auc_score(P.attack_day, P.mini_full), 3),
          "| honest mean", round(P[~P.attack_day].score.mean(), 2), "attack mean", round(P[P.attack_day].score.mean(), 2))
