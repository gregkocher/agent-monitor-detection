"""Round 4: does the accumulation gain track repeat-spike informativeness? Dependence-aware tests (audit2 A3 fix).

    unset VIRTUAL_ENV; uv run python tracks/r4_cs/mechanism.py [--boot 1000]

A3 (results/audit2/issues.csv): the round-3 Spearman +0.30 (p = 0.017) treated 64 dependent corpus x monitor cells
as independent, and computed the repeat-spike LR from the same insider streams that define the gain.

PRE-SPECIFIED:
  Primary (persistent state, identical-input monitors; unit = monitor, k = 9):
    y_m = TPR(whitened top-3 sum) − TPR(max) at run-level FPR 0.05 on gradual attacks of apps Q;
    x_m = repeat-spike log-LR (chooser.spike_features definition) from gradual attacks of the OTHER apps P
          (cross-fitting: no attack run enters both x and y); honest runs define the spike threshold and h2c.
    rho = Spearman(x, y) across monitors, averaged over all 20 app partitions (|P| = 2 or 3).
    CI: joint bootstrap, app-clustered (iid run bootstrap as sensitivity), every replicate re-weights the SAME runs
    for x, y and every monitor (the weights amd.evaluation.paired draws), so between-monitor dependence through
    shared runs is kept. Non-cross-fitted rho reported for comparison.
  Descriptive (all cells: persistent-state monitors + MOLE round-3 primary monitors + MOLE round-4 GPT-6 Luna):
    Spearman of the top-3-sum / 3rd-max gain vs repeat-spike log-LR with corpus-cluster, monitor-cluster and
    two-way (corpus x monitor) cluster bootstrap intervals; derived monitors (account-centered copies, the
    activity baseline) excluded.
Outputs: results/r4_cs/mechanism_ps.csv, mechanism_cells.csv, mechanism_pooled.csv, mechanism.md,
fig_mechanism.pdf.
"""
from __future__ import annotations

import argparse
import itertools
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from r4lib import (OUT, md, RAW, app_groups, common_sets, mpl, ps_monitor_streams, rep_lr_weighted,  # noqa: E402
                   shared_weights, spike_counts)

from amd.common.schema import REPO  # noqa: E402
from amd.evaluation.paired import paired_contrast_bootstrap  # noqa: E402

SEED = 31
ALPHA = 0.05


def _spearman_rows(X, Y):
    """Row-wise Spearman between matrices X, Y of shape (B, k)."""
    rx = np.apply_along_axis(rankdata, 1, X)
    ry = np.apply_along_axis(rankdata, 1, Y)
    rx -= rx.mean(1, keepdims=True); ry -= ry.mean(1, keepdims=True)
    return (rx * ry).sum(1) / np.sqrt((rx**2).sum(1) * (ry**2).sum(1))


def ps_mechanism(boot):
    mons = ps_monitor_streams()
    pool = [m for m in mons if mons[m]["identical"]]
    S, _ = common_sets(mons, policies=("gradual",))
    S = {m: S[m]["gradual"] for m in pool}
    d = pickle.loads((RAW / "ps_raws.pkl").read_bytes())
    raws = d["raws"]
    ss0 = S[pool[0]]
    hg, ag = app_groups(ss0)
    apps = np.unique(ag)
    parts = []
    for r in (2, 3):
        for P in itertools.combinations(apps, r):
            parts.append((np.isin(ag, P), ~np.isin(ag, P)))
    counts = {m: spike_counts(S[m].honest, S[m].attack) for m in pool}
    rows, out = [], {}
    for clus in ("app", "iid"):
        Wh, Wa = shared_weights(ss0.n_h, ss0.n_a, boot, SEED, hg if clus == "app" else None,
                                ag if clus == "app" else None)
        rho_pt, rho_b = [], []
        for P, Q in parts:
            X = np.zeros((boot, len(pool))); Y = np.zeros((boot, len(pool)))
            x0, y0 = np.zeros(len(pool)), np.zeros(len(pool))
            for j, m in enumerate(pool):
                ch, ca = counts[m]
                x0[j] = rep_lr_weighted(ch, ca[P])
                X[:, j] = rep_lr_weighted(ch[None, :], ca[P][None, :], Wh, Wa[:, P])
                r = paired_contrast_bootstrap([(1, raws[("main", m)], "top3sum"), (-1, raws[("main", m)], "max")],
                                              n_honest=ss0.n_h, n_attack=ss0.n_a, alpha=ALPHA,
                                              honest_groups=hg if clus == "app" else None,
                                              attack_groups=ag if clus == "app" else None, attack_mask=Q,
                                              n_boot=boot, seed=SEED, return_boot=True)
                y0[j], Y[:, j] = r["est"], r["boot"]
            rho_pt.append(spearmanr(x0, y0).statistic)
            rho_b.append(_spearman_rows(X, Y))
            if clus == "app":
                for j, m in enumerate(pool):
                    rows.append(dict(partition=len(rho_pt) - 1, monitor=m, x_rep_lr_P=x0[j], y_gain_Q=y0[j]))
        rb = np.nanmean(np.vstack(rho_b), axis=0)
        # non-cross-fitted: x and y on all attacks
        xa = np.array([rep_lr_weighted(*counts[m]) for m in pool])
        Xa = np.column_stack([rep_lr_weighted(counts[m][0][None, :], counts[m][1][None, :], Wh, Wa) for m in pool])
        ya, Ya = [], []
        for m in pool:
            r = paired_contrast_bootstrap([(1, raws[("main", m)], "top3sum"), (-1, raws[("main", m)], "max")],
                                          n_honest=ss0.n_h, n_attack=ss0.n_a, alpha=ALPHA,
                                          honest_groups=hg if clus == "app" else None,
                                          attack_groups=ag if clus == "app" else None, n_boot=boot, seed=SEED,
                                          return_boot=True)
            ya.append(r["est"]); Ya.append(r["boot"])
        rna_b = _spearman_rows(Xa, np.column_stack(Ya))
        out[clus] = dict(rho_crossfit=float(np.nanmean(rho_pt)), lo=float(np.nanquantile(rb, .025)),
                         hi=float(np.nanquantile(rb, .975)), p_le0=float(np.nanmean(rb <= 0)),
                         rho_full=float(spearmanr(xa, ya).statistic), full_lo=float(np.nanquantile(rna_b, .025)),
                         full_hi=float(np.nanquantile(rna_b, .975)), k=len(pool), n_partitions=len(parts))
        if clus == "app":
            full = pd.DataFrame(dict(monitor=pool, rep_lr=xa, gain_top3=ya,
                                     h2c=[((counts[m][0] >= 2).sum() + .5) / ((counts[m][0] >= 1).sum() + 1) for m in pool]))
    return pd.DataFrame(rows), out, full


def pooled_cells(ps_full):
    cells = []
    for r in ps_full.itertuples():
        cells.append(dict(corpus="persistent_state", monitor=r.monitor, rep_lr=r.rep_lr, gain_top3=r.gain_top3,
                          gain_kth3=np.nan, source="r4 PS"))
    G = pd.read_csv(OUT / "ps_gains.csv")
    g3 = G[(G.variant == "main") & (G.alpha == ALPHA) & (G.detector == "kth3") & (G.cluster == "app")].set_index("monitor").est
    for c in cells:
        c["gain_kth3"] = g3.get(c["monitor"], np.nan)
    F3 = pd.read_csv(REPO / "results" / "r3_t1" / "mole_features.csv")
    G3 = pd.read_csv(REPO / "results" / "r3_t1" / "mole_gains.csv")
    G3 = G3[(G3.alpha == 0.1) & (G3["set"] == "mole:" + G3.corpus + ":" + G3.monitor)]
    prim3 = ["qwen_int", "qwen_lp", "mini_full", "z_score", "peer_fit"]
    for f in F3[F3.monitor.isin(prim3)].itertuples():
        g = G3[(G3.corpus == f.corpus) & (G3.monitor == f.monitor)].set_index("detector").gain_vs_max
        cells.append(dict(corpus=f.corpus, monitor=f.monitor, rep_lr=f.rep_lr, gain_top3=g.get("top3sum", np.nan),
                          gain_kth3=g.get("kth3", np.nan), source="r3 MOLE"))
    p4 = OUT / "mole_features.csv"
    if p4.exists():
        F4 = pd.read_csv(p4)
        G4 = pd.read_csv(OUT / "mole_gains.csv")
        G4 = G4[(G4.alpha == 0.1) & ~G4.drop_attack_days]
        for f in F4[(F4.monitor == "luna") & ~F4.corpus.str.contains(":sub")].itertuples():
            g = G4[(G4.corpus == f.corpus) & (G4.monitor == f.monitor)].set_index("detector").est
            cells.append(dict(corpus=f.corpus, monitor="gpt-6-luna", rep_lr=f.rep_lr, gain_top3=g.get("top3sum", np.nan),
                              gain_kth3=g.get("kth3", np.nan), source="r4 MOLE"))
    C = pd.DataFrame(cells)
    # monitor identity across corpora (gpt-4.1-mini is the same model on PS and MOLE)
    C["monitor_id"] = C.monitor.replace({"mini_full": "gpt-4.1-mini", "qwen_int": "qwen3-235b", "qwen_lp": "qwen3-235b"})
    return C


def cluster_rho(C, y, B=4000, seed=0):
    rng = np.random.default_rng(seed)
    x = C.dropna(subset=[y])
    rho = spearmanr(x.rep_lr, x[y]).statistic
    corp, mon = x.corpus.unique(), x.monitor_id.unique()
    res = {"rho": rho, "n_cells": len(x), "n_corpora": len(corp), "n_monitors": len(mon)}
    for kind in ("corpus", "monitor", "twoway"):
        bs = []
        for _ in range(B):
            wc = pd.Series(np.bincount(rng.integers(len(corp), size=len(corp)), minlength=len(corp)), index=corp)
            wm = pd.Series(np.bincount(rng.integers(len(mon), size=len(mon)), minlength=len(mon)), index=mon)
            if kind == "corpus":
                w = x.corpus.map(wc)
            elif kind == "monitor":
                w = x.monitor_id.map(wm)
            else:
                w = x.corpus.map(wc) * x.monitor_id.map(wm)
            rep = x.loc[x.index.repeat(w.to_numpy().astype(int))]
            if len(rep) < 4 or rep.rep_lr.nunique() < 2 or rep[y].nunique() < 2:
                continue
            bs.append(spearmanr(rep.rep_lr, rep[y]).statistic)
        res[f"{kind}_lo"], res[f"{kind}_hi"] = np.nanquantile(bs, .025), np.nanquantile(bs, .975)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=1000)
    a = ap.parse_args()
    rows, out, full = ps_mechanism(a.boot)
    rows.to_csv(OUT / "mechanism_ps.csv", index=False)
    full.to_csv(OUT / "mechanism_ps_full.csv", index=False)
    C = pooled_cells(full)
    C.to_csv(OUT / "mechanism_cells.csv", index=False)
    pr = []
    for y in ("gain_top3", "gain_kth3"):
        r = cluster_rho(C, y)
        r["gain"] = y
        pr.append(r)
        sub = C[C.source != "r4 PS"]
        r2 = cluster_rho(sub, y)
        r2["gain"] = y + " (MOLE cells only)"
        pr.append(r2)
    P = pd.DataFrame(pr)
    P.to_csv(OUT / "mechanism_pooled.csv", index=False)
    L = ["# Round 4: accumulation gain vs repeat-spike informativeness (dependence-aware)", "",
         "## Primary: persistent state, identical-input monitors (cross-fitted by app halves)", "",
         "| bootstrap | k monitors | cross-fitted Spearman (mean over 20 app partitions) | 95% CI | p(≤0) | non-cross-fitted Spearman [CI] |",
         "|---|---|---|---|---|---|"]
    for clus, o in out.items():
        L.append(f"| {clus} | {o['k']} | {o['rho_crossfit']:+.3f} | [{o['lo']:+.3f}, {o['hi']:+.3f}] | {o['p_le0']:.3f} | "
                 f"{o['rho_full']:+.3f} [{o['full_lo']:+.3f}, {o['full_hi']:+.3f}] |")
    L += ["", "Per-monitor values (all gradual attacks):", "", md(full.round(3)), "",
          "## Descriptive: all corpus x monitor cells (PS + MOLE r3 primary monitors + MOLE r4 Luna)", "",
          "| gain | cells | corpora | monitors | Spearman | corpus-cluster CI | monitor-cluster CI | two-way CI |", "|---|---|---|---|---|---|---|---|"]
    for r in P.itertuples():
        L.append(f"| {r.gain} | {r.n_cells} | {r.n_corpora} | {r.n_monitors} | {r.rho:+.3f} | [{r.corpus_lo:+.2f}, {r.corpus_hi:+.2f}] | "
                 f"[{r.monitor_lo:+.2f}, {r.monitor_hi:+.2f}] | [{r.twoway_lo:+.2f}, {r.twoway_hi:+.2f}] |")
    (OUT / "mechanism.md").write_text("\n".join(L) + "\n")
    print("\n".join(L), flush=True)
    plt = mpl()
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    mk = {"r4 PS": ("o", "#1baf7a"), "r3 MOLE": ("s", "#2a78d6"), "r4 MOLE": ("D", "#eb6834")}
    for src, g in C.groupby("source"):
        ax.scatter(g.rep_lr, g.gain_top3, marker=mk[src][0], color=mk[src][1], s=22, label=src, edgecolors="white", lw=0.4)
    for r in C[C.source == "r4 PS"].itertuples():
        ax.annotate(r.monitor, (r.rep_lr, r.gain_top3), fontsize=6, xytext=(3, 2), textcoords="offset points")
    ax.axhline(0, color="#4a4a4a", lw=0.6)
    ax.set_xlabel("repeat-spike log-LR (attack vs honest)")
    ax.set_ylabel("TPR(top-3 sum) − TPR(max)")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_mechanism.pdf")


if __name__ == "__main__":
    main()
