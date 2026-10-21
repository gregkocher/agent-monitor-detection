"""Corrected building blocks for the r2_t2 E5 allocation analysis (audit issues C1 and M5).

What this fixes
---------------
C1  r2lib.nominal_and_matched swept the nominal level over B x (0.3..2) and np.interp CLAMPED when the
    realized test spend never came down to B, so 'matched' 1% rows of per-context rules really spent
    2-3.5%. `sweep_matched` here
      (a) sweeps the level on a fine grid B x {0, log-spaced 0.01..3, 1.0},
      (b) interpolates a metric at realized test spend = B ONLY when B lies inside the realized-spend
          range of that replicate (no clamping; otherwise every matched metric is NaN, matched_ok=False),
      (c) returns the realized spend of the nominal fit, the matched spend (= B or NaN), and the
          replicate's spend floor / ceiling (realized test spend at level 0 / at the top level).
M5  split_panel split attacks iid within context, so variants of one base attack (MonitoringBench
    original, its r0 rewrite under 3 arms, and r1/r2 adaptive rewrites) landed on both sides.
    `attack_meta` attaches base = meta.orig_traj_id (originals map to themselves), a content hash of
    the step (action, output) pairs, and is_orig; `dedupe` keeps one trajectory per identical hash;
    `grouped_split` splits the attacks of each context by base attack (all variants on one side) and
    bootstraps bases (clusters) within each half.

Library only; the driver is tracks/fixes/e5/e5_allocation_fixed.py.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tracks" / "r2_t2"))
sys.path.insert(0, str(ROOT))
import e5_new_streams as E5  # noqa: E402
import r2lib as R  # noqa: E402

L = R.L
PROC = R.P.PROCESSED
OUT = ROOT / "results" / "fixes" / "r2_t2"

# level multipliers: 0 (thresholds at the calibration maximum), log-spaced 0.01..3, and exactly 1
LEVEL_MULTS = tuple(sorted(set([0.0, 1.0] + list(np.round(np.logspace(-2, np.log10(3.0), 30), 6)))))


# --------------------------------------------------------------------------------------------
# data: E5 panel + attack metadata
# --------------------------------------------------------------------------------------------


def _hash_steps(d) -> str:
    return hashlib.sha256(json.dumps([(s.get("action"), s.get("output")) for s in d["steps"]]).encode()).hexdigest()


def attack_meta(ids) -> pd.DataFrame:
    """traj_id -> base attack (orig_traj_id; originals map to themselves), content hash, is_orig,
    arm, round. Reads data/processed/t3_refined/<arm>/trajectories.jsonl (the 6 E5 arms) and
    data/processed/monitoringbench/trajectories.jsonl."""
    ids = set(ids)
    rows = {}
    for arm in E5.ARMS:
        for d in E5._read(PROC / "t3_refined" / arm / "trajectories.jsonl"):
            t = d["traj_id"]
            if t in ids:
                h = _hash_steps(d)
                if t in rows and rows[t]["hash"] != h:
                    raise ValueError(f"same traj_id with different content: {t}")
                parts = t.split(":")
                rows[t] = dict(traj_id=t, base=d["meta"]["orig_traj_id"], hash=h, is_orig=False,
                               arm=parts[1], round=parts[2])
    for d in E5._read(PROC / "monitoringbench" / "trajectories.jsonl"):
        t = d["traj_id"]
        if t in ids:
            rows[t] = dict(traj_id=t, base=t, hash=_hash_steps(d), is_orig=True, arm="original", round="orig")
    missing = ids - set(rows)
    if missing:
        raise ValueError(f"{len(missing)} attack ids without trajectories, e.g. {sorted(missing)[:3]}")
    return pd.DataFrame(rows.values())


def dedupe(meta: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Keep one trajectory per identical content hash (prefer the original, then the lowest round,
    then traj_id order). Returns (kept meta, stats)."""
    pri = meta.assign(_o=(~meta.is_orig).astype(int), _r=meta["round"].map({"orig": -1, "r0": 0, "r1": 1, "r2": 2,
                                                                             "r3": 3}).fillna(9))
    pri = pri.sort_values(["hash", "_o", "_r", "traj_id"])
    kept = pri.drop_duplicates("hash", keep="first").drop(columns=["_o", "_r"])
    grp = meta.groupby("hash").size()
    return kept, dict(n_in=len(meta), n_kept=len(kept), n_dup_groups=int((grp > 1).sum()),
                      n_removed=int(len(meta) - len(kept)))


def load_panel():
    """E5 signals and frames exactly as tracks/r2_t2/e5_new_streams.py builds them, plus attack
    metadata. Returns (frames, sdf, base_df, meta, dedupe_stats) where base_df is the full common
    set (all contexts, used for AUROC) with columns traj_id, label, ctx and one column per signal
    (oriented as in E5)."""
    sig, info = E5.load_signals()
    frames, sdf = E5.build_frames(sig, info)
    ids = sorted(set.intersection(*[set(s) for s in sig.values()]))
    att = [t for t in ids if info.get(t, ("", None))[0] == "attack" and info[t][1] is not None]
    meta = attack_meta(att)
    kept, st = dedupe(meta)
    # full common set for AUROC (same as E5's AUROC set: ctx not null)
    rows = []
    for t in ids:
        lab, ctx = info.get(t, ("", None))
        if ctx is None or lab not in ("honest", "attack"):
            continue
        rows.append(dict(traj_id=t, label=lab, ctx=ctx))
    base = pd.DataFrame(rows)
    orient = dict(zip(sdf.signal, sdf.orientation))
    for name, s in sig.items():
        base[name] = [orient[name] * s[t] for t in base.traj_id]
    return frames, sdf, base, meta, kept, st


# --------------------------------------------------------------------------------------------
# splits
# --------------------------------------------------------------------------------------------


def grouped_split(df: pd.DataFrame, rng, frac=0.5, bootstrap=False):
    """df: columns ctx, label, stat, base (base attack id for attacks). Honest: iid 50/50 within ctx
    (as t2lib.split_panel). Attacks: the BASE ATTACKS of each context are split 50/50, all variants
    of a base go to the same half. Bootstrap: honest iid within half; attacks resample bases with
    replacement within each half and context (cluster bootstrap), keeping all their variants."""
    Hc, Ht, Ac, At = {}, {}, {}, {}
    for ctx, g in df.groupby("ctx", sort=True):
        h = g[g.label == "honest"].stat.values
        p = rng.permutation(len(h))
        m = int(round(frac * len(h)))
        Hc[ctx], Ht[ctx] = h[p[:m]], h[p[m:]]
        a = g[g.label == "attack"]
        bases = a.base.unique()
        pb = rng.permutation(len(bases))
        mb = int(round(frac * len(bases)))
        if len(bases) == 1:
            mb = int(rng.integers(0, 2))
        cal_b, test_b = bases[pb[:mb]], bases[pb[mb:]]
        by_base = {b: x.stat.values for b, x in a.groupby("base")}

        def gather(bs):
            if bootstrap and len(bs):
                bs = bs[rng.integers(0, len(bs), len(bs))]
            return np.concatenate([by_base[b] for b in bs]) if len(bs) else np.array([], float)
        Ac[ctx], At[ctx] = gather(cal_b), gather(test_b)
        if bootstrap:
            Hc[ctx] = Hc[ctx][rng.integers(0, len(Hc[ctx]), len(Hc[ctx]))]
            Ht[ctx] = Ht[ctx][rng.integers(0, len(Ht[ctx]), len(Ht[ctx]))]
    return Hc, Ht, Ac, At


# --------------------------------------------------------------------------------------------
# spend matching without clamping
# --------------------------------------------------------------------------------------------


def sweep_matched(fit, evalf, B: float, mults=LEVEL_MULTS, keep_curve=False):
    """fit(level) -> thresholds; evalf(th) -> metrics dict with 'spend' (realized test spend).

    Returns dict with
      nominal: metrics at level B (spend = realized test spend of the nominal fit)
      matched: metrics interpolated (linearly in realized spend) at spend = B if
               min(spend) <= B <= max(spend) over the sweep, else NaN for every metric;
               spend = B or NaN; matched_ok bool
      floor, ceiling: realized test spend at the lowest / highest sweep level
      curve: list of (level, metrics) if keep_curve
    """
    res = [(m, evalf(fit(B * m))) for m in mults]
    nominal = dict(next(r for m, r in res if m == 1.0))
    sp = np.array([r["spend"] for _, r in res], float)
    floor, ceil = float(sp[0]), float(sp[-1])
    ok = bool(np.nanmin(sp) <= B + 1e-12 and np.nanmax(sp) >= B - 1e-12)
    matched = {}
    if ok:
        o = np.argsort(sp, kind="stable")
        xs = sp[o]
        for k in res[0][1]:
            y = np.array([r[k] for _, r in res], float)[o]
            fin = np.isfinite(y)
            inside = fin.any() and xs[fin].min() <= B + 1e-12 and xs[fin].max() >= B - 1e-12
            matched[k] = float(np.interp(B, xs[fin], y[fin])) if inside else np.nan
        matched["spend"] = B
    else:
        matched = {k: np.nan for k in res[0][1]}
    matched["matched_ok"] = ok
    out = dict(nominal=nominal, matched=matched, floor=floor, ceiling=ceil)
    if keep_curve:
        out["curve"] = res
    return out


# --------------------------------------------------------------------------------------------
# summary
# --------------------------------------------------------------------------------------------


def summarize(raw: pd.DataFrame, keys: list, metrics: list, ref_rule="global", rule_col="rule") -> pd.DataFrame:
    """Point estimates = mean over 'plain' replicates where the metric is defined; 95% percentile
    intervals over 'boot' replicates; paired differences vs ref_rule on boot replicates where BOTH
    are defined. Adds share_matched (plain and boot) and n_plain_ok / n_boot_ok."""
    raw = raw.copy()
    for c in metrics:
        raw[c] = pd.to_numeric(raw[c], errors="coerce").astype(float)
    pl, b = raw[raw.kind == "plain"], raw[raw.kind == "boot"]
    out = pl.groupby(keys)[metrics].mean()
    out["share_matched_plain"] = pl.groupby(keys).matched_ok.mean()
    out["share_matched_boot"] = b.groupby(keys).matched_ok.mean()
    out["n_plain"] = pl.groupby(keys).size()
    out["n_boot"] = b.groupby(keys).size()
    bt = b.groupby(keys)[metrics]
    lo, hi = bt.quantile(0.025), bt.quantile(0.975)
    for c in metrics:
        out[c + "_lo"], out[c + "_hi"] = lo[c], hi[c]
    if ref_rule is not None:
        gk = [k for k in keys if k != rule_col]
        g = b[b[rule_col] == ref_rule][gk + ["rep"] + metrics]
        m = b.merge(g, on=gk + ["rep"], suffixes=("", "_ref"))
        for c in metrics:
            m[c] = m[c] - m[c + "_ref"]
        d = m.groupby(keys)
        for c in metrics:
            out[c + "_d"] = d[c].mean()
            out[c + "_dlo"] = d[c].quantile(0.025)
            out[c + "_dhi"] = d[c].quantile(0.975)
            out[c + "_dpos"] = d[c].apply(lambda x: float((x.dropna() > 0).mean()) if x.notna().any() else np.nan)
            out[c + "_n_pairs"] = d[c].apply(lambda x: int(x.notna().sum()))
    return out.reset_index()
