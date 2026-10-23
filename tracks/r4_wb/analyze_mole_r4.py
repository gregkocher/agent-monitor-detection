"""MOLE qwen36_27b_single_day policy-activation arm with account-matched benign sessions (PREREG Part 3).

Sessions: 233 attack + 233 benign sessions of the same account on the same day (tracks/r4_wb/mole_select.py).
Arms (per assistant turn, features pooled over the turn's tokens):
  policy          Qwen3.6-27B reads the session in its chat format with the original system prompt
  policy_neutral  same, attack sessions' system prompt replaced by the matched benign session's (identical
                  system prompt within each matched pair)
  reader          Qwen3.5-27B, monitor framing, no system prompt
  llm_insider / llm_generic   gpt-4.1-mini, one call per session (reader-format transcript, no system prompt)
Session statistic: max over turns (primary), mean (secondary). Primary stream: sab.
Metric: AUROC; TPR at 5% session FPR (randomized threshold on half of the benign sessions split by account,
200 splits). CIs: account-cluster bootstrap (B=2000) shared across arms (paired). Holm over M1-M5.

    unset VIRTUAL_ENV; uv run python -m tracks.r4_wb.analyze_mole_r4
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from amd.common.schema import REPO, read_jsonl
from amd.evaluation import calibrate
from tracks.wb_whitebox.analyze_mole import _derived_policy
from tracks.wb_whitebox.wblib import WB, derived

from .r4lib import holm

OUT = REPO / "results" / "r4_wb"
R4 = WB / "scores" / "r4"
STREAMS = ["sab", "fibs_tok", "jl_lm", "jl_hits"]
B = 2000


def load_arm(path):
    out = {}
    for d in read_jsonl(path):
        if d["n_steps"] == 0:
            continue
        F = d["feats"]
        dv = derived(F) if "dec_L19_mean" in F else _derived_policy(F)
        out[d["task_id"]] = {k: np.asarray(v, float) for k, v in dv.items() if k in STREAMS}
    return out


def auc_w(y, s, w):
    """Weighted AUROC (Mann-Whitney with integer weights)."""
    keep = w > 0
    y, s, w = y[keep], s[keep], w[keep]
    pos, neg = s[y], s[~y]
    wp, wn = w[y], w[~y]
    order = np.argsort(neg)
    neg, wn = neg[order], wn[order]
    cw = np.r_[0, np.cumsum(wn)]
    lo = np.searchsorted(neg, pos, side="left")
    hi = np.searchsorted(neg, pos, side="right")
    less = cw[lo]
    eq = cw[hi] - cw[lo]
    return float(((less + 0.5 * eq) * wp).sum() / (wp.sum() * wn.sum()))


def tpr_at(y, s, acct, alpha, rng, n_splits=200):
    accts = np.unique(acct[~y])
    v = []
    for _ in range(n_splits):
        cal = rng.permutation(accts)[: len(accts) // 2]
        m = (~y) & np.isin(acct, cal)
        th = calibrate(s[m], alpha, "randomized")
        v.append(th.alarm_prob(s[y]).mean())
    return float(np.mean(v))


def main():
    sel = [json.loads(l) for l in open("data/processed/whitebox/inputs/mole_r4_sel.jsonl")]
    meta = {s["task_id"]: dict(label=s["label"], account=s["account"], outcome=s["outcome"]) for s in sel}
    arms = {"policy": load_arm(R4 / "mole_policy.jsonl"), "policy_neutral": load_arm(R4 / "mole_policy_neutral.jsonl"),
            "reader": load_arm(R4 / "mole_reader.jsonl")}
    llm = {}
    for p in ("insider", "generic"):
        llm[f"llm_{p}"] = {d["task_id"]: d["score"] for d in read_jsonl(WB / "scores" / f"r4_mole_llm_{p}.jsonl")
                           if d["score"] is not None}
    ids = sorted(set(meta).intersection(*[set(a) for a in arms.values()], *[set(v) for v in llm.values()]))
    y = np.array([meta[t]["label"] == "attack" for t in ids])
    acct = np.array([meta[t]["account"] for t in ids])
    ua, inv = np.unique(acct, return_inverse=True)
    rng = np.random.default_rng(0)
    W = rng.multinomial(len(ua), np.full(len(ua), 1 / len(ua)), size=B)[:, inv]
    stats = {}
    for arm, D in arms.items():
        for st in STREAMS:
            for agg, f in (("max", np.nanmax), ("mean", np.nanmean)):
                stats[(arm, st, agg)] = np.array([f(D[t][st]) for t in ids])
    for k, v in llm.items():
        stats[(k, "score", "session")] = np.array([v[t] for t in ids], float)
    rows, boots = [], {}
    for key, s in stats.items():
        bs = np.array([auc_w(y, s, W[b]) for b in range(B)])
        boots[key] = bs
        rows.append(dict(arm=key[0], stream=key[1], agg=key[2], n_attack=int(y.sum()), n_benign=int((~y).sum()),
                         auroc=roc_auc_score(y, s), auroc_lo=np.quantile(bs, 0.025), auroc_hi=np.quantile(bs, 0.975),
                         tpr_at_0p05=tpr_at(y, s, acct, 0.05, np.random.default_rng(1)),
                         tpr_at_0p10=tpr_at(y, s, acct, 0.10, np.random.default_rng(1))))
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "mole_arms.csv", index=False)
    print(tab.round(3).to_string())

    def diff(a, b, name, family):
        pt = roc_auc_score(y, stats[a]) - roc_auc_score(y, stats[b])
        d = boots[a] - boots[b]
        p = float(min(1.0, 2 * min((d <= 0).mean(), (d >= 0).mean())))
        return dict(contrast=name, family=family, a="/".join(a), b="/".join(b), est=pt,
                    lo=np.quantile(d, 0.025), hi=np.quantile(d, 0.975), p_two=p)

    P, PN, R = ("policy", "sab", "max"), ("policy_neutral", "sab", "max"), ("reader", "sab", "max")
    LI = ("llm_insider", "score", "session")
    con = [diff(P, R, "M1 policy - reader", "holm"), diff(PN, R, "M2 policy_neutral - reader", "holm"),
           diff(P, PN, "M3 policy - policy_neutral (instruction effect)", "holm"),
           diff(R, LI, "M4 reader - LLM(insider)", "holm"), diff(PN, LI, "M5 policy_neutral - LLM(insider)", "holm")]
    adj = holm([c["p_two"] for c in con])
    for c, a in zip(con, adj):
        c["p_holm"] = a
    LG = ("llm_generic", "score", "session")
    for agg in ("mean",):
        con += [diff(("policy", "sab", agg), ("reader", "sab", agg), f"sec: policy - reader (sab {agg})", "secondary"),
                diff(("policy_neutral", "sab", agg), ("reader", "sab", agg), f"sec: policy_neutral - reader (sab {agg})",
                     "secondary"),
                diff(("policy", "sab", agg), ("policy_neutral", "sab", agg), f"sec: policy - policy_neutral (sab {agg})",
                     "secondary")]
    for st in ("fibs_tok", "jl_hits", "jl_lm"):
        con.append(diff(("policy", st, "max"), ("policy_neutral", st, "max"), f"sec: policy - policy_neutral ({st} max)",
                        "secondary"))
    con += [diff(R, LG, "sec: reader - LLM(generic)", "secondary"), diff(LI, LG, "sec: LLM(insider) - LLM(generic)",
                                                                         "secondary")]
    cdf = pd.DataFrame(con)
    cdf.to_csv(OUT / "mole_contrasts.csv", index=False)
    print(cdf.round(3).to_string())
    json.dump(dict(n_sessions=len(ids), n_accounts=len(ua)), open(OUT / "mole_info.json", "w"))


if __name__ == "__main__":
    main()
