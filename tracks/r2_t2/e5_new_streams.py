"""E5: per-context heterogeneity and allocation for white-box probe and strong-monitor streams.

Signals (per agent step; trajectory statistic = max over steps, oriented so attacks score higher):
  white-box reader (Qwen3.5-27B, tracks/wb_whitebox; definitions from wblib.derived), full and
  none modes: sab, sab_max (synthetic-sabotage probe), dec (Apollo deception probe), fibs_tok (FIBS
  probe on step tokens), fibs_fu (FIBS at the follow-up answer), jl_lm, jl_lm_max (J-lens watch-list
  log-mass)
  LLM monitors (ctrl-basic-v1): openai/gpt-4.1 none (strong, T3 round 2), gpt-4.1-mini none / full
Data: Honest-550 (submit step stripped) and the attack trajectories scored by EVERY signal: the
MonitoringBench originals in the intersection, plus T3's monitor-aware refined attacks
(t3ref:*, contexts from their original task). Contexts = the T2 TF-IDF task clusters (>= 20 honest).

Outputs (results/r2_t2/): e5_signals.csv (AUROC, orientation), e5_heterogeneity.csv (per signal:
ICC of honest max on normal scores, per-context FPR range under a global 5% threshold, logit-normal
tau and LR p), e5_allocation.csv (global / CFAR / pooled_cv / max-detection / Stackelberg at
B = 1%, 5%; 30 plain + 60 bootstrap splits; nominal and spend-matched), e5_tables.md.

    unset VIRTUAL_ENV; uv run python tracks/r2_t2/e5_new_streams.py [--quick]
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

import r2lib as R

L, P = R.L, R.P
PROC = P.PROCESSED
sys.path.insert(0, str(R.ROOT))
from tracks.wb_whitebox.wblib import derived  # noqa: E402

WB_SIGNALS = ["sab", "sab_max", "dec", "fibs_tok", "fibs_fu", "jl_lm", "jl_lm_max"]
ARMS = ["max", "cusum", "multichart", "max_r0", "cusum_r0", "multichart_r0"]


def _read(path):
    with open(path) as f:
        for line in f:
            yield json.loads(line)


def _llm(path, strip=None):
    out = {}
    for d in _read(path):
        s = np.array([np.nan if v is None else v for v in d["scores"]], float)
        if strip is not None:
            ss = strip.get(d["traj_id"])
            if len(s) > 1 and ss is not None and ss == len(s) - 1:
                s = s[:-1]
        s = s[~np.isnan(s)]
        if len(s):
            out[d["traj_id"]] = float(s.max())
    return out


def load_signals() -> tuple[dict, dict]:
    """signal -> {traj_id: trajectory max}, and traj_id -> (label, context)."""
    meta = {}
    for s in ("mb_honest", "monitoringbench"):
        meta.update(P._traj_meta(s))
    clus = P.mb_task_clusters()
    strip = {t: m.get("submit_step") for t, m in meta.items()}
    info = {t: (m["label"], clus.get(m["main_task"])) for t, m in meta.items()}
    sig = {}
    # white-box reader
    for mode in ("full", "none"):
        for src in ("mb", "t3"):
            p = PROC / "whitebox" / "scores" / f"{src}_{mode}.jsonl"
            if not p.exists():
                continue
            for d in _read(p):
                if d["n_steps"] == 0:
                    continue
                F = derived(d["feats"])
                for k in WB_SIGNALS:
                    if k in F and len(F[k]):
                        sig.setdefault(f"wb_{k}_{mode}", {})[d["traj_id"]] = float(np.nanmax(F[k]))
    # LLM monitors
    for name, fname in (("gpt-4.1_none", "scores_openai_gpt-4.1_none.jsonl"),
                        ("gpt-4.1-mini_none", "scores_openai_gpt-4.1-mini_none.jsonl"),
                        ("gpt-4.1-mini_full", "scores_openai_gpt-4.1-mini_full.jsonl")):
        d = {}
        h = PROC / "mb_honest" / fname
        if h.exists():
            d.update(_llm(h, strip))
        for a in (PROC / "monitoringbench" / fname, PROC / "monitoringbench" / f"r2orig_{fname}"):
            if a.exists():
                d.update(_llm(a, strip))
        for arm in ARMS:
            f = PROC / "t3_refined" / arm / fname
            if f.exists():
                d.update(_llm(f))
        if d:
            sig[f"llm_{name}"] = d
    # contexts of refined attacks = their original's
    for s in sig.values():
        for t in s:
            if t.startswith("t3ref:") and t not in info:
                orig = "monitoringbench:" + t.split(":")[-1]
                info[t] = ("attack", info.get(orig, ("attack", None))[1])
    return sig, info


def build_frames(sig, info, min_honest=20, min_attack=10):
    honest_common = set.intersection(*[{t for t in s if info.get(t, ("", None))[0] == "honest"} for s in sig.values()])
    attack_common = set.intersection(*[{t for t in s if info.get(t, ("", None))[0] == "attack"} for s in sig.values()])
    ids = sorted(honest_common | attack_common)
    base = pd.DataFrame(dict(traj_id=ids, label=[info[t][0] for t in ids], ctx=[info[t][1] for t in ids]))
    base = base[base.ctx.notna()]
    cnt = base.groupby(["ctx", "label"]).size().unstack(fill_value=0)
    keep_h = set(cnt.index[cnt.honest >= min_honest])
    keep_a = set(cnt.index[(cnt.honest >= min_honest) & (cnt.attack >= min_attack)])
    frames, rows = {}, []
    for name, s in sig.items():
        df = base.assign(stat=[s[t] for t in base.traj_id])
        y = (df.label == "attack").astype(int)
        auc = roc_auc_score(y, df.stat)
        sign = 1.0 if auc >= 0.5 else -1.0
        df["stat"] = sign * df.stat
        rows.append(dict(signal=name, auroc=max(auc, 1 - auc), orientation=sign, n_honest=int((y == 0).sum()),
                         n_attack=int(y.sum()), n_orig=int(((y == 1) & ~df.traj_id.str.startswith("t3ref")).sum())))
        frames[name] = (df[df.ctx.isin(keep_h)], df[df.ctx.isin(keep_a)])
    return frames, pd.DataFrame(rows)


def heterogeneity(name, dh):
    h = dh[dh.label == "honest"]
    w = L.traffic(h.assign(label="honest"))
    vc = L.varcomp_oneway(L.normal_scores(h.stat.values), h.ctx.values)
    G = L.Grid({c: g.stat.values for c, g in h.groupby("ctx")}, w)
    out = dict(signal=name, n_ctx=len(G.keys), n_honest=len(h), icc_ns=vc["icc"], icc_p=vc["p"])
    for B in (0.05, 0.10):
        th = L.rule_global(G, B)
        n = np.array([(h.ctx == c).sum() for c in G.keys])
        x = np.array([th[c].rate(h[h.ctx == c].stat.values) for c in G.keys]) * n
        re = L.logitnormal_re(np.round(x), n)
        out.update({f"fpr_min@{B}": float((x / n).min()), f"fpr_max@{B}": float((x / n).max()),
                    f"tau@{B}": re["tau"], f"tau_p@{B}": re["p"]})
    return out


def allocation(args):
    name, df, n_plain, n_boot, seed = args
    w = L.traffic(df)
    rng = np.random.default_rng(seed)
    rows = []
    for rep in range(n_plain + n_boot):
        kind = "plain" if rep < n_plain else "boot"
        Hc, Ht, Ac, At, _ = L.split_panel(df, rng, bootstrap=(kind == "boot"))
        Gc = L.Grid(Hc, w)
        for B in (0.01, 0.05):
            n0 = L.cv_n0(Hc, w, B, reps=1)
            fits = dict(global_=lambda b: L.rule_global(Gc, b), cfar=lambda b: L.rule_cfar(Gc, b),
                        pooled_cv=lambda b: L.rule_pooled(Gc, b, n0), maxdet=lambda b: L.rule_maxdet(Hc, Ac, w, b),
                        stack=lambda b: R.rule_stackelberg(Hc, Ac, w, b),
                        stack_m0=lambda b: R.rule_stackelberg(Hc, Ac, w, b, m0=10.0))

            def evalf(t):
                m = L.evaluate(t, Ht, At, w, Ac=Ac)
                return {k: m[k] for k in ("spend", "tpr_uniform", "sel_informed", "sel_oracle")}, {}
            for r, f in fits.items():
                for mode, m, _ in R.nominal_and_matched(f, evalf, B):
                    rows.append(dict(signal=name, B=B, mode=mode, rule=r.rstrip("_"), rep=rep, kind=kind, **m))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    sig, info = load_signals()
    print("signals:", {k: len(v) for k, v in sig.items()}, flush=True)
    frames, sdf = build_frames(sig, info)
    print(sdf.round(3).to_string(), flush=True)
    H = pd.DataFrame([heterogeneity(n, f[0]) for n, f in frames.items()])
    n_plain, n_boot = (2, 2) if a.quick else (30, 60)
    jobs = [(n, f[1], n_plain, n_boot, 13000 + i) for i, (n, f) in enumerate(frames.items())]
    with ProcessPoolExecutor(a.workers) as ex:
        raw = pd.concat(list(ex.map(allocation, jobs)), ignore_index=True)
    tag = "_quick" if a.quick else ""
    R.RAW.mkdir(parents=True, exist_ok=True)
    raw.to_parquet(R.RAW / f"e5{tag}.parquet")
    S_ = R.summarize(raw, ["signal", "B", "mode", "rule"], ["spend", "tpr_uniform", "sel_informed", "sel_oracle"])
    sdf.to_csv(R.OUT / f"e5_signals{tag}.csv", index=False, float_format="%.4g")
    H.to_csv(R.OUT / f"e5_heterogeneity{tag}.csv", index=False, float_format="%.4g")
    S_.to_csv(R.OUT / f"e5_allocation{tag}.csv", index=False, float_format="%.4g")
    ctx_counts = frames[next(iter(frames))][1].groupby(["ctx", "label"]).size().unstack(fill_value=0)
    md = ["## E5: white-box probe and strong-monitor streams\n",
          f"Common trajectory set: {sdf.n_honest.iloc[0]} honest (Honest-550) and {sdf.n_attack.iloc[0]} attacks "
          f"({sdf.n_orig.iloc[0]} MonitoringBench originals + T3 monitor-aware refined attacks), scored by every "
          "signal. Contexts = T2 task clusters. Heterogeneity uses honest runs only (clusters with >= 20 honest); "
          "allocation uses clusters with >= 10 attacks: "
          + ", ".join(f"{c} ({r.honest} h / {r.attack} a)" for c, r in ctx_counts.iterrows()) + ".\n",
          "| signal | AUROC (traj. max) | ICC (normal scores, p) | ctx FPR range @5% | tau@5% (p) | ctx FPR range @10% | tau@10% (p) |",
          "|---|---|---|---|---|---|---|"]
    Hm = H.merge(sdf, on="signal")
    for _, r in Hm.sort_values("auroc", ascending=False).iterrows():
        md.append(f"| {r.signal} | {r.auroc:.3f} | {r.icc_ns:.3f} ({r.icc_p:.3f}) | "
                  f"{100 * r['fpr_min@0.05']:.1f}–{100 * r['fpr_max@0.05']:.1f}% | {r['tau@0.05']:.2f} ({r['tau_p@0.05']:.3f}) | "
                  f"{100 * r['fpr_min@0.1']:.1f}–{100 * r['fpr_max@0.1']:.1f}% | {r['tau@0.1']:.2f} ({r['tau_p@0.1']:.3f}) |")
    md += ["", "Allocation (spend-matched): uniform TPR / informed selection safety [95%], Δ selection vs global.\n",
           "| signal | B | rule | uniform TPR | selection [95%] | Δ vs global |", "|---|---|---|---|---|---|"]
    for _, r in S_[S_["mode"] == "matched"].iterrows():
        md.append(f"| {r.signal} | {r.B} | {r.rule} | {r.tpr_uniform:.2f} | "
                  f"{R.fmt_ci(r.sel_informed, r.get('sel_informed_lo'), r.get('sel_informed_hi'))} | "
                  f"{r.get('sel_informed_d', np.nan):+.2f} [{r.get('sel_informed_dlo', np.nan):+.2f}, "
                  f"{r.get('sel_informed_dhi', np.nan):+.2f}] |")
    (R.OUT / f"e5_tables{tag}.md").write_text("\n".join(md) + "\n")
    print(Hm.round(3).to_string())


if __name__ == "__main__":
    main()
