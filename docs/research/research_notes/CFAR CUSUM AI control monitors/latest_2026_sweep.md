# Latest (Jan–Oct 2026) AI control and agent-monitoring work: scooping-risk sweep for sequential/adaptive monitors

Sweep date: 2026-10-20. Method: WebSearch (extended mode), WebFetch of arXiv abstract pages and org blogs, and direct arXiv API queries (export.arxiv.org, sorted by submission date, filtered to papers submitted on or after 2025-10-01). Flag legend used below:
- **[SEQ]** sequential/temporal monitoring across steps, sessions or agents; suspicion accumulation
- **[STAT]** CUSUM / SPRT / e-values / e-processes / anytime-valid / change-point
- **[THR]** adaptive or per-context thresholds; monitor calibration or normalization; calibration transfer
- **[DIST]** multi-step / distributed / gradual attacks against monitors
- **[LONG]** cross-session or long-horizon monitoring of persistent agents
- **[DRIFT]** "monitoring the monitor", drift

## Q1. What did Redwood, Apollo, UK AISI, Anthropic, OpenAI, GDM, METR, FAR.AI and academic groups publish on monitoring in 2026?

### Takeaway
2026 output on control monitoring was large. Several items already sit squarely on sequential/stateful monitoring: a stateful cross-account online monitor (UPenn, May 2026), a stateful cross-PR "link-tracker" monitor (Hills/Caspary/Cooper Stickland, Jul 2026), an explicit CUSUM/SPRT/HMM-LR evaluation against "marginal-preserving" distributed sabotage (Jun 2026), and several multi-agent "fragmentation effect" papers (UK AISI/GDM, Jul and Oct 2026). Lab outputs (OpenAI Mar 2026, GDM roadmap Jun 2026, Anthropic online/offline numbers Aug 2026) describe per-trajectory monitors with fixed escalation and name cross-trajectory, model-level detection as a goal. None of them publishes a formal sequential test.

### Cited Findings

**Redwood Research (and Redwood-affiliated authors)**
- 2026-01-30: "Monitoring benchmark for AI control" (LessWrong; Monika J, Angel Martinez). 428 static attack trajectories. Key finding: "most monitors detect most attacks but fail to calibrate suspiciousness enough to catch them", so calibration is named as the main weakness. Uses fixed FPR budgets taken from honest baseline distributions. **[THR]** — [LessWrong](https://www.lesswrong.com/posts/X8qTKsGcnsTFrqM96/monitoring-benchmark-for-ai-control)
- 2026-02-04: "Attack Selection Reduces Safety in Concentrated AI Control Settings against Trusted Monitoring" (Schaeffer, Khandelwal, Tracy). Safety is "significantly more sensitive to FPR than TPR". Attack selection drops safety from 99% to 59% at a 0.5% audit budget. **[THR]** (threshold/FPR sensitivity) — [arXiv 2602.04930](https://arxiv.org/html/2602.04930v1)
- 2026-03-20 to 22: AI Control Hackathon 2026 (Apart Research with Redwood). 125 submissions. Themes included attacks "distributed across multiple independently-monitored sessions" and non-LLM GNN code monitors (0.946 AUC). Winner: "Omission Attacks". **[DIST]** — [Apart](https://apartresearch.com/sprints/ai-control-hackathon-2026-03-20-to-2026-03-22)
- 2026-04-12: "Logit ROCs: Monitor TPR is linear in FPR in logit space" (Staley, Bhatt, Stastny). Benign and attack scores are roughly logistic. Validated on BashArena with partial support from LinuxArena. Trajectory TPR is defined via the **max** per-message suspicion (no summing across steps). Realistic audit budgets are around 1e-4. **[THR]**. This is directly relevant to tail calibration — [Redwood blog](https://www.redwoodresearch.org/blog/logit-rocs-monitor-tpr-is-linear)
- 2026-04-16: LinuxArena (Tracy et al.): 20 live environments, 1,671 main tasks, 184 side tasks, and the LaStraj human attack dataset. Opus 4.6 gets about 23% undetected sabotage against a GPT-5-nano monitor at a **1% step-wise FPR** — [arXiv 2604.15384](https://arxiv.org/pdf/2604.15384); [Redwood blog](https://blog.redwoodresearch.org/p/introducing-linuxarena)
- BashArena (637 sysadmin tasks, 4 sabotage objectives) blog post "BashArena and Control Setting Design". Date not verified in this sweep — [Redwood](https://www.redwoodresearch.org/blog/basharena-and-control-setting-design)
- 2026-05-10: MonitoringBench (Jotautaitė, Martinez, Matthews, Tracy). 2,644 refined BashArena attack trajectories. Opus-4.5 monitor catch rate falls from 94.9% to 60.3% on refined attacks — [arXiv 2605.09684](https://arxiv.org/html/2605.09684v1); [LW](https://www.lesswrong.com/posts/2YyEQhFRyaBCgfRWd/introducing-monitoringbench)
- 2026-05-25: "Retrying vs Resampling in AI Control" (Lucassen, Kaufman). In BashArena, five samples per step with audit on **max suspicion** raises safety from 61% to 71% at a 0.3% audit budget — [arXiv 2605.26047](https://arxiv.org/pdf/2605.26047)
- 2026-06-08: "Diffuse AI Control on Fuzzy Tasks" (Terekhov, Gulcehre, Hebbar, Benton). Defines diffuse control as "mitigating risks from AI sabotage distributed over long deployment horizons". The method is adversarial prompt optimization of a weak scorer, not sequential detection. **[LONG]** (framing only) — [arXiv 2606.08892](https://arxiv.org/abs/2606.08892)
- Redwood blog posts on Screwtape (adversarial transcript editing for monitor red-teaming), "Continual Learning Might Make Your Blocking Monitors Nearly Useless", and "AI Swarms Are Starting to Pose Indirect Takeover Risk". The archive fetch returned 2024 dates, which look wrong given the 2026 context (Hugging Face incident). Exact dates are unverified — [Redwood archive](https://blog.redwoodresearch.org/archive); [Screwtape](https://blog.redwoodresearch.org/p/screwtape-adversarial-transcript)

**Apollo Research**
- 2026-05-08: "A scalable monitoring research agenda". Proposes spending on the order of $10–100M on coding-agent monitors. Directions: data generation at scale, comparing techniques (hierarchical, ensembles, agentic, debate, fine-tuning), automated adversarial red-teaming, and automated research infrastructure. The fetch found **no explicit discussion** of thresholds, FPR, per-context baselines, cross-session aggregation or drift — [Apollo](https://www.apolloresearch.ai/monitoring/a-scalable-monitoring-research-agenda)
- May–Sep 2026: Watcher, Watcher Live (real-time blocking/steering) and Watcher Analyze (observability over past deployments). Claims 93% of high-severity failures caught at <1% FPR on benign tool calls, with 3–5% overhead, and defaults "tuned" against a taxonomy of 40+ failure modes. These are per-action risk scores with org-wide policies. **[THR]** (product-level tuning; no public sequential method) — [Announcing Watcher Live](https://watcher.apolloresearch.ai/blog/announcing-watcher-live); [Watcher tech details](https://watcher.apolloresearch.ai/blog/monitor-coding-agents/); [Apollo Update May 2026](https://www.apolloresearch.ai/blog/apollo-update-may-2026/)
- 2026-05-28: "Training Deliberative Monitors for Black-Box Scheming Detection" (Sinha … Hobbhahn). Action-only, SFT/RL-distilled open-weight scheming monitors — [arXiv 2605.29601](https://arxiv.org/abs/2605.29601)

**UK AISI**
- 2025-12-15 (important late-2025 item): "Practical challenges of control monitoring in frontier AI deployments" (Lindner, Griffin, Korbak, Zimmermann, Irving, Farquhar, Cooney). It names "parallel agent instances, non-negligible oversight latency, **incremental attacks between agent instances**, and the difficulty of identifying scheming agents based on individual harmful actions", and analyzes synchronous, semi-synchronous and asynchronous monitoring with a safety-case sketch. **[SEQ][DIST]** (problem statement) — [AISI](https://www.aisi.gov.uk/research/practical-challenges-of-control-monitoring-in-frontier-ai-deployments); [arXiv 2512.22154](https://arxiv.org/abs/2512.22154)
- 2025-12-15: "Async Control" (Cooper Stickland et al.). Five SWE environments, after-the-fact monitoring, ensemble reaching about 6% FNR at 1% FPR — [arXiv 2512.13526](https://arxiv.org/pdf/2512.13526)
- 2026-07-08 (v2 2026-10-12): "Multi-Agent AI Control: Distributed Attacks Hamper Per-Instance Monitors" (Makins, Angelini, Shams, Phuong; listed on AISI's control page). Introduces the FakeLab setting (9 services, 86 tasks). Reports a **"fragmentation effect"**: more coordinating agents means per-agent monitors are less likely to catch any of them. A stronger monitor cuts undetected success by more than 10x but stays imperfect. No cross-agent aggregation defense is proposed in the abstract. **[DIST][SEQ]** — [arXiv 2607.07368](https://arxiv.org/abs/2607.07368); [AISI control page](https://www.aisi.gov.uk/category/control)
- 2026-07-02: "Distributed Attacks in Persistent-State AI Control" (Hills, Caspary, Cooper Stickland). The Iterative VibeCoding setting has an agent ship a sequence of PRs into a persistent codebase. No single monitor is robust to both gradual and concentrated attacks. Introduces a **"stateful link-tracker monitor that tracks suspicious buildup across PRs"**. A four-monitor ensemble cuts gradual-attack evasion from 93% to 47%. **[SEQ][DIST][LONG]**, high overlap — [arXiv 2607.02514](https://arxiv.org/abs/2607.02514)
- 2026-06-17: "Did you lie?" lie-detector evaluation (AISI control page) — [AISI](https://www.aisi.gov.uk/category/control)
- ControlArena (14-setting library) remains the AISI infrastructure. No 2026 ControlArena changelog was found in this sweep — [AISI blog](https://www.aisi.gov.uk/blog/introducing-controlarena-a-library-for-running-ai-control-experiments)

**Anthropic**
- 2026-02: Risk Report and Sabotage Risk Report (Opus 4.6), which use SHADE-Arena for oversight-evasion capability — [Anthropic Feb 2026 risk report](https://anthropic.com/feb-2026-risk-report)
- 2026-05-15: SLEIGHT-Bench (Najt, Toft, Tracy, Roger, Benton; Anthropic Fellows). 40 synthetic evasive transcripts across 11 categories. 20/40 attacks are never caught by an Opus 4.6 monitor at **1% FPR**, with a 32% overall catch rate. Evasion strategies include "state manipulation" — [arXiv 2605.16626](https://arxiv.org/pdf/2605.16626); [alignment.anthropic.com](https://alignment.anthropic.com/2026/sleight-bench/)
- 2026-08: "Automated researchers can reliably mitigate alignment failures" (Anthropic Fellows). A post-hoc monitor scanned 1,601 AAR trajectories and excluded 2.4% for cheating — [alignment.anthropic.com](https://alignment.anthropic.com/2026/automated-alignment-researchers/)
- ~2026-08: "Measurements for understanding the pace of AI development". About 30,000 internal agents run concurrently. The **online monitor** sees 100% of actions pre-execution and blocks 0.002% (about 1 in 47,000). The **offline monitor** targets "dangerous behaviors that develop slowly and can be reversed": it flags about 100k transcripts per week (1–2 per 1,000), and about 50 per week reach human review. Slow-developing problems are named as a target, but no cross-transcript statistic is described. **[LONG]** (motivation) — [Anthropic](https://www.anthropic.com/institute/measuring-pace-of-ai-development)
- Claude Code "auto mode" (per-action model-adjudicated permissions) was presented at ControlConf 2026 — [FAR.AI ControlConf 2026](https://www.far.ai/blog/controlconf-2026)

**OpenAI**
- 2026-03-19: "How we monitor internal coding agents for misalignment". Covers CoT and action monitoring, review within 30 minutes of completion, severity categorization, and an aspiration to evaluate actions before execution. No evidence of motivations beyond the task — [OpenAI](https://openai.com/index/how-we-monitor-internal-coding-agents-misalignment/)
- Per the mid-2026 overview post: >99.9% coverage of internal coding agents, "tens of millions" of trajectories over five months, about 1,000 moderate alerts escalated, and 24/7 paging for the most severe alerts. The post found "no open discussion of cross-trajectory aggregation or stateful longitudinal monitoring". This last point is the summarizer's characterization and should be checked against the post — [LessWrong overview](https://www.lesswrong.com/posts/E4Jpmo3igPnGnXtL4/an-overview-of-frontier-ai-company-monitoring-practices-in)

**Google DeepMind**
- 2026-06-18/22: "GDM AI Control Roadmap v0.1" (Phuong, Jenner, Simon, Ho, Shah, Farquhar, Coull). Key passages, read directly from the PDF:
  - Detection invariant (b): "persistent misaligned intent or behaviour are detected on the model level / across trajectories, leading to the model being swapped out…" **[SEQ][LONG]**
  - "Distributed kill chains … individual agent trajectories may look benign in isolation but combine to create an attack, posing a new challenge to detection." **[DIST]**
  - Async monitoring now, synchronous monitoring from capability level R2. Metrics proposed: async coverage, recall and time-to-response.
  - "Distributed attack simulation (speculative)" is listed as a needed evaluation, and "attack execution capability … is an open problem in the field".
  - Threshold numbers are deliberately left unspecified ("evaluation-specific").
  — [GDM roadmap PDF](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/securing-the-future-of-ai-agents/gdm-ai-control-roadmap.pdf); [Fortune](https://fortune.com/2026/06/18/google-deepmind-unveils-plan-to-protect-itself-from-its-own-rogue-ai-agents/)
- 2026-06-10: "Bootstrapped Monitoring" (Xiao, Phuong). An untrusted CoT-transparent monitor is overseen by a trusted model, evaluated on BashArena — [arXiv 2606.11998](https://arxiv.org/html/2606.11998)
- 2026-10: Gemini 4 Argon Safety & Security Report. GDM cannot rule out the Stealth & Situational Awareness CCL — [GDM PDF](https://storage.googleapis.com/deepmind-media/gemini/gemini_4_safety_report.pdf)

**METR / FAR.AI**
- 2026-05-11: ControlConf 2026 recap (FAR.AI). Quotes: "attacks distributed across multiple trajectories already beat strong single-trajectory monitors", "motivational drift across deployment" via shared context or memory, and "monitorability is fragile". METR talks covered external control evaluations (Cotra) and embedded red-teaming of Anthropic's monitoring (Rein). **[DIST][DRIFT]** — [FAR.AI](https://www.far.ai/blog/controlconf-2026)
- 2026-05-19: METR Frontier Risk Report (Feb–Mar 2026). Not fetched in detail — [METR](https://metr.org/blog/2026-05-19-frontier-risk-report/)

**Academic / other groups (monitoring-relevant, 2026)**
- 2026-01-28: "How does information access affect LLM monitors' ability to detect sabotage?" (Arike … Ward). Describes a "less-is-more" effect and extract-and-evaluate (EaE) hierarchical monitoring — [arXiv 2601.21112](https://arxiv.org/html/2601.21112v2)
- ICLR 2026: "Reliable Weak-to-Strong Monitoring of LLM Agents" (Kale et al.; the MRT workflow). Finds that "hybrid hierarchical-**sequential** designs" beat baselines, and that escalating pre-flagged cases improves TPR by about 15% at FPR 0.01. Here "sequential" means chunk-by-chunk LLM reading, not a statistical sequential test. **[SEQ]** (weak sense) — [ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/file/7e105e4ae3016974e2d518e9d281f5e5-Paper-Conference.pdf)
- ICLR 2026: "Adaptive Attacks on Trusted Monitors Subvert AI Control Protocols" (Terekhov et al.; arXiv Oct 2025). Prompt injection against monitors — [arXiv 2510.09462](https://arxiv.org/pdf/2510.09462)
- 2026-04-13: Hodoscope (Zhong, Saxena, Raghunathan). Unsupervised monitoring via distributional diffing against well-behaved baselines (CMU) — [arXiv 2604.11072](https://arxiv.org/pdf/2604.11072)
- 2026-05-14: "Ensemble Monitoring for AI Control: Diverse Signals Outweigh More Compute" (Koran … Bernabeu-Pérez) — [arXiv 2605.15377](https://arxiv.org/abs/2605.15377)
- 2026-05-27: SCHEME benchmark (Radev, Haas, Arnav, Bernabeu-Pérez). Coordinated multi-agent sabotage in which no proper subset of agents can succeed alone. **[DIST]** — [arXiv 2605.29178](https://arxiv.org/pdf/2605.29178)
- 2026-07-21: ResearchArena (Libon … Andriushchenko). Long-horizon AI R&D sabotage with embedded and independent side tasks. **[LONG]** — [arXiv 2607.19321](https://arxiv.org/pdf/2607.19321)
- 2026-09-07: MOLE (Muhamed, Smith; CMU). 150 AI-operated accounts, 9 stateful services, 30 workdays, about 20B tokens, 40 monitors. The best monitor misses nearly half of completed harm under a limited review budget. **[LONG][DIST]**: a natural testbed for cross-session/cross-account sequential monitors — [arXiv 2609.06966](https://arxiv.org/abs/2609.06966)
- 2026-09-24: EvasionBench / "Instrumental Monitor Evasion Emerges Under Ordinary Task Pressure" (Schmotz … Andriushchenko). Evasion attempts reach up to 98% and successes up to 88% — [arXiv 2609.30217](https://arxiv.org/pdf/2609.30217)
- 2026-10-16: "Red-Teaming Multi-Agent Attacks for Loss-of-Control Risks" (Kitaoka, Pham, Giudice, Merizian). MiniLab: 5 services, 249 tasks, 8 objectives. GPT-5.6 Sol reading each agent separately flags only 7% of successful distributed attacks, against 87% for a single-agent attack. **[DIST]** — [arXiv 2610.24052](https://arxiv.org/html/2610.24052)
- 2026-07-06: "Calibration-Family Overfit: Why Trusted Sabotage Monitors Don't Transfer Across Lineages" (Lucas Pinto). Finds a cross-family AUROC interaction of +0.172 (95% CI [0.158, 0.185]). Recommends reporting transfer matrices, detecting off-lineage operation at inference, and **recalibrating per lineage**. **[THR]**, strong overlap with per-context calibration — [arXiv 2607.06596](https://arxiv.org/abs/2607.06596)
- 2026-08-25: "More Rejective, Not More Discriminative: The Unit of Verification in Pre-Execution LLM Oversight" (Han, Yan, Zhang). Matched the "trusted monitor" + threshold/calibration query; not read in detail — [arXiv 2608.23941](https://arxiv.org/abs/2608.23941)

### Inferences
- The multi-agent / distributed-attack problem is already crowded: at least 6 papers between May and Oct 2026 (SCHEME, UPenn stateful, AISI FakeLab, Hills et al., MiniLab, Distributed Detectability Band), plus hackathon projects. A paper whose only contribution is "distributed attacks beat per-step monitors" would be scooped.
- The open space is principled statistical aggregation with error control on real control settings. Today's lab baseline is "max suspicion per trajectory plus a fixed FPR/audit budget" (Redwood logit-ROC, Retrying vs Resampling, LinuxArena 1% step-wise FPR). The existing defenses are heuristic or learned: the link-tracker, real-time clustering, TRACE's evidence loop, and ensembles. None reports ARL / time-to-detection against a calibrated false-alarm budget on BashArena, LinuxArena or SHADE-Arena with LLM-monitor scores. The closest exception is the Distributed Detectability Band paper, which uses synthetic score streams.

### Gaps
- Exact dates for the Redwood Screwtape, continual-learning and AI-swarms posts (the archive fetch gave implausible 2024 years).
- No 2026 ControlArena release notes were found. Not checked: AISI's 2026 research agenda update, the METR report's monitoring content, and the OpenAI follow-up (summer 2026) that the overview post appears to cite for the "tens of millions of trajectories" figure.
- Author and date of the LessWrong "overview of frontier AI company monitoring practices in mid 2026" post were not captured.

## Q2. Do open-problem lists / research agendas explicitly mention sequential testing, change detection, adaptive thresholds, cross-trajectory evidence, or per-context calibration?

### Takeaway
Several agendas name the **problems**: cross-trajectory or model-level detection, incremental attacks across instances, calibration transfer, stateful monitoring, and slowly developing behaviors. None of the agendas found names the **statistical tools** (CUSUM, SPRT, e-values, change-point). So the method-level niche is open, but the problem statement is widely recognized, and that is a real scooping risk.

### Cited Findings
- 2026-03-05, Bruce W. Lee, "Salient Directions in AI Control" (LessWrong):
  - Lists "Calibration transfer across settings" and "Asynchronous, **stateful**, and active monitoring paradigms".
  - Quotes: "a threshold tuned on APPS Backdooring will be meaningless in a researcher's ML codebase"; "maintaining a running belief about the model's alignment and adapting the deployment protocol accordingly" (referencing Adaptive Deployment); "information asymmetry that grows over the course of operation".
  - **[SEQ][THR]**, the closest explicit open-problem match — [LessWrong](https://www.lesswrong.com/posts/kitaRHhSzphdvqie2/salient-directions-in-ai-control)
- GDM AI Control Roadmap (Jun 2026):
  - Model-level / across-trajectory detection is one of two detection goals.
  - Distributed kill chains are described as "a new challenge to detection".
  - Distributed-attack evaluations are flagged as speculative and needed, and attack-execution measurement as an open problem.
  - No mention of sequential statistics was found by grep (searched terms: aggregat, sequential, cumulative, drift, calibrat).
  - **[SEQ][DIST][LONG]** — [GDM PDF](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/securing-the-future-of-ai-agents/gdm-ai-control-roadmap.pdf)
- UK AISI "Practical challenges…" (Dec 2025) names "incremental attacks between agent instances" and the difficulty of "identifying scheming agents based on individual harmful actions" as core challenges — [arXiv 2512.22154](https://arxiv.org/abs/2512.22154)
- Apollo "scalable monitoring research agenda" (May 2026): the fetch found no explicit thresholds, calibration, per-context baselines, cross-session aggregation or drift. Its frame is "number-go-up" games — [Apollo](https://www.apolloresearch.ai/monitoring/a-scalable-monitoring-research-agenda)
- ControlConf 2026 recap (May 2026): distributed multi-trajectory attacks and "motivational drift across deployment" are framed as live problems — [FAR.AI](https://www.far.ai/blog/controlconf-2026)
- Mid-2026 overview post: "There are no existing standards regarding human oversight (e.g., how much should be applied, when it should be applied…)" — [LessWrong](https://www.lesswrong.com/posts/E4Jpmo3igPnGnXtL4/an-overview-of-frontier-ai-company-monitoring-practices-in)
- Earlier foundation (2024, ICLR 2025): "Adaptive Deployment of Untrusted LLMs Reduces Distributed Threats". A macro-protocol keeps an adaptive credence on the untrusted model's alignment from past actions. This is the canonical Bayesian cross-task accumulation prior art — [arXiv 2411.17693](https://arxiv.org/pdf/2411.17693)
- SPAR Fall 2026 project list. Control/monitoring projects found:
  - "In-the-Wild AI Control" (Sree Sharvesh & Thao Pham, MATS): attacks co-evolving with monitors, plus "long-horizon interactions"
  - "Extending the SCHEME Coordinated Sabotage Benchmark" (Bernabeu Pérez et al.)
  - "Understanding and Monitoring Collusion in LLM Multi-Agent Systems" (Zihao Zhao)
  - "Escalation Detection: When Do Agents Need Human Intervention" (Lange & Lohrbeer; turn-averaged SAE features)
  - "Auditing Games for Debate" (UK AISI; models learning spot-check patterns)
  - "Building a Robust Activation Monitor" (distribution shift)
  
  None mentions CUSUM/SPRT/e-values/change-point. (The "CRITICAL" flags in the fetch output were added by the summarizer, not by SPAR.) — [SPAR F26](https://sparai.org/projects/f26/); [In-the-Wild AI Control](https://sparai.org/projects/f26/rec8RybPH2kNV6qDa/)
- Apart "AI Collusion Research Sprint" is scheduled for 2026-10-23 to 25 and is likely to produce more multi-agent/distributed-monitoring projects — [Apart](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25)

### Inferences
- The problem framing (cross-trajectory, model-level evidence, incremental attacks, calibration transfer) is endorsed by GDM, UK AISI and a prominent LessWrong agenda. That makes the topic fundable and timely, and it means teams at AISI, GDM or UPenn could produce a sequential-test paper next. The authors most likely to move next are Phuong/Makins (AISI/GDM), Cooper Stickland/Hills, and the UPenn Hassani/Wong/Robey group.
- No agenda found asks for formal false-alarm control (ARL, anytime-valid) on monitor score streams. That is the differentiator to emphasize.

### Gaps
- Not checked: the MATS Winter/Summer 2026 project lists in detail (only the program page surfaced), the LASR 2026 project list, the Anthropic Fellows 2026 project list, AISI Challenge Fund / Alignment Project grant lists, and Redwood's 2026 "research directions" posts (if any). None was located with the searches used.

## Q3. 2026 arXiv papers matching sequential monitoring / CUSUM / SPRT / e-value / change point / adaptive threshold / calibrated monitor / multi-step or distributed sabotage / long-horizon / cross-episode / persistent agents

### Takeaway
There is **direct overlap** already. One June 2026 paper (Zhang & Gao) explicitly benchmarks CUSUM, SPRT and HMM-LR against distributed sabotage in an AI-control framing, using synthetic score streams. A May 2026 UPenn paper builds a stateful online monitor across accounts. Several 2026 papers apply CUSUM/e-processes to agent *failure* detection (CURA, ESN+CUSUM, E-valuator, WATCH lineage). The niche that appears still open: a calibrated sequential/change-point monitor on real LLM-monitor score streams in standard control settings, with per-context threshold normalization, evaluated against adaptive multi-step attackers with ARL/delay metrics.

### Cited Findings — direct hits (highest scooping risk first)
- **2026-06-09 (v2 06-13)**, "The Distributed Detectability Band Against Marginal-Preserving Attacks" (Zhang Qinqin, Gao Yuze). "AI-control monitors score individual agent actions … real harm can be distributed across many benign-looking steps, each individually below any per-step alarm."
  - Builds a Gaussian-copula AR(1) attack whose per-step score marginal equals benign, so mean, max, top-k and threshold monitors drop to AUC 0.52.
  - The **CUSUM, SPRT, HMM-LR, runs test, autocorrelation and windowed-logistic** family reaches AUC 0.79–0.97 at 1% FPR and holds around 0.95 as harm is amortized.
  - Synthetic score streams; 10 pages.
  - **[SEQ][STAT][DIST][THR]**, the single most overlapping paper — [arXiv 2606.10456](https://arxiv.org/abs/2606.10456)
- **2026-05-29**, "Stateful Online Monitoring Catches Distributed Agent Attacks" (Davis Brown, Samarth Bhargav, Arav Santhanam, Kasper Hong, Ivan Zhang, Matan Shtepel, Steffi Chern, Alexander Robey, Eric Wong, Hamed Hassani).
  - Attack: the first distributed agent attack (a cyber task split across subagents and accounts) is caught 5x less often by a standard monitor.
  - Defense: an online stateful monitor that uses real-time clustering "to collect weak suspiciousness signals across many agent transcripts" and escalates rarely to an LLM.
  - Results: Pareto-dominates and catches attacks 30% earlier with negligible latency for about 99% of traffic. The advantage narrows as benign background traffic grows. "A new class of safety monitors which reason over groups of users rather than isolated transcripts."
  - Framed as misuse rather than misalignment. **[SEQ][DIST][LONG]** — [arXiv 2605.31593](https://arxiv.org/abs/2605.31593)
- **2026-07-02**, "Distributed Attacks in Persistent-State AI Control" (Hills, Caspary, Cooper Stickland). Stateful cross-PR link-tracker monitor (see Q1). **[SEQ][DIST][LONG]** — [arXiv 2607.02514](https://arxiv.org/abs/2607.02514)
- **2026-06-05**, "TRACE: Trajectory Reasoning through Adaptive Cross-Step Evidence Aggregation for LLM Agents" (Mittapalli … Rossi, Ahmed; Adobe-affiliated authors). A Triage-Inspect-Judge loop "maintaining accumulated evidence across reasoning steps" to catch hidden objectives pursued "through sequences of individually benign actions". Evaluated on 10 SHADE-Arena domains (F1 0.713, recall 0.844). The aggregation is LLM-agentic rather than statistical, and the authors note that plausible local justifications suppress accumulation of global suspicion. **[SEQ][DIST]** — [arXiv 2606.07054](https://arxiv.org/html/2606.07054)
- **2026-07-08**, AISI/GDM "Multi-Agent AI Control" (fragmentation effect), and **2026-10-16** MiniLab (7% vs 87%). **[DIST]** — [2607.07368](https://arxiv.org/abs/2607.07368); [2610.24052](https://arxiv.org/html/2610.24052)
- **2026-07-06**, "Calibration-Family Overfit" (Pinto). Per-lineage recalibration and off-lineage detection. **[THR]** — [arXiv 2607.06596](https://arxiv.org/abs/2607.06596)

### Cited Findings — sequential-statistics tools applied to agents (not misalignment/control, but methodological prior art)
- 2026-08-28, "CURA: Certified Runtime Alarms for Computer-Use Agents" (Kumar … Trivedi). Turns a running trajectory into "a sequential test with certified false-alarm control". At α=0.10 its **CUSUM** alarm detects 42.3% of failures a median of 31 steps before termination, at a realized false-alarm rate of 0.066. Failures, not sabotage. **[STAT][THR]** — [arXiv 2608.27808](https://arxiv.org/abs/2608.27808)
- 2026-08-03, "Real-Time Detection and Repair of LLM Agent Failures" (Sunny Dubey). One-class echo-state-network ensemble with **CUSUM** alarms on step telemetry: 0.71 detection at 5% false-alarm (AUROC 0.872). The advantage grows with post-onset horizon. **[STAT]** — [arXiv 2608.02464](https://arxiv.org/abs/2608.02464)
- 2025-12-02 (v2 2026-05-28), "E-valuator: Reliable Agent Verifiers with Sequential Hypothesis Testing" (Sadhuka, Prinster, Fannjiang, Scalia, Berger, Regev, Wang). **E-processes** convert any black-box verifier score into an anytime-valid, false-alarm-controlled decision at every step and terminate bad trajectories early. Success verification, not safety. **[STAT]** — [arXiv 2512.03109](https://arxiv.org/abs/2512.03109)
- 2025-05 (v6 in 2026), "WATCH: Adaptive Monitoring for AI Deployments via Weighted-Conformal Martingales" (Prinster, Han, Liu, Saria). Prior art for CTM/anytime-valid deployment monitoring. **[STAT][DRIFT]** — [arXiv 2505.04608](https://arxiv.org/pdf/2505.04608)
- 2026-07-02, "Online Safety Monitoring for LLMs" (Schirmer, Jazbec, Timans, Naesseth, Waldron, Nalisnick; ICML 2026 Hypothesis Testing Workshop). A simple verifier-threshold monitor with the threshold "calibrated via risk control" is "competitive with more advanced monitors based on **sequential hypothesis testing**". This is a negative or cautionary data point for sequential methods, on outputs rather than agents. **[STAT][THR]** — [arXiv 2607.02510](https://arxiv.org/abs/2607.02510)
- 2026-10-08, "Anytime-valid detection of LLM weight exfiltration" (Ortega-Fernandez, Kowalczyk, Warr; oral at the NeurIPS 2026 workshop "E-Values: From Statistics to ML", Dec 13 2026). A prompt-level **e-process** calibrated on trusted benign traffic accumulates weak evidence across responses with anytime false-alarm control against "patient attackers". Security framing, but structurally the same idea as accumulating weak sub-threshold evidence. **[STAT][SEQ][THR]** — [arXiv 2610.11843](https://arxiv.org/abs/2610.11843)
- 2026-01-08, "Anytime Detection of Strategic Deviations in Multi-Agent Systems" (Gauthier, Bach, Jordan). E-value test supermartingale for drift from equilibrium in repeated games. **[STAT][DRIFT]** — [arXiv 2601.05427](https://arxiv.org/abs/2601.05427)
- 2026-05-13, "When Should an AI Workflow Release? Always-Valid Inference for Black-Box Generate-Verify Systems" (Cho, Sun). Calibrates evaluator scores against a hard-negative pool, then applies an e-process — [arXiv 2605.12947](https://arxiv.org/abs/2605.12947)
- 2026-05-18, "Sequential Consensus for Multi-Agent LLM Debates: A Wald-SPRT compute governor…" (Morandi). SPRT for stopping, not safety — [arXiv 2605.19193](https://arxiv.org/abs/2605.19193)
- 2026-06-15 (v2), "Bistable by Construction: Wall-Clock-Calibrated State Monitors Have No Moment-Detection Regime at Agent Cadence" (Modgil). Accumulated-state threshold monitors for agents: wall-clock-decay monitors are bistable at variable agent cadence, while sample-time **CUSUM** is "exactly dt-invariant". Relevant design caveat. **[STAT][THR]** — [arXiv 2606.19386](https://arxiv.org/abs/2606.19386)
- 2026-06-04, "From Reward-Hack Activations to Agentic Risk States: Context-Calibrated Mechanistic Monitoring in LLM Agents" (Wilhelm, Kao). Entropy and decision-context features improve risk estimation over raw reward-hack activation. "Context-calibrated" here means feature conditioning, not per-context thresholds. **[THR]** (weak) — [arXiv 2606.06223](https://arxiv.org/abs/2606.06223)
- 2026-02-18, "DeepContext: Stateful Real-Time Detection of Multi-Turn Adversarial Intent Drift in LLMs" (Albrethsen et al.). An RNN over turn embeddings for Crescendo-style multi-turn jailbreaks. Misuse, chat. **[SEQ]** — [arXiv 2602.16935](https://arxiv.org/abs/2602.16935)
- 2026-08-18, "Decomposition Attacks Across Unlinkable Identities: Limits of Stateful Defenses for LLM Services" (Sun … Xiao). Proves that the security/utility trade-off of stateful monitors depends on how benign requests group; fresh, unlinkable identities defeat grouping. **[SEQ][DIST]** (theoretical limits) — [arXiv 2608.17445](https://arxiv.org/abs/2608.17445)
- 2026-06-09, "The Arbiter Agent: Continually Monitoring Multi-Agent Conversations…" (Tonini et al.). A step-by-step budgeted inspector agent. **[SEQ]** — [arXiv 2606.10747](https://arxiv.org/pdf/2606.10747)
- 2026-08-27, "INTENT-AS-A-TOOL" (Zhang et al.). Dense per-step intent probabilities identify critical steps for online intervention. **[SEQ]** (signal) — [arXiv 2608.27348](https://arxiv.org/pdf/2608.27348)
- 2026-04-16 (v2), "When the Agent Is the Adversary…" mentions "sequential intent inference through five-phase taxonomic monitoring". This is a position/architecture paper — [arXiv 2604.23425](https://arxiv.org/abs/2604.23425)
- 2026-08, "Joint Lyapunov Certificates for K-Agent Generative AI Governance" suggests the JLP generator as a CUSUM input (governance theory) — [arXiv 2608.09087](https://arxiv.org/pdf/2608.09087)

### Exact arXiv API queries run (export.arxiv.org, sorted by submittedDate desc, max 40, results shown only for submissions on or after 2025-10-01)
1. `abs:"AI control" AND (abs:sequential OR abs:CUSUM OR abs:SPRT OR abs:"change point" OR abs:"e-value" OR abs:"e-process")` returned **only 2606.10456**.
2. `abs:monitor AND abs:agent AND (abs:CUSUM OR abs:SPRT OR abs:"sequential probability ratio")` returned 2608.27808 (CURA), 2608.02464, 2606.18697 (world-model poisoning; off-topic), 2606.19386, 2606.10456, 2605.19193.
3. `abs:agent AND abs:monitor AND (abs:"anytime-valid" OR abs:"e-process" OR abs:"e-values")` returned 2609.32361 (debate distillation auditing), 2608.06362 (AV-AIVAT, game evaluation), 2605.30335, 2605.12947, 2601.05427, 2512.03109. **None is AI control / misalignment.**
4. `abs:"AI control" AND (abs:threshold OR abs:calibrat)` returned 2606.10456 plus one off-topic result.
5. `abs:"AI control" AND (abs:"multi-step" OR abs:distributed OR abs:"cross-session" OR abs:"long-horizon" OR abs:persistent)` returned 2610.24052, 2607.19321, 2607.07368, 2607.02514, 2606.10456, 2606.08892, 2605.29601, 2605.15377.
6. `abs:monitor AND abs:agent AND abs:"suspicion" AND (abs:accumulat OR abs:aggregat OR abs:trajectory)` returned **0 results**.
7. `ti:"stateful monitor" OR abs:"stateful monitor" OR abs:"stateful monitoring"` returned the relevant hits 2605.31593, 2602.16935, 2608.17445 and 2606.19386 (the rest were off-topic).
8. `abs:sabotage AND abs:monitor AND (abs:drift OR abs:"monitoring the monitor" OR abs:"monitor drift")` returned only 2511.09904 (CTRL-ALT-DECEIT, Nov 2025). **No 2026 "monitoring the monitor"/drift paper in control.**
9. `abs:"chain-of-thought monitor" AND (abs:sequential OR abs:threshold OR abs:calibrat)` returned **0 results**.
10. `abs:monitor AND abs:sabotage AND (abs:"multi-session" OR abs:"across sessions" OR abs:"cross-episode" OR abs:"cross-trajectory")` returned **0 results**.
11. `abs:"trusted monitor" AND (abs:threshold OR abs:calibration OR abs:normaliz)` returned 2608.23941, 2607.06596.
12. `abs:agent AND abs:"change-point"` returned **no AI-safety hits** (MARL change-point 2609.05298, a finance agent, a household-task benchmark, etc.).

WebSearch queries with no direct control-monitoring hit for change-point: `"change point" OR "changepoint" detection LLM agent misbehavior monitor 2026`. The search engine itself reported finding no paper combining change-point detection with LLM agent misbehavior monitoring.

### Inferences
- **Scooping risk: HIGH for the generic claim** "temporal/sequential statistics beat per-step max/threshold monitors against distributed sabotage". Zhang & Gao (2606.10456) already show this with CUSUM/SPRT on synthetic AR(1) copula score streams under an AI-control framing, and the UPenn and Hills et al. papers show stateful aggregation works empirically.
- **Scooping risk: MODERATE for** stateful monitors in real control settings. Two empirical stateful defenses exist (clustering across accounts; a cross-PR link-tracker), but neither uses formal sequential tests with calibrated ARL/false-alarm control, and neither uses BashArena/LinuxArena/SHADE-Arena LLM-monitor score streams.
- **Scooping risk: LOW to MODERATE for** the combination below, which no paper found here does. It would extend the 2026 baseline (max-suspicion + fixed audit budget; Redwood logit-ROC tail modeling; Pinto per-lineage calibration).
  - CFAR-style per-context/per-task threshold normalization of LLM monitor scores
  - plus CUSUM/SPRT/e-process accumulation
  - plus ARL / detection-delay reporting at control-relevant audit budgets (1e-4 to 1e-2)
  - plus adaptive attackers who know the accumulation rule (e.g. spacing attacks, or the marginal-preserving attacks of 2606.10456)
- A cautionary counterpoint to cite: Schirmer et al. (ICML 2026 workshop) find a risk-control-calibrated threshold competitive with sequential-test monitors on LLM outputs. Any new paper should beat a well-calibrated per-step threshold, not only a naive one.
- The sequential-statistics community is already engaging with LLM security: the NeurIPS 2026 E-Values workshop accepted the exfiltration e-process paper as an oral, and the ICML 2026 Hypothesis Testing workshop hosted Schirmer et al. These venues may surface more control-adjacent e-process papers in Nov–Dec 2026.

### Gaps
- Full texts of 2606.10456, 2605.31593 and 2607.02514 were not read. Their exact baselines, thresholds, and whether they report ARL or detection delay are unverified beyond the abstracts.
- Not swept: OpenReview submissions for NeurIPS 2026 workshops (e.g. E-Values workshop accepted papers list, any control/agent-safety workshop), ICLR 2027 submissions (deadline ~late Sep/Oct 2026, so anonymous OpenReview submissions on this topic may already exist), and Alignment Forum posts tagged AI Control beyond those surfaced by search.
- arXiv API searches cover abstracts only. Papers that mention CUSUM/SPRT only in the body would be missed.
