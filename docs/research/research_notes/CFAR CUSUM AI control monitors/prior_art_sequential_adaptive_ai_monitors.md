# Prior art: sequential-detection (CUSUM/SPRT/change-point/evidence accumulation) and adaptive per-context (CFAR-like) thresholds for AI agent / LLM monitoring

Scope: 2023 to Oct 2026, emphasis 2025-2026. Searched as of 2026-10-20. Method note: every high/medium-overlap item below was verified against the paper's full text (PDF downloaded from arXiv and grepped), not only against search snippets. Two WebFetch summaries (for arXiv 2607.07368 and 2607.02514) claimed those papers discuss CUSUM/SPRT and per-context baselines; full-text grep showed they do NOT. A third (2607.02510) claimed "per-context calibration"; full text shows a single global threshold. Those claims were discarded. Treat third-party summaries of these papers with suspicion.

Overlap ratings: (a) = CFAR / adaptive per-context threshold normalized by that context's own honest baseline; (b) = CUSUM / SPRT / change-point / sequential evidence accumulation.

## 1. Wen et al. (2024) "Adaptive Deployment of Untrusted LLMs Reduces Distributed Threats": how the credence update works, how close it is to SPRT/CUSUM, and follow-ups

### Takeaway
Wen et al. is the closest AI-control prior art for (b). Their macro-protocol is a Bayesian sequential update: it multiplies likelihoods of each task's monitor scores across a deployment over a discrete grid of attacker hypotheses. Mathematically that is a multi-hypothesis likelihood-ratio accumulation, i.e. a Bayesian cousin of SPRT. It never uses SPRT/CUSUM language, has no stopping rule, no false-alarm/ARL guarantees, no change-point (onset) model, and no per-context normalization. Its output is a per-task choice among micro-protocols, not an alarm. No published follow-up recasts it as SPRT/CUSUM.

### Cited Findings
- Citation: Jiaxin Wen, Vivek Hebbar, Caleb Larson, Aryan Bhatt, Ansh Radhakrishnan, Mrinank Sharma, Henry Sleight, Shi Feng, He He, Ethan Perez, Buck Shlegeris, Akbir Khan. arXiv 2411.17693 (v1, 26 Nov 2024); ICLR 2025 poster — [arXiv](https://arxiv.org/abs/2411.17693); [ICLR 2025](https://www.iclr.cc/virtual/2025/poster/28567)
- Threat model: "we introduce the 'distributed threat setting', where no single action is catastrophic on its own. We additionally require that no single action provides overwhelming evidence of misalignment" — [arXiv 2411.17693](https://arxiv.org/pdf/2411.17693)
- Mechanism: "the macro-protocol maintains an adaptive credence on the untrusted model's alignment based on its past actions, using it to pick between safer and riskier micro-protocols" — [arXiv 2411.17693](https://arxiv.org/abs/2411.17693)
- Update rule (Eq. 5): "The macro-protocol performs a Bayesian update to obtain c_t ... c^j_t = c^j_{t-1} P(s_t | h^j) / Σ_k c^k_{t-1} P(s_t | h^k) where P(s_t | h^j) is the probability of observing the monitor scores given hypothesis h^j. To estimate this, the blue team is provided a reference distribution" — [arXiv 2411.17693](https://arxiv.org/pdf/2411.17693)
- Hypotheses: each h^j = (r_j, β_j), a misbehavior rate r and a "sneakiness" trade-off β. The prior over hypotheses is a Nash-equilibrium prior: "we find a Nash equilibrium between the red team and blue team, where the red team chooses a distribution ∆(r, β) over malign policies and the blue team chooses a prior over hypotheses for the macro-protocol" — [arXiv 2411.17693](https://arxiv.org/pdf/2411.17693)
- Decision (Eq. 6): expected utility v(y_t^i) = Σ_j c_t^j E[1_benign·usefulness − α·harmfulness | h^j, s_t]; choose argmax_i. This selects an output/micro-protocol per task. There is no stop/alarm decision — [arXiv 2411.17693](https://arxiv.org/pdf/2411.17693)
- Likelihood estimation: non-parametric. Monitor scores are bucketed ("bucket(s_ijk) = ⌊s_ijk / b⌋"), and P(s_t | h^j) ≈ (n_j + a)/|R| from a reference set of benign and malicious outputs — [arXiv 2411.17693](https://arxiv.org/pdf/2411.17693)
- They report calibration problems with accumulated evidence: "errors can accumulate over long time sequences to produce overconfident credences. We mitigate this by bootstrapping over subsamples of the reference distribution", and "Naively following the Bayesian update procedure causes disastrous miscalibration when the reference distribution is imperfect" — [arXiv 2411.17693](https://arxiv.org/pdf/2411.17693)
- They note additivity in log-odds (the SPRT/CUSUM structure) without naming it: "Log-odds are appropriate because Bayesian updates are additive in log-odds space (and normal distributions result from additive random walks)" — [arXiv 2411.17693](https://arxiv.org/pdf/2411.17693)
- Full-text grep for "SPRT", "CUSUM", "sequential test", "change-point", "likelihood ratio" in 2411.17693 returned no hits. The paper does not frame itself as sequential hypothesis testing — [arXiv 2411.17693](https://arxiv.org/pdf/2411.17693)
- Stated limitations include biased reference distributions and "evolving task distributions during long deployments" (non-stationarity of the honest baseline) — [arXiv HTML](https://arxiv.org/html/2411.17693v1)
- Follow-ups and citations found:
  - Kutasov et al. 2025 cite it.
  - Multi-agent AI control (Makins, Angelini et al. 2026) cites it as the incrimination-across-actions idea: "[... Wen et al., 2024], which is harder when attack actions are diluted across agents" — [arXiv 2511.02997](https://arxiv.org/pdf/2511.02997); [arXiv 2607.07368](https://arxiv.org/pdf/2607.07368)
  - Hebbar's AF post on diffuse threats (30 Apr 2025) discusses incrimination vs. online training. It does not formalize sequential tests. Quoted: "without that affordance, no amount of mildly suspicious actions is enough to incriminate the model" — [Alignment Forum](https://www.alignmentforum.org/posts/Mf5Hnpi2KcqZdmFDq/how-can-we-solve-diffuse-threats-like-research-sabotage-with)
- Overlap rating: (b) HIGH conceptually (Bayesian evidence accumulation over a deployment against a distributed threat), but different in formalism and output. (a) LOW: one reference distribution, no per-context normalization.

### Inferences
- A CUSUM/SPRT project can present Wen et al. as the Bayesian, non-change-point ancestor. Distinct contributions would be:
  - (i) explicit stopping rules with ARL/false-alarm guarantees;
  - (ii) change-point modeling, since Wen assumes a stationary policy hypothesis and not a switch from honest to attack mid-deployment;
  - (iii) robustness to the miscalibration they report, e.g. by using per-context normalized scores as the CUSUM input;
  - (iv) agentic multi-step trajectories (Wen is APPS-style single-shot code generation).
- The authors' own miscalibration finding ("disastrous miscalibration") is direct motivation for a CFAR-style locally normalized input to the accumulator.

### Gaps
- Could not find any paper that re-derives Wen's macro-protocol as an SPRT or GLR test, or that adds a change-point prior. Searched: "follow-up adaptive deployment untrusted model Bayesian credence macro-protocol 2025 2026 AI control" and "posterior probability misaligned model across episodes Bayesian monitor deployment shutdown threshold untrusted agent 2026".
- Did not inspect the ICLR 2026 paper returned by the follow-up search ([ICLR 2026 PDF](https://proceedings.iclr.cc/paper_files/paper/2026/file/54b153ad8a138f4c186f21a8b7341d5e-Paper-Conference.pdf)). Its title was not shown, so it is unverified.

## 2. Ctrl-Z / incrimination and multi-step aggregation; trajectory memory; distributed/diffuse/decomposition attacks; low-stakes and async control; time-varying and upfront audit budgets

### Takeaway
The control literature aggregates per-step suspicion with ad hoc rules: max, second-max, mean, top-k, k-of-n "strikes", LLM-written running notes, and cross-account clustering with top-k sums. None of these is a formal sequential test with run-length guarantees. Audit-budget allocation over time (upfront auditing, non-increasing schedules) is formalized game-theoretically but not as change-point detection. Thresholds are almost universally a single global percentile of an honest score distribution, at most calibrated per attacker/monitor model, never per task or context.

### Cited Findings
- **Ctrl-Z (Bhatt, Rushing, Kaufman, Tracy, Georgiev, Matolcsi, Khan, Shlegeris), arXiv 2504.10374, Apr 2025.**
  - Introduces resample protocols. Incrimination is a k-of-n count rule: "Within a task, the blue team keeps a record of how many steps' suspiciousness scores were above a certain threshold. Once this happens for the third time, it audits the trajectory. Additionally, there is a higher threshold where the blue team audits if the suspiciousness of the current step hits that threshold ... Empirically, we find that 3 is the best number of strikes to use."
  - Resampled steps use the minimum score: "its suspiciousness score is determined as the minimum of suspiciousness scores among its samples."
  - "Time travel" resamples past steps: "the protocol samples some more actions from the third most suspicious past step, since that is usually the most informative to the Auditing after three strikes protocol."
  - Not framed as sequential testing (no SPRT/CUSUM terms in the text). Overlap: (b) MEDIUM (a counting accumulator within a trajectory, adaptive sampling for information); (a) LOW.
  - Source: [arXiv 2504.10374](https://arxiv.org/pdf/2504.10374)
- **Kutasov, Loughridge, Sun, Sleight, Shlegeris, Tracy, Benton et al., "Evaluating Control Protocols for Untrusted AI Agents", arXiv 2511.02997, Nov 2025.**
  - "At the end of the trajectory, the blue team aggregates suspicion scores across all turns in the trajectory by taking the second maximum score ... We use the second maximum since this empirically produces lower variance in aggregated scores than simply taking the maximum score."
  - The threshold is set "to ensure that the false positive rate of auditing on benign transcripts is 0.5%". This is one global threshold. A per-turn threshold of 40 was chosen because "it approximately separates the two modes of the bimodal suspicion score distribution for SHADE transcript turns."
  - Overlap: (b) LOW-MEDIUM; (a) LOW.
  - Source: [arXiv 2511.02997](https://arxiv.org/pdf/2511.02997)
- **Control OSWorld (Sanchez del Rio, Terekhov), arXiv 2610.03818, Oct 2026.**
  - Max aggregation: "an attack trajectory's score is the maximum before side task completion, and an honest trajectory's is the maximum over the whole trajectory."
  - Notes that max over steps raises the honest threshold: "increasing the per-trajectory maximum even though mean suspicion across steps stays low ... This raises the threshold τ at a fixed [FPR]".
  - This is the problem a length/context-normalized threshold would address. Overlap: (a) LOW (identifies the issue only); (b) LOW.
  - Source: [arXiv 2610.03818](https://arxiv.org/html/2610.03818v1)
- **Async Control (Cooper Stickland, Michelfeit, Mani, Griffin, Matthews, Korbak, Inglis, Makins, Cooney; UK AISI), arXiv 2512.13526, Dec 2025.**
  - Models deployments in which the red team must accumulate several successful attacks, with upfront auditing: "the first 1000 episodes are audited upfront, and subsequent episodes are flagged for audit if their monitor score exceeds a threshold calibrated to achieve the target FPR. The red team wins only if they accumulate the required number of undetected successful attacks before any successful attack is caught by the monitor."
  - Monitor scores are aggregated with an LLM judge or a random forest ensemble. Thresholds are global and calibrated on honest episodes.
  - Discusses red-team manipulation of calibration: "The untrusted model can try to influence monitor calibration by producing 'honest' episodes." This is a direct risk for any per-context honest-baseline (CFAR) design.
  - Overlap: (a) LOW (but relevant attack on calibration); (b) LOW.
  - Source: [arXiv 2512.13526](https://arxiv.org/pdf/2512.13526)
- **Games for AI Control (Griffin, Thomson, Shlegeris, Abate), arXiv 2409.07985, 2024 (v2 May 2026).**
  - Formal models of control evaluations, including "Upfront Auditing" ("audits the first 2% of solutions from U").
  - Overlap: (b) LOW (time-allocation of audits, not evidence accumulation).
  - Source: [arXiv 2409.07985](https://arxiv.org/pdf/2409.07985)
- **Control Tax (Terekhov, Liu, Gulcehre, Albanie), arXiv 2506.05296 (v3 Mar 2026).**
  - "Sequential" deployment where outputs are approved one by one, with a time-varying audit budget: "The blue team's allocation strategy is a non-increasing, Riemann-integrable function p : [0, 1] → [0, 1], which represents the expected fraction of audited samples over time"; "Auditing p(τ) samples per round corresponds to selecting time-dependent thresholds s(p(τ), p_b)"; it cites "exponentially decaying allocations introduced by Bhatt et al. (2025)".
  - Time-varying thresholds, but driven by budget allocation against a memoryless attacker, not by accumulated evidence or a per-context baseline.
  - Also: "most errors manifest as false positives ... improved calibration of monitors could enhance their accuracy ... pointing to calibration as a valuable direction for future work."
  - Overlap: (a) LOW-MEDIUM (time-varying thresholds); (b) LOW.
  - Source: [arXiv 2506.05296](https://arxiv.org/pdf/2506.05296)
- **Hua, Lemoine, Baskerville, Bhatt, Hopman, Tracy, "Combining Cost-Constrained Runtime Monitors for AI Safety", arXiv 2507.15886, NeurIPS 2025.**
  - Audits on likelihood ratios across monitors: "allocates safety interventions based on the Neyman-Pearson lemma. By focusing on likelihood ratios ... we more than double our recall rate."
  - Monitors are called in sequence, but this is a one-shot LR per output, not accumulation over time.
  - Overlap: (b) LOW-MEDIUM (LR thresholding is the building block of SPRT); (a) LOW.
  - Source: [arXiv 2507.15886](https://arxiv.org/pdf/2507.15886)
- **Distributed Attacks in Persistent-State AI Control (Hills, Caspary, Cooper Stickland), arXiv 2607.02514, Jul 2026.**
  - Gradual attacks spread across PRs. The defense is an LLM "stateful link-tracker monitor that tracks suspicious buildup across PRs ... as it reviews each PR it writes notes to a file recording anything potentially suspicious."
  - Calibration uses honest baselines: "n = 60 honest baselines used for threshold calibration"; "a p98 threshold".
  - Full-text grep found no CUSUM/SPRT/change-point. The WebFetch summary claiming otherwise is false.
  - Overlap: (b) MEDIUM (stateful accumulation, but via LLM notes); (a) LOW.
  - Source: [arXiv 2607.02514](https://arxiv.org/pdf/2607.02514)
- **Multi-Agent AI Control: Distributed Attacks Hamper Per-Instance Monitors (Makins, Angelini, Shams, Phuong), arXiv 2607.07368 (v2 12 Oct 2026).**
  - "fragmentation effect: as more agents coordinate to attack, per-agent monitoring becomes less likely to catch any of the attackers."
  - Cites Benson-Tilsen's "sum-threshold attack". Full-text grep found no CUSUM/SPRT. The WebFetch summary claiming otherwise is false.
  - Overlap: (b) LOW-MEDIUM (motivates cross-instance accumulation, does not build it); (a) LOW.
  - Source: [arXiv 2607.07368](https://arxiv.org/pdf/2607.07368)
- **Stateful Online Monitoring Catches Distributed Agent Attacks (Brown, Bhargav, Hong, Zhang, Santhanam, Shtepel, Chern, Robey, Wong, Hassani), arXiv 2605.31593, 29 May 2026.**
  - Cross-account misuse. "an online stateful monitor that uses real-time clustering to collect weak suspiciousness signals across many agent transcripts, and escalates only rarely to a language model"; "To flag a cluster, the largest k scores are summed and exceed a threshold calibrated on held-out data. We also require ≥ m prior contexts above a certain score. This lets several moderate signals trigger review."
  - Reports "catching distributed attacks 30% earlier", which is a detection-delay framing.
  - Accumulator is top-k sum plus count, with thresholds tuned on held-out data. No CUSUM/SPRT language or guarantees.
  - Overlap: (b) MEDIUM-HIGH for the misuse/cross-session setting; (a) LOW.
  - Source: [arXiv 2605.31593](https://arxiv.org/pdf/2605.31593)
- **Monitoring Decomposition Attacks in LLMs with Lightweight Sequential Monitors (Chen Yueh-Han, Joshi, Chen, Andriushchenko, Angell, He), arXiv 2506.10949, Jun 2025; ICLR 2026.**
  - "Sequential" means an LLM reads the cumulative prompt history: "the monitor inspects the cumulative context C_i = [p_1, ..., p_i]. If C_i is flagged as harmful ..." Reports a 93% defense success rate.
  - Not a statistical sequential test. Overlap: (b) LOW-MEDIUM (name collision only); (a) LOW.
  - Source: [arXiv 2506.10949](https://arxiv.org/pdf/2506.10949)
- **TRACE (Mittapalli et al.), arXiv 2606.07054, Jun 2026.**
  - LLM monitor for long-horizon sabotage on SHADE-Arena with "accumulated evidence across reasoning steps" (Triage–Inspect–Judge loop).
  - LLM-reasoning accumulation, not statistical. Overlap: (b) LOW-MEDIUM.
  - Source: [arXiv 2606.07054](https://arxiv.org/html/2606.07054v1)
- **Meerkat, "Detecting Safety Violations Across Many Agent Traces" (Stein, Brown, Hassani, Naik, Wong), arXiv 2604.11806, Apr 2026.**
  - Clustering plus agentic search over many traces, for failures "only detectable when multiple traces are analyzed together".
  - Offline audit, not sequential. Overlap: (b) LOW.
  - Source: [arXiv 2604.11806](https://arxiv.org/pdf/2604.11806)
- **Reliable Weak-to-Strong Monitoring of LLM Agents (Kale et al., Scale AI), arXiv 2508.19461, 2025; ICLR 2026.**
  - "Sequential monitoring" here means recursive chunk summarization; "sequential scaffolding seems to have a relatively low TPR."
  - Not statistical. Overlap: LOW (term collision).
  - Source: [arXiv 2508.19461](https://arxiv.org/pdf/2508.19461)
- **GDM AI Control Roadmap (Phuong, Jenner, Simon, Ho, Shah, Farquhar, Coull), arXiv 2607.13087, Jul 2026.**
  - Separates per-trajectory detection from "persistent misaligned intent or behaviour ... detected on the model level / across trajectories ... (this is sometimes called 'incrimination' (Hebbar, 2025))".
  - Lists UEBA as a control measure: "UEBA (User and Entity Behaviour Analytics) is an approach to anomaly detection that works by establishing a baseline of normal activity for users and network entities ... and continuously monitoring for deviations from this baseline."
  - A roadmap-level endorsement of per-entity baselines (CFAR-like) and cross-trajectory accumulation, with no implementation. Overlap: (a) MEDIUM (as a stated idea); (b) MEDIUM (as a stated idea).
  - Source: [arXiv 2607.13087](https://arxiv.org/html/2607.13087v1)
- **Hebbar, "How can we solve diffuse threats like research sabotage with AI control?", Alignment Forum, 30 Apr 2025.**
  - Defines diffuse threats and discusses incrimination vs. online training. No statistical accumulation scheme.
  - Overlap: (b) LOW-MEDIUM (problem statement).
  - Source: [Alignment Forum](https://www.alignmentforum.org/posts/Mf5Hnpi2KcqZdmFDq/how-can-we-solve-diffuse-threats-like-research-sabotage-with)
- **Diffuse AI Control on Fuzzy Tasks (Terekhov, Gulcehre, Hebbar, Benton), arXiv 2606.08892, Jun 2026.**
  - Diffuse control via training against a weak score. No sequential detection.
  - Overlap: LOW.
  - Source: [arXiv 2606.08892](https://arxiv.org/pdf/2606.08892)
- **Benson-Tilsen, "Sum-threshold attacks", LessWrong, 8 Sep 2023.**
  - Conceptual: "an agent can push on something in a way that no one notices by distributing its effects through lots of different channels." No accumulation-based defense.
  - Overlap: LOW (threat-model origin).
  - Source: [LessWrong](https://www.lesswrong.com/posts/R3eDrDoX8LisKgGZe/sum-threshold-attacks)

### Inferences
- The field has converged on the problem: distributed, diffuse, gradual, and fragmented attacks beat per-step max/mean monitors. The fixes are ad hoc (strikes, second-max, top-k sums, LLM notes, clustering).
- A CUSUM/SPRT treatment with explicit ARL/false-alarm control is a natural, still-open formalization in the control setting. The Distributed Detectability Band paper (Section 3) is the main exception.
- No control paper tunes thresholds per task or per environment from that context's own honest baseline. "Per attacker" calibration in LinuxArena is per model, not per context.

### Gaps
- Did not check ControlArena's code for built-in aggregators (e.g., a "CUSUM" or "EWMA" scorer). The repo was not inspected.
- Redwood blog posts on "time-varying audit budget" beyond Control Tax/Bhatt citations were not individually located.

## 3. Explicit uses of CUSUM / SPRT / change-point / quickest detection / e-values / Page–Hinkley / EWMA / BOCPD / CFAR with LLM agents, AI control, jailbreaks, sabotage, scheming, misuse

### Takeaway
SCOOPING RISK IS REAL BUT PARTIAL.
- **Closest prior art for (b), in AI control:** one June 2026 arXiv paper (Zhang & Gao, "The Distributed Detectability Band Against Marginal-Preserving Attacks") explicitly evaluates CUSUM and SPRT monitors on AI-control suspicion-score streams against distributed sub-threshold sabotage. Its scope is narrow: synthetic Gaussian-copula AR(1) traces plus a small real-trace validation, and CUSUM/SPRT retargeted to autocorrelation.
- **Jailbreak and failure domains:** several 2026 papers use one-sided CUSUM in adjacent domains.
  - SafeDream: multi-turn jailbreaks, CUSUM on log-odds minus a global benign baseline κ.
  - CPD: adversarial suffixes, CUSUM over entropies standardized by a per-deployment baseline. This is the closest to CFAR+CUSUM combined.
  - CURA and "Real-Time Detection and Repair": agent task failures, CUSUM with thresholds calibrated on successful or healthy runs, and per-tool-type normalization in CURA.
  - E-valuator and Online Safety Monitoring: e-process/SPRT-style anytime-valid tests for agent success and LLM output safety.
- **Not found:**
  - No paper uses "CFAR" / "constant false alarm rate" with LLM monitors.
  - No paper combines a per-task or per-context honest-baseline normalization (CFAR) with CUSUM/SPRT for misaligned or scheming agents in a standard control setting (BashArena, SHADE-Arena, LinuxArena, ControlArena).
  - No paper treats an adaptive attacker's response to the accumulator in a realistic agent setting (the Band paper does it only on synthetic traces).

### Cited Findings

**Ranked list of closest prior art (most to least threatening to novelty):**

| # | Work | Date | Domain | (a) CFAR / per-context | (b) Sequential | Overall |
|---|---|---|---|---|---|---|
| 1 | Zhang & Gao, Distributed Detectability Band, arXiv 2606.10456 | Jun 2026 | AI control, distributed sabotage | Low (global benign marginal) | High (CUSUM, SPRT, HMM-LR on suspicion streams) | HIGH |
| 2 | Wen et al., Adaptive Deployment, arXiv 2411.17693 | Nov 2024 | AI control, distributed threats | Low | High-conceptual (Bayesian LR accumulation, no stopping rule) | HIGH |
| 3 | Alshaalan & Rodrigues, CPD Online, arXiv 2605.19966 | May 2026 | Jailbreak (adversarial suffix) | Medium-High (per-deployment median/MAD baseline) | High (one-sided CUSUM) | MEDIUM-HIGH (wrong domain) |
| 4 | SafeDream, arXiv 2604.16824 | Apr 2026 | Multi-turn jailbreak | Low-Medium (global benign κ) | High (CUSUM over turns) | MEDIUM-HIGH (wrong domain) |
| 5 | Brown et al., Stateful Online Monitoring, arXiv 2605.31593 | May 2026 | Agent misuse, cross-account | Low | Medium-High (top-k sum accumulator, detection delay) | MEDIUM |
| 6 | CURA, arXiv 2608.27808 | Aug 2026 | Agent task failure (not adversarial) | Medium (frozen z-scoring, per-tool-type Gaussian) | High (CUSUM, LTT-certified FPR) | MEDIUM |
| 7 | Dubey, Real-Time Detection & Repair, arXiv 2608.02464 | Aug 2026 | Agent failure | Medium (per-deployment recalibration) | High (per-channel CUSUM) | MEDIUM |
| 8 | E-valuator, arXiv 2512.03109 | Dec 2025 | Agent success verification | Low | High (e-process/SPRT, anytime-valid) | MEDIUM |
| 9 | Schirmer et al., Online Safety Monitoring for LLMs, arXiv 2607.02510 | Jul 2026 | LLM output safety (incl. red-teaming) | Low (global λ) | Medium (compares to sequential tests) | MEDIUM-LOW |
| 10 | Ctrl-Z three-strikes, arXiv 2504.10374 | Apr 2025 | AI control | Low | Medium (k-of-n counter) | MEDIUM-LOW |
| 11 | Persistent-state link-tracker, arXiv 2607.02514 | Jul 2026 | AI control | Low | Medium (LLM-notes accumulation) | MEDIUM-LOW |
| 12 | Peak+Accumulation, arXiv 2602.11247 | Feb/Mar 2026 | Multi-turn prompt injection | Low | Medium (CUSUM-inspired heuristic) | MEDIUM-LOW |
| 13 | GDM Control Roadmap, arXiv 2607.13087 | Jul 2026 | AI control strategy | Medium (UEBA baseline idea) | Medium (cross-trajectory idea) | MEDIUM-LOW (idea only) |
| 14 | WATCH (Prinster et al.), ICML 2025 | May 2025 | Generic ML deployment drift | Medium (weighted-conformal adaptation) | High (conformal test martingales) | LOW-MEDIUM |
| 15 | Hua et al., Combining Monitors, arXiv 2507.15886 | Jul 2025 | AI control | Low | Low-Medium (NP likelihood ratio, single-shot) | LOW-MEDIUM |
| 16 | Control Tax / Games for AI Control | 2024–2026 | AI control | Low-Medium (time-varying thresholds from budget) | Low | LOW |
| 17 | Modgil, Bistable by Construction, arXiv 2606.19386 | Jun/Oct 2026 | Agent runtime monitors (frustration/affect) | Low | Medium (CUSUM vs leaky accumulators) | LOW |
| 18 | Adaptive Triggering (bias), CUSUM-shaped decoding, Adaptive auditing (SAVI) | 2026 | Non-safety LLM uses | Low | Medium | LOW |

**Item details (verified passages):**

1. **Zhang Qinqin & Yuze Gao, "The Distributed Detectability Band Against Marginal-Preserving Attacks", arXiv 2606.10456, v2 13 Jun 2026, cs.CR. Code: github.com/Gyyz/distributed_sabotage_frontier.**
   - Abstract: "AI-control monitors score individual agent actions to detect misbehavior, but real harm can be distributed across many benign-looking steps, each individually below any per-step alarm ... mean, max, top-k tail, and threshold monitors (Monitor A) are defeated by construction ... Monitor B (the correlation/sequence family: CUSUM, SPRT, HMM-LR, runs test, autocorrelation, windowed logistic) ... Monitor A achieves AUC ≈ 0.52 (chance); Monitor B spans AUC 0.79–0.97 at the same 1% FPR target."
   - Statistics: "CUSUM-on-products: C_t = max(0, C_{t−1} + s_t s_{t−1} − κ)"; "SPRT-on-AR(1): likelihood ratio Λ_T = Π p(s_t|s_{t−1}; φ_att)/p(s_t|s_{t−1}; φ_ben)".
   - Key nuance: "Classical CUSUM and SPRT are designed for mean shifts. When applied to the per-step scores of a marginal-preserving attack, they detect nothing (as we show empirically)."
   - Claims priority: "We differentiate our contribution as the first formal treatment of this gap."
   - Includes a "Real-Data Validation" on "Qwen2.5-7B agent / Llama-3.2-3B monitor" benign scores fit by a Beta distribution.
   - No per-context/per-task normalization: one benign marginal F_ben.
   - Gaps it leaves:
     - real control settings with LLM attackers (not copula-synthesized scores);
     - mean-shift attacks (the usual case);
     - per-context baselines;
     - ARL-calibrated thresholds;
     - adaptive red-teaming against CUSUM on real agents.
   - Small team (gmail/outlook addresses), not peer-reviewed. Overlap: (b) HIGH, (a) LOW.
   - Source: [arXiv 2606.10456](https://arxiv.org/pdf/2606.10456); [HTML](https://arxiv.org/html/2606.10456v2)
2. **Mohammed Alshaalan & Miguel R. D. Rodrigues (UCL), "Detecting Fluent Optimization-Based Adversarial Prompts via Sequential Entropy Changes" (CPD Online), arXiv 2605.19966, 19 May 2026.**
   - "We cast adversarial suffix detection as an online changepoint detection problem over the token-level next-token entropy stream. Using the LLM system prompt to estimate a robust baseline, we standardize user-token entropies and apply a one-sided CUSUM statistic."
   - Per-deployment baseline: "Entropy magnitudes depend on the model and the deployed system prompt. Because the system prompt is fixed under a given deployment, its entropy sequence provides a deployment-specific reference sample. We estimate a robust location and scale using the median and the median absolute deviation (MAD)."
   - This is structurally CFAR (local reference cells → normalize → threshold) plus CUSUM, but for token-level jailbreak suffixes, not agent actions.
   - Overlap: (a) MEDIUM-HIGH, (b) HIGH, domain-distant.
   - Source: [arXiv 2605.19966](https://arxiv.org/html/2605.19966v1)
3. **Bo Yan, Weikai Lin, Yada Zhu (IBM), Song Wang et al., "SafeDream: Safety World Model for Proactive Early Jailbreak Detection", arXiv 2604.16824, 18 Apr 2026.**
   - "(2) CUSUM detection that accumulates weak per-turn risk signals into reliable evidence".
   - "We adopt CUSUM (Page, 1954), a sequential change-point detection method that is provably optimal for minimizing detection delay at a given false alarm rate (Moustakides, 1986)".
   - "The CUSUM statistic accumulates evidence by subtracting a baseline κ (the average log-odds under benign conversations): G_t = max(0, G_{t−1} + Λ_t − κ)".
   - Ablation: removing CUSUM makes "FPR surge to 13.8%".
   - Global benign baseline, not per-conversation or per-topic. Overlap: (b) HIGH (multi-turn misuse), (a) LOW-MEDIUM.
   - Source: [arXiv 2604.16824](https://arxiv.org/pdf/2604.16824)
4. **CURA: Certified Runtime Alarms for Computer-Use Agents (Divake Kumar, Tayebati, Naik, Rios, Ahuja, Tickoo, Krishnan, Trivedi; Intel/UIC), arXiv 2608.27808, 28 Aug 2026.**
   - CUSUM "W_t = max(0, W_{t−1} + S_t − k), k = 0.5" over z-scored signals with "frozen normalization constants" fit on successful runs, and a per-tool-type Gaussian: "For each tool type c = κ(A_t) a diagonal Gaussian is fit".
   - Threshold via Learn-then-Test with "Pr(FPR(θ̂_α) ≤ α) ≥ 1 − δ".
   - Explicitly not adversarial: "We find no evidence of strategic deception and do not study adversarial evasion."
   - Overlap: (b) HIGH, (a) MEDIUM, but for benign task failures.
   - Source: [arXiv 2608.27808](https://arxiv.org/html/2608.27808)
5. **Sunny Dubey, "Real-Time Detection and Repair of LLM Agent Failures", arXiv 2608.02464, 3 Aug 2026.**
   - Per-channel one-sided CUSUM over echo-state-network surprise. Threshold "Q_{1−β}({max_t s_t : healthy val episodes})".
   - Recalibration is needed per deployment: "calibrated on qwen2.5:7b and deployed on llama3.1:8b ... the monitor sits at chance (AUROC 0.527), while the same target recalibrated on itself reaches 0.885".
   - That finding is empirical support for per-context baselines. Failures only, not adversarial. Overlap: (b) HIGH, (a) MEDIUM.
   - Source: [arXiv 2608.02464](https://arxiv.org/html/2608.02464v1)
6. **E-valuator (Sadhuka, Prinster, Fannjiang, Scalia, Berger, Regev, Wang; Genentech/MIT/JHU/Stanford), arXiv 2512.03109, Dec 2025 (v2 May 2026).**
   - "We frame the problem of distinguishing a successful trajectory ... from an unsuccessful trajectory as a sequential hypothesis testing problem ... a sequential hypothesis test that remains valid at every step of an agent's trajectory, enabling online monitoring of agents."
   - The e-process is a density ratio M_t = p0(s_1:t)/p1(s_1:t) with threshold 1/α (Ville).
   - Success/failure, not misalignment. Overlap: (b) HIGH (method), (a) LOW.
   - Source: [arXiv 2512.03109](https://arxiv.org/pdf/2512.03109)
7. **Schirmer, Jazbec, Timans, Naesseth, Waldron, Nalisnick, "Online Safety Monitoring for LLMs", arXiv 2607.02510, 2 Jul 2026.**
   - "a simple real-time monitor that turns a verifier signal ... into an alarm decision by thresholding, with the threshold calibrated via risk control ... competitive with more advanced monitors based on sequential hypothesis testing."
   - Covers "factual correctness, toxicity and malicious use", with experiments including red-teaming conversations.
   - Single global λ. The WebFetch claim of "per-context calibration" was not supported by the full text. Overlap: (b) MEDIUM, (a) LOW.
   - Source: [arXiv 2607.02510](https://arxiv.org/pdf/2607.02510)
8. **J Alex Corll, "Peak + Accumulation: A Proxy-Level Scoring Formula for Multi-Turn LLM Attack Detection", arXiv 2602.11247 (v2 Mar 2026).**
   - "Drawing on analogies from change-point detection (CUSUM), Bayesian belief updating, and security risk-based alerting ... The common principle is accumulation, not averaging."
   - 90.8% recall at 1.20% FPR. A heuristic formula, not a CUSUM.
   - Source: [arXiv 2602.11247](https://arxiv.org/pdf/2602.11247)
9. **Prinster, Han, Liu, Saria, "WATCH: Adaptive Monitoring for AI Deployments via Weighted-Conformal Martingales", ICML 2025 (arXiv 2505.04608).**
   - Weighted conformal test martingales that "continuously adapt to mild distribution shifts while quickly detecting harmful shifts".
   - Generic deployment drift, not agent misbehavior. Overlap: (b) HIGH (method), (a) MEDIUM (adaptive baseline), domain-distant.
   - Source: [PMLR](https://proceedings.mlr.press/v267/prinster25a.html); [arXiv](https://arxiv.org/pdf/2505.04608)
10. **Manvendra Modgil, "Bistable by Construction: Wall-Clock-Calibrated State Monitors Have No Moment-Detection Regime at Agent Cadence", arXiv 2606.19386 (v2 9 Oct 2026).**
    - Agent runtime monitors that threshold accumulated state. A sample-time CUSUM is "exactly invariant across the entire ∆t grid", while wall-clock leaky integrators saturate.
    - "We claim no novelty for edge detection or for CUSUM."
    - Useful design caution: calibrate accumulators per step, not per second. Overlap: LOW.
    - Source: [arXiv 2606.19386](https://arxiv.org/pdf/2606.19386)
11. **Other CUSUM/e-value uses on LLMs that are not safety monitoring (LOW):**
    - "Adaptive Triggering for Bias Correction in LLM Reasoning" (arXiv 2608.25379, Aug 2026): "We formulate this decision as an online change-point detection problem. A per-step bias signal updates a CUSUM statistic." [arXiv](https://arxiv.org/html/2608.25379v1)
    - "CUSUM-Shaped Inference-Time Monitoring and Targeted Re-Decoding for Quantized SLM Reasoning" (arXiv 2607.20129). [arXiv](https://arxiv.org/html/2607.20129v1)
    - "Adaptive auditing of AI systems with anytime-valid guarantees" (Zhou, Vossler, Sivaraman, Mai, Feng; arXiv 2605.07002, May 2026), e-processes for adaptive evaluation audits. [arXiv](https://arxiv.org/html/2605.07002)
    - "ConSol: SPRT to find consistent LLM reasoning paths" (arXiv 2503.17587). [arXiv](https://arxiv.org/pdf/2503.17587)

**Search log (queries and results):**

Hits that yielded items above:
- "sequential probability ratio test LLM agent monitoring AI control" → E-valuator-adjacent, Kale et al., ConSol; no AI-control SPRT monitor.
- "CUSUM change-point detection LLM agent misbehavior monitor" → CURA, Dubey, Modgil, Adaptive Triggering, CPD.
- "aggregating suspicion scores across trajectory steps max mean monitor AI control" → Kutasov (second max), Control OSWorld, Distributed Detectability Band.
- "e-values anytime-valid monitoring LLM agent safety test martingale" → E-valuator, Online Safety Monitoring, CELEUS.
- "multi-turn jailbreak detection cumulative risk across turns sequential test defense Crescendo" and "\"risk increasing trend\" multi-turn jailbreak CUSUM detection delay false alarm" → SafeDream.
- "\"Bayesian online changepoint\" LLM jailbreak OR agent OR safety monitoring" → Stateful Online Monitoring (2605.31593), ProbGuard. No BOCPD-on-LLM-safety paper found.
- "\"CUSUM\" \"AI control\" monitor suspicion" → only the Distributed Detectability Band paper inside AI control. Otherwise medical-AI CUSUM tools (e.g., FDA DIDSR AIM-CU) unrelated to agents.

Negative results:
- "\"constant false alarm rate\" LLM monitor OR jailbreak OR agent" → no CFAR usage. Results only use "false alarm rate" generically (AutoMonitor-Bench, JailbreaksOverTime, CURA).
- "\"SPRT\" scheming OR sabotage OR \"untrusted model\" LLM monitoring" → no SPRT-based scheming or sabotage monitor (results: Constitutional Black-Box Monitoring, collusion posts).
- "\"quickest detection\" OR \"Page-Hinkley\" language model agent attack" → nothing LLM-specific (smart-grid and CPS only).
- Lesswrong/AF queries ("lesswrong AI control sequential testing SPRT untrusted model evidence accumulation audit") → no LW/AF post proposing SPRT/CUSUM for control monitors was found.

### Inferences
- Novelty for "CUSUM/SPRT for AI-control monitors" is partially pre-empted by Zhang & Gao (2606.10456) and conceptually by Wen et al. (2411.17693). A new project must differentiate on:
  - realistic agentic control settings with LLM red teams;
  - mean-shift / onset (change-point) attacks rather than copula-correlation attacks;
  - ARL/false-alarm-calibrated thresholds;
  - adaptive attackers who know the accumulator (e.g., slow-drip attacks below the CUSUM drift k);
  - combination with per-context normalization.
- Novelty for "CFAR-style per-context honest-baseline thresholds for agent monitors" looks open in AI control. Precedents exist only in adjacent domains: CPD's per-deployment baseline for jailbreaks, CURA's per-tool-type normalization for failures, Dubey's per-deployment recalibration. The GDM roadmap names UEBA-style baselines as a desired measure without implementing them.
- The combination (CFAR-normalized input → CUSUM/SPRT accumulator → calibrated alarm) for misaligned agents in a control evaluation appears unpublished as of 2026-10-20. Its nearest structural twin is CPD Online, in the jailbreak-suffix domain.

### Gaps
- Could not search Google Scholar or Semantic Scholar full text directly; relied on web search plus arXiv full text. Non-arXiv workshop papers (OpenReview-only, e.g. ICML 2026 / NeurIPS 2026 workshops) may be missed.
- Did not verify "Stateful Guardrails for Multi-Turn LLM Systems: A Conversational Risk Accumulation Framework" (arXiv 2607.19361) in depth. Full-text grep found no CUSUM/SPRT/change-point terms, so it is likely heuristic accumulation. [arXiv](https://arxiv.org/pdf/2607.19361)
- Did not inspect "Scalable Hierarchical Attention Transformers for Multi-Turn Jailbreak Detection" (2606.21082) or "D-Judge" (2606.02640).

## 4. Multi-turn jailbreak / conversation-level detection that accumulates risk across turns: does any use formal sequential tests?

### Takeaway
Yes, at least one: SafeDream (Apr 2026) uses a proper one-sided CUSUM with a benign-baseline drift, cites Moustakides' optimality, and shows CUSUM is what suppresses false alarms. The rest of the multi-turn literature accumulates via LLM context (sequential decomposition monitors), heuristic formulas (Peak+Accumulation), stateful firewalls, or cross-account clustering. None uses per-conversation or per-topic adaptive baselines (CFAR).

### Cited Findings
- SafeDream: CUSUM G_t = max(0, G_{t−1} + Λ_t − κ), with κ "the average log-odds under benign conversations"; a gray zone triggers world-model "imagination"; "CUSUM is essential for suppressing false alarms" (FPR rises to 13.8% without it) — [arXiv 2604.16824](https://arxiv.org/pdf/2604.16824)
- Salami Slicing (Zhang et al., arXiv 2604.11309, 13 Apr 2026): describes the attack as "chaining numerous low-risk inputs that individually evade alignment thresholds but cumulatively accumulate harmful intent". Proposes a defense, but full-text grep found no CUSUM/SPRT — [arXiv 2604.11309](https://arxiv.org/pdf/2604.11309)
- Peak+Accumulation: CUSUM-inspired but heuristic ("Accumulates deviations from an expected value; an alarm triggers when the cumulative sum exceeds a threshold" is given as an analogy) — [arXiv 2602.11247](https://arxiv.org/pdf/2602.11247)
- Monitoring Decomposition Attacks: LLM over cumulative prompt history; ICLR 2026 — [arXiv 2506.10949](https://arxiv.org/pdf/2506.10949)
- Stateful Online Monitoring (cross-account clustering, top-k score sums, "catching distributed attacks 30% earlier") — [arXiv 2605.31593](https://arxiv.org/pdf/2605.31593)
- Industry blogs describe "stateful prompt firewalls" with per-session risk that "increments when the latest turn nudges the trajectory in a dangerous direction, decrements on clean turns" (a CUSUM-like heuristic, no formal guarantees). Secondary sources — [AccuKnox blog](https://accuknox.com/blog/multi-turn-jailbreak-stateful-prompt-firewall); [FutureAGI blog](https://futureagi.com/blog/multi-turn-jailbreaking-defender-2026/)

### Inferences
- For multi-turn misuse, CUSUM is already published (SafeDream). A misuse-focused project would be incremental there unless it adds per-context baselines, anytime-valid guarantees, or adaptive-attacker analysis.

### Gaps
- Did not check whether Anthropic/OpenAI production classifier write-ups (e.g., account-level or "cumulative" misuse detection) use formal sequential tests; no public primary source found in these searches.

## 5. Conformal / anytime-valid monitoring of LLM outputs and agents: any per-context (Mondrian) calibration or online recalibration for agent monitors?

### Takeaway
Anytime-valid and conformal monitoring exists for agent success (E-valuator), LLM output safety (Online Safety Monitoring), generic deployment drift (WATCH), and agent failures (CURA via Learn-then-Test). None applies Mondrian/per-context calibration to misalignment or sabotage monitors in an AI-control setting. Mondrian per-group calibration appears only in agent evaluation/leaderboard work (AgentPulse), not monitoring.

### Cited Findings
- E-valuator: anytime-valid e-process for agent trajectories; its related work cites conformal test martingales for "continual monitoring of AI deployments" (Vovk) and WATCH — [arXiv 2512.03109](https://arxiv.org/pdf/2512.03109)
- Online Safety Monitoring for LLMs: risk-control-calibrated single threshold λ with false-alarm risk "R_I(λ) = P(∃ t ≥ 1 : s_t < λ | y = 1)"; compares against e-valuator variants — [arXiv 2607.02510](https://arxiv.org/pdf/2607.02510)
- WATCH: weighted conformal test martingales that adapt online to mild shifts — [PMLR v267](https://proceedings.mlr.press/v267/prinster25a.html)
- CURA: Learn-then-Test threshold on successful calibration runs, with "Pr(FPR(θ̂_α) ≤ α) ≥ 1 − δ" — [arXiv 2608.27808](https://arxiv.org/html/2608.27808)
- AgentPulse (Gao, Wang, Yu, arXiv 2605.19779, May 2026): split conformal + ACI for continuous agent evaluation, with per-agent conditional coverage. This is evaluation, not monitoring — [arXiv 2605.19779](https://arxiv.org/html/2605.19779)
- ConformalGuard (Bista et al., COLM 2026, arXiv 2610.14365): conformal FPR control for LM classifier action gating (phishing/moderation), with a global calibration set — [arXiv 2610.14365](https://arxiv.org/html/2610.14365)

### Inferences
- A project offering Mondrian (per-task/per-environment) conformal calibration of control-monitor thresholds, optionally feeding an anytime-valid or CUSUM accumulator, would be novel in the AI-control setting. It would need to address the Async Control caution that the untrusted model can poison honest calibration data.

### Gaps
- Did not find or verify a paper explicitly titled "conformal risk control for AI control monitors". Possibly unpublished, or hidden in workshop venues.

## 6. Per-context / per-task normalization of monitor scores, and monitor score calibration in agent settings

### Takeaway
Standard control practice is a single global threshold at a percentile (98th/99th/99.5th) of pooled honest scores, sometimes calibrated per attacker model or per monitor. Several papers observe that honest score distributions differ by monitor type, environment, and trajectory length. Some also observe that monitors fail to transfer across deployments without recalibration. Nobody in AI control sets thresholds per task or environment from that context's own honest baseline (CFAR). Adjacent-field precedents for local normalization exist (CPD, CURA, Dubey).

### Cited Findings
- LinuxArena (Redwood + EquiStamp, arXiv 2604.15384, Apr 2026): "At 1% stepwise FPR the threshold sits at the 99th percentile of the honest per-action score distribution ... The threshold is calibrated per attacker against its model-matched honest run" — per model, not per environment — [arXiv 2604.15384](https://arxiv.org/pdf/2604.15384)
- Persistent-state paper: thresholds from honest baselines, e.g. "a p98 threshold of 4.0", and "The full-diffs monitor sees the entire accumulated diff, so its honest scores run higher and its thresholds saturate". The honest distribution depends on context type — [arXiv 2607.02514](https://arxiv.org/pdf/2607.02514)
- Control OSWorld: max-aggregation inflates honest thresholds on long trajectories — [arXiv 2610.03818](https://arxiv.org/html/2610.03818v1)
- Constitutional Black-Box Monitoring for Scheming (Storf, Barton-Cooper, Peters-Gill, Hobbhahn; arXiv 2603.00829, Mar 2026): reports "Per-environment pAUROC" (evaluation breakdown), not per-environment thresholds — [arXiv 2603.00829](https://arxiv.org/pdf/2603.00829)
- Democratizing Agent Deployment Safety (Ravindra, Tiwari, Wolowski; arXiv 2607.14570, Jul 2026): "Thresholds for a given monitor are calibrated when an untrusted model runs with an honest policy only (n = 100 honest iac fast episodes pooled ...)" — a pooled global threshold — [arXiv 2607.14570](https://arxiv.org/pdf/2607.14570)
- Async Control: calibration-set sensitivity and red-team manipulation of calibration ("Recalibrating on this dataset modestly increases false negative rate from 7% to 9%") — [arXiv 2512.13526](https://arxiv.org/pdf/2512.13526)
- Dubey: cross-deployment transfer fails without recalibration (AUROC 0.527 vs 0.885) — [arXiv 2608.02464](https://arxiv.org/html/2608.02464v1)
- CPD Online: per-deployment robust baseline (median/MAD) from the fixed system prompt — [arXiv 2605.19966](https://arxiv.org/html/2605.19966v1)
- CURA: per-tool-type Gaussian normalization fit on successful runs — [arXiv 2608.27808](https://arxiv.org/html/2608.27808)
- GDM roadmap lists UEBA ("establishing a baseline of normal activity for users and network entities ... monitoring for deviations from this baseline") as a control measure — [arXiv 2607.13087](https://arxiv.org/html/2607.13087v1)
- Hua et al. note a related calibration issue: likelihood ratios instead of raw scores avoid treating chance-high scores as suspicious — [arXiv 2507.15886](https://arxiv.org/pdf/2507.15886)

### Inferences
- The CFAR component (per-task/per-environment honest-baseline normalization of suspicion scores before thresholding) has strong empirical motivation in existing papers: heterogeneous honest distributions, threshold saturation, and transfer failure. It has no direct implementation in the AI-control literature found here, so scooping risk for (a) in AI control is LOW. Adjacent-domain precedents (CPD, CURA, Dubey) should be cited.
- The main known risk to a CFAR design in control is calibration poisoning by the untrusted model (Async Control). A project should treat the per-context reference window as adversarially influenced, as in radar CFAR with interfering targets in the reference cells; e.g. use OS-CFAR/trimmed estimators.

### Gaps
- Did not inspect ControlArena or BashArena code for per-task threshold options.
- Did not find any LessWrong/AF post on "normalizing suspicion per task"; searched "AI control monitor threshold calibrated per task honest baseline normalization suspicion score" and "monitor honest suspicion score distribution varies across environments per-environment threshold AI control agent".
