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
