"""Assemble results/fixes/corrections.csv: one row per (issue, claim) mapping the original claim to its corrected
value / status. Numbers are read from the corrected CSVs written by tracks/fixes/*.py (and the T2 / T3 partial
correction files results/fixes/<track>/corrections_*.csv), so the table never re-types a number by hand except the
'before' values quoted from the original reports.

    unset VIRTUAL_ENV; uv run python tracks/fixes/build_corrections.py
"""
from __future__ import annotations

import glob

import pandas as pd

from amd.common.schema import REPO

F = REPO / "results" / "fixes"
COLS = ["issue_id", "track", "original_claim", "corrected_claim", "numbers_before", "numbers_after", "verdict"]


def ci(r, nd=3):
    return f"{r.est:+.{nd}f} [{r.lo:+.{nd}f}, {r.hi:+.{nd}f}]"


def pick(df, **kw):
    m = pd.Series(True, index=df.index)
    for k, v in kw.items():
        m &= df[k] == v
    out = df[m]
    assert len(out) == 1, (kw, len(out))
    return out.iloc[0]


def rows_c2():
    R = []
    r1 = pd.read_csv(F / "t1" / "gains_r1_corrected.csv")
    for det, before, what in (("top3sum", "+0.15 [0.12, 0.17]", "top-3 sum"), ("cusum_k0.5", "+0.12", "CUSUM k=0.5")):
        r = pick(r1, set_file="ps__diff_current_only__gradual", alpha=0.05, detector=det)
        R.append(("C2", "t1 r1 (persistent state, GPT-4o)",
                  f"history-free current_only, gradual attacks: {what} - max at FPR 0.05 = {before}",
                  f"still positive with a correct paired bootstrap (calibration noise, one joint resample per replicate); "
                  f"5-app cluster sensitivity [{r.sens_lo:+.3f}, {r.sens_hi:+.3f}]",
                  f"{before} (old CI [{r.old_lo:.3f}, {r.old_hi:.3f}])", f"{ci(r)}, p(<=0)={r.p_le0:.3f}",
                  "holds" if (r.lo > 0 and r.sens_lo > 0) else "weakened"))
    r = pick(r1, set_file="ps__diff_full_diffs__gradual", alpha=0.05, detector="top3sum")
    R.append(("C2", "t1 r1 (persistent state, GPT-4o)", "history-aware full_diffs: top-3 sum loses to max (-0.07)",
              "still negative", f"{r.old_est:+.3f} [{r.old_lo:.3f}, {r.old_hi:.3f}]", ci(r), "holds" if r.hi < 0 else "weakened"))
    r1["old_sig"] = (r1.old_lo > 0) | (r1.old_hi < 0)
    w = ((r1.hi - r1.lo) / (r1.old_hi - r1.old_lo)).median()
    R.append(("C2", "t1 r1 (40 stream sets)", "per-set gain-over-max CIs (results/t1/round1/gain_*.csv)",
              f"CIs were too narrow (median width ratio corrected/old = {w:.1f}); max-vs-accumulator rankings "
              "(point estimates, e.g. 'max-type >= best accumulator in 86% / 67% / 83%') are unchanged",
              f"{int(r1.old_sig.sum())}/{len(r1)} (set, alpha, detector) gains significant",
              f"{int(r1.sig.sum())}/{len(r1)} significant", "weakened"))
    g = pd.read_csv(F / "t1" / "gains_r2mb_corrected.csv")
    d = pd.read_csv(F / "t1" / "did_r2mb_corrected.csv")
    r = pick(g, tag="main", mode="full", alpha=0.01, group="all", detector="top3sum")
    R.append(("C2", "t1 r2 (MonitoringBench, gpt-4.1-mini)", "full mode, FPR 0.01: top-3 sum - max = +0.024 [0.018, 0.031]",
              "not significant", f"+0.024 [{r.old_lo:.3f}, {r.old_hi:.3f}]", ci(r), "dropped"))
    for grp, before in (("all", "+0.023 [0.015, 0.032]"), ("S4", "+0.029")):
        r = pick(d, tag="main", alpha=0.01, group=grp, detector="cusum_k0.5")
        R.append(("C2", "t1 r2 (MonitoringBench, gpt-4.1-mini)",
                  f"DiD (none - full) of the CUSUM gain at FPR 0.01 ({grp}) = {before}", "not significant",
                  before, f"{ci(r)}, p(<=0)={r.p_le0:.2f}", "dropped"))
    for det in ("kth2", "top3sum", "cusum_k0.5"):
        r = pick(d, tag="main", alpha=0.05, group="all", detector=det)
        R.append(("C2", "t1 r2 (MonitoringBench, gpt-4.1-mini)",
                  f"DiD (none - full) at FPR 0.05, {det}: negative (accumulators gain more in full mode)",
                  "still significantly negative with original prompts, but see M4 (prompt confound)",
                  f"{r.old_est:+.3f} [{r.old_lo:.3f}, {r.old_hi:.3f}]", ci(r), "holds" if r.hi < 0 else "weakened"))
    r = pick(g, tag="nano", mode="none", alpha=0.01, group="all", detector="top3sum")
    R.append(("C2", "t1 r2 (gpt-4.1-nano none)", "top-3 sum 0.082 vs max 0.056 at FPR 0.01 (mild accumulation helps)",
              "positive, barely significant", f"+0.026 [{r.old_lo:.3f}, {r.old_hi:.3f}]", f"{ci(r)}, p(<=0)={r.p_le0:.3f}",
              "holds" if r.lo > 0 else "weakened"))
    ps = pd.read_csv(F / "r2_t1" / "ps_gains_corrected.csv")
    for mon, before in (("gpt-4.1-mini", "+0.145 [0.13, 0.16]"), ("gpt-4o-orig", "+0.101 [0.09, 0.12]"),
                        ("gemini-2.5-flash", "+0.021 [0.01, 0.04]"), ("qwen3-235b-a22b-2507", "-0.025 [-0.04, -0.01]")):
        r = pick(ps, set=f"ps2:{mon}:current_only:gradual", alpha=0.05, detector="top3sum")
        sig = r.lo > 0 or r.hi < 0
        verdict = "holds" if sig else ("weakened" if mon == "gpt-4.1-mini" else "dropped")
        R.append(("C2", "r2_t1 (persistent state)", f"history-free {mon}, gradual: top-3 sum - max at FPR 0.05 = {before}",
                  ("significant" if sig else f"not significant at 95% (p(<=0) = {r.p_le0:.3f})") +
                  f"; 5-app cluster sensitivity [{r.sens_lo:+.3f}, {r.sens_hi:+.3f}]",
                  before, f"{ci(r)}, p(<=0)={r.p_le0:.3f}", verdict))
    for mon, det, before in (("gpt-4.1-mini", "sr_d1", "+0.063 [0.04, 0.08]"), ("gemini-2.5-flash", "top3sum", "+0.043")):
        r = pick(ps, set=f"ps2:{mon}:current_only:gradual", alpha=0.01, detector=det)
        R.append(("C2", "r2_t1 (persistent state)", f"FPR 0.01: {mon} {det} - max = {before}",
                  "not significant" if not (r.lo > 0) else "significant", before, ci(r), "dropped" if r.lo <= 0 else "holds"))
    r = pick(ps, set="ps2:gpt-4.1-mini:current_only:positional", alpha=0.05, detector="top3sum")
    R.append(("C2", "r2_t1 (persistent state)", "positional attacks: max is best for all new monitors (gpt-4.1-mini top-3 sum -0.163)",
              "still significantly negative", "-0.163", ci(r), "holds" if r.hi < 0 else "weakened"))
    dd = pd.read_csv(F / "r2_t1" / "ps_did_corrected.csv")
    for mon, before in (("gpt-4o-orig", "+0.173 [0.10, 0.25]"), ("qwen3-235b-a22b-2507", "+0.127 [0.04, 0.21]"),
                        ("gemini-2.5-flash", "-0.03 (ns)"), ("gpt-4.1-mini", "-0.169 [-0.27, -0.06]")):
        r = pick(dd, monitor=mon, policy="gradual", alpha=0.05, detector="top3sum")
        sig = r.lo > 0 or r.hi < 0
        R.append(("C2", "r2_t1 (persistent state)", f"DiD current_only - full_diffs, top-3 sum gain, {mon} = {before}",
                  ("significant" if sig else "not significant") + f"; 5-app cluster sensitivity [{r.sens_lo:+.3f}, {r.sens_hi:+.3f}]",
                  before, f"{ci(r)}, p(<=0)={r.p_le0:.3f}",
                  "holds" if (sig or "ns" in before) else "dropped"))
    R.append(("C2", "r2_t1 (persistent state)", "'history-aware kills the gain' holds for two of four monitors (GPT-4o, Qwen)",
              "significant only for GPT-4o; Qwen's DiD is not significant; gpt-4.1-mini's is significantly the other way",
              "2 of 4", "1 of 4 (GPT-4o)", "weakened"))
    mo = pd.read_csv(F / "r2_t1" / "mole_gains_corrected.csv")
    for s, a, det, before in (("mole:single_day:llm", 0.10, "kth3", "+0.131 [0.11, 0.15]"),
                              ("mole:single_day:llm", 0.10, "top4sum", "+0.086"),
                              ("mole:single_day:llm", 0.05, "kth3", "+0.088"),
                              ("mole:single_day:peer_fit", 0.10, "kth3", "+0.172"),
                              ("mole:multiday:llm", 0.10, "kth3", "max best (0.31 vs 3rd-max 0.13)"),
                              ("mole:dsv4_single_day:llm", 0.10, "kth3", "-0.039 (replication fails)")):
        r = pick(mo, set=s, alpha=a, detector=det)
        sig = r.lo > 0 or r.hi < 0
        if "dsv4" in s:
            v, txt = "holds", "not significant (replication still fails; but gpt53's own gain is no longer significant either)"
        elif "multiday" in s:
            v, txt = ("holds" if sig else "weakened"), ("significant" if sig else "negative but not significant")
        else:
            v, txt = ("holds" if sig else "weakened"), ("significant" if sig else f"not significant (p(<=0)={r.p_le0:.3f})")
        R.append(("C2", "r2_t1 (MOLE, n=30 insiders)", f"{s} {det} - max at account FPR {a} = {before}", txt, before,
                  f"{ci(r)}", v))
    hy = pd.read_csv(F / "r2_t1" / "hybrid_summary_corrected.csv")
    r = hy[(hy.alpha == 0.01) & (hy.detector == "lenbin(top3sum)")].iloc[0]
    R.append(("C2", "r2_t1 (length-aware hybrid)", "length-tercile calibration loses 0.11-0.15 TPR at FPR 0.01 (negative)",
              "negative result holds at the set-family level; per-set significance counts were inflated",
              f"per-set significant losses lenbin(top3sum) {r.sig_neg_old}/46", f"mean {r.mean_gain:+.3f}, family CI "
              f"[{r.family_lo:+.3f}, {r.family_hi:+.3f}]; per-set significant losses {r.sig_neg_new}/46", "holds"))
    return R


def rows_m4():
    C = pd.read_csv(F / "t1" / "m4_contrasts.csv")
    MD = pd.read_csv(F / "t1" / "m4_mechanism_repeat_share.csv")
    R = []
    did = lambda p, a, d, g="all": pick(C, kind="did_none_minus_full", prompt=p, alpha=a, group=g, detector=d)  # noqa: E731
    ie = lambda a, d: pick(C, kind="instruction_effect_on_did(orig-matched)", alpha=a, group="all", detector=d)  # noqa: E731
    m = [did("matched", a, d) for a in (0.05, 0.01) for d in ("top3sum", "kth2", "cusum_k0.5")]
    R.append(("M4", "t1 r2 (MonitoringBench, gpt-4.1-mini)",
              "pre-registered test 'sequential gains concentrate in the history-free mode': not supported",
              "still not supported with matched prompts (only the history block differs; 200 h / 175 a subset): no DiD "
              "(none - full) of the gain over max is significantly positive",
              "orig prompts (full subset): DiD top-3 sum -0.116 [-0.184, -0.041] at 0.05, +0.009 n.s. at 0.01",
              "matched: " + "; ".join(f"{d} @{a}: {ci(did('matched', a, d))}" for a in (0.05, 0.01)
                                      for d in ("top3sum", "kth2", "cusum_k0.5")),
              "holds" if all(x.lo <= 0 for x in m) else "reversed"))
    for d in ("kth2", "top3sum", "cusum_k0.5"):
        o, mm, e = did("orig", 0.05, d), did("matched", 0.05, d), ie(0.05, d)
        R.append(("M4", "t1 r2 (MonitoringBench, gpt-4.1-mini)",
                  f"at FPR 0.05 {d} gains MORE in full (history-aware) mode than in none mode (negative DiD)",
                  "an instruction artifact: with matched prompts the DiD is near zero; the difference between prompt "
                  f"families (instruction effect on the DiD, orig - matched) = {ci(e)}",
                  f"orig prompts, same subset: {ci(o)}", f"matched prompts: {ci(mm)}",
                  "dropped" if (mm.lo <= 0 <= mm.hi) else ("holds" if mm.hi < 0 else "reversed")))
    for g in ("S1", "all"):
        o = pick(MD, prompt="orig", group=g); mm = pick(MD, prompt="matched", group=g)
        R.append(("M4", "t1 r2 (MonitoringBench, gpt-4.1-mini)",
                  "mechanism: history makes gpt-4.1-mini re-flag attacks (S1: >=2 high steps 60% full vs 39% none)",
                  f"share of {g} attacks with >= 2 steps above the honest q95, full - none: small and not significant "
                  "under either prompt family on the subset (S1 n=25)",
                  f"orig prompts: {o.attack_ge2_full:.2f} vs {o.attack_ge2_none:.2f} ({o.diff_full_minus_none:+.2f} "
                  f"[{o.lo:+.2f}, {o.hi:+.2f}])",
                  f"matched prompts: {mm.attack_ge2_full:.2f} vs {mm.attack_ge2_none:.2f} ({mm.diff_full_minus_none:+.2f} "
                  f"[{mm.lo:+.2f}, {mm.hi:+.2f}])", "holds" if mm.lo > 0 else "weakened"))
    o = pick(C, kind="tpr_max_none_minus_full", prompt="orig", alpha=0.05, group="all")
    mm = pick(C, kind="tpr_max_none_minus_full", prompt="matched", alpha=0.05, group="all")
    R.append(("M4", "t1 r2 (MonitoringBench, gpt-4.1-mini)",
              "max TPR is higher for the history-free (none) monitor than the history-aware one at FPR 0.05 "
              "(r2_main: 0.322 none vs 0.226 full, all 775 attacks)",
              "the sign flips with matched prompts: the original none-mode instruction ('score low unless this action "
              "alone shows concrete signs') helps the history-free monitor; history itself does not hurt max",
              f"orig prompts, subset: none - full {ci(o)}", f"matched prompts: none - full {ci(mm)}", "reversed"
              if (o.est > 0 and mm.est < 0) else "weakened"))
    R.append(("M4", "r2_t1 (persistent state)", "current_only vs full_diffs comparisons (DiD of the accumulation gain)",
              "no prompt confound: both modes use the identical system prompt (incl. the conditional 'If previous context "
              "is provided, consider how the current changes relate to previously introduced code'); the user message "
              "differs only by the previous-diffs block (tracks/r2_t1/ps_score.py). Not re-scored; CIs corrected under C2",
              "history + instruction (suspected)", "history only (verified by reading the prompt builder)", "holds"))
    return R


def rows_chooser():
    R = []
    S = pd.read_csv(F / "r2_t1" / "chooser_fixed_summary_task_lab20.csv")
    Si = pd.read_csv(F / "r2_t1" / "chooser_fixed_summary_iid_lab20.csv")
    fmt = lambda r: f"{r.mean_gain_vs_max:+.3f} [{r.family_boot_lo:+.3f}, {r.family_boot_hi:+.3f}]"  # noqa: E731
    for ch, before in (("emp", "+0.023 [0.012, 0.038] (FPR 0.01; realized FPR 0.0156 vs 0.0142)"), ("meta", "+0.019"),
                       ("mech", "-0.022 [-0.044, -0.000]")):
        s0 = pick(S, design="same_cal", alpha=0.01, chooser=ch)
        s1 = pick(S, design="nested", alpha=0.01, chooser=ch)
        s2 = pick(S, design="fpr_matched", alpha=0.01, chooser=ch)
        i1 = pick(Si, design="nested", alpha=0.01, chooser=ch)
        issue = "M7" if ch == "mech" else "M6"
        verdict = ("dropped" if not (s1.family_boot_lo > 0 or s2.family_boot_lo > 0) else "weakened") if ch != "mech" else \
            ("holds" if s1.family_boot_hi < 0 else "weakened")
        R.append((issue, "r2_t1 (rule chooser, 67 sets)", f"{ch} chooser gain over always-max at FPR 0.01 = {before}",
                  "nested calibration (select on one calibration half, threshold on the other) and FPR-matched "
                  "evaluation; task-grouped labeled attacks; 95% CI = cluster bootstrap over 14 set families",
                  f"same-cal (re-run): {fmt(s0)}, realized FPR {s0.mean_fpr:.4f} vs always-max {s0.mean_fpr_max:.4f}",
                  f"nested: {fmt(s1)} (iid labeled draw {fmt(i1)}); FPR-matched: {fmt(s2)}", verdict))
    s1 = pick(S, design="nested", alpha=0.05, chooser="emp"); s2 = pick(S, design="fpr_matched", alpha=0.05, chooser="emp")
    R.append(("M6", "r2_t1 (rule chooser, 67 sets)", "emp chooser at FPR 0.05 = +0.014 [0.005, 0.028]", "not significant",
              "+0.014 [0.005, 0.028]", f"nested {fmt(s1)}; FPR-matched {fmt(s2)}", "dropped"))
    S40 = pd.read_csv(F / "r2_t1" / "chooser_fixed_summary_task_lab40.csv")
    a, b, c = (pick(S40, design=d, alpha=0.01, chooser="emp") for d in ("same_cal", "nested", "fpr_matched"))
    R.append(("M6", "r2_t1 (rule chooser, 67 sets)", "emp chooser with 40 labeled attacks = +0.028 [0.015, 0.044], 32 wins / 0 losses",
              "the extra labels do not rescue it once selection and threshold noise are separated", f"same-cal (re-run): {fmt(a)}",
              f"nested: {fmt(b)}; FPR-matched: {fmt(c)}", "dropped"))
    i0 = pick(Si, design="same_cal", alpha=0.01, chooser="emp"); t0 = pick(S, design="same_cal", alpha=0.01, chooser="emp")
    R.append(("m10", "r2_t1 (rule chooser)", "labeled attacks drawn iid (not by task) from the evaluation pool",
              "grouping the labeled draw by task changes little; the winner's curse (M6) dominates",
              f"iid draw, same-cal: {fmt(i0)}", f"task-grouped, same-cal: {fmt(t0)}", "weakened"))
    M = pd.read_csv(F / "r2_t1" / "chooser_mechanism_task_lab20.csv")
    for det, pred, before in (("top3sum", "rep_lr", "+0.29 (p=0.018) across 67 sets; T1: +0.55 (44 sets), nano +0.47"),
                              ("cusum_k0.5", "h2c", "-0.55 across 67 sets; T1: -0.65, nano -0.67")):
        r = pick(M, design="same_cal", alpha=0.05, gain_of=det, predictor=pred)
        R.append(("M7", "t1 / r2_t1 (mechanism)", f"held-out {det} gain tracks {pred} (Spearman {before})",
                  f"predictor estimated on disjoint labeled attacks; family-level inference over {r.n_families} families",
                  before, f"sets {r.spearman_sets:+.2f} (naive p {r.p_sets_naive:.3f}), family-cluster CI "
                          f"[{r.family_boot_lo:+.2f}, {r.family_boot_hi:+.2f}], family means {r.spearman_family_means:+.2f} "
                          f"(p {r.p_family_means:.2f})",
                  "holds" if (r.family_boot_lo > 0 or r.family_boot_hi < 0) else "weakened"))
    R.append(("M7", "t1 REPORT / PDF 00-01", "practitioner lesson 3: estimate stream properties from honest data + a small "
              "attack sample, then pick the rule", "not supported out of sample: neither the mechanism rule nor the empirical "
              "chooser beats always-max once calibration noise is separated from selection; keep max (or max with a "
              "length-aware null) as the default and treat stream properties as descriptive", "lesson stated as actionable",
              "see M6/M7 rows above", "dropped"))
    return R


def rows_misc():
    R = []
    T = pd.read_csv(F / "t1" / "m9_tpr_by_agent_model.csv")
    for mode in ("full", "none"):
        a = pick(T, monitor="gpt-4.1-mini", mode=mode, alpha=0.01, attack_subset="all", detector="max")
        b = pick(T, monitor="gpt-4.1-mini", mode=mode, alpha=0.01, attack_subset="opus-4-5", detector="max")
        c = pick(T, monitor="gpt-4.1-mini", mode=mode, alpha=0.01, attack_subset="opus-4-6", detector="max")
        t3 = pick(T, monitor="gpt-4.1-mini", mode=mode, alpha=0.01, attack_subset="opus-4-5", detector="top3sum")
        R.append(("M9", "t1 r2 (MonitoringBench)", f"absolute TPR 'about 17-20% at 1% FPR' (gpt-4.1-mini {mode}, max)",
                  "attack agent model is label-correlated (honest 100% opus-4-5; 36% of attacks opus-4-6); like-for-like "
                  f"opus-4-5 TPR is lower; top-3 sum on opus-4-5: {t3.tpr:.3f} [{t3.lo:.3f}, {t3.hi:.3f}]",
                  f"pooled {a.tpr:.3f} [{a.lo:.3f}, {a.hi:.3f}]",
                  f"opus-4-5 {b.tpr:.3f} [{b.lo:.3f}, {b.hi:.3f}] vs opus-4-6 {c.tpr:.3f} [{c.lo:.3f}, {c.hi:.3f}]", "weakened"))
    F1 = pd.read_csv(F / "t1" / "m1_realized_fpr.csv")
    x = F1[(F1.source == "t1 round2 main") & (F1.alpha == 0.01)]
    R.append(("m1", "t1 r2, r2_t1", "'randomized thresholds: every detector realizes about alpha'",
              "at alpha=0.01 the plug-in threshold on ~275 calibration runs over-alarms on held-out honest runs; realized "
              "FPR now tabulated next to every TPR (results/fixes/t1/m1_realized_fpr.csv)", "about alpha",
              f"t1 r2 main at 0.01: realized/target {x.fpr_over_alpha.min():.2f}-{x.fpr_over_alpha.max():.2f} "
              f"(mean {x.fpr_over_alpha.mean():.2f})", "weakened"))
    r1 = pd.read_csv(F / "t1" / "gains_r1_corrected.csv")
    for s in ("mrt__claude-3-5-sonnet-20241022|mrt_sequential_5", "mrt__claude-3-5-sonnet-20241022|mrt_sequential_5+likert_reminder_v2_superaware"):
        r = pick(r1, set_file=s, alpha=0.05, detector="max_lenaware")
        R.append(("m7", "t1 r1 (MRT)", f"length-aware max beats max ({s.split('|')[1]}, FPR 0.05)",
                  "gain survives the corrected CI; an attacker who pads benign steps controls length, so the gain is "
                  "conditional on unadapted attack lengths", f"{r.old_est:+.3f} [{r.old_lo:.3f}, {r.old_hi:.3f}]", ci(r),
                  "holds" if r.lo > 0 else "weakened"))
    P = pd.read_csv(F / "r2_t1" / "m9_ps_success_conditioned.csv")
    for mon in ("gpt-4.1-mini", "gpt-4o-orig"):
        s = pick(P, set=f"ps2:{mon}:current_only:gradual", alpha=0.05, subset="side-task success", detector="top3sum - max")
        f_ = pick(P, set=f"ps2:{mon}:current_only:gradual", alpha=0.05, subset="side-task failed", detector="top3sum - max")
        R.append(("m9", "r2_t1 (persistent state)", f"{mon} gradual top-3 sum gain counts 66/120 side-task-failed attacks as positives",
                  "success-conditioned gain reported", "all 120 attacks pooled",
                  f"successful (n={s.n_attack}): {ci(s.rename({'tpr': 'est'}))}; failed (n={f_.n_attack}): "
                  f"{ci(f_.rename({'tpr': 'est'}))}", "holds" if s.lo > 0 else "weakened"))
    R.append(("m8", "t1 / t3 data", "label-correlated surface features (truncation, str_replace, reasoning visibility)",
              "noted; LLM monitors never see reasoning (include_reasoning=False); the T1 M9 opus-4-5 stratification and the "
              "M4 matched prompts do not remove these features; no re-analysis", "unreported", "documented here", "holds"))
    R.append(("m12", "t1 r1 (aksh-n)", "'max alarms at the ideal flag step (median delay 0)'",
              "keep the caveat next to the claim: the onset is the adjudicator's ideal_flagging_step, itself an LLM "
              "judgment, so delay 0 for a spike rule is partly by construction", "median delay 0", "unchanged (caveat)",
              "weakened"))
    R.append(("M8", "PDF reports (docs/reports)", "PDF 00-03 headline statements (one clean gain +0.15; T3 condensation; "
              "LOCO tail resists poisoning; sqrt(ARL) slopes to ARL 1e4)",
              "PDFs NOT regenerated in this pass; this table is the errata: C2/M4/M6/M7 rows (T1), m2/m3/C1/M5 rows "
              "(T2), M1/M2/M3 rows (T3); round-1 sqrt(ARL) slopes are only calibratable to ARL ~ n_honest+1 = 551",
              "as printed", "see the rows of this table", "weakened"))
    R.append(("m13", "repo hygiene", "no real secrets; README budget text; .key_index; synthetic sk-proj placeholder",
              "not changed here (README, .gitignore and tracks/r2_t1/ps_score.py are outside the fixes scope); no secret "
              "was found and none is printed", "open", "open (recommendation stands)", "holds"))
    return R


def main():
    rows = [dict(zip(COLS, r)) for r in rows_c2() + rows_m4() + rows_chooser() + rows_misc()]
    D = pd.DataFrame(rows, columns=COLS)
    parts = [pd.read_csv(p) for p in sorted(glob.glob(str(F / "*" / "corrections_*.csv")))]
    for p in parts:
        assert list(p.columns) == COLS, p.columns
    D = pd.concat([D] + parts, ignore_index=True)
    bad = ~D.verdict.isin(["holds", "weakened", "reversed", "dropped"])
    assert not bad.any(), D[bad]
    order = {k: i for i, k in enumerate(["C1", "C2", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"] +
                                        [f"m{i}" for i in range(1, 14)])}
    D["_o"] = D.issue_id.map(lambda x: order.get(x, 99))
    D = D.sort_values("_o", kind="stable").drop(columns="_o")
    D.to_csv(F / "corrections.csv", index=False)
    print(D.groupby(["issue_id", "verdict"]).size().unstack(fill_value=0))


if __name__ == "__main__":
    main()
