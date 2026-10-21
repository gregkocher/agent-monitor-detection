"""Data-driven decision-rule chooser, evaluated out of sample on every stream set.

Candidate rules: max, 2nd-max (kth2), top-3 sum (whitened), CUSUM(k) on whitened scores, k in K_GRID.
A chooser sees only a CALIBRATION split of one stream set: honest calibration streams + a small labeled attack
sample (n_lab attacks). It picks one rule; that rule's threshold is set on the honest calibration streams at
trajectory FPR alpha (randomized plug-in, 5-fold cross-fitted per-unit transforms) and its TPR is measured on the
held-out attacks (FPR on held-out honest streams).

Choosers
- always_max                       the standard rule
- emp            empirical: argmax over rules of the labeled-attack TPR at alpha' in {alpha, 2 alpha, 5 alpha}
                 (averaged, to reduce variance), switching away from max only if the gain exceeds a margin
                 of one labeled attack (1/n_lab)
- mech           mechanism rule (no fitting across sets): estimate honest spike persistence h2c and the
                 repeat-spike log-LR on the calibration split; if log-LR > 0 and h2c < median-honest-reference
                 -> top-3 sum, elif log-LR > 0 -> 2nd-max, else max; CUSUM k is never picked by this rule
- meta (LOSO)    ridge regression of each rule's TPR gain over max on calibration-split features
                 (h2c, repeat-spike LR, first-spike LR, honest lag-1 autocorrelation, log length ratio, emp gains),
                 trained on all OTHER stream sets (leave-one-set-out); picks the argmax predicted gain if > 0
- oracle                           best rule on the held-out attacks (hindsight upper bound)

    uv run python tracks/r2_t1/chooser.py [--n-lab 20] [--splits 20] [--sets r1,mb,r2ps,mole]
Outputs results/r2_t1/chooser_*.csv and a summary markdown table.
"""
from __future__ import annotations

import argparse
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "t1_matched_budget"))

from amd.common.schema import REPO  # noqa: E402
from amd.detectors import CUSUM, KthLargest, Max, TopKSum, Whiten  # noqa: E402
from amd.detectors.base import pack  # noqa: E402
from amd.evaluation import calibrate, crossfit_models  # noqa: E402
from amd.evaluation.matched import _split, score_with_models  # noqa: E402

OUT = REPO / "results" / "r2_t1"
RAW = REPO / "data" / "raw" / "r2_t1" / "chooser"
SPLITS_OUT = REPO / "data" / "raw" / "r2_t1" / "chooser_out"   # large split-level CSVs (not committed)
K_GRID = (0.5, 1.0, 1.5, 2.0, 2.5)
ALPHAS = (0.05, 0.01)


def rules() -> dict:
    r = {"max": Max(), "kth2": KthLargest(2), "top3sum": TopKSum(3, transform=Whiten())}
    for k in K_GRID:
        r[f"cusum_k{k:g}"] = CUSUM(k=k, transform=Whiten())
    return r


RULES = list(rules())


# ------------------------------------------------------------------------------------------- features
def spike_features(H, A, q=0.95):
    """Honest spike persistence and attack repeat-spike informativeness (as in t1 mechanism.py), plus honest
    lag-1 autocorrelation of mid-p probit-whitened units and the log mean-length ratio."""
    hu = np.concatenate([s[np.isfinite(s)] for s in H])
    thr = np.quantile(hu, q)
    if (hu > thr).mean() < 0.005:
        vals = np.unique(hu)
        thr = vals[max(0, np.searchsorted(vals, thr) - 1)]
    cnt = lambda S: np.array([np.sum(s[np.isfinite(s)] > thr) for s in S])  # noqa: E731
    ch, ca = cnt(H), cnt(A)
    eps_h, eps_a = 0.5 / len(H), 0.5 / max(len(A), 1)
    h1, a1 = (ch >= 1).mean(), (ca >= 1).mean()
    h2c = ((ch >= 2).sum() + 0.5) / ((ch >= 1).sum() + 1)
    a2c = ((ca >= 2).sum() + 0.5) / ((ca >= 1).sum() + 1)
    # lag-1 autocorrelation of whitened honest units
    hs = np.sort(hu)
    n = len(hs)
    from scipy.stats import norm

    def z(s):
        x = s[np.isfinite(s)]
        gt = n - np.searchsorted(hs, x, side="right")
        eq = np.searchsorted(hs, x, side="right") - np.searchsorted(hs, x, side="left")
        return norm.isf((gt + (eq + 1) / 2) / (n + 1))
    Z = [z(s) for s in H]
    allz = np.concatenate(Z)
    mu, var = allz.mean(), allz.var()
    num = sum(((v[:-1] - mu) * (v[1:] - mu)).sum() for v in Z if len(v) > 1)
    cntp = sum(len(v) - 1 for v in Z if len(v) > 1)
    ac1 = num / cntp / var if cntp and var > 0 else 0.0
    lh = np.mean([np.isfinite(s).sum() for s in H])
    la = np.mean([np.isfinite(s).sum() for s in A]) if len(A) else lh
    return dict(h2c=h2c, rep_lr=np.log(a2c / h2c), first_lr=np.log((a1 + eps_a) / (h1 + eps_h)), ac1=ac1,
                log_len_ratio=np.log(la / lh), mean_len=lh)


# ------------------------------------------------------------------------------------------- per-set splits
def run_set(ss, n_lab=20, n_splits=20, seed=0, alphas=ALPHAS):
    """For each split: per-rule (a) labeled-attack TPRs at alpha' grid, (b) held-out attack TPR, honest-test FPR,
    and the calibration-split features. Returns a long frame (split x rule x alpha) and a split-feature frame."""
    rng = np.random.default_rng(seed)
    R = rules()
    rows, feats = [], []
    n_a = len(ss.attack)
    lab_n = min(n_lab, max(5, n_a // 3))
    for sp in range(n_splits):
        cal_idx, test_idx = _split(len(ss.honest), 0.5, rng, ss.honest_groups)
        lab = rng.choice(n_a, lab_n, replace=False)
        rest = np.setdiff1d(np.arange(n_a), lab)
        H = [ss.honest[i] for i in cal_idx]
        Ht = [ss.honest[i] for i in test_idx]
        Al = [ss.attack[i] for i in lab]
        At = [ss.attack[i] for i in rest]
        f = spike_features(H, Al)
        f.update(split=sp, n_lab=lab_n)
        Ph, Pht, Pal, Pat = pack(H), pack(Ht), pack(Al), pack(At)
        for name, det in R.items():
            models, cal_s = crossfit_models(det, Ph, 5, rng)
            s_ht = score_with_models(models, Pht, rng)
            s_al = score_with_models(models, Pal, rng)
            s_at = score_with_models(models, Pat, rng)
            for a in alphas:
                thr = calibrate(cal_s, a, "randomized")
                emp = np.mean([calibrate(cal_s, min(a * m, 0.2), "randomized").rate(s_al) for m in (1, 2, 5)])
                rows.append(dict(set=ss.name, split=sp, rule=name, alpha=a, tpr=thr.rate(s_at),
                                 fpr=thr.rate(s_ht), emp=emp, emp_at_alpha=thr.rate(s_al)))
        feats.append(f)
    return pd.DataFrame(rows), pd.DataFrame(feats).assign(set=ss.name)


# ------------------------------------------------------------------------------------------- choosers
def choose_emp(g: pd.DataFrame, n_lab: int) -> str:
    e = g.set_index("rule").emp
    best = e.idxmax()
    return best if e[best] - e["max"] > 1.0 / n_lab else "max"


def choose_mech(f: dict, h2c_ref: float) -> str:
    if f["rep_lr"] > 0 and f["h2c"] < h2c_ref:
        return "top3sum"
    if f["rep_lr"] > 0:
        return "kth2"
    return "max"


FEATS = ["h2c", "rep_lr", "first_lr", "ac1", "log_len_ratio"]


def meta_design(f: pd.Series, emp_gain: pd.Series) -> np.ndarray:
    return np.r_[1.0, [f[c] for c in FEATS], emp_gain.reindex(RULES).fillna(0).to_numpy()]


def evaluate(long: pd.DataFrame, feats: pd.DataFrame, ridge=1.0) -> pd.DataFrame:
    """Apply every chooser to every (set, split, alpha); meta is leave-one-set-out."""
    sets = sorted(long.set.unique())
    h2c_ref = feats.groupby("set").h2c.mean().median()
    # set-level training targets for meta: mean held-out TPR gain over max per rule
    tpr = long.groupby(["set", "alpha", "rule"]).tpr.mean().unstack("rule")
    gain = tpr.sub(tpr["max"], axis=0)
    # set-level features for training (mean over splits of calibration-split features + emp gains)
    emp = long.groupby(["set", "alpha", "rule"]).emp.mean().unstack("rule")
    emp_gain = emp.sub(emp["max"], axis=0)
    fset = feats.groupby("set")[FEATS].mean()
    out = []
    for a in sorted(long.alpha.unique()):
        La = long[long.alpha == a]
        for s in sets:
            train = [x for x in sets if x != s]
            X = np.array([meta_design(fset.loc[x], emp_gain.loc[(x, a)]) for x in train])
            mu, sd = X[:, 1:].mean(0), X[:, 1:].std(0) + 1e-9
            Xs = np.c_[X[:, :1], (X[:, 1:] - mu) / sd]
            coefs = {}
            for r in RULES:
                if r == "max":
                    continue
                y = gain.loc[[(x, a) for x in train], r].to_numpy()
                lam = ridge * np.eye(Xs.shape[1]); lam[0, 0] = 0
                coefs[r] = np.linalg.solve(Xs.T @ Xs + lam, Xs.T @ y)
            Ls = La[La.set == s]
            for sp, g in Ls.groupby("split"):
                f = feats[(feats.set == s) & (feats.split == sp)].iloc[0]
                n_lab = int(f.n_lab)
                t = g.set_index("rule").tpr
                eg = g.set_index("rule").emp
                eg = eg - eg["max"]
                x = meta_design(f, eg)
                xs = np.r_[x[:1], (x[1:] - mu) / sd]
                pred = {r: float(xs @ c) for r, c in coefs.items()}
                rb = max(pred, key=pred.get)
                picks = {"always_max": "max", "emp": choose_emp(g, n_lab), "mech": choose_mech(f, h2c_ref),
                         "meta": rb if pred[rb] > 0 else "max", "oracle": t.idxmax()}
                # best fixed CUSUM k chosen on labeled attacks only (CUSUM-tuned arm)
                ck = g[g.rule.str.startswith("cusum")].set_index("rule").emp.idxmax()
                picks["cusum_tuned"] = ck
                for r in ("kth2", "top3sum", "cusum_k1.5", "cusum_k0.5"):
                    picks[f"always_{r}"] = r
                for ch, r in picks.items():
                    out.append(dict(set=s, alpha=a, split=sp, chooser=ch, rule=r, tpr=t[r],
                                    fpr=g.set_index("rule").fpr[r], tpr_max=t["max"], tpr_oracle=t.max()))
    return pd.DataFrame(out)


def summarize(ev: pd.DataFrame) -> pd.DataFrame:
    per_set = ev.groupby(["alpha", "chooser", "set"]).agg(tpr=("tpr", "mean"), tpr_max=("tpr_max", "mean"),
                                                         tpr_oracle=("tpr_oracle", "mean"), fpr=("fpr", "mean"))
    per_set = per_set.reset_index()
    per_set["gain"] = per_set.tpr - per_set.tpr_max
    per_set["regret"] = per_set.tpr_oracle - per_set.tpr
    rng = np.random.default_rng(0)
    rows = []
    for (a, ch), g in per_set.groupby(["alpha", "chooser"]):
        d = g.gain.to_numpy()
        bs = d[rng.integers(len(d), size=(4000, len(d)))].mean(1)
        rows.append(dict(alpha=a, chooser=ch, n_sets=len(g), mean_tpr=g.tpr.mean(), mean_gain_vs_max=d.mean(),
                         gain_lo=np.quantile(bs, 0.025), gain_hi=np.quantile(bs, 0.975),
                         mean_regret_vs_oracle=g.regret.mean(), win=(d > 0.005).sum(), loss=(d < -0.005).sum(),
                         worst_set_gain=d.min(), mean_fpr=g.fpr.mean()))
    return pd.DataFrame(rows), per_set


# ------------------------------------------------------------------------------------------- sets
def collect_sets(which: list[str]):
    out = []
    if "r1" in which:
        from run_round1 import akshn_sets, la_sets, mrt_sets, ps_sets
        for f in (la_sets, akshn_sets, mrt_sets, ps_sets):
            out += f()
    if "mb" in which:
        from run_round2 import load_mode
        for model, modes in (("openai_gpt-4.1-mini", ("full", "none")), ("openai_gpt-4.1-nano", ("none",))):
            for score in ("expected", "int"):
                for m in modes:
                    try:
                        ss = load_mode(m, score=score, model=model)
                    except FileNotFoundError:
                        continue
                    ss.name = f"mb:{model.split('_')[-1]}:{m}:{score}"
                    out.append(ss)
    if "r2ps" in which:
        from ps_sets import r2_ps_sets
        out += r2_ps_sets(include_orig=False)
    if "mole" in which:
        from mole_sets import mole_stream_sets
        out += mole_stream_sets()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="r1,mb")
    ap.add_argument("--n-lab", type=int, default=20)
    ap.add_argument("--splits", type=int, default=20)
    ap.add_argument("--tag", default="")
    ap.add_argument("--reuse", action="store_true", help="reuse cached per-set split results")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    sets = collect_sets(a.sets.split(","))
    print(f"{len(sets)} sets", flush=True)
    longs, feats = [], []
    for ss in sets:
        if len(ss.attack) < 15 or len(ss.honest) < 40:
            print(f"  skip {ss.name}: n_h={len(ss.honest)} n_a={len(ss.attack)}")
            continue
        f = RAW / f"{ss.name.replace(':', '__').replace('/', '_')}__lab{a.n_lab}_s{a.splits}.pkl"
        if a.reuse and f.exists():
            L, F = pickle.loads(f.read_bytes())
        else:
            t0 = time.time()
            L, F = run_set(ss, n_lab=a.n_lab, n_splits=a.splits)
            f.write_bytes(pickle.dumps((L, F)))
            print(f"  {ss.name}: n_h={len(ss.honest)} n_a={len(ss.attack)} {time.time() - t0:.0f}s", flush=True)
        longs.append(L); feats.append(F)
    long, feat = pd.concat(longs), pd.concat(feats)
    ev = evaluate(long, feat)
    summ, per_set = summarize(ev)
    tag = a.tag or f"lab{a.n_lab}"
    SPLITS_OUT.mkdir(parents=True, exist_ok=True)
    long.to_csv(SPLITS_OUT / f"chooser_rules_{tag}.csv", index=False)
    feat.to_csv(OUT / f"chooser_features_{tag}.csv", index=False)
    ev.to_csv(SPLITS_OUT / f"chooser_picks_{tag}.csv", index=False)
    per_set.to_csv(OUT / f"chooser_per_set_{tag}.csv", index=False)
    summ.to_csv(OUT / f"chooser_summary_{tag}.csv", index=False)
    print(summ.round(3).to_string())


if __name__ == "__main__":
    main()
