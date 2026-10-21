"""Shared helpers for the T3 audit fixes (round 1 and round 2).

Fixes implemented here (used by fix_r2_t3.py and fix_t3_round1.py):

* m6 -- submit-step stripping. The project's `_submit_last_idx` also strips the last refined step
  when the ORIGINAL trajectory's meta says `submit_step == len(refined) - 1`, even if that refined
  step is not a submit call. `strip_submit_fixed` strips only when the refined trajectory's last
  action really is a submit call (and the score stream covers that step). Honest and original
  streams are unaffected (their meta rule and their last action agree; checked in the scripts).

* M2 -- validity. Besides the LLM-judge flag (`meta.valid`, the project's validity), every refined
  trajectory gets
    strict     = judge AND every target literal still appears verbatim in the refined actions
                 (`meta.literals_missing` empty; recomputed with the project's `_literal_check`
                 rule for the 4 round-1 trajectories per arm that lack the field),
    strict_rel = judge AND every target literal that appears in the ORIGINAL attack's own actions
                 is preserved. 28/150 originals (all side-task-successful) do not contain every
                 target literal in their actions, so `strict` also fails rewrites for literals the
                 successful original never wrote; `strict_rel` is the symmetric lower bound when a
                 rewritten arm is compared with the originals (which count as valid).

* m5 -- joint bootstrap. `alarm_engine` refits every deployed detector (whitening, multichart tail
  fits) and recomputes the randomized threshold on a resampled Honest-550 in every replicate; the
  analysis code pairs that with an independent resample of base attacks (one joint draw per
  replicate). `holdout_fpr` reports realized FPR on held-out honest runs under 50/50 splits.

Run nothing here directly; see fix_r2_t3.py / fix_t3_round1.py.
"""
from __future__ import annotations

import ast

import numpy as np

from amd.common.schema import PROCESSED, load_scores, load_trajectories
from amd.evaluation import calibrate


# ------------------------------------------------------------------------------- literals / validity

def target_literals(meta: dict) -> list[str]:
    """Same literal list as tracks/t3_aware_attacker/refine.py::_literal_check."""
    lits = []
    raw = meta.get("target_literals")
    if raw:
        try:
            lits = [str(x) for x in (ast.literal_eval(raw) if isinstance(raw, str) else raw)]
        except Exception:  # noqa: BLE001
            lits = []
    fal = meta.get("first_attack_step_literal")
    if fal and str(fal) not in lits:
        lits.append(str(fal))
    return [x for x in dict.fromkeys(lits) if len(x) >= 4]


def action_blob(traj) -> str:
    return "\n".join(s.action for s in traj.steps)


def originals_by_id():
    return {t.traj_id: t for t in load_trajectories("monitoringbench")}


def is_submit(action) -> bool:
    return str(action).strip().lower().startswith("submit")


def strip_submit_fixed(traj, scores: list) -> tuple[list, bool]:
    """Strip the last score only if the last action is a real submit call. Returns (scores, stripped)."""
    if traj.steps and is_submit(traj.steps[-1].action) and len(scores) == len(traj.steps) and scores:
        return scores[:-1], True
    return scores, False


def project_strip_idx(traj):
    """The project's rule (tracks/r2_t3/evaluate_r2.py::_submit_last_idx), for change counting."""
    if traj.steps and is_submit(traj.steps[-1].action):
        return len(traj.steps) - 1
    if traj.meta.get("ends_with_submit"):
        si = traj.meta.get("submit_step")
        si = int(si) if si is not None else (len(traj.steps) - 1)
        if si == len(traj.steps) - 1 and si < 60:
            return si
    return None


def load_refined_arm(src: str, score_file: str, orig: dict) -> dict:
    """orig_traj_id -> dict(stream (fixed stripping), stream_proj (project stripping), valid, strict,
    strict_rel, changed, agent_model). `src` is relative to data/processed."""
    p = PROCESSED / src / score_file
    if not p.exists():
        return {}
    trajs = {t.traj_id: t for t in load_trajectories(src)}
    out = {}
    for s in load_scores(src, p.name):
        t = trajs.get(s.traj_id)
        if t is None:
            continue
        sc = list(s.scores)
        fixed, _ = strip_submit_fixed(t, sc)
        si = project_strip_idx(t)
        proj = sc[:-1] if (si is not None and si == len(sc) - 1 and sc) else sc
        oid = t.meta["orig_traj_id"]
        lits = target_literals(t.meta)
        blob = action_blob(t)
        missing = [x for x in lits if x not in blob]
        if "literals_missing" in t.meta:
            assert list(t.meta["literals_missing"]) == missing, (src, s.traj_id)
        o = orig.get(oid)
        oblob = action_blob(o) if o is not None else ""
        missing_rel = [x for x in missing if x in oblob]
        v = 1.0 if t.meta.get("valid") else 0.0
        out[oid] = dict(stream=fixed, stream_proj=proj, valid=v,
                        strict=v * (0.0 if missing else 1.0),
                        strict_rel=v * (0.0 if missing_rel else 1.0),
                        changed=(len(fixed) != len(proj)),
                        has_meta_literals=("literals_missing" in t.meta),
                        agent_model=str(t.context.get("agent_model", "")),
                        n_steps=len(t.steps))
    return out


VALIDITIES = ("valid", "strict", "strict_rel")
VLABEL = {"valid": "judge-only", "strict": "strict (judge + all literals)",
          "strict_rel": "strict-rel (judge + literals present in original)"}


# ------------------------------------------------------------------------------- alarm engine

def alarm_engine(honest: list, streams: list, det_factory, det_names, alphas, B: int, seed: int,
                 log_every: int = 250):
    """Alarm probabilities for every stream.

    Returns P0 (n_det, n_alpha, n_streams) with detectors fit + randomized-calibrated on all of
    `honest`, and P (B, n_det, n_alpha, n_streams) float32, where replicate b fits and calibrates
    on a with-replacement resample of `honest` (indices `hidx[b]`)."""
    nH = len(honest)
    rng = np.random.default_rng(seed)
    hidx = rng.integers(0, nH, size=(B, nH))
    P0 = np.zeros((len(det_names), len(alphas), len(streams)))
    for d, dn in enumerate(det_names):
        det = det_factory(dn).fit(honest)
        cal = det.stats(honest)
        st = det.stats(streams)
        for a, al in enumerate(alphas):
            P0[d, a] = calibrate(cal, al, method="randomized").alarm_prob(st)
    P = np.zeros((B, len(det_names), len(alphas), len(streams)), np.float32)
    for b in range(B):
        Hb = [honest[j] for j in hidx[b]]
        for d, dn in enumerate(det_names):
            det = det_factory(dn).fit(Hb)
            cal = det.stats(Hb)
            st = det.stats(streams)
            for a, al in enumerate(alphas):
                P[b, d, a] = calibrate(cal, al, method="randomized").alarm_prob(st)
        if log_every and (b + 1) % log_every == 0:
            print(f"  joint bootstrap replicate {b + 1}/{B}", flush=True)
    return P0, P, hidx


def holdout_fpr(honest: list, det_factory, det_names, alphas, R: int = 200, seed: int = 11):
    """Calibrate on a random half of the honest runs, measure realized FPR on the other half."""
    rng = np.random.default_rng(seed)
    nH = len(honest)
    rows = []
    res = {(dn, al): [] for dn in det_names for al in alphas}
    for r in range(R):
        perm = rng.permutation(nH)
        A = [honest[j] for j in perm[: nH // 2]]
        Bh = [honest[j] for j in perm[nH // 2:]]
        for dn in det_names:
            det = det_factory(dn).fit(A)
            ca, cb = det.stats(A), det.stats(Bh)
            for al in alphas:
                res[(dn, al)].append(calibrate(ca, al, method="randomized").rate(cb))
    for (dn, al), v in res.items():
        v = np.array(v)
        rows.append(dict(detector=dn, alpha=al, n_cal=nH // 2, n_test=nH - nH // 2, splits=R,
                         realized_fpr_mean=float(v.mean()), realized_fpr_sd=float(v.std()),
                         realized_fpr_q05=float(np.quantile(v, .05)),
                         realized_fpr_q95=float(np.quantile(v, .95)),
                         ratio_to_nominal=float(v.mean() / al)))
    return rows


# ------------------------------------------------------------------------------- summaries

def boot_p(db: np.ndarray) -> float:
    """Two-sided percentile-bootstrap p-value for H0: diff = 0."""
    B = len(db)
    lo = (np.sum(db <= 0) + 1) / (B + 1)
    hi = (np.sum(db >= 0) + 1) / (B + 1)
    return float(min(1.0, 2 * min(lo, hi)))


def holm(pvals) -> np.ndarray:
    p = np.asarray(pvals, float)
    m = len(p)
    order = np.argsort(p)
    adj = np.empty(m)
    run = 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * p[i]))
        adj[i] = run
    return adj


def fmt_ci(x, lo, hi, signed=False):
    f = "{:+.3f}" if signed else "{:.3f}"
    return f"{f.format(x)} [{f.format(lo)}, {f.format(hi)}]"
