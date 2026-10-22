"""Independent reproduction (c): MOLE per-account accumulation (round 3).

1. Common monitor (Qwen3-235B compact, generated integer score) on the 4 single-day corpora: 3rd-max minus max at
   account-level FPR 0.10; random 50/50 routine-account splits (iid; accounts are the unit), randomized
   thresholds; joint account bootstrap shared across splits with thresholds recomputed; per-corpus SE ->
   DerSimonian-Laird random-effects pooled estimate. Claimed: -0.066 [-0.156, +0.023].
2. Account-centering control on GPT-5.3 single-day with gpt-4.1-mini full rendering: 3rd-max minus max, raw
   (claimed +0.131) vs account-centered (day score minus the account's median day score; claimed +0.001).
   Also the activity-only baseline (log1p events/day) raw and with attack days removed (claimed +0.32 / +0.21).
3. A stricter centering variant that uses only the account's NON-attack days for the median is not deployable
   (labels); instead we report centering by the account's median over its first 10 workdays as a sensitivity.
Single-day corpora drop collusive insider accounts (as in MOLE's single-day evaluation and the track code).

    unset VIRTUAL_ENV; uv run python -m tracks.audit2.repro_mole
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .a2lib import alarm, rand_threshold

ROOT = "data/processed/r2_mole"
SINGLE = ["gpt53_single_day", "deepseek_v4_flash_single_day", "qwen36_27b_single_day", "kimi_k26_single_day"]


def kth(s, k):
    s = np.sort(s[np.isfinite(s)])[::-1]
    return s[k - 1] if len(s) >= k else -np.inf


def load(corpus):
    D = pd.read_parquet(f"{ROOT}/{corpus}/accountdays.parquet")
    X = pd.read_parquet(f"{ROOT}/{corpus}/llm_qwen_qwen3-235b-a22b-2507_compact.parquet")
    D = D.merge(X[["account", "day", "int_score"]].rename(columns={"int_score": "qwen_int"}), on=["account", "day"],
                how="left")
    try:
        Y = pd.read_parquet(f"{ROOT}/{corpus}/llm_openai_gpt-4.1-mini.parquet")
        D = D.merge(Y[["account", "day", "score"]].rename(columns={"score": "mini"}), on=["account", "day"],
                    how="left")
    except FileNotFoundError:
        pass
    D["activity"] = np.log1p(D.n_events.astype(float))
    return D.sort_values(["account", "day"]).reset_index(drop=True)


def account_stats(D, col, drop_attack=False, center=None):
    hs, as_ = {"max": [], "kth3": []}, {"max": [], "kth3": []}
    for acct, g in D.groupby("account", sort=True):
        s = g[col].to_numpy(float).copy()
        ins = bool(g.is_insider.iloc[0])
        if ins and (g.collusive.iloc[0] or not g.attack_day.any()):
            continue
        if center == "median":
            s = s - np.nanmedian(s)
        elif center == "first10":
            s = s - np.nanmedian(s[:10])
        if ins and drop_attack:
            s[g.attack_day.to_numpy()] = np.nan
        tgt = as_ if ins else hs
        tgt["max"].append(np.nanmax(s)); tgt["kth3"].append(kth(s, 3))
    return {k: np.array(v) for k, v in hs.items()}, {k: np.array(v) for k, v in as_.items()}


def gain(H, A, alpha=0.10, n_splits=100, B=600, seed=0):
    rng = np.random.default_rng(seed)
    nh, na = len(H["max"]), len(A["max"])
    masks = []
    for _ in range(n_splits):
        m = np.zeros(nh, bool); m[rng.permutation(nh)[: nh // 2]] = True; masks.append(m)

    def val(wh, wa):
        out = 0.0
        for m in masks:
            for k, c in (("kth3", 1.0), ("max", -1.0)):
                h, g = rand_threshold(H[k][m], wh[m], alpha)
                out += c * (alarm(A[k], h, g) * wa).sum() / wa.sum()
        return out / n_splits
    est = val(np.ones(nh), np.ones(na))
    bs = np.array([val(np.bincount(rng.integers(0, nh, nh), minlength=nh).astype(float),
                       np.bincount(rng.integers(0, na, na), minlength=na).astype(float)) for _ in range(B)])
    tp = {}
    for k in ("max", "kth3"):
        v = []
        for m in masks:
            h, g = rand_threshold(H[k][m], np.ones(m.sum()), alpha); v.append(alarm(A[k], h, g).mean())
        tp[k] = float(np.mean(v))
    return dict(est=est, lo=np.quantile(bs, .025), hi=np.quantile(bs, .975), se=bs.std(ddof=1),
                p_le0=(bs <= 0).mean(), tpr_max=tp["max"], tpr_kth3=tp["kth3"], n_h=nh, n_a=na)


def dersimonian_laird(est, se):
    est, v = np.asarray(est), np.asarray(se) ** 2
    w = 1 / v
    mu_f = (w * est).sum() / w.sum()
    Q = (w * (est - mu_f) ** 2).sum()
    tau2 = max(0.0, (Q - (len(est) - 1)) / (w.sum() - (w ** 2).sum() / w.sum()))
    ws = 1 / (v + tau2)
    mu = (ws * est).sum() / ws.sum()
    s = np.sqrt(1 / ws.sum())
    return mu, mu - 1.96 * s, mu + 1.96 * s, np.sqrt(tau2)


def main():
    rows = []
    for c in SINGLE:
        D = load(c)
        H, A = account_stats(D, "qwen_int")
        rows.append(dict(corpus=c, monitor="qwen_int", variant="raw", **gain(H, A)))
        print(rows[-1], flush=True)
    q = [r for r in rows if r["monitor"] == "qwen_int"]
    mu, lo, hi, tau = dersimonian_laird([r["est"] for r in q], [r["se"] for r in q])
    rows.append(dict(corpus="POOLED single-day (DL random effects)", monitor="qwen_int", variant="raw", est=mu, lo=lo,
                     hi=hi, se=np.nan, p_le0=np.nan, tau=tau))
    print(rows[-1], flush=True)
    D = load("gpt53_single_day")
    for col in ("mini", "activity", "qwen_int"):
        for variant, kw in (("raw", {}), ("centered_median", {"center": "median"}),
                            ("centered_first10", {"center": "first10"}), ("no_attack_days", {"drop_attack": True})):
            H, A = account_stats(D, col, **kw)
            rows.append(dict(corpus="gpt53_single_day", monitor=col, variant=variant, **gain(H, A)))
            print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv("results/audit2/repro_mole.csv", index=False)




def provider_check():
    """DeepSeek-V4 single-day was scored by a MIX of Qwen3-235B providers; the logprob provider is clustered by
    account (25/150 accounts mostly scored there) and gives ~1 point higher integer scores on routine days.
    Sensitivity: drop accounts with logprob-provider share > 0.5, recompute 3rd-max - max, and re-pool."""
    rows = []
    c = "deepseek_v4_flash_single_day"
    D = load(c)
    X = pd.read_parquet(f"{ROOT}/{c}/llm_qwen_qwen3-235b-a22b-2507_compact.parquet")
    X["lp"] = X.lp_ok.fillna(False).astype(bool)
    share = X.groupby("account").lp.mean()
    keep = share[share <= 0.5].index
    for tag, DD in (("all accounts", D), ("lp-provider share<=0.5", D[D.account.isin(keep)])):
        H, A = account_stats(DD, "qwen_int")
        rows.append(dict(corpus=c, monitor="qwen_int", variant=tag, **gain(H, A)))
        print(rows[-1], flush=True)
    base = pd.read_csv("results/audit2/repro_mole.csv")
    q = base[(base.monitor == "qwen_int") & (base.variant == "raw") & base.corpus.isin(SINGLE)]
    q = q[q.corpus != c]
    est = list(q.est) + [rows[-1]["est"]]
    se = list(q.se) + [rows[-1]["se"]]
    mu, lo, hi, tau = dersimonian_laird(est, se)
    rows.append(dict(corpus="POOLED single-day, DeepSeek restricted", monitor="qwen_int", variant="sensitivity",
                     est=mu, lo=lo, hi=hi, tau=tau))
    print(rows[-1])
    pd.DataFrame(rows).to_csv("results/audit2/repro_mole_provider.csv", index=False)


if __name__ == "__main__":
    main()
    provider_check()
