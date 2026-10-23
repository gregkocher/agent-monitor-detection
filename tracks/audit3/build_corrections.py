"""Audit pass 3: assemble results/audit3/corrections.csv (claim, location, original, corrected/verdict, severity, note).

    unset VIRTUAL_ENV; uv run python -m tracks.audit3.build_corrections

Rows for r4_replay come from results/audit3/rep_r4_issues.csv and rows for r4_cs from results/audit3/cs_corrections.csv
(written by those sub-audits); the rest are listed here. Every number is from a results/audit3 file named in `note`.
"""
from __future__ import annotations

import pandas as pd

from amd.common.schema import REPO

OUT = REPO / "results" / "audit3"
COLS = ["claim", "location", "original", "corrected/verdict", "severity", "note"]

ROWS = [
    # ------------------------------------------------------------------ cross-cutting
    ("Randomized plug-in threshold realizes nominal FPR (all tracks using amd.evaluation.calibration.randomized_threshold "
     "or its weighted / vectorized copies)", "amd/evaluation/calibration.py; r4_wb, r5_jev, r4_replay, r4_cs",
     "expected FPR ~ alpha",
     "CORRECTED: for continuous scores the out-of-sample FPR is (floor(alpha n)+1)/(n+1); when alpha n is an integer the "
     "rule sits one order statistic too low (n=100, 1%: 1.98%; n=200: 1.49%; n=300: 1.33%). Randomization only helps "
     "tied (integer-score) monitors, so continuous vs tied monitors are compared at unequal realized FPR unless realized "
     "FPR is matched.", "major",
     "wb_convention.csv (simulation = theory). Biggest effect on LinuxArena sweep panels (n_cal=100). Always report and "
     "compare realized FPR; at integer alpha n use h = k-th largest with gamma = 1."),
    ("No monitor sees agent reasoning (label-leak check requested after commit 519fd6a)",
     "amd/scoring/prompts.render_step; amd/data/{monitoringbench,akshn}.py; tracks/wb_whitebox/export_inputs.py; "
     "tracks/r5_jev/jevlib.py; tracks/r2_t1/ps_score.py; MOLE renders",
     "reasoning text is near-label-revealing (MB AUROC 0.03; aksh-n LinuxArena 0.81)",
     "HOLDS for every monitor scored in this repo: Step.reasoning is rendered only with include_reasoning=True, which no "
     "track sets (no score file has a '-cot' monitor id); white-box reader, nano, gpt-4.1(-mini) none/window/full/"
     "trajectory, JEV, Decider, PS psdiff prompts (desc+diff only) and MOLE audit-event renders exclude it. Text-only "
     "assistant turns (ingested as '[assistant message]' action steps, visible to all monitors) occur in 0 of 3,194 MB "
     "trajectories' visible steps and 0 aksh-n / LinuxArena-sweep steps, so no prose leaks either. History-aware vs "
     "history-free gaps are therefore not reasoning leakage. Visible step count remains label-correlated (MB AUROC 0.70; "
     "BashArena opus-4-6 0.16, sonnet-4-5 0.08), which history / trajectory monitors can use (earlier m8).",
     "info", "leak_reasoning.csv. Not verifiable: external scores computed by dataset authors (aksh-n Gemini-3.1-Pro "
     "'nonpriv' streams, LinuxArena sweep monitors, persistent-state GPT-4o natives); aksh-n LinuxArena reasoning is "
     "attack-heavy (AUROC 0.81), so if that judge saw agent_reasoning its LinuxArena baseline would be inflated. MOLE "
     "session arms (r4_wb part 3) show assistant turn content by design, equally in every arm."),
    # ------------------------------------------------------------------ r4_ctx
    ("r4ctx primary: Stackelberg - global selection safety, aksh-n 7 settings, B=1%, spend-matched",
     "EXPERIMENT_LOG r4ctx results; results/r4_ctx/primary.csv", "+0.107 [+0.024, +0.152], P(>0)=1.00",
     "HOLDS WITH CAVEAT: reproduced exactly (+0.1069 [+0.0238, +0.1524]). The informed attacker picks SHADE under global in "
     "10/10 splits; SHADE, iac and agentdojo (5/5/16 main tasks) are resampled as single trajectories. With main-task "
     "cluster resampling (same splits): +0.107 [-0.004, +0.251], P(>0)=0.97 -> the pre-specified criterion (CI > 0) is "
     "not met under task-level clustering.", "major",
     "ctx_primary_checks.csv, ctx_selected_context.csv. Stackelberg raises SHADE test FPR to 5.0% (global 2.7%). A 5-task "
     "bootstrap is coarse; report both intervals."),
    ("r4ctx exact spend matching", "tracks/r4_ctx/r4lib.match_spend", "realized spend exactly B",
     "HOLDS WITH CAVEAT: the level is bisected on the TEST honest half (oracle operating point, same for every rule), so "
     "the comparison is at equal realized spend but not deployable; deployable nominal fits over-spend (Stackelberg 1.08% "
     "vs global 0.97% in the primary cell; nominal-fit delta +0.134 [+0.073, +0.182]).", "minor", "ctx_primary_checks.csv"),
    ("r4ctx pre-specification precedes analysis", "commits edb5cfd (14:17) / d2f4134 (14:53)",
     "'written before any allocation result'",
     "HOLDS WITH CAVEAT: prose design committed first, but r4lib.py / run_r4.py were not committed until the results "
     "commit (raw runs 14:20-14:30). Code matches the prose.", "minor", "data/processed/r4_ctx/runs mtimes"),
    ("r4ctx takeaway 1 'the 1% Stackelberg advantage ... is real: about +0.1'", "EXPERIMENT_LOG r4ctx takeaways",
     "real, ~+0.1", "CORRECTED wording: +0.1 point estimate, significant only with trajectory-level resampling in the "
     "small-task settings; driven by SHADE.", "major", "see r4ctx primary row"),
    # ------------------------------------------------------------------ r5_jev
    ("r5jev preregistration precedes held-out scoring", "commit f4d792a 19:18:42",
     "before any held-out call",
     "HOLDS: first held-out request file 19:19:12; eval logs later; primary code unchanged after prereg except the "
     "tested vectorization and the added LinuxArena-sweep secondary cells; provisional run killed before output "
     "(primary_run1.log has no hypothesis table).", "info", "data/r5_jev/logs, git diff f4d792a 37c76c6"),
    ("r5jev H1-H3 numbers reproduce", "results/r5_jev/hypotheses.csv", "as committed",
     "HOLDS: independent reimplementation (20 splits, B=400): H1-MB -0.003, H1-AK +0.001, H2-MB +0.005, H2-AK +0.174, "
     "H3-MB +0.010; same verdicts. Equal escalation (honest 0.105 vs 0.105) and equal realized FPR (~1.5% MB, ~1.2% "
     "aksh-n) between compared arms.", "info", "jev_indep_hyp.csv; jev_rerun/ (committed pipeline rerun)"),
    ("H1-AK supported (JEV->Gemini e=20% non-inferior to Gemini only, 6 settings pooled, 1% FPR)",
     "EXPERIMENT_LOG r5jev results; hypotheses.csv", "+0.001 [-0.015, +0.025], Holm p 0.005, supported",
     "HOLDS WITH CAVEAT (fragile): a cancellation of SHADE +0.17 and BashArena-opus-4-6 -0.24. Leave SHADE out: -0.025 "
     "[-0.038, +0.006], p_NI 0.27 (not NI). Equal-weight settings: -0.008 [-0.027, +0.019], p_NI 0.010. Main-task "
     "resampling (SHADE/iac have 5 tasks): p_NI 0.011 (B=2000) -> Holm ~0.022, just under 0.025; equal-weight p_NI 0.08. "
     "At 5% FPR the pooled cascade is significantly worse (-0.022 [-0.034, -0.011]). The SHADE gain exists only at 1% "
     "(5%: +0.009 [-0.07, +0.08]).", "major", "jev_indep_hyp.csv, jev_h1ak_task.csv, jev_indep_settings.csv"),
    ("H1-AK / aksh-n standalone JEV-vs-Gemini: equal inputs", "amd/data/_util.trunc; jevlib (4,000-char head+tail); "
     "aksh-n Gemini scores (dataset's, full actions)", "implicitly equal",
     "CAVEAT: JEV routes on head+tail-truncated actions while Gemini scored full actions (opus-4-6 attacks lose a median "
     "52% of action text; Gemini's top step is truncated in 75% of opus-4-6 attacks, 48% sonnet-4-5, 27% LinuxArena). "
     "This biases AGAINST JEV, so H1-AK's NI is conservative w.r.t. truncation and describes a deployable 4k-capped gate; "
     "the opus-4-6 -0.24 loss is partly a truncation effect. Standalone JEV-vs-Gemini gaps on BashArena / LinuxArena "
     "(RQ2) are not like-for-like. MB, nano (H2-AK) and probe (H3) comparisons used the same truncated text.",
     "major", "commit 519fd6a, results/r5_jev/explore_length_*.csv"),
    ("H1-MB supported", "hypotheses.csv", "-0.003 [-0.006, +0.002]",
     "HOLDS WITH CAVEAT: second stage weak (mini TPR 0.11 at realized 1.5%); margin 0.03 is 26% relative; the LLM-score "
     "oracle gate equals LLM-only. Not trivial: random e=20% fails NI (-0.022 [-0.103, +0.020]).", "minor",
     "cascade_cells.csv"),
    ("H2-AK: JEV triage beats nano triage (+0.17)", "hypotheses.csv", "+0.171 [+0.141, +0.203]",
     "HOLDS WITH CAVEAT: robust to task resampling (+0.174 [+0.129, +0.210]); but JEV's frozen request sees the main task "
     "+ 3 previous steps and a dev-selected rubric, nano's `none` prompt sees only the current step (dev: the window "
     "added ~+0.03 capture). It compares the two first-stage designs, not the two models.", "minor",
     "jevlib.VARIANTS, amd/scoring/prompts; dev_selection.csv"),
    ("H3-MB supported (JEV vs FIBS-axial probe cascade)", "hypotheses.csv", "+0.012 [-0.006, +0.034]",
     "HOLDS WITH CAVEAT: degenerate panel (both within 0.01 of LLM-only); same window confound as H2.", "minor",
     "cascade_cells.csv"),
    ("MB 5% FPR: JEV cascade e=5/10% beats mini-only (+0.046 / +0.040); probe e=5% +0.035",
     "EXPERIMENT_LOG r5jev secondary", "CIs above 0",
     "CORRECTED: at realized FPR 6.3-6.7% vs 5.6-5.8%. At equal realized FPR: JEV e=5% +0.014 [-0.018, +0.092], "
     "e=10% +0.020 [-0.004, +0.076], probe +0.008 [-0.023, +0.060]; none significant.", "major", "jev_equalfpr.csv"),
    ("RQ2: standalone JEV beats mini on MB at 1% (0.215 vs 0.103); Decider 0.19 vs JEV 0.23",
     "EXPERIMENT_LOG r5jev exploratory", "JEV > mini",
     "CORRECTED: JEV-only runs at realized FPR 2.4-2.7% vs 1.5-1.8%, and cannot reach the LLM's FPR (2.2% even at "
     "nominal 0.2%). At 2.2% vs 1.8%: +0.074 [-0.013, +0.205], n.s.; not shown at equal FPR.", "moderate",
     "jev_equalfpr.csv, jev_indep_equalfpr.csv"),
    ("JEV-only MB realized FPR 0.024 explained by 0.01 rounding ties", "EXPERIMENT_LOG r5jev secondary",
     "ties at the top of the honest distribution",
     "CORRECTED mechanism: no top ties (top honest maxima 0.94, 0.92, 0.92, 0.91); 8 of the top 9 honest JEV maxima come "
     "from one main task, so the threshold does not transfer across task-grouped splits (A1-type).", "minor",
     "jev_indep_equalfpr.csv"),
    ("aksh-n clustering in r5jev", "tracks/r5_jev/splits.py", "groups = trajectory for iac/SHADE/agentdojo",
     "CAVEAT: those settings have 5/5/16 main tasks; per-setting SHADE +0.171 [+0.070, +0.282] becomes [+0.006, +0.213] "
     "with task resampling (S=20, B=400). 20/15 agentdojo/iac evaluation trajectories duplicate dev-sample action "
     "sequences; 21/40 duplicate pairs inside evaluation.", "minor", "jev_indep_settings.csv"),
    ("Secondary/exploratory r5jev claims (Decider 'viable replacement', RQ3 overlap ratios)", "EXPERIMENT_LOG r5jev",
     "as logged", "HOLDS as exploratory; Decider arm scope extended after the budget raise; RQ3 intervals omit threshold "
     "noise and several confident-benign cells have 4-15 attacks; uncorrected.", "minor", "explore_*.csv"),
]

WB = [
    ("r4_wb H1: FIBS axial (none) - gpt-4.1-mini (none), held-out MB, 1%", "log Part 1; results/r4_wb/primary.csv",
     "+0.203 [+0.100, +0.296]",
     "HOLDS: rerun reproduces to 4 decimals; independent +0.198 [+0.104, +0.292] (joint task bootstrap [+0.103, +0.293]); "
     "both at exactly 1.00% realized FPR +0.167 [+0.065, +0.256].", "info",
     "wb_primary.csv, wb_rerun_primary/. ~2.7 calibration exceedances; held-out = new trajectories on largely the same "
     "scenarios (762/1000 share task x side x agent with pilot)."),
    ("r4_wb prereg timing", "c3cfacc 14:17:13", "before any held-out scoring",
     "HOLDS WITH CAVEAT: PREREG.md / heldout.json unchanged; first held-out cache row 14:17:30; analyze_primary.py last "
     "modified 19:04 after data existed (not committed earlier) but matches PREREG; '1,869 no earlier track scored' is "
     "false (T2 trajectory-level scores; not used for selection).", "minor", "wb_disjoint.json"),
    ("r4_wb external honest: reader threshold transfers at least as well as the LLM's", "log Part 1",
     "1.20% vs 1.42% at 1%; 4.99% vs 7.16% at 5%",
     "FAILS as worded: ~2.4 vs 2.8 alarms of 200 at 1% (CP 95% for 2/200 [0.1%, 3.6%]); gap [-1.8, +1.1] pp at 1%, "
     "[-6.1, +0.8] pp at 5%. No evidence of worse transfer; cannot rank.", "moderate", "wb_primary_external.csv"),
    ("r4_wb LinuxArena: reader above 7 sweep monitors (Holm)", "la_paired.csv", "7 Holm-significant at nominal 1% "
     "(reader realized ~2%)",
     "HOLDS WITH CAVEAT: the preregistered equal-realized-FPR comparison was not run (undeclared). At equal 1.00%: 7 "
     "(gpt-5.4 +0.19 [+0.07, +0.35], Holm 0.018); at equal 2.0%: 6 (gpt-5.4 Holm 0.090). Reader TPR at true 1% is "
     "0.66-0.71, not 0.76-0.81. n_cal=100 -> 1% rests on one calibration point.", "major",
     "wb_la_equalfpr.csv; realized-FPR gap is mostly the integer-alpha-n convention, not A1 shift"),
    ("r4_wb A1 MB table: FIBS axial full 'equal realized FPR' +0.061 [+0.021, +0.219]", "a1_mb_equalfpr.csv",
     "significant at equal FPR",
     "CORRECTED: value is at the reader's FPR floor (1.62-1.72%), not equal FPR; bootstrap bias +0.035-0.040, basic "
     "interval [-0.10, +0.10]; not significant. FIBS axial none (+0.189 [+0.101, +0.270]) and sab full hold.",
     "moderate", "wb_a1_mb.csv"),
    ("r4_wb MOLE: policy activations do not beat the reader (M1, AUROC)", "log Part 3", "-0.035 [-0.075, +0.008]",
     "CORRECTED: AUROC reproduces, but the preregistered TPR@5% session FPR (not reported) shows the reader detects more: "
     "0.49 vs 0.24, -0.24 [-0.34, -0.10], Holm < 0.001.", "major", "wb_mole.csv"),
    ("r4_wb MOLE: removing the insider instruction changes the policy probe by nothing measurable", "log Part 3",
     "M3 -0.002 [-0.017, +0.014]",
     "CORRECTED: holds only for sab max AUROC (shift bounded to ~+-0.017); TPR@5% -0.058 [-0.106, -0.025] (Holm 0.008), "
     "mean statistic +0.014, fibs_tok max -0.085, jl_lm max -0.060. 'Probes key on content, not the instruction' "
     "over-generalizes from sab.", "major", "wb_mole.csv"),
    ("r4_wb MOLE: gpt-4.1-mini beats every sab-max probe arm (M5)", "mole_contrasts.csv", "-0.086, Holm 0.005",
     "HOLDS WITH CAVEAT: reproduced -0.086 [-0.138, -0.037], Holm 0.015; whole-session LLM vs max-over-turns probe is "
     "history/aggregation-confounded; with the mean statistic reader - LLM +0.050 [+0.008, +0.098] (secondary).",
     "moderate", "wb_mole.csv"),
    ("r4_wb MOLE: pilot's high AUROCs came from the mean statistic and unmatched negatives", "log Part 3",
     "both causes", "CORRECTED: 'unmatched negatives' fails; with matched negatives mean-statistic AUROCs are still "
     "0.94-0.96.", "moderate", "wb_mole.csv"),
    ("r4_wb strata all positive", "primary_strata.csv", "every structure / side task positive",
     "HOLDS (descriptive, unadjusted; S2 n=63).", "minor", "wb_primary.csv"),
]


def main():
    rows = [dict(zip(COLS, r), track="cross-cutting" if i < 2 else ("r4_ctx" if i < 6 else "r5_jev"))
            for i, r in enumerate(ROWS)]
    rows += [dict(zip(COLS, r), track="r4_wb") for r in WB]
    for name, track in (("rep_r4_issues.csv", "r4_replay"), ("cs_corrections.csv", "r4_cs")):
        p = OUT / name
        if p.exists():
            d = pd.read_csv(p).rename(columns={"corrected_or_verdict": "corrected/verdict"})
            d["track"] = track
            rows += d[COLS + ["track"]].to_dict("records")
    df = pd.DataFrame(rows)
    df["location"] = df.track + ": " + df.location.astype(str)      # keep the six-column format of earlier passes
    df[COLS].to_csv(OUT / "corrections.csv", index=False)
    print(df.groupby(["track", "severity"]).size())


if __name__ == "__main__":
    main()
