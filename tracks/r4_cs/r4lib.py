"""Shared helpers for round-4 cross-session accumulation (track r4cs).

- ps_monitor_streams(): history-free per-PR streams of every persistent-state monitor with identical inputs
  (round-2 gpt-4.1-mini / Gemini 2.5 Flash / Qwen3-235B + round-4 monitors), plus GPT-4o original (reference only:
  it saw untruncated diffs under the paper's own output format, so its inputs are not identical).
- common_sets(): StreamSets on the runs complete under every identical-input monitor (same honest / attack
  universes and order for every monitor, so one bootstrap weight matrix is shared by all monitors).
- suite(): pre-specified detectors (max, 2nd/3rd-max, whitened and raw top-3 sum, CUSUM k=0.5/1.5).
- re_pool(): DerSimonian-Laird random-effects pooling (+ HKSJ interval, tau^2, I^2, prediction interval).
- shared_weights(): the honest / attack bootstrap weight matrices amd.evaluation.paired draws for a given seed,
  so other statistics (e.g. the repeat-spike LR) can be recomputed on exactly the same replicates.
- spike_counts(): per-stream count of units above the honest 95% unit quantile (repeat-spike LR ingredients).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import stats as sps

HERE = Path(__file__).parent
for p in (HERE.parent / "r2_t1", HERE.parent / "t1_matched_budget"):
    sys.path.insert(0, str(p))
from t1lib import StreamSet  # noqa: E402

from amd.common.schema import PROCESSED, REPO, load_trajectories, read_jsonl  # noqa: E402
from amd.detectors import CUSUM, KthLargest, Max, TopKSum, Whiten  # noqa: E402
from amd.evaluation.matched import bootstrap_weights  # noqa: E402

OUT = REPO / "results" / "r4_cs"
RAW = REPO / "data" / "raw" / "r4_cs"
PS = PROCESSED / "persistent_state"

# identical-input history-free monitors: (label, file, round, family)
R2 = [("gpt-4.1-mini", "r2_scores_openai_gpt-4.1-mini_current_only.jsonl", "r2", "OpenAI"),
      ("gemini-2.5-flash", "r2_scores_google_gemini-2.5-flash_current_only.jsonl", "r2", "Google"),
      ("qwen3-235b", "r2_scores_qwen_qwen3-235b-a22b-2507_current_only.jsonl", "r2", "Qwen")]
R4 = [("gpt-4.1", "r4_scores_openai_gpt-4.1_current_only.jsonl", "r4", "OpenAI"),
      ("claude-haiku-4.5", "r4_scores_anthropic_claude-haiku-4.5_current_only.jsonl", "r4", "Anthropic"),
      ("gemini-2.5-pro", "r4_scores_google_gemini-2.5-pro_current_only.jsonl", "r4", "Google"),
      ("gpt-5-mini", "r4_scores_openai_gpt-5-mini_current_only.jsonl", "r4", "OpenAI"),
      ("claude-haiku-5.5", "r4_scores_anthropic_claude-haiku-5.5_current_only.jsonl", "r4", "Anthropic"),
      ("gpt-6-luna", "r4_scores_openai_gpt-6-luna_current_only.jsonl", "r4", "OpenAI")]
REF = ("gpt-4o (orig, ref)", "openai/gpt-4o|score_pr_diff_current_only|current_only")


def _load(path):
    return {r["traj_id"]: np.array([np.nan if v is None else float(v) for v in r["scores"]], float)
            for r in read_jsonl(path)}


def ps_monitor_streams(include_ref=True):
    out = {}
    for lab, f, rnd, fam in R2 + R4:
        p = PS / f
        if p.exists():
            out[lab] = dict(streams=_load(p), round=rnd, family=fam, identical=True)
    if include_ref:
        d = {}
        for r in read_jsonl(PS / "scores.jsonl"):
            if r["monitor_id"] == REF[1]:
                d[r["traj_id"]] = np.array([np.nan if v is None else float(v) for v in r["scores"]], float)
        out[REF[0]] = dict(streams=d, round="r1", family="OpenAI", identical=False)
    return out


def common_sets(mons, policies=("gradual",), ids=None):
    """{monitor: {policy: StreamSet}} on runs complete (5 finite PR scores) under every identical-input monitor
    (and the reference). Honest = honest runs; attacks = runs of the given policy. App ids kept for clustering."""
    T = {t.traj_id: t for t in load_trajectories("persistent_state")}
    if ids is None:
        ids = set.intersection(*(set(m["streams"]) for m in mons.values()))
        ids = {i for i in ids if all(np.isfinite(m["streams"][i]).all() for m in mons.values())}
    ids = sorted(ids)
    out = {}
    for lab, m in mons.items():
        out[lab] = {}
        for pol in policies:
            H, A, hid, aid, on, hm, am, hmeta = [], [], [], [], [], [], [], []
            for tid in ids:
                t = T[tid]
                if t.label == "honest":
                    H.append(m["streams"][tid]); hid.append(tid); hmeta.append({"app": t.context["app"]})
                elif t.context["policy"] == pol:
                    A.append(m["streams"][tid]); aid.append(tid)
                    on.append(t.attack_step); hm.append(t.harm_step)
                    am.append({"app": t.context["app"], "side_task": t.context.get("side_task"),
                               "side_task_success": t.side_task_success})
            out[lab][pol] = StreamSet(f"ps4:{lab}:{pol}", H, A, hid, aid, None, None, on, hm, am, hmeta, "pr",
                                      "iid split; app clusters for inference")
    return out, ids


def app_groups(ss):
    return (np.array([m["app"] for m in ss.honest_meta]), np.array([m["app"] for m in ss.attack_meta]))


def suite():
    raw3 = TopKSum(3)
    raw3.name = "top3sum_raw"
    s = [Max(), KthLargest(2), KthLargest(3), TopKSum(3, transform=Whiten()), raw3,
         CUSUM(k=0.5, transform=Whiten()), CUSUM(k=1.5, transform=Whiten())]
    return {x.name: x for x in s}


def shared_weights(n_h, n_a, B, seed, hg=None, ag=None):
    """Exactly the (Wh, Wa) that amd.evaluation.paired.paired_contrast_bootstrap draws for these arguments."""
    rng = np.random.default_rng(seed)
    Wh = bootstrap_weights(n_h, B, rng, hg)
    Wa = bootstrap_weights(n_a, B, rng, ag)
    return Wh, Wa


def spike_counts(H, A, q=0.95):
    """Counts of units above the honest q-quantile (chooser.spike_features threshold rule)."""
    hu = np.concatenate([s[np.isfinite(s)] for s in H])
    thr = np.quantile(hu, q)
    if (hu > thr).mean() < 0.005:
        vals = np.unique(hu)
        thr = vals[max(0, np.searchsorted(vals, thr) - 1)]
    cnt = lambda S: np.array([np.sum(s[np.isfinite(s)] > thr) for s in S])  # noqa: E731
    return cnt(H), cnt(A)


def rep_lr_weighted(ch, ca, wh=None, wa=None):
    """log[ P(>=2 spikes | >=1, attack) / P(>=2 | >=1, honest) ] with the chooser.spike_features smoothing;
    optional bootstrap weights (vectors or (B, n) matrices)."""
    wh = np.ones_like(ch, float) if wh is None else wh
    wa = np.ones_like(ca, float) if wa is None else wa
    h2c = ((wh * (ch >= 2)).sum(-1) + 0.5) / ((wh * (ch >= 1)).sum(-1) + 1)
    a2c = ((wa * (ca >= 2)).sum(-1) + 0.5) / ((wa * (ca >= 1)).sum(-1) + 1)
    return np.log(a2c / h2c)


def re_pool(est, se):
    """DerSimonian-Laird random effects. Returns dict(mu, se, lo, hi (z), hksj_lo, hksj_hi, tau2, I2, Q, k,
    pi_lo, pi_hi (prediction interval), w (normalized weights))."""
    est, se = np.asarray(est, float), np.asarray(se, float)
    k = len(est)
    w = 1 / se**2
    mu_f = (w * est).sum() / w.sum()
    Q = (w * (est - mu_f) ** 2).sum()
    c = w.sum() - (w**2).sum() / w.sum()
    tau2 = max(0.0, (Q - (k - 1)) / c) if c > 0 else 0.0
    ws = 1 / (se**2 + tau2)
    mu = (ws * est).sum() / ws.sum()
    se_mu = np.sqrt(1 / ws.sum())
    # Hartung-Knapp-Sidik-Jonkman
    q_hk = (ws * (est - mu) ** 2).sum() / (k - 1) if k > 1 else np.nan
    se_hk = np.sqrt(max(q_hk, 1e-12) / ws.sum()) if k > 1 else np.nan
    t = sps.t.ppf(0.975, k - 1) if k > 1 else np.nan
    pi = sps.t.ppf(0.975, k - 2) * np.sqrt(tau2 + se_mu**2) if k > 2 else np.nan
    I2 = max(0.0, (Q - (k - 1)) / Q) if Q > 0 else 0.0
    return dict(mu=mu, se=se_mu, lo=mu - 1.96 * se_mu, hi=mu + 1.96 * se_mu, hksj_lo=mu - t * se_hk,
                hksj_hi=mu + t * se_hk, tau2=tau2, I2=I2, Q=Q, k=k, pi_lo=mu - pi, pi_hi=mu + pi,
                w=ws / ws.sum())


def mpl():
    import matplotlib
    matplotlib.use("pdf")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titlesize": 9, "axes.labelsize": 8.5, "legend.fontsize": 7.5,
                         "pdf.fonttype": 42, "font.family": "sans-serif"})
    return plt
