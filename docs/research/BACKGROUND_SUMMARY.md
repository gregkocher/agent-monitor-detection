# Background: how AI-agent monitors make decisions, and what is still open

*Literature summary, October 2026. Basis: 92 arXiv papers read in full (2009–Oct 2026) and 101 lab/blog/web sources (Redwood, Apollo, UK AISI, Anthropic, OpenAI, GDM, METR, LessWrong/AF, security vendors). Per-paper reading cards with exact numbers and quotes are in `background/papers/`. The earlier novelty red-team report is `CFAR CUSUM AI control monitors.md`.*

---

## 1. Bottom line

1. **The decision layer of AI-agent monitoring is almost untouched.** Research evaluations and deployed systems all do the same thing:
   - score each step (or the whole trajectory) with an LLM judge on an integer scale;
   - aggregate steps by **max**;
   - alarm above **one global threshold**. In research this is a percentile of pooled honest-run scores (1–2% FPR). In deployed products it is a fixed severity cutoff (Watcher: severity ≥ 6).

   Nobody reports average run length (ARL), detection delay, or anytime-valid false-alarm guarantees for an agent monitor.
2. **Sequential and stateful ideas exist, but in weaker forms or adjacent threat models:**
   - protocol-level adaptivity: decaying audit budgets, "three strikes", Wen et al.'s Bayesian macro-protocol;
   - LLM "memory" monitors that keep notes;
   - CUSUM for *benign* agent failures (CURA, Sentinel) and for *jailbreaks* (SafeDream, CPD);
   - anytime-valid tests for task correctness (e-valuator, Schirmer et al.).

   The one AI-control paper that claims CUSUM/SPRT on suspicion streams (2606.10456) uses synthetic streams. Its code does not implement sequential tests: its "CUSUM" is a non-sequential sum and its "SPRT" is a fixed-sample likelihood ratio.
3. **Simple numeric accumulation has repeatedly failed in control settings**, and any new method must explain why it would succeed where these failed:
   - k-strikes cuts safety from 61% to 44% at k=2 (Redwood, *Retrying vs Resampling*);
   - k-strikes fails in persistent-state control;
   - Bayesian score accumulation gives no gain (Meerkat);
   - Ctrl-Z found a KS-test trajectory statistic "brittle".

   The common reason: per-step monitors already read the full history, so their scores are cumulative judgments, and summing them double-counts.
4. **Per-context false-alarm control is clearly needed and has never been done.** Honest score levels vary strongly by environment, task, monitor, and agent model family:
   - a 1%-FPR threshold transfers to 0–94% realized audit spend across model families;
   - ResearchArena's per-setting FPRs at one threshold are 0/15/7/0%;
   - swapping the benign calibration set moves catch rates by 10–20 pp.

   But (a) fixing the operating point does not restore detection power under concept shift (Pinto), and (b) a threshold-aware attacker targets the loose-threshold contexts. In theory, optimal thresholds equalize worst-case *damage*, not FPR (Ghafouri et al.).
5. **Theory sets hard limits that the project must respect:**
   - Detection delay ≈ log(ARL)/KL-per-step.
   - A covert attacker who keeps its per-step KL ≈ 1/ARL cannot be caught sooner than the false-alarm clock by *any* detector. Its damage is then capped at ~√ARL.
   - Summing untrusted score streams is fragile; k-of-N voting restores robustness.
6. **Monitor-aware attackers are now standard in the literature:**
   - attack selection costs 20–28 pp of safety;
   - stop policies explicitly exploit max-aggregation ("buried in noise");
   - prompt injection drives monitor scores to 0 and ROC curves below the diagonal;
   - unlinkable identities defeat even ideal stateful defenders.

   A credible new monitor must be evaluated against an attacker that knows it.

---

## 2. Current practice: how monitors decide

| System / paper | Unit | Score | Threshold rule | Aggregation | Adaptive / stateful element |
|---|---|---|---|---|---|
| AI Control (Greenblatt 2023) | solution | LLM 1–10 (ensemble, honest-CDF-calibrated) | 2% honest FPR | n/a | binomial check on excess FPs; shutdown on confirmed backdoor |
| Ctrl-Z (2504.10374) | step (BashBench) | 0–9, max over sub-commands | honest percentile; **exponentially decaying budget** (safety 22% → 41.8%) | min(current, 3rd-highest so far) ("three strikes") | resampling; "time travel" acts like an SPRT continue-region |
| Wen et al. (2411.17693) | task | multi-monitor scores, bucketed | n/a (soft routing) | Bayesian credence across tasks | the only cross-task accumulator; "disastrous miscalibration" without bootstrapping |
| Games for AI Control (2409.07985) | task | TPR@FPR curves | thresholds indexed by (time, budget left); audit FPR > budget is Pareto-better | n/a | history-dependent protocols explicitly not evaluated |
| Control Tax (2506.05296) | task | 1–100 | pure honest quantile s(c,0); optimal allocations non-increasing in time | n/a | "patient attacker eventually succeeds" with unknown horizon |
| Combining monitors (Hua 2507.15886) | output | 2 monitors | **Neyman–Pearson LLR threshold** (KDE) | cascade | raw scores non-monotone in LLR ("winner's curse") |
| BashArena / LinuxArena | step | 0–10 / 0–100 | 99th pct honest per-step (or trajectory max) | any step > τ (max) | none |
| MonitoringBench (Apollo) | step & trajectory | 0–10 | 99th pct of 416 honest runs, per monitor (3.0–8.97) | max; 1% per step → **6.7–17.4% per trajectory** | none; matched-FPR stepwise-vs-full comparison "left to future work" |
| SHADE-Arena / Kutasov (2511.02997) | trajectory / turn | 0–100 | fixed 80 (~1%); 0.5% honest quantile | **second-highest** turn score | note-taking monitors *hurt* safety (−31%) |
| Retrying vs Resampling (2605.26047) | step | 0–100, max of 3 samples | 99.7th pct per step | max; **k-strikes hurts** (61 → 44%) | incremental resampling = sequential within a step |
| Async Control (AISI 2512.13526) | episode | random-forest aggregator | 99th pct | learned | honest-set poisoning shown; "stateful monitors between episodes" = future work |
| Attack selection (2602.04930, 2606.06529) | trajectory | 0–10 | honest pct | max | attacker abstains / stops; −20 to −28 pp |
| Watcher Live (Apollo) | action | severity 1–10 | **fixed** severity ≥ 6, triage → gateway cascade | per action | user-set thresholds per org |
| Claude Code auto mode | action | binary 2-stage | 8.5% → 0.4% FPR | per action | escalate after **3 consecutive / 20 total** denials |
| OpenAI internal monitor | conversation | severity tiers | n/a (async, within 30 min) | per conversation | none described |

**Standard metric:** TPR / catch rate at a fixed FPR (1%), safety-vs-usefulness at an audit budget, AUROC. Redwood's **Logit-ROC** result (TPR is linear in FPR in logit space, for a fixed policy/monitor/attack) is the best tool for extrapolating to realistic budgets (~1e-4).

---

## 3. Prior art closest to "sequential / adaptive monitors"

**Inside AI control:**
- **2606.10456 Distributed Detectability Band (Zhang & Gao, Jun 2026).** Marginal-preserving attacks put max/mean monitors at chance (AUC ≈ 0.52); "correlation" detectors reach 0.79–0.97. The cluster-C reader went through the code, and the paper's claims overstate what it implements:
  - the "CUSUM" is a non-sequential sum;
  - the "SPRT" is a fixed-sample likelihood ratio with a misspecified alternative;
  - the "HMM" is fit on the test trajectory itself;
  - results come from a single seed;
  - the "real traces" are 24-step text plans.
  
  Its useful theorem: any i.i.d. accumulator is powerless if the attacker matches the honest marginal.
- **Wen et al. 2024** (macro-protocol credence), **Ctrl-Z** (three strikes, resampling), **Kutasov** (2nd-highest score), **Retrying vs Resampling** (k-strikes fails; incremental resampling).
- **Stateful-by-LLM monitors** (link-tracker notes, TRACE evidence memory, MRT hierarchical summaries, Arbiter) and **cross-account clustering** (Brown et al. 2605.31593). None of these is statistical.
- **Distributed/multi-agent attack papers** (at least 6 in May–Oct 2026: FakeLab, MiniLab, SCHEME, MOLE, persistent-state, Salami). They show splitting attacks defeats per-unit monitors (MiniLab: 87% → 7% catch), with counter-findings that some joint sabotage stays loud (SCHEME).

**Adjacent threat models (port risk):**
- **CURA (2608.27808)** is the closest port. It runs a CUSUM (k=0.5) over z-scored agent behavior signals, with a Learn-then-Test threshold on successful runs (certified FPR), framed with AI-control citations, but for *benign task failures*. It reports 42% recall at FPR 0.066. A plain token-count baseline is nearly as good.
- **Sentinel (2608.02464):** ESN + CUSUM; per-deployment null; transfer collapse (AUROC 0.885 → 0.527).
- **SafeDream (2604.16824)** and **CPD (2605.19966):** CUSUM for jailbreaks. CPD uses a per-deployment median/MAD baseline, i.e. "CFAR + CUSUM" inside one prompt.
- **Anytime-valid** methods: e-valuator, Schirmer et al. 2607.02510 (a calibrated max threshold beats e-processes on delay), WATCH (conformal martingales, lists agents as future work), weight-exfiltration e-process (2610.11843; the only one with an attacker, a fixed codec).

**Gaps nobody has filled:**
- a true online sequential test on *real LLM-monitor suspicion streams* in a control setting;
- ARL/delay-calibrated thresholds;
- per-context (Mondrian/CFAR) nulls inside a sequential detector;
- cross-session accumulation for an untrusted model;
- any detector evaluated against an attacker that knows its parameters (k, h, reset rule, per-context thresholds).

---

## 4. Evidence on per-context calibration

**For:**
- Pinto 2607.06596: realized audit spend 0–94% (mean 27%) when a 1% threshold crosses model families; no 1% operating point exists for 3 of 4 families with a fixed-prompt monitor.
- SCHEME: one honest task with mean score 37–75 against a global p95 of 5–9 hijacks the pooled threshold.
- ResearchArena: per-setting FPR 0/15/7/0%.
- Trained monitors: per-dataset pAUROC 0.19–1.00; BashArena honest runs score 3–4 vs 0–2 elsewhere.
- MonitoringBench: firewall/sudo tasks inflate GPT-5's threshold to 8.97, and 82% of its misses are scoring/calibration errors.
- SLEIGHT: catch rate moves 10–20 pp with the benign set.
- Sentinel, CURA, MGT-B and CRA-Net thresholds all fail to transfer.
- Clio: topic-specific false-positive clusters in production classifiers.
- Deception probes: honest responses in deception-related scenarios exceed the 1% Alpaca threshold.

**Against / caveats:**
- Pinto: at matched FPR per family, an off-lineage *trained* monitor still catches 19% vs 41%. This is concept shift, which threshold normalization cannot fix. (Prompted monitors mainly suffer operating-point shift, which normalization can fix.)
- Ghafouri et al.: against a threshold-aware attacker, optimal per-context thresholds equalize damage, not FPR. CFAR hands the attacker the loose contexts, and attack selection (start policy) already picks tasks with "cover".
- Calibration data can be poisoned by the policy itself: Wen et al.'s baseline-poisoning warning; Async Control (threshold 30.2 → 31.5, FNR 7 → 9%).
- Per-context samples are small. With n honest runs the finest FPR is ~1/(n+1), and integer scores tie heavily: in the Ensembles paper, 3/4/5% FPR targets all yield 12.2%.

---

## 5. Theory the project must respect (cluster E1)

1. **Delay law:** delay ≥ log(ARL)/I, where I is the per-step KL of the monitor score; CUSUM attains it. Better monitors raise I; doubling ARL costs only ~log 2 / I more delay.
2. **Covert attacker** (Ramtin et al. 2509.17778, 2601.20022): if ARL·KL stays bounded, the optimal delay is Θ(ARL), so no detector catches the attacker before false alarms would. A mean shift is covert iff it scales ≤ ARL^(−1/2). Total damage is capped at Θ(√ARL) under a mean-shift damage model. The proofs assume a non-adaptive attacker.
3. **Minimax-robust CUSUM** (Unnikrishnan et al.): CUSUM on a clipped LLR designed at θ_min is exactly minimax for shifts ≥ θ_min; it costs about 2× delay on large shifts.
4. **Byzantine streams** (Bayraktar & Lai): summing one lying monitor into the statistic breaks it; k-of-N voting of per-monitor CUSUMs restores log-ARL delay.
5. **Strategic thresholds** (Ghafouri et al.): Stackelberg-optimal time/context thresholds equalize worst-case damage before detection.
6. **Boiling frog:** slow baseline poisoning works but is rate-limited if only non-alerting data updates the baseline. Frozen trusted references and drift caps help.
7. **Index statistics by step, not wall-clock** (otherwise the agent controls the decay).
8. **Evaluation hygiene** (Urbina et al. CCS'16): metric = maximum undetected impact vs time between false alarms, with the attack re-optimized per threshold. Static attack sets overstate catch rates.

---

## 6. Adversary results the project must survive

- **Attack selection / abstention:** −20 to −28 pp safety at a 1% audit budget (2606.06529). The GEPA-optimized attacker submits on 5.3% of tasks (2602.04930). Monitor randomization failed to help.
- **Stop policies** explicitly reason about dilution and "gradually escalating patterns" against max-monitors. Accumulation counters this directly, but a last-step-only stop recovers most of the effect.
- **Prompt injection into monitors** (Terekhov 2510.09462): an injected step scores ~0, so score-based sequential tests are blind to it. *Failed* injections produce extreme scores, which an accumulator could exploit. Min-aggregation is exploitable.
- **Unlinkable identities + retry feedback** (2608.17445): even ideal stateful defenders fail. Accumulate on keys the attacker cannot refresh: deployment, model, resource.
- **Training against a monitor** drives CoT-monitor recall to ~0 (Baker). Keep detectors out of the training loop.
- **Interleaving honest steps** resets CUSUM. An attacker holding exactly at drift k never accumulates (Urbina). A burst-and-pause attacker defeats reset-to-zero rules, whereas whole-episode e-processes keep evidence.

---

## 7. Data and testbeds

Full scan: `background/data_availability.md`, tested live 2026-10-20. Samples (~30 MB) and HF helper scripts are in `data/samples/`. The usable public data:

| Source | What it gives us | Per-step series? | Cost to start |
|---|---|---|---|
| **MonitoringBench** `neur26anonsub/ctrldataset2026` (CC-BY) | 2,644 successful attacks on 136 BashArena tasks; `attack_step` change-point; S1–S4 structure (S4 = 475 distributed) | no; per-trajectory max only | re-score per step: ~$15 (S4 + matched honest) to ~$85 (all) |
| **MonitoringBench-Honest-550** `palaestraresearch/...` (CC-BY) | 550 task-matched honest runs | no scores | included above |
| **LinuxArena** API `data.linuxarena.ai` (no login) + HF `anonymouslinuxarena/linuxarena-public` (CC-BY, 22k traj) | monitor sweep: **12 per-action monitors on the same 200 honest + 142 attack trajectories**, 20 environments, harm step; max-step AUROC 0.63 (gpt-4.1-nano) → 0.994 (opus-4-6) | **yes** (per action, 0–10) | $0 |
| **ScaleAI MRT** `ScaleAI/mrt` (CC-BY-NC) | ~9.6k honest / ~24k attack SHADE + CUA-SHADE transcripts over 20 tasks, ~20 monitor models | **yes**, `sequential_N` per-chunk verdicts | $0 |
| **aksh-n `*-monitor-labels`** (no license stated) | ControlArena bash/agentdojo/iac/shade, BashArena, LinuxArena gold set; Gemini-3.1-Pro streaming judge; ideal-flag step and point of no return | **yes**, per step | $0 |
| **Persistent-state VibeCoding** `idacy/...eval-logs-2026-05-23` | 5-PR runs (honest / gradual / positional), per-PR scores from several monitors | **yes**, per PR (cross-session) | $0–30 |
| **MOLE** `forgelab/mole` (Apache-2.0) | 150 accounts × 30 days, multi-day insider threats | per event / session | $0 (classical monitors); $20–55 for LLM scoring |
| Control OSWorld, ResearchArena, CTRL-ALT-DECEIT | per-setting scores | partly | $0 |
| METR MALT, SLEIGHT-Bench | gated (click-through) | no | — |

Not public: FakeLab, Mini-Lab, SCHEME, Stateful Online Monitoring.

Caveats:
- The MonitoringBench attack `.eval` headers leak a GitHub token. Don't republish raw headers.
- There are length and format confounds between honest and attack sets (`cmd` vs `command`; 22% of attacks lack `submit()`). Normalize these before comparing.

Benchmarks from the reading:
- **LinuxArena:** 20 heterogeneous environments, per-action scores, harm step t*; best for per-context baselines.
- **BashArena + MonitoringBench:** per-step honest and attack scores, documented FPR inflation; best for sequential-vs-max.
- **Control OSWorld:** running-max loses at low FPR (TPR@1% 0.85 → 0.49).
- **MOLE:** 150 accounts × 30 days, saved scores; cross-session.
- **SHADE-Arena:** heterogeneous but few honest runs per task.
- **SLEIGHT-Bench:** multi-session attacks.
- **Pinto's calibration matrices:** per-family transfer.

Many papers release no per-step scores, so expect to regenerate scores with our own monitor calls.

---

## 8. Open problems the sources name explicitly

- **Calibration transfer / per-context thresholds:** Lee *Salient Directions*, Scale MRT, AISI Async, MonitoringBench, Kale et al., GDM roadmap (UEBA at D4).
- **Stateful / cross-trajectory evidence:** *Salient Directions* ("every action … is a noisy signal about the same underlying variable"), AISI Async, Ctrl-Z, Stickland at ControlConf 2026, Anthropic, GDM roadmap, METR (sandbagging trends).
- **Score calibration:** MonitoringBench ("monitors detect most attacks but fail to calibrate … the lowest-hanging fruit"), BashArena, Greenblatt ("we should have used log probs").
- **Drift / reference-distribution updating:** Wen et al., Mallen (continual learning), Apollo agenda.
- **Diffuse threats:** Redwood and Anthropic deprioritize monitoring for them, in favor of training.

---

## 9. Source-reliability notes

- Web-page summaries (WebFetch) hallucinated CUSUM/SPRT content for 2607.07368 and 2607.02514, and per-context calibration for 2607.02510. All three were checked against full text; none contains those methods.
- 2606.10456's paper and code disagree (§3). Its claims should not be taken at face value.
- Wen et al. report different usefulness figures across versions (99.6% vs 98.4%). Kutasov's resample-then-defer safety is 89% in the abstract vs 80% in §3.1.
- Some 2026 papers are workshop-grade with small n (2606.06223, 2607.14570) or position papers (2604.23425, 2608.09087).
