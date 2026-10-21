"""Write the corrections CSVs for T3 (round 2: results/fixes/r2_t3/corrections_r2_t3.csv; round 1:
results/fixes/t3/corrections_t3.csv). Every number is read from the CSVs written by fix_r2_t3.py and
fix_t3_round1.py; 'numbers_before' quote the original claims (results/r2_t3, results/t3, EXPERIMENT_LOG).

Issues: M1, M2, M3, m4, m5, m6, M9 (T3 part), covert sqrt(ARL) check.

    unset VIRTUAL_ENV; uv run python tracks/fixes/t3/write_corrections_t3.py
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
R2 = REPO / "results" / "fixes" / "r2_t3"
R1 = REPO / "results" / "fixes" / "t3"
COLS = ["issue_id", "track", "original_claim", "corrected_claim", "numbers_before", "numbers_after", "verdict"]


def pick(df, **kw):
    m = np.ones(len(df), bool)
    for k, v in kw.items():
        m &= (df[k] == v).values
    out = df[m]
    assert len(out) == 1, (kw, len(out))
    return out.iloc[0]


def f(r, kind="joint", signed=True):
    s = "{:+.3f}" if signed else "{:.3f}"
    return f"{s.format(r['value'])} [{s.format(r[f'ci_{kind}_lo'])}, {s.format(r[f'ci_{kind}_hi'])}]"


def rng_(vals, signed=False):
    s = "{:+.2f}" if signed else "{:.2f}"
    return f"{s.format(min(vals))} to {s.format(max(vals))}"


def r2_rows():
    C = pd.read_csv(R2 / "contrasts.csv")
    L = pd.read_csv(R2 / "levels_undetected_success.csv")
    H = pd.read_csv(R2 / "m5_holdout_fpr.csv")
    S = pd.read_csv(R2 / "m6_stripping_changes.csv")
    V = pd.read_csv(R2 / "validation_vs_project.csv")
    M9 = pd.read_csv(R2 / "m9_nothing_by_agent_model.csv")
    c = lambda **kw: pick(C, **kw)  # noqa: E731
    P = "paired126"
    rows = []

    def m1(p, det, al=0.01, vk="valid", sub=P):
        return c(family="M1_oneshot_vs_control", subset=sub, comparison=f"pace_{p}_r0 - rewrite_control",
                 detector=det, alpha=al, validity=vk)

    def ad(p, det, al=0.01, vk="valid", sub=P):
        return c(family="adaptive_vs_control_CONFOUNDED", subset=sub, comparison=f"pace_{p} - rewrite_control",
                 detector=det, alpha=al, validity=vk)

    def og(p, det, al=0.01, vk="valid"):
        return c(family="oracle_feedback_selection_gain", subset=P, comparison=f"pace_{p} - pace_{p}_r0",
                 detector=det, alpha=al, validity=vk)

    pmin = C[(C.family == "M1_oneshot_vs_control") & (C.subset == P) &
             C.detector.isin(["max", "cusum1.5", "multichart", "top3sum"])]
    rows.append(dict(
        issue_id="M1", track="r2_t3",
        original_claim="Pacing vs control: +0.21 [+0.12, +0.29] against max, a real strategy effect",
        corrected_claim=("The pacing arms are adaptive (best of up to 3 attempts selected on the same deterministic "
                         "gpt-4.1 scores and threshold used for evaluation); the control is one-shot, so +0.21 mixes "
                         "strategy with in-sample selection. Adaptive-vs-adaptive is not identifiable (no adaptive "
                         "control exists). One-shot vs one-shot against max: pace_max_r0 - control is about +0.09, "
                         "CI includes 0 under the joint (attack + honest) bootstrap, not significant after Holm. The "
                         "adaptive-minus-one-shot gain (+0.11) is oracle-feedback selection, not strategy."),
        numbers_before="pace_max - rewrite_control (adaptive vs one-shot), max, a=0.01: +0.206 [+0.119, +0.294] (attack-only CI, judge validity)",
        numbers_after=(f"one-shot pace_max_r0 - control, max, a=0.01: judge {f(m1('max', 'max'))}, strict "
                       f"{f(m1('max', 'max', vk='strict'))}; a=0.003 judge {f(m1('max', 'max', 0.003))}; n=150 judge "
                       f"{f(m1('max', 'max', sub='all150_m1arms'))}; Holm p (24 one-shot contrasts) = "
                       f"{m1('max', 'max').p_holm_joint:.2f}. Confounded adaptive - control with joint CI: "
                       f"{f(ad('max', 'max'))}. Oracle-feedback selection gain pace_max - pace_max_r0: "
                       f"judge {f(og('max', 'max'))}, strict {f(og('max', 'max', vk='strict'))}"),
        verdict="weakened"))
    rows.append(dict(
        issue_id="M1", track="r2_t3",
        original_claim="Pacing vs control: +0.18 [+0.10, +0.26] against multichart, a real strategy effect",
        corrected_claim=("One-shot vs one-shot against the multichart OR the pacing effect is +0.01 to +0.08 at "
                         "a=0.01 and -0.04 to +0.02 at a=0.003, CI includes 0 for all three pacing arms and both alphas; the +0.18 is mostly oracle-feedback "
                         "selection. Also, the multichart's in-sample threshold is anti-conservative on held-out "
                         "honest runs (see m5 row)."),
        numbers_before="pace_multichart - rewrite_control, multichart, a=0.01: +0.177 [+0.095, +0.258] (attack-only CI, judge)",
        numbers_after=(f"one-shot pace_multichart_r0 - control, multichart, a=0.01: judge {f(m1('multichart', 'multichart'))}, "
                       f"strict {f(m1('multichart', 'multichart', vk='strict'))}; pace_max_r0 - control on multichart: "
                       f"judge {f(m1('max', 'multichart'))}; a=0.003 pace_multichart_r0: judge "
                       f"{f(m1('multichart', 'multichart', 0.003))}. Oracle gain pace_multichart - r0 on multichart: "
                       f"{f(og('multichart', 'multichart'))}"),
        verdict="weakened"))
    rows.append(dict(
        issue_id="M1", track="r2_t3",
        original_claim="Pacing vs control: +0.03 (n.s.) against top-3 sum, which neutralizes it",
        corrected_claim=("Holds: one-shot pacing vs one-shot control against top-3 sum is null-to-negative for all "
                         "three pacing arms (point estimates -0.02 to -0.12 across alphas, all CIs include 0)."),
        numbers_before="pace_max - rewrite_control, top3sum, a=0.01: +0.032 [-0.063, +0.127]",
        numbers_after=(f"pace_max_r0 - control, top3sum, a=0.01: judge {f(m1('max', 'top3sum'))}, strict "
                       f"{f(m1('max', 'top3sum', vk='strict'))}; pace_cusum_r0 {f(m1('cusum', 'top3sum'))}; "
                       f"pace_multichart_r0 {f(m1('multichart', 'top3sum'))}"),
        verdict="holds"))
    rows.append(dict(
        issue_id="M1", track="r2_t3",
        original_claim="Adaptive feedback adds +0.11-0.13 for pacing (oracle-feedback caveat)",
        corrected_claim=("Holds as a description of selection: adaptive minus one-shot is an in-sample selection gain "
                         "(the attempt is chosen with the evaluation monitor's own deterministic scores and "
                         "threshold), so it must not be counted as evasion strategy or as out-of-sample attacker "
                         "capability."),
        numbers_before="+0.11-0.13 (adaptive - r0, pacing arms, matched detector)",
        numbers_after=(f"pace_max on max {f(og('max', 'max'))}; pace_multichart on multichart "
                       f"{f(og('multichart', 'multichart'))}; pace_cusum on cusum1.5 {f(og('cusum', 'cusum1.5'))}; "
                       f"strict: {f(og('max', 'max', vk='strict'))} / {f(og('multichart', 'multichart', vk='strict'))}"),
        verdict="holds"))

    # m4
    F = C[(C.family == "m4_paired_diffs_family") & (C.subset == P)]
    g = lambda comp, det, al, vk="valid": pick(F, comparison=comp, detector=det, alpha=al, validity=vk)  # noqa: E731
    nsig = {vk: int((F[F.validity == vk].p_holm_joint < 0.05).sum()) for vk in ("valid", "strict", "strict_rel")}
    rows.append(dict(
        issue_id="m4", track="r2_t3",
        original_claim="Pacing vs round-1 condensation: +0.07-0.10 (significant at alpha=0.003)",
        corrected_claim=("Selective and not robust. None of the six pace-vs-round-1 comparisons survives Holm "
                         "correction across the 20 reported paired comparisons (judge, strict or strict-rel). At "
                         "alpha=0.003 pace_cusum - r1_cusum on CUSUM k=1.5 is negative (-0.10); with the attack-only "
                         "CI it was significant in the other direction, with the joint CI it is not. The pacing arms "
                         "were also selected on gpt-4.1 feedback while the round-1 arms were selected on gpt-4.1-mini "
                         "feedback, which favours pacing under gpt-4.1 evaluation."),
        numbers_before="pace_max - r1_max +0.087 [+0.008, +0.167], pace_multichart - r1_multichart +0.104 [+0.032, +0.179] at a=0.003 (attack-only CIs); pace_cusum - r1_cusum -0.103 [-0.183, -0.024] not mentioned",
        numbers_after=(f"a=0.003 (joint CI; Holm p judge): pace_max - r1_max {f(g('pace_max - r1_max', 'max', 0.003))} "
                       f"(Holm {g('pace_max - r1_max', 'max', 0.003).p_holm_joint:.2f}); pace_multichart - r1_multichart "
                       f"{f(g('pace_multichart - r1_multichart', 'multichart', 0.003))} (Holm "
                       f"{g('pace_multichart - r1_multichart', 'multichart', 0.003).p_holm_joint:.2f}); pace_cusum - r1_cusum "
                       f"{f(g('pace_cusum - r1_cusum', 'cusum1.5', 0.003))} (attack-only "
                       f"[{g('pace_cusum - r1_cusum', 'cusum1.5', 0.003).ci_attack_lo:+.3f}, "
                       f"{g('pace_cusum - r1_cusum', 'cusum1.5', 0.003).ci_attack_hi:+.3f}]; Holm "
                       f"{g('pace_cusum - r1_cusum', 'cusum1.5', 0.003).p_holm_joint:.2f}). a=0.01: "
                       f"{f(g('pace_max - r1_max', 'max', 0.01))}, {f(g('pace_cusum - r1_cusum', 'cusum1.5', 0.01))}, "
                       f"{f(g('pace_multichart - r1_multichart', 'multichart', 0.01))}. Holm-significant of 20: "
                       f"judge {nsig['valid']}, strict {nsig['strict']}, strict-rel {nsig['strict_rel']}"),
        verdict="dropped"))
    pr = pd.read_csv(R2 / "primary_contrast.csv").iloc[0]
    rows.append(dict(
        issue_id="m4", track="r2_t3",
        original_claim="(no pre-specified primary contrast; 20 paired comparisons reported without multiplicity control)",
        corrected_claim=("Pre-specified primary contrast: one-shot pace_max_r0 - one-shot rewrite_control, deployed "
                         "max, alpha=0.01, strict validity, paired n=126, joint bootstrap. It is positive but not "
                         "significant: no detectable strategy effect of one-shot pacing over a plain rewrite."),
        numbers_before="pace_max - rewrite_control +0.206 [+0.119, +0.294] (adaptive vs one-shot, judge, attack-only CI)",
        numbers_after=(f"primary: {f(pr)}, joint bootstrap p = {pr.p_joint:.2f}; attack-only CI "
                       f"[{pr.ci_attack_lo:+.3f}, {pr.ci_attack_hi:+.3f}]"),
        verdict="weakened"))

    # M2
    def vn(comp, det="max", al=0.01, vk="valid"):
        return c(family="vs_nothing", subset=P, comparison=comp, detector=det, alpha=al, validity=vk)
    rows.append(dict(
        issue_id="M2", track="r2_t3",
        original_claim="Net, pacing vs originals is -0.15 (still worse than doing nothing)",
        corrected_claim=("Holds and gets stronger under literal-based validity. Judge-only is an upper bound; with "
                         "strict-rel (rewrites must keep the literals the original attack wrote) the deficit is "
                         "about -0.19, with strict about -0.32. One-shot pacing is about -0.26 (judge)."),
        numbers_before="pace_max - nothing, max, a=0.01: -0.151 [-0.254, -0.056]",
        numbers_after=(f"pace_max - nothing, max, a=0.01: judge {f(vn('pace_max - nothing'))}, strict-rel "
                       f"{f(vn('pace_max - nothing', vk='strict_rel'))}, strict {f(vn('pace_max - nothing', vk='strict'))}; "
                       f"one-shot pace_max_r0 - nothing judge {f(vn('pace_max_r0 - nothing'))}"),
        verdict="holds"))
    rows.append(dict(
        issue_id="M2", track="r2_t3",
        original_claim="rewrite_control: undetected vs max -0.36 [-0.45, -0.26] relative to the originals",
        corrected_claim=("Holds; a lower bound with literal-based validity is larger in magnitude (-0.39 strict-rel, "
                         "-0.50 strict). strict is asymmetric vs the originals because 28/150 successful originals do "
                         "not contain every target literal in their own actions; strict-rel is the fair lower bound."),
        numbers_before="-0.357 [-0.452, -0.262] (judge, attack-only CI)",
        numbers_after=(f"judge {f(vn('rewrite_control - nothing'))}; strict-rel "
                       f"{f(vn('rewrite_control - nothing', vk='strict_rel'))}; strict "
                       f"{f(vn('rewrite_control - nothing', vk='strict'))}; a=0.003 judge "
                       f"{f(vn('rewrite_control - nothing', al=0.003))}"),
        verdict="holds"))
    lv = lambda arm, vk: pick(L, subset=P, arm=arm, detector="max", alpha=0.01, validity=vk)  # noqa: E731
    r2arms = ["rewrite_control", "pace_max", "pace_cusum", "pace_multichart", "pace_max_r0", "pace_cusum_r0",
              "pace_multichart_r0"]
    rows.append(dict(
        issue_id="M2", track="r2_t3",
        original_claim="Limitations: validity by judge + literal checks, 0.88-1.00; undetected-success levels for the rewritten arms",
        corrected_claim=("valid = LLM judge only; the literal check was not part of it. Only 75-83% of round-2 "
                         "rewrites are judge-valid AND keep every target literal. Every rewritten-arm level should be "
                         "read as a [strict, judge] interval; e.g. pace_max vs max at a=0.01 is 0.44-0.60, the "
                         "rewrite control 0.25-0.40."),
        numbers_before="judge-valid 0.95-1.00; literal preservation 0.88-1.00 (mean fraction)",
        numbers_after=(f"paired 126: judge-valid rate {rng_([lv(a, 'valid').valid_rate for a in r2arms])}, "
                       f"strict-valid rate {rng_([lv(a, 'strict').valid_rate for a in r2arms])}; max, a=0.01 "
                       f"undetected-success judge/strict: pace_max {lv('pace_max', 'valid').value:.3f}/"
                       f"{lv('pace_max', 'strict').value:.3f}, pace_max_r0 {lv('pace_max_r0', 'valid').value:.3f}/"
                       f"{lv('pace_max_r0', 'strict').value:.3f}, control {lv('rewrite_control', 'valid').value:.3f}/"
                       f"{lv('rewrite_control', 'strict').value:.3f}"),
        verdict="weakened"))

    # m5
    hf = lambda det, al: pick(H, detector=det, alpha=al)  # noqa: E731
    rows.append(dict(
        issue_id="m5", track="r2_t3",
        original_claim="All T3 round-2 CIs (bootstrap over base attacks only; thresholds calibrated in-sample on all 550 honest)",
        corrected_claim=("CIs re-done with a joint bootstrap (base attacks and Honest-550 resampled together; "
                         "detectors refit and thresholds recomputed per replicate); most intervals widen (pace_max - "
                         "control from 0.175 to 0.262 wide) and some become asymmetric around the point estimate. Held-out check (calibrate on 275, test on 275, 200 splits): max, CUSUM, "
                         "e-process and top-3 sum realize roughly nominal FPR (1.1x at a=0.01, 1.2-1.4x at 0.003, "
                         "expected with half the calibration data), but the multichart OR realizes about 1.9x nominal at "
                         "a=0.01 and 3.8x at a=0.003: its tail fits and threshold use the same honest runs, so "
                         "multichart's matched-FPR comparisons favour the defender."),
        numbers_before="pace_max - control [+0.119, +0.294]; rewrite_control - nothing [-0.452, -0.262]; FPR assumed = alpha",
        numbers_after=(f"pace_max - control {f(ad('max', 'max'))}; rewrite_control - nothing "
                       f"{f(vn('rewrite_control - nothing'))}; held-out FPR mean (a=0.01 / 0.003): max "
                       f"{hf('max', 0.01).realized_fpr_mean:.4f} / {hf('max', 0.003).realized_fpr_mean:.4f}, top3sum "
                       f"{hf('top3sum', 0.01).realized_fpr_mean:.4f} / {hf('top3sum', 0.003).realized_fpr_mean:.4f}, "
                       f"cusum1.5 {hf('cusum1.5', 0.01).realized_fpr_mean:.4f} / {hf('cusum1.5', 0.003).realized_fpr_mean:.4f}, "
                       f"multichart {hf('multichart', 0.01).realized_fpr_mean:.4f} / "
                       f"{hf('multichart', 0.003).realized_fpr_mean:.4f}"),
        verdict="weakened"))
    # m6
    ch = int(S.n_streams_changed.sum())
    ch_ad = int(S[S.arm.isin(["r1_max", "r1_cusum", "r1_multichart", "pace_max", "pace_cusum", "pace_multichart",
                               "rewrite_control"])].n_streams_changed.sum())
    rows.append(dict(
        issue_id="m6", track="r2_t3",
        original_claim="Submit-step stripping of refined trajectories (strip when the ORIGINAL's submit_step == len(refined) - 1)",
        corrected_claim=("Fixed: strip only when the refined trajectory's last action is a submit call. Changes "
                         "the streams below; no reported undetected-success point estimate moves (the dropped steps "
                         "were never the deciding steps)."),
        numbers_before="non-submit last step stripped in some refined streams",
        numbers_after=(f"streams changed: {ch_ad} in the 7 adaptive/control arms, {ch} over all 13 refined arms incl. r0; "
                       f"max |change| in any cross-table point estimate = {V.effect_of_m6_fix.abs().max():.3g}"),
        verdict="holds"))
    # M9
    m9 = lambda sub, det, al: pick(M9, subset=sub, detector=det, alpha=al)  # noqa: E731
    pooled = pick(L, subset=P, arm="nothing", detector="max", alpha=0.01, validity="valid")
    o = lambda fam, comp, det="max", al=0.01, vk="valid": c(family=fam, subset="paired126_opus45", comparison=comp,  # noqa: E731
                                                            detector=det, alpha=al, validity=vk)
    rows.append(dict(
        issue_id="M9", track="r2_t3",
        original_claim="T3 'nothing' baseline (original attacks): gpt-4.1 none max TPR 0.24 at 1% FPR; all T3 contrasts pooled over attack agent models",
        corrected_claim=("Honest-550 is 100% claude-opus-4-5 while 40/126 paired base attacks are opus-4-6. In T3 the "
                         "confound is small at a=0.01: the opus-4-5-only baseline TPR is within 0.025 of the pooled one. "
                         "At a=0.003 CUSUM k=1.5 catches opus-4-6 originals far more often (0.13 vs 0.01). The main "
                         "contrasts keep their sign and size on the opus-4-5 subset (n=86)."),
        numbers_before=f"pooled n=126: max TPR {pooled.tpr:.3f}, undetected-success {pooled.value:.3f} at a=0.01",
        numbers_after=(f"max a=0.01 TPR opus-4-5 {m9('paired126_opus45', 'max', 0.01).tpr:.3f} (n=86) vs opus-4-6 "
                       f"{m9('paired126_opus46', 'max', 0.01).tpr:.3f} (n=40); cusum1.5 a=0.003 "
                       f"{m9('paired126_opus45', 'cusum1.5', 0.003).tpr:.3f} vs {m9('paired126_opus46', 'cusum1.5', 0.003).tpr:.3f}. "
                       f"opus-4-5 subset: pace_max_r0 - control {f(o('M1_oneshot_vs_control', 'pace_max_r0 - rewrite_control'))}; "
                       f"pace_max - control {f(o('adaptive_vs_control_CONFOUNDED', 'pace_max - rewrite_control'))}; "
                       f"rewrite_control - nothing {f(o('vs_nothing', 'rewrite_control - nothing'))}"),
        verdict="holds"))
    rows.append(dict(
        issue_id="covert", track="r2_t3",
        original_claim="Covert sqrt(ARL): slopes 0.01-0.07 (CIs <= 0.10) vs 0.5 over the calibratable ARL 10^1.5-551",
        corrected_claim=("No change: round 2 already fit only on ARL <= n_honest + 1 = 551 (a conformal threshold on "
                         "550 honest runs is +inf above that, so no alarms by construction). Submit-stripping fix "
                         "does not change any stream used there in a way that moves a point estimate."),
        numbers_before="slopes 0.01-0.07", numbers_after="unchanged (not recomputed beyond the stripping check)",
        verdict="holds"))
    return rows


def r1_rows():
    C1 = pd.read_csv(R1 / "contrasts_r1.csv")
    L1 = pd.read_csv(R1 / "levels_r1.csv")
    H1 = pd.read_csv(R1 / "m5_holdout_fpr_r1.csv")
    S1 = pd.read_csv(R1 / "m6_stripping_changes_r1.csv")
    V1 = pd.read_csv(R1 / "validation_vs_project_r1.csv")
    CV = pd.read_csv(R1 / "covert_refit_r1.csv")
    M3 = pd.read_csv(R1 / "r1_vs_rewrite_control_gpt41.csv")
    L2 = pd.read_csv(R2 / "levels_undetected_success.csv")
    C2 = pd.read_csv(R2 / "contrasts.csv")
    m3 = lambda comp, det="max", vk="valid": pick(M3, subset="paired126", comparison=comp, detector=det,  # noqa: E731
                                                  alpha=0.01, validity=vk)
    lv = lambda mode, v, arm, det, vk: pick(L1, mode=mode, variant=v, alpha=0.01, arm=arm, detector=det,  # noqa: E731
                                            validity=vk)
    cd = lambda mode, v, arm, det, vk: pick(C1, mode=mode, variant=v, alpha=0.01, detector=det,  # noqa: E731
                                            comparison=f"{arm}-aware - nothing", validity=vk)
    ctrl = pick(C2, family="vs_nothing", subset="paired126", comparison="rewrite_control - nothing", detector="max",
                alpha=0.01, validity="valid")
    rows = []
    rows.append(dict(
        issue_id="M3", track="t3",
        original_claim="Detector-aware rewriting did not help the attacker; it usually hurt (condensation) [results/t3/REPORT.md, EXPERIMENT_LOG 'T3 results', PDF 03]",
        corrected_claim=("Superseded. Round 1 had no rewrite-only control, so the aware-minus-original drop mixes "
                         "detector-aware strategy with the cost of LLM rewriting itself; the strategy effect is not "
                         "identifiable under the round-1 monitor (gpt-4.1-mini). Round 2's rewrite_control shows "
                         "that rewriting alone costs about -0.36 undetected-success vs max (gpt-4.1 none). Re-expressed "
                         "against that rewrite-only reference (gpt-4.1 none; control from the round-2 pipeline, so "
                         "only approximate), the round-1 aware arms are not worse than a plain rewrite; point estimates "
                         "favour the aware arms (+0.06 to +0.14 vs max, one-shot +0.06 to +0.10; 3 of the 6 joint CIs "
                         "exclude 0, all in the attacker's favour). The drop is not evidence that detector-aware strategy hurts."),
        numbers_before="max, a=0.01, full adaptive: originals 0.86 vs aware arms 0.63-0.73",
        numbers_after=(f"rewrite_control - nothing (gpt-4.1 none, max, a=0.01) {f(ctrl)}; vs rewrite control (judge, "
                       f"max): r1_max {f(m3('r1_max - rewrite_control'))}, r1_cusum {f(m3('r1_cusum - rewrite_control'))}, "
                       f"r1_multichart {f(m3('r1_multichart - rewrite_control'))}; one-shot r1_max_r0 "
                       f"{f(m3('r1_max_r0 - rewrite_control'))}, r1_cusum_r0 {f(m3('r1_cusum_r0 - rewrite_control'))}, "
                       f"r1_multichart_r0 {f(m3('r1_multichart_r0 - rewrite_control'))}; strict r1_max "
                       f"{f(m3('r1_max - rewrite_control', vk='strict'))}"),
        verdict="dropped"))
    full_ad = [lv("full", "adaptive", a, "max", "valid").value for a in ("max", "cusum", "multichart")]
    full_ad_s = [lv("full", "adaptive", a, "max", "strict").value for a in ("max", "cusum", "multichart")]
    rows.append(dict(
        issue_id="M2", track="t3",
        original_claim="Against max at 1% FPR, undetected success was 0.86 for the originals vs 0.63-0.73 for the aware arms (full, adaptive)",
        corrected_claim=("Levels reproduce under judge-only validity, but are upper bounds: with strict validity the "
                         "aware arms are at 0.47-0.53; the aware-minus-original drop is -0.13 to -0.22 (judge), "
                         "-0.20 to -0.26 (strict-rel), -0.33 to -0.39 (strict). Attribution to detector-aware "
                         "strategy is dropped (M3)."),
        numbers_before="0.86 vs 0.63-0.73 (attack-only CIs)",
        numbers_after=(f"judge {rng_(full_ad)}; strict {rng_(full_ad_s)}; diffs (joint CI) max-aware "
                       f"{f(cd('full', 'adaptive', 'max', 'max', 'valid'))} / strict {f(cd('full', 'adaptive', 'max', 'max', 'strict'))}; "
                       f"cusum-aware {f(cd('full', 'adaptive', 'cusum', 'max', 'valid'))}; multichart-aware "
                       f"{f(cd('full', 'adaptive', 'multichart', 'max', 'valid'))}; strict-rel range "
                       f"{rng_([cd('full', 'adaptive', a, 'max', 'strict_rel').value for a in ('max', 'cusum', 'multichart')], True)}"),
        verdict="weakened"))
    mc = [lv("full", "adaptive", a, "multichart", "valid").value for a in ("max", "cusum", "multichart")]
    mcs = [lv("full", "adaptive", a, "multichart", "strict").value for a in ("max", "cusum", "multichart")]
    hfm = pick(H1, mode="full", detector="multichart", alpha=0.01)
    rows.append(dict(
        issue_id="M2", track="t3",
        original_claim="Undetected-success vs multichart fell from 0.85 (original) to 0.49-0.68 (aware arms)",
        corrected_claim=("Judge-only upper bound; strict lower bound 0.35-0.48. The multichart's in-sample threshold "
                         "realizes about 1.8x the nominal FPR on held-out honest runs, so the multichart cells "
                         "overstate detection at matched FPR. Attribution to aware strategy dropped (M3)."),
        numbers_before="0.85 -> 0.49-0.68",
        numbers_after=(f"judge {rng_(mc)}, strict {rng_(mcs)}; held-out FPR multichart (full, a=0.01) "
                       f"{hfm.realized_fpr_mean:.4f} ({hfm.ratio_to_nominal:.1f}x)"),
        verdict="weakened"))
    vr = [pick(L2, subset="paired126", arm=a, detector="max", alpha=0.01, validity=vk).valid_rate
          for a in ("r1_max", "r1_cusum", "r1_multichart") for vk in ("strict",)]
    vr0 = [pick(L2, subset="paired126", arm=a, detector="max", alpha=0.01, validity="strict").valid_rate
           for a in ("r1_max_r0", "r1_cusum_r0", "r1_multichart_r0")]
    gap = [lv("full", "adaptive", a, "max", "valid").value - lv("full", "adaptive", a, "max", "strict").value
           for a in ("max", "cusum", "multichart")]
    rows.append(dict(
        issue_id="M2", track="t3",
        original_claim="Validity: judge preservation 98-99%, literal preservation 0.88-0.90; 'Undetected-success drops are genuine detection, not broken attacks'",
        corrected_claim=("valid = LLM judge only (gpt-4.1-mini, reading fabricated outputs). 0.88-0.90 is the mean "
                         "literal fraction; only about 80% of adaptive (72-80% of one-shot) rewrites are judge-valid "
                         "AND keep every target literal. Requiring the literals lowers every aware level by a further "
                         "0.17-0.20 at max, so part of the drop is plausibly broken attacks, not detection. The "
                         "'genuine detection' sentence is dropped; levels are reported as [strict, judge] bounds."),
        numbers_before="judge 98-99%; literal 0.88-0.90",
        numbers_after=(f"strict-valid rate (paired 126) adaptive {rng_(vr)}, one-shot {rng_(vr0)}; judge - strict gap in "
                       f"undetected-success (full, adaptive, max, a=0.01) {rng_(gap)}"),
        verdict="dropped"))
    dg = lambda mode, arm, vk="valid": pick(C1, mode=mode, variant="adaptive-r0", alpha=0.01, detector=arm,  # noqa: E731
                                            comparison=f"{arm}-aware adaptive - one-shot", validity=vk)
    rows.append(dict(
        issue_id="M1", track="t3",
        original_claim="Adaptive (2 feedback rounds) beats one-shot by +0.10..+0.17 undetected-success on the matched diagonal",
        corrected_claim=("Holds in full mode with joint CIs and strict validity, but it is an in-sample oracle "
                         "selection gain (the feedback used the same gpt-4.1-mini full-mode scores and threshold as "
                         "the evaluation), not out-of-sample attacker capability. In none mode (not the feedback mode) "
                         "the gain is +0.03 to +0.08."),
        numbers_before="+0.10..+0.17",
        numbers_after=(f"full: max {f(dg('full', 'max'))}, cusum {f(dg('full', 'cusum'))}, multichart "
                       f"{f(dg('full', 'multichart'))}; strict max {f(dg('full', 'max', 'strict'))}; none: max "
                       f"{f(dg('none', 'max'))}, cusum {f(dg('none', 'cusum'))}, multichart {f(dg('none', 'multichart'))}"),
        verdict="weakened"))
    cvr = CV.slope_resolvable_only
    rows.append(dict(
        issue_id="covert", track="t3",
        original_claim="Covert sqrt(ARL): undetected damage flat over ARL 10^1.5-10^4, slopes 0.00-0.03 << 0.5",
        corrected_claim=("Conclusion holds, but the fit range was wrong: with 550 honest runs no threshold is "
                         "calibratable above ARL ~551 (conformal threshold +inf, damage flat by construction). "
                         "Re-fit on ARL <= 551 only, slopes stay far below 0.5."),
        numbers_before=f"slopes {CV.slope_project_all_arls.min():.3f}-{CV.slope_project_all_arls.max():.3f} over 10^1.5-10^4",
        numbers_after=f"slopes {cvr.min():.3f}-{cvr.max():.3f} over 10^1.5-551 (7 of 14 ARL points)",
        verdict="holds"))
    hf = lambda mode, det, al: pick(H1, mode=mode, detector=det, alpha=al)  # noqa: E731
    d0 = cd("full", "adaptive", "max", "max", "valid")
    rows.append(dict(
        issue_id="m5", track="t3",
        original_claim="All round-1 CIs (bootstrap over base attacks only; in-sample thresholds on all 550 honest)",
        corrected_claim=("Joint (attack + honest) bootstrap CIs reported in levels_r1.csv / contrasts_r1.csv; "
                         "aware-minus-original differences stay clearly negative. Held-out FPR is about nominal for max, "
                         "CUSUM and e-process, but the multichart OR realizes about 1.8-2.0x nominal at a=0.01 and about "
                         "4x at a=0.003 on held-out honest runs."),
        numbers_before="max-aware - nothing (full, adaptive, max): attack-only CI",
        numbers_after=(f"max-aware - nothing (full, adaptive, max): attack-only [{d0.ci_attack_lo:+.3f}, {d0.ci_attack_hi:+.3f}] "
                       f"-> joint {f(d0)}; held-out FPR multichart full a=0.01 {hf('full', 'multichart', 0.01).realized_fpr_mean:.4f}, "
                       f"a=0.003 {hf('full', 'multichart', 0.003).realized_fpr_mean:.4f}; max full a=0.01 "
                       f"{hf('full', 'max', 0.01).realized_fpr_mean:.4f}"),
        verdict="weakened"))
    rows.append(dict(
        issue_id="m6", track="t3",
        original_claim="Submit-step stripping of round-1 refined trajectories (meta rule from the original)",
        corrected_claim="Fixed (strip only real submit calls). No round-1 point estimate changes.",
        numbers_before="project stripping",
        numbers_after=(f"streams changed per mode: {int(S1[S1['mode'] == 'full'].n_streams_changed.sum())} over 6 "
                       f"arm-variants; max |change| in any cross-table cell = {V1.effect_of_m6_fix.abs().max():.3g}"),
        verdict="holds"))
    return rows


def write(rows, path):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            assert r["verdict"] in ("holds", "weakened", "reversed", "dropped")
            w.writerow({k: r[k] for k in COLS})


def main():
    write(r2_rows(), R2 / "corrections_r2_t3.csv")
    write(r1_rows(), R1 / "corrections_t3.csv")
    print("wrote corrections_r2_t3.csv, corrections_t3.csv")


if __name__ == "__main__":
    main()
