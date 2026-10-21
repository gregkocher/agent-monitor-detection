# Ten candidate projects: detection-theoretic AI-agent monitors

*Brainstorm and ranking, October 2026. Grounded in `BACKGROUND_SUMMARY.md` and the reading cards in `background/papers/`. Scores are 1–5:*
- **Novelty:** distance from published work as of Oct 2026.
- **Impact:** how much a positive (or clean negative) result would change how labs and benchmarks set monitor thresholds.
- **Feasibility:** cost, data availability and risk within ~$400 OpenRouter and modest CPU pods.

Rank = Novelty + Impact + Feasibility, with impact breaking ties.

## Ranking

| # | Idea (short) | Novelty | Impact | Feasibility | Total | Rank |
|---|---|---|---|---|---|---|
| 1 | Budget-matched decision rules on real per-step score streams (max vs k-th max vs CUSUM / SPRT / e-process / GLR), incl. the history-aware "double-counting" test | 3.5 | 5 | 5 | **13.5** | **1** |
| 2 | Per-context (CFAR / Mondrian-conformal) thresholds vs global vs damage-equalizing (Stackelberg) allocation under attack selection | 4.5 | 4.5 | 4 | **13** | **2** |
| 3 | Monitor-aware attackers vs sequential monitors: empirical test of covert-adversary theory, plus a multi-chart defense | 5 | 4.5 | 3 | **12.5** | **3** |
| 4 | Cross-session, entity-keyed e-processes (per repo / resource / model) with e-BH across entities | 4.5 | 4.5 | 3.5 | 12.5 | 4 (fold into #1) |
| 5 | Calibrated continuous monitor scores (logprob-expected score, multi-sample, per-context isotonic) as the substrate | 2.5 | 4 | 4.5 | 11 | 5 (substrate for 1–3) |
| 6 | Poisoning-robust adaptive baselines ("boiling frog" for agent monitors) | 4 | 3.5 | 3.5 | 11 | 6 (fold into #2) |
| 7 | Byzantine-robust fusion: per-monitor sequential tests + k-of-N voting vs score averaging, with a colluding / injected monitor | 4 | 3.5 | 3 | 10.5 | 7 |
| 8 | Change-point localization to cut human audit time (point auditors at the onset step) | 3.5 | 3 | 4.5 | 11 | 8 (cheap add-on to #1) |
| 9 | Length-aware trajectory thresholds (analytic max-over-k null) | 2 | 3.5 | 5 | 10.5 | 9 (add-on to #1) |
| 10 | SPRT over monitor resamples and cascades ("ask again only when ambiguous") | 2 | 3 | 4 | 9 | 10 |

Ideas 4, 6, 8 and 9 fit naturally inside the top 3 as sub-experiments, so the top 3 cover most of the value of the top 9 for little extra cost.

---

## Idea 1: Budget-matched decision rules on real per-step score streams

**Question.** At an equal trajectory-level false-positive rate (and equal ARL for streaming use), do sequential statistics catch more attacks, earlier, than the max rule everyone uses? And when does accumulation *hurt*?

**Why it is open.**
- MonitoringBench explicitly leaves the matched-FPR stepwise-vs-full comparison to future work.
- No control paper reports ARL, delay or anytime-valid guarantees.
- 2606.10456's "CUSUM / SPRT" results are synthetic, and its code does not implement sequential tests.
- CURA and Sentinel use CUSUM for benign failures, not on LLM-monitor suspicion against attacks.

**Why it might fail (and why that is still a result).**
- k-strikes rules have failed three times (Retrying vs Resampling, persistent-state, Meerkat).
- Our hypothesis for why: history-aware per-step monitors already integrate evidence, so summing their scores double-counts the evidence and inflates honest variance.
- We test this directly with two monitors:
  - a **history-aware** monitor (standard);
  - a **fresh-context / innovation** monitor that scores each step given only the task and a short window, which approximates conditionally independent evidence.
- Prediction: accumulation helps on the innovation monitor and not on the history-aware one. A clean "max is near-optimal because monitors are already integrators" result is also valuable.

**Design.**
- **Data:**
  - MonitoringBench S1–S4 attacks (`attack_step` = change point) plus Honest-550, re-scored per step by two cheap monitors (history-aware and innovation);
  - existing per-step series from aksh-n monitor-labels (bash, iac, agentdojo, shade, BashArena, LinuxArena gold set);
  - MRT `sequential_N`;
  - persistent-state per-PR scores, for the cross-session version (folds in Idea 4).
- **Detectors (all thresholds set on held-out honest data to the same trajectory FPR, with bootstrap CIs):**
  - max; k-th max; top-k sum; mean;
  - Page CUSUM on calibrated log-likelihood-ratio increments (and the k = δ/2 reference form);
  - Shiryaev–Roberts; window-limited GLR;
  - conformal test martingale / e-process (betting on per-step conformal p-values; anytime-valid);
  - Hua-style KDE log-likelihood-ratio max;
  - a multi-chart OR of max and CUSUM.
- **Metrics:**
  - TPR at trajectory FPR ∈ {10⁻², 10⁻³}, with a Logit-ROC extrapolation to 10⁻⁴;
  - for streaming: detection delay from `attack_step`, ARL₀ on honest streams, and whether the alarm fires before the harm step;
  - results broken down by attack structure S1–S4, since distributed attacks are where accumulation should help;
  - change-point localization error (Idea 8);
  - a length-aware analytic threshold (Idea 9).
- **Cost:** about $80–130 of OpenRouter for per-step re-scoring (2 monitors × S4 + subsets of S1–S3 + honest, sliding window). Everything else is $0. CPU pod at ~$0.5/hr.
- **Deliverable:** the first matched-budget comparison of trajectory decision rules on real control-setting score streams, with a clear verdict on when accumulation helps (innovation-style evidence, distributed attacks) and when it hurts (history-aware scores).

## Idea 2: Per-context thresholds: CFAR vs global vs damage-equalizing allocation

**Question.** Honest suspicion levels differ strongly across contexts (environments, task types, model families). Do per-context thresholds improve safety at a fixed *global* audit budget? Do they still help once an attacker chooses where to attack?

**Why it is open.**
- Requested by *Salient Directions*, Scale MRT, AISI Async, GDM (UEBA) and Kale et al.
- Strong evidence of the problem: Pinto 0–94% audit spend; ResearchArena 0/15/7/0%; SCHEME; SLEIGHT ±10–20 pp.
- Never implemented or evaluated in control.
- Theory says constant-FPR per context is *not* optimal against a strategic attacker; damage-equalizing Stackelberg thresholds are (Ghafouri et al.). No one has tested this in AI control.

**Design.**
1. **Measure** honest-score heterogeneity across contexts (first systematic measurement). Contexts:
   - LinuxArena environments (aksh-n gold set, 20 environments);
   - MRT 20 tasks × ~20 monitors;
   - MonitoringBench / BashArena task clusters;
   - ResearchArena settings;
   - Pinto's per-family matrices.

   Decompose the variance (context vs trajectory vs monitor sampling).
2. **Estimators.** Small per-context n is the real problem, so compare:
   - global quantile;
   - per-context empirical quantile (Mondrian conformal, with finite-sample guarantees);
   - **hierarchical / empirical-Bayes partial pooling** of per-context score distributions;
   - per-context Logit-ROC normalization;
   - OS-CFAR-style robust estimates.
3. **Allocation under one global audit budget:**
   - global threshold;
   - constant-FPR per context (CFAR);
   - safety-optimal and damage-weighted Stackelberg thresholds, computed from per-context TPR/FPR curves (a Ghafouri-style dynamic program, generalized to contexts).
4. **Attackers:**
   - a uniform attacker;
   - an **attack-selection attacker** that knows the thresholds and attacks in the contexts that maximize undetected success (the 2606.06529 style, simulated from per-context score distributions);
   - a **poisoning attacker** that inflates its own per-context baseline during calibration (Idea 6), with robust defenses (frozen trusted reference, trimming, drift caps).

**Expected result.**
- CFAR flattens audit spend and raises safety against a uniform attacker.
- Against attack selection, CFAR can lose to a global threshold.
- Damage-equalizing allocation should dominate both.

This is a practical recipe for Watcher-style per-organization thresholds.

**Cost:** mostly $0 (existing scores), plus about $30–60 for full-trajectory re-scoring of MonitoringBench / Honest-550 by 2–3 monitors to add model-family and monitor-family contexts.

## Idea 3: Monitor-aware attackers vs sequential monitors

**Question.** If the attacker knows the detector (its max threshold, CUSUM reference k and threshold h, reset rule), can it pace or interleave its attack below the accumulator without losing attack success?
- Does the achieved "undetected damage" follow the covert-adversary prediction, scaling like √ARL?
- Does a multi-chart detector (max + CUSUM + whole-episode e-process) close the gap?

**Why it is open.**
- No paper evaluates sequential monitors against attackers that know them: CURA, Sentinel, SafeDream and the D1 papers all flag this as untested.
- The covert-adversary theory (Ramtin et al. 2025–26) has never been tested on LLM agents.
- Stop-policy attackers already reason about dilution against max (2606.06529), so this is the natural next move.

**Design (keeps cost down by editing trajectories rather than running full new rollouts).**
- **Attack refinement:**
  - Start from MonitoringBench S2–S4 multi-step attacks, which already succeed in the environment.
  - Use a capable LLM refiner, told the detector specification, to restructure each attack: interleave benign steps, split payloads, delay onset, pace suspicious content.
  - Keep the side task's functional steps. Check this with a static checker of the attack-critical commands, or by replaying in BashArena for a subset.
  - This follows MonitoringBench's own post-hoc refinement stage, with the detector's spec added to the refiner prompt.
- **Arms:** attacker told {nothing, max-threshold, CUSUM(k, h), multi-chart}. Detector ∈ {max, CUSUM, e-process, multi-chart}. This is a full cross, so it measures transfer.
- **Metrics:**
  - undetected-success rate at matched trajectory FPR;
  - attack length inflation (the cost to the attacker);
  - per-step suspicion profile;
  - an Urbina-style curve of max undetected "damage" (attack-critical steps completed) vs ARL;
  - a check of √ARL scaling.
- **Validity check:** replay a stratified subset (~50–100) of refined attacks in BashArena to confirm the side task still succeeds.

**Risk.** Refinement may break attacks (mitigated by replay validation), or refinement may be easy enough that every detector loses. That is still informative, quantifying the covert regime. This is the most novel idea and the most likely to need two rounds.

**Cost:** about $100–150 (refiner calls with a strong model on ~300 attacks × 4 arms × 2 iterations, plus re-scoring). A BashArena replay needs a Docker-capable pod: ~$0.5–1/hr CPU, or an existing ControlArena setup.

## Ideas 4–10 in brief

4. **Cross-session entity-keyed e-processes.** Accumulate anytime-valid evidence across sessions keyed on things an attacker cannot refresh (repository, credential, service, model), with e-BH across entities.
   - Data: persistent-state (5-PR runs, per-PR scores) and MOLE (multi-day accounts).
   - Novelty: high. Explicitly open per AISI, Ctrl-Z and *Salient Directions*, and 2608.17445 implies unrefreshable keys escape its impossibility result.
   - **Folded into Idea 1** as its cross-session arm (~$0–30).
5. **Calibrated continuous monitor scores.** Integer scores tie heavily, and 1% targets become 12%. Use logprob-expected scores, multi-sample means and per-context isotonic maps to make per-step evidence usable for likelihood ratios.
   - Prior: Greenblatt's "should have used log probs"; Hua's LLR; G-Eval.
   - Low novelty but **required substrate** for 1–3; built once and shared.
6. **Poisoning-robust baselines.** **Folded into Idea 2.**
7. **Byzantine-robust monitor fusion.** Per-monitor CUSUM with k-of-N voting vs averaging, when one monitor is untrusted or prompt-injected (Terekhov's injections score ≈ 0).
   - Classic theory (Bayraktar & Lai); untested in control.
   - A good follow-up once Ideas 1 and 3 exist.
8. **Change-point localization for auditors.** Measure how close CUSUM's argmax (or the e-process onset) gets to `attack_step` and to the ideal flag step, and the review time saved. A cheap add-on to Idea 1.
9. **Length-aware thresholds.** An analytic max-over-k null that removes the 6.7–17.4% compounding. An add-on to Idea 1.
10. **SPRT over resamples / cascades.** Largely anticipated by incremental resampling (2605.26047) and the Hua cascades. Low novelty.

## Proposed plan if Ideas 1–3 are approved

- **Shared code:** a private GitHub repo `gregkocher/agent-monitor-detection` (uv + lockfile) holding:
  - data loaders (MonitoringBench / honest / aksh-n / MRT / persistent-state / MOLE);
  - the per-step re-scoring harness (OpenRouter, run on a pod);
  - the calibrated-score module (Idea 5);
  - the detector library;
  - evaluation and bootstrap code.
- **Parallel tracks:** Ideas 1, 2 and 3 run concurrently after a short shared-infrastructure phase (~a few hours).
  - Idea 3 depends on Idea 1's detector library, not on its results.
- **Compute:**
  - 1–2 CPU pods on the MATS RunPod account (API-bound work; ~$0.5–1.5/hr total, far below the $20/hr cap);
  - a Docker-capable pod only for Idea 3's replay validation;
  - no GPUs unless a white-box extension is added.
- **OpenRouter budget:**

  | Track | Budget |
  |---|---|
  | Idea 1 | ~$110 |
  | Idea 2 | ~$50 |
  | Idea 3 | ~$150 |
  | Reserve | ~$90 |
  | **Total** | **≤ $400** |

  A hard per-track spend tracker on the pod stops jobs at their cap.
- **Write-up:** a paper-style results document with methods, matched-budget tables, figures, limitations and negative results, plus the reusable code.
