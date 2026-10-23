"""Assemble results/fixes2/rows_rep.csv (r4_replay + Idea-3 overview headlines, plug-in vs conformal randomized
threshold) from the rerun outputs of rep_r4_analyze_thrfix, rep_r4_independent_thrfix, rep_idea3_r3t3_thrfix,
rep_idea3_fix_r2t3_thrfix and rep_fpr_thrfix. Old numbers are the plug-in reruns (checked identical to the
committed tables in the log printed here).

    unset VIRTUAL_ENV; uv run python -m tracks.fixes2.rep_rows_thrfix
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from tracks.fixes2.rep_thrfix_lib import OUT, REPO

COLS = ["claim", "old_estimate", "old_ci", "new_estimate", "new_ci", "old_realized_fpr", "new_realized_fpr",
        "verdict_change", "note"]


def ci(lo, hi):
    return f"[{lo:+.3f}, {hi:+.3f}]"


def sig(lo, hi):
    return lo > 0 or hi < 0


def main():
    rows = []
    # ---------------- checks: plug-in reruns == committed tables
    chk = {}
    for f in ("paired_contrasts.md", "reproduction.md", "agreement.md"):
        chk[f"r4_replay/{f}"] = (REPO / "results/r4_replay" / f).read_text() == \
            (OUT / "rep_r4_analyze_plugin_thrfix" / f).read_text()
    chk["r3_t3/paired_contrasts.md"] = (REPO / "results/r3_t3/paired_contrasts.md").read_text() == \
        (OUT / "rep_r3t3_plugin_thrfix/paired_contrasts.md").read_text()
    for f in ("rep_r4_contrasts.csv", "rep_r4_multiplicity.csv", "rep_r4_realized_fpr.csv"):
        a = pd.read_csv(REPO / "results/audit3" / f).select_dtypes("number")
        b = pd.read_csv(OUT / "rep_r4_indep_plugin_thrfix" / f).select_dtypes("number")
        chk[f"audit3/{f}"] = bool(a.shape == b.shape and np.allclose(a.values, b.values, equal_nan=True))
    a = pd.read_csv(REPO / "results/audit2/repro_t3r3.csv").select_dtypes("number")
    b = pd.read_csv(OUT / "rep_audit2_t3r3_plugin_thrfix/repro_t3r3.csv").select_dtypes("number")
    chk["audit2/repro_t3r3.csv"] = bool(np.allclose(a.values, b.values))
    for f in ("primary_contrast.csv", "contrasts.csv", "m5_holdout_fpr.csv"):
        a = pd.read_csv(REPO / "results/fixes/r2_t3" / f).select_dtypes("number")
        b = pd.read_csv(OUT / "rep_fix_r2t3_plugin_thrfix/r2_t3" / f).select_dtypes("number")
        chk[f"fixes/r2_t3/{f}"] = bool(a.shape == b.shape and np.allclose(a.values, b.values, equal_nan=True))
    print("plug-in reproduction of committed outputs:", json.dumps(chk, indent=1))

    # ---------------- realized FPR (LOO / splits) of the full-550 max threshold
    fr = pd.read_csv(OUT / "rep_realized_fpr_thrfix.csv")

    def fpr(alpha, conv, stat="raw_max_550 (r4_replay, r3_t3, audit2)"):
        r = fr[(fr.statistic == stat) & (fr.alpha == alpha) & (fr.convention == conv)].iloc[0]
        return (f"LOO {r.loo_fpr:.4f} ({r.loo_ratio:.2f}x); 50/50 iid {r.split_iid_fpr:.4f} ({r.split_iid_ratio:.2f}x);"
                f" 50/50 task-grouped {r.split_task_fpr:.4f} ({r.split_task_ratio:.2f}x)")

    # ---------------- r4_replay: committed track pipeline
    def track(conv):
        return pd.DataFrame(json.loads((OUT / f"rep_r4_analyze_{conv}_thrfix/paired_contrasts.json").read_text()))

    T0, T1 = track("plugin"), track("conformal")

    def tsel(T, contrast, det="max", alpha=0.01, validity="exec"):
        return T[(T.validity == validity) & (T.contrast == contrast) & (T.detector == det) & (T.alpha == alpha)].iloc[0]

    def add_track(claim, contrast, alpha=0.01, note=""):
        o, n = tsel(T0, contrast, alpha=alpha), tsel(T1, contrast, alpha=alpha)
        vc = "yes" if sig(o.lo, o.hi) != sig(n.lo, n.hi) else "no"
        rows.append(dict(claim=claim, old_estimate=round(o.est, 3), old_ci=ci(o.lo, o.hi), new_estimate=round(n.est, 3),
                         new_ci=ci(n.lo, n.hi), old_realized_fpr=fpr(alpha, "plugin"),
                         new_realized_fpr=fpr(alpha, "conformal"), verdict_change=vc, note=note))

    conv_note = ("Convention applies: paired_contrast_bootstrap(method='randomized') follows the flag; one threshold on "
                 "all 550 honest runs (alpha n = 5.5 at 1%), so the rule moves by about one order statistic band. ")
    add_track("r4_replay PRIMARY (track analyze.py): rewrite_control - original, exec validity, max, alpha 0.01, n=28",
              "rewrite_control − original",
              note=conv_note + "Point unchanged (no attack in the moved band); CI upper +0.040 -> +0.032, still crosses 0: "
                               "negative but inconclusive. The track's printed realized-FPR column (0.0141) is an "
                               "np.quantile threshold on 50/50 splits, not the procedure used.")
    # independent audit analysis
    I0 = pd.read_csv(OUT / "rep_r4_indep_plugin_thrfix/rep_r4_contrasts.csv")
    I1 = pd.read_csv(OUT / "rep_r4_indep_conformal_thrfix/rep_r4_contrasts.csv")

    def isel(I, setname, contrast, kind="US", va="exec", vb="exec", alpha=0.01):
        return I[(I.set == setname) & (I.contrast == contrast) & (I.kind == kind) & (I.validity_a == va) &
                 (I.validity_b == vb) & (I.alpha == alpha)].iloc[0]

    def add_ind(claim, setname, contrast, kind="US", va="exec", vb="exec", alpha=0.01, note="", force_vc=None):
        o, n = isel(I0, setname, contrast, kind, va, vb, alpha), isel(I1, setname, contrast, kind, va, vb, alpha)
        vc = force_vc or ("yes" if sig(o.lo, o.hi) != sig(n.lo, n.hi) else "no")
        rows.append(dict(claim=claim, old_estimate=round(o.est, 3), old_ci=ci(o.lo, o.hi), new_estimate=round(n.est, 3),
                         new_ci=ci(n.lo, n.hi), old_realized_fpr=fpr(alpha, "plugin"),
                         new_realized_fpr=fpr(alpha, "conformal"), verdict_change=vc, note=note))

    a2note = ("Audit-3 independent code (tracks/audit3/rep_r4_independent.py) has its own plug-in copy (a2lib) which the "
              "flag does not reach; swapped for conformal_randomized_threshold (integer bootstrap weights) by "
              "monkeypatch. ")
    add_ind("r4_replay PRIMARY (audit-3 independent reimplementation), n=28", "n28_track", "rewrite_control - original",
            note=a2note + "Point unchanged; CI still crosses 0.")
    add_ind("r4_replay secondary: rewrite_control - original, all 33 pairs (exec, max, 0.01)", "n33_orig_ctrl",
            "rewrite_control - original",
            note=a2note + "Knife-edge claim: old CI upper bound sat exactly at 0.000; under the conformal rule one "
                          "original (honest-rank 5-6 gap) alarms with prob 0.51 instead of 1, raising US(original) by "
                          "0.015, so the CI now excludes 0 (upper -0.026). Marginal; the n=28 primary is unchanged.",
            force_vc=None)
    add_ind("r4_replay secondary: rewrite_control - original, no firewall (n=24 of the 33 pairs; exec, max, 0.01)",
            "n33_orig_ctrl_nofirewall", "rewrite_control - original",
            note=a2note + "Holds; slightly larger.")
    add_ind("r4_replay secondary: rewrite_control - original, no firewall (n=20 of the 28 primary pairs)",
            "n28_track_nofirewall", "rewrite_control - original",
            note=a2note + "Unchanged (CI still touches 0).")
    add_track("r4_replay secondary: pace_max - original (track, exec, max, 0.01, n=28)", "pace_max − original",
              note=conv_note + "Holds (significant both ways). Audit decomposition (independent code): validity part "
                               "-0.232 -> -0.241 (sig), detection part -0.089 -> -0.081 (n.s.): still validity loss.")
    add_track("r4_replay secondary: pace_max - rewrite_control (track, exec, max, 0.01, n=28)",
              "pace_max − rewrite_control", note=conv_note + "Unchanged; n.s.")
    # Holm over the 24 exec cells
    M = {c: pd.read_csv(OUT / f"rep_r4_indep_{c}_thrfix/rep_r4_multiplicity.csv") for c in ("plugin", "conformal")}
    mo, mn = M["plugin"], M["conformal"]
    eo, en = mo[mo.validity == "exec"], mn[mn.validity == "exec"]
    rows.append(dict(claim="r4_replay execution-validity cells (24 = 3 contrasts x 4 detectors x 2 alpha): # CI excl. 0 / "
                           "min Holm p / # Holm p<.05",
                     old_estimate=f"{int(eo.ci_excl0.sum())}/24; min Holm {eo.holm_exec_24.min():.3f}; "
                                  f"{int((eo.holm_exec_24 < .05).sum())} survive",
                     old_ci="", new_estimate=f"{int(en.ci_excl0.sum())}/24; min Holm {en.holm_exec_24.min():.3f}; "
                                             f"{int((en.holm_exec_24 < .05).sum())} survive",
                     new_ci="", old_realized_fpr=fpr(0.01, "plugin") + " | a=0.003: " + fpr(0.003, "plugin"),
                     new_realized_fpr=fpr(0.01, "conformal") + " | a=0.003: " + fpr(0.003, "conformal"),
                     verdict_change="no",
                     note="Same 5 cells exclude 0 (rewrite-original multichart 0.01; pace-original max/multichart at both "
                          "alphas); none survives Holm under either rule."))
    # realized FPR at 0.003 claim
    r3o = fr[(fr.statistic.str.startswith("raw")) & (fr.alpha == 0.003) & (fr.convention == "plugin")].iloc[0]
    r3n = fr[(fr.statistic.str.startswith("raw")) & (fr.alpha == 0.003) & (fr.convention == "conformal")].iloc[0]
    rows.append(dict(claim="r4_replay realized FPR at alpha 0.003 (max, procedure actually used): audit '1.2-1.5x nominal'",
                     old_estimate=f"{r3o.split_iid_ratio:.2f}x-{r3o.split_task_ratio:.2f}x (LOO {r3o.loo_ratio:.2f}x)",
                     old_ci="", new_estimate=f"{r3n.split_iid_ratio:.2f}x-{r3n.split_task_ratio:.2f}x (LOO {r3n.loo_ratio:.2f}x)",
                     new_ci="", old_realized_fpr=fpr(0.003, "plugin"), new_realized_fpr=fpr(0.003, "conformal"),
                     verdict_change="yes",
                     note="Threshold fit on all 550 honest runs, so realized FPR = LOO / 50/50-split estimates. The plug-in "
                          "excess at exchangeable (iid) splits (1.19-1.21x) is the convention bias and disappears (0.99-1.00x). "
                          "The task-grouped split stays 1.19x (was 1.48x): residual out-of-task shift, not the convention. "
                          "At alpha 0.01: LOO 1.09x -> 1.00x, task-grouped 1.22x -> 1.09x."))

    # ---------------- Idea 3 overview panel c
    def r3t3(conv):
        return pd.DataFrame(json.loads((OUT / f"rep_r3t3_{conv}_thrfix/paired_contrasts.json").read_text()))

    R0, R1 = r3t3("plugin"), r3t3("conformal")
    sel = lambda R: R[(R.contrast == "control/gemini − original") & (R.detector == "max") & (R.alpha == 0.01)].iloc[0]  # noqa: E731
    o, n = sel(R0), sel(R1)
    A0 = pd.read_csv(OUT / "rep_audit2_t3r3_plugin_thrfix/repro_t3r3.csv")
    A1 = pd.read_csv(OUT / "rep_audit2_t3r3_conformal_thrfix/repro_t3r3.csv")
    asel = lambda A, k, c="control/gemini - original": A[(A.contrast == c) & (A.kind == k)].iloc[0]  # noqa: E731
    ao, an_ = asel(A0, "strict_US"), asel(A1, "strict_US")
    rows.append(dict(claim="Idea 3 overview (c1): uninformed rewrite - original (gemini, strict), max, alpha 0.01, n=35 "
                           "(tracks/r3_t3/paired_contrasts.py)",
                     old_estimate=round(o.est, 3), old_ci=ci(o.lo, o.hi), new_estimate=round(n.est, 3), new_ci=ci(n.lo, n.hi),
                     old_realized_fpr=fpr(0.01, "plugin"), new_realized_fpr=fpr(0.01, "conformal"),
                     verdict_change="yes" if sig(o.lo, o.hi) != sig(n.lo, n.hi) else "no",
                     note=conv_note + f"Holds. One original sits in the honest rank-5/6 gap (alarm 1 -> 0.51), so US(original) "
                                      f"rises 0.014 and the contrast grows. audit2 independent repro (own a2lib plug-in, "
                                      f"monkeypatched): {ao.est:+.3f} {ci(ao.lo, ao.hi)} -> {an_.est:+.3f} {ci(an_.lo, an_.hi)}."))
    do, dn = asel(A0, "detection_only"), asel(A1, "detection_only")
    bo, bn = asel(A0, "both_valid_pairs"), asel(A1, "both_valid_pairs")
    rows.append(dict(claim="Idea 3 overview (c2): same, detection only (validity ignored), n=35 (tracks/audit2/repro_t3r3.py)",
                     old_estimate=round(do.est, 3), old_ci=ci(do.lo, do.hi), new_estimate=round(dn.est, 3),
                     new_ci=ci(dn.lo, dn.hi), old_realized_fpr=fpr(0.01, "plugin"),
                     new_realized_fpr=fpr(0.01, "conformal"),
                     verdict_change="yes" if sig(do.lo, do.hi) != sig(dn.lo, dn.hi) else "no",
                     note=a2note.replace("Audit-3 independent code (tracks/audit3/rep_r4_independent.py)",
                                         "audit2 repro_t3r3") +
                     f"Holds (still excludes 0). The overview label 'valid rewrites' is inaccurate: this row ignores "
                     f"validity (every rewrite counted); the both-strictly-valid-pairs row is {bo.est:+.3f} "
                     f"{ci(bo.lo, bo.hi)} -> {bn.est:+.3f} {ci(bn.lo, bn.hi)} (n={int(bn.n)})."))
    pr = {c: pd.read_csv(OUT / f"rep_fix_r2t3_{c}_thrfix/r2_t3/primary_contrast.csv").iloc[0] for c in ("plugin", "conformal")}
    hf = {c: pd.read_csv(OUT / f"rep_fix_r2t3_{c}_thrfix/r2_t3/m5_holdout_fpr.csv") for c in ("plugin", "conformal")}
    hfs = {c: hf[c][(hf[c].detector == "max") & (hf[c].alpha == 0.01)].iloc[0] for c in hf}
    po, pn = pr["plugin"], pr["conformal"]
    stat2 = "r2_t3_deployed_max_550"
    rows.append(dict(claim="Idea 3 overview (c3): pacing - uninformed rewrite (one-shot pace_max_r0 - rewrite_control, strict, "
                           "max, alpha 0.01, n=126; tracks/fixes/t3/fix_r2_t3.py pre-specified primary)",
                     old_estimate=round(po.value, 3), old_ci=ci(po.ci_joint_lo, po.ci_joint_hi),
                     new_estimate=round(pn.value, 3), new_ci=ci(pn.ci_joint_lo, pn.ci_joint_hi),
                     old_realized_fpr=fpr(0.01, "plugin", stat2) + f"; track m5 50/50 refit {hfs['plugin'].realized_fpr_mean:.4f}",
                     new_realized_fpr=fpr(0.01, "conformal", stat2) + f"; track m5 50/50 refit {hfs['conformal'].realized_fpr_mean:.4f}",
                     verdict_change="yes" if sig(po.ci_joint_lo, po.ci_joint_hi) != sig(pn.ci_joint_lo, pn.ci_joint_hi) else "no",
                     note="Convention applies: the alarm engine and holdout FPR call amd calibrate(method='randomized'), "
                          "which follows the flag; detector refit + threshold recomputed per honest resample (B=2000). "
                          f"joint-bootstrap p {po.p_joint:.3f} -> {pn.p_joint:.3f}."))
    df = pd.DataFrame(rows)[COLS]
    df.to_csv(OUT / "rows_rep.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 60)
    print(df[["claim", "old_estimate", "old_ci", "new_estimate", "new_ci", "verdict_change"]].to_string())


if __name__ == "__main__":
    main()
