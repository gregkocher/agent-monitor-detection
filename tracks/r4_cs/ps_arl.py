"""Round 4, goal 3: long unreset PR streams. CUSUM vs max at matched ARL0 with bootstrap CIs, and a robust /
forgetting family (CUSUM k-grid, EWMA, windowed top-k, Shiryaev-Roberts).

    unset VIRTUAL_ENV; uv run python tracks/r4_cs/ps_arl.py [--boot 200] [--splits 10] [--workers 8]

Deployment model (as round 3, tracks/t1_matched_budget/t1lib.matched_arl): one monitor watches an unbounded stream of
runs; an attack run arrives after U{0..4} honest test runs with no reset of the statistic. Each detector's threshold
gives the same long-run false-alarm rate on honest streams, ARL0 = 5 / alpha PRs (100 and 500), estimated by
simulating 300 concatenations of random honest CALIBRATION runs (first-passage times, censored-exponential MLE),
smallest threshold with ARL0 >= target (bisection on a continuous threshold). Realized ARL0 on held-out honest TEST
runs is reported. Raw scores get a 1e-6 uniform jitter (fixed seed) before anything, so integer-score monitors have
randomized ties (the analogue of randomized thresholds) and no detector is favoured by tie discreteness.
Outcome (as round 3): detection = first alarm inside the attack run, given no alarm in the honest prefix (20 prefix
draws per attack, ratio estimator); prefix false-alarm rate and the unconditional rate are also reported.

PRE-SPECIFIED:
  Primary   (P3a) CUSUM k=0.5 − max at ARL0 = 100 PRs, history-free gpt-4.1-mini, gradual attacks (the round-3
            claim 0.71 vs 0.58, now with CIs); (P3b) windowed top-3 sum (W = 5 PRs, whitened) − max, same cell.
  Pooled    random-effects mean of (P3a) and (P3b) contrasts across the identical-input monitors, interval from the
            joint bootstrap (same resampled runs for every monitor in a replicate).
  Nested    "best forgetting rule": pick the family member with the highest detection on attacks from a random
            2- or 3-app half (selection), evaluate it and max on the other apps; both directions, averaged.
  Secondary ARL0 = 500; every other family member (exploratory).
  Inference point estimate = mean over 10 random calibration / test splits of the original runs; CI = percentile
            of B = 200 bootstrap replicates of the whole procedure (honest runs resampled iid, split by original run
            so copies stay on one side; attacks resampled iid). App-cluster bootstrap (resample the 5 apps) =
            sensitivity for the primary contrasts.
Outputs: results/r4_cs/arl_rates.csv, arl_contrasts.csv, arl_meta.csv, arl_tables.md, fig_arl.pdf.
"""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from r4lib import OUT, common_sets, mpl, ps_monitor_streams, re_pool  # noqa: E402

from amd.detectors import CUSUM, Max, ShiryaevRoberts, Whiten  # noqa: E402
from amd.detectors.base import Detector, pack  # noqa: E402

PRIMARY = ("cusum_k0.5", "wtop3_w5")
N_SIMS, R_PREFIX, MAX_PREFIX = 300, 20, 4


class EWMA(Detector):
    """E_t = (1 - lam) E_{t-1} + lam u_t, E_0 = 0 (on whitened scores)."""
    empty_value = 0.0

    def __init__(self, lam=0.2, transform="whiten"):
        super().__init__(Whiten() if transform == "whiten" else transform)
        self.lam = lam
        self.name = f"ewma_l{lam:g}"

    def _agg(self, U, lengths):
        n, T = U.shape
        out = np.empty((n, T))
        E = np.zeros(n)
        for t in range(T):
            E = (1 - self.lam) * E + self.lam * U[:, t]
            out[:, t] = E
        return out


class WindowTopK(Detector):
    """Sum of the k largest units among the last W units (missing slots count 0)."""
    empty_value = 0.0

    def __init__(self, W=5, k=3, transform="whiten"):
        super().__init__(Whiten() if transform == "whiten" else transform)
        self.W, self.k = W, k
        self.name = f"wtop{k}_w{W}"

    def _agg(self, U, lengths):
        n, T = U.shape
        pad = np.concatenate([np.full((n, self.W - 1), -np.inf), U], axis=1)
        win = np.lib.stride_tricks.sliding_window_view(pad, self.W, axis=1)   # (n, T, W)
        top = -np.sort(-win, axis=2)[:, :, : self.k]
        return np.where(np.isfinite(top), top, 0.0).sum(axis=2)


def detectors():
    d = [Max()] + [CUSUM(k=k, transform=Whiten()) for k in (0.25, 0.5, 1.0, 1.5, 2.0)] + \
        [EWMA(lam) for lam in (0.1, 0.2, 0.3, 0.5)] + [WindowTopK(W, k) for W, k in ((5, 2), (5, 3), (10, 3))] + \
        [ShiryaevRoberts(delta=1.0, transform=Whiten())]
    return {x.name: x for x in d}


FAMILY = [n for n in detectors() if n != "max"]


def _paths(det, streams):
    P = pack(streams)
    return det.paths_packed(P), P.lengths


def _sim_runmax(det, pool, L, rng):
    """Running max of the statistic path over N_SIMS concatenations of random pool runs (length L units)."""
    lens = np.array([len(s) for s in pool])
    rows = []
    for _ in range(N_SIMS):
        idx, tot = [], 0
        while tot < L:
            i = int(rng.integers(len(pool)))
            idx.append(i); tot += lens[i]
        rows.append(np.concatenate([pool[i] for i in idx])[:L])
    paths, _ = _paths(det, rows)
    return np.maximum.accumulate(paths, axis=1)


def _arl(M, h):
    hit = M > h
    alarmed = hit.any(axis=1)
    rl = np.where(alarmed, hit.argmax(axis=1) + 1, M.shape[1])
    return rl.sum() / max(alarmed.sum(), 1e-9)


def _threshold(M, target):
    lo, hi = np.min(M), np.max(M) + 1e-9
    if _arl(M, hi) < target:      # never reached: alarm-free
        return hi
    for _ in range(40):
        mid = (lo + hi) / 2
        if _arl(M, mid) >= target:
            hi = mid
        else:
            lo = mid
    return hi


def evaluate(cal, test, attack, attack_app, alphas, seed):
    """One calibration / evaluation pass. Returns rows per (alpha, detector) with per-attack arrays."""
    rng = np.random.default_rng(seed)
    dets = detectors()
    n_a = len(attack)
    pre = [[np.concatenate([test[j] for j in rng.integers(len(test), size=k)]) if k else np.array([])
            for k in rng.integers(0, MAX_PREFIX + 1, size=R_PREFIX)] for _ in range(n_a)]
    longs = [np.r_[p, a] for i, a in enumerate(attack) for p in pre[i]]
    offs = np.array([len(p) for i in range(n_a) for p in pre[i]])
    ends = offs + np.repeat([len(a) for a in attack], R_PREFIX)
    mean_len = np.mean([len(s) for s in cal])
    out = {}
    for name, det in dets.items():
        d = det.clone().fit(cal)
        Mpaths, _ = _paths(d, longs)
        Mrun = np.maximum.accumulate(Mpaths, axis=1)
        for al in alphas:
            target = mean_len / al
            L = int(4 * target)
            M = _sim_runmax(d, cal, L, np.random.default_rng(seed + 7))
            h = _threshold(M, target)
            Mt = _sim_runmax(d, test, L, np.random.default_rng(seed + 8))
            T = Mrun.shape[1]
            first = np.where((Mrun > h).any(axis=1), (Mrun > h).argmax(axis=1), T + 10)
            pre_alarm = first < offs
            det_in = (first >= offs) & (first < ends)
            ok = (~pre_alarm).reshape(n_a, R_PREFIX)
            dd = det_in.reshape(n_a, R_PREFIX)
            out[(al, name)] = dict(det=dd.sum(1).astype(float), ok=ok.sum(1).astype(float),
                                   pre=(pre_alarm.reshape(n_a, R_PREFIX) & (offs.reshape(n_a, R_PREFIX) > 0)).sum(1).astype(float),
                                   npre=(offs.reshape(n_a, R_PREFIX) > 0).sum(1).astype(float),
                                   h=h, arl0_cal=_arl(M, h), arl0_test=_arl(Mt, h))
    return out


def summarize(res, alphas, w=None, app=None, nested_seed=0):
    """Rates and contrasts from one evaluate() output; w = attack weights (bootstrap)."""
    rows = {}
    for (al, name), r in res.items():
        ww = np.ones_like(r["det"]) if w is None else w
        rows[(al, name)] = dict(det=(ww * r["det"]).sum() / max((ww * r["ok"]).sum(), 1e-9),
                                uncond=(ww * r["det"]).sum() / (ww.sum() * R_PREFIX),
                                prefix_fa=(ww * r["pre"]).sum() / max((ww * r["npre"]).sum(), 1e-9),
                                arl0_cal=r["arl0_cal"], arl0_test=r["arl0_test"])
    # nested best forgetting rule (selection on one app half, evaluation on the other)
    if app is not None:
        rng = np.random.default_rng(nested_seed)
        apps = np.unique(app)
        for al in alphas:
            gains = []
            for _ in range(5):
                perm = rng.permutation(apps)
                m = int(rng.integers(2, 4))
                for A_, B_ in ((perm[:m], perm[m:]), (perm[m:], perm[:m])):
                    ma, mb = np.isin(app, A_), np.isin(app, B_)
                    ww = np.ones(len(app)) if w is None else w

                    def rate(name, msk):
                        r = res[(al, name)]
                        return (ww * r["det"] * msk).sum() / max((ww * r["ok"] * msk).sum(), 1e-9)
                    pick = max(FAMILY, key=lambda n: rate(n, ma))
                    gains.append(rate(pick, mb) - rate("max", mb))
            rows[(al, "nested_best_forgetting")] = dict(det=np.nan, contrast=float(np.mean(gains)))
    return rows


def _rep(args):
    """One bootstrap replicate (b >= 0) or one point-estimate split (b < 0) for every monitor."""
    b, data, alphas, mode = args
    rng = np.random.default_rng(1000 + b if b >= 0 else 10 + (-b))
    n_h, n_a = len(data["hid"]), len(data["aapp"])
    if b < 0:
        hi_idx, ai_idx = np.arange(n_h), np.arange(n_a)
    elif mode == "iid":
        hi_idx, ai_idx = rng.integers(n_h, size=n_h), rng.integers(n_a, size=n_a)
    else:   # app cluster: resample apps, take every honest / attack run of each drawn app
        apps = np.unique(data["happ"])
        pick = rng.choice(apps, len(apps))
        hi_idx = np.concatenate([np.flatnonzero(data["happ"] == a) for a in pick])
        ai_idx = np.concatenate([np.flatnonzero(data["aapp"] == a) for a in pick])
    uniq = np.unique(hi_idx)
    cal_u = set(rng.permutation(uniq)[: len(uniq) // 2])
    cal_i = [i for i in hi_idx if i in cal_u]
    test_i = [i for i in hi_idx if i not in cal_u]
    out = {}
    for mon, S in data["streams"].items():
        cal = [S["H"][i] for i in cal_i]
        test = [S["H"][i] for i in test_i]
        att = [S["A"][i] for i in ai_idx]
        res = evaluate(cal, test, att, data["aapp"][ai_idx], alphas, seed=int(rng.integers(1 << 30)))
        out[mon] = summarize(res, alphas, app=data["aapp"][ai_idx], nested_seed=b + 5000)
    return b, out


def jitter(s, key):
    import hashlib
    r = np.random.default_rng(int(hashlib.sha256(repr(key).encode()).hexdigest()[:8], 16))
    return s + 1e-6 * r.random(len(s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=200)
    ap.add_argument("--boot-app", type=int, default=200)
    ap.add_argument("--splits", type=int, default=10)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--alphas", default="0.05,0.01")
    ap.add_argument("--monitors", default="")
    a = ap.parse_args()
    alphas = tuple(float(x) for x in a.alphas.split(","))
    mons = ps_monitor_streams()
    if a.monitors:
        mons = {k: v for k, v in mons.items() if k in a.monitors.split(",")}
    S, ids = common_sets(ps_monitor_streams(), policies=("gradual",))
    S = {k: v["gradual"] for k, v in S.items() if k in mons}
    ss0 = next(iter(S.values()))
    data = dict(hid=ss0.honest_ids, happ=np.array([m["app"] for m in ss0.honest_meta]),
                aapp=np.array([m["app"] for m in ss0.attack_meta]),
                streams={m: dict(H=[jitter(s, (m, i)) for s, i in zip(ss.honest, ss.honest_ids)],
                                 A=[jitter(s, (m, i)) for s, i in zip(ss.attack, ss.attack_ids)])
                         for m, ss in S.items()})
    print(f"{len(S)} monitors, {len(data['hid'])} honest / {len(data['aapp'])} gradual runs", flush=True)
    jobs = [(-(s + 1), data, alphas, "point") for s in range(a.splits)] + \
           [(b, data, alphas, "iid") for b in range(a.boot)] + \
           [(10000 + b, data, (alphas[0],), "app") for b in range(a.boot_app)]
    recs = []
    with ProcessPoolExecutor(a.workers) as ex:
        for k, (b, out) in enumerate(ex.map(_rep, jobs, chunksize=1)):
            kind = "point" if b < 0 else ("iid" if b < 10000 else "app")
            for mon, rows in out.items():
                for (al, det), r in rows.items():
                    recs.append(dict(kind=kind, rep=b, monitor=mon, alpha=al, detector=det, **r))
            if k % 20 == 0:
                print(f"  {k + 1}/{len(jobs)} done", flush=True)
    R = pd.DataFrame(recs)
    R.to_csv(OUT / "arl_replicates.csv.gz", index=False, compression="gzip")
    analyse(R, list(S), mons)


def fa(x):
    """Realized ARL0 for display; a pool with no alarm in 300 x 4*target units is shown as '> 4e4' style."""
    return f"{x:.0f}" if x < 1e6 else "no alarm"


def analyse(R, monitors, mons):
    rates, cons = [], []
    for (mon, al, det), g in R[R.detector != "nested_best_forgetting"].groupby(["monitor", "alpha", "detector"]):
        p = g[g.kind == "point"]
        bi = g[g.kind == "iid"]
        rates.append(dict(monitor=mon, alpha=al, detector=det, det=p.det.mean(), lo=bi.det.quantile(.025),
                          hi=bi.det.quantile(.975), uncond=p.uncond.mean(), prefix_fa=p.prefix_fa.mean(),
                          arl0_cal=p.arl0_cal.median(), arl0_test=p.arl0_test.median(),
                          arl0_test_noalarm_share=float((p.arl0_test > 1e6).mean())))
    rates = pd.DataFrame(rates)
    piv = R[R.detector != "nested_best_forgetting"].pivot_table(index=["kind", "rep", "monitor", "alpha"],
                                                                 columns="detector", values="det")
    nb = R[R.detector == "nested_best_forgetting"].set_index(["kind", "rep", "monitor", "alpha"]).contrast
    piv["nested_best_forgetting"] = nb + piv["max"]
    D = piv.sub(piv["max"], axis=0).drop(columns="max")
    D = D.reset_index().melt(id_vars=["kind", "rep", "monitor", "alpha"], var_name="detector", value_name="diff")
    for (mon, al, det), g in D.groupby(["monitor", "alpha", "detector"]):
        p, bi, ba = g[g.kind == "point"], g[g.kind == "iid"], g[g.kind == "app"]
        cons.append(dict(monitor=mon, alpha=al, detector=det, est=p["diff"].mean(), lo=bi["diff"].quantile(.025),
                         hi=bi["diff"].quantile(.975), se=bi["diff"].std(), p_le0=float((bi["diff"] <= 0).mean()),
                         app_lo=ba["diff"].quantile(.025) if len(ba) else np.nan,
                         app_hi=ba["diff"].quantile(.975) if len(ba) else np.nan))
    C = pd.DataFrame(cons)
    rates.to_csv(OUT / "arl_rates.csv", index=False)
    C.to_csv(OUT / "arl_contrasts.csv", index=False)
    # pooled across identical-input monitors (joint bootstrap)
    pool = [m for m in monitors if mons[m]["identical"]]
    meta = []
    for al in sorted(C.alpha.unique()):
        for det in list(PRIMARY) + ["nested_best_forgetting", "cusum_k1.5", "ewma_l0.2", "sr_d1"]:
            c = C[(C.alpha == al) & (C.detector == det)].set_index("monitor").loc[pool]
            re = re_pool(c.est.to_numpy(), np.maximum(c.se.to_numpy(), 1e-3))
            for kind in ("iid", "app"):
                bb = D[(D.kind == kind) & (D.alpha == al) & (D.detector == det)].pivot(index="rep", columns="monitor", values="diff")
                if bb.empty:
                    continue
                pb = bb[pool].to_numpy() @ re["w"]
                meta.append(dict(alpha=al, detector=det, boot=kind, k=len(pool), re_mu=re["mu"],
                                 joint_lo=np.quantile(pb, .025), joint_hi=np.quantile(pb, .975),
                                 p_le0=float((pb <= 0).mean()), hksj_lo=re["hksj_lo"], hksj_hi=re["hksj_hi"],
                                 tau2=re["tau2"], I2=re["I2"], n_sig_pos=int((c.lo > 0).sum()),
                                 n_sig_neg=int((c.hi < 0).sum())))
    MT = pd.DataFrame(meta)
    MT.to_csv(OUT / "arl_meta.csv", index=False)
    L = ["# Round 4: long unreset PR streams at matched ARL0 (persistent state, gradual attacks, history-free monitors)", "",
         "Detection = alarm inside the attack run given no alarm in the 0-4-run honest prefix. Point = mean over 10 "
         "calibration/test splits; [CI] = 200 iid run-bootstrap replicates of the whole procedure (thresholds "
         "re-calibrated); {app} = 200 app-cluster replicates (FPR-0.05 cell only). Realized ARL0 = median over splits of the mean first-passage "
         "length on held-out honest TEST runs ('no alarm' = no false alarm in 300 simulated streams of 4 x target PRs).", ""]
    for al in sorted(C.alpha.unique()):
        tgt = int(round(5 / al))
        L += [f"## ARL0 = {tgt} PRs", "", "| monitor | max | CUSUM k=0.5 | windowed top-3 (W=5) | CUSUM 0.5 − max [CI] {app} | wtop3 − max [CI] {app} | nested best forgetting − max [CI] | realized ARL0 (test) max / CUSUM |",
              "|---|---|---|---|---|---|---|---|"]
        for mon in monitors:
            r = rates[(rates.monitor == mon) & (rates.alpha == al)].set_index("detector")
            c = C[(C.monitor == mon) & (C.alpha == al)].set_index("detector")

            def cc(d):
                x = c.loc[d]
                s = f"{x.est:+.3f} [{x.lo:+.3f}, {x.hi:+.3f}]"
                if np.isfinite(x.app_lo):
                    s += f" {{{x.app_lo:+.2f}, {x.app_hi:+.2f}}}"
                return s
            L.append(f"| {mon} | {r.loc['max'].det:.3f} | {r.loc['cusum_k0.5'].det:.3f} | {r.loc['wtop3_w5'].det:.3f} | "
                     f"{cc('cusum_k0.5')} | {cc('wtop3_w5')} | {cc('nested_best_forgetting')} | "
                     f"{fa(r.loc['max'].arl0_test)} / {fa(r.loc['cusum_k0.5'].arl0_test)} |")
        L.append("")
        L += ["Full family (detection rate, point; best per monitor in bold):", "",
              "| monitor | " + " | ".join(sorted(rates.detector.unique())) + " |", "|---|" + "---|" * rates.detector.nunique()]
        for mon in monitors:
            r = rates[(rates.monitor == mon) & (rates.alpha == al)].set_index("detector").det
            L.append(f"| {mon} | " + " | ".join((f"**{v:.2f}**" if v == r.max() else f"{v:.2f}") for v in r.sort_index()) + " |")
        L.append("")
    L += ["## Random-effects pooled contrasts over max (identical-input monitors; joint bootstrap)", "",
          "| ARL0 | detector | bootstrap | RE mean | joint CI | p(≤0) | HKSJ CI | I² | monitors sig + / − |", "|---|---|---|---|---|---|---|---|---|"]
    for r in MT.itertuples():
        L.append(f"| {int(round(5 / r.alpha))} | {r.detector} | {r.boot} | {r.re_mu:+.3f} | [{r.joint_lo:+.3f}, {r.joint_hi:+.3f}] | "
                 f"{r.p_le0:.3f} | [{r.hksj_lo:+.3f}, {r.hksj_hi:+.3f}] | {r.I2:.2f} | {r.n_sig_pos} / {r.n_sig_neg} |")
    (OUT / "arl_tables.md").write_text("\n".join(L) + "\n")
    print("\n".join(L), flush=True)
    fig_arl(C, monitors)


def fig_arl(C, monitors):
    plt = mpl()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6), sharey=True)
    cols = {"cusum_k0.5": "#b23a80", "wtop3_w5": "#1baf7a", "nested_best_forgetting": "#eda100"}
    lab = {"cusum_k0.5": "CUSUM k=0.5", "wtop3_w5": "windowed top-3 (W=5)", "nested_best_forgetting": "nested best forgetting"}
    for ax, al in zip(axes, sorted(C.alpha.unique(), reverse=True)):
        for j, det in enumerate(cols):
            c = C[(C.alpha == al) & (C.detector == det)].set_index("monitor")
            for i, m in enumerate(monitors):
                if m not in c.index:
                    continue
                y = i + (j - 1) * 0.22
                ax.plot([c.loc[m].lo, c.loc[m].hi], [y, y], color=cols[det], lw=1.4)
                ax.plot(c.loc[m].est, y, "o", color=cols[det], ms=3.8, label=lab[det] if i == 0 else None)
        ax.axvline(0, color="#4a4a4a", lw=0.7)
        ax.set_title(f"ARL0 = {int(round(5 / al))} PRs")
        ax.set_xlabel("detection − max (no-reset stream)")
    axes[0].set_yticks(range(len(monitors)))
    axes[0].set_yticklabels(monitors)
    axes[0].legend(frameon=False, loc="lower left")
    fig.tight_layout()
    fig.savefig(OUT / "fig_arl.pdf")


if __name__ == "__main__":
    if "--reanalyse" in sys.argv:   # tables / figure from the saved replicates only
        R = pd.read_csv(OUT / "arl_replicates.csv.gz")
        m = ps_monitor_streams()
        analyse(R, [x for x in m if x in set(R.monitor)], m)
    else:
        main()
