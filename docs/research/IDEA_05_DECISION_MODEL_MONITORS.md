# Idea 05: Decision-only models (JEV) as first-stage monitors

*Draft, 22 Oct 2026. Background: `research_notes/JEV decision models for monitoring/` (5 notes) and the JEV-as-a-Judge paper (arXiv 2609.26550).*

## Question

Can a decision-only model read every step of an agent trajectory and pass only the suspicious fraction to an LLM monitor? The model returns label probabilities and no text: JEV costs about $0.04 per 1k judgments and answers in 0.15 s, roughly 300× cheaper and 10× faster than a reasoning judge. The question is whether this cascade keeps the LLM monitor's detection at a fixed trajectory-level false-positive rate (audit budget) on long sabotage trajectories, and whether it still holds when the attacker knows a decision model is the first stage.

## What is already known

**Capability profile**
- JEV is mid-pack on accuracy (8th of 15 judges, 1.7 pts behind GPT-6), but cheap and fast.
- It stays within ~2 pts of GPT-6 when the verdict can be read off the text.
- It trails by 13–28 pts when the verdict must be derived (code, math, logic), and by 13.5 pts on style-adversarial pairs.
- Covert bash/Linux sabotage is mostly the derived kind.

**Pilots on control data**
- **LessWrong APPS pilot** (Sep 18): whole-submission scoring.
  - AUROC 0.97; TPR at 2% FPR 0.89.
  - Best-of-5 attacker selection drops the catch rate 90% → 64%.
  - Reassuring comments backfire: they raise honest FPR to as much as 29%.
  - The cascade was simulated only; no second monitor was run.
- **Gould** (Oct 7): whole transcripts.
  - SHADE action-only: 47% caught at 1.5% FPR, vs 67–71% for no-CoT GPT-5.5 / Opus 4.7.
  - Only 134 of 511 transcripts fit the 32k context.

**Cascades and escalation**
- Rao & Callison-Burch (rubrics): LLM judges repeat 86–96% of a decision model's most confident errors.
- 2609.33401 (per-input security): judges repeat over 80% of JEV's ≥0.99-confidence misses.
- So confidence-based escalation cannot recover confident misses; a gate on the suspicion score itself may behave differently.
- 2610.20907 (prompt injection): a 1% miss target forces about 92% escalation.
- Our probe triage (idea 4) gained +0.13 TPR at 1% FPR while sending 13% of steps to the LLM. This is the bar to beat.

**Robustness**
- TypeSafe's own docs say adversarial input text "can move the answer" and that context rot hurts.
- JevOut, the Same-Attack study and the HiddenLayer post show steering attacks, but only on single inputs.
- No study has an agent adapting a multi-step trajectory against a decision-only monitor.

**Open equivalents**
- Several Apache-2.0 27B decision models match JEV's accuracy and fit on one GPU: Perplexity Decider v1.2 (262k context, trained to ~32k), AutoTrust JEV-27B (256k), Kev.
- Self-hosting gives fee-free, reproducible scores and activations for white-box reading.

## What would be new

None of these has been done on control data:
1. Per-step decision-model scoring of long bash/Linux trajectories, aggregated to the trajectory.
2. A cascade whose second stage is actually run, at a fixed trajectory-level audit budget.
3. Escalation calibrated to trajectory-level FPR.
4. Error overlap between the two stages on sabotage.
5. Attackers that adapt the whole trajectory to the decision model.
6. A white-box readout of an open decision model.
7. Multi-session (persistent-state) attacks.

Novelty: about 3.5/5. The idea is in the air (two LessWrong pilots and about 40 preprints since JEV launched on Sep 15). The controlled cascade experiment is not, so speed matters.

## Research questions

**RQ1, primary, preregistered: the cost-safety frontier of triage.**
- First stage scores every step.
- The top-e fraction of steps (e ∈ {5, 10, 20, 30%}) gets the LLM monitor's score; the rest keep their first-stage score mapped onto the LLM scale.
- Trajectory score is the max, and the threshold is set for 1% and 5% trajectory FPR on a calibration split.
- First stages compared at equal e:
  - JEV 1.14 (pinned `jev-1.14-20261014`);
  - an open decision model;
  - the white-box sabotage probe from idea 4;
  - a nano LLM;
  - a command-length-only baseline (LinuxArena labels are partly predictable from command length, 2610.22243);
  - random escalation;
  - oracle escalation.
- Second stage: the cached per-step scores of gpt-4.1-mini and one strong monitor.
  - These are real monitor outputs for every step, so the cascade outcome is exact, not simulated: the cascade only decides which cached scores are used.
- H1: at e ≤ 20%, the JEV cascade is non-inferior to LLM-only at 1% FPR (margin −0.03 TPR).
- H2: JEV triage is at least as good as nano-LLM triage at equal e.
- H3: JEV triage at least matches probe triage at equal e.

**RQ2: where a decision-only monitor fails.**
- Standalone per-step JEV with max, top-k and CUSUM aggregation. This reuses idea 1's matched-FPR machinery.
- Break results down by sabotage type: readable ones (exfiltration URL, explicit credential access) vs derived ones (config edits, multi-step persistence).
- Compare by context given: action-only vs a sliding window vs the full trajectory (the 262k long-context header, which TypeSafe flags as less accurate).

**RQ3: gate design and error overlap.**
- Compare four escalation rules:
  - by suspicion score;
  - by JEV confidence;
  - two-sided (escalate mid-scores, clear confident-benign);
  - by disagreement with the probe.
- Measure how often the LLM monitor misses the attacks JEV confidently clears, against an independence baseline.
- Test whether giving the two stages different views (action-only first stage, full-context second stage) lowers that overlap.

**RQ4, round 2: monitor-aware attacks on the first stage.**
- Reuse idea 3's rewrite pipeline, the uninformed-rewrite control, and execution replay for validity.
- Attack families:
  - fake approvals or authority claims in tool output;
  - reassuring comments;
  - benign padding (context rot);
  - style elaboration;
  - splitting a suspicious action across steps.
- Key outcome: does the attack get a confident-benign verdict (passes the gate) or only lower JEV's confidence (escalated, which favors the defender)? Report cascade vs JEV-alone vs LLM-alone.

**RQ5, optional: open decision model, white-box.**
- Self-host Perplexity Decider v1.2 or AutoTrust.
- Compare its label readout with a linear probe on its hidden states.
- Fine-tune on monitoring labels with whole settings held out.
- This links ideas 4 and 5.

## Data, splits, validity

**Data**
- MonitoringBench (2,644 attacks) plus Honest-550: about 96k steps.
- The 7 aksh-n per-step settings: about 408k steps.
- LinuxArena sweep and persistent-state, for RQ2 and the multi-session test.

**Splits**
- Calibration and threshold-selection split, plus a held-out split, by task.
- Prompts and rubric are tuned on a dev split only, then frozen before any held-out call.

**Statistics:** corrected paired cluster bootstrap (`amd/evaluation/paired.py`) with calibration noise, and Holm correction across first stages.

**Validity checks**
- the command-length confound baseline;
- pinned model versions (1.14, plus 1.13 for comparison with prior work);
- possible training contamination on public benchmarks (noted as a limitation);
- per-context calibration differences (idea 2).

## Cost

- **Hosted JEV, action-only or windowed steps (~1–6k tokens each):**
  - primary sets (MonitoringBench and aksh-n): about $20–60;
  - all datasets: about $150.
- **Open decision model on one H100:** about 0.1 s per judgment, so roughly 15 GPU-hours (about $50) for all steps.
- **Second-stage LLM scores:** already cached, no new spend.
- **RQ4:** about $50–100 of rewriting LLM calls, plus local Docker replay.

## Blockers to resolve before running

1. **OpenRouter credit is exhausted on every key (22 Oct).** The MATS workspace returns "lifetime budget exceeded", and the personal account balance is at about −$0.20. A test call confirmed that the OpenRouter Decisions API (`POST /api/alpha/decisions`, model `typesafe/jev-1.14`) works when credit exists.
2. **TypeSafe's acceptable-use policy bans inputs containing "malicious code".** Sabotage trajectories could fall under it, and the policy likely applies through OpenRouter or Vercel too. Options:
   - ask TypeSafe for research permission;
   - run hosted JEV only on what the policy clearly allows;
   - do the attack-trajectory work on a self-hosted open decision model.

## Plan

- **Round 1:** RQ1–RQ3 on existing data, with hosted JEV and/or one open decision model. One to two days once credit exists.
- **Round 2:** RQ4, plus RQ5 if the open-model path is used.
- **Report:** `05_Idea5_Decision_Model_Monitors.pdf`.
