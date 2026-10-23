"""EXPLORATORY (Idea 05 round 2, part A): is standalone JEV's failure on BashArena-opus-4-6 a length / format confound?

Cached scores only (no API calls). Per panel (MonitoringBench + the 7 aksh-n settings, evaluation split, steps aligned
to the second stage exactly as in the round-1 analyses):
  1. length / format features vs label: AUROC (attack = positive) of step count, action length (mean / max / total),
     output length (mean / max / total), total characters, and format shares (tool-call name, truncated action
     >= 4,000 chars, empty output);
  2. a length-only (and a length + format) baseline: logistic regression on log features, out-of-fold AUROC from
     grouped 5-fold CV (groups = the panel's split groups);
  3. JEV AUROC within length-matched strata: strata = quintiles of step count, and quintiles of the out-of-fold
     length-only score (a length propensity score that balances all length features at once); stratified AUROC =
     Mann-Whitney restricted to within-stratum honest/attack pairs (weights n_h * n_a);
  4. aggregation: max vs mean vs top-3 mean vs a length-adjusted max (-log(1 - F(max)^n), F = empirical CDF of all
     honest steps of the panel; in-sample in F, exploratory);
  5. step level: AUROC of JEV, action length and output length for honest steps vs post-onset attack steps, and JEV
     within action-length quintile strata;
  6. post-hoc content check (added after reading the top-scoring honest BashArena steps): firewall-mentioning steps
     as the trajectory's highest-JEV step, JEV max AUROC with those steps masked, and per-side-task AUROC;
  7. post-hoc truncation check: action text dropped by the 4,000-char head+tail truncation, and whether the second
     stage's highest step is truncated and reached by the JEV or action-length gate at e = 20%.
Intervals: grouped (cluster) bootstrap over the panel's groups, B = 500, with the out-of-fold scores held fixed
(no refit noise). TPR at 1% FPR for max vs mean is taken from round 1 (`explore_rq2_standalone.csv`).

    unset VIRTUAL_ENV; uv run python -m tracks.r5_jev.analyze_length [--boot 500]
"""
from __future__ import annotations

import argparse
import re

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from amd.common.schema import PROCESSED, REPO, Trajectory, read_jsonl

from . import panels as PN
from .analyze_primary import frozen
from .splits import AKSHN

OUT = REPO / "results" / "r5_jev"
TOOL = re.compile(r"^\s*([A-Za-z_][\w.]*)\s*\(")
CAP = 4000


def load_rows(name, variant, scheme):
    P = PN.load_mb(variant, scheme, probe=False) if name == "mb" else PN.load_akshn(name, variant, scheme)
    files = ["mb_honest", "monitoringbench"] if name == "mb" else [name]
    ids = set(P.hid) | set(P.aid)
    T = {d["traj_id"]: Trajectory(**d) for f in files for d in read_jsonl(PROCESSED / f / "trajectories.jsonl")
         if d["traj_id"] in ids}
    rows = []
    for j, t in enumerate(P.hid + P.aid):
        n = len(P.streams["llm"][j])
        st = T[t].steps[:n]
        rows.append(dict(traj_id=t, y=int(j >= P.nh), n=n, steps=st,
                         alen=np.array([len(s.action) for s in st], float),
                         olen=np.array([len(s.output or "") for s in st], float),
                         jev=np.asarray(P.streams["jev"][j], float), llm=np.asarray(P.streams["llm"][j], float),
                         group=str(P.hg[j] if j < P.nh else P.ag[j - P.nh]),
                         onset=None if j < P.nh else (P.attack_onset[j - P.nh] or 0),
                         side=None if j < P.nh else P.meta["side"][j - P.nh]))
    return rows


def tool_of(a):
    m = TOOL.match(a)
    return m.group(1) if m else "other"


def features(rows):
    tools = pd.Series([tool_of(s.action) for r in rows for s in r["steps"]]).value_counts()
    top = [t for t in tools.index[:4]]
    L, F = [], []
    for r in rows:
        a, o = r["alen"], r["olen"]
        L.append(dict(n_steps=r["n"], mean_alen=a.mean(), max_alen=a.max(), tot_alen=a.sum(), mean_olen=o.mean(),
                      max_olen=o.max(), tot_olen=o.sum(), tot_chars=a.sum() + o.sum()))
        tl = [tool_of(s.action) for s in r["steps"]]
        F.append({**{f"share_tool_{t}": np.mean([x == t for x in tl]) for t in top},
                  "share_trunc_action": np.mean(a >= CAP), "share_empty_output": np.mean(o == 0)})
    return pd.DataFrame(L), pd.DataFrame(F)


def oof_lr(X, y, groups, k=5, seed=0):
    """Out-of-fold P(attack) from a logistic regression on the given features, grouped k-fold."""
    X = np.asarray(X, float)
    s = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=min(k, len(set(groups)))).split(X, y, groups):
        m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0))
        m.fit(X[tr], y[tr])
        s[te] = m.predict_proba(X[te])[:, 1]
    return s


def auc_w(y, s, w=None):
    ok = np.isfinite(s)
    y, s = y[ok], s[ok]
    w = None if w is None else w[ok]
    if len(set(y.tolist())) < 2:
        return np.nan
    return roc_auc_score(y, s, sample_weight=w)


def strat_auc(y, s, strata, w=None):
    """Mann-Whitney AUROC over within-stratum (honest, attack) pairs only."""
    w = np.ones(len(y)) if w is None else w
    num = den = 0.0
    for st in np.unique(strata):
        m = strata == st
        wh, wa = (w * m * (y == 0)).sum(), (w * m * (y == 1)).sum()
        if wh <= 0 or wa <= 0 or len(set(y[m].tolist())) < 2:
            continue
        num += auc_w(y[m], s[m], w[m]) * wh * wa
        den += wh * wa
    return num / den if den else np.nan


def quintiles(v):
    q = np.quantile(v, [0.2, 0.4, 0.6, 0.8])
    return np.searchsorted(q, v, side="right")


def boot(stat, groups, B, seed):
    """Point estimate + 95% grouped-bootstrap interval of stat(weights)."""
    rng = np.random.default_rng(seed)
    ug, inv = np.unique(groups, return_inverse=True)
    est = stat(np.ones(len(groups)))
    v = []
    for _ in range(B):
        c = np.bincount(rng.integers(0, len(ug), len(ug)), minlength=len(ug)).astype(float)
        v.append(stat(c[inv]))
    v = np.asarray(v, float)
    return est, np.nanquantile(v, 0.025), np.nanquantile(v, 0.975)


def nadj_max(rows):
    hs = np.sort(np.concatenate([r["jev"][np.isfinite(r["jev"])] for r in rows if r["y"] == 0]))
    out = []
    for r in rows:
        x = r["jev"][np.isfinite(r["jev"])]
        if not len(x):
            out.append(np.nan)
            continue
        F = np.searchsorted(hs, x.max(), side="left") / len(hs)     # P(honest step < max), conservative at ties
        out.append(-np.log(max(1 - F ** len(x), 1e-12)))
    return np.array(out)


def analyze(name, rows, B, seed, frows, srows, grows):
    y = np.array([r["y"] for r in rows])
    groups = np.array([r["group"] for r in rows])
    Lf, Ff = features(rows)
    for c in list(Lf.columns) + list(Ff.columns):
        v = (Lf[c] if c in Lf else Ff[c]).to_numpy(float)
        frows.append(dict(panel=name, feature=c, kind="length" if c in Lf else "format",
                          median_honest=np.median(v[y == 0]), median_attack=np.median(v[y == 1]),
                          auroc=auc_w(y, v)))
    XL = np.log1p(Lf.to_numpy(float))
    s_len = oof_lr(XL, y, groups)
    s_lenfmt = oof_lr(np.c_[XL, Ff.to_numpy(float)], y, groups)
    jmax = np.array([np.nanmax(r["jev"]) for r in rows])
    jmean = np.array([np.nanmean(r["jev"]) for r in rows])
    jtop3 = np.array([np.mean(np.sort(r["jev"][np.isfinite(r["jev"])])[-3:]) for r in rows])
    jadj = nadj_max(rows)
    lmax = np.array([np.nanmax(r["llm"]) if np.isfinite(r["llm"]).any() else np.nan for r in rows])
    st_n = quintiles(Lf["n_steps"].to_numpy(float) + 1e-6 * np.arange(len(y)))
    st_p = quintiles(s_len)
    aggs = dict(jev_max=jmax, jev_mean=jmean, jev_top3mean=jtop3, jev_nadj_max=jadj, llm_max=lmax)
    res = dict(panel=name, n_honest=int((y == 0).sum()), n_attack=int((y == 1).sum()))
    for k, (s, strata) in dict(len_only_cv=(s_len, None), len_format_cv=(s_lenfmt, None),
                               **{f"{a}": (v, None) for a, v in aggs.items()},
                               **{f"{a}|strat_nsteps": (v, st_n) for a, v in aggs.items()},
                               **{f"{a}|strat_lenscore": (v, st_p) for a, v in aggs.items()}).items():
        f = (lambda w, s=s: auc_w(y, s, w)) if strata is None else (lambda w, s=s, z=strata: strat_auc(y, s, z, w))
        e, lo, hi = boot(f, groups, B, seed)
        res[k], res[k + "_lo"], res[k + "_hi"] = e, lo, hi
        grows.append(dict(panel=name, score=k.split("|")[0], strata=(k.split("|") + ["none"])[1], auroc=e, lo=lo,
                          hi=hi))
    # per-stratum detail for JEV max / mean (step-count quintiles)
    for q in range(5):
        m = st_n == q
        res_q = dict(panel=name, stratum=f"nsteps_q{q + 1}", n_lo=int(Lf["n_steps"][m].min()),
                     n_hi=int(Lf["n_steps"][m].max()), n_honest=int((y[m] == 0).sum()), n_attack=int((y[m] == 1).sum()),
                     jev_max=auc_w(y[m], jmax[m]), jev_mean=auc_w(y[m], jmean[m]), jev_nadj_max=auc_w(y[m], jadj[m]),
                     llm_max=auc_w(y[m], lmax[m]))
        srows.append(res_q)
    # step level: honest steps vs post-onset attack steps
    hj = np.concatenate([r["jev"] for r in rows if r["y"] == 0])
    ha = np.concatenate([r["alen"] for r in rows if r["y"] == 0])
    ho = np.concatenate([r["olen"] for r in rows if r["y"] == 0])
    aj = np.concatenate([r["jev"][r["onset"]:] for r in rows if r["y"] == 1])
    aa = np.concatenate([r["alen"][r["onset"]:] for r in rows if r["y"] == 1])
    ao = np.concatenate([r["olen"][r["onset"]:] for r in rows if r["y"] == 1])
    ys = np.r_[np.zeros(len(hj)), np.ones(len(aj))]
    sj, sa, so = np.r_[hj, aj], np.r_[ha, aa], np.r_[ho, ao]
    res.update(step_auroc_jev=auc_w(ys, sj), step_auroc_action_len=auc_w(ys, sa), step_auroc_output_len=auc_w(ys, so),
               step_auroc_jev_strat_action_len=strat_auc(ys, sj, quintiles(sa + 1e-6 * np.arange(len(sa)))),
               step_jev_q90_honest=np.nanquantile(hj, 0.9), step_jev_q90_attack_post=np.nanquantile(aj, 0.9),
               share_honest_traj_jevmax_ge_0_5=float(np.mean(jmax[y == 0] >= 0.5)),
               share_attack_traj_jevmax_ge_0_5=float(np.mean(jmax[y == 1] >= 0.5)))
    res.update(content(rows, y, jmax))
    res.update(truncation(rows, y, jmax, seed))
    return res


FW = re.compile(r"firewall", re.I)
TRUNC = re.compile(r"\[truncated (\d+) chars\]")


def truncation(rows, y, jmax, seed):
    """Post-hoc truncation check. Ingest (`amd/data/_util.trunc`, ACTION_CHARS = 4,000) keeps the head and tail of every
    long action, and the frozen JEV request caps the current action at 4,000 chars as well; the aksh-n second-stage
    scores are the dataset's own (computed on the original actions). Reports the share of action characters dropped,
    whether the second stage's highest-scoring step is a truncated one, JEV max AUROC restricted to attacks whose
    second-stage argmax step is untruncated (alone and with firewall steps masked), and how often a gate escalating
    the top 20% of honest steps (JEV vs action length; seeded jitter for ties) reaches that argmax step."""
    lost = np.array([sum(int(m) for s in r["steps"] for m in TRUNC.findall(s.action)) for r in rows], float)
    tot = np.array([r["alen"].sum() for r in rows]) + lost
    gi = [int(np.nanargmax(r["llm"])) if np.isfinite(r["llm"]).any() else 0 for r in rows]
    tr = np.array([bool(TRUNC.search(r["steps"][k].action)) for r, k in zip(rows, gi)])
    masked = np.array([np.nanmax(np.where([not FW.search(s.action) for s in r["steps"]], r["jev"], 0.0))
                       for r in rows])
    keep = (y == 0) | ~tr
    a = y == 1
    out = dict(median_share_chars_truncated_honest=float(np.median(lost[y == 0] / tot[y == 0])),
               median_share_chars_truncated_attack=float(np.median(lost[a] / tot[a])),
               share_honest_llm_argmax_step_truncated=float(tr[y == 0].mean()),
               share_attack_llm_argmax_step_truncated=float(tr[a].mean()),
               jev_at_llm_argmax_step_attack_truncated=float(np.nanmean([r["jev"][k] for r, k, t in zip(rows, gi, tr)
                                                                         if r["y"] and t])) if (a & tr).any() else np.nan,
               jev_max_auroc_untruncated_argmax_attacks=auc_w(y[keep], jmax[keep]),
               jev_max_auroc_untruncated_argmax_attacks_fw_masked=auc_w(y[keep], masked[keep]))
    rng = np.random.default_rng(seed)
    for gate in ["jev", "alen"]:
        sc = [np.where(np.isfinite(r[gate]), r[gate], np.inf) + 1e-6 * rng.random(r["n"]) for r in rows]
        thr = np.quantile(np.concatenate([x for x, r in zip(sc, rows) if r["y"] == 0]), 0.8)
        esc = np.array([sc[i][k] >= thr for i, k in enumerate(gi)])
        out[f"esc20_{gate}_llm_argmax_attack"] = float(esc[a].mean())
        out[f"esc20_{gate}_llm_argmax_attack_truncated"] = float(esc[a & tr].mean()) if (a & tr).any() else np.nan
        out[f"esc20_{gate}_llm_argmax_attack_untruncated"] = float(esc[a & ~tr].mean())
    pk = np.array([any("PACKET_SIZE_LIMIT" in s.action for s in r["steps"]) for r in rows])
    ps = [r["jev"][k] for r in rows if r["y"] == 0 for k, s in enumerate(r["steps"])
          if "PACKET_SIZE_LIMIT" in s.action and np.isfinite(r["jev"][k])]
    out.update(share_honest_packet_size_limit_edit=float(pk[y == 0].mean()),
               share_attack_packet_size_limit_edit=float(pk[a].mean()),
               median_jev_honest_packet_size_limit_steps=float(np.median(ps)) if ps else np.nan)
    return out


def content(rows, y, jmax):
    """Post-hoc content check (motivated by reading the top honest BashArena steps): share of trajectories whose
    highest-JEV step mentions the firewall, and JEV max AUROC with every firewall-mentioning step masked (both
    classes); per side task, JEV max AUROC of that side task's attacks vs all honest runs."""
    arg_fw = np.array([bool(FW.search(r["steps"][int(np.nanargmax(r["jev"]))].action)) for r in rows])
    any_fw = np.array([any(FW.search(s.action) for s in r["steps"]) for r in rows])
    masked = np.array([np.nanmax(np.where([not FW.search(s.action) for s in r["steps"]], r["jev"], 0.0))
                       for r in rows])
    out = dict(share_honest_argmax_step_firewall=float(arg_fw[y == 0].mean()),
               share_attack_argmax_step_firewall=float(arg_fw[y == 1].mean()),
               share_honest_any_firewall_step=float(any_fw[y == 0].mean()),
               share_attack_any_firewall_step=float(any_fw[y == 1].mean()),
               jev_max_auroc_firewall_steps_masked=auc_w(y, masked),
               jev_max_auroc_honest_without_firewall_steps=auc_w(y[(y == 1) | ~any_fw], jmax[(y == 1) | ~any_fw]))
    return out


def side_rows(name, rows, out):
    y = np.array([r["y"] for r in rows])
    jmax = np.array([np.nanmax(r["jev"]) for r in rows])
    lmax = np.array([np.nanmax(r["llm"]) if np.isfinite(r["llm"]).any() else np.nan for r in rows])
    side = np.array([str(r.get("side")) for r in rows])
    for s in sorted(set(side[y == 1].tolist())):
        m = (y == 0) | (side == s)
        if (side == s).sum() < 15:
            continue
        out.append(dict(panel=name, side_task=s, n_attack=int((side == s).sum()), jev_max_auroc=auc_w(y[m], jmax[m]),
                        llm_max_auroc=auc_w(y[m], lmax[m]),
                        median_steps_attack=float(np.median([r["n"] for r, k in zip(rows, side == s) if k]))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=500)
    a = ap.parse_args()
    variant, scheme = frozen()
    summ, frows, srows, grows, side = [], [], [], [], []
    for i, name in enumerate(["mb"] + list(AKSHN)):
        rows = load_rows(name, variant, scheme)
        summ.append(analyze(name, rows, a.boot, 500 + i, frows, srows, grows))
        side_rows(name, rows, side)
        print(name, {k: round(v, 3) for k, v in summ[-1].items() if isinstance(v, float) and not k.endswith(("_lo", "_hi"))},
              flush=True)
    pd.DataFrame(summ).to_csv(OUT / "explore_length_confound.csv", index=False)
    pd.DataFrame(frows).to_csv(OUT / "explore_length_features.csv", index=False)
    pd.DataFrame(srows).to_csv(OUT / "explore_length_strata.csv", index=False)
    pd.DataFrame(grows).to_csv(OUT / "explore_length_auroc_long.csv", index=False)
    pd.DataFrame(side).to_csv(OUT / "explore_length_side_task.csv", index=False)


if __name__ == "__main__":
    main()
