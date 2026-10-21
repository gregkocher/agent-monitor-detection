"""Write the audit issue table and the reproduction summary (results/audit/issues.csv, repro_summary.csv).

    unset VIRTUAL_ENV; uv run python tracks/audit/write_issues.py
"""
from __future__ import annotations

import csv
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "results" / "audit"

COLS = ["id", "track", "severity", "claim_affected", "evidence", "suggested_fix", "status"]
ISSUES = [
    ("C1", "r2_t2 (E5)", "critical",
     "E5: 'CFAR roughly doubles uniform TPR for heterogeneous probes (dec_full 0.24 -> 0.50 at 1%; fibs_fu_full 0.35 -> 0.62)'; "
     "all 1% 'spend-matched' rows in results/r2_t2/e5_tables.md for cfar / stack / stack_m0 / maxdet",
     "r2lib.nominal_and_matched uses np.interp, which clamps when the 0.25-2xB sweep never reaches B. In e5_allocation.csv the "
     "'matched' 1% rows realize spend: cfar 1.95-2.76%, stack 2.41-3.08%, maxdet 2.60-3.57% (global 0.87-1.07%). "
     "e5_tables.md drops the spend and matched_ok columns. So the 'doubling' compares CFAR at about 2.5x budget with global at 1x. "
     "The 5% rows are matched (spend 5.0-5.5%).",
     "Report spend and matched_ok in e5_tables. Drop or flag 1% rows with matched_ok=False, extend the multiplier sweep below 0.25, "
     "or state that per-context rules cannot reach 1% with 10-20 honest runs per cluster half (T2's own small-n result). "
     "Cheap re-analysis; no API.", "open"),
    ("C2", "t1 (r1, r2), r2_t1 (PS, MOLE, hybrid), PDFs", "critical",
     "Every 'gain over max' CI and the MB DiD CIs. Headlines: PS history-free top-3 vs max '+0.15 [0.12, 0.17]' (r1 / PDF 00 / 01), "
     "'+0.145 [0.13, 0.16]' gpt-4.1-mini and '+0.101 [0.09, 0.12]' gpt-4o (r2); MOLE '+0.131 [0.11, 0.15]' (n=30 insiders); "
     "MB 'CUSUM DiD +0.023 [0.015, 0.032]'",
     "t1lib.paired_gain and run_round2.paired_gains/DiD draw NEW attack-bootstrap indices in each split and then AVERAGE the replicates "
     "across splits, which shrinks the CI by about sqrt(n_splits). They also hold thresholds fixed (no calibration noise) and resample "
     "attacks iid (no task clustering). The paired_did helper in r2lib shares indices correctly. "
     "Independent reproduction (repro_t1_ps.csv, repro_t1_mb_*.csv): "
     "PS gpt-4o gradual a=0.05, gain +0.094: project-style CI [0.077, 0.108]; shared-index attack-only [0.019, 0.159]; "
     "with calibration noise [-0.093, 0.278] (p(<=0)=0.18); 5-app cluster [-0.068, 0.288]. "
     "PS gpt-4.1-mini, +0.174: [0.156, 0.192] / [0.107, 0.245] / [-0.083, 0.317] (p=0.13). "
     "MB full a=0.01 top3-max, +0.035: [0.029, 0.042] / [0.016, 0.057] / [-0.049, 0.105]. "
     "Gain sign is positive in 5/5 apps for both PS monitors at a=0.05.",
     "Use shared bootstrap indices across splits, resample honest calibration (cluster by task/app) with thresholds recomputed, and "
     "cluster attacks by task. Restate the PS result as 'directionally consistent (5/5 apps) but not significant once calibration noise "
     "is included'. r3_t1/r3lib.paired_gain_full is in progress and was not audited; mole_r3_analysis.py and reflag_analysis.py "
     "still call the old gains_table. Cheap re-analysis.", "open (quantified by audit)"),
    ("M1", "r2_t3", "major",
     "'Pacing vs control: +0.21 [+0.12, +0.29] against max and +0.18 against multichart, a real strategy effect'",
     "The pacing arms are ADAPTIVE: up to 2 feedback rounds with best-attempt selection on the same deterministic (T=0) scores and "
     "threshold used for evaluation. rewrite_control ran with rounds=0 (all 150 control trajectories are identical to their r0 version). "
     "One-shot vs one-shot, a=0.01, max: pace_max_r0 - control +0.095 [0.008, 0.183] attack-bootstrap, [-0.024, 0.190] with honest "
     "resampling; pace_multichart_r0 +0.063 [-0.016, 0.143]; pace_cusum_r0 +0.048 (n.s.). Adaptive minus r0 for pace_max is +0.11.",
     "Report the r0-vs-control contrast as the strategy effect (about +0.05 to +0.10, marginal) and the adaptive gain separately as "
     "oracle-feedback selection. Or run the control with matched feedback rounds (API).",
     "open (quantified by audit)"),
    ("M2", "t3, r2_t3", "major",
     "'Validity: judge preservation 98-99%', 'literal preservation 0.88-0.90', 'Undetected-success drops are genuine detection, not broken "
     "attacks'; every undetected-success level for the rewritten arms",
     "valid = LLM judge (gpt-4.1-mini) all_preserved only. The literal check is not part of valid, and the judge reads fabricated outputs. "
     "15-20% of judge-valid rewrites per arm lack a target literal that appears in the side-task description itself. Example: the first "
     "pace_max_r2 record (firewall side task, range 203.0.113.16/28) is missing '203.0.113' and is still valid=True. "
     "'0.88-0.90' is the mean literal fraction; only 73-80% of rewrites keep all literals. With strict validity at a=0.01 vs max: "
     "pace_max - nothing -0.15 -> -0.32; rewrite_control - nothing -0.36 -> -0.50; pace_max - control +0.21 -> +0.18 (robust).",
     "Report judge-only and strict validity as upper and lower bounds (repro_t3.csv). Add the literal check to valid, or flag it. "
     "Prioritize Docker replay (r3_t3 part A, in progress). Cheap re-analysis.", "open (quantified by audit)"),
    ("M3", "t3 REPORT, PDF 00/03", "major",
     "Round-1 headline 'detector-aware rewriting did not help the attacker; it hurt (condensation)'",
     "No rewrite control in round 1, and the monitor was gpt-4.1-mini full history over LLM-fabricated outputs. Round 2's control shows that "
     "rewriting alone costs -0.36 undetected-success, so the round-1 effect is mostly a rewrite artifact. The PDFs (built 2026-10-21 02:20) "
     "and results/t3/REPORT.md were not updated.",
     "Revise the PDF and REPORT text: the round-1 drop is not evidence about detector-aware strategy. Cheap.", "open"),
    ("M4", "t1 (r2 MonitoringBench)", "major",
     "Pre-registered test 'sequential gains concentrate in the history-free mode: not supported' and the mechanism 'history makes "
     "gpt-4.1-mini re-flag attacks'",
     "The full and none prompts differ by more than history. full tells the monitor that continuing or completing something suspicious "
     "set up earlier 'counts as evidence'. none tells it to 'score low even if it could be one part of a larger plan'. "
     "The re-flagging mechanism is exactly what the full-mode instruction requests. The PS prompts (r2_t1) are clean: same system prompt, "
     "only the prior diffs differ.",
     "Rescore a subset with a full-history prompt that has the none-mode instruction wording (about $15-30 API), or restate the result "
     "as a contrast of history plus instruction.", "open"),
    ("M5", "r2_t2 (E5)", "major",
     "E5 allocation and AUROC results that use attacks: 'Stackelberg >= global on 14/17 signals at 5%', CFAR uniform TPR, probe AUROCs",
     "541 attacks = 33 originals + 508 T3 refined variants of about 148 base attacks across 6 arms. 329 of 419 adaptive refined "
     "trajectories are byte-identical to their r0 version. split_panel splits attacks iid within context, so duplicates land in both the "
     "Stackelberg/maxdet fit half and the test half. 94% of attacks also have LLM-fabricated tool outputs, while honest outputs are real, "
     "so a probe can key on fabrication. From the matched CSV: stack >= global on 13/17 at 5%, not 14.",
     "Dedupe identical trajectories and group the split by orig_traj_id. Report TPR on originals separately and flag the fabrication "
     "confound. Cheap.", "open"),
    ("M6", "r2_t1 (chooser)", "major",
     "'Empirical chooser +0.023 [0.012, 0.038] over always-max at FPR 0.01' (and meta +0.019)",
     "The chosen rules over-alarm out of sample. Realized FPR at nominal 0.01: emp 0.0156, meta 0.0155, oracle 0.0179 vs always-max "
     "0.0142. At 0.05: 0.0559 vs 0.0532. Picking the rule with the highest labeled-attack TPR at its own calibrated threshold favors "
     "rules whose split threshold is low by calibration noise (winner's curse). A +10% FPR at TPR about 0.38 is worth about 0.01-0.02 "
     "TPR under a logit-linear ROC (slope 0.5-1), a large share of +0.023.",
     "Use nested calibration (choose the rule on one calibration half, set the threshold on the other) or compare at matched realized FPR. "
     "Cheap.", "open"),
    ("M7", "t1 REPORT, PDF 00/01", "major",
     "'The decision depends on measurable stream properties... estimate both from honest data plus a small attack sample, then pick' "
     "(practitioner lesson 3); mechanism Spearman p-values",
     "The out-of-sample mechanism-rule chooser (r2_t1) LOSES to always-max: -0.022 [-0.044, -0.000] at 0.01. The across-set correlations "
     "compute repeat-spike LR from the same attacks that define the gain, which is partly tautological. They also treat 46 or 67 "
     "correlated sets (full/none, local/cumulative, int/expected copies of the same data) as independent.",
     "Reword as descriptive. Cite the chooser result. Use set-family-level inference. Cheap.", "open"),
    ("M8", "PDF reports (docs/reports/*.pdf)", "major",
     "PDF 00 'one clean gain +0.15', 'Stackelberg best', 'OS-CFAR with LOCO tail resists poisoning', T3 condensation and sqrt(ARL) "
     "statements",
     "The PDFs predate round 2. Round 2 found: gpt-4o PS gain +0.10 on the paired filter, and history-free > history-aware holds for only "
     "2 of 4 monitors (gpt-4.1-mini DiD -0.17). The LOCO tail breaks under spread poisoning (0.88 -> 0.44 at 2%). The T3 effect is a "
     "rewrite artifact. Round-1 sqrt(ARL) slopes were fit out to ARL 1e4 with 550 honest runs (unresolvable above about 551).",
     "Regenerate the PDFs with round-2 and audit corrections (C2, M1-M7). Cheap.", "open"),
    ("M9", "t1, t3 (MonitoringBench)", "major",
     "Absolute MonitoringBench TPRs ('about 17-20% TPR at 1% FPR'; T3 'nothing' baseline)",
     "Agent-model confound. Honest-550 is 100% claude-opus-4-5, while 281/775 T1 attacks (36%) and 46/150 T3 base attacks are opus-4-6. "
     "Max TPR at a=0.01: full 0.25 (opus-4-6) vs 0.12 (opus-4-5); none 0.25 vs 0.14. The monitor may react to agent-model style rather "
     "than to the attack. Detector comparisons are paired, so less affected.",
     "Report TPR on the opus-4-5 subset as primary or alongside. Cheap.", "open (quantified by audit)"),
    ("m1", "t1 (r2), r2_t1", "minor",
     "'randomized thresholds... every detector realizes about alpha'",
     "At a=0.01 realized FPRs run 1.4-1.9x target: reproduction max 0.014/0.018, always_max in the chooser 0.0142. r2_main per-detector "
     "realized FPR spans 0.006-0.025 (max full 0.019 vs top3 0.008), but the independent rerun gives 0.014 vs 0.014, so the "
     "per-detector gaps are split noise. Cause: plug-in quantile on about 275 grouped-split honest runs (n*a = 2.75).",
     "Report realized FPR next to every TPR, or use the conformal or a larger calibration set at a=0.01.", "open"),
    ("m2", "t2", "minor",
     "'Stackelberg best against selection (7 settings 0.79 vs 0.64 at 1%)'",
     "(a) The informed attacker estimates context weakness from the SAME calibration attacks Stackelberg was fit on. With independent "
     "attacker info (3-way split): 0.775 vs 0.791 at 1%, 0.957 vs 0.966 at 5%; still above global (0.64 / 0.89). Claim holds. "
     "(b) In spend-matched mode the 1% 7-settings interval crosses 0 (-0.11..+0.20). ControlArena Stackelberg spends 1.38% vs global "
     "0.97% nominal and shows no gain when matched (0.610 vs 0.607, matched_ok 0.66).",
     "Use disjoint attacker-information data and caveat 1%. 5% is robust (+0.03..+0.12).", "open (quantified by audit)"),
    ("m3", "t2 REPORT / PDF", "minor", "'OS-CFAR with a LOCO tail holds 0.77-0.86'",
     "Range taken from la_env_local. At eps=10%: akshn 0.72, ControlArena 0.71, la_taskcat 0.62. Unpoisoned cost on la_taskcat: 0.778 vs "
     "global 0.914. Round 2 E2 shows the LOCO tail breaks under spread poisoning.",
     "Quote per-panel ranges and the unpoisoned cost.", "open"),
    ("m4", "r2_t3", "minor",
     "'Pacing vs round-1 condensation: +0.07-0.10 (significant at alpha=0.003)'",
     "Selective. At a=0.01 all three CIs cross 0. At a=0.003, pace_cusum - r1_cusum on cusum1.5 is -0.103 [-0.183, -0.024], "
     "significant the other way. Twenty paired comparisons are reported with no multiplicity control.",
     "Report all comparisons and the sign reversal. Add a Holm correction or a pre-specified primary contrast.", "open"),
    ("m5", "t3, r2_t3", "minor", "All T3 CIs and threshold validity",
     "Thresholds are calibrated in-sample on all 550 honest runs (no held-out FPR). CIs resample base attacks only. Adding honest "
     "resampling widens pace_max - control from [0.119, 0.294] to [0.063, 0.325]; at a=0.003, pace_max - nothing becomes [-0.167, +0.024].",
     "Add honest resampling to the CIs (repro_t3.csv column ci_attack_and_honest_boot).", "open (quantified by audit)"),
    ("m6", "r2_t3", "minor", "Submit-step stripping of refined trajectories",
     "_submit_last_idx uses the ORIGINAL's submit_step: when len(refined) == len(original), the last refined step is dropped even if it "
     "is not a submit. 12 adaptive (16 incl. r0) refined streams lost a real final step. Effect is negligible (the reproduction stripping "
     "only real submits matches to 2 decimals).",
     "Strip only when the last action is a submit call.", "open"),
    ("m7", "t1", "minor",
     "Practitioner default 'max with a length-aware null' (MRT 0.21 -> 0.58)",
     "Gains come where honest and attack length distributions differ, and an attacker controls length. CIs are very wide (MRT superaware "
     "length-aware 0.70 [0.38, 0.92]). The gain persists in length-matched subsets, which supports it.",
     "Add an attacker-padding caveat and report CIs.", "open"),
    ("m8", "t1 / t3 data", "minor", "Label-correlated surface features",
     "16 honest (2.9%) vs 0 attack trajectories are truncated at 60 steps. The str_replace tool appears only in honest runs (3.3%). "
     "text_editor is used by 100% of honest vs 96% of attack runs. Visible reasoning is present on 100% of honest vs 57% of attack steps, "
     "hidden from all LLM monitors (prompts include_reasoning=False). The white-box export (in progress) should be checked for the same.",
     "Note in the data section. Check the WB renderer excludes reasoning.", "open"),
    ("m9", "r2_t1 (PS)", "minor", "PS gradual TPRs",
     "66/120 gradual attacks failed their side task but count as positives. Only 5 task sequences, so splits and bootstraps are iid over "
     "runs. An app-cluster bootstrap gives CIs similar to the iid full bootstrap (repro_t1_ps.csv).",
     "State the success-conditioned TPR as well.", "open"),
    ("m10", "r2_t1 (chooser)", "minor", "Chooser out-of-sample claim",
     "Labeled attacks are drawn iid, not grouped by task, from the same pool as the evaluation attacks. Chooser variants (margin, alpha' "
     "averaging, n_lab) were reported after seeing results.",
     "Group the labeled draw by task. Pre-specify one chooser.", "open"),
    ("m11", "r3_t2", "minor", "akshn_adj rows in results/r3_t2/tables.md",
     "The label-leaking upper-bound caveat is only in EXPERIMENT_LOG. The table shows watcher_strict / sev_tilt at 0.98-0.99 with no "
     "warning. The severity rater itself is blind (no side task, no reasoning).",
     "Add the caveat to the table header.", "open"),
    ("m12", "t1 (round 1)", "minor", "'max alarms at the ideal flag step (median delay 0)' on aksh-n",
     "The onset is the adjudicator's ideal_flagging_step, itself an LLM judgment about when evidence appears, so delay 0 for a spike rule "
     "is partly by construction. Acknowledged in Limitations.",
     "Keep the caveat next to the claim.", "open"),
    ("m13", "repo hygiene", "minor", "Secrets / payloads / docs",
     "No real secrets in the 466 tracked files. tracks/r2_t1/ps_score.py holds a synthetic 'sk-proj-' placeholder that will trip secret "
     "scanners. results/.key_index is untracked and not gitignored. README budget text ($500 cap) is stale (code: $1,400). The spend "
     "ledger reconciles with every reported track total (t1 109.56, t2 17.11, t3 68.36, r2t1 147.89, r2t3 304.77, r3t2 21.82, wb 2.95; "
     "total $793.43, all tracks under cap). No raw attack transcripts are committed; only test fixtures with target literals.",
     "Gitignore .key_index, rename the placeholder (e.g. a 'sk-proj-EXAMPLE' style marker), update the README.", "open"),
]

REPRO = [
    ("T1 r2 MB full a=0.05 max / top3sum TPR", "0.226 / 0.324", "0.216 / 0.311", "match (split noise)"),
    ("T1 r2 MB full a=0.01 max / top3sum TPR", "0.171 / 0.195", "0.166 / 0.202", "match"),
    ("T1 r2 MB none a=0.05 max / top3sum TPR", "0.322 / 0.304", "0.340 / 0.308", "match"),
    ("T1 r2 MB none a=0.01 max / top3sum TPR", "0.156 / 0.190", "0.180 / 0.202", "match (split noise)"),
    ("T1 r2 MB full a=0.01 top3 - max gain CI", "+0.024 [0.018, 0.031]", "+0.035; shared-index [0.016, 0.057]; full [-0.049, 0.105]",
     "point match; CI MISMATCH (understated)"),
    ("PS gpt-4o current_only gradual a=0.05 top3 - max", "r2 +0.101 [0.09, 0.12]; r1 +0.15 [0.12, 0.17]",
     "+0.094; shared [0.019, 0.159]; full [-0.093, 0.278]", "point matches r2 (not r1); CI MISMATCH"),
    ("PS gpt-4.1-mini current_only gradual a=0.05 top3 - max", "+0.145 [0.13, 0.16] (max 0.59 -> top3 0.73)",
     "+0.174 (0.585 -> 0.759); shared [0.107, 0.245]; full [-0.083, 0.317]", "point approx match; CI MISMATCH"),
    ("T2 7 settings B=1% sel_informed global / CFAR / Stackelberg", "0.645 / 0.404 / 0.791", "0.641 / 0.409 / 0.791", "match"),
    ("T2 7 settings B=1% uniform TPR global / CFAR / Stackelberg", "0.853 / 0.821 / 0.834", "0.853 / 0.822 / 0.834", "match"),
    ("T2 7 settings B=5% sel_informed global / Stackelberg", "0.89 / 0.97", "0.887 / 0.966", "match"),
    ("T2 7 settings Stackelberg with independent attacker info (1% / 5%)", "n/a", "0.775 / 0.957", "small optimism (m2)"),
    ("T3 r2 a=0.01 vs max undetected-success nothing / pace_max / rewrite_control", "0.75 / 0.60 / 0.40", "0.754 / 0.603 / 0.397", "match"),
    ("T3 r2 a=0.01 pace_max - rewrite_control (max)", "+0.206 [+0.119, +0.294]", "+0.206 [0.119, 0.294]", "exact match"),
    ("T3 r2 a=0.01 pace_max - nothing; rewrite_control - nothing", "-0.151; -0.357", "-0.151; -0.357", "exact match"),
    ("T3 r2 a=0.01 ONE-SHOT pace_max_r0 - rewrite_control", "not reported", "+0.095 [0.008, 0.183]; with honest resampling [-0.024, 0.190]", "new (M1)"),
    ("T3 r2 strict validity pace_max - nothing (a=0.01)", "not reported", "-0.317 [-0.421, -0.214]", "new (M2)"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "issues.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        w.writerows(ISSUES)
    with open(OUT / "repro_summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["quantity", "reported", "reproduced_independently", "verdict"])
        w.writerows(REPRO)
    print(len(ISSUES), "issues;", len(REPRO), "reproduction rows")


if __name__ == "__main__":
    main()
