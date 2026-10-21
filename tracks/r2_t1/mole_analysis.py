"""Round-2 MOLE analysis: per-ACCOUNT accumulation of history-free per-day evidence across 30 workdays.

    uv run python tracks/r2_t1/mole_analysis.py [--splits 50] [--boot 300]

1. Matched account-level FPR (alpha in {0.10, 0.05}; 112 routine accounts, 50/50 splits): TPR of max,
   2nd/3rd-max, top-k sums, mean, CUSUM(k grid), Shiryaev-Roberts, conformal e-process over each account's
   day stream; paired gains over max.
2. Streaming at alpha = 0.10: detection delay in workdays from the first attack day, share alarmed by the
   first executed (harm) day.
3. MOLE's native daily-budget metric: each day the K accounts with the highest running statistic are
   reviewed; R@K/day = share of executed attack account-days whose account is in that day's top K
   (K = 1..10, budget-AUC = mean over K). Running statistics come from detectors fit on routine accounts
   with 5-fold account cross-fitting (insiders: fit on all routine accounts).
Writes results/r2_t1/mole_*.csv, mole_tables.md, PDFs.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "t1_matched_budget"))
from mole_sets import CORPORA, MONITORS, load_days  # noqa: E402
from r2lib import COLORS, LABEL, gains_table, mpl_style, run_matched, suite  # noqa: E402
from t1lib import streaming_metrics  # noqa: E402

from amd.common.schema import REPO  # noqa: E402
from mole_sets import account_sets  # noqa: E402

OUT = REPO / "results" / "r2_t1"
ALPHAS = (0.10, 0.05)
SHOW = ["kth2", "kth3", "top2sum", "top3sum", "top4sum", "mean", "cusum_k0.5", "cusum_k1", "cusum_k1.5",
        "cusum_k2", "sr_d1", "eproc_power"]


def daily_ranking(D: pd.DataFrame, monitor: str, corpus: str, dets: dict, Ks=range(1, 11), seed=0):
    """R@K/day for running statistics. Population each day: routine accounts + included insiders."""
    rng = np.random.default_rng(seed)
    single = "single" in corpus
    keep = ~(D.is_insider & D.collusive) if single else np.ones(len(D), bool)
    D = D[keep].sort_values(["account", "day"])
    accts = sorted(D.account.unique())
    by = {a: g for a, g in D.groupby("account")}
    routine = [a for a in accts if not by[a].is_insider.iloc[0]]
    folds = np.array_split(rng.permutation(routine), 5)
    fold_of = {a: i for i, f in enumerate(folds) for a in f}
    rows = []
    for name, det in dets.items():
        models = [det.clone().fit([by[a][monitor].to_numpy(float) for a in routine if fold_of[a] != i])
                  for i in range(5)]
        full = det.clone().fit([by[a][monitor].to_numpy(float) for a in routine])
        paths = []
        for a in accts:
            g = by[a]
            m = models[fold_of[a]] if a in fold_of else full
            p = g[monitor].to_numpy(float) if name == "today" else m.stat_path(g[monitor].to_numpy(float))
            paths.append(pd.DataFrame({"account": a, "day": g.day.to_numpy(), "stat": p,
                                       "pos": (g.outcome == "executed").to_numpy() & g.attack_day.to_numpy()}))
        P = pd.concat(paths)
        P["stat"] = P.stat.fillna(-np.inf) + rng.uniform(0, 1e-9, len(P))  # random tie-break
        P["rank"] = P.groupby("day").stat.rank(ascending=False, method="first")
        pos = P[P.pos]
        for K in Ks:
            rows.append(dict(corpus=corpus, monitor=monitor, detector=name, K=K, recall=(pos["rank"] <= K).mean(),
                             n_pos=len(pos)))
    R = pd.DataFrame(rows)
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=int, default=50)
    ap.add_argument("--boot", type=int, default=300)
    ap.add_argument("--monitors", default=",".join(MONITORS))
    a = ap.parse_args()
    dets = suite(extra_topk=True)
    matched, gains, stream, rank = [], [], [], []
    for corpus in CORPORA:
        try:
            D = load_days(corpus)
        except FileNotFoundError:
            print(f"skip {corpus} (not built)"); continue
        for mon in a.monitors.split(","):
            if mon not in D or D[mon].isna().mean() > 0.02:
                print(f"skip {corpus}:{mon} (missing)"); continue
            D[mon] = D[mon].fillna(D[mon].median())
            for exec_only, drop in ((False, False), (True, False), (False, True)):
                ss = account_sets(corpus, mon, exec_only, D, drop_attack_days=drop)
                df, raw = run_matched(ss, detectors=dets, alphas=ALPHAS, n_splits=a.splits, n_boot=a.boot,
                                      return_raw=True, seed=0)
                matched.append(df); gains.append(gains_table(ss, raw, ALPHAS, list(dets)))
                if not exec_only and not drop:
                    sm, _ = streaming_metrics(ss, detectors={k: v for k, v in dets.items()}, alpha=0.10, n_splits=20)
                    stream.append(sm)
                print(f"  {ss.name}: n_h={ss.n_h} n_a={ss.n_a}", flush=True)
            rank.append(daily_ranking(D, mon, corpus, {k: dets[k] for k in
                                                       ["max", "kth2", "top3sum", "cusum_k0.5", "cusum_k1.5",
                                                        "cusum_k2", "sr_d1", "mean"]}))
            # today's score only (MOLE's per-day ranking, no accumulation)
            from amd.detectors import Max
            rank.append(daily_ranking(D, mon, corpus, {"today": Max()}))
    M, G, S, R = pd.concat(matched), pd.concat(gains), pd.concat(stream), pd.concat(rank)
    M.to_csv(OUT / "mole_matched.csv", index=False); G.to_csv(OUT / "mole_gains.csv", index=False)
    S.to_csv(OUT / "mole_streaming.csv", index=False); R.to_csv(OUT / "mole_daily_rank.csv", index=False)

    lines = ["# MOLE: per-account accumulation across workdays (round 2)", ""]
    for al in ALPHAS:
        sub = M[(M.alpha == al) & (M.threshold_kind == "calibrated")]
        cols = ["max"] + SHOW
        lines += [f"## TPR at account-level FPR {al} (95% CI)", "",
                  "| set | n_h/n_a | FPR(max) | " + " | ".join(LABEL.get(c, c) for c in cols) + " |",
                  "|" + "---|" * (len(cols) + 3)]
        for s, g in sub.groupby("set", sort=False):
            g = g.set_index("detector")
            best = g.loc[cols].tpr.idxmax()
            cells = [(lambda v: f"**{v}**" if c == best else v)(
                f"{g.loc[c].tpr:.2f} [{g.loc[c].tpr_lo:.2f}, {g.loc[c].tpr_hi:.2f}]") for c in cols]
            lines.append(f"| {s} | {int(g.n_honest_total.iloc[0])}/{int(g.n_attack_total.iloc[0])} | "
                         f"{g.loc['max'].fpr:.3f} | " + " | ".join(cells) + " |")
        lines.append("")
        gg = G[(G.alpha == al) & G.detector.isin(SHOW)]
        piv = gg.assign(cell=gg.apply(lambda r: f"{r.gain_vs_max:+.3f} [{r.lo:+.2f}, {r.hi:+.2f}]", axis=1))
        piv = piv.pivot(index="set", columns="detector", values="cell")[SHOW].reindex(sub.set.unique())
        lines += [f"### Paired gain over max at FPR {al}", "",
                  "| set | " + " | ".join(LABEL.get(c, c) for c in SHOW) + " |", "|" + "---|" * (len(SHOW) + 1)]
        lines += [f"| {s} | " + " | ".join(str(x) for x in r.to_numpy()) + " |" for s, r in piv.iterrows()]
        lines.append("")
    lines += ["## Streaming at account-level FPR 0.10 (delay in workdays from the first attack day)", "",
              "| set | detector | detection | early (pre-onset) | median delay | mean delay | alarm by first executed day |",
              "|---|---|---|---|---|---|---|"]
    for _, r in S[S.detector.isin(["max", "kth2", "kth3", "top3sum", "top4sum", "cusum_k1.5", "cusum_k0.5",
                                   "sr_d1"])].iterrows():
        lines.append(f"| {r.set} | {LABEL.get(r.detector, r.detector)} | {r.detection_rate:.2f} | "
                     f"{r.early_rate_among_onset:.2f} | {r.median_delay:.1f} | {r.mean_delay:.1f} | "
                     f"{r.get('before_harm_rate', np.nan):.2f} |")
    lines += ["", "## Daily review budget (MOLE metric): R@10/day and budget-AUC (mean R@K, K=1..10)", "",
              "| corpus | monitor | statistic | R@10/day | budget-AUC | n positive account-days |", "|---|---|---|---|---|---|"]
    for (c, m, d), g in R.groupby(["corpus", "monitor", "detector"], sort=False):
        lines.append(f"| {c} | {m} | {LABEL.get(d, d)} | {g[g.K == 10].recall.iloc[0]:.3f} | {g.recall.mean():.3f} | "
                     f"{g.n_pos.iloc[0]} |")
    (OUT / "mole_tables.md").write_text("\n".join(lines) + "\n")

    plt = mpl_style()
    for al in ALPHAS:
        sets = [s for s in G.set.unique() if not s.endswith((":exec", ":noattackdays"))]
        fig, axes = plt.subplots(1, len(sets), figsize=(2.2 * len(sets) + 0.8, 3.2), sharey=True, squeeze=False)
        show = ["kth2", "kth3", "top2sum", "top3sum", "top4sum", "mean", "cusum_k0.5", "cusum_k1.5", "sr_d1",
                "eproc_power"]
        for ax, s in zip(axes[0], sets):
            g = G[(G.alpha == al) & (G.set == s)].set_index("detector").loc[show]
            y = np.arange(len(show))
            ax.errorbar(g.gain_vs_max, y, xerr=[g.gain_vs_max - g.lo, g.hi - g.gain_vs_max], fmt="o", ms=4,
                        lw=1, color="#2a78d6")
            ax.axvline(0, color="#999", lw=0.8)
            ax.set_yticks(y, [LABEL[x] for x in show])
            ax.set_title(s.replace("mole:", "").replace(":", "\n"), loc="left")
            ax.set_xlabel(f"TPR gain over max\n(account FPR {al})")
        fig.tight_layout()
        fig.savefig(OUT / f"fig_mole_gain_alpha{al}.pdf")
    print((OUT / "mole_tables.md").read_text()[:8000])


if __name__ == "__main__":
    main()
