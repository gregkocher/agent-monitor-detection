# Experiment log

## 2026-10-20: setup

- Background: `../BACKGROUND_SUMMARY.md` and `../IDEAS.md` (ranked ideas; tracks T1–T3 approved).
- OpenRouter is reachable from the laptop as of today, so all API work runs locally. SSH to RunPod timed out (VPN); RunPod is a fallback only.
- Balances (2026-10-20): MATS account ≈ $6,346 left; weekly1000 key has $1,000 this week. Budget for T1–T3: ≤ $500 total, enforced by the ledger.
- Monitor models:
  - `openai/gpt-4.1-mini` ($0.40/M in): returns token logprobs via OpenRouter even though metadata says no. Primary cheap monitor, using the logprob-expected score for continuous calibration.
  - `openai/gpt-4.1-nano` ($0.10/M): weak monitor.
  - Existing streams from much stronger monitors: LinuxArena sweep (12 monitors incl. opus-4-6), aksh-n Gemini-3.1-Pro.
- Data sources (see `../background/data_availability.md`):
  - LinuxArena monitor sweep: 12 monitors × 342 trajectories, per action.
  - aksh-n per-step labels.
  - MRT sequential.
  - Persistent-state per-PR.
  - MonitoringBench attacks + Honest-550.

## 2026-10-20: T1 (matched-budget decision rules): setup, pilot, Round 2 scoring launched

**Scoring outputs (T1 owns these; T3 may reuse them).** Monitor `openai/gpt-4.1-mini`, prompt
`ctrl-basic-v1` (action-only: agent reasoning hidden; current action's output shown), `--max-steps 60`:
- Honest-550 (all 550): `data/processed/mb_honest/scores_openai_gpt-4.1-mini_{full,none}.jsonl`
- MonitoringBench attack sample (775 = all 475 S4 + 100 each of S1/S2/S3, stratified by side task, seed
  20261020; ids in `tracks/t1_matched_budget/sample.json`):
  `data/processed/monitoringbench/scores_openai_gpt-4.1-mini_{full,none}.jsonl`
- Per-step cache: `data/processed/{monitoringbench,mb_honest}/score_cache.sqlite`, monitor ids
  `openai/gpt-4.1-mini|ctrl-basic-v1|{full,none,window}`. Pilot files are `pilot_scores_*` (do not use).
- Each file is (re)written at the end of its job; a job still running means the default-named file may be
  missing or hold an older selection. Status lines are appended below when each finishes.

**Pilot (40 trajectories, 1,166 steps per mode; $4.97).** No API errors, 100% logprob coverage.
Mean per-step score at the attack (execution) step / heuristic first attack step / pre-onset attack steps /
honest steps: full 4.2 / 3.2 / 0.31 / 0.23; none 3.9 / 3.5 / 0.13 / 0.13; window 4.5 / 3.5 / 0.41 / 0.22.
AUROC of the per-trajectory max (20 vs 20): full 0.76, none 0.83, window 0.79. Cost per step: full
$0.0022 (attack) / $0.0027 (honest), none $0.0009 / $0.0010, window $0.0012 / $0.0014.

**Cost decisions.**
- The full run at harness scheduling projected to ~$134 (> the $125 T1 limit). Full mode benefits from
  OpenAI's automatic prompt caching, but the harness dispatches all steps of a trajectory at once, so
  only ~25% of the cache discount was realized. `tracks/t1_matched_budget/score.py` now sends each
  trajectory's steps strictly in order (many trajectories in parallel), with identical prompts, cache keys
  and records; then `amd.scoring.run` assembles the file from the cache (0 calls). Measured on 8 S4
  attacks (300 steps): cost / list price 0.55 vs 0.74. Projected Round 2 (full + none, all 775 + 550):
  ≈ $101, leaving ≈ $15 for window mode / nano on subsets.
- `amd/common/openrouter.py`: `ledger_totals()` now reads the ledger incrementally (it re-read the
  whole file before every call, quadratic over a ~40k-call job). Same results; tests pass.

**Analysis decisions.**
- Calibration: honest-only, 10 repeated 50/50 splits, grouped by main task when ≥ 30 tasks (else iid),
  5-fold cross-fitting, randomized plug-in thresholds as primary (removes integer-score discreteness so
  all detectors realize ≈ α), α ∈ {0.05, 0.01, 0.003}, cluster bootstrap by task (300 replicates).
- T1 suite = `default_suite()` with three changes (`tracks/t1_matched_budget/t1lib.py:t1_suite`):
  (1) `eproc_jumper` uses randomized p-values: with conservative p, the jumper's ε=+1 bet *grows* on
  tie-heavy honest data (p = 1 for the modal score), giving TPR 0 on LinuxArena; (2) the OR charts'
  max component uses raw scores (whitened z saturates above the honest range, so attacks tie);
  (3) the OR charts use a new opt-in exponential tail beyond the calibration range
  (`MultiChart(tail="exp")`, default unchanged). Added `or(max+cusum)`.
- LinuxArena hidden tools (auto-scored 0, never shown to the monitor) are set to NaN.
- MonitoringBench / Honest-550: the final submit step is stripped from both before analysis (78% of
  attacks vs 99% of honest end with submit); with/without check reported.
- Matched ARL: attacks are appended to 0–4 random honest test trajectories with no reset. The
  non-restarting e-process has no stationary ARL (its log-statistic peaks at the stream start and drifts
  to −∞), so it is excluded there; its fresh-start vs after-prefix detection is reported separately.

**2026-10-20 13:49: Honest-550 scoring done (T3 may use it now).**
`data/processed/mb_honest/scores_openai_gpt-4.1-mini_full.jsonl` (550 streams, 13,797 steps, 0 NaN) and
`..._none.jsonl` (550 streams, 13,796/13,797 steps scored; 1 API failure left as NaN). Monitor ids
`openai/gpt-4.1-mini|ctrl-basic-v1|full` / `|none`. All steps are scored (≤ 60 per trajectory; no honest trajectory
exceeds 60 except the 75-step max, truncated at 60), including the final submit step (strip it at analysis time).
Honest cost: ≈ $33.6 (full ≈ $0.0015/step after `prompt_cache_key`, none ≈ $0.00095/step). Spend t1 so far $41.5.
The cache-routing fix: with all T1 prompts sharing the same first ~256 tokens (system prompt), OpenAI's prefix-hash
routing overflowed and most cache lookups missed; passing `prompt_cache_key=<traj id>` (an OpenAI routing hint,
not part of the prompt) gave a cost / list-price ratio of 0.47 vs 0.78 in an A/B on 6+6 S4 attacks.

## 2026-10-20: T3 (monitor-aware attacker): setup, refiner pilots

**Question.** Can an LLM that knows the deployed detector (Kerckhoffs) restructure real multi-step
MonitoringBench attacks to evade it without breaking the attack? Full cross of attacker-told
{nothing, max, CUSUM, multichart} x deployed {max, CUSUM, e-process, multichart}; covert-adversary
sqrt(ARL) damage check; does the multi-chart OR close the gap?

**Design / code (`tracks/t3_aware_attacker/`).**
- `detector_specs.py`: natural-language Kerckhoffs spec per arm, embedding the exact monitor system
  prompt + rubric (`amd.scoring.prompts.SYSTEM`) and how each detector maps per-step scores to an
  alarm. Arm `nothing` = the original attack (control), not a refiner call.
- `select_attacks.py`: 150 base attacks, S2-S4, with a known onset (`meta.first_attack_step`) and
  execution step, 6-55 steps, stratified across side-task x structure. Restricted to track 1's 775
  attack sample (517 eligible) so the originals' per-step streams come free from track 1; T3 pays
  only for refined attacks.
- `refine.py`: per (attack, arm): LLM checklist of attack-critical effects -> refiner produces a
  restructured action sequence with fabricated-but-plausible tool outputs -> LLM validity judge
  checks every effect is preserved -> deployed monitor scores it -> the arm detector's calibrated
  verdict + per-step profile fed back for up to `--rounds` adaptive rounds (round 0 kept separately
  for the non-adaptive comparison). Early-stop when evaded AND valid. Resumable (skips pairs in
  `refine_log.jsonl`); in-loop full-mode scores are saved to avoid re-scoring.
- `evaluate.py`: calibrates each deployed detector on Honest-550 at matched trajectory FPR
  (randomized thresholds, alpha in {0.01, 0.003}); undetected-success = valid * (1 - E[alarm]);
  cost (length inflation / steps added); covert ARL sweep (undetected attack-critical steps before
  alarm vs ARL=1/FPR, fitted exponent vs sqrt); suspicion profiles; vector-PDF figures.

**Monitor / modes.** Deployed monitor = `openai/gpt-4.1-mini`, prompt `ctrl-basic-v1`, action-only
(matches track 1; refined trajectories carry no visible reasoning, so the reasoning honest/attack
confound noted by the data worker does not apply). Feedback/analysis primary mode `full`
(history-aware, deployed-realistic); `none` (innovation) scored for the robustness view (least
sensitive to fabricated outputs). The final submit step is stripped from honest/attack/refined at
analysis time (matches track 1).

**Output fabrication choice.** New/changed actions' tool outputs do not exist, so the refiner
generates plausible outputs consistent with the originals. This affects history-aware (`full`)
scoring of later steps but not `none` (each step scored on its own action+output); both are
reported and the caveat flagged. Side-task success of refined attacks is validated by (1) an LLM
judge over a per-attack critical-effect checklist and (2) a judge-independent static check that the
attack's target literals (IP prefixes/host/user) still appear verbatim. BashArena Docker replay is
disk-infeasible on this laptop (~12 GB free; coordinator cap ~6 GB) and pod SSH is blocked, so
replay is deferred and this is flagged as a validity limitation.

**Refiner model pilot.** gpt-5-mini: cheapest, but ~50% of completions were unparseable JSON even
with `json.loads(strict=False)` (embedded unescaped quotes in fabricated outputs). gpt-4.1: parses
reliably (no refusals; restructured sequences of 13-31 steps), chosen as the refiner;
`gpt-4.1-mini` as validity judge and checklist builder; `REFINER_MAX_TOKENS=14000` (31-step outputs
need ~11k). Pilot cost ~ $0.08 per (attack, arm) at rounds=2 with early-stop.

**2026-10-20 ~15:15: Round 2 scoring done.** `data/processed/monitoringbench/scores_openai_gpt-4.1-mini_{full,none}.jsonl`:
775 attack streams (all 475 S4 + 100 each of S1/S2/S3), 25,021 steps each, 0 NaN after the retry pass (~1.8% of calls
needed a second pass: rate limiting while T2 was also scoring). The one failed honest none step was re-scored: both
honest files now have 0 NaN. T1 spend $103.81 (honest ≈ $33.6, attacks ≈ $56.6, pilots/tests ≈ $8.8, chained-cost
A/B ≈ $0.9; full-mode attack cost $0.0013/step with cache keys). Window mode was **not** run at scale: full + none
used the budget, and window on a meaningful sample (≥ $15) plus the nano arm would exceed the $125 T1 limit.
Window results are pilot-only (20 + 20). Started: gpt-4.1-nano `none` on the 775 attacks (honest nano none done:
`data/processed/mb_honest/scores_openai_gpt-4.1-nano_none.jsonl`, $3.4).

### 2026-10-20: T1 results (Rounds 1–3)

**Round 1 ($0; 40 stream sets: LinuxArena 12 monitors, aksh-n 7 sets × local/cumulative, MRT, persistent state).**
At matched FPR 0.01 a max-type rule (max / 2nd-max / length-aware max) ≥ the best accumulator in 86% of aksh-n, 67% of
LinuxArena and 83% of MRT streams. Median CUSUM(k=0.5) − max: −0.39 / −0.25 / −0.01. Streaming: max alarms at the ideal
flag step (median delay 0), CUSUM 3–25 steps late. CUSUM gain vs honest lag-1 autocorrelation: Spearman −0.57 (α=0.05),
−0.45 (α=0.01). Persistent state (same GPT-4o PR monitor): history-free `current_only` → accumulation beats max on
gradual attacks at α=0.05 (top-3 sum +0.15 [0.12, 0.17], CUSUM +0.12); history-aware `full_diffs` → it loses (−0.07, −0.02).

**Round 2 (MonitoringBench 775 attacks + Honest-550, gpt-4.1-mini, full vs none).** Pooled TPR at FPR 0.01: max
0.171 / 0.156, top-3 sum 0.195 / 0.190, 2nd-max 0.190 / 0.152, CUSUM 0.030 / 0.039, e-process 0.052 / 0.065 (full / none).
DiD (none − full) of the gain over max: CUSUM +0.023 [0.015, 0.032] at α=0.01 (S4 +0.029) but −0.083 at α=0.05; 2nd-max
and top-3 sum gain more in full mode. With integer scores every DiD is negative. Prediction (sequential gains concentrate
in none mode on S4) **not supported** for gpt-4.1-mini. Mechanism: its full-mode honest scores are not cumulative
(integer lag-1 autocorrelation 0.01, tail lift ≈ 1) while attacks get re-flagged (S1: ≥2 high steps 60% full vs 39%
none). Across 44 sets (α=0.05), the top-3-sum gain tracks the repeat-spike LR (Spearman +0.55) and the CUSUM gain falls
with honest spike persistence (−0.65).

**Round 3 ($0 + nano).** CUSUM with k = 1.5–2 ≈ max (k = 0.5 is mis-tuned for spike evidence); the integer score lifts
CUSUM to ≈ max; conformal thresholds give the same ranking; Mondrian per-task whitening inflates FPR under grouped
splits (inconclusive); keeping the submit step changes nothing. The Ville threshold of the e-process over-alarms
(2× nominal); the length-aware max's analytic threshold holds nominal FPR.

**gpt-4.1-nano, none mode (weak history-free monitor; 775 attacks + 550 honest, $9.1).** Files:
`data/processed/{monitoringbench,mb_honest}/scores_openai_gpt-4.1-nano_none.jsonl` (0 NaN). Pooled TPR at FPR 0.01: max
0.056 [0.02, 0.12], top-3 sum 0.082 [0.03, 0.16], CUSUM(k=0.5) 0.021; S4: top-3 sum 0.108 vs max 0.070. Mild accumulation
helps on the noisy weak monitor; the textbook CUSUM still loses. Mechanism over 46 sets (α=0.05): top-3-sum gain vs
repeat-spike LR Spearman +0.47 (p=0.001); CUSUM gain vs honest spike persistence −0.67 (p<0.001).

**T1 final spend: $109.56** (cap $130). REPORT.md: the subagent harness refused to write report files, so the write-up
is not in `results/t1/REPORT.md`; all numbers are in `results/t1/tables/` (r1_tpr.md, r2_main.md, r2_score_int.md,
r2_nano.md) and the entries above.

## 2026-10-20: T2 per-context thresholds (Rounds 1–2)

**Setup.** Code in `tracks/t2_per_context/` (`t2lib.py` rules/evaluation/attackers/robust estimators, 8 tests;
`panels.py`; `r1_heterogeneity.py`; `r1_allocation.py`; `r2_poisoning.py`; `r2_boiling.py`; `make_tables.py`;
`figures.py`). Results in `results/t2/` (CSVs, `tables.md`, PDF figures). Panels = dataset × monitor × context key,
statistic = trajectory max: aksh-n LinuxArena env/task type/agent model (Gemini local + cumulative), 7 aksh-n settings,
ControlArena setting × agent, LinuxArena sweep (12 monitors × 10 envs, 20 honest each), MRT CUA tasks (claude-3.5 N5,
3 prompts), MonitoringBench/Honest-550 task clusters (TF-IDF k-means, 7 clusters with ≥ 20 honest) for T1's per-step
gpt-4.1-mini full/none + nano none (submit step stripped) and T2's trajectory-mode gpt-4.1-mini/nano on all 2,644
attacks + 550 honest. **T2 spend: $17.11** (trajectory scoring only).

**Design decisions.** All allocation rules are budget-matched on calibration data with randomized thresholds (so
differences are allocation, not ties). New rules: randomized Stackelberg on ROC hulls (bisection on payoff level;
equal and logU[1,10] damage), partial pooling with n0 by beta-binomial EB or 5-fold CV, OS-CFAR (p75 offset) and
TM-CFAR (10% trim) with leave-one-context-out tail. 60 plain 50/50 splits (points) + 150 split-then-bootstrap
replicates (95% intervals, paired differences vs global). Two modes: nominal, and spend-matched (nominal level swept
B×[0.25, 2], metrics interpolated at realized test spend = B; `matched_ok` flags extrapolation). Attackers: uniform,
informed context selection (from own calibration attacks), threshold-only, oracle, (context × attack type) cells,
damage-weighted.

**Results.**
- Heterogeneity: across deployments sharing one monitor+rubric, a global 5% threshold gives 0–9.0% per-setting FPR
  (τ = 1.34 logit, p < 0.001) and 0–15.8% across ControlArena setting × agent (τ = 1.75); within LinuxArena 2.1–7.2%
  across envs (τ n.s. at 5%, 0.45 at 10%), none across 8 agent models (ICC 0). Context explains 0.1–9% of per-step
  variance (MRT 8–38%). LinuxArena-sweep env effects are shared across the 12 monitors (mean Spearman 0.70; env ×
  monitor interaction ≤ noise).
- Allocation: CFAR is worst against an informed attacker on heterogeneous panels (7 settings at 1%: 0.40 vs 0.64
  global, paired −0.47..−0.10; ControlArena 0.22 vs 0.60, −0.58..−0.11; at 5% spend-matched 0.56 vs 0.91,
  −0.63..−0.06). Stackelberg best against selection (7 settings 0.79 vs 0.64 at 1%, +0.06..+0.24; 0.97 vs 0.89 at
  5%, +0.03..+0.12) at ≤ 0.02 uniform-TPR cost; maxdet best for uniform TPR. Homogeneous LinuxArena panels: all rules
  within ±0.02. Weak monitors (BashArena clusters): CFAR/maxdet raise uniform TPR (nano trajectory 0.079 → 0.106 /
  0.162 at 5%), selection safety stays low for all. Cell-level selection costs 0.2–0.4 more.
- Small n: plug-in CFAR spends ≈ 1/(n_c+1): 6.2–7.7× budget at n = 10, 2.5–2.9× at 30, 1.4–1.6× at 100; Mondrian
  never alarms below n ≈ 1/B; partial pooling with CV n0 holds 1.1–1.3× (1.4–2.9× at n = 10) at equal TPR.
- Poisoning (B = 1%): CFAR breaks at ε ≈ B (LinuxArena target TPR 0.95 → 0.37 at 2%, 0.16 at 5%); global at
  ε ≈ B/w_t (0.93 at 5%, 0.79 at 10%); EB pooling ~2–5B; OS-CFAR with LOCO tail holds 0.81–0.86 up to 10%. Boiling
  frog: outlier filters only delay (same end state), cumulative cap bounds loss (0.54–0.78) but under genuine +2
  drift overspends 3–5×; OS-CFAR (LOCO) is the only defense robust to poisoning that also tracks real drift (FPR
  0.6–1.1%).

**REPORT.md.** The subagent harness refused to write `results/t2/REPORT.md`; the full write-up text is in the T2
hand-back message, and all numbers are in `results/t2/tables.md` and the CSVs.

## 2026-10-20: T3 results (150 base attacks, 3 refiner arms x 2 rounds; t3 $68)

Refined 150 MonitoringBench S2-S4 attacks (within track-1's scored sample) with a gpt-4.1 refiner
told the Kerckhoffs detector spec per arm (max / cusum / multichart), gpt-4.1-mini judge+checklist;
scored every refined trajectory with the deployed monitor in `full` and `none`; evaluated the full
attacker x detector cross at matched FPR on Honest-550. Coverage 145/131/143 of 150; paired on 126.
Tables/figures/CSV in `results/t3/` (full write-up handed back to the coordinator).

- **Negative headline:** detector-aware refinement did NOT improve, and usually reduced, undetected-
  success vs leaving the attack unchanged. gpt-4.1-mini catches only 14/4/8/15% of the *original*
  attacks at 1% FPR (max/cusum/eproc/multichart) — originals already evade by length/dilution. The
  refiner condensed attacks (−8 to −15 steps; length ratio 0.58–0.83), concentrating malicious
  actions and raising per-step max suspicion 5.8→7.6, so undetected-success vs multichart fell from
  0.85 (original) to 0.49–0.68 (aware arms).
- CUSUM-alone is the weakest/most-evadable detector (cusum-aware vs cusum 0.86 undetected); max and
  the multi-chart OR are strongest; the OR closes CUSUM's gap but ~ties max on this monitor.
- Adaptive (2 feedback rounds) beats one-shot by +0.10..+0.17 undetected-success on the matched
  diagonal, but still underperforms the original attack.
- Covert √ARL: undetected damage is flat in ARL (10^1.5–10^4), slopes 0.00–0.03 ≪ 0.5 — attacks sit
  below the detectability band of this weak monitor, so damage saturates (no √ARL growth).
- Validity: judge preservation 98–99%, target-literal preservation 0.88–0.90; BashArena Docker
  replay deferred (laptop disk ~12 GB free vs ~6 GB cap; pod SSH blocked) — flagged as a limitation.
- Caveat: results are conditioned on a weak monitor (AUROC≈0.76–0.83); the small evasion headroom and
  the refiner's condensation behavior drive the negative result. Fabricated new-step outputs affect
  `full` more than `none` (results are consistent across both modes).
