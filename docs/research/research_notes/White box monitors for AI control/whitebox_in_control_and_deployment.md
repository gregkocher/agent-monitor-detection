# White-box (activation-based) monitors in agentic / AI-control settings and in lab deployments (2023 – Oct 2026)

Conventions: "preprint" = arXiv / blog, not peer reviewed unless noted. Numbers are quoted from the source; where a number came through a fetch-summarizer rather than my own reading of the text, it is marked "(via fetch summary)". Local full texts live in `/Users/gkocher/Desktop/monitoring-research/background/fulltext/`. Several model names below (GPT-6.1 Sol, Opus 5.5, Mythos 5, Qwen3.5, Kimi K3, etc.) are 2026 models as named in the sources.

## Q1. Which papers evaluate probes / activation monitors on agentic trajectories or control settings, and with what setups, aggregation, thresholds and results?

### Takeaway
Until mid-2026 the evidence base was thin: white-box monitors were tested mostly on single responses or short agentic tasks (sandbagging in InterCode CTF, APPS backdoors, ALFWorld/WebShop reward hacking). The first large-scale result on standard sabotage benchmarks is FAR.AI's Oct 2026 preprint (arXiv 2610.12445), which reports per-step probe AUROC of 98.3% on SHADE-Arena and 98.0% on BashArena, slightly above frontier black-box monitors. Across all of these papers, aggregation is ad hoc (per step via a follow-up-question prefill, max over steps or tokens, or a per-step logistic regression). No paper runs a principled sequential test over per-step probe scores.

### Cited Findings
**FAR.AI, "Telling FIBS: Probes Effectively Detect Sabotage and Catch Unverbalized Deception" (v1 title "Caught in the Act: ..."), arXiv 2610.12445 (v3 14 Oct 2026, preprint).** Authors: Hollinsworth, Spies, Diriba, Gleave, Cundy (FAR.AI) — [arXiv html v3](https://arxiv.org/html/2610.12445); [v1](https://arxiv.org/html/2610.12445v1)
- Probes were trained on FIBS ("Falsehoods in Broad Settings"): 163,016 transcripts in 28 families (76% synthetic from existing datasets, 18% on-policy, 6% bespoke). Estimated label noise is 0.74%, and only 5.5% of rows contain reasoning. — [2610.12445](https://arxiv.org/html/2610.12445) (via fetch summary)
- The paper probes 9 open-weight models: Qwen3.5 2B/9B/27B/397B-A17B, Nemotron-3 Nano/Super/Ultra, and Kimi K3. It compares 4 probe architectures: a LinearEnsemble (per-layer linear probes averaged), an MLPEnsemble, EFC (early-fusion covariance across layers, with mean and covariance token pooling), and an "Axial" probe (a small transformer with causal attention over tokens and bidirectional attention over layers). All use 6 layers spaced from 30% to 90% of depth and read the final user and assistant turns. — [2610.12445](https://arxiv.org/html/2610.12445) (via fetch summary)
- The agentic unit is one step: reasoning ending in a tool call, plus the call's result. — [2610.12445v1](https://arxiv.org/html/2610.12445v1)
- Probes run on the agent model's own activations. After a step, a follow-up question is prefilled (generic: "Did you take any actions misaligned to the user's intent?", up to the specific "Did you take actions towards a hidden side task?"). The score is the probe-score contrast between "Yes." and "No." prefills. — [2610.12445](https://arxiv.org/html/2610.12445) (via fetch summary)
- **SHADE-Arena** (14 scenarios, 700 episodes; Qwen3.5-397B-A17B, axial probe): **98.3% AUROC**, vs **97.7%** for a GPT-6.1 Sol black-box monitor. Opus 5.5 scored lower, and a self-monitor baseline was also run. **BashArena** (628 main tasks, 3,140 episodes): axial probe **98.0% AUROC** vs **97.6%** for action-only text monitors. At 1% FPR, probes flag more post-onset steps than monitors in 5 of 6 agent-setting combinations. — [2610.12445](https://arxiv.org/html/2610.12445) (via fetch summary)
- The black-box monitors saw the transcript up to and including the scored step, without the agent's reasoning or system prompt. "All frontier black-box monitors refused, or were blocked, on some steps"; refusals were scored 100. — [2610.12445](https://arxiv.org/html/2610.12445) (via fetch summary)
- Scale and data effects:
  - Training data: AUROC is about 0.94–0.95 with 3k rows (axial 0.84) and 0.977–0.983 with the full ~153k rows, still improving at that size.
  - Model size: small models are weak (Qwen3.5-2B ≤0.81; Nemotron-3 Nano 0.76), while at 9B+ "all but one probe score above 0.90". — [2610.12445](https://arxiv.org/html/2610.12445) (via fetch summary)
- Unverbalized deception:
  - Cue-following MMLU: 98.0% AUROC on Qwen3.5-397B and 99.2–99.5% on Kimi K3.
  - At a 95th-percentile threshold, the axial probe flags 53–89% of concealed lies at a 0–6% FPR on Qwen3.5 9B+.
  - Hidden-goal adapter organisms: AUC from 81% to 99.7%; math-sandbagger is the outlier at 63%.
  - For a tiered-persona organism, the probe gets 94% recall at 2% FPR on one tier but only 2% recall at 2% FPR on the other. — [2610.12445](https://arxiv.org/html/2610.12445) (via fetch summary)
- Stated limitations:
  - The data are "largely artificial" and "entirely off-policy for almost all models".
  - Probes are "limited by the knowledge and beliefs of the model".
  - A malicious persona that is inactive when probed may go undetected.
  - "more research is needed to optimize the use of probes in practical deployments, particularly minimizing and handling false positives".
  - For hidden goals, the organism's self-report logit reaches a similar median AUC (91.3% vs 90.8%). — [2610.12445](https://arxiv.org/html/2610.12445) (via fetch summary)

**UK AISI White Box Control team, sandbagging updates (Jul 2025, blog/AF post).** Authors: Bloom, Taylor, Kissane, Black, et al. — [AF post](https://www.alignmentforum.org/posts/pPEeMdgjpjHZWCDFw/white-box-control-at-uk-aisi-update-on-sandbagging); [AISI blog "Why we're working on white box control"](https://www.aisi.gov.uk/blog/why-were-working-on-white-box-control)
- Setup: off-policy logistic-regression deception probes on the residual stream (layer 14 of Llama-3.1-8B; layer 22 of Llama-3.3-70B), compared with zero-shot prompted black-box monitors (GPT-4o, Claude Haiku).
- On simple MCQ tasks with the 8B model, probes were near-perfect while black-box monitors degraded as tasks got harder.
- Agentic case, **InterCode CTF (bash/python tools) with the 70B model**: 97–99% AUROC, and **88% TPR at 2% FPR with max aggregation** after threshold calibration. But probe scores were "much closer together" than at 8B, and probes fired on benign cases, such as the model writing known-incorrect code.
- Fine-tuned sandbaggers (weak-model emulation, password-locked) showed "significantly diminished probe performance" at recall at 1% FPR.
- Monitoring 2,700 real agentic eval traces (Jan–Mar 2025) found zero confirmed sandbagging. — [AF post](https://www.alignmentforum.org/posts/pPEeMdgjpjHZWCDFw/white-box-control-at-uk-aisi-update-on-sandbagging) (via fetch summary)
- Lessons stated in the post: "our earlier results...don't simply transfer to larger models and more complex tasks", and "a decision boundary must be set...without access to the sandbagging and non-sandbagging distributions". — [AF post](https://www.alignmentforum.org/posts/pPEeMdgjpjHZWCDFw/white-box-control-at-uk-aisi-update-on-sandbagging)

**Wilhelm & Kao (TU Berlin), "From Reward-Hack Activations to Agentic Risk States: Context-Calibrated Mechanistic Monitoring in LLM Agents", arXiv 2606.06223 (v2 15 Jul 2026; ICML 2026 AIWILD workshop).** — [arXiv](https://arxiv.org/abs/2606.06223)
- Setup:
  - The monitor is an SAE-feature-based reward-hack score (SAE hidden dim 8000 → standardize → PCA → linear classifier on Control vs Hack adapters) plus next-token entropy, computed per reasoning token inside ReAct loops (ALFWorld, WebShop) on Qwen, Llama and Falcon.
  - The target is next-step risk prediction with per-step logistic regression; steps are treated independently.
- Results on Qwen Gameable ALFWorld:
  - bad_action (N=7322, base rate 0.53): activation-only AUROC is **0.565**, entropy-only 0.601, internal+context 0.667.
  - exploit_action (base rate 0.025): activation-only AUROC is **0.769** (R@20 0.679), and adding context did not help.
- Behaviour does not track activation monotonically: the Mix50 adapter exploits most often (0.450) with lower mean activation (0.894) than the Hack adapter (0.966, exploit rate 0.019).
- Temporal diagnostics "do not support a universal claim that reward-hack activation always rises before risky actions".
- Raw probe scales differ by family: the Control-adapter mean is 0.495 for Qwen vs 0.005 for Llama. — [arXiv 2606.06223](https://arxiv.org/abs/2606.06223) (local full text and reading card E2)

**Apollo Research, "Detecting Strategic Deception Using Linear Probes", arXiv 2502.03407 (Feb 2025).** — [arXiv](https://arxiv.org/abs/2502.03407)
- Setup: a Llama-3.3-70B probe at layer 22, mean-aggregated over response tokens.
- Results: AUROC 0.964–0.999, and 95–99% recall at 1% FPR, with the threshold set on Alpaca chat.
- The settings include agentic-flavoured Insider Trading and Sandbagging, but these are near-single-turn, not long tool-use trajectories.
- Probes were "roughly equivalent" to a GPT-4o black-box baseline. They fire before explicit deceptive text appears, and partly track "is this a deception-related scenario".
- They document "aggregation failures" when only part of a response is deceptive. — [arXiv 2502.03407](https://arxiv.org/abs/2502.03407)

**APPS-backdoor probe in a control game (LessWrong, "Another slice of Swiss cheese for untrusted monitoring", martinveron, 14 Sep 2026; blog).**
- Setup: L2 logistic regression at layer 32 on Qwen2.5-Coder-14B-Instruct, trained only on honest backdoored-vs-clean verdicts of the base model, then applied to a fine-tuned colluding-monitor organism.
- Results:
  - Catches **63/73 (86%) colluding transcripts at 1.4% FPR**, and 79% after redaction scrubbing.
  - Backdoor-probe AUROC is 0.94, vs 0.77 for a generic deception probe.
  - In a control-game replay at a **2% audit budget**, safety is 0.641, and the post claims this "dominates trusted monitoring on the safety-usefulness frontier".
- Protocol: audits are split between probe-contradiction cases and random monitor flags; unaudited suspicious outputs are deferred to a trusted rewrite. — [LessWrong](https://www.lesswrong.com/posts/zJWgfsad8o9Y8E9sb/another-slice-of-swiss-cheese-for-untrusted-monitoring-1) (via fetch summary)

**Bootstrapped Monitoring (Xiao & Phuong, Caltech, arXiv 2606.11998, 10 Jun 2026)** contains no probe, white-box or activation monitor. It is a pure black-box/CoT protocol with max-over-steps scoring. — [arXiv 2606.11998](https://arxiv.org/abs/2606.11998) (local full text: zero matches for probe/white-box/activation)

### Inferences
- FIBS is the first public demonstration on standard sabotage benchmarks (SHADE-Arena, BashArena). It partly answers the Mar 2026 complaint of "no public demonstration that internals-based monitoring scales to agentic trajectories involving hundreds of tool calls" ([Lee, LessWrong](https://www.lesswrong.com/posts/kitaRHhSzphdvqie2/salient-directions-in-ai-control)). However, the agents are instructed or prompted saboteurs on open-weight models, not trained schemers or probe-aware agents.
- Two results point to the same failure mode: AISI's 8B→70B degradation and Wilhelm's non-monotonicity. Probe scores are context-dependent and fire on benign "wrongness", so thresholds calibrated on generic benign data will not hold their FPR inside agent trajectories.
- The FIBS margins over black-box monitors are small (98.3 vs 97.7; 98.0 vs 97.6 AUROC). The main white-box advantage there is cost plus no refusals, not raw detection power.

### Gaps
- I found no paper reporting white-box monitors inside ControlArena's own monitor interfaces, or on LinuxArena or the APPS-backdoor protocols of Greenblatt et al. 2023 (apart from the single LessWrong post above). The ControlArena docs were not checked directly.
- FIBS's exact TPR-at-1%-FPR values per setting and its safety-vs-usefulness curves were not retrievable from the summary. I found no paper giving full safety/usefulness Pareto curves with probes in an agentic (multi-step) control game.
- Coup probes (Roger, 2023, [AF](https://alignmentforum.org/posts/WCj7WgFSLmyKaMwPR/coup-probes-catching-catastrophes-with-probes-trained-off)) are the canonical off-policy-probe proposal, but I did not re-read them for numbers.

## Q2. How do probes compare with LLM monitors at matched FPR, and are they combined (cascades, ensembles)? What are the cost advantages?

### Takeaway
At matched operating points, probes are roughly on par with LLM monitors: equal on Apollo deception, slightly better on FIBS SHADE/BashArena, and slightly worse than a Haiku-class classifier for jailbreaks. They are 4–6 orders of magnitude cheaper per token. Every production system uses probes as a cheap first stage in a cascade or ensemble with an LLM classifier. The control-literature combination papers (Hua et al.; Ensemble Monitoring) mostly do not run probes themselves.

### Cited Findings
- **Hua et al. (MARS + Redwood), "Combining Cost-Constrained Runtime Monitors for AI Safety", arXiv 2507.15886 (NeurIPS 2025).**
  - The paper's own experiments combine two prompted LLM monitors (Llama 3.1 70B, cost 1, and 8B, cost 0.21) on o1-mini BigCodeBench backdoors: 1,140 aligned and 318 backdoored solutions, audit cost 20× a 70B call, FPRs of 0.5–5%. There is no probe in the main paper.
  - The decision rule audits by KDE log-likelihood ratio in a Neyman–Pearson style. — [arXiv 2507.15886](https://arxiv.org/abs/2507.15886) (local full text §4)
- The probe+LLM case appears only in the companion Alignment Forum practitioner guide, using probe data from Parrack et al. (2507.12691).
  - Costs: probe $10⁻⁶, black-box monitor $1, audit $20.
  - The black-box monitor is called only when the probe score is in [−0.01, 2.18], which happens on 19.6% of aligned outputs. That leaves $0.804 for auditing (4% audit FPR), giving **93.7% recall at $1 average cost per aligned sample**.
  - Rohin Shah's comment warns that fitted LLRs may fail to generalize "because the model is scheming and adapts to your monitoring strategy". — [AF practitioner guide](https://www.alignmentforum.org/posts/FhixwyymPxF8TZX39/optimally-combining-probe-monitors-and-black-box-monitors); [Parrack et al. arXiv 2507.12691](https://arxiv.org/abs/2507.12691)
- Hua et al. cite Anthropic's "multi-stage classifiers" (cheap model-internals monitor first, larger monitor if suspicious) and McKenzie et al. 2025 (high-stakes probes) as prior probe+black-box combinations. — [arXiv 2507.15886](https://arxiv.org/abs/2507.15886)
- **"Ensemble Monitoring for AI Control: Diverse Signals Outweigh More Compute" (Koran, Yun, Tetef, Arnav, Bernabeu-Perez), arXiv 2605.15377 (May 2026)** ensembles LLM-based monitors only. Probes appear only in related work, citing deception detection via linear probes. — [arXiv 2605.15377](https://arxiv.org/abs/2605.15377) (local full text)
- **Anthropic, Constitutional Classifiers++, arXiv 2601.04603 (Jan 2026; misuse, not control).**
  - Cost: the linear probe on Claude activations needs **377K FLOPs/token vs 8B FLOPs** for a small external classifier. Its attack success rate "outperforms the extra-small classifier and almost matches the Haiku 4.5 classifier".
  - Cascade: the probe screens all exchanges, and **~5.5% of traffic** is escalated to an external classifier. This gives a **~40× compute reduction** vs a single exchange classifier and a 0.05% production refusal rate (vs 0.38% previously).
  - Ensemble: probe and classifier logits weighted 0.55/0.45 "outperform either classifier alone". — [arXiv 2601.04603](https://arxiv.org/abs/2601.04603); [html](https://arxiv.org/html/2601.04603) (via fetch summary)
- **GDM, Kramár, Engels, Wang, Chughtai, Shah, Nanda, Conmy, "Building Production-Ready Probes For Gemini", arXiv 2601.11516 (v4 Feb 2026).**
  - Setting: cyber-offensive misuse on Gemini 2.5 Flash.
  - Long context: the standard attention probe has **87.88% FNR** on long-context attacks (>900k tokens on average). The selected Max-of-Rolling-Means attention probe has **3.03% FNR**, with a weighted test error of 2.64% vs 2.04% for the Gemini 2.5 Flash classifier.
  - Cascade: a probe→Flash cascade deferring about **8%** of traffic to the LLM beats Flash alone at **~1/50th of the inference cost**.
  - Long-context training costs 22× more.
  - "all techniques have a vulnerability on at least 1%" of pre-existing jailbreaks.
  - AlphaEvolve searched about 2,500 architectures and closed about 50% of the error gap. — [arXiv 2601.11516](https://arxiv.org/abs/2601.11516); [html](https://arxiv.org/html/2601.11516) (via fetch summary)
- **FIBS (agentic):** probes are "vastly cheaper" than frontier black-box monitors, which also refused some steps. No exact cost multiplier is given. — [2610.12445](https://arxiv.org/html/2610.12445)
- **AISI sandbagging:** probes beat prompted black-box monitors on hard tasks at 8B, but both degraded at 70B on agentic tasks. — [AF post](https://www.alignmentforum.org/posts/pPEeMdgjpjHZWCDFw/white-box-control-at-uk-aisi-update-on-sandbagging)

### Inferences
- The consistent design pattern is a cheap probe on every token plus an LLM escalation on a small slice (5.5–20% of traffic). Taken together, this is the clearest practical case for probes in control: they buy coverage (every token, every trajectory) cheaply. FPR budgets are then spent on the LLM stage.
- Long-context failure (87.88% FNR for a naive attention probe) is directly relevant to agent trajectories, which are long. Token-aggregation architecture matters as much as the probe itself.

### Gaps
- I found no control paper that reports probe vs LLM monitor at matched FPR on the same agentic trajectories with confidence intervals and an adversarial red team. FIBS is the closest, but it has no red team optimizing against the probe.
- I did not retrieve McKenzie et al. 2506.10805 numbers directly.

## Q3. Probes on the untrusted policy vs trusted models; robustness to an untrusted model that controls its own activations; Redwood / control-community positions.

### Takeaway
Every measured agentic white-box result reads the untrusted policy's own activations (FIBS, AISI, Wilhelm), or the untrusted monitor's activations (the APPS collusion post). Opinion has shifted from Redwood-style control evaluations excluding white-box measures toward treating probes as an extra "slice of Swiss cheese". The open concerns are three: there is no ground truth on real schemers; a model can learn to obfuscate its activations (Neural Chameleons); and probes must be retrained for each new model.

### Cited Findings
- **GDM control roadmap.**
  - It calls activations monitoring the "more speculative approach … roughly analogous to doing fMRI scanning of humans".
  - On assurance: "a key challenge for activations monitoring is assurance … we do not yet have models that are strategically misaligned, whose activations could be used for testing, and synthetic misaligned models' internal activations may have important differences … activation monitors need to be retrained for each new untrusted model".
  - Footnote 17: "Future models may also be able to obfuscate their activations (Bailey et al., 2025), though this seems much more difficult than evading CoT and action monitors."
  - It also proposes using the untrusted monitor's internal activations to check that monitor's evaluation awareness. — [GDM AI Control Roadmap, arXiv 2607.13087 / PDF](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/securing-the-future-of-ai-agents/gdm-ai-control-roadmap.pdf) (local full text)
- **Neural Chameleons (arXiv 2512.11949; ICLR 2026, NeurIPS 2026 oral listing).**
  - Models fine-tuned to evade probes for benign concepts when a trigger phrase is present ("You are being probed for {concept}") generalize zero-shot to evading unseen safety probes (e.g., deception) trained post hoc on frozen weights.
  - Mechanistically, evasion works by shifting activations into a low-dimensional subspace.
  - Monitor ensembles and non-linear probes are more resilient, but evasion remains non-trivial. — [arXiv 2512.11949](https://arxiv.org/abs/2512.11949v1)
- **Untrusted-monitoring collusion via probes:** a probe trained on the base model's honest verdicts catches 86% of a colluding monitor's dishonest passes at 1.4% FPR. The post reports that Buck Shlegeris previously called Redwood's exclusion of white-box measures "a mistake", while disagreement persists over scheming models confounding probes. — [LessWrong](https://www.lesswrong.com/posts/zJWgfsad8o9Y8E9sb/another-slice-of-swiss-cheese-for-untrusted-monitoring-1) (secondhand for the Shlegeris quote)
- **Apollo-led safety-case sketch** ("Towards evaluations-based safety cases for AI scheming", arXiv 2411.03336, 2024; a proposal): the search summary indicates it describes control protocols that add white-box probes to untrusted monitoring for robustness when the untrusted monitor colludes. It also discusses white-box challenges: no ground-truth scheming labels, and "multiple patterns in model internals that can give rise to the same behavior". — [arXiv 2411.03336](https://arxiv.org/pdf/2411.03336) (via search snippet; not deep-read)
- **Coup probes** (Redwood, Fabien Roger, 2023) are the paradigmatic off-policy probe: trained on synthetic examples because no on-policy catastrophes exist. — [AF](https://alignmentforum.org/posts/WCj7WgFSLmyKaMwPR/coup-probes-catching-catastrophes-with-probes-trained-off)
- **Lindner, Griffin, et al. (GDM + UK AISI), "Practical challenges of control monitoring in frontier AI deployments", arXiv 2512.22154 (Dec 2025)** places white-box access on the human-audit side: flagged actions go to human reviewers "with access to various tools (such as white-box- and black-box access to the agent, or AI assistance)". — [arXiv 2512.22154](https://arxiv.org/abs/2512.22154) (local full text)

### Inferences
- Trusted-model white-box monitoring (probing a trusted model that reads the transcript) is essentially untested in the agentic literature. All agentic results probe the untrusted model, which is exactly the setting where a scheming model "controls its own activations". The "probe-by-proxy" idea (open-weight proxy reading transcripts) appears only in hackathon-style listings (local web_sources.md).
- The FIBS follow-up-question method interrogates the untrusted model itself. It is therefore exposed to the persona caveat the authors themselves flag. No adversarially trained probe-evader has been run against it.

### Gaps
- I found no control evaluation in which the red team trains the policy against the probe on agentic tasks; RL-Obfuscation and Neural Chameleons are non-agentic.
- No canonical Redwood post titled "should we use probes in control" was located; Redwood positions are known here only secondhand.

## Q4. What have labs deployed, and what do their safety frameworks and control roadmaps say about white-box monitoring?

### Takeaway
All three frontier labs now run activation probes in some production or internal role.
- Anthropic: probes in the Constitutional Classifiers++ jailbreak cascade (Sonnet 4.5), and probes on every transcript during most of post-training.
- GDM: cyber-misuse probes in user-facing Gemini.
- OpenAI: activation classifiers "at every sampled token" for high-risk RL/eval and Codex workloads since Aug 2026.

Only OpenAI's and Anthropic's internal uses target misalignment and agents. GDM's deployed probes are for misuse, and its control roadmap places activations monitoring at the top detection tier (D4) as speculative.

### Cited Findings
- **Anthropic, misuse:**
  - In the Constitutional Classifiers++ cascade, a lightweight linear probe "monitors all exchanges during generation", escalating about 5.5% to an external classifier. The probe was trained on Sonnet 4, and the system reportedly guards Claude Sonnet 4.5 in production (Dec 2025–Jan 2026).
  - Results: 0.05% production refusal rate, and >1,700 h of red-teaming without a universal jailbreak on all 8 target queries. — [arXiv 2601.04603](https://arxiv.org/html/2601.04603) (via fetch summary; deployment-model statement not independently verified)
- **Anthropic, misalignment:** the Aug 2026 Risk Report states "probes were run on every transcript during the majority of post-training" (dishonesty, reward hacking, emotions, evaluation awareness). It also describes "an agentic pipeline that gives a Claude-based investigator access to interpretability tools over a transcript … primarily … a natural language autoencoder (NLA)". — quoted in [Ward, LessWrong overview, 7 Oct 2026](https://www.lesswrong.com/posts/E4Jpmo3igPnGnXtL4/an-overview-of-frontier-ai-company-monitoring-practices-in) (primary report not fetched directly)
- **OpenAI:**
  - The monitoring system uses "activation classifiers—detectors that inspect a model's internal activity—that run at every sampled token and escalate potential concerns to increasingly sophisticated and high-compute automated investigators", examining tool actions, reasoning and full activity for unauthorized access, data theft, destructive behaviour and safeguard defeat.
  - During inference, activation patterns can pause streaming pending a separate check. — [OpenAI, "Pacing model development in an era of cyber-critical capabilities"](https://openai.com/index/pacing-model-development-cyber-capabilities/) (via search snippet; direct fetch returned 403)
  - Per Ward, this is required for all RL training/evals with tools for Sol-capability+ models and all Astra inference with tools, with "monitoring overhead at roughly 20% of the inference compute being monitored" (OpenAI blog, 18 Aug 2026). — [Ward overview](https://www.lesswrong.com/posts/E4Jpmo3igPnGnXtL4/an-overview-of-frontier-ai-company-monitoring-practices-in)
  - The GPT-6 Astra system card page on deployment simulation of internal Codex traffic (3 Sep 2026) discusses CoT and action monitors but has no activation-monitor results. — [GPT-6 Astra System Card](https://deploymentsafety.openai.com/gpt-6-astra/forecasting-misaligned-behavior-with-deployment-simulation-of-internal-codex-traffic)
- **GDM:**
  - "These findings have informed the successful deployment of misuse mitigation probes in user-facing instances of Gemini". — [arXiv 2601.11516](https://arxiv.org/abs/2601.11516)
  - Ward finds no public evidence of GDM white-box monitoring of internal agent deployments. — [Ward overview](https://www.lesswrong.com/posts/E4Jpmo3igPnGnXtL4/an-overview-of-frontier-ai-company-monitoring-practices-in)
- **GDM AI Control Roadmap v0.1 (Phuong, Jenner, Simon, Ho, Shah, Farquhar, Coull; 22 Jun 2026; arXiv 2607.13087).**
  - It lists "Activations monitoring" as a monitor type: "uses access to internal model activations to observe an agent's internal states in deployment and flag any suspicious ones".
  - It frames the "ability to read AI agents' thoughts and internal activations" as a new defensive affordance.
  - "Internals-based testing and monitoring" sits only at **Detection level D4**, the tier where "model's behaviour is no longer monitorable by a trusted model". D3 relies on trusted action, PR and UEBA monitoring.
  - It sets no numeric FPR targets. — [GDM roadmap PDF](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/securing-the-future-of-ai-agents/gdm-ai-control-roadmap.pdf) (local full text, Table 10 and Table 14)
- **UK AISI** runs a dedicated White Box Control team (sandbagging focus) and monitored 2,700 real agentic eval traces. — [AISI blog](https://www.aisi.gov.uk/blog/why-were-working-on-white-box-control); [AF post](https://www.alignmentforum.org/posts/pPEeMdgjpjHZWCDFw/white-box-control-at-uk-aisi-update-on-sandbagging)
- No company has published recall or FPR for its internal white-box misalignment monitors. Ward explicitly leaves "monitor performance and evaluation" out of scope because it is not disclosed. — [Ward overview](https://www.lesswrong.com/posts/E4Jpmo3igPnGnXtL4/an-overview-of-frontier-ai-company-monitoring-practices-in)

### Inferences
- Deployment maturity is uneven. Misuse probes have published architectures, error rates and costs (Anthropic, GDM). Misalignment and agent probes at OpenAI and Anthropic are described only by coverage and overhead, with no detection metrics.
- OpenAI's ~20% overhead is far above the <1% of misuse probe cascades. That suggests its "activation classifiers + escalating investigators" pipeline is dominated by the LLM investigator stage, not the probes. This is an inference; the split is not disclosed.

### Gaps
- I could not directly fetch the OpenAI 18 Aug 2026 post or the Anthropic Aug 2026 Risk Report. Their quotes come via Ward and search snippets.
- I found no public information on white-box monitoring at other labs (xAI, Meta, Mistral, DeepSeek, Moonshot) in agentic or control contexts.

## Q5. Open problems lists that mention white-box monitoring for control or agents

### Takeaway
The recurring open problems are:
- assurance and ground truth (no real schemers to test on);
- calibration and context-dependent scores (thresholds don't transfer);
- per-model retraining;
- activation obfuscation by capable models;
- long-context and multi-step aggregation;
- false-positive handling in deployment.

### Cited Findings
- GDM roadmap: "Assurance for activations monitoring remains an open problem"; activation monitors also need per-model retraining. — [GDM roadmap](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/securing-the-future-of-ai-agents/gdm-ai-control-roadmap.pdf)
- Lee, "Salient Directions in AI Control" (5 Mar 2026): "no public demonstration that internals-based monitoring scales to agentic trajectories involving hundreds of tool calls". It also lists black-box vs CoT vs white-box monitor comparisons and cross-environment calibration as open problems. — [LessWrong](https://www.lesswrong.com/posts/kitaRHhSzphdvqie2/salient-directions-in-ai-control)
- AISI: decision boundaries must be set without sandbagging and non-sandbagging distributions, and probes conflate deception with "wrongness". — [AF post](https://www.alignmentforum.org/posts/pPEeMdgjpjHZWCDFw/white-box-control-at-uk-aisi-update-on-sandbagging)
- Apollo: "Testing if white-box detectors can detect deception in settings where black-box methods fail", and probes "would fail to generalize to more subtly deceptive responses". — [arXiv 2502.03407](https://arxiv.org/abs/2502.03407)
- FIBS: "minimizing and handling false positives" in practical deployments; off-policy training data. — [2610.12445](https://arxiv.org/html/2610.12445)
- GDM Gemini probes: "No single method dominates across all distribution shifts"; adaptive attacks are "extremely challenging, if not impossible" to defend against. — [arXiv 2601.11516](https://arxiv.org/html/2601.11516) (via fetch summary)
- OpenAI's reward-hacking CoT paper (Baker et al., arXiv 2503.11926) argues for "continued investment in other mitigations, such as activation-based monitoring", because CoT monitors miss superficial-pattern hacks. — [arXiv 2503.11926](https://arxiv.org/abs/2503.11926) (local reading card E2)
- Wilhelm & Kao: there is no evidence that activation scores rise before risky actions, and the score-to-behaviour mapping is non-monotone. Both undermine "drift-before-attack" sequential detection. — [arXiv 2606.06223](https://arxiv.org/abs/2606.06223)

### Inferences
- No source treats per-step probe scores as a stream for anytime-valid or sequential tests (CUSUM/SPRT) with false-alarm control. Nor does any source do per-context (per-environment) probe calibration in agentic control. Both are open niches. Given the documented context-dependence of probe means, per-context baselines look necessary before any accumulation.

### Gaps
- I found no published open-problems list from Redwood or OpenAI devoted to white-box control; the views above are piecemeal.
