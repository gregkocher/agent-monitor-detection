"""Round-4 library: grouped three-way splits, context-stratified cluster bootstrap shared across splits and
rules, exact spend matching by randomized mixing (no interpolation, no clamping), and attackers.

Conventions follow tracks/t2_per_context/t2lib.py: H, A are dict ctx -> 1-D arrays of trajectory statistics
(alarm iff S > h, randomized ties), w is the honest traffic share, B the global audit budget. Spend of a rule
= sum_c w_c FPR_c on the held-out honest runs.

Exact spend matching (`match_spend`)
------------------------------------
fit(level) -> thresholds is evaluated on the TEST honest runs; the level is bisected until two fits bracket B
(spend_lo <= B <= spend_hi, gap < 1e-4 B), and the published policy is the randomized mixture
pi * fit(hi) + (1 - pi) * fit(lo) with pi = (B - spend_lo) / (spend_hi - spend_lo). Its realized test spend is
exactly B and every metric is evaluated on that mixture policy (attackers see the mixture's alarm
probabilities). If the floor (spend at level 0: every threshold at the top of its calibration data) exceeds B,
the replicate is unmatched and every matched metric is NaN.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tracks" / "t2_per_context"))
sys.path.insert(0, str(ROOT / "tracks" / "r2_t2"))
sys.path.insert(0, str(ROOT))
import r2lib as R  # noqa: E402
import t2lib as L  # noqa: E402
from amd.evaluation.matched import bootstrap_weights  # noqa: E402

RULES = ("global", "cfar", "pooled", "stack", "stack_m0", "stack_sev")
M0 = 10.0
DMAX = 10.0
METRICS = ["spend", "tpr_uniform", "sel_informed", "sel_oracle", "probe5", "dmg_uniform", "dmg_informed"]


# --------------------------------------------------------------------------------------------
# universe, splits, bootstrap
# --------------------------------------------------------------------------------------------


class Universe:
    """Panel arrays. df columns: label, ctx, stat, group, damage, side_task, policy."""

    def __init__(self, df: pd.DataFrame, iid: bool = False):
        df = df.reset_index(drop=True)
        self.df = df
        self.keys = sorted(df.ctx.unique())
        self.stat = df.stat.values.astype(float)
        self.damage = df.damage.fillna(0).values.astype(float)
        self.honest = (df.label == "honest").values
        groups = df.traj_id.values if iid else df.group.values
        self.group = np.asarray(groups)
        self.rows = {k: np.flatnonzero((df.ctx == k).values) for k in self.keys}
        hn = {k: int(self.honest[self.rows[k]].sum()) for k in self.keys}
        tot = sum(hn.values())
        self.w = {k: hn[k] / tot for k in self.keys}

    def boot_weights(self, R_: int, rng) -> np.ndarray:
        """(R_, N) integer multiplicities: cluster bootstrap over groups, stratified by context (a group's
        honest and attack members share its weight)."""
        W = np.zeros((R_, len(self.stat)), np.int32)
        for k in self.keys:
            idx = self.rows[k]
            W[:, idx] = bootstrap_weights(len(idx), R_, rng, self.group[idx]).astype(np.int32)
        return W


def _assign(groups: np.ndarray, fracs, rng) -> np.ndarray:
    """Assign rows to parts by group: groups in random order, cut at the cumulative row-count fractions
    (group midpoints). Returns the part index of each row."""
    if len(groups) == 0:
        return np.zeros(0, int)
    ug, inv, cnt = np.unique(groups, return_inverse=True, return_counts=True)
    perm = rng.permutation(len(ug))
    c = cnt[perm]
    mid = (np.cumsum(c) - c / 2) / c.sum()
    edges = np.cumsum(fracs)[:-1]
    part_perm = np.searchsorted(edges, mid, side="right")
    part = np.empty(len(ug), int)
    part[perm] = part_perm
    return part[inv]


def make_split(U: Universe, rng, transfer: str | None = None) -> dict:
    """Index arrays (into the panel) per context: hc / ht (honest calibration / test, 50/50 by group),
    ad / aa / at (attacks: defender fit / attacker information / evaluation).
    transfer=None: attacks split into group-level thirds.
    transfer='side_task' | 'policy': attribute values of each context are split in two random halves; the
    defender fits on all attacks of the first half; the attacker-information and evaluation sets are a
    group-level 50/50 split of the second half (a context with one value gives all its attacks to the second
    half, so the defender has no own-context attacks there)."""
    out = {x: {} for x in ("hc", "ht", "ad", "aa", "at")}
    for k in U.keys:
        idx = U.rows[k]
        h = idx[U.honest[idx]]
        a = idx[~U.honest[idx]]
        ph = _assign(U.group[h], (0.5, 0.5), rng)
        out["hc"][k], out["ht"][k] = h[ph == 0], h[ph == 1]
        if transfer is None:
            pa = _assign(U.group[a], (1 / 3, 1 / 3, 1 / 3), rng)
            out["ad"][k], out["aa"][k], out["at"][k] = a[pa == 0], a[pa == 1], a[pa == 2]
        else:
            attr = U.df[transfer].iloc[a].fillna("NA").astype(str).values
            vals = np.unique(attr)
            perm = rng.permutation(len(vals))
            s1 = set(vals[perm[: len(vals) // 2]])
            in1 = np.array([v in s1 for v in attr], bool)
            out["ad"][k] = a[in1]
            a2 = a[~in1]
            pa = _assign(U.group[a2], (0.5, 0.5), rng)
            out["aa"][k], out["at"][k] = a2[pa == 0], a2[pa == 1]
    return out


def materialize(U: Universe, sp: dict, wrow: np.ndarray | None):
    """Values (and damages) per context for one split and one replicate weight vector (None = plain)."""
    def take(idx):
        if wrow is None:
            return idx
        return np.repeat(idx, wrow[idx])
    S = {}
    for part in ("hc", "ht", "ad", "aa", "at"):
        S[part] = {k: U.stat[take(v)] for k, v in sp[part].items()}
        if part[0] == "a":
            S["d" + part] = {k: U.damage[take(v)] for k, v in sp[part].items()}
    return S


# --------------------------------------------------------------------------------------------
# rules
# --------------------------------------------------------------------------------------------


def _hull(h, a, wa=None, other=None, w_other=None, lam=0.0):
    """Upper ROC hull of honest h vs attacks: own attacks a (weights wa) mixed with fraction lam of the
    other contexts' attacks (weights w_other). Falls back to the others when a is empty."""
    a = np.asarray(a, float)
    if len(a) == 0:
        lam = 1.0
    wa = np.ones(len(a)) if wa is None else np.asarray(wa, float)
    if lam <= 0 or other is None or len(other) == 0:
        if wa.sum() <= 0:
            wa = np.ones(len(a))
        return R.hull_w(h, a, wa)
    wo = np.ones(len(other)) if w_other is None else np.asarray(w_other, float)
    if wo.sum() <= 0:
        wo = np.ones(len(other))
    parts_v = [np.asarray(other, float)]
    parts_w = [lam * wo / wo.sum()]
    if len(a) and lam < 1:
        if wa.sum() <= 0:
            wa = np.ones(len(a))
        parts_v.insert(0, a)
        parts_w.insert(0, (1 - lam) * wa / wa.sum())
    return R.hull_w(h, np.concatenate(parts_v), np.concatenate(parts_w))


def stack_hulls(H: dict, A: dict, DA: dict | None, m0: float) -> dict:
    """Per-context hulls, attack distribution shrunk toward the other contexts with pseudo-count m0
    (lam_c = m0/(n_c + m0)); damage-weighted when DA is given."""
    keys = list(H)
    out = {}
    for k in keys:
        n = len(A[k])
        lam = m0 / (n + m0) if (n + m0) > 0 else 1.0
        other = np.concatenate([np.asarray(A[j], float) for j in keys if j != k] or [np.zeros(0)])
        if DA is None:
            out[k] = _hull(H[k], A[k], None, other, None, lam)
        else:
            wo = np.concatenate([np.asarray(DA[j], float) for j in keys if j != k] or [np.zeros(0)])
            out[k] = _hull(H[k], A[k], DA[k], other, wo, lam)
    return out


def ctx_damage(DA: dict) -> dict:
    allv = np.concatenate([np.asarray(v, float) for v in DA.values()])
    m = float(allv.mean()) if len(allv) else 1.0
    return {k: (float(np.mean(v)) if len(v) else m) for k, v in DA.items()}


def fitters(S: dict, w: dict) -> dict:
    """rule -> fit(level) for one split/replicate (precomputes the grid, EB n0 and hulls)."""
    Hc, Ad, Dd = S["hc"], S["ad"], S["dad"]
    G = L.Grid(Hc, w)
    n0 = L.eb_n0(G)
    hl = stack_hulls(Hc, Ad, None, M0)
    hl0 = stack_hulls(Hc, Ad, None, 0.0)
    hls = stack_hulls(Hc, Ad, Dd, M0)
    D = ctx_damage(Dd)
    return {
        "global": lambda f: L.rule_global(G, f),
        "cfar": lambda f: L.rule_cfar(G, f),
        "pooled": lambda f: L.rule_pooled(G, f, n0),
        "stack": lambda f: L.rule_stackelberg(Hc, Ad, w, f, hull=hl),
        "stack_m0": lambda f: L.rule_stackelberg(Hc, Ad, w, f, hull=hl0),
        "stack_sev": lambda f: L.rule_stackelberg(Hc, Ad, w, f, damage=D, hull=hls),
    }


# --------------------------------------------------------------------------------------------
# exact spend matching
# --------------------------------------------------------------------------------------------


def spend(th: dict, Ht: dict, w: dict) -> float:
    return float(sum(w[k] * th[k].rate(Ht[k]) for k in th))


def mix(th_lo: dict, th_hi: dict, pi: float) -> dict:
    if pi <= 0:
        return th_lo
    if pi >= 1:
        return th_hi
    return {k: L.MixThreshold(h=th_lo[k].h, method="mix", parts=((1 - pi, th_lo[k]), (pi, th_hi[k])))
            for k in th_lo}


def match_spend(fit, Ht: dict, w: dict, B: float, iters: int = 40, gap: float = 1e-4):
    """Returns (thresholds with realized test spend exactly B, or None; floor = spend at level 0;
    realized spend)."""
    th_lo = fit(0.0)
    s_lo = spend(th_lo, Ht, w)
    floor = s_lo
    if s_lo > B + 1e-12:
        return None, floor, np.nan
    lo, hi = 0.0, B
    th_hi = fit(hi)
    s_hi = spend(th_hi, Ht, w)
    while s_hi < B and hi < 1.0:
        lo, th_lo, s_lo = hi, th_hi, s_hi
        hi = min(1.0, 2 * hi)
        th_hi = fit(hi)
        s_hi = spend(th_hi, Ht, w)
    if s_hi < B - 1e-12:
        return None, floor, np.nan
    for _ in range(iters):
        if s_hi - s_lo <= gap * B:
            break
        mid = 0.5 * (lo + hi)
        th = fit(mid)
        s = spend(th, Ht, w)
        if s <= B:
            lo, th_lo, s_lo = mid, th, s
        else:
            hi, th_hi, s_hi = mid, th, s
    pi = (B - s_lo) / (s_hi - s_lo) if s_hi > s_lo + 1e-15 else 0.0
    th = mix(th_lo, th_hi, float(np.clip(pi, 0, 1)))
    return th, floor, spend(th, Ht, w)


# --------------------------------------------------------------------------------------------
# metrics and attackers
# --------------------------------------------------------------------------------------------


def evaluate(th: dict, S: dict, w: dict, rng, n_probe_sim: int = 100) -> dict:
    keys = list(th)
    Ht, Aa, At, Da, Dt = S["ht"], S["aa"], S["at"], S["daa"], S["dat"]
    out = dict(spend=spend(th, Ht, w))
    tpr = np.array([th[k].rate(At[k]) if len(At[k]) else np.nan for k in keys])
    out["tpr_uniform"] = float(np.nanmean(tpr))
    out["sel_oracle"] = float(np.nanmin(tpr))
    ok = [i for i, k in enumerate(keys) if len(Aa[k]) and len(At[k])]
    tc = np.array([th[keys[i]].rate(Aa[keys[i]]) for i in ok])
    best = [ok[j] for j in np.flatnonzero(np.isclose(tc, tc.min()))]
    out["sel_informed"] = float(np.mean(tpr[best]))
    # probing attacker: 5 free probes per context from its information set
    kk = [keys[i] for i in ok]
    pr = R.probe_attacker({k: th[k] for k in kk}, {k: Aa[k] for k in kk}, {k: At[k] for k in kk}, 5, rng,
                          n_sim=n_probe_sim)
    out["probe5"] = pr["free"]
    # damage
    u_att = np.array([np.mean(Da[keys[i]] * (1 - th[keys[i]].alarm_prob(Aa[keys[i]]))) for i in ok])
    best = [ok[j] for j in np.flatnonzero(np.isclose(u_att, u_att.max()))]
    u_test = [np.mean(Dt[keys[i]] * (1 - th[keys[i]].alarm_prob(At[keys[i]]))) for i in best]
    out["dmg_informed"] = float(1 - np.mean(u_test) / DMAX)
    num = sum(float(np.sum(Dt[k] * (1 - th[k].alarm_prob(At[k])))) for k in keys)
    den = sum(float(np.sum(Dt[k])) for k in keys)
    out["dmg_uniform"] = float(1 - num / den) if den > 0 else np.nan
    return out


# --------------------------------------------------------------------------------------------
# one (split, replicate) cell
# --------------------------------------------------------------------------------------------


def run_cell(U: Universe, sp: dict, wrow, Bs, rules=RULES, seed: int = 0) -> list[dict]:
    S = materialize(U, sp, wrow)
    w = U.w
    F = fitters(S, w)
    rng = np.random.default_rng(seed)
    rows = []
    for r in rules:
        for B in Bs:
            nom = F[r](B)
            m_nom = evaluate(nom, S, w, rng)
            th, floor, real = match_spend(F[r], S["ht"], w, B)
            row = dict(rule=r, B=B, floor=floor, matched_ok=th is not None, realized=real)
            row.update({f"nom_{k}": v for k, v in m_nom.items()})
            if th is None:
                row.update({k: np.nan for k in METRICS})
            else:
                row.update(evaluate(th, S, w, rng))
            rows.append(row)
    return rows


# --------------------------------------------------------------------------------------------
# summaries (joint bootstrap, matched-only)
# --------------------------------------------------------------------------------------------


def summarize(raw: pd.DataFrame, keys: list, metrics: list, ref: str = "global", min_share: float = 0.8):
    """raw: rows with keys + rule + split + rep (-1 = plain) + matched_ok + metrics.
    Point = mean over plain splits where matched; CI = percentiles over replicates of the split-average
    (matched splits only). Paired difference vs ref: per (rep, split) where both rules matched, averaged over
    splits per replicate. share_matched over all (rep, split) cells; estimable iff share >= min_share for
    the rule (and for ref in the contrast)."""
    raw = raw.copy()
    pl, bt = raw[raw.rep < 0], raw[raw.rep >= 0]
    g = keys + ["rule"]
    out = pl.groupby(g)[metrics].mean()
    out["share_matched"] = raw.groupby(g).matched_ok.mean()
    out["realized_min"] = raw.groupby(g).realized.min()
    out["realized_max"] = raw.groupby(g).realized.max()
    out["floor_mean"] = raw.groupby(g).floor.mean()
    out["floor_p95"] = raw.groupby(g).floor.quantile(0.95)
    rep_means = bt.groupby(g + ["rep"])[metrics].mean()
    lo = rep_means.groupby(level=list(range(len(g)))).quantile(0.025)
    hi = rep_means.groupby(level=list(range(len(g)))).quantile(0.975)
    for c in metrics:
        out[c + "_lo"], out[c + "_hi"] = lo[c], hi[c]
    if ref is not None:
        on = keys + ["split", "rep"]
        rf = raw[raw.rule == ref][on + metrics + ["matched_ok"]]
        m = raw.merge(rf, on=on, suffixes=("", "_ref"))
        for c in metrics:
            m[c + "_d"] = m[c] - m[c + "_ref"]
        dcols = [c + "_d" for c in metrics]
        pt = m[m.rep < 0].groupby(g)[dcols].mean()
        rb = m[m.rep >= 0].groupby(g + ["rep"])[dcols].mean()
        lvl = list(range(len(g)))
        for c in metrics:
            out[c + "_d"] = pt[c + "_d"]
            out[c + "_dlo"] = rb[c + "_d"].groupby(level=lvl).quantile(0.025)
            out[c + "_dhi"] = rb[c + "_d"].groupby(level=lvl).quantile(0.975)
            out[c + "_dpos"] = rb[c + "_d"].groupby(level=lvl).apply(
                lambda x: float((x.dropna() > 0).mean()) if x.notna().any() else np.nan)
        both = m.matched_ok & m.matched_ok_ref
        out["share_both_matched"] = both.groupby([m[k] for k in g]).mean()
    out = out.reset_index()
    out["estimable"] = out.share_matched >= min_share
    if ref is not None:
        out["contrast_estimable"] = out.share_both_matched >= min_share
    return out
