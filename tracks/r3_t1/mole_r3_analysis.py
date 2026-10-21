"""Round 3, part A analysis: per-account accumulation across all MOLE corpora + meta-analysis.

    uv run python tracks/r3_t1/mole_r3_analysis.py [--splits 50] [--boot 300]

Per corpus x monitor (qwen3-235b compact = the common monitor on all 8 corpora; gpt-4.1-mini full rendering on
the 3 corpora scored in round 2; MOLE classical z-score / peer-fit):
  1. matched account-level FPR (alpha 0.10, 0.05; 112 routine accounts, 50/50 splits): max, 2nd/3rd-max,
     top-2/3/4 sums, mean, CUSUM k in {0.5, 1, 1.5, 2}, Shiryaev-Roberts, e-process; paired gains vs max;
  2. the empirical rule chooser (tracks/r2_t1/chooser.py; 10 labeled insider accounts) vs always-max;
  3. streaming delay in workdays (alpha 0.10) and alarm-by-first-executed-day;
  4. MOLE's daily review budget R@K/day for today's score vs running statistics;
  5. diagnostics: insider streams without attack days; horizon sweep (first D = 5, 10, 15, 20, 30 workdays);
  6. per-corpus features (repeat-spike log-LR, honest persistence, first-spike LR, attack days per insider) and
     a meta-analysis of the gain across corpora (inverse-variance pooled mean; Spearman vs features).
Single-day corpora exclude the collusive accounts (attack on most days), as in MOLE's single-day evaluation.
Writes results/r3_t1/mole_*.csv, mole_tables.md, figures.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
for p in (HERE.parent / "r2_t1", HERE.parent / "t1_matched_budget"):
    sys.path.insert(0, str(p))
from chooser import spike_features  # noqa: E402
from mole_analysis import daily_ranking  # noqa: E402
from r2lib import COLORS, LABEL, mpl_style, run_matched, suite  # noqa: E402
from r3lib import chooser_matched, chooser_summary  # noqa: E402
from r3lib import gains_full as gains_table  # noqa: E402  (full paired bootstrap incl. calibration noise)
from t1lib import StreamSet, streaming_metrics  # noqa: E402

from amd.common.schema import PROCESSED, REPO  # noqa: E402

OUT = REPO / "results" / "r3_t1"
CORPORA = ["gpt53_single_day", "gpt53_multiday", "deepseek_v4_flash_single_day", "deepseek_v4_flash_multiday",
           "qwen36_27b_single_day", "qwen36_27b_multiday", "kimi_k26_single_day", "kimi_k26_multiday"]
MON_FILES = {"qwen_compact": "llm_qwen_qwen3-235b-a22b-2507_compact.parquet",
             "mini_full": "llm_openai_gpt-4.1-mini.parquet"}
ALPHAS = (0.10, 0.05)
SHOW = ["kth2", "kth3", "top2sum", "top3sum", "top4sum", "mean", "cusum_k0.5", "cusum_k1.5", "cusum_k2", "sr_d1",
        "eproc_power"]
SHORT = {"gpt53": "GPT-5.3", "deepseek_v4_flash": "DeepSeek-V4", "qwen36_27b": "Qwen3.6-27B", "kimi_k26": "Kimi-K2.6"}


def cname(c):
    for k, v in SHORT.items():
        if c.startswith(k):
            return f"{v} {'single-day' if 'single' in c else 'multiday'}"
    return c


def load(corpus):
    d = PROCESSED / "r2_mole" / corpus
    if not (d / "accountdays.parquet").exists():
        return None
    D = pd.read_parquet(d / "accountdays.parquet")
    for m, f in MON_FILES.items():
        if (d / f).exists():
            D = D.merge(pd.read_parquet(d / f)[["account", "day", "score"]].rename(columns={"score": m}),
                        on=["account", "day"], how="left")
    return D.sort_values(["account", "day"]).reset_index(drop=True)


def make_set(D, corpus, mon, drop_attack=False, horizon=None):
    single = "single" in corpus
    H, A, hid, aid, on, hm, am = [], [], [], [], [], [], []
    for acct, g in D.groupby("account", sort=True):
        g = g.iloc[:horizon] if horizon else g
        s = g[mon].to_numpy(float)
        if not g.is_insider.iloc[0]:
            H.append(s); hid.append(acct)
            continue
        if single and g.collusive.iloc[0]:
            continue
        att = np.flatnonzero(g.attack_day.to_numpy())
        if not len(att):
            continue  # insider whose attacks all fall after the horizon
        ex = np.flatnonzero((g.outcome == "executed").to_numpy() & g.attack_day.to_numpy())
        if drop_attack:
            s = s.copy(); s[att] = np.nan
        A.append(s); aid.append(acct)
        on.append(int(att[0])); hm.append(int(ex[0]) if len(ex) else None)
        am.append({"n_attack_days": len(att)})
    name = f"mole:{corpus}:{mon}" + (":noattackdays" if drop_attack else "") + (f":D{horizon}" if horizon else "")
    return StreamSet(name, H, A, hid, aid, None, None, on, hm, am, [], "day", "iid split (accounts)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=int, default=50)
    ap.add_argument("--boot", type=int, default=300)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    dets = suite(extra_topk=True)
    M, G, S, R, F, C, HZ, CF = [], [], [], [], [], [], [], []
    for corpus in CORPORA:
        D = load(corpus)
        if D is None:
            print(f"skip {corpus}"); continue
        D["activity_only"] = np.log1p(D.n_events.astype(float))  # length/activity-only baseline monitor
        mons = [m for m in list(MON_FILES) + ["z_score", "peer_fit", "activity_only"]
                if m in D and D[m].notna().mean() > 0.98]
        CF.append(confounds(D, corpus))
        for mon in mons:
            D[mon] = D[mon].fillna(D[mon].median())
            ss = make_set(D, corpus, mon)
            df, raw = run_matched(ss, detectors=dets, alphas=ALPHAS, n_splits=a.splits, n_boot=a.boot,
                                  return_raw=True, seed=0)
            df["corpus"], df["monitor"] = corpus, mon
            M.append(df)
            g = gains_table(ss, raw, ALPHAS, list(dets)); g["corpus"], g["monitor"] = corpus, mon
            G.append(g)
            f = spike_features(ss.honest, ss.attack)
            f.update(corpus=corpus, monitor=mon, n_h=ss.n_h, n_a=ss.n_a,
                     attack_days=np.mean([m["n_attack_days"] for m in ss.attack_meta]))
            F.append(f)
            # chooser (empirical) with 10 labeled insiders
            C.append(chooser_matched(ss, n_lab=10, n_splits=40, alphas=ALPHAS))
            sm, _ = streaming_metrics(ss, detectors={k: dets[k] for k in ["max", "kth2", "kth3", "top3sum", "top4sum",
                                                                          "cusum_k1.5", "mean"]}, alpha=0.10, n_splits=20)
            sm["corpus"], sm["monitor"] = corpus, mon
            S.append(sm)
            # diagnostics: no attack days
            nd = make_set(D, corpus, mon, drop_attack=True)
            df2, raw2 = run_matched(nd, detectors={k: dets[k] for k in ["max", "kth3", "top3sum", "mean"]},
                                    alphas=ALPHAS, n_splits=a.splits, n_boot=100, return_raw=True, seed=0)
            g2 = gains_table(nd, raw2, ALPHAS, ["max", "kth3", "top3sum", "mean"])
            g2["corpus"], g2["monitor"] = corpus, mon
            G.append(g2)
            df2["corpus"], df2["monitor"] = corpus, mon
            M.append(df2)
            # horizon sweep (single-day corpora carry repeated attacks)
            for hz in (5, 10, 15, 20):
                hs = make_set(D, corpus, mon, horizon=hz)
                if hs.n_a < 8:
                    continue
                d3, r3 = run_matched(hs, detectors={k: dets[k] for k in ["max", "kth2", "kth3", "top3sum", "cusum_k1.5"]},
                                     alphas=(0.10,), n_splits=30, n_boot=50, return_raw=True, seed=0)
                g3 = gains_table(hs, r3, (0.10,), ["max", "kth2", "kth3", "top3sum", "cusum_k1.5"])
                g3["horizon"], g3["corpus"], g3["monitor"] = hz, corpus, mon
                g3["n_a"] = hs.n_a
                g3["tpr_max"] = d3[(d3.detector == "max") & (d3.threshold_kind == "calibrated")].tpr.iloc[0]
                HZ.append(g3)
            if mon in ("qwen_compact", "mini_full"):
                rk = daily_ranking(D, mon, corpus, {k: dets[k] for k in ["max", "kth3", "top3sum", "cusum_k1.5", "mean"]})
                from amd.detectors import Max
                rk = pd.concat([rk, daily_ranking(D, mon, corpus, {"today": Max()})])
                R.append(rk)
            print(f"  {corpus}:{mon} n_h={ss.n_h} n_a={ss.n_a}", flush=True)
    M, G, S, F = pd.concat(M), pd.concat(G), pd.concat(S), pd.DataFrame(F)
    CF = pd.DataFrame(CF)
    CF.to_csv(OUT / "mole_confounds.csv", index=False)
    R = pd.concat(R) if R else pd.DataFrame()
    HZ = pd.concat(HZ) if HZ else pd.DataFrame()
    CHS = pd.concat(C)
    emp = chooser_summary(CHS).set_index(["set", "alpha"])
    for name, df in (("matched", M), ("gains", G), ("streaming", S), ("features", F), ("daily_rank", R),
                     ("horizon", HZ), ("chooser", emp.reset_index()), ("chooser_splits", CHS)):
        df.to_csv(OUT / f"mole_{name}.csv", index=False)
    report(M, G, S, F, R, HZ, emp, CF)


def confounds(D, corpus):
    """Activity/length confounds: events per account-day by group; AUROC of activity alone; monitor-score vs
    activity correlation on routine days."""
    from scipy.stats import spearmanr
    from sklearn.metrics import roc_auc_score
    single = "single" in corpus
    keep = ~(D.is_insider & D.collusive) if single else np.ones(len(D), bool)
    X = D[keep]
    rout, att = X[~X.is_insider], X[X.attack_day]
    ins_other = X[X.is_insider & ~X.attack_day]
    y = np.r_[np.zeros(len(rout)), np.ones(len(att))]
    out = dict(corpus=corpus, ev_routine=rout.n_events.median(), ev_insider_other=ins_other.n_events.median(),
               ev_attack_day=att.n_events.median(),
               auroc_activity_attackday=roc_auc_score(y, np.r_[rout.n_events, att.n_events]),
               days_routine=rout.groupby("account").size().mean(), days_insider=X[X.is_insider].groupby("account").size().mean())
    for m in MON_FILES:
        if m in X and X[m].notna().all():
            out[f"rho_{m}_vs_events_routine"] = spearmanr(rout[m], rout.n_events).statistic
    return out


def pooled(g):
    se = (g.hi - g.lo) / (2 * 1.96)
    w = 1 / np.maximum(se, 1e-3) ** 2
    m = np.sum(w * g.gain_vs_max) / w.sum()
    s = 1 / np.sqrt(w.sum())
    # DerSimonian-Laird random effects
    q = np.sum(w * (g.gain_vs_max - m) ** 2)
    tau2 = max(0.0, (q - (len(g) - 1)) / (w.sum() - (w ** 2).sum() / w.sum())) if len(g) > 1 else 0.0
    wr = 1 / (se ** 2 + tau2)
    mr = np.sum(wr * g.gain_vs_max) / wr.sum()
    sr = 1 / np.sqrt(wr.sum())
    return mr, mr - 1.96 * sr, mr + 1.96 * sr, np.sqrt(tau2)


def report(M, G, S, F, R, HZ, emp, CF):
    from scipy.stats import spearmanr
    lines = ["# MOLE: per-account accumulation across 8 corpora (round 3)", "",
             "Gains: paired gain over max with a FULL bootstrap (honest calibration accounts and insider accounts "
             "resampled, thresholds recomputed per replicate; r3lib.paired_gain_full); p = share of replicates <= 0. "
             "Discovery corpora (detector choices made in round 2): GPT-5.3 single-day and multiday, DeepSeek-V4 "
             "single-day; the other five are confirmation corpora. Pre-specified comparisons: 3rd-max, top-3 sum, "
             "CUSUM k=1.5 and the empirical chooser vs max; all other detectors are exploratory.", ""]
    main = G[~G.set.str.contains("noattackdays")]
    for al in ALPHAS:
        sub = M[(M.alpha == al) & (M.threshold_kind == "calibrated") & ~M.set.str.contains("noattackdays")]
        cols = ["max", "kth2", "kth3", "top3sum", "top4sum", "mean", "cusum_k1.5", "eproc_power"]
        lines += [f"## TPR at account-level FPR {al} (95% CI); paired gain vs max in parentheses", "",
                  "| corpus | monitor | n_h/n_a | realized FPR (max / 3rd-max) | " + " | ".join(LABEL.get(c, c) for c in cols) + " | chooser (emp; 10 labeled insiders) |",
                  "|" + "---|" * (len(cols) + 5)]
        for s, g in sub.groupby("set", sort=False):
            g = g.set_index("detector")
            gg = main[(main.alpha == al) & (main.set == s)].set_index("detector")
            best = g.loc[cols].tpr.idxmax()
            cells = []
            for c in cols:
                v = f"{g.loc[c].tpr:.2f}" + ("" if c == "max" else
                                             f" ({gg.loc[c].gain_vs_max:+.3f} [{gg.loc[c].lo:+.2f}, {gg.loc[c].hi:+.2f}], p={gg.loc[c].p_le0:.2f})")
                if c == "max":
                    v = f"{g.loc[c].tpr:.2f} [{g.loc[c].tpr_lo:.2f}, {g.loc[c].tpr_hi:.2f}]"
                cells.append(f"**{v}**" if c == best else v)
            ch = emp.loc[(s, al)] if (s, al) in emp.index else None
            chs = (f"{ch['tpr_choice']:.2f} (FPR {ch['fpr_choice']:.3f}; vs max at same FPR {ch['gain_matched']:+.3f})"
                   if ch is not None else "")
            c0, m0 = g.corpus.iloc[0], g.monitor.iloc[0]
            lines.append(f"| {cname(c0)} | {m0} | {int(g.n_honest_total.iloc[0])}/{int(g.n_attack_total.iloc[0])} | "
                         f"{g.loc['max'].fpr:.3f} / {g.loc['kth3'].fpr:.3f} | " + " | ".join(cells) + f" | {chs} |")
        lines.append("")
    lines += ["## Per-corpus stream features (whole set) and gain of the 3rd-max / top-3 sum over max (FPR 0.10)", "",
              "| corpus | monitor | attack days / insider | repeat-spike log-LR | first-spike log-LR | honest persistence h2c | honest lag-1 ac | 3rd-max - max | top-3 sum - max |",
              "|---|---|---|---|---|---|---|---|---|"]
    gm = main[main.alpha == 0.10]
    for _, f in F.iterrows():
        s = f"mole:{f.corpus}:{f.monitor}"
        k3 = gm[(gm.set == s) & (gm.detector == "kth3")]
        t3 = gm[(gm.set == s) & (gm.detector == "top3sum")]
        lines.append(f"| {cname(f.corpus)} | {f.monitor} | {f.attack_days:.1f} | {f.rep_lr:+.2f} | {f.first_lr:+.2f} | "
                     f"{f.h2c:.2f} | {f.ac1:.2f} | {k3.gain_vs_max.iloc[0]:+.3f} | {t3.gain_vs_max.iloc[0]:+.3f} |")
    lines += ["", "## Meta-analysis (FPR 0.10): random-effects pooled gain over max, by corpus type and monitor", "",
              "| monitor | corpus type | detector | k corpora | pooled gain [95% CI] | tau |", "|---|---|---|---|---|---|"]
    gm = gm.assign(kind=gm.corpus.str.contains("single").map({True: "single-day (3-4 attack days)", False: "multiday (1 attack day)"}))
    for (mon, kind, det), g in gm[gm.detector.isin(["kth2", "kth3", "top3sum", "top4sum", "cusum_k1.5", "mean"])].groupby(
            ["monitor", "kind", "detector"]):
        m, lo, hi, tau = pooled(g)
        lines.append(f"| {mon} | {kind} | {LABEL.get(det, det)} | {len(g)} | {m:+.3f} [{lo:+.3f}, {hi:+.3f}] | {tau:.3f} |")
    j = gm[gm.detector.isin(["kth3", "top3sum"])].merge(F, on=["corpus", "monitor"])
    lines += ["", "Spearman across all corpus x monitor cells (FPR 0.10):"]
    for det in ("kth3", "top3sum"):
        x = j[j.detector == det]
        for col in ("rep_lr", "first_lr", "h2c", "attack_days"):
            r = spearmanr(x[col], x.gain_vs_max)
            lines.append(f"- {LABEL[det]} gain vs {col}: {r.statistic:+.2f} (p = {r.pvalue:.3f}, n = {len(x)})")
    lines += ["", "## Insider streams WITHOUT attack days (diagnostic; FPR 0.10): gain over max", "",
              "| corpus | monitor | max TPR | 3rd-max - max | top-3 sum - max | mean - max |", "|---|---|---|---|---|---|"]
    nd = G[G.set.str.contains("noattackdays") & (G.alpha == 0.10)]
    mnd = M[M.set.str.contains("noattackdays") & (M.alpha == 0.10) & (M.threshold_kind == "calibrated") & (M.detector == "max")]
    for s, g in nd.groupby("set", sort=False):
        g = g.set_index("detector")
        mx = mnd[mnd.set == s].tpr.iloc[0]
        lines.append(f"| {cname(s.split(':')[1])} | {s.split(':')[2]} | {mx:.2f} | {g.loc['kth3'].gain_vs_max:+.3f} | "
                     f"{g.loc['top3sum'].gain_vs_max:+.3f} | {g.loc['mean'].gain_vs_max:+.3f} |")
    lines += ["", "## Streaming at FPR 0.10: detection, median delay (workdays from the first attack day), alarm by first executed day", "",
              "| corpus | monitor | max | 2nd-max | 3rd-max | top-3 sum | CUSUM k=1.5 |", "|---|---|---|---|---|---|---|"]
    for (c, mon), g in S.groupby(["corpus", "monitor"], sort=False):
        g = g.set_index("detector")
        cell = lambda d: f"{g.loc[d].detection_rate:.2f} / {g.loc[d].median_delay:.0f} d / {g.loc[d].get('before_harm_rate', np.nan):.2f}"  # noqa: E731
        lines.append(f"| {cname(c)} | {mon} | " + " | ".join(cell(d) for d in ["max", "kth2", "kth3", "top3sum", "cusum_k1.5"]) + " |")
    if len(R):
        lines += ["", "## Daily review budget: R@10/day (budget-AUC), executed attack account-days", "",
                  "| corpus | monitor | today | running max | 3rd-max | top-3 sum | CUSUM k=1.5 | mean | n pos |", "|---|---|---|---|---|---|---|---|---|"]
        for (c, mon), g in R.groupby(["corpus", "monitor"], sort=False):
            cell = lambda d: (lambda x: f"{x[x.K == 10].recall.iloc[0]:.2f} ({x.recall.mean():.2f})")(g[g.detector == d])  # noqa: E731
            lines.append(f"| {cname(c)} | {mon} | " + " | ".join(cell(d) for d in ["today", "max", "kth3", "top3sum", "cusum_k1.5", "mean"])
                         + f" | {g.n_pos.iloc[0]} |")
    lines += ["", "## Activity / length confounds (median events per account-day; AUROC of activity alone)", "",
              "| corpus | routine days | insider other days | attack days | AUROC(events: attack day vs routine) | "
              "days/account routine vs insider | rho(qwen score, events) routine | rho(mini score, events) routine |",
              "|---|---|---|---|---|---|---|---|"]
    for _, c in CF.iterrows():
        lines.append(f"| {cname(c.corpus)} | {c.ev_routine:.0f} | {c.ev_insider_other:.0f} | {c.ev_attack_day:.0f} | "
                     f"{c.auroc_activity_attackday:.2f} | {c.days_routine:.1f} vs {c.days_insider:.1f} | "
                     f"{c.get('rho_qwen_compact_vs_events_routine', np.nan):+.2f} | {c.get('rho_mini_full_vs_events_routine', np.nan):+.2f} |")
    lines.append("The `activity_only` monitor rows in the main table run the same per-account statistics on log(1 + events "
                 "per day): what activity volume alone achieves.")
    if len(HZ):
        lines += ["", "## Horizon sweep (first D workdays; FPR 0.10): gain over max", "",
                  "| corpus | monitor | D | n insiders | max TPR | 2nd-max | 3rd-max | top-3 sum | CUSUM k=1.5 |", "|---|---|---|---|---|---|---|---|---|"]
        for (c, mon, hz), g in HZ.groupby(["corpus", "monitor", "horizon"], sort=False):
            g = g.set_index("detector")
            lines.append(f"| {cname(c)} | {mon} | {hz} | {int(g.n_a.iloc[0])} | {g.tpr_max.iloc[0]:.2f} | " + " | ".join(
                f"{g.loc[d].gain_vs_max:+.3f}" for d in ["kth2", "kth3", "top3sum", "cusum_k1.5"]) + " |")
    (OUT / "mole_tables.md").write_text("\n".join(lines) + "\n")
    figures(G, F)
    print("\n".join(lines)[:12000])


def figures(G, F):
    plt = mpl_style()
    gm = G[(G.alpha == 0.10) & ~G.set.str.contains("noattackdays")]
    j = gm[gm.detector.isin(["kth3", "top3sum", "cusum_k1.5"])].merge(F, on=["corpus", "monitor"])
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.7), sharey=True)
    mk = {"qwen_compact": "o", "mini_full": "s", "z_score": "^", "peer_fit": "D", "activity_only": "x"}
    for ax, det in zip(axes, ["kth3", "top3sum", "cusum_k1.5"]):
        x = j[j.detector == det]
        for mon, g in x.groupby("monitor"):
            col = np.where(g.corpus.str.contains("single"), "#1baf7a", "#7d2a63")
            ax.scatter(g.rep_lr, g.gain_vs_max, c=col, marker=mk.get(mon, "o"), s=24, edgecolors="white",
                       linewidths=0.4, label=mon)
        ax.axhline(0, color="#999", lw=0.8)
        ax.set_title(f"{LABEL[det]} - max", loc="left")
        ax.set_xlabel("repeat-spike log-LR (attack vs honest)")
    axes[0].set_ylabel("TPR gain over max (account FPR 0.10)")
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker=mk[m], ls="", color="#888", label=m) for m in mk] + \
        [Line2D([], [], marker="o", ls="", color="#1baf7a", label="single-day corpus"),
         Line2D([], [], marker="o", ls="", color="#7d2a63", label="multiday corpus")]
    fig.legend(handles=h, frameon=False, ncol=6, loc="lower center", fontsize=6.5)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(OUT / "fig_mole_gain_vs_repeat_lr.pdf")

    q = gm[(gm.monitor == "qwen_compact")]
    if len(q):
        corp = list(dict.fromkeys(q.corpus))
        fig, ax = plt.subplots(figsize=(7.2, 3.0))
        dets = ["kth2", "kth3", "top3sum", "top4sum", "mean", "cusum_k1.5", "eproc_power"]
        w = 0.8 / len(dets)
        for k, d in enumerate(dets):
            v = q[q.detector == d].set_index("corpus").reindex(corp)
            x = np.arange(len(corp)) + (k - len(dets) / 2) * w + w / 2
            ax.bar(x, v.gain_vs_max, w, color=COLORS.get(d, "#888"), label=LABEL[d])
            ax.errorbar(x, v.gain_vs_max, yerr=[v.gain_vs_max - v.lo, v.hi - v.gain_vs_max], fmt="none", ecolor="#333", lw=0.6)
        ax.axhline(0, color="#999", lw=0.8)
        ax.set_xticks(range(len(corp)), [cname(c).replace(" ", "\n", 1) for c in corp], fontsize=7)
        ax.set_ylabel("TPR gain over max\n(account FPR 0.10)")
        ax.legend(frameon=False, ncol=4, fontsize=6.5)
        ax.set_title("History-free qwen3-235b account-day monitor, per-account accumulation over 30 workdays", loc="left")
        fig.tight_layout()
        fig.savefig(OUT / "fig_mole_gain_by_corpus.pdf")


if __name__ == "__main__":
    main()
