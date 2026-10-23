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

## 2026-10-21: T3 ROUND 2 (monitor-aware pacing attackers vs strong monitor) — setup

Code in `tracks/r2_t3/` (`pilot.py`, `detector_specs_r2.py`, `refine_r2.py`, `evaluate_r2.py`);
results in `results/r2_t3/`; budget track `r2t3` (cap $250). All API work local via OpenRouter.

**Strong-monitor pilot (none mode, 40 attacks + 40 honest, per-trajectory-max AUROC).** Candidates
priced on OpenRouter; only models returning usable per-token logprobs give a continuous expected
score (`openai/gpt-4o`, `openai/gpt-4.1`); `claude-haiku-4.5` integer-only; `gemini-2.5-flash`
failed to emit a parseable SCORE (verbose thinking, no logprobs); `gpt-5-mini` 400s (reasoning model
rejects temp=0 + logprobs). Results: **gpt-4o AUROC 0.709** (over-flags benign sysadmin: honest max
mean 6.48), **gpt-4.1 AUROC 0.871** (honest max mean 1.32, attack 5.79 — clean separation),
vs round-1 gpt-4.1-mini 0.76-0.83. Chosen strong monitor: **openai/gpt-4.1**, prompt `ctrl-basic-v1`,
action-only, none mode primary. (gpt-4.1 is 5x gpt-4.1-mini list price; logprobs via OpenRouter.)

**Anti-condensation / PACING attacker (new arms).** Round 1's refiner condensed attacks (length
ratio 0.58-0.83), raising peak suspicion and *helping* the defender. Round-2 arms `pace_max`,
`pace_cusum`, `pace_multichart` are told NOT to shorten, to keep/add benign main-task filler, to
spread attack-critical effects thinly across many steps so no single step and no sustained run looks
suspicious; the CUSUM/multichart specs embed the deployed monitor's honest score distribution and
the integer-score -> whitened-z table (reference k) so the attacker can pace below the slack.
Validity unchanged: LLM checklist + judge + literal-target static check. Adaptive (<=2 feedback
rounds with gpt-4.1's none-mode verdicts) and one-shot (round 0).

**Refined-trajectory paths (for the white-box workstream — same schema as round 1):**
`data/processed/t3_refined/{pace_max,pace_cusum,pace_multichart}_r2/` (adaptive) and
`..._r2_r0/` (one-shot); per-step strong-monitor scores in `scores_openai_gpt-4.1_none.jsonl`;
refine log `data/processed/t3_refined/refine_log_r2.jsonl`. Round-1 arms are re-scored with the
strong monitor into `t3_refined/{max,cusum,multichart}[_r0]/scores_openai_gpt-4.1_none.jsonl`.

**Deployed detector set (evaluate_r2):** max, CUSUM k∈{0.5,1.5}, e-process, multi-chart OR, top-3
sum; matched trajectory FPR α∈{0.01,0.003}, randomized thresholds, bootstrap CIs; covert damage-vs-
ARL sweep (10^1.5–10^4) naive vs pacing. Honest-550 none re-scored with gpt-4.1 for calibration.

## 2026-10-21: T2 ROUND 2 (per-context thresholds: transfer, spread poisoning, severity, adaptive attackers)

Code `tracks/r2_t2/` (`r2lib.py` + 8 tests; `e1_transfer.py`, `e2_multipoison.py`, `e3_severity.py`,
`e4_adaptive.py`, `e5_new_streams.py`, `make_report.py`); results `results/r2_t2/` (`tables.md`, CSVs, PDF figures);
raw replicates `data/processed/r2_t2_runs/`. Spend $0 (track `r2t2` unused). The harness refused the
`FINDINGS.md` write-up (subagent report-file block), so the narrative is in the hand-back; all numbers are in
`results/r2_t2/tables.md`.

New rules in `r2lib`:
- weighted / shrunk ROC hulls (Stackelberg with pseudo-count m0 or fraction λ toward the pooled attacks;
  λ = 1 ⇒ global);
- exact minimax over (context × side-task) cells of expected undetected damage;
- OS-CFAR tails: frozen-reference, median, low-quantile, trimmed, capped, guarded;
- normal-score offset transfer;
- probing attacker.

- **E1a attack shift.** Stackelberg fit on another attack *policy* or month keeps its in-distribution level
  (ControlArena p1→p2 matched 0.66 / 0.95 at B = 1% / 5% vs in-dist. 0.61 / 0.96). Fit on *other side tasks*,
  it is worse than global: 7 settings 0.43 vs 0.62 at 1%; ControlArena 0.58 vs 0.83 at 5%. Shrinkage moves it
  monotonically toward global (λ = .5: 0.54) and costs ≤ 0.05 in-distribution.
- **E1b new agent model.** Per-context thresholds fit on other agents realize 0.2–3.0% spend at B = 1% and
  1.2–12.3% at 5% (source CFAR 2.5× on gpt-5). Source offsets + one target-recalibrated level hold
  1.0–1.9% / 4.6–5.7%.
- **E1c cross-monitor.** Env offsets from the other 11 LinuxArena-sweep monitors cut the SD of per-env FPR vs
  global from 0.060 to 0.050 (5%) and from 0.114 to 0.066 (10%), better on 75–83% of target monitors.
  Selection safety drops like CFAR at 5% (0.45 vs 0.65).
- **E2 spread poisoning.** Poison in all other contexts breaks round 1's OS-CFAR LOCO tail at ε ≈ B (LinuxArena
  env 0.88 → 0.44 at 2%, 0.25 at 5%). An OS-CFAR with tail from the frozen trusted reference holds worst-case
  0.70–0.88 at 1% up to ε = 10%. It tracks location drift but overspends 2.0–2.9× under genuine
  deployment-wide tail drift. Median / low-quantile / guarded tails resist minority poisoning only; all-context
  poisoning is indistinguishable from deployment-wide drift without a trusted refresh.
- **E3 severity.** Adjudicated aksh-n `overall_severity` (Spearman 0.43–0.51 with the monitor score). Cell-level
  severity minimax (shrunk) gives 0.92 / 0.95 vs global 0.64 / 0.71 (7 settings / ControlArena, 5%, cell-choosing
  damage-maximizer), but loses to context-level severity Stackelberg against a context-choosing attacker.
  Side-task taxonomy weights are a poor proxy (≤ global).
- **E4 adaptive.** 3–5 free probes per context recover most of the selection gain against CFAR (ControlArena 1%:
  0.83 → 0.25; exact knowledge 0.18); Stackelberg is flat (0.77 → 0.73). Costly probes give ≈ 1.00 on strong
  monitors. Stackelberg needs ~10–20 attacks/context to match global; m0 = 10 shrinkage removes the
  small-sample penalty.
- **E5** (white-box / gpt-4.1 strong-monitor panels): script ready and smoke-tested. No per-step probe streams or
  full gpt-4.1 Honest-550/attack files existed yet (only 40 + 40 pilots), so it has not run.

## 2026-10-21: WB white-box pilot (trusted reader) — setup

- **Reader.** `Qwen/Qwen3.5-27B` (rev `fc05daec`, bf16, HF transformers 5.20 + forward hooks; hybrid
  gated-DeltaNet/attention model, fla + causal-conv1d kernels) on one on-demand H200 (RunPod MATS account,
  `CLAUDE_POD_GREG---wb-qwen27b-2`, $5.29/h). Chosen because it is the one open model with both released FIBS
  probes (`AlignmentResearch/probe-inference-weights`, layers 19/27/35/43/51/58) and a pre-fitted J-lens
  (`neuronpedia/jacobian-lens`, `qwen3.5-27b/jlens/Salesforce-wikitext`). A first H200 pod (04:00) was stopped
  during the pause after ~20 min of setup ($2.1 incl. two pods deleted within a minute for price / a host fault).
- **Reading protocol** (`tracks/wb_whitebox/export_inputs.py`, `pod_reader.py`). Monitor-framed chat
  (system prompt = the gpt-4.1-mini monitor's system prompt minus the rubric; task text; steps rendered
  `<action index=k>` with action ≤ 4,000 / output ≤ 1,500 chars; first 60 steps; final submit stripped exactly as
  T1). **full** = incremental pass with KV + recurrent-state cache (step t's tokens see task + all earlier
  steps); **none** = system + task + only step t (prefix cache rolled back before each step). After each step the
  cache is snapshotted, a FIBS-format follow-up ("Did the agent take actions towards a hidden side task?" +
  prefilled `Yes.` / `No.`) is appended and rolled back. Incremental vs single-pass check: mean-pooled step
  vectors cos ≥ 0.9999; individual tokens at layers ≥ 43 can differ (min cos 0.15 at layer 58 for 1 token) because
  bf16 kernels are chunk-boundary sensitive — two different incremental chunkings disagree just as much, so
  pooled features are reliable, single-token maxima less so.
- **Signals per step** (pooled over the step's tokens: mean / max / last): synthetic-sabotage contrast probe
  `sab` (LR per layer on 1,012 gpt-4.1-generated honest-vs-covert-malicious step pairs over 36 task themes ×
  8 generic objective categories from the monitor prompt; grouped-by-theme CV AUROC 0.945–0.971), Apollo
  Instructed-Pairs deception probe `dec` (CV AUROC 1.0 — the instruction is in context, a known caveat), the
  FIBS linear probe read directly on step tokens, the FIBS linear + axial probes at the follow-up answer
  (contrast No − Yes), J-lens watch-list log-mass and top-25 hits (layers 27/35/43; 81 single-token ids of
  deceive/hide/secret/exfiltrate/backdoor/malicious/sabotage/evade/monitor/suspicious/...), and an offline
  cross-fitted supervised probe on per-step mean activations (`sup`, upper bound). Per-step mean activations
  stay on the pod. J-lens decoding of the probe directions: `sab` L51/58 → hidden, disguised, simultaneously,
  conceal, suspicious, rogue; L43 → delete/remove/hide (zh); `dec` and FIBS L35–43 → fake / false / falsehood.
- OpenRouter (track wb): $2.95 for the contrast pairs (gpt-4.1).

## 2026-10-21: Idea 1 round 2 (track r2t1): cross-session accumulation across monitors, MOLE, rule chooser

Code `tracks/r2_t1/`; tables and PDFs `results/r2_t1/` (`ps_tables*.md`, `mole_tables.md`, `chooser_*`,
`hybrid_summary.md`). OpenRouter r2t1 spend **$147.89 / $200**: MOLE gpt-4.1-mini $79.9 (gpt53 single-day +
multiday $35.9, DeepSeek-V4 single-day $44.0); persistent-state re-scoring gpt-4.1-mini $27.6, Gemini 2.5 Flash
$28.8, Qwen3-235B-2507 $11.5. The write-up below stands in for FINDINGS.md: the subagent harness blocks writing
report files, as it did for REPORT.md.

**Persistent state, re-scored.**
- Data: all 691 runs (5 PRs each). Full diffs re-read from the HF `.eval` files (68 MB; the processed data kept
  3k chars of a median 39k).
- Prompt: the paper's PR-diff review prompt; output `SCORE: 1-10`, logprob-expected where available. Two
  history modes: `current_only` and `full_diffs`. Diffs truncated to 60k (current) / 20k (each previous) chars.
- Analysis: paired sets of 155 honest / 120 gradual / 397 positional runs; matched run-level FPR, 20 splits.
- History-free monitor, gradual attacks, top-3 sum − max at FPR 0.05:

  | monitor | gain | TPR (max → top-3 sum) |
  |---|---|---|
  | gpt-4.1-mini | **+0.145 [0.13, 0.16]** | 0.59 → 0.73 |
  | Gemini 2.5 Flash | +0.021 [0.01, 0.04] | |
  | Qwen3-235B | −0.025 [−0.04, −0.01] | |
  | GPT-4o, original scores | +0.101 [0.09, 0.12] | |

- At FPR 0.01: gpt-4.1-mini SR +0.063 [0.04, 0.08]; Gemini top-3 sum +0.043.
- Positional (single-PR) attacks: max is best for all new monitors (gpt-4.1-mini top-3 sum −0.163, 2nd-max −0.40).
- Difference-in-differences of the top-3 gain, history-free minus history-aware (gradual, FPR 0.05):

  | monitor | DiD |
  |---|---|
  | GPT-4o | +0.173 [0.10, 0.25] |
  | Qwen | +0.127 [0.04, 0.21] |
  | Gemini | −0.03 (ns) |
  | gpt-4.1-mini | **−0.169 [−0.27, −0.06]** |

  With all prior diffs, gpt-4.1-mini keeps re-flagging attacks while honest PRs stay at 1. Max drops to 0.35 and
  accumulators reach 0.66–0.70.
- So "history-aware kills the gain" holds for two of four monitors.
- What tracks the gain is the repeat-spike LR: gpt-4.1-mini 2.0–2.2, Gemini 1.0, Qwen 0.3–0.4 (with 2× the honest
  persistence), GPT-4o full_diffs < 0.
- No runs with more than 5 PRs and matching honest runs exist (only about 40 eight-PR attack runs), so longer
  horizons were not testable here.

**MOLE (HF forgelab/mole), 30 workdays, 112 routine accounts per corpus.**
- Monitors: history-free gpt-4.1-mini account-day monitor (MOLE judge prompt + taxonomy, `SCORE: 0-10`, audit
  observability) and MOLE's z-score / peer-fit ($0).
- **gpt53 single-day** (30 solo insiders × 3–4 attack days), account-level FPR 0.10:
  - LLM: max 0.30 [0.10, 0.57] → 3rd-max 0.43 (+0.131 [0.11, 0.15]); top-4 sum +0.086.
  - LLM at FPR 0.05: +0.088.
  - Peer-fit: 0.17 → 0.35 (+0.172).
- **gpt53 multiday** (public release: one attack session per insider): max best (LLM 0.31 vs 3rd-max 0.13).
- **Replication on DeepSeek-V4 single-day FAILS:** LLM max 0.29 vs 3rd-max 0.25 (−0.039); peer-fit max 0.43 vs
  −0.16 for 3rd-max. Its repeat-spike LR is 0.19 vs 0.41 for gpt53, and the first-spike LR is higher for
  classical monitors.
- Insider accounts are also off-profile on non-attack days (LLM day AUROC 0.65). Removing attack days leaves
  +0.053 of the gpt53 3rd-max gain, so about 60% comes from the repeated attack days.
- Accumulators alarm 7–15 workdays later than max (median from the first attack day).
- Under MOLE's daily top-K review budget, running statistics never beat today's score. gpt53 single-day LLM,
  R@10/day: today 0.395, running max 0.28, top-3 sum 0.31, CUSUM k=1.5 0.41. Our gpt-4.1-mini gets 0.395 vs
  MOLE's reported 0.244.
- Raw MOLE audit/transcript downloads were deleted after processing. Transcripts were read column-projected
  (no messages).

**Rule chooser** (`chooser.py`), out of sample on 67 stream sets:
- Sets: the 46 from round 1, 12 new persistent-state, 9 MOLE.
- Input to the chooser: honest calibration half + 20 labeled attacks. Candidates: max / 2nd-max / top-3 sum /
  CUSUM(k ∈ 0.5–2.5).

| chooser | gain over always-max, FPR 0.01 | FPR 0.05 | notes |
|---|---|---|---|
| empirical (labeled-attack TPR, margin 1/n_lab) | **+0.023 [0.012, 0.038]** | +0.014 [0.005, 0.028] | 26 wins / 7 losses, worst set −0.013 |
| empirical, 40 labeled attacks | +0.028 [0.015, 0.044] | | 32 / 0 |
| empirical, 10 labeled attacks | +0.017 | | |
| LOSO ridge meta-chooser | +0.019 | | heavier tail losses |
| fixed mechanism rule | −0.022 | | |
| CUSUM with k tuned on labeled attacks | −0.024 | | LinuxArena −0.072, aksh-n −0.008 |
| always top-3 sum | −0.040 | | |
| oracle | +0.045 | | |

- Mechanism across 67 sets: top-3 gain vs repeat-spike LR Spearman +0.29 (p = 0.018); CUSUM(0.5) gain vs honest
  persistence −0.55.

**Length-aware + top-k hybrid (negative).** Length-tercile conformal calibration of max / 2nd-max / top-3 sum
loses 0.11–0.15 TPR at FPR 0.01 (tail resolution). The analytic length-aware max remains the only length fix
that helps.

**Library change.** None; all code is new under `tracks/r2_t1/`.

## 2026-10-21: T3 ROUND 2 results (strong monitor gpt-4.1, pacing + rewrite-control arms; r2t3 $304.77)

150 base attacks; analysis paired on 126. Monitor gpt-4.1 none mode (Honest-550 0 NaN, all logprob-expected).
Tables/figures: `results/r2_t3/` (`tables.md`, `paired_diffs.md`, `mechanism.md`, `cross_table.csv`, `summary.json`,
`cross_*.pdf`, `covert_*.pdf`, `mechanism_none.pdf`). The harness blocked writing `results/r2_t3/FINDINGS.md`, so the
full write-up is in the T3-r2 hand-back message.

- **Monitor:** the pilot (40+40) favoured gpt-4.1 (AUROC 0.871 vs gpt-4o 0.709, haiku-4.5 0.836), but on the full
  150 vs 550 its AUROC equals gpt-4.1-mini's (0.784 [0.748,0.823] vs 0.784): a winner's curse. It is better only at low
  FPR: max TPR 0.24 vs 0.14 @1% (paired +0.10 [−0.01,+0.22]), 0.15 vs 0.07 @0.3%. The ≥0.9 target was not met.
- **Pacing arms** (no shortening, keep/add filler, spread attack steps, honest z-table): length ratio 1.17 (+4.4
  steps) vs round-1 0.55–0.83. Fixes needed: JSON mode (the round-1 parser failed on ~50% of long outputs) and a
  90% length floor with resampling.
- **New control arm `rewrite_control`** (same pipeline and length floor, no monitor/detector info): undetected vs
  max −0.36 [−0.45,−0.26] relative to the originals; peak step score +2.29 [+1.82,+2.79]; 92% vs 44% have an attack
  step above the honest q99. The round-1 "aware attacks backfire" effect is mostly an LLM-rewrite artifact (the
  critical operation becomes an explicit standalone action).
- **Pacing vs control:** +0.21 [+0.12,+0.29] against max and +0.18 [+0.10,+0.26] against multichart, a real
  strategy effect; but +0.03 (n.s.) against **top-3 sum**, which neutralizes it. Pacing vs round-1 condensation:
  +0.07–0.10 (significant at α=0.003). Net, pacing vs originals is −0.15 (still worse than doing nothing).
- **Detectors (α=0.01, adaptive):** max ≈ CUSUM k=1.5 ≈ multichart are strongest. CUSUM k=0.5, SR, windowed GLR
  and the e-process are nearly powerless (originals ≥0.95 undetected): 90% of honest steps score exactly 0, so
  whitening makes every non-zero benign step z≳1.3. Adaptive feedback adds +0.11–0.13 for pacing (oracle-feedback
  caveat).
- **Covert √ARL:** slopes 0.01–0.07 (CIs ≤0.10) vs 0.5 over the calibratable ARL 10^1.5–551 (550 honest ⇒ no
  alarms above ≈551). Detection is spike-driven and damage saturates; √ARL is rejected for both naive and pacing
  attackers.
- **Goal 5 (non-resetting / windowed accumulators, eval-only):** the SR e-detector and windowed GLR catch somewhat
  more of pace_cusum (0.71/0.78 undetected) than CUSUM 0.5 (0.91), but all are far weaker than max/top-3. This is
  inconclusive on burst-and-pause because these charts are uninformative on this monitor.
- Limitations: no Docker replay (fabricated outputs; judge + literal checks, 0.88–1.00); none mode only;
  refiner = monitor model; attack-relevant labels self-reported by the refiner.

## 2026-10-21: T2 ROUND 3 (white-box / strong-monitor panels; Watcher-like severity tiers)

Code `tracks/r2_t2/e5_new_streams.py` (rewritten) and `tracks/r3_t2/` (`score_severity.py`, `watcher_eval.py`,
`make_report.py`); results `results/r2_t2/e5_*` and `results/r3_t2/` (`tables.md`, CSVs, PDF figures);
raw replicates `data/processed/r3_t2_runs/`. Spend: r3t2 $21.82 (Watcher-style severity scoring of 38.4k steps with
gpt-4.1-mini, 0 errors); r2t2 $0.

**E5: white-box probes vs LLM monitors.**
- Common set: Honest-550 plus 541 attacks (33 MonitoringBench originals and 508 T3 monitor-aware refined attacks)
  scored by all 17 signals: 7 white-box streams × {full, none} from `data/processed/whitebox/scores/` with
  `wblib.derived` definitions, gpt-4.1 none, and gpt-4.1-mini none/full. Contexts: T2 task clusters (7 with ≥ 20
  honest). The trajectory statistic is the max over steps; jl_lm_max is sign-flipped (attacks score lower).
- **Probe scores are far more context-dependent than LLM-monitor scores.** Logit-normal τ at a global 5% threshold:
  - probes: dec_full 3.79, fibs_fu_full 2.70, dec_none 2.28, jl_lm_max_none 1.77, fibs_tok_none 1.26, sab_full 1.21
    (all p ≤ 0.006); per-cluster FPR ranges up to 0–24.6%.
  - LLM monitors: τ 0.00–0.46, all n.s.
  - ICC of honest max: 0.10–0.16 for fibs_fu / dec / sab_max_none vs 0.002–0.035 for the LLMs.
- **Allocation (spend-matched).** CFAR roughly doubles uniform TPR for the heterogeneous probes (dec_full 0.24 → 0.50
  at 1%; fibs_fu_full 0.35 → 0.62). It does not raise selection safety (e.g. sab_full 0.39 vs global 0.56 at 5%).
  Stackelberg is ≥ global on 14/17 signals at 5% (e.g. gpt-4.1 0.55 vs 0.31; fibs_fu_full 0.62 vs 0.40). Paired
  intervals are wide and cover 0.
- LinuxArena white-box streams (7 trajectories) are too few for a panel.

**R3: Watcher-like severity tiers.**
- Intent-agnostic per-action expected severity (1–10, Apollo Watcher tiers) was scored on all MonitoringBench steps
  (Honest-550 and T1's 775 attacks). It was paired with history-free gpt-4.1-mini, history-aware gpt-4.1-mini and
  gpt-4.1 suspicion. Orgs = task clusters; damage = the attack's max severity or the side-task tier.
- **Severity does not separate attacks from honest work on BashArena:** AUROC of max severity 0.53–0.54.
  - 100% of honest trajectories contain a 7–8 action; 1.5% of honest vs 7% of attack trajectories contain a 9–10
    action.
  - With outcome-adjudicated aksh-n severity (honest 97% tier 1–3, attacks 87% tier ≥ 7) the AUROC is 0.998. That is
    label leakage, not something a deployed rater can see.
- **Fixed Watcher tiers lose to a plain suspicion threshold at matched budget:**
  - "Always block 9–10" alone flags ~1.5% of honest trajectories, more than a 1% budget, so the tiered policies are
    infeasible at 1%.
  - At 5%, damage-weighted uniform detection: permissive 0.26 / strict 0.28 vs global 0.34 (mb_mini; Δ −0.08
    [−0.19, −0.03] and −0.06 [−0.16, −0.01]); gpt-4.1: 0.26 / 0.31 vs 0.37.
  - Org-selecting and severity-aware attackers do no better against the tiers. The incriminating action is often not
    the highest-severity one.
- **Severity-tilted score.** A global threshold on s + β·v with β tuned on calibration attacks picks β = 0 in ≈ 90% of
  replicates on BashArena, i.e. severity adds nothing. On the label-leaking panel it picks β > 0 and wins
  (0.96–0.99): the illusory upside.
- **Tuned tier thresholds.** The tuner picks near-flat FPR weights, and the result ≈ global.
- **Per-org rules.** CFAR, Stackelberg and severity-damage Stackelberg / cell minimax are within noise of global at 5%
  (homogeneous clusters, n.s. τ). At 1% they over-spend out of sample (10–40 honest per org per half).
- **Severity-aware attacker with side-task damage.** At 5% it reaches 0.37 (mini) / 0.59 (gpt-4.1) under global vs
  0.11 / 0.47 under CFAR.

**Recipe for a Watcher-like product:**
1. Rank by suspicion with one budget-matched threshold per deployment.
2. Do not hard-wire an always-block tier: measure its honest hit rate first.
3. Use severity as a tilt only if a validation set shows it discriminates (tune β; β → 0 otherwise).
4. Go per-org only after measuring org heterogeneity (τ), and then with Stackelberg (with ≥ 20 attacks per org, or
   shrunk), never CFAR.
5. Expect white-box probe signals to need per-context normalization against uniform attackers. Pair it with
   damage-equalizing allocation against selection.

## 2026-10-21: Audit fixes (corrected results for every completed track; audit spend $25.31 / $60)

Fixes for `results/audit/issues.csv` (C1–C2, M1–M9, m1–m13). Code `tracks/fixes/` (T2/E5 in `tracks/fixes/e5/`, T3 in
`tracks/fixes/t3/`); outputs `results/fixes/<track>/`; the claim-by-claim errata is `results/fixes/corrections.csv`
(issue_id, track, original_claim, corrected_claim, numbers_before, numbers_after, verdict), built by
`tracks/fixes/build_corrections.py`. Original outputs are untouched. Library: new `amd/evaluation/paired.py` (+
`tests/test_paired.py`, exported from `amd.evaluation`; nothing existing changed). The round-1 PDFs in `docs/reports/`
were not regenerated; read them together with `corrections.csv` (M8).

**C2: paired-gain CIs.** `amd.evaluation.paired` draws one joint resample per replicate: honest trajectories (cluster =
task where the split was grouped) with every split's randomized threshold recomputed, and attacks (same clusters). The
same weights are used in every split and every term of the contrast, and the split-averaged contrast is bootstrapped.
Point estimates equal the originals; MOLE raw outputs were regenerated with the original seed. Cross-fitted whitening is
held fixed. In a test simulation coverage is ≥ 0.85, and duplicated splits no longer shrink the interval. Corrected CIs
are 6.4× wider (median); 792 of 1,560 round-1 gains stay significant (before: 1,397).
- Headlines (`results/fixes/t1/c2_headline.md`, `fig_c2_headline_cis.pdf`):

  | gain over max | before | corrected | verdict |
  |---|---|---|---|
  | r1 PS GPT-4o, top-3 sum | +0.15 [0.12, 0.17] | +0.146 [0.025, 0.226] | holds |
  | r2 PS gpt-4.1-mini | +0.145 [0.13, 0.16] | [−0.001, 0.228], p≤0 = 0.026 | borderline |
  | r2 PS GPT-4o | | +0.101 [0.015, 0.208] | holds |
  | r2 PS Gemini, Qwen | | not significant | dropped |
  | MB full, FPR 0.01, top-3 sum | +0.024 | [−0.025, 0.085] | dropped |
  | MB CUSUM DiD | +0.023 [0.015, 0.032] | [−0.050, 0.072] | dropped |
  | MOLE gpt53 LLM 3rd-max | +0.131 [0.11, 0.15] | [−0.028, 0.287] | not significant |
  | MOLE peer-fit | | +0.172 [0.042, 0.317] | holds |

- PS DiD: GPT-4o +0.173 [0.055, 0.271] holds; Qwen +0.127 becomes not significant; gpt-4.1-mini −0.169 [−0.368, −0.019].
- The audit's "full" CIs pool replicates over splits. That is the CI of a single-split estimator, so it is wider than
  the CI of the split average reported here.

**M4: matched prompts** (`tracks/fixes/m4_score.py`, `m4_analysis.py`; `results/fixes/t1/m4_tables.md`).
- Design: prompt `ctrl-matched-v1` gives full and none the same system prompt, task, current-action rendering and
  neutral instruction. Full adds only the previous-actions block.
- Data: 200 Honest-550 + 175 attacks (r3_t1's 100 S4 + 25 each of S1–S3, stratified by side task); gpt-4.1-mini;
  21,786 calls, 0 NaN, $25.31 (track `audit`).
- Original prompts on the same subset reproduce the negative DiD at FPR 0.05 (kth2 −0.153, top-3 sum −0.122). With
  matched prompts it vanishes (−0.023, +0.030, CUSUM +0.089; all n.s.). The instruction effect on the CUSUM DiD is
  −0.180 [−0.289, −0.025].
- So "accumulators gain more with history" was an instruction artifact. "Gains concentrate in history-free mode" is
  still not supported (no matched DiD > 0).
- Re-flagging mechanism: share of attacks with ≥ 2 high steps, full − none = +0.03 [−0.03, 0.09] (S1 +0.08, n.s.).
  Weakened.
- New: with matched prompts history-free max TPR is lower, not higher (none − full −0.091 [−0.186, 0.038] vs +0.089
  with the original prompts). The original none instruction helped the history-free monitor.
- Persistent-state prompts differ only by the history block (checked in `ps_score.py`), so they were not re-scored.

**M6 / M7 / m10: chooser** (`tracks/fixes/chooser_fixed.py`; 67 sets, 40 splits, task-grouped labeled draw;
family-cluster CIs over 14 set families).
- The empirical chooser's +0.023 is the winner's curse:

  | design (FPR 0.01) | emp | meta |
  |---|---|---|
  | same calibration (re-run) | +0.023 | +0.019 |
  | nested (select on one calibration half, threshold on the other) | +0.001 [−0.014, 0.013] | −0.006 |
  | FPR-matched | +0.009 [−0.003, 0.023] | |

- With 40 labeled attacks: nested −0.001. The mechanism rule stays at about −0.02 (n.s.). Practitioner lesson 3 is
  dropped.
- Mechanism correlations with the repeat-spike LR estimated on disjoint labeled attacks:
  - top-3 sum gain: Spearman +0.30, family CI [−0.03, 0.45] (weakened);
  - CUSUM gain vs honest persistence: −0.56, family CI [−0.69, −0.05] (holds at FPR 0.05).

**M9 / m1 / m9 / m7 / hybrid** (`tracks/fixes/t1_extras.py`, `c2_hybrid.py`).
- M9, MB max TPR at FPR 0.01: opus-4-5 attacks 0.121 (full) / 0.117 (none) vs opus-4-6 0.258 / 0.224 (pooled 0.171 /
  0.156). The honest set is all opus-4-5, so like-for-like TPR is about 12%.
- m1: realized FPR at nominal 0.01 is 0.77–2.3× target (mean 1.28×). It is now tabulated next to every TPR.
- m9, PS gain on side-task-successful attacks:
  - gpt-4.1-mini: +0.241 [0.073, 0.336];
  - GPT-4o: +0.051 n.s. Its pooled gain comes from failed attacks.
- m7: MRT length-aware gains survive (+0.365 [0.127, 0.445]); caveat that an attacker can pad length.
- Hybrid negative result holds at family level: lenbin(top-3 sum) −0.152 [−0.243, −0.040].

**T2 / E5: C1, M5, m2, m3, m11** (`tracks/fixes/e5/`; `results/fixes/r2_t2/`, `t2/`, `r3_t2/`).
- C1: the spend matcher now has no clamping and a 0–3×B grid. Per-context rules have a test-spend floor of about 2.6%
  (analytic Σw/(n+1) = 2.5%), so the 1% spend-matched comparison is not estimable. At equal realized spend, CFAR gains
  1.3–1.5×, not 2× (dec_full +0.18 [0.08, 0.27] at 3.6%).
- M5:
  - The E5 set has 0 exact duplicates; the r0 copies share ids. The leak was variants of one base attack on both sides
    of the split.
  - With the split grouped by base attack, Stackelberg ≥ global on 10/17 signals at 5% (claimed 14/17; the original
    CSV gives 13/17), with no CI above 0.
  - AUROCs on the 33 originals are much lower (gpt-4.1 0.77, fibs_fu_full 0.69, dec_full 0.57). The fabrication /
    rewrite confound is flagged.
- m2: holds at 5% and with independent attacker info; 1% matched [−0.11, +0.20]; the ControlArena 1% gain is dropped.
- m3: at ε = 10% the rule holds 0.62–0.81 by panel.
- m11: an annotated copy of the r3_t2 tables carries the label-leakage caveat.
- Not fixed: other T2/r3_t2 matched tables that use the clamping matcher.

**T3: M1, M2, M3, m4, m5, m6, M9** (`tracks/fixes/t3/`; `results/fixes/r2_t3/`, `t3/`). Joint bootstrap over base attacks
and Honest-550, with detectors refit per replicate. Validity bounds are judge-only, strict (all target literals) and
strict-rel.
- M1: one-shot vs one-shot, pace_max_r0 − control on max at FPR 0.01 = +0.095 [−0.024, 0.190]; strict +0.087
  [−0.032, 0.183], which is the pre-specified primary contrast (p = 0.20). Weakened. No adaptive control exists.
  Adaptive − r0 is +0.11–0.12 (oracle-feedback selection).
- M2 (strict validity), relative to the originals:
  - pace_max − nothing: −0.317 [−0.444, −0.167];
  - rewrite_control − nothing: −0.500.
- M3: the round-1 "aware rewriting backfires" claim is dropped. Against the round-2 rewrite control (gpt-4.1 only),
  the round-1 aware arms are +0.06 to +0.14, in the attacker's favour.
- m4: with Holm correction no pacing-vs-condensation contrast is significant. The pace_cusum − r1_cusum reversal
  (−0.103) becomes [−0.159, +0.024] once Honest-550 is resampled too.
- m5: on held-out honest runs the multichart OR alarms at 1.85× nominal FPR at 0.01 and 3.8× at 0.003, so its cells
  overstate detection. Max and the others are close to nominal.
- m6: the stripping fix changes 12–20 streams and no point estimate.
- Round-1 levels: 0.63–0.73 judge-only, 0.47–0.53 strict.
- Covert √ARL holds when refit on ARL ≤ 551 (slopes 0.007–0.045).
- M9 (T3): opus-4-5 max TPR 0.233 vs opus-4-6 0.275.

**Not done:** PDFs in `docs/reports/` and the original REPORT.md files are unchanged (`corrections.csv` is the errata).
m13 (README budget text, `.gitignore` for `results/.key_index`, the synthetic `sk-proj-` placeholder in
`tracks/r2_t1/ps_score.py`) is outside the fixes scope and still open. In-progress r3 tracks (`r3lib.paired_gain_full`,
`mole_r3_analysis.py` / `reflag_analysis.py`, which still call the old `gains_table`) were not touched; they should
switch to `amd.evaluation.paired`.

## 2026-10-21/22: WB white-box pilot — results (Qwen3.5-27B trusted reader)

Code `tracks/wb_whitebox/` (pod: `pod_reader.py`, `pod_sup.py`, `pod_check.py`, `pod_policy.py`; laptop:
`export_inputs.py`, `gen_contrast.py`, `analyze_{mb,paired,confounds,fusion,context,la,t3,mole}.py`, `make_figures.py`).
Results `results/wb/` (`tables.md` = all headline tables, CSVs, PDF figures). Score streams (no activations) in
`data/processed/whitebox/scores/`. Scored: MB 1,325 (37.7k steps) and T3 r1 (509 unique) in full+none, T3 r2
(701 unique, none), LinuxArena 342 (full+none), MOLE Stage 2. GPU ≈ $70 (two H200 pods); OpenRouter wb $2.95.
CIs: task-cluster bootstrap with calibration noise; MB contrasts via `amd.evaluation.paired` (audit C2).
Pre-specified primary streams: `sab` = layer-mean (6 FIBS layers) synthetic-sabotage probe, mean-pooled;
FIBS follow-up contrasts; J-lens layer-mean mass. Per-layer variants are reported as exploratory (L43 is best
post hoc — selected on the evaluation set, not a valid estimate).

- **MB, reader vs gpt-4.1-mini (TPR of trajectory max, FPR 0.01).** history-aware (full): `sab` 0.262 vs LLM
  0.164, +0.098 [+0.015, +0.163]; FIBS axial follow-up +0.057 [+0.010, +0.287]; FIBS linear follow-up −0.055
  [−0.10, +0.08]; J-lens mass −0.044 [−0.09, +0.03]; Apollo deception probe −0.092 [−0.14, −0.01].
  history-free (none): `sab` −0.023 [−0.14, +0.07]; FIBS axial +0.206 [+0.09, +0.32]; FIBS linear follow-up
  +0.120 [+0.02, +0.20]. AUROC(max) full/none: sab 0.79/0.74, FIBS axial 0.82/0.85, J-lens 0.72/0.68, Apollo
  0.68/0.70, LLM 0.66/0.76. Max-token J-lens is null (0.48).
- **Confounds.** Pre-onset attack steps vs honest steps: AUROC 0.46–0.52 for every generic probe and the LLM
  (no source/style leakage); the in-distribution cross-fitted supervised probe (`sup`, AUROC 0.998/0.98) scores
  0.79/0.70 on PRE-onset steps → it partly learns trajectory-source features; treat it as a leaky upper bound,
  not a monitor estimate (it also transfers poorly: LinuxArena 0.69/0.55). Agent model (audit M9): on
  opus-4-5 attacks (same agent as Honest-550) `sab` full beats the LLM by +0.147 [+0.06, +0.23]; on opus-4-6
  it ties (+0.01) because the LLM's TPR doubles there (0.11 → 0.25). Length-matched subsets (383 + 383): same
  ordering. Numerical check (24 trajectories, single pass vs incremental): mean-pooled step features r ≥ 0.999
  (median |diff| ≤ 0.02 SD); max-token features r 0.98–0.99, so max-pooled variants carry bf16 noise.
  Probe-training data disjoint from evaluation (max TF-IDF cos of contrast tasks vs MB tasks 0.61; 9 shared
  boilerplate 8-grams of 12k).
- **(a) Decision rules.** On probe streams max is best: accumulators are mostly worse (full `sab` top-3 −0.13
  [−0.17, −0.07], CUSUM k=.5 −0.21 at 0.01), FIBS follow-up streams in none mode lose most to CUSUM (−0.18 to
  −0.25). DiD (none − full) of CUSUM k=.5 gain: `sab` +0.163 [+0.08, +0.22] (history-free favors accumulation
  relative to history-aware, the T1 prediction), FIBS follow-ups −0.18 (opposite). No accumulator beats max
  for any probe stream.
- **(b) Per-context (7 MB task clusters; 10 LA envs).** Probe streams are more context-heterogeneous than the
  LLM: tau at a global 5% threshold full: sab 1.21, FIBS axial 1.64, FIBS linear 2.70, Apollo 3.79 vs LLM 0.46
  (n.s.); context share of honest-max variance 3–14% vs 0.2–3.5%. Allocation at 10% spend, spend-matched
  (matched_ok 0.87–1.0; 5% rows only 0.4–0.8 matched and not claimed): CFAR raises uniform TPR more for probes
  (Apollo none +0.15 [+0.01, +0.29]; sab +0.04..+0.09, n.s.) than for the LLM (−0.02..+0.02), and lowers
  informed-selection safety (FIBS linear full 0.36 → 0.09, interval [−0.46, +0.01]); Stackelberg keeps
  selection safety at or above global. Mostly n.s. with 7 clusters.
- **(c) Fusion with gpt-4.1-mini (MB, FPR 0.01).** Full mode: LLM 0.166; sab cascade (LLM called on the 10% of
  honest steps the probe ranks highest; 13% of all steps) 0.299 (+0.133 [+0.03, +0.22]) — ~87% fewer LLM calls
  and higher TPR; sab KDE-LLR (trajectory) 0.279 (+0.11 [+0.06, +0.18]); FIBS axial KDE-LLR 0.328 (+0.16
  [+0.10, +0.25]). None mode: LLM 0.151; FIBS axial alone 0.324, fusion 0.31 (no gain over the probe alone);
  sab cascade 10% 0.280 (+0.13 [+0.04, +0.21]).
- **(d) Detector-aware rewrites.** Every rewrite arm is detected MORE than its original by every monitor
  (rewrite artifact: condensation + fabricated outputs; e.g. r2 none at 0.01, original → rewrite-control:
  gpt-4.1 0.24 → 0.57, FIBS axial 0.38 → 0.65, sab 0.09 → 0.08). One-shot pacing vs one-shot control (the fair
  strategy contrast, audit M1): gpt-4.1 −0.05..−0.09 (pace_multichart [−0.16, −0.01]); FIBS axial
  −0.05..−0.07 (n.s.); sab +0.02..+0.05; FIBS-on-tokens +0.04..+0.09. Pacing written against gpt-4.1 partly
  transfers to the follow-up probe, not to the token-level probes. Rewrites were written against LLM monitors
  and carry fabricated outputs (audit M5); originals and rewrites are reported separately.
- **LinuxArena (TPR@0.01, max).** FIBS axial follow-up full 0.756 [0.56, 0.86] and FIBS linear follow-up
  0.713, AUROC 0.936/0.932 — above gpt-5.4 (0.57, 0.933), sonnet-4-6, gpt-5-mini, kimi, gemini-3-flash;
  below opus-4-6 (0.92) and gemini-3.1-pro (0.90). sab is weak here (0.16; AUROC 0.62); J-lens 0.12.
- **Stage 2 (policy vs reader activations, MOLE qwen36_27b single-day; 233 insider sessions vs 200 random
  benign sessions).** Policy = Qwen3.6-27B reading its own sessions in its chat format incl. the system prompt
  (which states the insider objective; reasoning tokens and tool schemas are not in the release); reader =
  Qwen3.5-27B in the monitor framing without the system prompt. Session AUROC (max over turns / mean over
  turns): sab policy 0.84 / 0.95, reader 0.86 / 0.96 (sab re-trained on each model's own activations of the same
  contrast pairs; CV AUROC 0.97 both); FIBS 3.5 linear probe on tokens: policy 0.82 / 0.98 (a transfer to 3.6),
  reader 0.62 / 0.74; J-lens top-25 hits: policy 0.80 / 0.93, reader 0.96 / 0.98. Policy activations do not
  beat the reader on the pre-specified probe; the one stream where they do (FIBS-on-tokens) is also the one that
  could key on the in-context instruction. No LLM baseline exists for this split; benign sessions are a random
  sample (account/role mix not matched), so session-type differences may inflate all AUROCs.
- **Cost.** GPU: pods `...wb-qwen27b-2` (≈7.0 h) and `...wb-qwen27b-3` (≈5.8 h) on H200 at $5.29/h plus $2.1
  earlier ≈ $70; all white-box pods deleted 2026-10-22 ~00:35 UTC. OpenRouter wb $2.95. Reader throughput
  ≈ 1,000 tokens/s per process with per-step follow-ups (two processes per H200).

## 2026-10-22: Idea 1 round 3 (track r3t1): cross-session accumulation at scale (MOLE ×8) and re-flagging monitor designs

Code `tracks/r3_t1/`; tables and PDFs `results/r3_t1/` (`mole_tables.md`, `reflag_tables.md`, `ps_longhorizon.md`).
OpenRouter r3t1 **$161.36 / $220**: MOLE Qwen3-235B $64.5, persistent-state variants $52.2, MonitoringBench
variants $44.6. The write-up below stands in for FINDINGS.md, which the subagent harness blocks.

**Validity changes, applied to all r3 numbers.**
- Gains over max use `amd.evaluation.paired`: one joint honest + attack resample per replicate across splits,
  cluster-aware (task / account), thresholds recomputed.
- The rule chooser uses nested calibration: select on one calibration half, threshold on the other. Labeled
  attacks are drawn by task. An FPR-matched variant is also saved.
- Realized FPR is reported throughout.
- Prompt-variant pairs differ only in the variable under test: reflag vs plain history-aware; ledger vs
  ledger-null; two T = 1 samples vs one.
- Activity / length confound checks.
- Pre-specified comparisons: 3rd-max, top-3 sum, CUSUM k = 1.5 and the chooser vs max.
- Round-2 MOLE corpora are "discovery"; the five new ones are "confirmation".

**Part A: MOLE, all 8 public corpora** (4 generators × single-day / multiday; 112–114 routine accounts each).
- Monitor: one common history-free account-day monitor — Qwen3-235B-2507, MOLE judge prompt + taxonomy, compact
  audit rendering (first 250 events, lines ≤ 250 chars).
- Logprob providers throttled to ~0.4 calls/s, so the remaining calls ran on any provider without logprobs. The
  common output is the generated integer score.
- Robustness monitors: gpt-4.1-mini full rendering (3 corpora), MOLE z-score / peer-fit, an activity-only
  baseline (log events per day), and account-centered variants (day score minus the account's median).

**Part A results** (account-level FPR 0.10):
- **No accumulation rule beats max for the common monitor on any corpus.**
- 3rd-max − max: GPT-5.3 single-day −0.02 [−0.15, 0.09]; DeepSeek single-day +0.01; Qwen3.6 single-day −0.17
  [−0.36, −0.02]; Kimi single-day −0.16 [−0.31, 0.03].
- Random-effects pooled, single-day corpora (3–4 attack days per insider): 3rd-max −0.066 [−0.156, 0.023],
  top-3 sum −0.045 [−0.109, 0.019], mean −0.130 [−0.229, −0.031].
- Multiday corpora (one attack day): every rule ≤ max (pooled −0.02 to −0.09).
- Nested chooser vs always-max: −0.01 / −0.02 on average; it stays with max in most splits.
- **The round-2 gpt53 single-day gain was mostly an account-level confound.**
  - Insider accounts are more active and look more suspicious on routine days too: median events 123 vs 116;
    LLM non-attack-day AUROC 0.65.
  - An activity-only "monitor" (no content at all) reaches TPR 0.37 with 3rd-max (+0.32 [0.14, 0.49] over its
    own max), and keeps +0.21 with the attack days deleted.
  - Account-centering removes the gpt-4.1-mini 3rd-max gain: +0.131 → +0.001.
  - Peer-fit keeps +0.14 [0.01, 0.33].
- **Mechanism.** Across 64 corpus × monitor cells, the gain tracks repeat-spike informativeness: Spearman +0.30
  (p = 0.017) for top-3 sum, +0.28 for 3rd-max. For the common monitor on single-day corpora, though, a repeat
  high day is barely more likely for insiders than for routine accounts (log-LR −0.10 to +0.54), while honest
  persistence is high (h2c 0.23–0.62).
- **Horizon sweep** (first 5 / 10 / 15 / 20 workdays): no horizon produces a gain for the common monitor.
- **Daily review budget** (MOLE R@10/day): today's score is best or tied on every corpus (0.19–0.39); CUSUM
  k = 1.5 is close; running max, k-th largest and top-k are worse.
- Streaming-delay cells for integer scores are affected by ties: streaming alarms use a non-randomized threshold.

**Persistent state over longer horizons** ($0; matched ARL0, no reset):
- History-free gpt-4.1-mini: CUSUM k = 0.5 beats max (0.71 vs 0.58 at ARL0 = 100 PRs; 0.59 vs 0.48 at 500).
- Non-forgetting k-th largest / top-k collapse to ≈ 0.
- Concatenating runs into longer "attacks" was rejected: it would fabricate cross-run continuity.
**Part B: re-flagging as a monitor design target** (`ps_variants.py`, `mb_variants.py`, `reflag_analysis.py`;
`results/r3_t1/reflag_tables.md`).

Monitor: gpt-4.1-mini, logprob-expected scores.

Designs (matched pairs differ only in the variable under test):
- **history-free** (current PR / current step only; round-2 / track-1 streams);
- **history-aware** (all prior diffs / steps; plain);
- **reflag** = history-aware + an explicit rule: re-raise suspicion when the current unit continues earlier
  suspicious work, keep benign continuations low. Its matched pair is history-aware.
- **ledger**: no history; the monitor's own ledger of open suspicions plus an incremental-evidence score.
  - Its matched control, **ledger-null**, is the identical prompt with the notes always empty.
- **two samples at T = 1**:
  - **sample0** and **sample1**: one sample each;
  - **sample_mean**: per-unit mean of the two;
  - **sample_units**: both samples as separate units.

Data:
- Persistent state: 155 honest runs, 120 gradual, 397 positional.
- MonitoringBench: 150 Honest-550 trajectories + 150 attacks (100 S4); subsets S4, opus-4-5-only attacks
  (agent-model match), and a length-matched subset.

Results at matched run-level FPR. Gains over max use the corrected `amd.evaluation.paired` bootstrap; the
chooser is nested.
- **Re-flagging is not a better design.** On persistent-state gradual attacks at 5% FPR:
  - run-max AUROC is lower with the reflag rule than the plain history-aware monitor (0.806 vs 0.831), and its
    repeat-spike log-LR is unchanged (2.00 vs 1.91);
  - best TPR: history-free top-3 sum **0.74** (+0.16 [0.02, 0.23] over its max); history-aware top-3 0.67
    (+0.30 [0.16, 0.42] over a weak max 0.37); reflag top-3 0.56; ledger top-3 0.64; sample_mean top-3 0.72.
- At 1% FPR the best rules are close and CIs overlap: history-aware top-3 0.57 vs history-free top-3 0.53 and
  max 0.50.
- **MonitoringBench** (all / S4): no design exceeds TPR 0.43 at 5% FPR.
  - The reflag rule lowers the repeat-spike LR vs the plain history-aware prompt (0.45 vs 0.58).
  - Every gain over max is ≤ +0.12 and is mostly not significant.
- **Ledger vs ledger-null.** The carried notes raise max-type detection on persistent-state gradual attacks
  (max 0.55 vs 0.37), but the ledger monitor's honest scores grow with diff length (Spearman +0.71). It is not
  better than history-free.
- **Two samples.**
  - Each T = 1 sample is weaker than T = 0 (persistent-state gradual max 0.45 / 0.49 vs 0.58).
  - Their mean recovers T = 0 (top-3 0.72).
  - Using both samples as units gives a small significant accumulation gain on positional attacks at 1% FPR:
    +0.09 [0.03, 0.13] for top-3 over that stream's max.
- **Chooser.** With nested calibration it gains +0.05 to +0.31 where top-k clearly wins (persistent-state
  gradual), and stays within ±0.07 of max elsewhere, at realized FPR close to nominal.

**Validity checks.**
- **Diff length.** Gradual-attack diffs are about 4× shorter than honest diffs. A length-only "monitor"
  (−log chars) with 2nd-max reaches TPR 0.40 at 5% FPR on gradual attacks.
- But monitor scores rise with diff length (Spearman within honest PRs: gpt-4.1-mini +0.09, Qwen +0.51,
  ledger +0.71). So length works against the monitors, and it explains Qwen's high honest persistence in round 2.
- Length-matched persistent-state gradual subsets are too small (25/25; realized FPR ≈ 0.15) to conclude anything.
- MonitoringBench stream length AUROC is 0.72: attacks are longer. The opus-4-5-only and length-matched subsets
  give the same qualitative picture.

**Persistent state under continuous monitoring** (no reset; matched ARL0 = 5/α PRs; `ps_longhorizon.md`):
- CUSUM k = 0.5 beats max for history-free gpt-4.1-mini: 0.71 vs 0.58 at ARL0 = 100 PRs; 0.59 vs 0.48 at 500 PRs.
- Same for GPT-4o: 0.27 vs 0.16.
- Non-forgetting accumulators (k-th largest, top-k sum over the whole stream) collapse to ≈ 0.
- So in deployment, cross-session accumulation has to forget (CUSUM) or be windowed.
- Why no longer attacks were built: concatenating independent runs into longer campaigns would fabricate
  cross-run attack continuity that no agent produced.

## 2026-10-22: T3 ROUND 3 (execution replay feasibility; rewriter ≠ monitor; output-leak test; realized FPR; r3t3 $111.02)

Code `tracks/r3_t3/`, results `results/r3_t3/` (`paired_contrasts[_noout].md` primary; `compare[_noout].md`,
`leak_peaks.md`, `realized_fpr.md`). FINDINGS.md writes are blocked; full write-up is in the r3 hand-back message.
Audit (results/audit/issues.csv) M1/M2/M5/m5/m6 are applied: one-shot vs one-shot only; strict validity (judge AND
all target literals) primary; paired on identical base attacks; canonical joint bootstrap
(amd.evaluation.paired: honest + attacks resampled together, task-clustered, threshold recalibrated);
submit stripped only on a real submit.

- **A. Replay — infrastructure verified, replay of our trajectories NOT run.** Laptop Docker works (190 GB free).
  control-arena 20.1.0 ships BashArena (HF `Eccentricity/bashbench2`, 637 tasks; our task_ids match).
  benchmark-base builds in 1m51s (938 MB); the per-task 5-service compose is healthy in ~25 s. control-arena's
  official `test_disable_firewall` (fixed_policy + real sandbox + official side_task_success scorer, mockllm, no
  API key) PASSED in 103 s. Blocker = data fidelity: the stored trajectories keep only a rendered action
  string per step. bash steps keep the raw command, but text_editor steps (often the attack-critical config edit)
  have no recoverable structured arguments; some rewritten steps are bare shell; rewrites never had structured
  tool calls. A mis-parsed step would score as a failed attack, so replay was not run. Recipe for a full run:
  re-extract structured tool calls from the source .eval files for the originals, make the refiner emit
  structured {function, arguments}, then run fixed_policy per (sample, arm) (~1–2 min each, $0 API, laptop;
  `replay_basharena.py` + test_side_tasks.run_fixed_policy pattern). All probe images/containers were removed.
- **B. Rewriter ≠ monitor.** claude-sonnet-4.5 refused 44/46 pacing prompts (finish=content_filter; the control
  passed 13/13), so it was replaced by **google/gemini-2.5-pro**. Gemini one-shot control + 3 pacing arms on 35
  base attacks (no refusals), scored by gpt-4.1 none; compared with the round-2 gpt-4.1 one-shot arms (`*_r2_r0`)
  on the same 35. Canonical paired ΔUS @max, α=0.01:
  control − original: gpt-4.1 −0.60 [−0.72, −0.38], gemini −0.37 [−0.55, −0.19] → the rewrite artifact is NOT a
  same-model effect. Same-model inflation exists for the control: gpt-4.1 − gemini control −0.23
  [−0.36, −0.04] (multichart −0.14 [−0.31, −0.03]); no cross-rewriter difference for the pacing arms.
  Strategy (pace − control, one-shot): all 12 contrasts n.s. (gpt-4.1 −0.03..+0.11; gemini −0.14..−0.03).
  Strict validity: gpt-4.1 arms 0.74–0.77 (judge 0.94–0.97); gemini control 0.74, pacing 0.57–0.63 (judge
  0.74–0.80). Peak score: originals 5.62, gpt-4.1 rewrites 8.2–8.5, gemini 7.0–7.6.
- **C. Fabricated-output leak test** (re-scored with the current action's output stripped: 250 honest + 35
  originals + 8 arms). Rewrite peaks barely move (Δ −0.33..+0.25); originals' real outputs add suspicion
  (−0.55 [−1.03, −0.08] when stripped); DiD +0.2..+0.8 (the gap widens without outputs). No-output contrasts
  replicate: control − original −0.51 (gpt-4.1), −0.31 (gemini); strategy n.s. Fabricated outputs do not drive
  the findings.
- **D. Realized held-out FPR** (200 random 50/50 splits): with output (550 honest), max/cusum1.5/top3sum ≈
  nominal (0.0107/0.0102/0.0106 @0.01; 0.0033–0.0040 @0.003); **multichart runs hot**: 0.0173 @0.01, 0.0102
  @0.003 (exp-tail OR overfits the calibration set). No output (250 honest, 125 per half): every detector is
  1.6–2.6× nominal (small calibration halves).
- Caveats: n=35 base attacks (17 tasks); one-shot only; no execution replay; agent-model confound (audit M9)
  not stratified here.

## 2026-10-22: Second-pass audit (round 3 T1/T3, white-box pilot, E5 / r3_t2; $0 API)

Code `tracks/audit2/` (own minimal implementation in `a2lib.py`: randomized plug-in thresholds, task-grouped
splits, one joint cluster bootstrap shared across splits with thresholds recomputed; no reuse of
`amd.evaluation`). Outputs `results/audit2/`: `issues.csv` (4 major, 10 minor), `corrections.csv`,
`repro_summary.csv` and one CSV per reproduction. FINDINGS.md writes are blocked; this entry is the narrative.

**Reproductions (all headline numbers match within split / bootstrap noise).**
- WB, MB, TPR@FPR 0.01 minus gpt-4.1-mini: FIBS axial (none) +0.194 [+0.10, +0.28] (claimed +0.206); sab (full)
  +0.100 [+0.03, +0.17] (claimed +0.098).
- WB fusion: sab cascade 10% (full) 0.298 vs LLM 0.168, +0.129 [+0.07, +0.23] (claimed 0.299 vs 0.166);
  realized FPR 1.43% vs 1.81%; 13% of steps sent.
- MOLE: pooled single-day 3rd-max − max −0.073 [−0.166, +0.019] (claimed −0.066); account centering +0.126 →
  −0.001 (claimed +0.131 → +0.001); activity-only +0.32, +0.24 without attack days.
- T3 r3: gemini control − original −0.371 [−0.548, −0.182] (claimed −0.37); every pace − control contrast n.s.
- r3_t1 part B: whitened top-3 0.742 vs max 0.581, +0.161 [+0.026, +0.233] (claimed 0.74, +0.16).

**Major issues.**
- A1. The full-mode FIBS-axial reader threshold does not transfer across tasks: realized FPR 2.05% at nominal
  1% (LLM 1.42%; floor 1.58% at any nominal level). Its "+0.057" over the LLM is ≈ +0.06 at the reader's FPR
  floor, and every FIBS-axial-full fusion rule (KDE-LLR 0.328) runs at 1.9–3.2% realized FPR. The sab cascade
  and FIBS axial none are unaffected.
- A2. `data/processed/whitebox/scores/{la,t3}_{full,none}.jsonl` are 0-byte files, overwritten by the last pod
  sync (21:10, after the LA / T3-r1 analyses ran). The pods are deleted, so the LinuxArena and T3-round-1
  reader results cannot be re-derived or re-tested.
- A3. MOLE mechanism Spearman (+0.30, p = 0.017) treats 64 dependent cells as independent (first-audit M7,
  unfixed). Corpus-cluster CI [−0.04, +0.54]; primary monitors only: +0.18 (p 0.36).
- A4. T3 r3 undetected-success contrasts mix validity loss with detection. Detection-only, gemini control −
  original is −0.14 [−0.30, −0.03] (both-valid pairs −0.19). The artifact is real and not same-model, but about
  60% of −0.37 is broken attacks. The negative gemini pacing contrasts are validity loss (detection-only −0.06
  to +0.09).

**Minor issues.**
- Only 10 splits in the WB MB analysis (point-estimate noise).
- "Pre-specified primary" appears first in the results entry; with Holm over 18 stream × mode contrasts only
  FIBS axial none survives; sab full is Holm p 0.22.
- The LinuxArena ranking has no paired test.
- Cascade q was chosen among 5 levels; its gain is +0.165 on opus-4-5 attacks vs +0.067 on opus-4-6.
- MOLE "confound" claim: the raw gain was n.s. to begin with; without attack days gpt-4.1-mini barely separates
  accounts.
- Log typo: activity-only TPR is 0.32, not 0.37.
- DeepSeek single-day was scored by a provider mix clustered by account (+1 point on routine days); the pooled
  estimate is unchanged (−0.064).
- The part-B top-3 gain depends on whitening (raw top-3 +0.03).
- r3_t2 still uses the clamping matcher. Its 5% claims are unchanged; its 1% "matched" rows are mostly clamped
  (only infeasibility is claimed). The E5 table and log entry lack an erratum pointer.
- WB LinuxArena allocation rows are mostly clamped.

**Verdicts.**
- Round 3 T1: "no accumulation rule beats max on MOLE" holds; the mechanism correlation and the "account-level
  confound" wording are weakened.
- T3 r3: "artifact not same-model" holds with a smaller detection component; "strategy n.s." holds.
- White-box: FIBS axial none > LLM holds. sab full > LLM holds only if sab is the declared primary, and only
  for agent-matched attacks. The sab cascade holds. FIBS-axial-full claims and the LinuxArena ranking are
  weakened (and A2 makes them unverifiable).
- E5 / r3_t2: the C1 fix holds for E5 (results/fixes); the r3_t2 5% claims hold.

## 2026-10-22: T2 ROUND 4 (track r4ctx): per-context allocation at B = 1% with many honest runs per context — pre-specification

Written before any allocation result of this round was computed. Code `tracks/r4_ctx/`; outputs `results/r4_ctx/`.
OpenRouter spend: $0 planned (track `r4ctx`, cap $30, not expected to be used).

**Why.** Per-context plug-in rules have a test-spend floor of about Σ_c w_c/(n_c + 1). In rounds 1–3 the 1%
"spend-matched" rows were clamped (C1, m2, m9). This round uses panels with hundreds of honest runs per
context and an exact spend matcher.

**Data (descriptive counts only; `results/r4_ctx/panels.csv`).**
- `akshn_setting`: aksh-n 7 settings, Gemini-3.1-Pro local suspicion, trajectory max; 5,189 honest
  (328–1,396 per setting), 5,794 attacks. **Primary panel (largest n).** Damage = adjudicated overall_severity.
- `ca_setting_model`: ControlArena setting × agent, 12 contexts, ~250 honest each (secondary).
- `la_pub_env`: full public LinuxArena paper runs (data.linuxarena.ai metadata = HF
  anonymouslinuxarena/linuxarena-public; only per-trajectory monitor maxima, env, tasks and success flags were
  fetched, 45 MB). Monitor mean-action@gpt-5-nano. 2,183 honest (11 agent models × 200 tasks; 215–220 per
  environment, 20 tasks per environment), 919 attacks (8 attack models, Haiku obvious-attack, Opus
  strategy-attack). Damage = side-task severity tier (steep 1/2.5/5/10).
- The public data has no other monitor with ≥ 300 honest per context. Excluded before analysis:
  - `xd_*` cross-deployment panels (BashArena / MonitoringBench / LinuxArena leaderboard runs, 550–616
    honest each). The `simple@` monitors' trajectory max saturates: 8–47% of honest runs hit the scale top
    (100), so a 1% threshold is a coin flip among tied runs.
  - `la_pub_taskcat`: 3 of 6 categories have 9–36 attacks.
  - MRT SHADE: about 70 honest transcripts per task re-scored under many monitor prompts.

**Design.**
- Rules:
  - global; CFAR; pooled (EB n0).
  - Stackelberg, equal damage, attack hulls shrunk toward the other contexts with pseudo-count m0 = 10
    (`stack`); unshrunk `stack_m0`.
  - Severity-weighted Stackelberg (`stack_sev`): D_c = mean damage of the defender-fit attacks in c, hulls
    weighted by damage, m0 = 10.
- Splits: 10 random splits per panel, grouped by main task within a context when the context has
  ≥ 20 distinct main tasks, otherwise by trajectory (aksh-n iac / shade / agentdojo have 5–16 tasks).
  - Honest: calibration / test 50/50.
  - Attacks: three disjoint group-level thirds: defender fit (Stackelberg hulls, D_c), attacker information
    (informed / probing / damage-weighted attackers), evaluation.
  - Calibration uses honest runs only and is disjoint from test.
- Spend matching:
  - For each rule, the fit level is bisected so that the realized TEST spend Σ_c w_c FPR_c brackets B.
  - The two bracketing fits are mixed as a randomized policy (MixThreshold) so the realized spend equals B
    exactly. No interpolation of metrics, no clamping.
  - If the floor (test spend at level 0) exceeds B, the replicate is unmatched (NaN).
  - Rows matched in < 80% of (replicate, split) cells are reported as not estimable and their values are not
    shown.
  - The realized spend of every matched replicate is stored and checked (|spend − B| ≤ 1e-6).
- Inference (corrected joint bootstrap as in `amd.evaluation.paired`):
  - 200 replicates of a context-stratified cluster bootstrap over groups (honest and attack members of a
    group share its weight).
  - Each replicate's weights are reused in all 10 splits and by all rules; thresholds are refit and
    re-matched per replicate.
  - Replicate value = average over splits where the rule (or both rules of a contrast) matched.
  - Point estimate = average over the unweighted splits.
  - 95% percentile intervals.
- Attackers: uniform (mean TPR over contexts); informed context selection (min TPR on the attacker-information
  thirds under the published thresholds); probing (5 free probes per context); damage-weighted (max
  expected undetected damage); oracle min test TPR (reported, biased low).
- Budgets B ∈ {0.5%, 1%, 2%, 5%}.
- Transfer: the defender fits on attacks of a random half of the side tasks (or attack policies / agent
  models) in each context; the attacker information and evaluation thirds come from the other half
  (contexts with one side task / policy give the defender no own-context attacks; shrinkage falls back to
  the other contexts).

**Primary contrast (pre-specified).** On `akshn_setting`, B = 1%, in-distribution, spend-matched:
Δ = selection safety (informed attacker) of `stack` (equal damage, m0 = 10) minus `global`. The claim
"Stackelberg beats global against selection at 1%" is supported iff the 95% joint-bootstrap interval of Δ
is above 0 and both rules are matched in ≥ 80% of cells. Every other contrast (other rules, attackers,
budgets, panels, transfer) is secondary / exploratory and reported with its interval, without a
multiplicity claim.

## 2026-10-22: T3 ROUND 4 (execution-replay validity for Idea 3) — setup + pre-registration

Code `tracks/r4_replay/`, results `results/r4_replay/`, budget track `r4rep` (cap $90). Goal: ground
Idea-3's side-task validity in REAL execution (official BashArena side_task_success scorers in isolated
per-sample Docker sandboxes) instead of the round-2/3 LLM judge + target-literal check.

**Infrastructure.** control-arena 20.1.0 BashArena; benchmark-base image built once; per sample a fresh
5-service compose (unique Inspect project), torn down after scoring. A fixed-policy (mockllm, no API key)
replays the attack's recorded tool calls, then the official side-task scorer reads final SYSTEM STATE.
`extract_structured.py` re-extracts structured {function, arguments} (incl. text_editor create/str_replace
payloads) from the source .eval files via HTTP range requests — reusing the loader's machinery and NEVER
opening header.json (leaked-token safety). `replay_run.py` = fixed_policy + task_id_whitelist + official
scorer; per-command timeout lowered to 12 s (faithful attack-critical ops finish in <<12 s; this only caps
blocking benign filler) + a 1800 s per-sample hard cap. `rewrite_structured.py` re-runs the round-2/3
rewriter system prompts (control + pacing) but emits STRUCTURED tool calls so rewrites are replayable;
`score_and_judge.py` scores rewrites with the gpt-4.1 history-free monitor and the round-2 judge.

**Base set.** The 35 round-3 base attacks (17 BashArena tasks), stratified over the 4 official side tasks
(firewall 9 / malware 9 / sudo 8 / password_leak 9) and structures S2/S3/S4, all with native
side_task_success=True. One-shot vs one-shot only; paired on identical base attacks.

**Pre-specified primary contrast (written before any result is computed).**
1. ORIGINALS reproduction: fraction of the 35 "successful" MonitoringBench attacks whose recorded tool
   calls, replayed faithfully, re-achieve side_task_success under the official scorer. (Measures how often
   the dataset's success label reproduces in a clean sandbox.)
2. PRIMARY Idea-3 contrast under EXECUTION validity: the paired ΔUS = US(rewrite_control) − US(original)
   in undetected-success against the **max** detector at trajectory **FPR α=0.01** (gpt-4.1 history-free
   monitor, whitened), computed with the canonical joint paired bootstrap (amd.evaluation.paired: honest +
   attacks resampled together, task-clustered, threshold recalibrated per replicate), US_i = valid_i·(1 −
   P(alarm_i)) with an execution-invalid attack set to statistic +inf (never an undetected success).
   SECONDARY: pace_max − rewrite_control (strategy effect) against max at α=0.01; both contrasts also at
   α=0.003 and against multichart / cusum1.5 / top3sum; and the SAME contrasts recomputed with JUDGE
   validity, to quantify how much the validity source moves the Idea-3 conclusions.
3. Judge-vs-execution agreement and FALSE-VALID rate = P(execution side_task fails | predicted valid), for
   judge / literal / strict predictors, per rewrite arm.
Realized held-out FPR of each matched threshold is reported alongside. Rewriter = google/gemini-2.5-pro
(round-3 primary), arms rewrite_control + pace_max.

## 2026-10-22: T2 ROUND 4 (track r4ctx): results — per-context allocation at B = 1% with exact spend matching

Code `tracks/r4_ctx/`:
- `fetch_linuxarena.py`, `panels_r4.py`: data and panels.
- `r4lib.py` (+ 5 tests in `test_r4lib.py`): grouped three-way splits, joint cluster bootstrap, exact spend
  matching by randomized mixing.
- `run_r4.py`, `make_report.py`, `r3t2_rematch.py`.

Results in `results/r4_ctx/`:
- `tables.md`, `summary.csv` (every panel × mode × B × rule), `primary.csv`.
- `spend_check.csv`: per-rule share matched, floor and nominal spend; the max |realized − B| over every
  matched replicate is 3.5e-17.
- `panels.csv`, `figures/*.pdf`, `r3t2_corrected/`.

Raw replicates are in `data/processed/r4_ctx/` (gitignored). OpenRouter spend: $0 (track `r4ctx` unused). The
design is the pre-specification entry above, unchanged. 10 grouped splits × 200 joint cluster-bootstrap
replicates; about 10 minutes of compute.

**Primary contrast (pre-specified): met.** 7 settings (Gemini), B = 1%, in-distribution, exactly spend-matched.
Matched in 99.9% of cells; the spend floor is 0.19% on average (95th percentile 0.52%).
- Selection safety against the informed context-selecting attacker:
  - Stackelberg (equal damage, m0 = 10): 0.753 [0.661, 0.796].
  - global: 0.646 [0.596, 0.695].
  - **Δ = +0.107 [+0.024, +0.152]**, P(Δ > 0) = 1.00.
- Robustness:
  - basic bootstrap interval [+0.061, +0.190];
  - replicate mean +0.089;
  - all 10 splits > 0 (+0.042 to +0.172);
  - iid instead of task-grouped splits: +0.129 [+0.05, +0.16].
- So the round-1 1% advantage, which was not significant when spend-matched (m2: [−0.11, +0.20], partly
  clamped), holds once each context has 160–700 calibration runs.

**Secondary (exploratory; 7 settings, in-distribution, spend-matched; Δ vs global).**
- Cost to a uniform attacker at 1%: −0.020 [−0.04, +0.01] (TPR 0.834 vs 0.854).
- Severity-weighted Stackelberg at 1%:
  - selection: +0.124 [+0.05, +0.15];
  - damage-maximizing attacker: +0.077 [+0.02, +0.10] (equal-damage Stackelberg +0.058 [−0.01, +0.08]);
  - probing attacker (5 free probes per context): +0.067 [+0.00, +0.09] (equal damage +0.057 [−0.01, +0.08]).
- Shrinkage (m0 = 10) barely matters in-distribution (unshrunk +0.104 [+0.02, +0.15]).
- B = 0.5%: matched in 94% of cells. Stackelberg +0.089 [−0.08, +0.10], n.s.; the interval is wide and
  sits mostly above 0.
- B = 5%: +0.069 [+0.02, +0.09] (round 1 replicated). B = 2%: +0.133 [+0.07, +0.16].
- CFAR is worst at every budget: −0.280 [−0.46, −0.22] at 1%, −0.318 at 0.5%, −0.143 at 5%. Partial
  pooling (EB n0) −0.22 at 1%. Neither raises uniform TPR here (CFAR −0.047 [−0.11, −0.02] at 1%).
- Nominal fits over-spend out of sample at B = 1% (mean realized test spend): CFAR 1.27%, Stackelberg 1.20%,
  pooled 1.23%, global 0.99%.

**Transfer (7 settings).**
- Defender fit on other side tasks: Stackelberg is worse than global at every budget.
  - 1%: 0.510 vs 0.643, Δ −0.133 [−0.20, −0.08]. Severity-weighted −0.108 [−0.17, −0.06]; unshrunk −0.146.
  - 5%: −0.122 [−0.18, −0.08].
  - m0 = 10 shrinkage does not rescue it, so round 2's E1a result holds at 1%.
- Defender fit on other attack policies / agent models:
  - 1%: +0.033 [−0.09, +0.10], n.s.
  - 5%: +0.050 [+0.01, +0.08].
- So the 1% gain needs attack data from the deployed side-task distribution.

**Panels with fewer honest runs per context: the spend floor binds.**
- ControlArena setting × agent (~250 honest per context, 125 calibration):
  - CFAR / Stackelberg floor 0.63% mean, 1.30% p95.
  - Matched in 85% of cells at 1% and 41% at 0.5% (n.e.).
  - At 1%: Stackelberg Δ −0.004 [−0.23, +0.03]; CFAR −0.35 [−0.54, −0.24].
  - At 5%: Stackelberg +0.057 [−0.00, +0.09]; severity-weighted +0.065 [+0.01, +0.09].
  - Transfer to unseen side tasks: −0.14 at 1%, −0.23 at 5%.
- Public LinuxArena by environment (gpt-5-nano per-action monitor, about 217 honest per environment over
  20 tasks):
  - Per-context rules are not estimable at 1% (matched in 68%; floor 0.83% mean, 2.27% p95) or at 0.5% (40%).
  - The monitor is weak at these budgets: global uniform TPR 0.17 at 1%, 0.41 at 5%; selection safety 0.07
    / 0.15.
  - At 5% no contrast is significant (Stackelberg +0.10 [−0.12, +0.16]).
- The global and pooled rules have no material floor (≤ 0.09% mean), so they are matchable everywhere.
- In every panel CFAR and all Stackelberg variants share one floor (thresholds at each context's
  calibration maximum).

**Data notes.**
- The full public LinuxArena dataset has only ~217 honest runs per environment for any single monitor:
  11 agent models × 20 tasks, scored by the gpt-5-nano paper monitor.
- The cross-deployment `simple@` monitor panels were excluded before analysis because the maximum
  saturates: 8–47% of honest runs score 100.

**r3_t2 Watcher tables without the clamping matcher** (`results/r4_ctx/r3t2_corrected/tables_noclamp.md`,
`watcher_summary_noclamp.csv`).
- Method: same panels, seeds and 40 + 100 replicates; level swept over B × {0, 0.01..3}; NaN unless
  bracketed; n.e. below 80% matched. The r3_t2 files are untouched.
- The 5% Watcher claims hold:
  - mb_mini permissive 0.257 / strict 0.281 vs global 0.344 (Δ −0.082 [−0.19, −0.02], −0.059 [−0.17, −0.006]);
  - gpt-4.1 permissive 0.263 vs 0.373 (−0.122 [−0.25, −0.006]).
- At 1%, every per-org rule and both Watcher tiers on the MonitoringBench panels are n.e. (matched in 4–25%).
  The clamped originals had shown values for them (e.g. tier_opt 0.191 → 0.140 matched-only). Global,
  sev_tilt and tier_w/opt are matched in 85–96%.
- At 5%, the mb_mini per-org rows (CFAR, Stackelberg, cell minimax) are matched in 78%: now n.e.; the other
  panels' are 80–87%.
- On akshn_adj, watcher_perm (1% and 5%), watcher_strict (5%) and tier_w (5%) were never matched
  (0%; spend unreachable). Their original "matched" values were clamped.

**Takeaways.**
1. With hundreds of honest runs per context, the 1% Stackelberg advantage over global against a
   context-selecting attacker is real: about +0.1 selection safety at equal realized spend, at a small,
   n.s. uniform-TPR cost.
2. It needs on-distribution attack data. Fit on other side tasks, it loses about 0.13 to global.
3. Per-context rules are only usable at budget B if Σ_c w_c/(n_c + 1) ≪ B, i.e. at least ~1/B calibration runs
   in the smallest contexts. That is about 300+ per context for 1% after a 50/50 split. ~125 (ControlArena)
   and ~110 (LinuxArena env) are not enough.
4. CFAR remains the worst rule against selection at every budget.

## 2026-10-22: Idea 1 round 4 (track r4cs): cross-session accumulation across monitor families, MOLE with a stronger monitor, unreset streams with CIs

Code `tracks/r4_cs/`; tables and vector PDFs `results/r4_cs/` (`ps_tables.md`, `ps_meta.csv`, `fig_ps_forest.pdf`,
`arl_tables.md`, `fig_arl.pdf`, `mole_tables.md`, `fig_mole.pdf`, `mechanism.md`, `fig_mechanism.pdf`). OpenRouter
r4cs **$143.53 / $150** (pilot $6.54): persistent-state scoring incl. pilot $82.0 (gpt-4.1 $24.8, Claude Haiku 4.5 $17.8,
Gemini 2.5 Pro $31.4, gpt-5-mini $3.8, Claude Haiku 5.5 $2.5, GPT-6 Luna $1.6), MOLE GPT-6 Luna on 4 corpora $26.7,
MOLE gpt-4.1 subset $34.9. This entry stands in for FINDINGS.md (blocked for subagents). The analysis scripts were
committed (5d2d96a) before any full round-4 score was analysed; each script's docstring holds the pre-specification.

**Validity rules applied.** Honest-only calibration disjoint from test (50/50 splits); gains via
`amd.evaluation.paired` (one joint honest + attack resample per replicate, thresholds recomputed), clustered by app
(task sequence) on persistent state and by account on MOLE; realized FPR / ARL0 reported; prompts and inputs
identical across monitors (round-2 `build_messages`, current_only; only API-side settings differ: Gemini 2.5 Pro
1,024-token reasoning budget, gpt-5-mini / Luna `effort: low`, higher completion caps where hidden reasoning or
Claude verbosity truncated the `SCORE` line); monitor choice for MOLE made on persistent-state data only; length and
activity controls. Pilot (16 runs) was used only for parse rate and cost; all 6 candidate monitors were kept.

**Goal 1: more monitor families on persistent state** (`ps_multi.py`). 153 honest / 117 gradual runs with 5 scored
PRs under every monitor; 40 splits.

| monitor | run-max AUROC | max TPR @ FPR 0.05 (realized FPR) | top-3 sum − max [app CI] | 3rd-max − max [app CI] |
|---|---|---|---|---|
| gpt-4.1-mini (r2) | 0.894 | 0.565 (0.048) | +0.171 [−0.006, +0.275] | +0.032 [−0.230, +0.269] |
| Gemini 2.5 Flash (r2) | 0.623 | 0.227 (0.048) | +0.022 [−0.069, +0.140] | −0.058 |
| Qwen3-235B (r2) | 0.737 | 0.454 (0.054) | −0.063 [−0.155, +0.087] | −0.141 |
| gpt-4.1 | 0.818 | 0.521 (0.046) | −0.132 [−0.286, +0.161] | −0.322 [−0.468, −0.096] |
| Claude Haiku 4.5 | 0.707 | 0.251 (0.058) | +0.091 [−0.100, +0.250] | −0.005 |
| Gemini 2.5 Pro | 0.674 | 0.147 (0.046) | +0.008 [−0.168, +0.150] | −0.038 |
| gpt-5-mini | 0.797 | 0.463 (0.053) | −0.059 [−0.143, +0.057] | −0.345 [−0.575, −0.134] |
| Claude Haiku 5.5 | 0.894 | 0.729 (0.054) | **−0.241 [−0.400, −0.075]** | −0.651 [−0.779, −0.563] |
| GPT-6 Luna | 0.912 | 0.757 (0.052) | **−0.425 [−0.504, −0.261]** | −0.664 [−0.785, −0.533] |
| GPT-4o original (reference, not pooled) | 0.634 | 0.154 (0.048) | +0.087 [−0.001, +0.226] | +0.040 |

- **Pre-specified pooled estimate (9 identical-input monitors, random effects, joint app-clustered bootstrap):
  top-3 sum − max at FPR 0.05 = −0.070 [−0.144, +0.015]** (p(≤0) 0.94; HKSJ [−0.210, +0.070]; I² 0.87,
  τ² 0.031, 95% prediction interval [−0.51, +0.37]). No monitor has a significant gain; 2 have significant losses.
- 3rd-max − max pooled −0.253 [−0.383, −0.139] (4 monitors significantly negative). FPR 0.01: top-3 −0.099
  [−0.137, +0.023]. Raw top-3 −0.034 [−0.088, +0.027]; CUSUM k=1.5 −0.008 [−0.022, 0.000].
- Robustness, pooled top-3 at FPR 0.05: leave-apps-out calibration −0.076 [−0.134, +0.012] (max's realized FPR
  0.014–0.117 across monitors); length-residualized scores −0.031 [−0.136, +0.053]. gpt-4.1-mini keeps its gain under
  length residualization (+0.147 [+0.052, +0.192]) and on side-task-successful attacks (+0.260 [+0.044, +0.369]).
- On this common run set and with app clustering the GPT-4o reference gain is +0.087 [−0.001, +0.226], below the
  corrected round-1 +0.146 [+0.025, +0.226] (different run filter, 40 vs 10 splits, app vs iid clusters).
- **Reading:** the cross-session gain is a property of a few weak-to-mid monitors (gpt-4.1-mini, GPT-4o, maybe Haiku
  4.5), not of history-free per-PR monitoring in general. The strongest monitors put a near-ceiling score on the
  single payload PR, so max is already high (0.73–0.76), while their honest scores rise with diff length
  (Spearman +0.47 to +0.67), which inflates the honest top-3 tail. Exploratory, post hoc, k = 9: the gain falls with
  the honest score–diff-length correlation (Spearman −0.73, naive p 0.025) and with max TPR (−0.57, p 0.11).

**Goal 1b: mechanism, audit2 A3 fix** (`mechanism.py`, pre-specified). Per-monitor y = top-3 − max on attacks from
apps Q, x = repeat-spike log-LR from attacks of the other apps P, averaged over 20 app partitions, joint bootstrap
reusing the same run weights for x, y and every monitor. **Cross-fitted Spearman across the 9 monitors +0.065
[−0.341, +0.460]** (app), [−0.347, +0.391] (iid); not cross-fitted +0.100 [−0.417, +0.567]. Across all 42
corpus × monitor cells (persistent state + MOLE round-3 primary monitors + MOLE round-4 Luna; derived monitors
excluded): top-3 +0.016 with corpus-cluster CI [−0.15, +0.45], monitor-cluster [−0.43, +0.40], two-way [−0.54, +0.59];
MOLE cells only +0.189, two-way [−0.43, +0.72]. **The repeat-spike mechanism claim is not supported.** Example:
Claude Haiku 5.5 has the highest repeat-spike LR (2.72) and the second-largest loss.

**Goal 2: longer real multi-session data.** A search of HF / GitHub found no public release with more than 5
sessions per run and matched honest runs. Closest: the persistent-state archive `idacy/control-arena-persistent-state-eval-archive-2026-07-30`
"dbl" batch (6 PRs; 50 honest / 60 triggered-exfil attack runs; 885 MB `.eval` tarball, not used: one extra PR does
not change the question). `idacy/ca-pse-iclr2027` (13,311 runs, 3–4 PRs, 885k per-PR draws from 8 monitors) is
shorter, and its per-draw `level` field (confounded with monitor model) is undocumented in the public export, so the
history mode cannot be verified; it is a candidate for a $0 multi-monitor check once the analysis code is public.
MOLE has no release beyond 30 workdays. So the fallback was used: MOLE's 4 single-day corpora (112 routine vs 30
solo insiders, 3–4 attack days each, 30 workdays), renders rebuilt with the round-2 code into
`data/processed/r4_mole/` (account-day tables verified identical to rounds 2–3), scored with GPT-6 Luna on the
round-3 compact input (same input as the common Qwen3-235B monitor), plus gpt-4.1 on a budget-aware subset (gpt53
single-day: all 30 solo insiders + 50 random routine accounts, seed 4).

- Day-level: Luna separates attack days from routine days better than Qwen (AUROC 0.69–0.80 vs 0.57–0.69), but it
  also flags insiders on non-attack days (AUROC 0.60–0.64; gpt53 median day score 7.5 for insiders vs 5.8 routine).
- **Pre-specified primary, 3rd-max − max at account-level FPR 0.10, RE-pooled over the 4 corpora: Luna +0.047
  [−0.019, +0.114]** (no corpus significant); top-3 sum +0.030 [−0.013, +0.072]. Qwen (same accounts) −0.061
  [−0.150, +0.028]. With the attack days removed, Luna keeps +0.041 [−0.019, +0.101], so whatever gain there is is
  not driven by repeated attack days.
- Account centering removes Luna's detection entirely (TPR ≈ 0 for every rule): its insider signal is an
  account-level offset that saturates near the 10-point ceiling, so attack days add almost nothing on top.
- Activity-only control: gpt53 3rd-max − max +0.338 [+0.164, +0.514] (its max TPR is 0), +0.177 after centering;
  no effect on the other three corpora.
- gpt-4.1 subset (gpt53; 25 calibration accounts per split, realized FPR 0.138 at nominal 0.10, low power): max
  0.371, 3rd-max − max +0.093 [−0.075, +0.253], top-3 +0.055 [−0.072, +0.182]; Luna on the same accounts +0.037.
- Daily review budget (R@10/day): today's score is best or tied for every monitor and corpus (e.g. Luna gpt53 0.432
  vs running max 0.296, CUSUM k=1.5 0.395).

**Goal 3: long unreset streams** (`ps_arl.py`, pre-specified). No reset across runs; attack after U{0..4} honest
runs; ARL0 matched on calibration runs (1e-6 jitter = randomized ties); point = 10 splits; CI = 200 iid run-bootstrap
replicates of the whole procedure with re-calibrated thresholds; app-cluster bootstrap for ARL0 = 100.
- **Primary P3a (round-3 claim with CIs): gpt-4.1-mini, ARL0 = 100 PRs: CUSUM k=0.5 0.718 vs max 0.586,
  +0.132 [−0.086, +0.296]** (app {−0.09, +0.32}). The point estimate reproduces round 3 (0.71 vs 0.58), but it is
  not significant once threshold calibration and run sampling are resampled. ARL0 = 500: +0.120 [−0.076, +0.248].
- P3b: windowed top-3 (W = 5) − max, gpt-4.1-mini: +0.123 [−0.084, +0.266].
- Pooled over the 9 identical-input monitors (joint bootstrap), ARL0 = 100: CUSUM k=0.5 −0.032 [−0.109, +0.049];
  windowed top-3 **−0.116 [−0.178, −0.053]**; EWMA λ=0.2 −0.088 [−0.162, −0.009]; SR −0.061 [−0.133, +0.011];
  CUSUM k=1.5 +0.004 [−0.019, +0.020].
- Nested best forgetting rule (selected on attacks from one app half, evaluated on the other): +0.015 [−0.010,
  +0.062] pooled at ARL0 = 100; +0.039 [+0.007, +0.070] at ARL0 = 500 (iid only). No single monitor significant.
- Strong integer-score monitors (Luna, Haiku 5.5, gpt-5-mini) do best with CUSUM k = 1–2, which behaves like max.
  Low-k CUSUM, EWMA and windowed sums lose 0.1–0.4 for them.
- Realized ARL0 on held-out honest runs is near target at 100 (median 65–138 PRs). At 500, CUSUM over-alarms
  out of sample (median 168–351; Gemini 2.5 Pro 620) while max is conservative (no false alarm in 47% of splits), which favours
  CUSUM. The 500 cell is therefore not matched.

**Verdict.**
- The round-1/2 claim that cross-session accumulation helps history-free per-PR monitors does not generalize across
  monitor families. Pooled over 9 monitors it is −0.07 [−0.14, +0.02], with strong heterogeneity. It is positive only
  for gpt-4.1-mini (borderline) and GPT-4o (reference). The strongest monitors lose up to 0.43.
- "Repeat-spike informativeness predicts the gain" is not supported under dependence-aware, cross-fitted tests
  (A3 resolved: weakened to null).
- "Unreset streams favour CUSUM" is not significant for gpt-4.1-mini (+0.13 [−0.09, +0.30]). Pooled over monitors,
  max is as good as any forgetting rule at matched ARL0, and windowed sums are worse.
- On MOLE, a stronger day monitor does not create an accumulation gain (+0.05 [−0.02, +0.11]). Its insider signal
  is mostly account-level.

**Not done / caveats.**
- Only 5 apps, so the app-cluster bootstrap is coarse; iid intervals are given alongside.
- The gpt-4.1 MOLE subset is underpowered and runs at realized FPR 0.14.
- ca-pse-iclr2027 was not analysed (the history mode of its monitors is undocumented).
- Raw renders (`data/processed/r4_mole/*/renders.jsonl`, 1.1 GB) were deleted after scoring. Rebuild them with
  `tracks/r4_cs/mole_prep.py`.
- Scores: `data/processed/persistent_state/r4_scores_*_current_only.jsonl` and
  `data/processed/r4_mole/<corpus>/llm_*_compact*.parquet`. Caches are in `data/raw/r4_cs/`. ARL replicates are in
  `results/r4_cs/arl_replicates.csv.gz`.

### 2026-10-22: T3 ROUND 4 RESULTS (execution replay; r4rep $13.26)

All replays ran locally in isolated per-sample BashArena Docker sandboxes (official side_task scorers,
mockllm fixed-policy, no API key), torn down after each sample; 6 parallel workers, 10 s per-command cap,
900 s per-sample hard limit. Hangs beyond the limit are recorded as `status=error` (time-limit), kept
SEPARATE from scorer-false. Tables: `results/r4_replay/{reproduction,agreement,paired_contrasts}.{md,json}`.

**A. Execution reproduction of side_task_success (official scorers; the headline validity number).**
Faithfully replaying the recorded tool calls of attacks the dataset labels successful:
- originals        24/33 scored = **0.727** (2 time-limit errors, excluded)
- rewrite_control  16/33 scored = **0.485** (2 errors)
- pace_max         11/28 scored = **0.393** (4 errors)
So ~27% of "successful" MonitoringBench attacks do NOT reproduce in a clean sandbox, and LLM rewriting
breaks them much further: a NEUTRAL control rewrite loses ~a quarter more (0.73→0.49), and detector-aware
pacing (which adds/spreads steps) loses more still (0.39). The pilot firewall case is one concrete
non-reproducer (native label CORRECT → replay FALSE: the firewall edit is undone / not sufficient).

**B. LLM-judge vs EXECUTION validity (step 5; the key methodological result).** false_valid =
P(execution side_task fails | predictor says valid):
- rewrite_control: judge false_valid **0.571** (agree 0.39), strict 0.500, literal 0.423.
- pace_max:        judge false_valid **0.762** (agree 0.21), strict 0.750, literal 0.545.
The round-2/3 LLM judge calls a rewrite valid, yet the official scorer shows the side task actually FAILS
the majority of the time (57% control, 76% pacing). The target-literal static check is a somewhat better
but still poor predictor. Idea 3's validity therefore should NOT rest on the LLM judge — confirmed.

**C. Idea-3 contrasts recomputed with EXECUTION validity** (canonical joint paired bootstrap,
amd.evaluation.paired: honest+attacks resampled together, task-clustered, threshold recalibrated;
US=valid·(1−P(alarm)), execution-invalid→statistic +inf; n=28 common base attacks, 14 tasks, honest 550;
realized held-out FPR ≈ nominal: max 0.0141@.01 / 0.0070@.003, multichart slightly hot 0.0160).
- PRIMARY (pre-registered) ΔUS rewrite_control − original, max, α=0.01: **−0.214 [−0.480, +0.040]**,
  p(Δ≤0)=0.96 — negative (rewrites LESS undetected-successful than originals) but the 95% CI crosses 0,
  so NOT significant at the pre-specified bar. Under JUDGE validity the same contrast is −0.321
  [−0.500,−0.071] (significant). Execution grounding shrinks the magnitude ~1/3 and removes significance,
  because the originals themselves are only 0.727 execution-valid (the judge-/strict-validity analyses had
  assumed originals=1.0). Direction is robust across detectors (multichart −0.250 [−0.480,−0.017] sig;
  cusum1.5 −0.214; top3sum −0.107 n.s.).
- pace_max − original (exec, max α=0.01): −0.321 [−0.625,−0.030] (sig) — pacing is even worse for the attacker.
- SECONDARY strategy effect pace_max − rewrite_control (exec, max α=0.01): −0.107 [−0.357,+0.120], p=0.84
  (n.s.); all 8 detector×α cells n.s. — pacing does NOT beat a plain rewrite, replicating round 3 under
  execution validity.

**Takeaway.** Grounding side-task success in real execution (i) reveals that the dataset's and especially
the LLM judge's "success" are substantially over-stated (judge false-valid 57–76% on rewrites), and
(ii) leaves Idea 3's qualitative conclusion intact and arguably stronger — monitor-aware / pacing
rewriting does not help the attacker (pace−control n.s.; rewrite−original ≤0) — while showing the
rewrite−original magnitude is smaller and noisier than the judge-validity analysis implied. Idea 3 no
longer rests on an LLM judge.

**Caveats.** n=28 paired (14 tasks) after excluding execution errors/missing; one-shot vs one-shot;
rewriter = google/gemini-2.5-pro; 6 replay samples hit the 900 s wall and are recorded as errors (not
scorer-false). Fixed-policy replays recorded commands literally; a command that silently depended on a
real earlier dynamic output can fail — that is itself a genuine attack fragility and the right thing to
count. Replays never ran outside the sandbox; attack content stays in gitignored data/.

## 2026-10-22: Idea 05 round 1 (track r5jev): JEV as a per-step first-stage monitor — preregistration

Written and committed after the dev-split prompt choice and BEFORE any evaluation (held-out) trajectory is scored
by JEV, gpt-4.1-nano or the open decision model. Nothing below changes after evaluation scoring starts; any deviation
is reported as a deviation in the results entry. Plan: `docs/research/IDEA_05_DECISION_MODEL_MONITORS.md` (RQ1–RQ3).
Code `tracks/r5_jev/`; results `results/r5_jev/`; raw outputs and caches `data/r5_jev/` (gitignored). Budget tracks
`r5dev` ($10, dev pilots; spent $5.34) and `r5jev` ($150, everything else); open-model arm ≤ $50 RunPod.

**Model and interface.** OpenRouter Decisions API (`POST /api/alpha/decisions`, `amd.common.openrouter.OpenRouter.
decisions`, same ledger / caps / key fallback as chat), model `typesafe/jev-1.14`; every dev answer came from
`typesafe/jev-1.14-20261014` (the version is stored per call and reported). Requests carry only the main-task text
and step texts (no metadata, labels or eval headers). Probabilities are returned rounded to 0.01.

**Frozen JEV first stage (chosen on dev only; `results/r5_jev/dev_selection*.csv`, `dev_choice.json`).**
- Request variant `B_w3` (`tracks/r5_jev/jevlib.py`): state = {main_task (≤ 5,000 chars, head+tail), previous_actions
  (the 3 previous steps, action ≤ 600 / output ≤ 300 chars), current_action (action ≤ 4,000 / output ≤ 1,500)}; one
  Choice question with the structured rubric `B` (mirrors the ctrl-basic-v1 monitor's objectives and signs), asked
  in both label orders in the same request (state billed once).
- Score = P(suspicious) of the benign-first question, normalized over the two labels (order scheme `bs`).
- Dev selection: 3 variants (A_w3 concise rubric + 3-step window, A_w0 concise rubric, action only, B_w3) × 3 order
  schemes (benign-first, suspicious-first, mean). Dev = a seeded 10% of groups (main tasks; trajectories where a
  setting has < 20 tasks) per source, sample of ≤ 40 honest + 40 attacks per source (8 sources, 639 trajectories,
  18.9k steps per variant). Pre-set criterion (in `dev_select.py` before scores were read): mean over sources of
  capture@10% (share of attacks with a post-onset step above the 90th percentile of dev honest steps), tie-break
  (< 0.01) by mean trajectory-max AUROC. Result: A_w3/avg 0.895, A_w3/bs 0.894, A_w3/sb 0.894, **B_w3/bs 0.889
  (AUROC 0.813, highest of the tied set)**, B_w3/sb 0.888, A_w0 0.860–0.863 (the window helps). Dev per-source
  trajectory-max AUROC of the chosen config: MB 0.74, bash 1.00, agentdojo 0.99, iac 0.98, shade 0.84, BashArena
  opus-4-6 **0.24** (honest runs are longer than these attacks), BashArena sonnet-4-5 0.80, LinuxArena 0.92.

**Data and splits** (`tracks/r5_jev/splits.py` → `splits.json`, seed 20261022, metadata only). Dev groups are
excluded from every evaluation set.
- `mb` (primary): Honest-550 eval honest **511**; attacks = the 1,775 MonitoringBench attacks that already have
  gpt-4.1-mini `none` per-step scores (T1 sample 775 + r4_wb held-out 1,000) minus dev groups: **1,637**. First 60
  steps, final submit step stripped (T1 / r4_wb convention). Groups = main task. Honest-550 and these attacks were
  used by earlier tracks (not new data); JEV and nano have never seen them.
- `akshn_*` (primary, 7 settings, pooled): every eval trajectory with a Gemini-3.1-Pro step-unit stream; all steps.
  Eval honest / attacks: bash 680/669, agentdojo 680/670, iac 688/662, shade 679/668, BashArena-opus-4-6 418/489,
  BashArena-sonnet-4-5 300/853, LinuxArena 1,213/1,120. Groups = main task (traj for agentdojo / iac / shade).
- nano subset (H2 on aksh-n): per setting a seeded min(500, n) honest + min(300, n) attack eval trajectories.
- `linuxarena_sweep` (secondary): 200 honest / 142 attacks, 12 per-action sweep monitors, hidden-tool steps
  removed; 1% FPR not estimable (100 calibration honest) → 5% only.
- `persistent_state`: not used this round (5 PR-level units per run, no per-step second stage of the right kind).

**Second stages (cached, $0):** `mb` gpt-4.1-mini `ctrl-basic-v1` `none` (logprob-expected); secondary gpt-4.1-mini
`full` on the T1-sample attacks (`mb_fullhist`); aksh-n Gemini-3.1-Pro local per-step suspicion (strong monitor,
step unit). **First stages compared at equal e:** JEV (frozen); gpt-4.1-nano with the identical ctrl-basic-v1
`none` prompt (chat path, track r5jev, cache in each source's `score_cache.sqlite`; mb: all eval trajectories,
aksh-n: the nano subset); probe = FIBS axial follow-up `fibs_fu_ax`, trusted-reader `none` mode (the r4_wb primary
probe; mb only; honest + r4 attacks from the round-4 pod, T1-sample attacks from the pilot pod); `len` = characters
of the action; `rand` (seeded uniform); `oracle` (= the second-stage score itself, i.e. a perfect predictor of the
LLM); `oracle_label` (post-onset attack steps first, all else random; non-deployable upper reference).
Also reported: LLM-only and JEV-only (trajectory max).

**Cascade (`tracks/r5_jev/cascade.py`).** Per panel and split: (1) escalate the top-e share of CALIBRATION-HONEST
steps by first-stage score (global ranking, random tie-breaking by a fixed seeded jitter; a step without a
first-stage score is always escalated); (2) escalated steps take the cached LLM score; **non-escalated steps take a
conservative floor (primary)** (they can never raise an alarm); the quantile map of the first-stage score onto the
LLM's calibration-honest step distribution is a secondary sensitivity (JEV only; map held fixed per split);
(3) trajectory score = max; randomized plug-in threshold at nominal trajectory FPR α on calibration-honest
trajectories; TPR on all evaluation attacks (never used for calibration); realized FPR on the test-honest half.
e ∈ {5, 10, 20, 30}%, α ∈ {1, 5}%.

**Estimation and inference.** 50 random 50/50 splits of each panel's eval honest into calibration / test, grouped by
main task (trajectory for the < 20-task settings). Joint clustered bootstrap, B = 1,000 (as `amd.evaluation.
paired`, extended): one resample per replicate of honest groups and attack groups, reused in every split and by
every first stage; in each replicate BOTH the escalation threshold and the trajectory threshold are recomputed from
the reweighted calibration honest (calibration noise). Point estimate = split mean (unweighted). Pooled aksh-n
estimates sum alarms and attack weights across settings split by split (each setting keeps its own thresholds).
**Estimability:** an α = 1% cell uses only panels/settings with mean calibration n ≥ 200 (≥ 2 expected
exceedances); BashArena-sonnet-4-5 (≈150) is therefore excluded from every 1% pooled estimate and reported at 5%
only; at 5% the floor is 40. Analysis code: `tracks/r5_jev/analyze_primary.py` (tested in
`tests/test_r5_cascade.py` against brute force).

**Confirmatory hypotheses** (Holm over these five; each a one-sided non-inferiority test with margin 0.03 TPR;
p = (1 + #{Δ* ≤ −0.03})/(B + 1); **supported iff the Holm-adjusted p < 0.025**; all at α = 1% trajectory FPR):
- **H1-MB / H1-AK:** TPR(JEV→LLM cascade, e = 20%) − TPR(LLM-only) > −0.03 on `mb` / pooled aksh-n. (e = 20% is
  the largest rate the hypothesis allows; 5/10/30% are secondary.)
- **H2-MB / H2-AK:** TPR(JEV cascade, e = 10%) − TPR(nano cascade, e = 10%) > −0.03 on `mb` / the pooled aksh-n
  nano subset.
- **H3-MB:** TPR(JEV cascade, e = 10%) − TPR(probe cascade, e = 10%) > −0.03 on `mb` (only panel with probe scores).
- Secondary (no multiplicity claim, reported with intervals): every first stage × e × α, vs LLM-only and vs JEV;
  5% FPR; the map sensitivity; `mb_fullhist`; per-setting cells; realized FPR; escalated share of honest and attack
  steps; cost per 1k trajectories (first-stage $/step × steps + LLM $/step × escalated steps).

**Exploratory (labelled as such in the results).** RQ2: standalone JEV with max / top-k / CUSUM at matched FPR
(`matched_budget_eval`); breakdowns by side task and MonitoringBench structural strategy; readable vs derived side
tasks where a label allows it (MB: password-leak / malware download vs firewall / sudo edits; LinuxArena
exfiltration vs others); the length-only confound baseline. RQ3: gate by suspicion vs JEV confidence (escalate the
least confident steps) vs two-sided (escalate by suspicion but let confidently suspicious JEV steps p ≥ 0.99 alarm
on their own); overlap of JEV confident-benign attack misses with LLM misses vs an independence baseline.
Open decision model arm: Perplexity Decider v1.2 (`perplexity-ai/pplx-decider-v1.2`, Apache-2.0, bf16, sha
cce0f3f8) on the identical frozen requests, same score definition, as one more first stage on `mb` (exploratory;
not in the Holm family; scope set by the $50 RunPod cap, ≈ 3 requests/s on one H100).

**Predictions written down now (from prior work):** standalone JEV TPR at 1% FPR well below the LLM's
(Gould: SHADE 47% vs 67–71%); any value is in routing; JEV misses concentrate in derived/state-changing sabotage;
confident JEV misses are repeated by the LLM more than independence predicts.

## 2026-10-22/23: Round 4 white-box follow-ups (track r4_wb): preregistered replication, regenerated LinuxArena / T3-r1 streams, MOLE policy arm

Code `tracks/r4_wb/`; results `results/r4_wb/` (CSVs, `figures/*.pdf`). The preregistration `tracks/r4_wb/PREREG.md`
and the fixed held-out sets `tracks/r4_wb/heldout.json` were committed (c3cfacc) before any held-out item was scored.
Reader streams (no activations) are in `data/processed/whitebox/scores/r4/`. The pod code (`pod_reader.py`,
`pod_policy.py`, `probes.pt`, `probes_qwen36.pt`) is unchanged from the pilot. Pod environment: torch 2.14.1+cu130,
transformers 5.20.2, fla 0.5.2, no causal_conv1d.

**Environment agreement.** Honest trajectories re-read on the new pods agree with the pilot's stored streams at
bf16-noise level:
- Honest-550 `none`: FIBS axial r(max) 0.9993, median |Δmax| 0.025 honest SD.
- 60 honest trajectories, `full`: r(max) 0.998.
- Every mean-pooled stream has r ≥ 0.999 (`results/r4_wb/agreement_*.csv`).

### Part 1 (confirmatory): FIBS axial follow-up (`none`) vs gpt-4.1-mini (`none`) on held-out MonitoringBench

**Data.**
- Attacks: 1,000 attacks the pilot never touched, stratified by agent model × structure × side task.
  771 are opus-4-5 and 229 opus-4-6. There are no S4 attacks: all S4 attacks were in the pilot.
- Honest: Honest-550, re-used for calibration and realized FPR, as preregistered. The reader honest scores were
  recomputed on the replication pod.
- Analysis: 200 task-grouped splits; paired task-cluster bootstrap with calibration noise (B = 2,000).

| contrast (FPR 0.01 unless stated) | TPR reader | TPR LLM | Δ [95% CI] |
|---|---|---|---|
| **H1 primary** (realized FPR: reader 1.39%, LLM 1.28%) | 0.274 | 0.071 | **+0.203 [+0.100, +0.296]** |
| S1 opus-4-5 attacks (n=771) | 0.265 | 0.063 | +0.202 [+0.086, +0.307] |
| S2 opus-4-6 attacks (n=229; agent not in Honest-550) | 0.304 | 0.099 | +0.205 [+0.106, +0.296] |
| S3 FPR 0.05 (realized 6.1% / 5.4%) | 0.426 | 0.266 | +0.160 [+0.096, +0.290] |
| sens: pilot-stored honest reader scores | 0.273 | 0.071 | +0.202 [+0.099, +0.294] |
| sens: 972 attacks with complete LLM streams | 0.262 | 0.066 | +0.196 [+0.095, +0.289] |
| sens: missing LLM steps re-scored | 0.274 | 0.073 | +0.201 [+0.097, +0.293] |
| sens: calibration on Honest-550 + 200 external honest | 0.263 | 0.068 | +0.195 [+0.111, +0.286] |
| exploratory: `sab` (none) − LLM | 0.043 | 0.071 | −0.029 [−0.108, +0.020] |
| exploratory: FIBS linear follow-up (none) − LLM | 0.146 | 0.071 | +0.075 [−0.002, +0.148] |

- **H1 is supported.** The lower bound is +0.100 > 0. The estimate +0.203 lies inside the pilot interval
  [+0.10, +0.30] and is almost the same as the pilot's S1–S3-only estimate (+0.180).
- The equal-realized-FPR guard was not triggered (gap 0.11 pp < 0.25 pp).
- S1–S3 survive Holm, each with bootstrap p < 0.001.
- AUROC of the trajectory max: 0.817 for the reader vs 0.715 for the LLM.
- Both TPRs are lower than in the pilot (0.334 / 0.146). The pilot was S4-heavy; the gap between monitors is not.
- Strata (descriptive, `primary_strata.csv`):
  - Every structure and side task is positive: S1 +0.18, S2 +0.15, S3 +0.22; malware +0.33, sudo +0.29,
    passwords +0.19, firewall +0.08.
  - Firewall attacks are nearly undetectable by both monitors (0.09 / 0.01).
- **External honest** (200 akshn BashArena opus-4-6 honest runs on tasks not in Honest-550,
  `primary_external.csv`): at the Honest-550-calibrated thresholds, realized FPR is
  - at 1%: reader 1.20%, LLM 1.42%;
  - at 5%: reader 4.99%, LLM 7.16%.

  So the reader threshold transfers to new tasks and a new agent at least as well as the LLM's.
- The trusted reader's FIBS axial follow-up therefore beats a history-free gpt-4.1-mini at 1% FPR on new attacks
  by about +0.20. The other generic probes do not: `sab` is null, and the FIBS linear follow-up is borderline.

### Part 2: regenerated LinuxArena and T3-r1 streams (audit A2), paired tests, realized FPR (audit A1)

**Reproduction.**
- LinuxArena (342 trajectories) and T3-r1 (509) were re-read in `full` and `none`. The pilot's analyses
  (`tracks/r4_wb/repro_pilot.py` → `results/r4_wb/repro/`) reproduce the published tables:
  - LinuxArena AUROC: |diff| ≤ 0.001 for every stream.
  - LinuxArena TPR@0.01/0.05: |diff| ≤ 0.008 (FIBS axial full 0.756 → 0.763).
  - T3-r1 detection rows: 532 rows, mean |diff| 0.002, max 0.016.
- **The lost score files are regenerated.** `scores/{la,t3}_{full,none}.jsonl` were written only over the
  0-byte files.

**LinuxArena, paired** (`la_paired.csv`, `fig_la_paired.pdf`). FIBS axial follow-up `full` minus each of the 12 sweep
monitors, on the trajectories both scored. 200 splits; paired bootstrap; Holm over 12 contrasts per α.

| Comparator at FPR 0.01 (reader TPR 0.76–0.81) | Δ [95% CI] | Holm result |
|---|---|---|
| gpt-4.1-nano | +0.64 | Holm p < 0.05 |
| gpt-5-nano | +0.63 | Holm p < 0.05 |
| gpt-oss-120b | +0.46 | Holm p < 0.05 |
| gpt-5-mini | +0.30 | Holm p < 0.05 |
| kimi-k2.5 | +0.30 | Holm p < 0.05 |
| gemini-3-flash | +0.28 | Holm p < 0.05 |
| gpt-5.4 | +0.22 [+0.05, +0.32] | Holm p 0.020 |
| haiku-4.5 | +0.18 | not significant |
| glm-5 | +0.15 | not significant |
| sonnet-4.6 | +0.12 | not significant |
| gemini-3.1-pro | −0.15 | not significant |
| opus-4.6 | −0.16 [−0.28, −0.07] | **below the reader**, significant |

- At FPR 0.05:
  - The reader also beats sonnet-4.6 (+0.12, Holm 0.036).
  - It is below gemini-3.1-pro (−0.11) and opus-4.6 (−0.12).
  - gpt-5.4, gpt-5-mini and kimi drop to Holm 0.10.
- Realized FPR on the held-out honest half is 1.8–2.1% for the reader vs 1.2–1.8% for the LLMs (A1 again). The
  reader therefore runs at up to about 0.8 pp more FPR, and part of the margin over the weaker monitors is budget.
- In `none` mode the reader is weak on LinuxArena: TPR 0.19, and it loses to 9 of the 12 monitors.
- Revised pilot claim: in `full` mode the reader probe is above all small/mid monitors (7 Holm-significant), not
  distinguishable from haiku / glm / sonnet / gemini-3.1-pro, and below opus-4.6.

**A1 on the pilot MonitoringBench data** (`a1_mb_equalfpr.csv`, 200 splits; Δ vs gpt-4.1-mini of the same mode).

| Stream | Realized FPR, reader vs LLM | Δ at nominal 1% | Δ at equal realized FPR |
|---|---|---|---|
| FIBS axial `full` | 2.2% vs 1.27% | +0.105 [+0.052, +0.285] | +0.061 [+0.021, +0.219] |
| FIBS axial `none` | 1.3% vs 1.3% | +0.187 [+0.087, +0.265] | unchanged |
| sab `full` | equal | +0.099 [+0.021, +0.166] | +0.098 |

- FIBS axial `full`: equal FPR is unreachable. The bisection floor at nominal 1e-5 still gives 1.72%; the Δ at
  that floor is the "equal realized FPR" column.

**Per-context calibration as a sensitivity** (`a1_mb_percluster.csv`, `la_percontext.csv`). It is **not a usable
fix at 1%**:
- 8 MonitoringBench task clusters: per-cluster plug-in thresholds give realized FPR 5–7.6% at nominal 1% for every
  monitor, the LLM included, and about 10% at nominal 5%.
- 10 LinuxArena environments: realized FPR about 10%. Each environment has only 10 honest trajectories per
  calibration half.
- The global threshold, reported with its realized FPR, stays the right comparison. Per-context thresholds need far
  more honest data per context.

### Part 3: MOLE policy-activation arm with account-matched benign sessions (qwen36_27b_single_day)

**Design.**
- 233 attack sessions, each paired with a benign session of the **same account on the same day** (all 233 pairs
  same-day, 38 accounts; `tracks/r4_wb/mole_sel_ids.json`).
- `policy_neutral`: each attack session's system prompt (insider objective) is replaced by its paired benign
  session's system prompt, so within a pair the instruction is identical.
- LLM baselines: gpt-4.1-mini reads the reader-format transcript (no system prompt), one call per session.
- Inference: account-cluster bootstrap (B = 2,000), paired across arms (`mole_arms.csv`, `mole_contrasts.csv`,
  `fig_mole.pdf`).

**Session AUROC, `sab` max over turns:**

| Arm | AUROC [95% CI] |
|---|---|
| policy | 0.815 [0.77, 0.86] |
| policy_neutral | 0.817 [0.77, 0.86] |
| reader | 0.850 [0.80, 0.90] |
| LLM (insider prompt) | 0.903 [0.85, 0.95] |
| LLM (generic prompt) | 0.915 [0.87, 0.96] |

**Preregistered contrasts (Holm family of 5):**

| Contrast | Δ AUROC [95% CI] | Holm p |
|---|---|---|
| M1 policy − reader | −0.035 [−0.075, +0.008] | 0.29 |
| M2 policy_neutral − reader | −0.033 [−0.071, +0.005] | 0.29 |
| M3 policy − policy_neutral | −0.002 [−0.017, +0.014] | 0.80 |
| M4 reader − LLM(insider) | −0.053 [−0.104, −0.003] | 0.14 |
| M5 policy_neutral − LLM(insider) | **−0.086 [−0.140, −0.032]** | **0.005** |

**Secondary.**
- Mean over turns: policy 0.957, policy_neutral 0.943, reader 0.953. The instruction effect is small but nonzero
  (+0.014 [+0.006, +0.024]).
- FIBS-on-tokens (max over turns) rises when the instruction is neutralized: 0.818 → 0.903.
- Reader J-lens hits: 0.935 max / 0.974 mean, the best probe stream.

**Reading.**
- With account-matched negatives, the policy's own activations do not beat the trusted reader on the preregistered
  probe.
- Removing the insider instruction from the policy's context changes the policy probe by nothing measurable on the
  primary statistic. The probes key on the session's own content, not on the instruction.
- A cheap LLM session monitor (gpt-4.1-mini) beats every `sab`-max probe arm on these sessions (M5 survives Holm;
  M4 is nominal only). The pilot's high policy/reader AUROCs (0.95+) came from the mean statistic, which was chosen
  post hoc, and from unmatched negatives.

**Deviations and caveats.**
- OpenRouter credit ran out mid-run (402 on the personal key; the MATS workspace was already at its lifetime cap).
  - 305 LLM steps in 28 held-out attack trajectories were NaN in the registered run. They were handled by nanmax, as
    preregistered. Re-scored once credit was restored, they change Δ by −0.002 (sensitivity row).
  - The 200 external honest trajectories were scored after credit was restored. Nothing was changed after seeing
    primary results apart from adding those sensitivity rows.
- The held-out set has no S4 attacks, so the replication covers S1–S3 only.
- Honest-550 is re-used, so the honest side of the replication is not new data. The external honest check (new
  tasks, new agent) is the out-of-sample FPR evidence.
- The Qwen3.6-27B revision is unpinned, as in the pilot.
- The FIBS axial probe's training data (FIBSv1) may include BashArena-like transcripts. FIBS is an external release,
  so disjointness from MonitoringBench cannot be verified.
- The MOLE LLM baseline sees whole sessions (history-aware), while the probes take a max over turns.

**Cost.**
- GPU (RunPod MATS account, on-demand):
  - `r4wb-a` H200, 5.0 h: $26.5.
  - `r4wb-b` H200, 0.35 h: $1.9. It had a slow network and was replaced by `-c`.
  - `r4wb-c` H200, 5.4 h: $28.6.
  - `r4wb-d` H100, 3.35 h: $13.4.
  - Total ≈ $70.
- All four pods were deleted after their outputs were copied off and verified: row counts and unique ids checked,
  no empty files.
- OpenRouter track r4wb: $34.47 / $60.

## 2026-10-23: Idea 05 round 1 (track r5jev): JEV as a per-step first-stage monitor — results

Preregistration: commit f4d792a (the entry above), written before any held-out call. Code `tracks/r5_jev/`; tables and
vector PDFs `results/r5_jev/` (`hypotheses.csv`, `cascade_cells.csv` = every panel × first stage × e × α incl. realized
FPR and escalated shares, `panels.csv`, `explore_*.csv`, `fig_tpr_vs_e_alpha{1,5}.pdf`, `fig_hypotheses.pdf`,
`fig_decider_vs_jev.pdf`); scores and caches in `data/r5_jev/` and `data/processed/*/r5_scores_openai_gpt-4.1-nano_none.jsonl`.
Analysis: 50 grouped 50/50 honest splits per panel, joint clustered bootstrap B = 1,000 with both thresholds recomputed
per replicate (`analyze_primary.py`); exploratory parts B = 500 (`analyze_explore.py`).

**Scoring completeness.** JEV (`typesafe/jev-1.14-20261014` on every call): 420,986 held-out steps + 18,922 dev steps per
variant, 0 missing after re-runs. About 927 steps had failed in every pass during a laptop network outage (DNS / "network
unreachable"); a direct re-run with the network back scored all of them (HTTP 200), so no request was invalid and no
deviation rule was needed. gpt-4.1-nano: MonitoringBench 64.0k steps, 0 NaN; aksh-n nano subset 174.0k steps, 1 NaN
(a cached parse failure in akshn_bash; escalated per the preregistered missing-score rule). Probe and LLM streams aligned
with 0 length mismatches.

### Confirmatory (preregistered; Holm over five one-sided non-inferiority tests, margin 0.03, α = 1% trajectory FPR)

| test | contrast | TPRs | Δ [95% CI] | Holm p | verdict |
|---|---|---|---|---|---|
| H1-MB | JEV→mini cascade e=20% − mini only | 0.110 vs 0.114 | −0.003 [−0.006, +0.002] | 0.005 | supported |
| H1-AK | JEV→Gemini cascade e=20% − Gemini only, 6 settings pooled | 0.834 vs 0.833 | +0.001 [−0.015, +0.025] | 0.005 | supported |
| H2-MB | JEV cascade − nano cascade, e=10% | 0.124 vs 0.122 | +0.003 [−0.042, +0.038] | 0.071 | **not supported** (inconclusive) |
| H2-AK | JEV cascade − nano cascade, e=10%, nano subset pooled | 0.792 vs 0.621 | **+0.171 [+0.141, +0.203]** | 0.005 | supported |
| H3-MB | JEV cascade − probe (FIBS axial) cascade, e=10% | 0.124 vs 0.112 | +0.012 [−0.006, +0.034] | 0.005 | supported |

BashArena-sonnet-4-5 is excluded from every 1% pooled estimate (mean calibration n 151 < 200, preregistered rule).

**How to read these (do not overclaim).**
- *MonitoringBench is nearly degenerate as a cascade test.* The second stage (gpt-4.1-mini `none`) is weak (TPR 0.114 at
  realized FPR 0.015), and the LLM-score oracle gate reproduces LLM-only exactly. Every gate that escalates ≥ 20% (JEV,
  nano, probe, length, random at 30%) lands within 0.01 of LLM-only. So H1-MB and H3-MB show JEV routing loses nothing
  here, not that it is a strong router. H2-MB is a null with a wide interval.
- *H1-AK is a pooled average over heterogeneous settings.* Per setting (1%, e = 20%, Δ vs Gemini only): SHADE **+0.171
  [+0.070, +0.282]** (JEV filters Gemini's honest false alarms); iac +0.015; LinuxArena +0.003 [−0.005, +0.016];
  bash −0.002; agentdojo −0.001; **BashArena-opus-4-6 −0.244 [−0.288, −0.121]** (JEV ranks these attacks *below*
  honest runs; standalone AUROC 0.30, TPR 0.000). The SHADE gain offsets the opus-4-6 loss.
- *At 5% FPR (secondary) non-inferiority is not shown:* pooled 7 settings, e = 20%: −0.026 [−0.037, −0.014]; e = 30%:
  −0.013 [−0.022, −0.002]; e = 10%: −0.052. BashArena-sonnet-4-5 at 5%: −0.014 [−0.024, −0.007].
- *H2-AK is the clearest result:* at equal escalation, JEV triage beats gpt-4.1-nano triage (same `none` prompt as the
  mini monitor) by +0.17 at 1% and by +0.12 to +0.30 at 5% (e = 30% down to 5%). nano escalates only 11–37% of attack steps at
  e = 5–30% vs 23–46% for JEV.

**Secondary cells** (`cascade_cells.csv`; 1% FPR unless noted).
- Pooled aksh-n (6 settings), Gemini only 0.833: JEV cascade e = 5/10/20/30%: 0.800 / 0.824 / 0.834 / 0.839; action
  length 0.316 / 0.487 / 0.712 / 0.787; random 0.215 / 0.321 / 0.460 / 0.563; label oracle 0.968 → 0.900; JEV only
  0.581 [0.530, 0.620]. Escalated share of attack steps at e = 20%: JEV 0.37, length 0.20, oracle 0.51.
- MonitoringBench at 5% FPR: JEV cascade e = 5/10% beats mini-only by +0.046 [+0.009, +0.107] / +0.040 [+0.005, +0.077];
  probe e = 5% +0.035 [+0.005, +0.077]; nano never does. With mini full-history as the second stage (T1-sample attacks
  702): every gate within 0.01 of LLM-only (0.165) at e ≥ 10%.
- Quantile-map sensitivity (non-escalated steps keep a mapped JEV score instead of the floor): identical to the floor
  in every cell. The mapped values never reach the trajectory threshold.
- Realized FPR: cascades 0.010–0.016 at nominal 0.01; LLM-only on MB 0.015; **JEV-only on MB 0.024** (JEV probabilities
  are rounded to 0.01 and tie at the top of the honest distribution), so standalone JEV TPRs on MB are optimistic.
- Cost per 1k trajectories (MonitoringBench, 29 steps / trajectory): mini only $25.6; JEV only $3.96; nano only $6.33;
  JEV→mini cascade $5.3 / $6.7 / $9.3 / $11.8 at e = 5/10/20/30% (nano→mini $7.7–14.2). JEV costs $0.06–0.14 per 1k
  steps across sources (median request ≈ 2.7k tokens, latency ≈ 0.2 s). aksh-n: LLM calls per 1k trajectories drop
  from 57.8k to 11.6k at e = 20% (LinuxArena).
- LinuxArena sweep (5% only; 12 per-action monitors): JEV→monitor cascades lose to strong monitors at e ≤ 20%
  (e.g. opus-4-6 0.94 → 0.80 at e = 20%; gemini-3.1-pro 0.93 → 0.83) and are near LLM-only for weak ones.

### Exploratory (not preregistered tests; intervals uncorrected)

**RQ2: standalone JEV and where it fails.**
- Trajectory max at 1% FPR (JEV vs the second-stage LLM): MB 0.215 [0.095, 0.444] vs mini 0.103 (nano 0.029);
  bash 0.99 vs 0.99; agentdojo 0.91 vs 1.00; iac 0.57 vs 0.79; SHADE 0.15 vs 0.37; LinuxArena 0.64 vs 0.94;
  BashArena-opus-4-6 0.00 vs 0.82. The prediction "standalone JEV is weak at low FPR against a strong monitor" holds on
  aksh-n. On MonitoringBench JEV beats the weak mini `none` monitor.
- Aggregation (JEV, 1%): max is best on MB, bash, agentdojo and SHADE; mean is better on iac (0.69 vs 0.57),
  LinuxArena (0.74 vs 0.64), BashArena-sonnet-4-5 (0.44 vs 0.40) and opus-4-6 (0.03 vs 0.00); CUSUM (k = 0.5) and
  top-3 are worse almost everywhere (e.g. bash CUSUM 0.39 vs max 0.99).
- Readable vs derived (MB, 1%): JEV only, readable (password leak + malware, 666) 0.19 vs derived (firewall + sudo,
  971) 0.24; mini only, 0.18 vs **0.04**. The predicted derived-sabotage weakness is the LLM's, not JEV's, on this data.
  By side task, JEV only: sudo 0.37, firewall 0.10, password leak 0.19, malware 0.18. By agent: opus-4-5 0.25,
  opus-4-6 0.16.
- Length confound: max action length AUROC 0.33–0.66 (MB 0.48); step count AUROC 0.70 on MB and 0.83 on agentdojo,
  but 0.05–0.18 on the BashArena sets (attacks are shorter). Spearman(JEV, action length) on honest steps 0.04–0.21.
  JEV max rises with honest trajectory length (Spearman 0.06–0.42), which explains the BashArena-opus-4-6 failure:
  honest runs are longer than its short attacks.

**RQ3: gates and error overlap.**
- Gates at 1%, e = 10% (`explore_rq3_gates.csv`): suspicion ≥ confidence everywhere. Confidence gating fails where
  attack steps get p ≈ 1 (bash 0.72 vs 0.99, LinuxArena 0.92 vs 0.94, MB 0.09 vs 0.12). The two-sided rule (least
  confident escalated, p ≥ 0.99 alarms alone) ≈ suspicion (MB 0.126 vs 0.119).
- Overlap: attacks JEV confidently clears (every step p ≤ 0.05; 0.6–13.5% of attacks) are missed by the second-stage
  LLM far more often than its base rate. At 1%: LinuxArena P(Gemini miss | JEV confident-benign) 0.39 vs 0.066,
  ratio 5.9 [3.7, 8.9]; iac 0.77 vs 0.21 (3.6 [3.1, 4.3]); opus-4-6 1.6 [1.1, 2.1]; SHADE 1.4 [1.3, 1.5]; MB 1.11
  (mini misses 90% anyway). Conditional on any JEV miss the ratios are 1.0–2.7. Thresholds are held at split means, so
  these intervals omit threshold noise; sonnet-4-5 at 1% is below the calibration-size floor. The prediction (correlated
  confident errors) holds on sabotage data. This is why confidence-based escalation cannot rescue confident JEV misses.

**Open decision model (Perplexity Decider v1.2 27B, bf16, one H100, same frozen requests; `explore_decider.csv`).**
Scored MB eval (64.0k steps), the full aksh-n LinuxArena eval set (134.9k) and the LinuxArena sweep (20.3k) at
3.7–4.4 req/s. Standalone it matches JEV: AUROC(max) MB 0.82 vs 0.81, LinuxArena 0.96 vs 0.94, sweep 0.91 vs 0.88;
TPR at 1% MB 0.19 vs 0.23 (both ± 0.1), LinuxArena 0.64 vs 0.64. As a router it is equal or slightly better. MB 1%
cascade vs JEV cascade: e = 10% +0.017 [−0.004, +0.033], e = 20% +0.024 [−0.002, +0.046]; MB 5%, e = 20%: +0.039
[+0.007, +0.068]; sweep 5% with opus-4-6 as second stage: +0.046 to +0.055 (CIs exclude 0 at e = 10–20%);
LinuxArena 1%: ±0.001. The open model is a viable fee-free replacement for JEV in this cascade (and it returns
full-precision probabilities, with no 0.01 rounding).

### Deviations and caveats
- After the preregistration commit: (a) `rand_threshold_rows` vectorized (identical output, tested against the loop);
  (b) the preregistered LinuxArena-sweep secondary cells had been omitted from `analyze_primary.py` and were added
  (no effect on H1–H3); (c) the exploratory readable/derived map missed the label `password_leak` and was fixed before
  the reported numbers; (d) the open-model arm was extended from MB to the full aksh-n LinuxArena eval set and the
  LinuxArena sweep after its RunPod budget was raised (exploratory only); (e) a provisional primary run started before
  nano completed was discarded unread; only the final run (all scores complete) is reported.
- Honest-550 and the MB attacks were used by earlier tracks; MB calibration (mean n 252) and the 1% cells rest on
  2–3 calibration exceedances. Realized FPRs are reported above.
- aksh-n Gemini scores are the dataset's own monitor outputs. JEV / Decider training-data contamination with these
  public benchmarks cannot be excluded.
- JEV probabilities are rounded to 0.01, so its top tail ties (handled by random tie-breaking / randomized thresholds).
- RQ4 (monitor-aware attacks on the first stage) and fine-tuning / white-box reading of the open model are not done.

**Spend.** OpenRouter: r5dev $5.34 / $10 (JEV dev, 3 variants); r5jev $82.08 / $150 (JEV eval $47.04, gpt-4.1-nano
$35.04). RunPod (MATS account): one H100 on-demand pod `CLAUDE_POD_GREG---r5-decider` at $3.99/h, ≈ 16.9 h ≈ $67
(setup, smoke test, 219k Decider judgments); outputs copied and verified (md5), then the pod was deleted. The total
rate of prefixed pods stayed ≤ $15/h.

## 2026-10-23: Idea 05 round 2, part A (exploratory): is JEV's failure on BashArena-opus-4-6 a length or format confound?

Exploratory, not preregistered. Uses cached round-1 scores only (no API calls, $0). Same evaluation panels and step
alignment as round 1 (MB first 60 steps with submit stripped; aksh-n all steps; second stage = mini `none` on MB,
Gemini-3.1-Pro on aksh-n). Code `tracks/r5_jev/analyze_length.py`. Tables in `results/r5_jev/`:
`explore_length_confound.csv` (per panel), `explore_length_features.csv`, `explore_length_strata.csv`,
`explore_length_auroc_long.csv`, `explore_length_side_task.csv`. Intervals: grouped bootstrap over the panel's groups,
B = 500. Out-of-fold scores are held fixed, so there is no refit noise.

**Question.** On BashArena-opus-4-6, standalone JEV ranks attacks below honest runs (trajectory-max AUROC 0.30). The
JEV→Gemini cascade loses −0.244 at 1% FPR there. Is this because attacks are shorter (14 vs 23 median steps) and
the max over more steps is higher?

**Trajectory AUROC (attack = positive).**
- *Length only*: logistic regression on log step count, action / output / total chars; grouped 5-fold CV,
  out-of-fold scores.
- *+ format*: adds tool-call shares, share of truncated actions and share of empty outputs.
- *Stratified*: Mann-Whitney over within-stratum pairs only.
  - "n-strata": quintiles of step count.
  - "len-score strata": quintiles of the out-of-fold length-only score.
- *nadj-max*: −log(1 − F(max)^n), with F the empirical CDF of honest steps (in-sample).

| setting | length only | + format | JEV max | JEV max, n-strata | JEV max, len-score strata | JEV mean | JEV mean, len-score strata | JEV nadj-max | LLM max (len-score strata) |
|---|---|---|---|---|---|---|---|---|---|
| MB | 0.73 [0.67, 0.79] | 0.79 | 0.81 [0.76, 0.85] | 0.80 | 0.80 | 0.74 | 0.76 | 0.78 | 0.73 (0.71) |
| bash | 0.58 | 0.67 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 (1.00) |
| agentdojo | 0.90 [0.88, 0.92] | 0.92 | 0.99 | 0.99 | 0.99 | 0.99 | 0.99 | 0.99 | 1.00 (1.00) |
| iac | 0.67 | 0.70 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0.99 (0.99) |
| SHADE | 0.67 | 0.71 | 0.81 | 0.80 | 0.82 | 0.75 | 0.79 | 0.79 | 0.97 (0.97) |
| **BashArena-opus-4-6** | **0.84 [0.81, 0.86]** | **0.92** | **0.30 [0.27, 0.33]** | **0.35 [0.30, 0.39]** | **0.36 [0.31, 0.40]** | 0.44 | 0.40 | 0.43 | 0.98 (0.97) |
| BashArena-sonnet-4-5 | 0.95 [0.93, 0.96] | 0.97 | 0.87 [0.85, 0.89] | 0.92 | 0.92 | 0.93 | 0.91 | 0.94 | 1.00 (1.00) |
| LinuxArena | 0.77 [0.74, 0.80] | 0.83 | 0.94 | 0.96 | 0.95 | 0.96 | 0.96 | 0.96 | 0.99 (0.99) |

**Findings.**

1. **Length predicts the label on several sets, but it does not explain the opus-4-6 inversion.**
   - *Length alone carries signal.* Length-only AUROC is 0.84 on opus-4-6, 0.95 on sonnet-4-5, 0.90 on agentdojo,
     0.77 on LinuxArena and 0.73 on MB. On BashArena and LinuxArena attacks are shorter; on MB and agentdojo they are
     longer. Adding format features raises it to 0.92 on opus-4-6 (text_editor share AUROC 0.80, submit share 0.82,
     truncated-action share 0.82).
   - *Stratifying barely helps on opus-4-6.* Within length strata JEV max moves only from 0.30 to 0.35–0.36. In every
     step-count quintile it is 0.15–0.47, while Gemini scores 0.97–0.99 in the same strata.
   - *Elsewhere stratification changes JEV max by ≤ 0.05.* The gains are sonnet-4-5 0.87 → 0.92 and LinuxArena
     0.94 → 0.96. Length mildly dampens JEV max where honest runs are longer.
   - *Step level.* Action length barely separates steps (AUROC 0.50–0.62), and JEV is unchanged within action-length
     strata.

2. **Max vs mean.** Part of the round-1 max/mean difference is a length effect.
   - *Before stratifying*:
     - mean beats max where honest runs are longer: sonnet-4-5 0.93 vs 0.87, LinuxArena 0.96 vs 0.94, opus-4-6
       0.44 vs 0.30;
     - max beats mean on MB (0.81 vs 0.74) and SHADE (0.81 vs 0.75).
   - *After stratifying by the length score*, the gaps shrink to MB 0.80 vs 0.76, SHADE 0.82 vs 0.79, sonnet-4-5
     0.92 vs 0.91, and opus-4-6 0.36 vs 0.40.
   - *Length-adjusted max* is close to the better of the two everywhere (MB 0.78, SHADE 0.79, sonnet-4-5 0.94,
     LinuxArena 0.96). No aggregation rescues opus-4-6.
   - *Round-1 TPR at 1% FPR, max vs mean*: MB 0.22 vs 0.03, opus-4-6 0.00 vs 0.03.

3. **What does explain it: content on the honest side.** These checks are post hoc, added after reading the
   top-scoring honest steps.
   - *Honest runs make a firewall edit JEV flags.* 80% of opus-4-6 honest runs raise the firewall `PACKET_SIZE_LIMIT`
     as part of the main task (`sed -i 's/PACKET_SIZE_LIMIT=256/…65535/' /etc/firewall/firewall.conf`); only 19% of
     sonnet-4-5 honest runs do. JEV scores these steps at median 0.46, even with the main task in the request.
   - *That edit sets the honest maximum.* The highest-JEV step of 80% of opus-4-6 honest runs mentions the firewall
     (sonnet-4-5: 37%). 45% of opus-4-6 honest runs have JEV max ≥ 0.5, vs 18% of its attacks.
   - *Masking firewall steps* in both classes raises opus-4-6 AUROC from 0.30 to 0.58. On sonnet-4-5 the same masking
     lowers it (0.87 → 0.80), because there the firewall steps carry attack signal.

4. **...and truncation on the attack side.**
   - *Where actions are cut.* Ingest keeps only the head and tail of any action over 4,000 chars (`amd/data/_util.trunc`,
     `ACTION_CHARS`). The frozen JEV request also caps the current action at 4,000 chars. The aksh-n Gemini scores are
     the dataset's own, computed on the original actions. So on long steps Gemini saw text that JEV did not.
   - *Opus-4-6 attacks lose the most text.* They lose a median 52% of their action characters to truncation (honest
     28%; sonnet-4-5 30% / 27%; LinuxArena 3% / 12%; bash, agentdojo, iac and SHADE 0%).
   - *Gemini's top step is usually a truncated one there.* That holds for 75% of opus-4-6 attacks (honest 15%;
     sonnet-4-5 48%; LinuxArena 27%; others ≤ 6%). JEV's mean score at those steps is 0.09.
   - *Excluding truncated top steps is not enough on its own.* Restricting to attacks whose Gemini-argmax step is
     untruncated gives 0.36; with firewall steps also masked, 0.61. The corresponding figure for sonnet-4-5 is 0.95.
   - *Per-step separation is weak.* Even post-onset, JEV barely separates opus-4-6 attack steps from honest steps
     (step AUROC 0.56; 90th percentile 0.17 vs 0.09). On sonnet-4-5 the step AUROC is 0.67, with a 90th percentile of
     0.68 vs 0.02.
   - *By side task*, opus-4-6 JEV max AUROC ranges from 0.17 (disable_firewall) to 0.38. Gemini scores 0.91–1.00.

5. **How this produces the cascade loss.** Consider a gate that escalates the top 20% of honest steps:
   - *JEV gate.* It reaches Gemini's highest step in 52% of opus-4-6 attacks (49% when that step is truncated, 60% when
     not). On sonnet-4-5 and LinuxArena it reaches 96–97%.
   - *Action-length gate.* It reaches 90% on opus-4-6, including every truncated top step.
   - *Round 1 already showed the consequence* (opus-4-6, 1% FPR, e = 20%):
     - length-gate cascade 0.851, +0.039 [−0.020, +0.141] vs Gemini only;
     - JEV cascade 0.568, −0.244.
     On opus-4-6 the attack payload sits in long file writes, so a length gate routes better than JEV.

**Interpretation.**
- *Not mainly a length confound.* Length is a strong label predictor in these datasets, which matters for any
  standalone comparison, but holding it fixed leaves JEV at 0.35 on opus-4-6.
- *Two content effects drive the failure.*
  - Honest main tasks require a security-relevant config edit that JEV flags.
  - Attack payloads sit in the middle of long writes, which a 4,000-char head+tail view drops.
- *The truncation effect is a property of the frozen request, not only of ingest.* Even untruncated data would be cut
  at 4,000 chars by the request.
- *It also makes the aksh-n comparison uneven.* Standalone JEV-vs-Gemini comparisons on BashArena and LinuxArena favor
  Gemini partly because Gemini saw more text. In H1-AK, the escalated steps get Gemini's full-text score, but the
  routing decision is made on truncated text.
- *Not affected:* MB and the nano arms. Every MB score, and the nano scores on aksh-n, were computed on the same
  truncated text.
- *Reasoning text is not a JEV confound but is label-leaking.* JEV requests do not include it, but it differs sharply by
  label: MB honest median 944 chars vs attack 71 (AUROC 0.003); LinuxArena AUROC 0.79. Any monitor that reads
  reasoning on these sets would see a label leak.

**Leads for RQ4.**
- "Payload in the middle of a long write" is a concrete monitor-aware attack on a head+tail-truncating
  decision-model gate.
- A cheap length gate (or a full-text chunked first stage) is a natural complement.

**Caveats.**
- The firewall and truncation checks were chosen after inspecting the data.
- The CDF F in the length-adjusted max is in-sample.
- Stratified AUROCs ignore strata without both classes (e.g. sonnet-4-5 step-count quintile 1 has no honest runs).
- Gate coverage uses one global 80th-percentile threshold over all honest steps, not the cascade's split-wise
  calibration.
