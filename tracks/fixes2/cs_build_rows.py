"""Assemble results/fixes2/rows_cs.csv (old = plug-in convention, new = conformal randomized) from the outputs of
cs_ps_multi_thrfix, cs_indep_ps_thrfix and cs_overview_thrfix (run each with `plugin` and `conformal` first).

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.cs_build_rows
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from amd.common.schema import REPO

F2 = REPO / "results" / "fixes2"
REF = "gpt-4o (orig, ref)"


def ci(lo, hi):
    return f"[{lo:+.3f}, {hi:+.3f}]"


def fpr(a, b):
    return f"max {a:.4f} / accumulator {b:.4f}"


def ps_multi(conv):
    d = F2 / f"cs_ps_multi_{conv}_thrfix"
    MT, G, M = (pd.read_csv(d / f) for f in ("ps_meta.csv", "ps_gains.csv", "ps_matched.csv"))
    r = MT[(MT.variant == "main") & (MT.alpha == 0.05) & (MT.detector == "top3sum") & (MT.cluster == "app")].iloc[0]
    g = G[(G.variant == "main") & (G.alpha == 0.05) & (G.detector == "top3sum") & (G.cluster == "app")
          & (G.monitor != REF)].copy()
    g["p"] = np.maximum(2 * np.minimum(g.p_le0, g.p_ge0), 1 / g.n_boot)   # two-sided bootstrap p, floor 1/B
    g = g.sort_values("p")
    k = len(g)
    g["p_holm"] = np.maximum.accumulate(np.minimum(1, (k - np.arange(k)) * g.p.to_numpy()))
    m = M[(M.variant == "main") & (M.alpha == 0.05) & (M.threshold_kind == "calibrated") & (M.monitor != REF)]
    f = (m[m.detector == "max"].fpr.mean(), m[m.detector == "top3sum"].fpr.mean())
    return r, g.set_index("monitor"), f


def indep(conv):
    d = F2 / f"cs_indep_ps_{conv}_thrfix"
    P, R = pd.read_csv(d / "cs_indep_ps_pooled.csv"), pd.read_csv(d / "cs_indep_ps.csv")
    p = P[(P.alpha == 0.05) & (P.scheme == "app_indep")].iloc[0]
    r = R[(R.alpha == 0.05) & (R.scheme == "app_indep")]
    return p, (r.fpr_max.mean(), r.fpr_top3.mean())


def ov(conv, part):
    return pd.read_csv(F2 / f"cs_overview_{conv}_thrfix" / f"cs_overview_{part}.csv")


def main():
    rows = []
    (ro, go, fo), (rn, gn, fn) = ps_multi("plugin"), ps_multi("conformal")
    rows.append(dict(
        claim="r4_cs pooled top-3 sum - max, 9 identical-input monitors, FPR 0.05 (pre-specified primary; committed "
              "ps_multi, RE pool, joint app-clustered bootstrap)",
        old_estimate=f"{ro.re_mu:+.3f}", old_ci=ci(ro.joint_lo, ro.joint_hi), new_estimate=f"{rn.re_mu:+.3f}",
        new_ci=ci(rn.joint_lo, rn.joint_hi), old_realized_fpr=fpr(*fo), new_realized_fpr=fpr(*fn),
        verdict_change="no",
        note=f"Convention applies (matched_budget_eval + paired_contrast_bootstrap, method='randomized'). n_cal = 76 "
             f"(alpha*n = 3.8, not an integer) so the plug-in excess is small: mean realized FPR of max "
             f"{fo[0]:.3f} -> {fn[0]:.3f}. Still negative, CI covers 0; HKSJ {ci(rn.hksj_lo, rn.hksj_hi)}; "
             f"unadjusted sig +/-: {int(ro.n_sig_pos)}/{int(ro.n_sig_neg)} -> {int(rn.n_sig_pos)}/{int(rn.n_sig_neg)}."))
    (po, fpo), (pn, fpn) = indep("plugin"), indep("conformal")
    rows.append(dict(
        claim="r4_cs pooled top-3 sum - max, FPR 0.05, audit-3 independent re-implementation (cs_indep_ps, app_indep)",
        old_estimate=f"{po.re_mu:+.3f}", old_ci=ci(po.joint_lo, po.joint_hi), new_estimate=f"{pn.re_mu:+.3f}",
        new_ci=ci(pn.joint_lo, pn.joint_hi), old_realized_fpr=fpr(*fpo), new_realized_fpr=fpr(*fpn),
        verdict_change="no",
        note="cs_indep_ps has its own vectorized plug-in rule (rand_thr / alarm); the flag does not reach it, so both "
             "functions were monkeypatched with amd smoothed_rows_shared (same integer bootstrap multiplicities). "
             "Audit wording 'Pooled -0.07 [-0.14, +0.02]' still holds."))
    lo_, ln_ = go.loc["gpt-6-luna"], gn.loc["gpt-6-luna"]
    ho, hn = go.loc["claude-haiku-5.5"], gn.loc["claude-haiku-5.5"]
    mo, mn = go.loc["gpt-4.1-mini"], gn.loc["gpt-4.1-mini"]
    rows.append(dict(
        claim="r4_cs per-monitor top-3 sum - max at FPR 0.05, Holm over 9 monitors (app bootstrap, two-sided p = "
              "2 min(p_le0, p_ge0), floor 1/B)",
        old_estimate=f"Holm-significant: Luna only ({lo_.est:+.3f}, p_Holm {lo_.p_holm:.4f}); Haiku 5.5 {ho.est:+.3f} "
                     f"p_Holm {ho.p_holm:.3f}",
        old_ci=f"Luna {ci(lo_.lo, lo_.hi)}; Haiku 5.5 {ci(ho.lo, ho.hi)}",
        new_estimate=f"Holm-significant: Luna only ({ln_.est:+.3f}, p_Holm {ln_.p_holm:.4f}); Haiku 5.5 {hn.est:+.3f} "
                     f"p_Holm {hn.p_holm:.3f}",
        new_ci=f"Luna {ci(ln_.lo, ln_.hi)}; Haiku 5.5 {ci(hn.lo, hn.hi)}",
        old_realized_fpr=fpr(*fo), new_realized_fpr=fpr(*fn), verdict_change="no",
        note=f"Holm set unchanged (Luna only). Unadjusted, gpt-4.1-mini's app CI moves from {ci(mo.lo, mo.hi)} to "
             f"{ci(mn.lo, mn.hi)} (p_Holm {mo.p_holm:.2f} -> {mn.p_holm:.2f}), so 'no monitor has a significant "
             "(unadjusted) gain' would become 1; it does not survive Holm, and audit 3 showed this gain exists only "
             "with the logprob-expected read-out."))
    for part, claim, old_claim in (
            ("ps", "ps_gpt4o_top3_minus_max_fpr05",
             "Idea 1 overview: persistent state GPT-4o history-free top-3 sum - max, FPR 0.05 (fixes C2, t1 r1)"),
            ("ps", "ps_gpt41mini_top3_minus_max_fpr05",
             "Idea 1 overview: persistent state gpt-4.1-mini history-free top-3 sum - max, FPR 0.05 (fixes C2, r2_t1)")):
        o, n = ov("plugin", part).set_index("claim").loc[claim], ov("conformal", part).set_index("claim").loc[claim]
        change = "yes" if (o.lo > 0) != (n.lo > 0) else "no"
        note = (f"Recomputed from the saved matched-eval raws with c2_gains.contrast_row (iid bootstrap, B = 1000; "
                f"convention applies). App-cluster sensitivity {ci(o.sens_lo, o.sens_hi)} -> {ci(n.sens_lo, n.sens_hi)}. ")
        if claim.startswith("ps_gpt4o"):
            note += ("Gain shrinks by 0.013 (max TPR 0.163 -> 0.157, top-3 0.310 -> 0.291) and stays significant; "
                     "realized FPR is above nominal under both rules (n_cal 84, 10 splits; the conformal excess is within split noise, SE ~0.01).")
        else:
            note += ("Knife-edge: the lower bound crosses 0 (-0.001 -> +0.007), so 'not significant at 95%' becomes "
                     "barely significant (p(<=0) 0.026 -> 0.018); the app-cluster sensitivity still covers 0 and "
                     "the r4_cs common-run-set version (cs_ps_multi) moves the same way. Point estimate unchanged.")
        rows.append(dict(claim=old_claim, old_estimate=f"{o.est:+.3f}", old_ci=ci(o.lo, o.hi),
                         new_estimate=f"{n.est:+.3f}", new_ci=ci(n.lo, n.hi), old_realized_fpr=fpr(o.fpr_max, o.fpr_det),
                         new_realized_fpr=fpr(n.fpr_max, n.fpr_det), verdict_change=change, note=note))
    o, n = ov("plugin", "mole").iloc[0], ov("conformal", "mole").iloc[0]
    rows.append(dict(
        claim="Idea 1 overview: MOLE pooled single-day 3rd-max - max, account FPR 0.10 (r3_t1, qwen_int, RE over 4 corpora)",
        old_estimate=f"{o.est:+.3f}", old_ci=ci(o.lo, o.hi), new_estimate=f"{n.est:+.3f}", new_ci=ci(n.lo, n.hi),
        old_realized_fpr=fpr(o.fpr_max, o.fpr_det), new_realized_fpr=fpr(n.fpr_max, n.fpr_det), verdict_change="no",
        note="Convention applies (r3_t1 run_matched + r3lib.gains_full, method='randomized'; integer scores, 56 "
             "calibration accounts at alpha*n = 5.6). Per-corpus matched evals rerun with the original seeds; "
             "pooled with mole_r3_analysis.pooled. Negligible change."))
    o, n = ov("plugin", "chooser").iloc[0], ov("conformal", "chooser").iloc[0]
    rows.append(dict(
        claim="Idea 1 overview: rule chooser (emp) vs always-max, nested calibration, FPR 0.01 (fixes M6, 67 sets, "
              "family-cluster CI)",
        old_estimate=f"{o.est:+.3f}", old_ci=ci(o.lo, o.hi), new_estimate=f"{n.est:+.3f}", new_ci=ci(n.lo, n.hi),
        old_realized_fpr=f"chooser {o.fpr_det:.4f} / always-max {o.fpr_max:.4f}",
        new_realized_fpr=f"chooser {n.fpr_det:.4f} / always-max {n.fpr_max:.4f}", verdict_change="no",
        note="Convention applies (calibrate(..., 'randomized') in chooser_fixed.run_set; ProcessPool children get it "
             "via AMD_THRESHOLD_CONVENTION). The nested design thresholds on a quarter of the honest set, where the "
             "plug-in rule ran BOTH arms at ~2x nominal (2.04% at 1%); conformal brings both to 1.01%. Gain stays "
             "~0, CI narrower; 'dropped' verdict unchanged."))
    out = pd.DataFrame(rows)
    out.to_csv(F2 / "rows_cs.csv", index=False)
    print(out.drop(columns="note").to_string())


if __name__ == "__main__":
    main()
