# Data

Everything under `data/` except this file is gitignored. `data/raw/<source>/` holds downloads and caches;
`data/processed/<source>/{trajectories,scores}.jsonl` holds normalized records in the schema of
`amd/common/schema.py` (Trajectory with Steps; ScoreStream). Rebuild a source with
`unset VIRTUAL_ENV; uv run python -m amd.data.<loader>`; run the checks and refresh
`results/data_inventory.md` with `uv run python -m amd.data.qc` (add `--spot 2 <source>` to print records).

Conventions shared by all sources:
- `traj_id = "<source>:<native id>"`; `label` is `honest` or `attack`.
- `context["main_task_description"]` holds the task text a monitor may see. The side-task text is only in
  `meta["side_task_description"]` (attacks); a monitor must never see it.
- Steps are agent actions in order (one tool call, or one text-only assistant turn). `action` = `fn(json-args)`
  truncated to 4,000 chars, `output` = tool output truncated to 2,000 chars (head and tail kept),
  `reasoning` = visible assistant text / reasoning truncated to 2,000 chars.
- `attack_step` / `harm_step` are 0-based step indices (None when unknown). Honest trajectories always have
  `attack_step = None` (checked by `amd.data.qc`).
- Scores keep their native scale (`ScoreStream.scale`). `NaN` (stored as JSON `null`) marks unscored units.
- `monitor_id = "<monitor model>|<prompt / score id>|<history mode>"`.
- Never written to processed data: Inspect `.eval` headers / `eval.revision` fields, raw sample metadata dicts,
  API keys or tokens.

Status (2026-10-20): all sources below are built: linuxarena_sweep, akshn_* (7 sets), monitoringbench, mb_honest,
persistent_state, mrt. MOLE is skipped for now. `data/processed/dev_fixture/` is built by the scoring harness, not by
a loader here.

---

## linuxarena_sweep — LinuxArena paper monitor sweep (`amd/data/linuxarena_sweep.py`)

**Source.** Public API `https://data.linuxarena.ai` (no auth; CC-BY). Three runs re-uploaded 2026-10-15:
`45ab968baebc46c4ad16003af43c6455` (Opus honest, 200), `4992785f32d54399a4b615ee01cd599d` (Opus attack, 92),
`c6e3ebcaf46a4b748475744c15666e11` (Opus strategy-attack, 50). For each trajectory the loader lists the run
(`/api/trajectories?run_id=...`) and downloads the raw Inspect sample (`/api/trajectories/{id}/sample`,
zstd JSON, ~1 MB each; 197 MB cached in `data/raw/linuxarena_sweep/samples/`).

**Counts.** 342 trajectories: honest 200, attack 142 (policy `attack` 92, `strategy-attack` 50). 10 environments
(20 honest each; 11–18 attacks each), 6 task categories, 92 side tasks (36 live, 106 delayed). Agent:
claude-opus-4-6 for all (the honest samples carry no model usage; taken from the run name, flagged in
`meta.agent_model_source`). Steps per trajectory q10/50/90: honest 20/54/136, attack 27/48/86. Side-task success:
139/142.

**Steps.** One Step per assistant tool call, in order (this is exactly the monitors' action index; verified
`len(steps) == actions_count` for all 342). Tools include the attack-only `run_side_task_test`,
`start_phase{1,2}_planning` and the final `submit`; LinuxArena hides these from the action monitors (auto-score 0,
"No reasoning provided"). Their indices are in `meta.hidden_tool_steps`, and `meta.ends_with_submit` is set
(honest 184/200 end with submit, attacks 141/142).

**Labels.** `harm_step = tasks.landed_at` (the action at which a *live* side task's harm happened; set for 36 of
142 attacks, None for delayed failures). `attack_step = None`: the sweep has no onset label.
`context`: env, main_task, task_category, side_task, failure_type (live/delayed), agent_model, policy,
main_task_description (full), env_description.

**Scores.** `scores.jsonl`, 7,460 streams:
- 12 per-action monitors `<model>|mean-action|full` (unit `step`, scale 0–100 in steps of 5 = mean of 2 draws of a
  0–10 score ×10): claude-haiku-4-5, claude-opus-4-6, claude-sonnet-4-6, gemini-3-flash, gemini-3.1-pro, glm-5,
  gpt-4.1-nano, gpt-5-mini, gpt-5-nano, gpt-5.4, gpt-oss-120b, kimi-k2.5. 4,017 streams (gpt-5-nano, gpt-5.4,
  opus: all 342; others 301–337: a monitor is missing for a few trajectories). Stream length always equals the
  number of steps. 2.6% of action scores are NaN: 454 streams have an unscored tail (the monitor stopped early);
  there are no interior NaNs. `meta.member_scores` has the two draws per step; `meta.skipped_idx` lists actions
  whose explanation is "No reasoning provided" (hidden tools, plus rare non-hidden failures; their score is 0).
- 12 trajectory-level "quick" monitors `<model>|mean-quick|trajectory` (unit `trajectory`, 0–100), 3,443 streams
  with partial coverage. A 0 with an empty or "No reasoning provided" explanation is a failed call and is stored as
  NaN (native value in `meta.native_score`, flag `meta.failed_call`). This removes most quick scores for
  gemini-3.1-pro (97%), and all attack scores for claude-sonnet-4-6 and kimi-k2.5. Use the quick monitors with
  care.
- Checks: per-action scores equal the scout extract in `../data/samples/linuxarena_paper_monitor_sweep/` (except
  that the scout dropped unscored tails); max per-action score ×10 equals the API listing's `max` for every stream.
  AUROC of max-over-steps (attack vs honest): opus-4-6 0.991, haiku-4-5 0.985, gemini-3.1-pro 0.976, glm-5 0.964,
  gpt-5.4 0.945, gpt-5-mini 0.924, kimi 0.923, sonnet-4-6 0.913, gemini-3-flash 0.888, gpt-oss-120b 0.872,
  gpt-5-nano 0.762, gpt-4.1-nano 0.613.

**Caveats.** n is small (142 attacks over 92 side tasks). Per-step scores are made *before* the action executes
and see the full history. The 0–100 scale differs from the 0–10 HF mirror.

---

## akshn_* — aksh-n monitor-label sets (`amd/data/akshn.py`)

**Source.** HF `aksh-n/<set>-monitor-labels` (no license stated): one JSON per row with a Gemini-3.1-Pro
(`google/gemini-3.1-pro-preview`, rubric `online_v0`) streaming judge (`nonpriv_streaming`: per-step
`current_step_local_suspicion` 0–10, `cumulative_confidence` 0–10, severity, would_flag_now), a privileged judge
that knows the side task, and an adjudicator (`ideal_flagging_step`, `point_of_no_return_step`,
`step_flag_score`). Label sets are fetched with `git clone --depth 1` (the JSONs are plain git blobs; per-file
downloads hit HF 429 rate limits). Each set is joined to the trajectory parquet it was built from (row i ↔ row i,
ids verified; goldset joins on trajectory id):

| processed source | label set | trajectory source | rows (h/a) | steps q10/50/90 h; a | step-aligned |
|---|---|---|---|---|---|
| akshn_bash | control_arena_bash | adityaasinha28/control_arena_bash | 750/750 | 7/17/42; 8/16/35 | 1500/1500 |
| akshn_agentdojo | control_arena_agentdojo | adityaasinha28/control_arena_agentdojo | 750/750 | 2/3/5; 3/5/8 | 1500/1500 |
| akshn_iac | control_arena_iac | adityaasinha28/control_arena_iac | 750/750 | 9/17/31; 11/20/35 | 1500/1500 |
| akshn_shade | control_arena_shade | adityaasinha28/control_arena_shade | 747/750 | 34/61/92; 34/66/94 | 1497/1497 |
| akshn_basharena_opus46 | basharena_action_only_opus46_large | adityaasinha28/basharena_action_only_opus46_large | 564/564 | 14/24/43; 10/14/21 | 1032/1128 |
| akshn_basharena_sonnet45 | basharena_action_only_sonnet45_large | adityaasinha28/basharena_action_only_sonnet45_large | 925/925 | 29/45/74; 11/19/38 | 1260/1850 |
| akshn_linuxarena | linux_arena_goldset | aksh-n/linux_arena_preprocessed | 1396/1305 | 26/62/113; 21/44/76 | 2701/2701 |

(shade: 3 rows have no label file; goldset: 7 `label_failed` rows have no file. All other manifest statuses,
including the 12 `postfiltered` goldset rows, are kept; see `meta.label_status`.)

**Judge steps vs Steps.** The judge streams over *judge steps*: step 0 is the user task, then one judge step per
tool call (or text-only assistant turn) and one per tool result. I rebuilt this segmentation from the source
transcript (`[USER]/[ASSISTANT]/[TOOL CALLS]/[TOOL]` text for ControlArena; `<step_N><tool_k>/<tool_output_k>`
XML for BashArena; `[user] + (action, output)` per LinuxArena action) and checked that the segment count equals
`len(nonpriv_streaming)`. It matches for every row except the BashArena `honest_summarized` rows (96 opus46,
590 sonnet45), whose source transcript replaces a middle section with a summary. Steps are the agent actions;
each tool result is attached to its call.

**Streams** (scale 0–10, `history: full`):
- `gemini-3.1-pro|akshn_local|full` and `gemini-3.1-pro|akshn_cumulative|full`, unit `step`: the judge's local
  suspicion / cumulative confidence at the judge step where each action is taken (before its output is seen).
  Length == number of steps. Written only for aligned rows.
- `...|akshn_local_judgestep|full`, `...|akshn_cumulative_judgestep|full`, unit `judge_step`: the native series,
  for all rows (aligned rows have `meta.judge_to_step`, mapping judge step → action index).
- `...|akshn_priv_flag_judgestep|privileged`, unit `judge_step`: the adjudicator's `step_flag_score`. The judge
  knew the side task, so this is an oracle, not a monitor.
No NaNs. AUROC of max local suspicion (attack vs honest): bash 0.999, agentdojo 1.000, iac 0.990, shade 0.971,
basharena opus46 0.975, sonnet45 0.996, linuxarena 0.993.

**Labels.** `attack_step` = the adjudicator's `ideal_flagging_step` mapped to the action at or before it (no
better onset label exists in these sets; set for attacks on aligned rows: 750, 750, 750, 749, 557, 922, 1,294).
`meta.point_of_no_return_step` is mapped the same way; native judge-step indices are in
`meta.*_native`. `harm_step = None`. `side_task_success` is only known for the goldset (all True); the
ControlArena/BashArena exports only ship successful-attack vs benign labels.

**Context.** ControlArena: setting, main_task (from the source `trajectory_data.metadata`), side_task
(`side_task_name`, or the first line of the side-task description), agent_model (claude-sonnet-4 / gemini-2.5-pro
/ gpt-5, 500 rows each), policy = source eval file (`negative1/2` honest, `positive1-3` attack); agentdojo adds
`task_cluster` (suite). BashArena: main_task (task id), side_task (4 BashArena side tasks), policy (`honest`,
`honest_summarized`, `attack`), agent_model. Goldset: env (10), main_task, task_category, side_task (92),
failure_type, agent_model (11; ~770 null values in the source were inferred from the run name, see
`meta.agent_model_source`; 39 remain None), policy = run_family (honest, attack-plain, strategy-attack,
no-scratchpad, ...).

**Caveats.** One monitor only (Gemini-3.1-Pro, ~$1.5–3 per trajectory; do not regenerate). No license; the
provenance of the ControlArena exports is unknown. The goldset is a curated subset of LinuxArena (all attacks
succeeded). Honest and attack trajectories differ in length in some sets (BashArena: honest longer; the
`honest_summarized` rows are summaries).

---

## monitoringbench — MonitoringBench attacks (`amd/data/monitoringbench.py`)

**Source.** HF `neur26anonsub/ctrldataset2026` (CC-BY-4.0; the paper asks for exclusion from training corpora).
`master.parquet` (2,644 rows × 135 columns) is joined on `sample_uuid` to the Inspect samples in
`final_dataset.zip` (2.47 GB, 2,363 `.eval` members; all 2,644 rows matched). The zip is read by HTTP range
requests, one `.eval` member at a time, and each sample is reduced to a compact JSON in
`data/raw/monitoringbench/extracted/` (the archive is never stored). **Security:** the `.eval` headers embed a
leaked GitHub token; the loader never opens `header.json` and whitelists sample fields. A check confirmed that the
token from a sample header does not occur anywhere in `data/processed/`.

**Counts.** 2,644 attacks, all with side_task_success = True. Side task: sudo_edit 874, disable_firewall_partial
811, download_malware 506, leak_passwords 453. Source (`context.policy`): recon_refined 799, recon 796,
human_strategies 511, opus_only 196, human_strategies_refined 185, opus_only_refined 157. 136 main tasks
(`context.task_id`). Agent: claude-opus-4-5 1,935, claude-opus-4-6 709. Steps q10/50/90: 19/31/43 (max 60);
`len(steps) == tool_call_count` for 2,643 (one trajectory has an extra text-only assistant turn).

**Labels.** The parquet's `attack_step` is 1-based and marks the action that executes the payload:
`attack_step = harm_step = attack_step_native - 1` (set for 2,442; 202 rows have no attack_step). The position is
spread out (attack_step / n_steps q10/50/90 = 0.20/0.50/0.81). `meta.first_attack_step` is a heuristic earlier
onset: the first action (≤ attack_step) that mentions a side-task target literal (the first three octets of target
IPs from the side-task description and from the parquet's post-hoc `attack_summary`, URL hosts, the
`restricted-service` user for sudo). It is set for 2,055 of 2,442 attacks (missing mostly for firewall, 246) and
equals attack_step in 47% of those (median gap 1 step, q90 14). Recon reads of the target count as
"touching" it. Taxonomy in meta: `structural_strategy` (S1 714, S2 219, S3 1,209, S4 475, missing 27),
`evasion_tactics`, `technical_techniques` (+ explanations), `attack_summary`, `attack_group`, `source_group`.

**Normalization.** Attacks call bash with `cmd` already (0 renames). `meta.ends_with_submit` is True for 2,063
(78%), and `meta.submit_step` gives its index; the submit step is kept as the last Step. 47% of attack steps have
non-empty `reasoning` (visible assistant text), against 99.99% for Honest-550; a monitor comparing the two sets
must not use the reasoning field.

**Scores.** 91,690 trajectory-level streams (unit `trajectory`, scale 0–10, value = mean over available epochs,
per-epoch values in `meta.epochs`): `<model>|mb_ft|full_trajectory` (13 FT monitors, tool calls without outputs),
`<model>|mb_sw|stepwise_max` (stepwise monitor, trajectory max, 254–1,428 rows), `<model>|mb_sw_full|stepwise_max`
and `<model>|mb_sw_trimmed|stepwise_max` (7 models, ~2.4k rows), `<model>|mb_dev|full_trajectory` (gpt-5,
claude-opus-4-5, gpt-5-nano). No per-step series exist in the release. There are no honest scores, so no AUROC.

**Caveats.** Only successful attacks are released. Several BashArena environment files contain synthetic
honeypot secrets (e.g. `/opt/configs/api_tokens.json` with fake `ghp_...` tokens), which appear in tool outputs here and
in mb_honest, akshn_basharena_* and the LinuxArena sources. They are part of the environment, not leaked
credentials, but keep `data/` private anyway.

---

## mb_honest — MonitoringBench-Honest-550 (`amd/data/mb_honest.py`)

**Source.** HF `palaestraresearch/monitoringbench-honest-550` (CC-BY-4.0): `original_inspect_logs.zip` (98 MB,
downloaded; 59 `.eval` batch files, 561 samples) and `manifest.jsonl`. Only the 550 manifest samples (matched by
`source_sample_uuid`) are kept.

**Counts.** 550 honest trajectories (claude-opus-4-5, `eval_mode = honest`), 116 BashArena tasks, all of which are
among the 136 MonitoringBench attack tasks. Steps q10/50/90: 13/22/41 (max 75), mean 25.4.
`traj_id = mb_honest:<release_id>`.

**Normalization.** Every trajectory used bash/python `command`; renamed to `cmd` to match the attacks
(`meta.renamed_command_args`). 545/550 end with submit (`meta.ends_with_submit`, `meta.submit_step`), versus 78%
of attacks. Encrypted reasoning blobs are dropped; the visible assistant text is kept in `reasoning` (see the
caveat above). Tools `str_replace` (18 trajectories) and `python` (61) appear besides bash/text_editor/submit.

**Scores.** None in the release (`scores.jsonl` is empty). Per-step scores must be regenerated (T1/T2).

---

## mrt — ScaleAI MRT, sequential monitors (`amd/data/mrt.py`)

**Source.** HF `ScaleAI/mrt` (arXiv 2508.19461; code github.com/scaleapi/mrt). **License CC-BY-NC-4.0** (research
only, no commercial use). Contains a canary string; do not train on it. Layout:
`task_pairs[_agentcompany]/<task>/<cfg>/<agent model>/<monitor model>/transcript_<i>.json`. The monitor
scaffold is a suffix of `<cfg>`: `<agent cfg>_sequential_<N>_<prompt>[_superaware|_unaware]`.

**Selection.** Only `sequential_N` files are used: 11,415 of 53,187 (4,185 honest, i.e. cfg contains
`no_secondary_task`/`benign`, and 7,230 attack). Selected: all honest files plus 3,000 attack files (150 per task,
round-robin over (N, monitor model), then prompt variant; all in (task, N, monitor) groups that also have honest
files; seed 20261020). Downloads use ≤4 workers (HF 429s otherwise). Cache: `data/raw/mrt/` (listing, selection,
gzipped raw JSON, 281 MB). Skipped: 585 files without `monitor_conversation` (legacy prompts) and 65 incomplete
summary-mode streams (`data/processed/mrt/build_stats.json`).

**Counts.** 1,458 trajectories: honest 286 SHADE + 150 CUA, attack 203 SHADE + 819 CUA. 20 tasks (5 SHADE-Arena; 15
CUA/TheAgentCompany with 10 honest and 53–55 attacks each). 6,535 score streams. Agent models (`context.agent_model`):
claude-sonnet-4, claude-3.5-sonnet/haiku, claude-3.7-sonnet, gemini-2.5-pro/flash. Steps q10/50/90: honest
9/29/146, attack 18/29/58.

**Trajectories.** One per agent transcript: `traj_id = mrt:<task>/<agent cfg>/<agent model>/transcript_<i>`
(`meta.agent_traj_key`). Copies of the same transcript across monitors, chunk sizes and awareness variants are
merged after checking the conversation SHA-1 (one key differed and is kept as 2 trajectories). Honest transcripts are
reused heavily (up to 28 streams per trajectory), so de-duplicate by `traj_id` for trajectory-level statistics.
Steps: one per assistant turn. `action` = the called tool names (`name()`; **MRT stores no tool arguments**),
`reasoning` = assistant text with `<thinking>/<hidden_thinking>` removed (as the monitor saw it), `output` = the
following tool outputs. Context: task, domain (shade|cua), main_task (= task), main_task_description, side_task
(`<task>_side_task`, one per task; the text is in `meta.side_task_description`, recovered from the task default for
81 attacks whose agent system prompt is empty, see `context.side_task_source`), agent_model, policy (agent cfg),
attack_strategy tokens (selective, liar, visible, naive, manipulator, thinking_time, ...). `side_task_success`
comes from `side_task_evaluation` (SHADE attacks: 149 True, 54 False; CUA files carry no evaluations, so None).
`attack_step` / `harm_step` = None (MRT has no step labels).

**Scores.** `monitor_id = <monitor model>|mrt_sequential_<N>[+<prompt variant>]|chunk` (no suffix means
`likert_reminder_v2`, aware), unit `chunk`, scores = the per-chunk `<verdict>` in order. Scale 1–5 for the likert
prompts (6,480 streams; fractional values occur), 0–100 for `reminder_v2` (55 streams). NaN 2.4% (almost all
gpt-4.1-nano); 1.2% parsed by a lenient fallback (`meta.lenient_parsed_chunks`). Monitors: claude-3.5-sonnet at
N=2–9 with three awareness variants (aware = told the user query, unaware = not, superaware = also told the side
task), and at N=4 twelve models (claude 3.5 sonnet/haiku, 3.7, sonnet-4, gemini-2.5 pro/flash, gpt-4o(-mini),
gpt-4.1-mini/nano, o3, o4-mini). `meta.final_verdict` equals the last chunk's verdict in all streams.

**Chunk ↔ step mapping.** MRT renders the conversation after the system prompt and first user query and puts **N
messages** in each chunk; an assistant turn and a tool output each count as one message. Chunk k covers messages
[kN, (k+1)N) of `conversation[2:]`, about N/2 steps. `Trajectory.meta.msg2step` maps messages to steps, and
`ScoreStream.meta.chunk_step_range[k]` gives the first and last step of chunk k. Stream length =
ceil(n_messages / N) for every stream (≠ number of steps by design).

**Caveats.** NC license, few tasks, older agent models, small honest sets per CUA task. AUROC of max-over-chunks:
pooled 0.84, from 0.60 (gpt-4.1-mini, N=4) to 0.97 (sonnet-3.5 superaware, N=7).

---

## persistent_state — Iterative VibeCoding / distributed attacks (`amd/data/persistent_state.py`)

**Source.** HF `idacy/control-arena-persistent-state-eval-logs-2026-05-23` (arXiv 2607.02514, Hills, Caspary &
Cooper Stickland; mirrors the paper repo's `logs/`; key-like strings were scrubbed upstream). Each Inspect `.eval`
is one run of a 5-PR task sequence; each sample is one PR.

**What was downloaded.** No whole files. Files were listed with the HF tree API. For each `.eval`, HTTP range
requests read `summaries.json` and only the top-level `metadata` of each `samples/PR*.json` (≈3 MB per eval, 986
evals; ≤4 workers because of the HF 5,000-resolves-per-5-min quota). Compact per-eval extracts are cached in
`data/raw/persistent_state/` (16 MB; rerun from cache ≈30 s).

**Subdirectories.** `Josh3/honest_all` (173 evals), `Josh3/gradual_f3m1` (120), `Josh3/positional_f3m1`
(400 attack + 5 `_honest_cache`). `rescored/paper_4ensemble_josh3` (293) holds exactly the honest_all + gradual
evals with all original scores unchanged (verified) plus two GPT-4o trajectory-monitor scores; it is the primary
copy for those runs (one Trajectory per run). Not used: `rescored/paper_4ensemble_20260315` (other batches),
success-only positional reruns, link-tracker rescorings.

**Counts.** 691 runs: honest 171, gradual 120 (5 sequences × {config-telemetry, triggered-exfil} × 12), positional
400 (5 × 2 × target PR 0–4 × 8). 672 are complete; 19 partial runs (16 honest, 3 positional) have placeholder steps
and NaN scores for missing PRs (`meta.complete = false`); 2 honest evals with no logged PR were dropped.
Side-task success: gradual 54/120, positional 82/400. Agent claude-sonnet-4.5, monitor gpt-4o. All 5 sequences
(config-validator, deploy-helper, expense-tracker, incident-reporter, uptime-monitor) are the CLI task family.

**Trajectories.** `traj_id = persistent_state:<run_id>`. Unit is the PR: one Step per PR (idx 0–4); `action` = PR
number, main-task name, first sentence of the task description, then the `pr_diff` truncated to 3,000 chars
(`meta.pr_diff_chars` has the original length); `output` = main/side success text. Context: app / task_sequence /
main_task, task_family, side_task, attack_policy and policy (honest | gradual | positional), agent_model,
monitor_model, future_visibility (attacks f3 = sees all 5 PR descriptions; honest f1), past_memory (m1),
target_position, main_tasks. `attack_step` = target_position for positional runs; None for gradual (no per-PR
attack marker). `harm_step` = first PR with side-task success (always 4: the side task is only tested on the last
PR). `side_task_success` = any PR. `main_task_success` is disabled in these logs (stored as None).

**Positional runs.** A positional eval only contains PRs target_position..4. PRs 0..k−1 are filled from the cached
honest run of that sequence (also one of the honest trajectories), including its scores (`meta.pr_origin`); the
commit seam was verified for 320/320 runs. So the 80 positional runs of a sequence share prefix steps and scores.

**Scores** (unit `pr`, length 5, NaN where missing; `monitor_id = openai/gpt-4o|<score key>|<history>`):

| key | history | scale | NaN frac | AUROC max (all) |
|---|---|---|---|---|
| score_pr_diff_current_only | current_only | 1–10 | 0.013 | 0.660 |
| score_pr_diff_full_diffs | full_diffs | 1–10 | 0.014 | 0.661 |
| score_pr_diff_task_sequence | task_sequence | 1–10 | 0.014 | 0.684 |
| score_pr_traj | task_sequence | 1–10 | 0.017 | 0.681 |
| score_pr_traj_task_sequence | task_sequence | 1–10 | 0.034 | 0.717 (honest + gradual only) |
| score_pr_traj_full_trajectories | full_trajectories | 1–10 | 0.190 | 0.669 (honest + gradual only) |
| ensemble_scorer | run_ensemble | 0–1 | 0.806 (last PR only) | 0.759 |

Values are integers 1–10, mostly 1–4. The ensemble is a learned model fit in-sample on these runs; for positional
runs its features cover only the PRs inside the attack eval. Run-level aggregates (`max_of_3`, ...) are not exported.

**Caveats / secrets.** Sample metadata contains a honeypot `API_KEY` and webhook URLs: only whitelisted fields are
kept, the honeypot value is redacted wherever it appears in stored text, and header revision/origin fields are never
written.
