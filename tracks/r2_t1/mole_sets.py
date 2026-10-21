"""MOLE per-account day streams (unit = account-day, up to 30 workdays) for cross-day accumulation.

Honest streams = routine-only accounts (112 per corpus). Attack streams = insider accounts:
  single_day corpus: solo insiders (30), each with 3-4 attack days; the 8 collusive accounts (an attack
                     session on almost every day) are excluded, as in the MOLE single-day evaluation.
  multiday corpus:   all 38 insiders, each with ONE attack day (a negative control for accumulation).
Onset = index of the first attack day; harm = index of the first day labeled `executed` (None if none).
Variants: attack accounts restricted to those with >= 1 executed day ("exec").
Monitors: llm (history-free gpt-4.1-mini on the current account-day), z_score, peer_fit (MOLE classical, level 0).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "t1_matched_budget"))
from t1lib import StreamSet  # noqa: E402

from amd.common.schema import PROCESSED  # noqa: E402

CORPORA = ("gpt53_single_day", "gpt53_multiday", "deepseek_v4_flash_single_day")
MONITORS = {"llm": "llm_openai_gpt-4.1-mini.parquet", "z_score": None, "peer_fit": None}


def load_days(corpus: str) -> pd.DataFrame:
    d = PROCESSED / "r2_mole" / corpus
    D = pd.read_parquet(d / "accountdays.parquet")
    for name, f in MONITORS.items():
        if f and (d / f).exists():
            S = pd.read_parquet(d / f)[["account", "day", "score"]].rename(columns={"score": name})
            D = D.merge(S, on=["account", "day"], how="left")
    return D.sort_values(["account", "day"]).reset_index(drop=True)


def account_sets(corpus: str, monitor: str, exec_only=False, D=None, drop_attack_days=False) -> StreamSet | None:
    """drop_attack_days=True: insider streams with their attack days set to NaN (diagnostic: how much of an
    accumulator's detection comes from the insider's NON-attack days, i.e. a persistent account offset)."""
    D = load_days(corpus) if D is None else D
    if monitor not in D:
        return None
    single = "single" in corpus
    H, A, hid, aid, on, hm, am = [], [], [], [], [], [], []
    for acct, g in D.groupby("account", sort=True):
        s = g[monitor].to_numpy(float)
        if not g.is_insider.iloc[0]:
            H.append(s); hid.append(acct)
            continue
        if single and g.collusive.iloc[0]:
            continue
        ex = np.flatnonzero((g.outcome == "executed").to_numpy())
        if exec_only and not len(ex):
            continue
        att = np.flatnonzero(g.attack_day.to_numpy())
        if drop_attack_days:
            s = s.copy(); s[att] = np.nan
        A.append(s); aid.append(acct)
        on.append(int(att[0]) if len(att) else None)
        hm.append(int(ex[0]) if len(ex) else None)
        am.append({"n_attack_days": len(att), "n_executed": len(ex), "scenario": g.scenario_acct.iloc[0],
                   "attack_idx": att.tolist()})
    name = (f"mole:{corpus.replace('gpt53_', '').replace('deepseek_v4_flash_', 'dsv4_')}:{monitor}" + (":exec" if exec_only else "")
            + (":noattackdays" if drop_attack_days else ""))
    return StreamSet(name, H, A, hid, aid, None, None, on, hm, am, [], "day", "iid split (accounts)")


def mole_stream_sets(exec_only=False):
    out = []
    for c in CORPORA:
        try:
            D = load_days(c)
        except FileNotFoundError:
            continue
        for m in MONITORS:
            ss = account_sets(c, m, exec_only, D)
            if ss is not None and np.isfinite(np.concatenate(ss.honest)).mean() > 0.95:
                out.append(ss)
    return out
