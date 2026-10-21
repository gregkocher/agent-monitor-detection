"""Round 1.1: how much do honest monitor-score distributions vary by context?

Per panel (dataset x monitor x context key):
  - variance decomposition of the honest trajectory max (raw and normal scores): ICC;
  - nested decomposition of honest per-unit scores: context / trajectory / unit;
  - realized per-context FPR under one global threshold set at 1% and 5% (in-sample, Wilson CIs),
    the spread of realized FPR, audit-spend share vs traffic share, and a logit-normal
    random-effects estimate of the between-context SD of logit FPR (net of binomial noise);
  - per-context AUROC and honest quantiles.
Also: are the same contexts "hot" for every monitor? (LinuxArena sweep, 12 monitors x 10 envs.)

    unset VIRTUAL_ENV; uv run python tracks/t2_per_context/r1_heterogeneity.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
import panels as P  # noqa: E402
import plotstyle as S  # noqa: E402
import t2lib as L  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "results" / "t2"
FIG = OUT / "figures"


def auroc(h, a):
    h, a = np.asarray(h, float), np.asarray(a, float)
    if len(h) == 0 or len(a) == 0:
        return np.nan
    r = stats.rankdata(np.concatenate([h, a]))
    return float((r[len(h):].sum() - len(a) * (len(a) + 1) / 2) / (len(h) * len(a)))


def panel_stats(df):
    name = df.attrs["name"]
    hon = df[df.label == "honest"]
    w = L.traffic(df)
    H = {c: g.stat.values for c, g in hon.groupby("ctx")}
    A = {c: g.stat.values for c, g in df[df.label == "attack"].groupby("ctx")}
    G = L.Grid(H, w)
    row = dict(panel=name, n_ctx=len(H), n_honest=len(hon), n_attack=int((df.label == "attack").sum()),
               min_n_honest=int(min(len(v) for v in H.values())),
               median_n_honest=float(np.median([len(v) for v in H.values()])),
               auroc_pooled=auroc(hon.stat, df[df.label == "attack"].stat),
               n_unique_honest=int(hon.stat.nunique()))
    vc = L.varcomp_oneway(hon.stat.values, hon.ctx.values)
    vz = L.varcomp_oneway(L.normal_scores(hon.stat.values), hon.ctx.values)
    row.update(icc_max=vc["icc"], icc_max_ns=vz["icc"], F_p=vc["p"])
    if hon.n_units.median() > 1:
        vn = L.varcomp_nested(list(hon.units.values), hon.ctx.values)
        row.update(step_share_ctx=vn["share_ctx"], step_share_traj=vn["share_traj"],
                   step_share_unit=vn["share_unit"], n_units=vn["n_units"])
    per_ctx = []
    for B in (0.01, 0.05, 0.10):
        th = L.rule_global(G, B)
        fpr = L.rates(th, H)
        n = np.array([len(H[c]) for c in H])
        x = fpr * n
        lo, hi = L.wilson(x, n)
        re = L.logitnormal_re(x, n)
        wv = np.array([w[c] for c in H])
        share = wv * fpr / (wv @ fpr)
        row.update({f"fpr_min@{B:g}": fpr.min(), f"fpr_max@{B:g}": fpr.max(),
                    f"fpr_max_over_B@{B:g}": fpr.max() / B,
                    f"n_ctx_ci_excl_B@{B:g}": int(((lo > B) | (hi < B)).sum()),
                    f"tau_logit@{B:g}": re["tau"], f"tau_p@{B:g}": re["p"],
                    f"re_fpr_p10@{B:g}": re["fpr_p10"], f"re_fpr_p90@{B:g}": re["fpr_p90"],
                    f"spend_tv@{B:g}": 0.5 * np.abs(share - wv).sum(),
                    f"max_spend_over_traffic@{B:g}": float((share / wv).max())})
        for i, c in enumerate(H):
            per_ctx.append(dict(panel=name, ctx=c, B=B, n_honest=int(n[i]), n_attack=len(A.get(c, [])),
                                fpr=fpr[i], fpr_lo=lo[i], fpr_hi=hi[i], traffic=wv[i], spend_share=share[i],
                                h=th[c].h, med=np.median(H[c]), p90=np.quantile(H[c], 0.9),
                                p99=np.quantile(H[c], 0.99), mean=np.mean(H[c]),
                                auroc=auroc(H[c], A.get(c, []))))
    row["eb_n0"] = L.eb_n0(G, 0.05)
    return row, per_ctx


def monitor_consistency(names):
    """Env effects per monitor (mean normal score of honest max within monitor); correlation of
    env effects across monitors and the share of env x monitor variance that is a common env
    effect."""
    eff, noise = {}, []
    for n in names:
        df = P.load(n)
        hon = df[df.label == "honest"].copy()
        hon["z"] = L.normal_scores(hon.stat.values)
        eff[n.replace("lasweep_", "")] = hon.groupby("ctx").z.mean()
        g = hon.groupby("ctx").z
        noise.append(float((g.var(ddof=1) / g.size()).mean()))
    M = pd.DataFrame(eff)  # env x monitor
    Mc = M - M.mean(axis=0)
    env_main = Mc.mean(axis=1)
    resid = Mc.sub(env_main, axis=0)
    # sampling-noise floor: average squared standard error of a cell mean
    noise = float(np.mean(noise))
    var_main = env_main.var(ddof=1) - noise / M.shape[1]
    var_int = (resid ** 2).values.sum() / ((M.shape[0] - 1) * (M.shape[1] - 1)) - noise
    rho = M.corr(method="spearman").values
    iu = np.triu_indices_from(rho, 1)
    return M, dict(mean_pairwise_spearman=float(np.mean(rho[iu])),
                   min_pairwise_spearman=float(np.min(rho[iu])),
                   var_env_main=float(var_main), var_env_x_monitor=float(max(var_int, 0)),
                   noise_per_cell=noise,
                   share_common=float(var_main / (var_main + max(var_int, 0))))


def fig_forest(per_ctx, panels, B, path):
    S.setup()
    import matplotlib.pyplot as plt
    k = len(panels)
    fig, axes = plt.subplots(1, k, figsize=(2.35 * k, 2.9), sharey=False)
    for ax, (pn, title) in zip(np.atleast_1d(axes), panels):
        d = per_ctx[(per_ctx.panel == pn) & (per_ctx.B == B)].sort_values("fpr")
        y = np.arange(len(d))
        ax.errorbar(d.fpr * 100, y, xerr=[np.clip(d.fpr - d.fpr_lo, 0, None) * 100,
                                          np.clip(d.fpr_hi - d.fpr, 0, None) * 100],
                    fmt="o", color=S.SERIES[0], ecolor=S.INK2, elinewidth=0.8, capsize=0, ms=4)
        ax.axvline(B * 100, color=S.SERIES[7], lw=1, ls="--")
        ax.set_yticks(y)
        ax.set_yticklabels([str(c)[:22] for c in d.ctx], fontsize=6.5)
        ax.set_xlabel(f"realized FPR (%) at global {B:.0%} threshold")
        ax.set_title(title)
        ax.grid(axis="y", visible=False)
    fig.tight_layout()
    S.save(fig, path)


def fig_quantiles(per_ctx, pn, title, path):
    S.setup()
    import matplotlib.pyplot as plt
    df = P.load(pn)
    hon = df[df.label == "honest"]
    order = hon.groupby("ctx").stat.quantile(0.9).sort_values().index
    fig, ax = plt.subplots(figsize=(4.6, 2.8))
    for i, c in enumerate(order):
        v = hon[hon.ctx == c].stat.values
        qs = np.quantile(v, [0.5, 0.75, 0.9, 0.95, 0.99])
        ax.plot([qs[0], qs[-1]], [i, i], color=S.GRID, lw=3, solid_capstyle="round")
        for q, m, col in zip(qs, ["o", "s", "D", "^", "v"], S.SERIES[:5]):
            ax.plot(q, i, m, color=col, ms=4.5, mec="white", mew=0.6)
    for m, col, lab in zip(["o", "s", "D", "^", "v"], S.SERIES[:5], ["p50", "p75", "p90", "p95", "p99"]):
        ax.plot([], [], m, color=col, label=lab)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([str(c)[:24] for c in order], fontsize=6.5)
    ax.set_xlabel("honest trajectory max score")
    ax.set_title(title)
    ax.legend(ncol=5, loc="lower center", bbox_to_anchor=(0.5, 1.08), fontsize=6.5, handletextpad=0.2)
    ax.grid(axis="y", visible=False)
    S.save(fig, path)


def fig_roc(pn, title, path):
    """Per-context ROC (logit-logit) from all data, to show context-dependent detectability."""
    S.setup()
    import matplotlib.pyplot as plt
    from scipy.special import logit
    df = P.load(pn)
    fig, ax = plt.subplots(figsize=(3.6, 3.0))
    ctxs = sorted(df.ctx.unique())
    for i, c in enumerate(ctxs):
        g = df[df.ctx == c]
        cur = L.hulls({c: g[g.label == "honest"].stat.values}, {c: g[g.label == "attack"].stat.values})[c]
        f, t, _ = cur
        m = (f > 0) & (f < 1) & (t > 0) & (t < 1)
        col = S.SERIES[i % 8] if len(ctxs) <= 8 else S.INK2
        ax.plot(logit(f[m]), logit(t[m]), "-o", ms=2.5, lw=1, color=col, alpha=0.9 if len(ctxs) <= 8 else 0.5,
                label=str(c)[:18] if len(ctxs) <= 8 else None)
    ticks = [0.005, 0.01, 0.05, 0.2, 0.5]
    ax.set_xticks(logit(ticks))
    ax.set_xticklabels([f"{x:g}" for x in ticks])
    tt = [0.2, 0.5, 0.8, 0.95, 0.99]
    ax.set_yticks(logit(tt))
    ax.set_yticklabels([f"{x:g}" for x in tt])
    ax.set_xlabel("FPR (logit scale)")
    ax.set_ylabel("TPR (logit scale)")
    ax.set_title(title)
    if len(ctxs) <= 8:
        ax.legend(fontsize=6, loc="lower right")
    S.save(fig, path)


def fig_monitor_heatmap(M, path):
    S.setup()
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    Mc = M - M.mean(axis=0)
    Mc = Mc.loc[Mc.mean(axis=1).sort_values().index]
    order = M.columns[np.argsort(-M.std(axis=0).values)]
    Mc = Mc[order]
    cmap = LinearSegmentedColormap.from_list("div", ["#2a78d6", "#f2f1ed", "#e34948"])
    fig, ax = plt.subplots(figsize=(5.4, 3.0))
    v = np.abs(Mc.values).max()
    im = ax.imshow(Mc.values, cmap=cmap, vmin=-v, vmax=v, aspect="auto")
    ax.set_xticks(range(Mc.shape[1]))
    ax.set_xticklabels(Mc.columns, rotation=45, ha="right", fontsize=6.5)
    ax.set_yticks(range(Mc.shape[0]))
    ax.set_yticklabels(Mc.index, fontsize=6.5)
    ax.grid(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.85)
    cb.set_label("env effect (mean normal score of honest max)", fontsize=6.5)
    ax.set_title("LinuxArena sweep: honest env effects by monitor")
    S.save(fig, path)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = [n for n in P.available() if not n.startswith("mb_clusters")]
    rows, per = [], []
    for n in names:
        r, pc = panel_stats(P.load(n))
        rows.append(r)
        per += pc
        print(f"{n:45s} icc={r['icc_max']:.3f} tau@1%={r['tau_logit@0.01']:.2f} "
              f"tau@5%={r['tau_logit@0.05']:.2f} fprmax/B@1%={r['fpr_max_over_B@0.01']:.1f}", flush=True)
    het = pd.DataFrame(rows)
    per = pd.DataFrame(per)
    het.to_csv(OUT / "heterogeneity.csv", index=False, float_format="%.4g")
    per.to_csv(OUT / "context_fpr_global.csv", index=False, float_format="%.4g")
    las = [n for n in names if n.startswith("lasweep_")]
    M, cons = monitor_consistency(las)
    M.to_csv(OUT / "lasweep_env_effects.csv", float_format="%.4g")
    pd.Series(cons).to_csv(OUT / "lasweep_monitor_consistency.csv", header=["value"], float_format="%.4g")
    print(cons)
    main_panels = [("la_env_local", "LinuxArena env (Gemini)"), ("akshn_setting", "Setting (Gemini)"),
                   ("ca_setting_model", "ControlArena setting/agent"),
                   ("mb_gpt-4.1-nano_trajectory", "BashArena cluster (nano)")]
    main_panels = [p for p in main_panels if p[0] in names]
    for B in (0.01, 0.05):
        fig_forest(per, main_panels, B, FIG / f"r1_forest_global_{int(B * 100)}pct.pdf")
    fig_quantiles(per, "la_env_local", "LinuxArena goldset, Gemini-3.1-Pro local: honest max by env",
                  FIG / "r1_quantiles_la_env.pdf")
    fig_quantiles(per, "akshn_setting", "Gemini-3.1-Pro (same rubric): honest max by setting",
                  FIG / "r1_quantiles_setting.pdf")
    fig_roc("akshn_setting", "Per-setting ROC (Gemini-3.1-Pro)", FIG / "r1_roc_setting.pdf")
    if "mb_gpt-4.1-nano_trajectory" in names:
        fig_roc("mb_gpt-4.1-nano_trajectory", "Per-cluster ROC (gpt-4.1-nano, BashArena)",
                FIG / "r1_roc_mb_nano.pdf")
    fig_monitor_heatmap(M, FIG / "r1_lasweep_env_by_monitor.pdf")


if __name__ == "__main__":
    main()
