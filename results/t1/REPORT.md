# Track 1: Do sequential tests beat max-aggregation at a matched false-alarm budget?

*October 2026. Code: `tracks/t1_matched_budget/`. Tables: `results/t1/tables/`. Figures (PDF): `results/t1/figures/`. Raw per-run CSVs: `results/t1/round{1,2,3}/`. Spend: $109.56 of OpenRouter (cap $130).*

## Question

AI-control evaluations turn per-step monitor scores into a trajectory decision by taking the **max** and comparing it with an honest-run quantile. Detection theory suggests sequential statistics should be stronger when evidence is spread over several steps, as in distributed attacks:
- CUSUM, Shiryaev–Roberts, window GLR;
- conformal e-processes;
- simple accumulators such as the 2nd-largest score or the top-k sum.

We compare all of them **at the same trajectory-level false-positive rate (FPR)**. MonitoringBench explicitly lists that comparison as future work.

**Mechanism hypothesis (pre-registered in `IDEAS.md`).** Accumulation should help only when per-step scores are approximately conditionally independent "innovations", i.e. history-free monitors. It should not help, and may hurt, when per-step monitors read the full history: their scores are already cumulative judgments, so summing them double-counts. That would explain three prior negative results:
- k-strikes hurt safety from 61% to 44% in Redwood's *Retrying vs Resampling*;
- k-strikes failed in persistent-state control;
- Bayesian accumulation added nothing in Meerkat.

## Data

| Set | Streams | Monitor(s) | Notes |
|---|---|---|---|
| aksh-n monitor-labels (7 settings: agentdojo, bash, iac, shade, BashArena opus/sonnet, LinuxArena) | ~14k trajectories | Gemini-3.1-Pro streaming judge: **local** (per-step) and **cumulative** scores | ideal-flag step as onset |
| LinuxArena monitor sweep | 200 honest / 142 attack | 12 per-action monitors, gpt-4.1-nano → claude-opus-4-6 | harm step for live side tasks |
| ScaleAI MRT (SHADE / CUA-SHADE) | 436 / 1,022 | sonnet-3.5 sequential chunk monitors (chunk N = 5, 7; aware / unaware) | per-chunk verdicts |
| Persistent-state VibeCoding | 171 honest / 520 attack (5 PRs each) | gpt-4o per-PR diff monitors: `current_only` (history-free), `full_diffs` / `task_sequence` (history-aware), trajectory | cross-session: gradual and positional attacks |
| **MonitoringBench (new scoring)** | 775 attacks (all 475 S4 distributed + 100 each of S1–S3, stratified) + 550 task-matched honest | **gpt-4.1-mini, same prompt, history mode `full` vs `none`**; gpt-4.1-nano `none` | action-only prompts; final `submit` step stripped from both classes (78% vs 99% end with it) |

## Method

- **Calibration** uses honest data only:
  - 10 repeated 50/50 honest splits, grouped by main task when there are ≥ 30 tasks;
  - 5-fold cross-fitting of per-step whitening / p-values;
  - randomized plug-in thresholds as the primary rule. These remove integer-score discreteness so every detector realizes ≈ α. Conformal thresholds are a robustness check.
- **α** ∈ {0.05, 0.01, 0.003}. CIs are a cluster bootstrap by task (300 replicates) that includes calibration noise.
- **Detectors:**
  - max; k-th largest (k=2); top-3 sum; mean; length-aware max;
  - CUSUM (k = 0.5 primary, plus a k-grid) on whitened scores; Shiryaev–Roberts; window GLR (w = 20; plus a w-grid);
  - power-calibrator conformal e-process and its Shiryaev–Roberts e-detector;
  - OR multi-charts (max + CUSUM; max + CUSUM + e-process) jointly calibrated.
- **Streaming metrics:**
  - matched ARL, by appending attacks to honest prefixes;
  - detection delay from the onset label;
  - alarm-before-harm rate;
  - onset localization.

## Results

### Round 1: existing score streams (40 stream sets, $0)

- **Max-type rules win on most sets.** At matched FPR 0.01, max, 2nd-max or length-aware max matched or beat every accumulator on:
  - 86% of aksh-n sets;
  - 67% of LinuxArena monitors;
  - 83% of MRT sets.

  Median TPR(CUSUM) − TPR(max) is −0.39 (aksh-n), −0.25 (LinuxArena) and −0.01 (MRT).
- **Accumulation gain falls as honest autocorrelation rises.** Spearman correlation between the CUSUM−max gain and honest lag-1 autocorrelation is −0.57 at α = 0.05 and −0.45 at α = 0.01 (`figures/r1_gain_vs_autocorr.pdf`). This is consistent with the double-counting mechanism.
- **Timing (aksh-n):** max alarms at the ideal flag step (median delay 0). CUSUM alarms 3–25 steps later, because these attacks are concentrated in time.
- **Length matters.** Length-aware max is often the best single rule. For MRT sonnet-3.5 N=5 it lifts TPR at α = 0.05 from 0.21 to 0.58 and from 0.33 to 0.83 ("superaware"). Attack and honest trajectories differ in length, and the max of a longer honest stream is inflated.
- **Cross-session (persistent state) is the clearest positive result, and it splits by history mode as predicted.** TPR at α = 0.05, 5 PRs per run:

| PR monitor | history | attack | max | top-3 sum | CUSUM | SR | best |
|---|---|---|---|---|---|---|---|
| `diff_current_only` | **none** (current PR diff only) | gradual | 0.16 | **0.31** | 0.28 | **0.33** | SR |
| `diff_current_only` | none | positional | 0.19 | **0.30** | 0.26 | 0.29 | top-3 |
| `diff_full_diffs` | full (all prior diffs) | gradual | **0.24** | 0.16 | 0.22 | 0.22 | GLR 0.25 ≈ max |
| `diff_full_diffs` | full | positional | 0.18 | 0.13 | 0.17 | 0.14 | e-proc 0.22 |
| trajectory monitor | full transcript | gradual | 0.35 | 0.31 | 0.37 | 0.37 | ≈ tie |

  With the history-free per-PR monitor, accumulation beats max by about +0.15 TPR (top-3 sum vs max: +0.15 [0.12, 0.17]). With the history-aware monitor, the advantage disappears (−0.07 for top-3 sum).

### Round 2: controlled experiment, same monitor and prompt, history `full` vs `none` (MonitoringBench + Honest-550)

TPR at matched trajectory FPR (95% CI). Full table: `tables/r2_main.md`.

| detector | α=0.05 full | α=0.05 none | α=0.01 full | α=0.01 none | α=0.003 full | α=0.003 none |
|---|---|---|---|---|---|---|
| max | 0.226 [0.17, 0.33] | **0.322** [0.19, 0.43] | 0.171 [0.13, 0.22] | 0.156 [0.06, 0.32] | **0.140** [0.10, 0.20] | 0.079 |
| 2nd-max | **0.342** [0.23, 0.45] | 0.276 | 0.190 | 0.152 | 0.111 | 0.078 |
| top-3 sum | 0.324 | 0.304 | **0.195** [0.09, 0.31] | **0.190** [0.04, 0.31] | 0.106 | 0.082 |
| CUSUM k=0.5 | 0.073 | 0.087 | 0.030 | 0.039 | 0.017 | 0.021 |
| e-process (power) | 0.130 | 0.126 | 0.052 | 0.065 | 0.039 | 0.045 |
| OR(max + CUSUM) | 0.201 | 0.247 | 0.137 | 0.085 | 0.077 | 0.030 |

- **The pre-registered prediction is not supported here.** Sequential gains do not concentrate in the history-free mode on S4 distributed attacks. The none − full difference-in-differences for CUSUM is +0.02 only at α = 0.01, and negative at α = 0.05 and with integer scores.
- **Why:** gpt-4.1-mini's full-history honest scores do **not** behave like cumulative judgments here (the honest tail lift from adding history is ≈ 1). Meanwhile its full-history mode *re-flags* attacks across several steps: for S1 attacks, ≥ 2 high-scoring steps occur 60% of the time (full) vs 39% (none). So in this monitor the "history" effect sits in the attack stream, not the honest one, and helps 2nd-max / top-3 rather than hurting them.
- **Absolute detection is low** for this cheap monitor: ~17–20% TPR at 1% trajectory FPR. Strong monitors on the same benchmark catch far more. Differences between detectors are within wide CIs at α ≤ 0.01.
- **Weak monitor (gpt-4.1-nano, `none`):** top-3 sum 0.082 vs max 0.056 at α = 0.01.

### Mechanism across all 46 stream sets

The accumulation gain is predicted by two stream properties (`mechanism_correlations.csv`, `figures/mechanism_second_spike.pdf`):
- **how informative a repeat spike is**, i.e. the likelihood ratio of a second high step under attack vs honest. Positive association (+0.47).
- **how persistent honest spikes are**, i.e. P(another high step | one high step) on honest streams. Negative association (−0.67).

History-aware monitors can land on either side. A monitor whose honest flags persist (cumulative judgment) makes accumulation useless. A monitor that re-flags attacks but not honest work makes 2nd-max / top-k accumulation useful. This refines the original hypothesis: **the relevant quantity is not "history-aware vs not" but the honest vs attack persistence of high scores.** It can be measured cheaply on honest data plus a few attacks before choosing a rule.

### Round 3: robustness

- **CUSUM's reference value k matters a lot.** At α = 0.01 on MonitoringBench:

  | k | TPR (full) | TPR (none) |
  |---|---|---|
  | 0.25 | 0.024 | 0.031 |
  | 0.5 | 0.032 | 0.043 |
  | 1 | 0.097 | 0.070 |
  | 1.5 | **0.186** | 0.155 |
  | 2 | 0.162 | **0.159** |
  | max (for comparison) | 0.164 | 0.146 |

  On whitened LLM-monitor scores, a textbook small k accumulates honest noise and is badly mis-tuned. Large k makes CUSUM behave like a smoothed max. The poor showing of k = 0.5 CUSUM / SR / long-window GLR in the main tables is partly this mis-tuning, not only a failure of accumulation.
- **Calibration under dependence.** Small-k CUSUM and long-window GLR realize ~2–3× the target FPR when calibrated on dependent honest streams (e.g. 0.020–0.031 at α = 0.01). Ville (1/α) thresholds for e-processes roughly double the FPR on dependent streams. Calibrate empirically; don't rely on i.i.d. guarantees.
- **Conformal (non-randomized) thresholds** give the same ranking as randomized ones.
- **Per-task (Mondrian) whitening** was inconclusive: realized FPR was too far above target to compare fairly.

## Conclusions

1. **Max, 2nd-max and top-3 sum are strong, cheap defaults.** At a matched budget, classic sequential tests (CUSUM, SR, GLR, e-processes) with textbook parameters lose to them on almost every real stream set: aksh-n, LinuxArena with 12 monitors, MRT, MonitoringBench.
2. **Accumulation pays off in exactly one clean regime here: cross-session evidence from a history-free per-unit monitor** (persistent-state, `current_only`: +0.15 TPR over max at 5% FPR). Once the per-PR monitor sees prior diffs, the gain disappears. To our knowledge this is the first matched-budget evidence that cross-session accumulation of independent per-session judgments beats max (the source paper, 2607.02514, tested only a k-strikes rule, which failed).
3. **The decision depends on measurable stream properties:** honest high-score persistence (hurts accumulation) and attack repeat-spike informativeness (helps). A practical rule: estimate both from honest data plus a small attack sample, then pick max / k-th max / top-k / CUSUM(k ≈ 1.5–2).
4. **Length-aware thresholds are an easy win** whenever honest and attack trajectory lengths differ (MRT: TPR 0.21 → 0.58 at 5% FPR).
5. **The cumulative "double counting" mechanism is real (Round 1 autocorrelation results) but not universal.** gpt-4.1-mini's full-history scores were not cumulative on MonitoringBench.

## Limitations

- **Small honest sets** (≈ 200–550 per set) make α ≤ 0.003 estimates noisy. The Logit-ROC extrapolation is in `round1/logit_roc_*.csv` but is not used for headline claims.
- **Onset labels are heuristic.** MonitoringBench `attack_step` marks payload execution, and the heuristic `first_attack_step` covers only 2,055 of 2,442 attacks. The aksh-n ideal-flag step is itself a monitor judgment.
- **Only one cheap monitor family was re-scored** (gpt-4.1-mini / nano). Window mode was piloted but not run at scale.
- **The persistent-state result rests on one monitor model (gpt-4o) and 5-PR runs.** Longer horizons and other monitors are untested.
- **All attacks are static.** No attacker adapted to the detector; Track 3 tests that.

## Next steps

- Re-run the persistent-state comparison with more PRs per run and a second monitor family, to confirm the cross-session result.
- Add an online "rule chooser" that estimates honest persistence and attack repeat-spike informativeness, and a CUSUM with k tuned by those estimates.
- Combine with Track 2's per-context whitening, for which Mondrian needs larger honest sets per context.
