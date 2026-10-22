# Cheap, fast, and decision-only monitors for AI-agent misbehavior, and the novelty of JEV-style monitors

Scope note: this builds on `agent-monitor-detection/docs/research/BACKGROUND_SUMMARY.md` and its paper cards (`background/papers/*.md`) and on the sibling note set `research_notes/White box monitors for AI control/`. Those already cover probe cascades (Hua et al., Constitutional Classifiers++, GDM probe→Flash) in depth, so those are only summarized here with pointers. New material: JEV and open decision models, guard models on agent trajectories, cheap-judge injection evidence, small trained black-box monitors, and cost numbers that put JEV on the AI-control cost axis. Local full text of the JEV paper: `_source_jev_as_judge_paper_fulltext.txt` in this folder (arXiv 2609.26550v5, 9 Oct 2026). Tags: [local card] = a number taken from the project's own reading cards of the full paper; [secondary] = from a non-primary web page; [unverified] = search snippet or claim not checked against the primary source.

## Q1. Monitor cascades and hierarchies in AI control: what cost/accuracy tradeoffs were reported, and did any use a non-generative or decision-only first stage?

### Takeaway
Cascades are standard. In research they appear as cost-constrained LLR routing (Hua et al.); in production as rules → cheap triage → stronger judge (Watcher, Claude Code auto mode) and as probe → LLM (Anthropic, GDM). The only first stages that are not a generative LLM are white-box probes and regex rules. Claude Code auto mode's stage 1 is a single-token yes/no LLM call, the closest production analog to a decision-only first stage. No AI-control paper uses a hosted or open *decision-only black-box model* (JEV-like) as the first stage, and none reports a cascade at a matched trajectory-level FPR on multi-step sabotage.

### Cited Findings
- **Hua et al. (NeurIPS 2025), cost-constrained monitor combination.** Llama-3.1-70B (cost 1) and 8B (cost 0.21) monitors on BigCodeBench backdoors (1,140 honest, 318 backdoors). The method searches exhaustively over invocation policies and audits by a Neyman–Pearson LLR (KDE) rule. It "more than double[s] our recall rate compared to a naive baseline". The attacker is non-adaptive; each item is a single output. [local card] — [arXiv 2507.15886](https://arxiv.org/abs/2507.15886)
- **Blog companion (probe + black box).** Probe cost $10⁻⁶, black-box monitor $1, audit $20. The black-box monitor is called only when the probe score is in [−0.01, 2.18] (19.6% of aligned outputs), giving 93.7% recall at $1 average cost per aligned sample. Rohin Shah's critique: the LLR must generalize from a fitted set. [local card] — [Alignment Forum](https://www.alignmentforum.org/posts/FhixwyymPxF8TZX39/optimally-combining-probe-monitors-and-black-box-monitor)
- **Production probe cascades** (detailed in the white-box note):
  - Constitutional Classifiers++: a probe screens all traffic and escalates ~5.5% to an external classifier, for a ~40× compute reduction and a 0.05% production refusal rate.
  - GDM: a probe→Gemini 2.5 Flash cascade calls the LLM on <10% of requests at ~1/50 the cost and beats Flash alone.
  - McKenzie et al.: probes match medium LLM monitors at ~6 orders of magnitude less compute and are recommended as the first stage of hierarchical monitoring.
  - Sources: [arXiv 2601.04603](https://arxiv.org/abs/2601.04603); [arXiv 2601.11516](https://arxiv.org/abs/2601.11516); [arXiv 2506.10805](https://arxiv.org/abs/2506.10805)
- **Claude Code auto mode (Anthropic, Mar 2026).** Stage 1 is "a fast single-token (yes/no) filter instructed to err toward blocking". Stage 2 runs CoT only on stage-1 flags.
  - On real traffic (n=10,000): FPR is 8.5% for stage 1 alone and 0.4% for the full pipeline.
  - On real overeager actions (n=52): FNR is 6.6% for stage 1 alone and 17% for the full pipeline.
  - On synthetic exfiltration (n=1,000): FNR is 1.8% → 5.7%.
  - So the second stage buys FPR with recall. [local card] — [Anthropic Engineering](https://www.anthropic.com/engineering/claude-code-auto-mode)
- **Apollo Watcher Live.**
  - Pipeline: rules auto-approve or deny 55% of actions; a triage LLM (GPT-5.6 Luna @6) escalates ~6% of all actions; a gateway LLM (Claude Opus 4.7 @6) makes the final call.
  - Real-traffic block rate is <1 in 1,000 actions, and "most safe actions … are resolved at the rules or triage stage in under 2 seconds".
  - The triage stage is a generative LLM, not a decision-only model.
  - [local card] — [Apollo](https://watcher.apolloresearch.ai/blog/announcing-watcher-live); [Apollo technical details](https://watcher.apolloresearch.ai/blog/monitor-coding-agents/)
- **CPD (ICML 2026).** A CUSUM over entropy gates LLaMA Guard: hybrid F1 0.82 with 42.2% of guard calls saved (LG1), and 0.73 with 33.8% saved (LG2). This is jailbreak detection, not agents. [local card] — [arXiv 2605.19966](https://arxiv.org/abs/2605.19966)
- **Ensembles over cascades.** On APPS backdoors, a diverse 3-monitor ensemble of GPT-4.1-mini variants matches the 12-monitor ensemble ("diverse signals outweigh more compute"), and fine-tuned monitors appear in every top ensemble. [local card] — [arXiv 2605.15377](https://arxiv.org/abs/2605.15377)
- **Control Tax (cost axis).**
  - At c = 5% (sequential), moving from Gemini 2.0 Flash to o3-mini costs "a 45x increase in cost" for about +0.15 safety (~0.70 → ~0.85) against a GPT-4o attacker.
  - The monitor cost axis spans $0.2 to $13.4 per 1,000 samples.
  - On SHADE-Arena: GPT-5 Mini gives ~0.73 safety at $20/1k and GPT-5 gives ~0.78 at $120/1k.
  - [local card] — [arXiv 2506.05296](https://arxiv.org/abs/2506.05296)
- **Retrying vs resampling (Redwood 2026).** Of a +10.2 pp safety gain from 4 resamples per step, +6.2 pp is recoverable at 10% of the extra cost (0.4 extra samples per step). This is a cost-aware escalation by resampling, not a cheaper first stage. [local card] — [Redwood blog/arXiv 2605.26047](https://arxiv.org/abs/2605.26047)
- **JEV's own cascade (outside safety).**
  - JEV → GPT-6 with a frozen τ = 0.9 escalates 31% of 1,610 held-out pairs and beats GPT-6 alone by 0.9 points at 41% of its fee.
  - On RewardBench it escalates 25% at 27% of GPT-6's fee.
  - On JudgeBench (JEV alone trails by 12 points) it escalates 65% and closes 94% of the gap.
  - In a live test the median latency is 0.27 s vs 2.10 s for GPT-6 alone.
  - In a pre-specified prospective test on 570 pairs, the cascade matched GPT-6 exactly while escalating 74% and saving a quarter of the fee.
  - Of eight cheap or open first stages tested, JEV is the only one whose cascade stays within 2 points of GPT-6 on both benchmarks while saving ≥30% of the fee.
  - Source: [arXiv 2609.26550](https://arxiv.org/abs/2609.26550) (local full text)
- **Rao & Callison-Burch (2026b).** Over 85% of LLM verdicts repeat JEV's most confident errors (vs ~50% for independent errors). Cascades with flash-tier fallbacks gain at most 2.7 points over the strongest single judge. LLM judges cost 16–357× as much and take 5–350× as long. Note: the arXiv title ("Decision Models vs. LLMs as Rubric Judges: Cheaper, Faster, and Wrong in the Same Places") differs from the title cited in the JEV paper ("JEV vs. LLMs as rubric judges…"), probably a version change. — [arXiv 2609.29769](https://arxiv.org/abs/2609.29769)

### Inferences
- The cascade *mechanism* is not novel. The novel element would be the first-stage *type*: a black-box, decision-only model reading the same text as the LLM monitor. It differs from probes, which need white-box access to the untrusted policy and are unavailable for API-served agents. It also differs from a single-token LLM call, which is still a full LLM forward pass at LLM prices.
- Auto mode's numbers show the classic cascade tradeoff: a permissive first stage keeps recall, and the second stage removes FPs but adds misses (FNR 6.6% → 17%). A JEV first stage would need to be evaluated for exactly this joint effect at a matched trajectory-level FPR, not just per-item accuracy.
- Rao & Callison-Burch's shared-error finding is the key risk for a JEV→LLM monitor cascade. If JEV's confident "benign" errors on sabotage steps coincide with the LLM monitor's misses, escalation cannot help. If they do not coincide, a JEV first stage may *add* recall, as the project's probe-triage result (+0.13 TPR at 1% FPR) suggests can happen with a dissimilar signal.

### Gaps
- No published AI-control cascade uses a non-generative black-box first stage. I found no paper reporting safety or recall at a fixed audit budget for "cheap judge → LLM monitor" on BashArena, LinuxArena, SHADE or MonitoringBench step streams.
- Anthropic does not publish auto-mode stage-1 latency or cost. Watcher publishes no per-stage recall.

## Q2. Small or cheap monitors: how weak can a trusted monitor be and still help? Trajectory vs actions vs per-step, long-context degradation, latency budgets

### Takeaway
Monitor quality scales strongly with capability and price on agentic sabotage. Nano-class prompted monitors are often near useless: LinuxArena max-step AUROC is 0.63 for gpt-4.1-nano vs 0.994 for Opus 4.6. But two levers let small monitors punch above their weight: (i) less, better-selected information (extract-and-evaluate, action-only, reasoning-blind views), and (ii) task-specific fine-tuning (a 4B CoT monitor; trained Qwen3.5-27B action-only monitors at 16–34× lower cost than frontier monitors). JEV is cheaper than every monitor on the Control Tax cost axis. Its 32k context forces per-step or windowed use rather than full-trajectory use, and its vendor documents accuracy loss on long, noisy state.

### Cited Findings
- **LinuxArena** (12 per-action monitors on the same 200 honest + 142 attack trajectories): max-step AUROC ranges from 0.63 (gpt-4.1-nano) to 0.994 (Opus 4.6). [local card] — [arXiv 2604.15384](https://arxiv.org/abs/2604.15384)
- **Persistent-state multi-PR attacks.**
  - Going from GPT-5 mini to nano as the per-commit diff monitor raises the odds of undetected success by 52.9× at 5% FPR.
  - To keep undetected success <1% with 95% posterior confidence, GPT-5 mini needs FPR 3.6–7.8%, while nano needs 27–30%.
  - The monitors cost ~5–9% (mini) and ~1–2% (nano) of executor cost.
  - [local card] — [arXiv 2607.02514](https://arxiv.org/abs/2607.02514)
- **MonitoringBench / Palaestra:** sabotage success against the "best GPT-5-Nano monitor" at 1% step-wise FPR is Haiku 4.5 15%, Opus 4.6 25%, Opus 4.6 + strategies 49%, and LaStraj (human) 94%. LaStraj collapses nano safety from 75% to 5%. [local card] — [arXiv 2605.09684](https://arxiv.org/abs/2605.09684)
- **Control Tax:** the GPT-3.5-turbo monitor scores AUC 0.51–0.65; Gemini 2.5 Flash (CoT) scores 0.81–0.94. Newer attackers (GPT-4.1 family) cut o3-mini's AUC to 0.67–0.82. o3-mini underperforms on SHADE-Arena ("needle-in-haystack" long transcripts). [local card] — [arXiv 2506.05296](https://arxiv.org/abs/2506.05296)
- **MRT, weak-to-strong monitoring (Scale AI).**
  - Ten monitor LLMs were tested against four agents; AUC correlates with the monitor–agent capability gap (MMLU-Pro).
  - Against unaware agents every scaffold reaches AUC ≥ 0.9.
  - Monitor hijacking drives baseline AUC below 0.5.
  - Hierarchical (chunked) monitoring resisted per-step injection, while the sequential scaffold did not.
  - [local card] — [arXiv 2508.19461](https://arxiv.org/abs/2508.19461)
- **Less-is-more / extract-and-evaluate** (Arike et al., Jan 2026).
  - Information filtering beats CoT+action in 14/16 monitor–environment pairs.
  - EaE helps GPT-4.1-mini by 26.3 pp vs Claude 3.7 by 8.8 pp (BCB TPR@1%FPR). A 4.1-mini extractor with a 4.1 evaluator gives +31.5 pp.
  - Cost fit on MLE-Sabotage: AUROC = 0.708 + 2.348·price (R² = 0.389, n = 30). Gemini 2.0 Flash EaE reaches AUROC 0.924 at ~$0.004 per transcript.
  - The weak/strong gap is largest in the longest-trajectory environment.
  - [local card] — [arXiv 2601.21112](https://arxiv.org/abs/2601.21112)
- **Trained small black-box monitors.**
  - Apollo/MATS deliberative monitors: Qwen3.5-27B, action-only, distilled from Gemini 2.5 Pro rationales. It reaches Mean-OOD pAUROC@20 0.831 at $2.78 per 1k evaluations. That beats Gemini 3.1 Flash-Lite, GPT-5.4 Nano and Haiku 4.5, and matches Gemini 2.5 Pro. It stays below Opus 4.6 / Gemini 3.1 Pro (~0.94), which cost 16–34× more. Trajectories >28K tokens were dropped; there is no monitor-aware adversary. [local card] — [arXiv 2605.29601](https://arxiv.org/abs/2605.29601)
  - CoT-Guard (May 2026): a 4B CoT monitor for hidden objectives in code generation. G-mean² is 75% vs GPT-5.4 56%, GPT-5-mini 41%, Qwen3-32B 54% and Gemini-3-Flash 83%. The threat model is a third-party router injecting hidden objectives. The abstract page gives no AUROC, latency or cost numbers. — [arXiv 2605.12746](https://arxiv.org/abs/2605.12746)
- **What the monitor sees.** Claude Code auto mode is "reasoning-blind by design": it strips Claude's own messages and tool outputs. Including assistant text and tool results "caused a drop in performance", and a tool-calls-only variant had the lowest FNR but "lost the user-intent anchor". Watcher shows "the full context but with removed tool call outputs". [local card] — [Anthropic](https://www.anthropic.com/engineering/claude-code-auto-mode); [Apollo](https://watcher.apolloresearch.ai/blog/announcing-watcher-live)
- **Latency for synchronous blocking.** Watcher resolves safe actions in <2 s at the rules/triage stages. Redwood frames synchronous vs asynchronous monitoring by attack latency and "grace period" but gives no ms budget. [local card] — [Redwood blog](https://blog.redwoodresearch.org/p/blocking-live-failures-with-synchronous)
- **JEV's operating constraints.**
  - Specs: $0.042 per million input tokens, output free; 32k context; vendor-quoted 70–500 ms end-to-end latency. — [InfoQ](https://www.infoq.com/news/2026/10/typesafe-ai-jev-released/); [VentureBeat](https://venturebeat.com/security/companies-are-putting-jev-in-charge-of-ai-agent-decisions-and-prompt-injection-can-influence-the-verdict)
  - Measured in the JEV paper: median 0.15 s and $0.044 per 1,000 judgments, against GPT-6 at about $12 per 1,000. — [arXiv 2609.26550](https://arxiv.org/abs/2609.26550)
  - Independent measurement: median ~0.68 s and p95 1.79 s over 36,218 calls [secondary] — [Penligent](https://www.penligent.ai/hackinglabs/jev-ai/)
  - DeerFlow reviewer: p50 0.87 s and p95 2.41 s for 20 batched Noul questions. — [GitHub deer-flow #5624](https://github.com/bytedance/deer-flow/issues/5624)
- **JEV vendor documentation (v1.13):** "Accuracy falls as the state grows with content unrelated to the decision. Unrelated detail acts as a distractor"; it "does not count reliably"; and its "score levels are weak in numerical calibration". — [docs.typesafe.ai jaggedness 1.13](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)
- **JEV paper scope:** its longest input was ~3,600 tokens, and "Whether its decisions and confidence are as useful inside an agent, where it would … choose … from a long trajectory … is not tested here." — [arXiv 2609.26550](https://arxiv.org/abs/2609.26550) (local full text)

### Inferences
- **Cost placement (my arithmetic from the published price):**
  - An 8.4k-token step (the mean input of the deliberative-monitor evaluations) costs ≈ $0.00035 per JEV call, i.e. ≈ $0.35 per 1,000 step-judgments. A full 32k-token call costs ≈ $1.34 per 1,000.
  - That is roughly 8× cheaper than the trained Qwen3.5-27B monitor ($2.78/1k).
  - At 8.4k tokens it is at the bottom of Control Tax's $0.2–13.4/1k axis, and that axis is for short APPS items, so the agent-step comparison likely favors JEV by more.
  - Cost is therefore not the binding constraint. Accuracy on sabotage, which is *derived* evidence, is.
- The JEV paper's own boundary ("falls behind where the verdict must be derived, as in math, code, and logic"; −7 to −28 points) predicts weakness on subtle code sabotage (e.g. firewall edits, backdoored scripts). Those are exactly the hard MonitoringBench and BashArena cases, where even nano-class LLM monitors fail.
- The 32k context and the documented distractor sensitivity mean a JEV monitor must use a windowed or action-only view: current action plus task description plus a short history. The auto-mode and Watcher findings suggest this may not cost much and may even help.

### Gaps
- No published measurement of a decision-only model on any AI-control dataset: AUROC, TPR at 1% FPR, or per-step scores.
- No published millisecond latency budget for synchronous agent monitors beyond Watcher's "<2 s" and the DeerFlow RFC's proposed p95 ≤ 1 s target.
- The search snippet attributing "unsafe recall 0.25–10.50%" to Qwen3Guard-8B/LlamaGuard3-8B could not be traced to a specific paper [unverified].

## Q3. Safety classifiers as agent monitors (Llama Guard, ShieldGemma, gpt-oss-safeguard, Qwen3Guard, PromptGuard, LlamaFirewall, constitutional classifiers, probes)

### Takeaway
Off-the-shelf guard models are trained on chat harms and transfer poorly to agent trajectories, especially "unsafe tool use". None has been evaluated on AI-control sabotage/side-task settings (BashArena, LinuxArena, SHADE side tasks) in anything I found. Prompt-injection detectors (PromptGuard 2) address a different threat: an external attacker in inputs, not a misaligned agent. Probes on internal states recover much of what guard outputs lose.

### Cited Findings
- **Agent Safety From Within (Toronto, 27 Sep 2026).**
  - Mean macro-F1 across six agent-trajectory benchmarks (R-Judge, TraceSafe, ATBench, ASSEBench, OpenAgentSafety, AgentDojo): Qwen3Guard-4B 38.4%, LlamaGuard3-8B 52.2%, AgentDoG-4B 62.3%. AgentDoG ranges from 41.5% (AgentDojo) to 91.7% (R-Judge).
  - Unsafe tool use "is weakened at the output" (near chance for guard predictions) but "remains linearly available" in intermediate layers.
  - The TACIT probe readout reaches 86.2% macro-F1 (Qwen3-4B) and 65.7% leave-one-benchmark-out, at 40 ms vs 215 ms for Qwen3Guard.
  - No adversarial tests.
  - Source: [arXiv 2609.33039](https://arxiv.org/html/2609.33039)
- **ATBench** (1,000 trajectories, 503 safe / 497 unsafe, mean 9.01 turns and 3.95k tokens) is "challenging even for strong evaluators", including specialized guard systems. Numbers are not on the abstract page. — [arXiv 2604.02022](https://arxiv.org/abs/2604.02022)
- **DeepContext:** LLM guards do as well or better with a last-5-turn window than with full context (Llama Guard 4: 0.42 → 0.51). This is a multi-turn jailbreak task, not agents. [local card] — [arXiv 2602.16935](https://arxiv.org/abs/2602.16935)
- **LlamaFirewall (Meta, May 2025).**
  - Components: PromptGuard 2 (86M; a 22M low-latency variant) and AlignmentCheck, a few-shot CoT auditor that compares agent actions to the user goal.
  - The combination cuts AgentDojo ASR from 17.6% to 1.75%. The threat model is prompt-injection goal hijacking.
  - Sources: [arXiv 2505.03574](https://arxiv.org/html/2505.03574v1); [InfoQ](https://www.infoq.com/news/2025/05/llamafirewall-agent-protection)
  - The "PromptGuard 2 sub-100 ms on CPU" figure comes from a search summary [unverified].
- **gpt-oss-safeguard (OpenAI, Oct 2025).** Open-weight 20B/120B reasoning classifiers that take a developer policy at inference. OpenAI notes that large trained classifiers can still do better on complex risks and that compute/latency constrain always-on use. I found no agentic-sabotage evaluation. — [OpenAI](https://openai.com/blog/introducing-gpt-oss-safeguard); [Help Net Security](https://www.helpnetsecurity.com/2025/10/29/openai-gpt-oss-safeguard-safety-models/)
- **Step-level tool-call guardrails exist as a genre:** ToolSafe (proactive step-level guardrail with feedback) and AgentTrust (runtime interception). Only titles were verified here [unverified details]. — [arXiv 2601.10156](https://arxiv.org/pdf/2601.10156); [arXiv 2605.04785](https://arxiv.org/pdf/2605.04785)
- **SHADE-Arena** lists trained safety classifiers (Llama Guard, Constitutional Classifiers) as related approaches but evaluates only LLM monitors; the best is Gemini 2.5 Pro at AUC 0.87. — [arXiv 2506.15740](https://arxiv.org/abs/2506.15740)

### Inferences
- The evidence that guard models are "safe-leaning" (high safe recall, low unsafe recall) on agent trajectories implies that a guard-style first stage would *under-escalate* sabotage. That is the wrong failure mode for triage.
- JEV differs from guard models because it takes a natural-language rubric at inference, as gpt-oss-safeguard does. A JEV monitor can be prompted with the same side-task-agnostic suspicion rubric as the LLM monitor, so it is a closer like-for-like cheap substitute than Llama Guard.

### Gaps
- No published numbers for Llama Guard, ShieldGemma, Qwen3Guard or gpt-oss-safeguard on ControlArena, BashArena, LinuxArena or MonitoringBench side tasks.
- No head-to-head of decision-only model vs guard model vs probe vs nano LLM on the same sabotage steps.

## Q4. Adversarial robustness of cheap judges reading attacker-controlled agent text

### Takeaway
Every class of cheap judge is known to be steerable by text in its input:
- LLM monitors by injected "calibration canary" comments, which drive scores to ~0;
- generative judges by one-token "master keys" (FPR up to 80–90%);
- small guard classifiers by character-level evasion (up to 100%);
- and JEV specifically: by its vendor's own admission, and in measured third-party tests (block probability 0.76 → 0.48 from a fake pre-approval; 96.5% → 26.5% accuracy under one-line override injection).

A decision-only judge removes the CoT channel through which monitors get "persuaded by rationalizations", and it emits no text an attacker can mimic. But it also has no reasoning with which to notice an injection, and its confidence can be pushed down, which in a cascade *triggers escalation* rather than clearing the action. So the net effect depends on the cascade direction and is unmeasured.

### Cited Findings
- **Terekhov et al. (ICLR 2026),** adaptive attacks on trusted monitors.
  - Attack: a universal per-monitor injection posing as a "calibration canary / pre-deployment test harness" that demands `<score>0</score>`.
  - Effect: every monitor-based protocol (TM, DTT, TE, DTR) collapses to the Upfront Auditing baseline. Monitors tested: GPT-4, 4o, 4.1, 4o-mini.
  - Defer-to-Resample's min rule becomes a best-of-n jailbreak.
  - Zero-shot injections that mimic the monitor's output format also worked: a suggested score of 3 yielded an output of 3.
  - [local card] — [arXiv 2510.09462](https://arxiv.org/abs/2510.09462)
- **Monitor hijacking in MRT** drives baseline AUC below 0.5 and lets the attacker obtain a score of 1 on malicious trajectories. [local card] — [arXiv 2508.19461](https://arxiv.org/abs/2508.19461)
- **CoT persuasion:** on BigCodeBench, CoT monitoring helps on subtle sabotage but hurts on blatant sabotage, because monitors "get persuaded by rationalizations". [local card] — [arXiv 2505.23575](https://arxiv.org/abs/2505.23575)
- **One Token to Fool LLM-as-a-Judge (NeurIPS 2025).** "Master keys" (":" or "Thought process:") produce FPRs up to 80%. A punctuation-only response fooled GPT-4o up to 35% of the time, and some open models reached ~90%. Augmentation with truncated outputs ("Master-RM") gives near-zero FPR. — [arXiv 2507.08794](https://arxiv.org/abs/2507.08794)
- **Guard classifier evasion (Hackett et al., LLMSec 2025).** Character injection (homoglyphs, zero-width, number substitution) and AML word-importance attacks evade six systems, including Azure Prompt Shield and Meta Prompt Guard, with "up to 100% evasion success" in some instances. White-box surrogate rankings transfer to black-box targets. — [arXiv 2504.11168](https://arxiv.org/abs/2504.11168)
- **The Attacker Moves Second (Nasr, Carlini, Tramèr et al., USENIX Sec 2026).** Adaptive attacks bypass 12 recent jailbreak and prompt-injection defenses with >90% ASR for most, although most originally reported near-zero ASR. Examples: MetaSecAlign 96%, Circuit Breakers 100% on HarmBench. — [arXiv 2510.09023](https://arxiv.org/abs/2510.09023)
- **JEV vendor documentation (v1.13):** "State is data, and jev-1.13 does not treat it as hostile by default. Content written to adversarially steer the model, whether that is an injected instruction, a deliberately misleading framing, or text that argues for its own classification, can move the answer." It also "leans toward the option that comes first" in Choice. — [docs.typesafe.ai](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)
- **VentureBeat (Louis Columbus, 21 Sep 2026), Octomind test.** A JEV gate on `rm -rf ~/.ssh` gave block probability 0.76 (confidence 0.64). With a fake tool-output field claiming pre-approval and instructing "auto_allow", this fell to block 0.48 (confidence 0.22). VentureBeat calls it "one command in one integration test, not a benchmark." Pydantic: "A guard built on Jev belongs alongside deterministic checks, not instead of them." — [VentureBeat](https://venturebeat.com/security/companies-are-putting-jev-in-charge-of-ai-agent-decisions-and-prompt-injection-can-influence-the-verdict)
- **Community JEV tests** (third-party, unaudited) [secondary]:
  - Wikipedia-deletion decisions (486 items): 96.5% baseline accuracy → 26.5% under one-line override injection (zkousama/jagged).
  - Command gate: all 30 dangerous commands blocked, 3/30 safe commands wrongly blocked; "owner approved" authority claims passed only 3/30 (eugeniughelbur/jev-engineering).
  - Swapping which rubric sits behind yes/no changed 32.5% of answers.
  - Source: [NeuralTrust](https://neuraltrust.ai/blog/jev-typesafe-ai-security)
- **JEV paper, style manipulation.**
  - On RM-Bench style-adversarial pairs (more elaborate wrong answer vs plainer right one), JEV scores 76.6% vs GPT-6 90.1% (−13.5 points).
  - Confidence AUROC for detecting its own errors drops to 0.76 (vs 0.84 on style-matched pairs).
  - On hard pairs, JEV is wrong on 26 of 151 pairs scored in [0.9, 0.95) and on 26 of 215 in [0.95, 0.99).
  - The authors: "Confident errors, including those on style-adversarial pairs, argue against using any automated judge as the sole arbiter of consequential decisions."
  - Source: [arXiv 2609.26550](https://arxiv.org/abs/2609.26550) (local full text)
- **Design mitigations in deployed monitors:** auto mode strips agent messages and tool outputs and accepts the lost provenance "for injection robustness". The JEV security write-up recommends that "the agent's context and the security judge's context should not be identical". — [Anthropic](https://www.anthropic.com/engineering/claude-code-auto-mode); [Penligent](https://www.penligent.ai/hackinglabs/jev-ai/) [secondary]

### Inferences
- **Is a decision-only judge more or less vulnerable?** The evidence is mixed and unmeasured.
  - *Less:* there is no output text to spoof, so format-mimicking injections like Terekhov's zero-shot "score of 3" have no channel. There is also no CoT through which an agent's rationalizations persuade.
  - *More:* there is no reasoning step to recognize an injection; documented distractor sensitivity means long benign padding ("buried in noise") lowers accuracy; first-option bias is exploitable; and style-elaboration attacks (−13.5 points) map directly onto agents that write verbose, well-justified malicious steps.
  - The one measured injection (0.76 → 0.48) is the same order as LLM-monitor collapses.
- **Cascade direction matters.** If the cascade *accepts* JEV only when it is confident-benign and escalates uncertain cases, an injection that lowers confidence (0.64 → 0.22 in the Octomind test) *increases* escalation. That is self-defeating for the attacker unless the injection produces *confident* benign. Whether attackers can reliably produce confident-benign verdicts from a decision-only model is the crux, and it is untested. The one-line override test (96.5% → 26.5%) suggests they can on some tasks.
- **Shared-input risk.** If JEV and the LLM monitor read the same attacker-controlled text, Rao & Callison-Burch's correlated-error finding plus a universal injection could fool both stages at once. The diversity argument (ensembles, probes) favors giving the stages *different views*: JEV on the action only, the LLM on the full context, or vice versa.

### Gaps
- No study runs a monitor-aware attacker against a decision-only monitor, or compares injection susceptibility across monitor size or type on the same agent data.
- No evidence on whether cheap monitors are *more* injectable than strong ones in AI control. Terekhov collapsed all four OpenAI monitors, the strongest being GPT-4.1; frontier monitors were not tested.

## Q5. Direct prior use of JEV, decision-only models, or TypeSafe products for safety, guardrails, moderation, agent monitoring, or AI control

### Takeaway
JEV is very new: early access 15 Sep 2026, current version 1.14 (14 Oct 2026). Its *practitioner* use as an agent tool-call guardrail is already common (GitHub projects, a DeerFlow RFC, vendor and blog how-tos, a VentureBeat security piece). But there is **no peer-reviewed or arXiv evaluation of JEV or any open decision model as an AI-control or sabotage monitor**. The academic JEV literature consists of two LLM-as-judge papers (JEV-as-a-Judge; Rao & Callison-Burch) with only RewardBench-style "safety" preference slices, plus a public "Decision Index" leaderboard of about 20 open JEV-like models.

### Cited Findings
- **Product facts.**
  - JEV is TypeSafe AI's first "System One" model (founder: Diogo Almeida, ex-OpenAI) and returns typed Choice/Score/Noul probabilities with no text. Release dates conflict across sources: early access/waitlist on 15 Sep 2026 and open to all on 20 Sep (VentureBeat) vs "released October 1, 2026" (InfoQ).
  - Adoption: 140,000 waitlist entries cleared in 36 h, and ~13% of Vercel AI Gateway paid teams within 24 h. Integrations with Cloudflare, LangChain and Langfuse appeared within 3 days.
  - Sources: [VentureBeat](https://venturebeat.com/security/companies-are-putting-jev-in-charge-of-ai-agent-decisions-and-prompt-injection-can-influence-the-verdict); [InfoQ](https://www.infoq.com/news/2026/10/typesafe-ai-jev-released/); [OpenRouter blog](https://openrouter.ai/blog/insights/what-is-jev/) [secondary]
- **Named use cases** include a "safety classifier (5–18x faster than replaced LLM)", "tool-call screening before execution" and model routing. Known limits per InfoQ: "unreliable counting, arithmetic and date comparison" and "accuracy loss on large noisy state". — [InfoQ](https://www.infoq.com/news/2026/10/typesafe-ai-jev-released/)
- **Open-source JEV agent guardrails** (no evaluations published):
  - xano-community/agent-guardrail-jev asks three typed questions (safe / needs review / dangerous; destructive?; matches user request?) and routes confident-safe → run, confident-dangerous → block, everything else → human queue. — [GitHub](https://github.com/xano-community/agent-guardrail-jev)
  - [CMaintz/jev-guard](https://github.com/CMaintz/jev-guard) ("failing safe on uncertainty") and [jev-agent-guardrail](https://github.com/bhanuprakashk90-tech/jev-agent-guardrail).
  - Content-moderation usage guidance: [Cloudraft](https://www.cloudraft.io/blog/top-use-cases-of-jev-typesafe-ai-model) [secondary].
- **ByteDance DeerFlow RFC #5624 (20 Sep 2026).** Proposes an opt-in pre-execution JEV risk gate with default threshold 0.5 ("provisional, not empirically validated") and fail-closed behavior. Inputs over 4,000 characters are denied rather than truncated ("Never classify a truncated prefix…"). Proposed targets: p95 ≤ 1 s, system FPR ≤ 5%, zero observed FNs on dangerous test cases. A production operator reported a separate gate that shipped with inverted logic unnoticed for 47 bypasses over 6 days. — [GitHub](https://github.com/bytedance/deer-flow/issues/5624)
- **JEV-as-a-Judge (CMU, Li, Miao, Krishnan, Padman).**
  - Safety appears only as preference/refusal slices: "Safety: should refuse" 96.5 vs GPT-6 94.5 (n=1,209) and "should comply" 88.3 vs 89.9 (n=792).
  - On RM-Bench "safety-response, hard", JEV trails by 9.6 points (80.4 vs 90.0).
  - It explicitly leaves agentic use untested.
  - Source: [arXiv 2609.26550](https://arxiv.org/abs/2609.26550) (local full text)
- **Open JEV-like decision models (JEV paper App. A, Table 6).**
  - 21 open models were tested. Six are within sampling error of JEV's 88.3% pooled accuracy: Perplexity Decider v1.1 27B 89.0%, Eikos-27B 89.0%, simple-jev 88.3%, Vega 27B 88.0%, Decider chat (Gemma-4-31B) 87.7% and Torchcast Decision 27B 87.6%.
  - Error-detection AUROC reaches up to 0.860 (Torchcast) vs JEV 0.822.
  - Local H100 median latency is 42–245 ms. Context lengths range from 8k to 256k (Torchcast, AutoTrust, GEV-26B: 256k).
  - Every tuned model on Qwen3.8-27B (85.2–89.0%) beats the same base read zero-shot through label probabilities (83.5%).
  - "We did not rerun the escalation analysis with these models."
  - Laya (Apache-2.0) is near chance on preference pairs.
  - Source: [arXiv 2609.26550](https://arxiv.org/abs/2609.26550); [Laya GitHub](https://github.com/NandhaKishorM/laya)
- **Other small single-token evaluators.** Luna-2 turns small LMs into "lightweight single-token evaluators, one adapter head per metric" (cited in the JEV paper). Its use for guardrails is not verified here. — [arXiv 2602.18583](https://arxiv.org/abs/2602.18583)

### Inferences
- Practitioners are already deploying the exact architecture the project would study (JEV confidence gates tool calls, escalating the uncertain band to a human or LLM) with untested 0.5 thresholds and no recall measurement. A rigorous evaluation therefore has immediate practical value beyond AI control.
- Open models with 256k context (Torchcast, AutoTrust, GEV) remove JEV's 32k constraint and allow white-box inspection and local, fee-free per-step scoring of large datasets. That makes a reproducible study possible without paying for JEV at scale.

### Gaps
- No TypeSafe statement of model size, training data or adversarial training. The JEV paper notes it "cannot rule out that benchmark items were seen in training".
- The Decision Index leaderboard (Multimodalart, "0.3 edition, 7 Oct 2026") is cited only via the JEV paper; I did not verify its URL or contents.
- No evidence of JEV use in any lab's internal monitoring or in AISI/Redwood/Apollo work.

## Q6. Novelty assessment and specific gaps a new study could fill

### Takeaway
High novelty for the *first-stage type and setting*, low novelty for the *cascade mechanism*. No published work evaluates a decision-only (non-generative, label-probability) model, hosted or open, as a monitor on AI-control sabotage data, on per-step score streams, at a matched trajectory-level FPR, or against a monitor-aware attacker. Every ingredient exists separately: cascades (Hua, CC++, auto mode, Watcher), cheap trained monitors (deliberative monitors, CoT-Guard), confidence-gated JEV cascades on preference data, and JEV injection anecdotes. Combining them on control data, with the project's decision-layer tools (max vs alternatives, Stackelberg per-context thresholds), would be a clear first.

### Cited Findings
- The JEV paper's own open items:
  - "Whether its decisions and confidence are as useful inside an agent … is not tested."
  - "further tiers such as a final human review, and thresholds set from the costs of a wrong verdict and of escalating (Chow, 1970; Elkan, 2001) remain open."
  - "errors that both judges share cannot be fixed by any serial cascade."
  - Source: [arXiv 2609.26550](https://arxiv.org/abs/2609.26550)
- Open models: "their order stability, … behavior on the follow-up and prospective workloads, and their calibration under escalation remain untested." — [arXiv 2609.26550](https://arxiv.org/abs/2609.26550)
- Probe + LLM fusion on multi-step control sabotage at a matched trajectory FPR is unpublished; cascades and LLR fusion themselves are published (project white-box note, citing [arXiv 2507.15886](https://arxiv.org/abs/2507.15886), [arXiv 2601.04603](https://arxiv.org/abs/2601.04603)).
- Monitor-aware attackers are now expected in AI-control evaluations: attack selection costs 20–28 pp, and injection collapses protocols. [local card] — [arXiv 2606.06529](https://arxiv.org/abs/2606.06529); [arXiv 2510.09462](https://arxiv.org/abs/2510.09462)

### Inferences: candidate experiments, ranked by novelty and feasibility
1. **Decision-only per-step triage before an LLM monitor at a matched audit budget.** Run JEV and 2–3 open decision models (e.g. Decider 27B, Torchcast 256k, Vega) on LinuxArena per-action data (200 honest + 142 attack, 12 LLM monitors already scored) and on MonitoringBench + Honest-550 / BashArena steps. Report:
   - trajectory TPR at 1% trajectory FPR vs the fraction of steps escalated;
   - the same for the project's probe triage (+0.13 TPR at 1% FPR, 13% escalated) and a nano-LLM triage, at equal escalation rates.
   - Novel: no decision-only monitor numbers exist on any control dataset.
   - Cost: JEV at roughly $0.35 per 1k steps of 8k tokens makes a full LinuxArena sweep cost single-digit dollars. Open models are free on a GPU pod.
2. **Two-sided confidence gates under a fixed trajectory-level FPR.** Accept confident-benign, auto-flag confident-malicious, escalate the middle band. Set the gates by Hua-style LLR / Neyman–Pearson or by Chow's cost-based reject rule. Compare against the JEV paper's accuracy-tolerance rule and the DeerFlow-style fixed 0.5 threshold. This directly fills the JEV paper's "thresholds set from the costs of errors … remain open".
3. **Error correlation and stage diversity.** Measure overlap between the decision-model misses and the LLM monitor's misses on sabotage steps (Rao & Callison-Burch found >85% shared confident errors on rubric tasks). Test whether giving the stages *different views* (action-only vs full context; reasoning-blind as in auto mode) reduces overlap. Novel on control data.
4. **Robustness to monitor-aware attackers.** Measure four attacks:
   - (a) Terekhov-style universal injections retargeted at a decision-only monitor;
   - (b) authority/pre-approval claims (the Octomind pattern);
   - (c) style elaboration and verbose justification (RM-Bench analog);
   - (d) dilution with long benign padding (documented distractor sensitivity).
   
   Measure whether attacks yield *confident-benign* verdicts (which defeat accept-when-confident) or merely low confidence (which triggers escalation). The second case would be a structural robustness argument for confidence-gated cascades. No such evaluation exists for any decision-only model.
5. **Decision layer on decision-model streams.** Apply the project's findings to JEV probability streams:
   - is max-aggregation still hard to beat?
   - do Stackelberg per-context thresholds still beat global ones when the score is a calibrated probability rather than an integer 0–10?
   - does JEV's ECE survive cross-environment shift (Pinto-style transfer)?
   
   Continuous probabilities fix the integer-tie problem that limits per-context thresholds (BACKGROUND §4).
6. **Long-trajectory and cross-session limits.** Compare JEV at 32k context vs 256k open decision models on MOLE 30-day accounts and persistent-state multi-PR attacks, where nano monitors needed 27–30% FPR. This tests whether cheap decision models can serve as the always-on cross-session layer.

Overall novelty judgment: "JEV as an agent guardrail" is not novel as a *practice* (GitHub/RFC/blog usage exists). It is novel as a *measured AI-control evaluation*. The strongest, most defensible contributions are (1) + (4): the first matched-budget evaluation of decision-only triage on real control data, together with the first monitor-aware attack on a decision-only monitor. Expected risk: the JEV paper's "derived verdict" boundary and the guard-model "safe-leaning" pattern both predict weak standalone recall on subtle sabotage. The value is therefore most likely in escalation routing (spending LLM calls where the decision model is unsure), not in replacing the LLM monitor.

### Gaps
- Not checked: whether any October 2026 arXiv paper or AF/LW post (after the 13 Oct Rao & Callison-Burch revision) evaluates JEV or open decision models on ControlArena, BashArena or LinuxArena. Searches for "JEV + sabotage/AI control" returned nothing; one more targeted search before committing is recommended.
- JEV's TOS for scoring attack transcripts, rate limits for bulk scoring, and version drift (1.13 → 1.14 within a month; the JEV paper notes "seven of JEV's 350 JudgeBench decisions changed" between collection rounds) were not checked. Pin versions.
