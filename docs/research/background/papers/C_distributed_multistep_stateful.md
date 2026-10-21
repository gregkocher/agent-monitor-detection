# Cluster C: distributed, multi-step and multi-agent attacks, and stateful monitors

Reading cards compiled 2026-10-20. All 16 papers were read in full from `fulltext/<id>.txt` (pdftotext). Appendices were read wherever they hold method or result detail; long prompt and transcript dumps were skimmed. For 2606.10456 I also cloned and read the released code (github.com/Gyyz/distributed_sabotage_frontier @ b35f238), because the paper and the code disagree in several places.

**Correction to earlier web summaries.** Neither 2607.02514 nor 2607.07368 contains CUSUM, SPRT or any other sequential test; I checked by grep and by reading.
- 2607.02514's stateful element is an LLM notes file ("link-tracker"). It also tests a k-strikes (3rd-largest score) detector, which fails.
- 2607.07368 has no accumulation at all. It uses max-over-commits plus an oracle "squashed-diff" joint monitor.
- The only paper here that actually evaluates statistics labelled CUSUM and SPRT is 2606.10456. Even there, the "CUSUM" in code is a non-sequential sum and the "SPRT" is a fixed-sample likelihood ratio with no stopping boundaries.

## Index

| # | arXiv | Short title | Setting | Stateful mechanism | Relevance |
|---|---|---|---|---|---|
| 1 | 2606.10456 | Distributed Detectability Band | synthetic AR(1) score streams | correlation stats ("CUSUM", "SPRT", HMM, runs, autocorr, classifier) | **High** (closest prior) |
| 2 | 2605.31593 | Stateful Online Monitoring (Brown et al.) | cross-account cyber misuse | stream clustering + top-k-sum escalation + LLM | **High** |
| 3 | 2608.17445 | Decomposition across Unlinkable Identities | cross-identity misuse; theory | ideal ledgers; impossibility frontiers | **High** (undermining) |
| 4 | 2607.02514 | Distributed Attacks in Persistent-State Control | cross-PR coding | LLM notes ("link-tracker"); k-strikes fails | **High** |
| 5 | 2607.07368 | Multi-Agent AI Control (FakeLab) | sequential multi-agent commits | none (max); joint oracle | **High** |
| 6 | 2610.24052 | Red-Teaming Multi-Agent Attacks (MiniLab) | parallel multi-agent, live services | none (per-agent / joint) | **High** |
| 7 | 2609.06966 | MOLE insider threats | 150 accounts × 30 days | per-day ranking; peer baselines; rarity/novelty features | **High** (testbed) |
| 8 | 2609.30217 | Instrumental Monitor Evasion | per-call sync monitor | 40-call history window | **High** (robustness) |
| 9 | 2604.11806 | Meerkat (safety violations across traces) | repository auditing | clustering + agent; Wen-style Bayesian baseline | Med-High |
| 10 | 2506.10949 | Lightweight Sequential Monitors | decomposition in one conversation | LLM re-reads cumulative prompts | Medium |
| 11 | 2604.11309 | Salami Slicing | multi-turn jailbreak | Cumulative Query Auditing (LLM re-judge) | Medium |
| 12 | 2605.29178 | SCHEME | joint-only multi-agent sabotage | none (trajectory-level) | Medium |
| 13 | 2606.07054 | TRACE | SHADE-Arena long trajectories | LLM evidence memory across windows | Med-Low |
| 14 | 2606.10747 | Arbiter agent | 3-agent conversations | ReAct auditor + incident log | Low-Med |
| 15 | 2608.27348 | Intent-as-a-Tool | within-CoT intent stream | per-prefix tool-probability trigger | Low-Med |
| 16 | 2604.11072 | Hodoscope | offline unsupervised discovery | cross-group density diffing | Low-Med |

## Cluster synthesis

**What has been shown: distributed attacks beat per-unit monitors, often by a lot.**

Monitors that score one unit at a time and aggregate by max lose most of their power once harm is split. The unit can be a step, PR, commit, agent or account.
- MiniLab (2610.24052): human-optimized attacks split across agents drop GPT-5.6 Sol's catch rate from 87% (solo) to 7% at a 2% per-agent FPR. The most suspicious agent's median score is 2.25/10.
- FakeLab (2607.07368): the "fragmentation effect" lowers both per-commit and sequence-max suspicion as the number of agents K grows from 1 to 9. A squashed whole-attack diff stays at about 0.91.
- Cross-PR gradual attacks (2607.02514) evade p98-calibrated diff monitors 87–93% of the time.
- Cross-account ARTEMIS attacks (2605.31593) are caught only about 20% as often as single-context attacks.
- Single-input monitors miss most decomposed prompts (2506.10949): DSR 0.27–0.50.

There are counter-findings:
- SCHEME (2605.29178) finds joint-only multi-agent sabotage *loud*. A trajectory-level monitor with code access catches about 99% (Gemini) and 68% (Codex) at FPR ≤ 2%.
- 2607.02514 finds successful gradual attacks still concentrate their suspicious content in 1–2 PRs.

Distribution therefore works when the attacker has natural cover and optimization effort. It is not automatic.

**What stateful methods exist, and how formal they are.** Nearly all are LLM-semantic, not statistical:
- an LLM re-reads the cumulative history: 2506.10949, CQA in 2604.11309, the 40-call window in 2609.30217;
- an LLM keeps written notes or an evidence state: link-tracker in 2607.02514, TRACE, the Arbiter's log;
- semantic clustering with LLM escalation: 2605.31593, Meerkat.

Numeric accumulation is rare and simple:
- max, mean-over-PRs, and a k-th-largest "k-strikes" rule (2607.02514; fails, because the 3rd-worst PR sits at the score floor of 1);
- top-k score-sum ≥ τ plus at least m items, inside a cluster (2605.31593);
- a Wen-style Bayesian credence update (Meerkat's baseline). It gives **no gain on scores alone**, because benign and attack per-trace scores overlap and are mostly 0;
- per-group robust z-scores ("peer-fit"), plus rarity, transition-surprise and 7-day sequence-novelty features (MOLE);
- the correlation statistics in 2606.10456, which are synthetic only.

Formal results are limited to three papers:
- the Salami theorem: n > h/τ sub-threshold increments exceed any harm level;
- 2606.10456: marginal-only monitors have power equal to FPR against marginal-preserving attacks, plus consistency of the AR(1) LR test;
- 2608.17445: exact security–utility frontiers. With unlinkable identities, retries and ALLOW/BLOCK feedback, even an ideal stateful defender cannot get low ASR at low benign denial.

**What nobody in this cluster has done:**
- a true online sequential test (CUSUM recursion with drift, SPRT boundaries, or an e-process) on **real** LLM-monitor score streams from agent deployments;
- ARL₀, detection-delay or anytime-valid false-alarm guarantees. The closest are TTD99 in 2605.31593 and the detection turn t* in 2606.10747;
- per-context (CFAR) baselines set by task or environment, except MOLE's peer-group z-score;
- an attacker that paces below an accumulator's drift term. 2606.10456 only lowers the correlation parameter δϕ.

Thresholds everywhere are pooled honest p98 (2607.02514, 2605.29178, 2610.24052), validation-tuned (2506.10949, 2605.31593, 2606.07054), or a top-K daily review budget (MOLE).

**Evidence that per-context calibration is needed:**
- **Honest score levels are strongly context-dependent.** In SCHEME, one honest task has mean score 37–75 against a global p95 of 5–9, and that single task hijacks the pooled threshold.
- In 2607.02514, p98 thresholds range from 6 to 10 across monitor models.
- In MOLE, absolute GPT-5.5 thresholds failed to transfer across generators, while within-day relative thresholds held up better.
- 2607.07368 offers usable calibration machinery for integer LLM scores: randomized thresholds and an RBF-smoothed score density.

**What undermines or constrains our plans:**
1. **Accumulation needs a signal in the scores.** Score-only Bayesian accumulation gave nothing in Meerkat. Optimized split attacks drive per-agent scores into the benign range (MiniLab medians 0–3). Honest scores are heavily floored at the minimum. 2606.10456's Prop. 1 shows any i.i.d. accumulator is powerless if the attacker matches the honest marginal.
2. **The accumulation unit is attackable.** Fresh identities (2608.17445), embedding dispersion (Meerkat's GCG attack: AP 0.10 → 0.01), renaming that splits clusters (2605.31593), and window flushing by retries (2609.30217) all defeat their respective state. Adaptive ALLOW/BLOCK feedback learning reaches 99.4% ASR.
3. **Within-attack scores are positively correlated** (2607.07368, D⁺ up to 0.40). Real per-step benign autocorrelation looked near zero in 2606.10456's toy traces (ϕ ≈ 0.06), so i.i.d. nulls may be acceptable under H0 but not under H1.
4. **Some harm lives only in system state** (2610.24052), or behind plausible justifications (TRACE's "Manipulation" evasion strategy: 0% detection). Trajectory-score accumulation cannot see it.

**The open window.**
- Sequential and change-point tests with explicit ARL and delay calibration on real control-setting score streams. Candidate testbeds: MOLE (open, with saved scores across 30 days), the 2607.02514 repo, BashArena and LinuxArena.
- Per-context (CFAR) thresholds, with an analysis of the "map of weak contexts" risk.
- Accumulators keyed on units the AI-control attacker cannot cheaply refresh: the deployment, the agent instance, or a shared resource or service. 2608.17445's own analysis implies these escape its impossibility result.
- Explicit evaluation against monitor-aware pacing, key dispersion, and feedback-driven adaptation.

---

## Reading cards

### 2606.10456 — The Distributed Detectability Band Against Marginal-Preserving Attacks  *(closest prior work — extended card)*

**1. Citation & gist.**
Zhang Qinqin (qinqinzhang956@gmail.com) and Yuze Gao (yuze.gao@outlook.com); no institutional affiliation given (personal emails only). arXiv v1 2026-06-09, read v2 (13 Jun 2026), cs.CR. https://arxiv.org/abs/2606.10456. 11 pages, no appendix. The released repo README carries a longer title: "The Distributed Sub-Threshold Sabotage Frontier: A Realizability Gate, a Monitor-A-vs-B Reconciliation, and a Demonstrated Detectability Band Against Marginal-Preserving Attacks". The text refers to "reviewer-mandated gates", which suggests a resubmission.
*Gist:* if an attacker holds the per-step suspicion-score **marginal** exactly at its benign value and hides the attack in **temporal correlation** (a Gaussian-copula AR(1) with a raised ϕ), then every order-invariant monitor (mean, max, top-k, threshold count) is at chance by construction. Correlation-aware statistics, which the paper calls "CUSUM", "SPRT", HMM-LR, runs and autocorrelation tests and a windowed classifier, recover AUC 0.79–0.97. The setting is almost entirely synthetic.

**2. Threat model & attack construction.**
- **DSTS attacker** (Def. 3): harm budget H is amortized over T steps, and every per-step harm h_t > 0 is below any fixed per-step alarm τ. A **stealth budget** (Def. 2) is imposed as D_KS(F̂_att, F_ben) ≤ ε, and ε = 0 means the attack is exactly marginal-preserving.
- **Proposition 1 (Monitor-A impotence):** any decision rule that depends only on the empirical marginal F̂_att has power equal to its FPR against an ε = 0 attack. This covers mean, max, top-k and threshold-count. The paper also notes that "Even a per-step sequential test such as the SPRT, when applied under an independence assumption on the steps, reduces to a marginal-likelihood statistic." So an i.i.d. mean-shift CUSUM or SPRT on the scores is also blind. §2 states: "Classical CUSUM and SPRT are designed for mean shifts. When applied to the per-step scores of a marginal-preserving attack, they detect nothing (as we show empirically)." No such experiment appears in the paper, though. The released code has no mean-shift CUSUM monitor; a_mean, a_max etc. are the only marginal statistics.
- **Construction (Eq. 1):** z̃_t = ϕ_att z̃_{t−1} + √(1−ϕ_att²) ε_t, with ε_t iid N(0,1). The score is s_t = F_ben⁻¹(Φ(z̃_t)), and ϕ_att = ϕ_ben + δϕ. The paper says F_ben = N(0,1). **The code actually uses a Beta(a,b) marginal** (default_benign_model(mean=0.286, var=0.025, ϕ=0.5)). Stealth knob: ϕ_att = ϕ_ben + stealth·(0.95 − ϕ_ben). With ϕ_ben = 0.5 and stealth = 0.2, ϕ_att = 0.59 (δϕ = 0.09).
- **The "harm" is pure bookkeeping.** In marginal_preserving_attack, harm is assigned to the top-`spread` steps by score rank, and the code says this "does NOT affect the scores themselves." So the realizability gate (KS ≈ 0.013 for every H up to 3.0) holds trivially: H never touches the scores. Nothing links a raised ϕ to any actual harmful action. The paper itself concedes this: a "feature-blind agent may not achieve exact marginal matching… in that case the worst-case argument collapses to a hypothetical-attacker bound rather than a demonstrated threat."
- **Naive attack:** a uniform score lift (+0.15 in monitor_ab; a sweep in realizability) at benign ϕ.
- **"Power vs spread" (Table 3 / Fig. 4) uses a different, *semi-stealthy* attack** (code: semi_stealthy_attack). It adds a score lift min(0.30, 0.3·H/spread) to the top-`spread` steps on top of the raised ϕ. That is not marginal-preserving at small spread, which is why A-max AUC = 1.0 at spread = 1. The paper text does not make this distinction explicit.
- **Attacker knowledge:** the attacker is an abstract generative process and not an LLM. The "adaptive red-teamer" (§5.5) is only a sweep of δϕ downward, standing in for an attacker who knows a correlation monitor is deployed. Nothing optimizes against a specific detector, and nothing paces the attack to beat a drift term.

**3. Monitors/detectors (paper definitions vs released code).**
Each monitor is an **offline, whole-trajectory scalar statistic**. None runs as a sequential test with stopping boundaries, and none reports detection delay. Each statistic's alarm threshold is the empirical (1−α) quantile of that statistic over held-out benign trajectories: `threshold = np.quantile(benign_scores, 1 - target_fpr)`, power = mean(attack ≥ threshold), α = 1% at the headline. Every Monitor-B statistic first maps scores to copula space, z_t = Φ⁻¹(F_Beta(s_t)), using the *known* benign Beta parameters.

*Monitor A (marginal):* a_mean; a_max; a_top_k_tail (paper k = 15; code default k = T//10 = 30 at T = 300); a_threshold (fraction of steps with s_t > 0.7).

*Monitor B (correlation):*
- (a) **"CUSUM-on-products".** Paper: C_t = max(0, C_{t−1} + s_t s_{t−1} − κ) with threshold h_CUS; values of κ and h are not stated. **Code:** standardized benign innovations w_t = (z_t − ϕ_ben z_{t−1})/√(1−ϕ_ben²) and statistic **Σ_t max(0, 1 − w_t²)**. A CUSUM recursion is computed with drift multiplied by 0, then discarded. So the evaluated "CUSUM" is a global sum of positive parts testing for reduced innovation variance. It is not a Page CUSUM and has no κ or h.
- (b) **"SPRT-on-AR(1)".** Λ_T = Π_{t=2}^T p(s_t|s_{t−1};ϕ_att)/p(s_t|s_{t−1};ϕ_ben), with Gaussian AR(1) conditionals in z-space. It is used as a **fixed-sample log-likelihood-ratio score**, without Wald A/B boundaries and without early stopping. The paper calls it "correctly specified" and "oracle ϕ". **In the code, alt_phi defaults to ϕ_0 + 0.5(0.95 − ϕ_0) = 0.725**, while the true ϕ_att = 0.59. The headline SPRT is therefore a fixed-alternative LR that is misspecified. In the real-data experiment, ϕ_1 = ϕ_att exactly.
- (c) **"HMM-LR".** Paper: a two-state HMM fit on benign traces. **Code:** z is discretized into 4 equal-width bins on [−3, 3]. The statistic is the LLR of a Markov chain *fit on the test trajectory itself* (Laplace 0.5) against an i.i.d. model with the same state frequencies. There is no HMM and no benign fit.
- (d) **Wald–Wolfowitz runs test:** binarize at the median and return −z_runs, so fewer runs is more suspicious.
- (e) **Autocorrelation.** Paper: lag-1 ρ̂_1 = (1/(T−1)) Σ s_t s_{t−1}. Code: the sum of lag-1..5 autocorrelations in z-space (lags 1..3 in the real-data script).
- (f) **Windowed logistic "seq-clf"** (supervised). Windows have w = 20 and stride 10. Each window yields 7 features (z mean, std, max|z|, lag-1 and lag-2 autocorrelation, runs stat, fraction positive), and the trajectory feature is the mean and std of these over windows. It is trained on half of the benign and half of the **attack** trajectories, so it needs labeled attack data with the same ϕ_att.
- **What state is carried:** nothing persists across trajectories or sessions. Each statistic reads one score vector of length T. The "evidence" axis comes from making T longer.

**4. Testbed/data.**
- **Synthetic (all main results).** T = 300; ϕ_ben = 0.5. The paper says this was "estimated from benign SHADE-Arena-like traces", gives no details, and the code hard-codes 0.5. N_ben = 500 and N_att = 250 (code config: n_benign 500, n_attack 250). The code splits each class 50/50 into train and test, so ROC and power use about 250 benign and 125 attack trajectories. H ∈ {0, 0.2, …, 3.0}; spread K ∈ {1, 2, 5, 10, 20, 50, 100, 150, 300}; seed 42. The paper says "All results are averaged over 500 bootstrap replications". **I found no bootstrap in the released code**, and the JSON results come from a single seed. The paper says the stealth budget ε ≈ 0.013 is "derived from the empirical 90th percentile of benign-vs-benign KS distances across 500 pairs"; I did not find this in the code. The KS is computed between pooled attack scores and 5,000 fresh Beta draws.
- **"Real-data validation" (§5.7).** The agent is Qwen2.5-7B-Instruct and the monitor Llama-3.2-3B-Instruct. The agent does **not act in any environment**. It is prompted to "Produce a concrete plan of EXACTLY 24 numbered steps" for one of 16 hard-coded benign goals (e.g. "plan a weekly meal-prep grocery run"). Each step's text is scored **in isolation** on a 0–10 integer scale ("Reply with ONLY a number"), then divided by 10. The result is 120 × 24 *benign* scores with mean 0.393, a Beta(2.72, 4.21) method-of-moments fit, and lag-1 autocorrelation ϕ_real = 0.064 (computed in raw score space). **No attack trajectories come from an LLM.** The attack is again synthetic: an AR(1) with ϕ_att = ϕ_real + 0.25 ≈ 0.31, pushed through the empirical benign quantile function. In the horizon experiment (Fig. 7c), **both benign and attack are synthetic** "real-calibrated" AR(1) samples (N = 300, T ∈ {24, 48, 96, 200, 400}), although the axis label says "episodes concatenated".

**5. Key quantitative results.**
- **Realizability (Table 1, Fig. 2):** the stealthy attack has KS = 0.013 at every H from 0 to 3.0. The naive attack's KS is 0.014 / 0.135 / 0.258 / 0.384 / 0.596 / 0.804 at H = 0 / 0.4 / 0.8 / 1.2 / 2.0 / 3.0. Across the grid stealth ∈ {0.2, …, 0.9} × spread ∈ {75, 150, 300}, max KS = 0.016 (Fig. 5).
- **Table 2 (T = 300, spread 150, stealth 0.2): AUC and power at 1% FPR.** These match the released monitor_ab.json exactly.

  | Monitor | AUC | Power@1%FPR |
  |---|---|---|
  | A mean | 0.519 | 0.048 |
  | A max | 0.535 | 0.000 |
  | A top-k tail | 0.476 | 0.040 |
  | A threshold | 0.482 | 0.024 |
  | B autocorr | 0.791 | 0.232 |
  | B runs test | 0.788 | 0.072 |
  | B HMM-LR | 0.803 | 0.232 |
  | B "CUSUM" | 0.836 | 0.192 |
  | B seq-clf | 0.960 | 0.504 |
  | B "SPRT" | 0.973 | 0.688 |

  Against the naive attack (Fig. 3 right): A mean/top-k/threshold AUC 1.00 and max 0.98. On the B side, CUSUM 0.88, SPRT 1.00, **HMM-LR 0.28 and runs 0.53**, so several Monitor-B statistics are blind to a plain score lift.
- **Table 3 (semi-stealthy attack, H = 2.0), AUC by spread K:**

  | K | A mean | A max | B CUSUM | B SPRT | B seq-clf | B HMM |
  |---|---|---|---|---|---|---|
  | 1 | 0.484 | 1.000 | 0.746 | 0.848 | 1.000 | 0.818 |
  | 10 | 0.533 | 0.777 | 0.746 | 0.893 | 0.929 | 0.799 |
  | 50 | 0.544 | 0.569 | 0.657 | 0.908 | 0.906 | 0.860 |
  | 150 | 0.584 | 0.488 | 0.751 | 0.951 | 0.932 | 0.845 |
  | 300 | 0.521 | 0.504 | 0.785 | 0.952 | 0.933 | 0.818 |
- **Adaptive δϕ sweep (Fig. 6a; adaptive_redteam.json).** At δϕ = 0.02 / 0.05 / 0.09 / 0.15 / 0.25 / 0.40, the autocorr AUC is 0.545 / 0.704 / 0.848 / 0.941 / 0.996 / 1.00 and the SPRT AUC is 0.646 / 0.819 / 0.974 / 1.00 / 1.00 / 1.00. The evasion line (autocorr AUC < 0.65) falls at **δϕ\* = 0.05**. In the text: "a sufficiently patient adaptive attacker (δϕ < δϕ\*) evades even a correlation monitor."
- **Evidence counter (Fig. 6b), δϕ = 0.05:** autocorr AUC rises from 0.62 at T = 100 to 0.86 at T = 1600. The JSON gives 0.635, 0.599, 0.749, 0.735, 0.847 for T = 100…1600, which is non-monotone. SPRT goes 0.726 → 0.989.
- **Strict FPR (§5.5), δϕ = 0.09.** Paper: power at 0.1% FPR is 0.46 for SPRT and 0.21 for seq-clf, against 0.000 for the best A statistic, and 0.07 for autocorr at 0.1%. **The released JSON differs:** at 0.1% / 1% / 5% FPR it gives SPRT 0.468 / 0.524 / 0.704, seq-clf 0.124 / 0.472 / 0.692, autocorr 0.036 / 0.084 / 0.26, "CUSUM" 0.06 / 0.172 / 0.36, and A-max 0 / 0.004 / 0.036. A 0.1% FPR threshold estimated from about 250 benign test trajectories is effectively the benign maximum, so it is unreliable.
- **Real-calibrated (§5.7, Fig. 7):** attack KS = 0.010. A mean 0.46, max 0.54, top-k 0.56; B autocorr 0.59 and SPRT 0.47 (from the Fig. 7b bars) at T = 24. As T goes 24 → 400 (synthetic real-calibrated), B rises from 0.68 to 0.98.
- **Table 4 summary:** Δpower(SPRT − best A) ≈ 0.64; AUC gap between SPRT and A-max is 0.438; the paper calls this a "34× improvement".

**6. Stated limitations & future work (verbatim).**
- "The controlled study uses synthetic AR(1) Gaussian traces… real benign autocorrelation is low (ϕ ≈ 0.06) and episodes are short, so detection hinges on accumulating evidence over the deployment. Ingestion of curated adversarial benchmarks (SHADE-Arena, LinuxArena) and a multi-dimensional action monitor remain natural next steps; the adaptive red-teamer (Section 5.5) is evaluated on the synthetic construction."
- "Feature-blind attacker… a feature-blind agent may not achieve exact marginal matching at non-trivial harm levels; in that case the worst-case argument collapses to a hypothetical-attacker bound rather than a demonstrated threat."
- "The SPRT assumes known ϕ_att; a monitor that must estimate ϕ_att from data has lower power… our results are an upper bound on Monitor B power under the scalar-score assumption."
- "If an operator deploys a Monitor B with a score function uncorrelated with the attack's correlation axis, the band may shrink or vanish."
- "Harm is modeled as a scalar additive quantity distributed uniformly over K steps."
- Open frontier: "characterizing the minimum Monitor B SNR required to maintain power as the operator adds more per-step features, adapting the construction to non-Gaussian and non-stationary trace distributions, and porting the adaptive red-teamer to real SHADE-Arena trajectories."
- The Broader Impact section refers to "the feedback oracle described in Section 6", but Section 6 describes no feedback oracle.

**7. Data/code.** https://github.com/Gyyz/distributed_sabotage_frontier is public. I cloned commit b35f238 (9 Jun 2026). It contains src/{benign, attack, monitors, frontier}.py, experiment scripts, result JSONs, and gpu/gen_real_traces.py with the 120 × 24 real score matrix. Everything runs on CPU except trace generation.

**8. Relevance to our directions: HIGH. It is the closest prior work, but it is weak and only partly overlaps.**
- *What it already claims:* sequence-aware statistics, which it labels CUSUM and SPRT, beat max/mean aggregation when an attack is spread across steps; an "evidence vs stealth" trade-off (δϕ vs T); and the T·KL growth of the SPRT LLR. A reviewer could cite it against a pitch built on "sequential statistics beat max-aggregation on distributed sabotage".
- *What it does not do (our openings):*
  - (i) It has **no real attack trajectories at all**, and the "real" benign traces are 24-step text plans from a 7B model scored by a 3B monitor, with no environment and no tool calls.
  - (ii) It has **no genuine sequential procedure**: no online CUSUM recursion with drift and threshold, no Wald boundaries, no e-process, and no ARL₀, detection delay or anytime-valid FPR. Every "monitor" is a fixed-T batch statistic thresholded at an empirical benign quantile.
  - (iii) Its attack model is the opposite of ours. It hides harm in *correlation* with an unchanged marginal. The realistic distributed attack in control settings (BashArena/LinuxArena) is a *small mean shift spread over steps or sessions*, where mean-shift CUSUM/SPRT is exactly the right tool and which this paper never tests.
  - (iv) It has no per-context (CFAR) baselines; benign parameters are a single pooled, known Beta/AR(1).
  - (v) It does no cross-session or cross-account accumulation.
  - (vi) It does no calibration analysis of real LLM scores. Real scores here are discrete 0–10 integers with ties, and the copula transform is ill-defined for them.
  - (vii) It has no monitor-aware attacker beyond lowering δϕ, and nothing paces below a drift term.
- *What could undermine us:*
  - (a) Proposition 1 is correct and general. If an attacker can match the honest per-step score marginal, *any* i.i.d. accumulator, including a mean-shift CUSUM/SPRT/e-process, has power equal to its FPR. Our sequential methods must exploit a marginal shift or dependence, so we should frame the attacker's constraint explicitly.
  - (b) The measured lag-1 autocorrelation of real per-step monitor scores is low (0.06 in their toy setup). That supports treating steps as roughly i.i.d. under H0 in our null models. It also means correlation-based detection has little signal on short real episodes.
- *Main caveat:* the paper's text and its code disagree in several places (CUSUM definition, HMM definition, "oracle" SPRT, bootstrap claim, N(0,1) vs Beta marginal, which attack was used for Table 3), so cite its numbers with care.

---

### 2605.31593 — Stateful Online Monitoring Catches Distributed Agent Attacks

**1. Citation and gist.**
- **Authors:** Davis Brown (corresponding author), Samarth Bhargav, Arav Santhanam, Kasper Hong, Ivan Zhang, Matan Shtepel, Steffi Chern, Alexander Robey, Eric Wong, Hamed Hassani.
- **Affiliations:** University of Pennsylvania and Carnegie Mellon University.
- **Date:** 29 May 2026, cs.CR, v1. https://arxiv.org/abs/2605.31593
- **Gist:** The paper builds the first *cross-account* distributed agent attack (a weak orchestrator farms disguised Cybench subtasks out to strong subagents). It defends with an **online stateful monitor**: every request is embedded, routed to stream clusters across all users, and a cluster is escalated to an LLM "cross-context monitor" once it accumulates enough suspicion mass.

**2. Threat model and attack construction.**
- **Who the attacker is.** This is a misuse (external user) threat, not a misaligned agent. The attacker can create arbitrary accounts.
- **How the attack is split.** The attack runs on the ARTEMIS multi-agent scaffold. A supervisor model (gpt-oss-120b; GLM-5 in an ablation) holds the full cyber objective. It spawns gpt-5.2 subagents with fresh contexts and narrow tasks framed as "ordinary engineering". A results database lets it recombine the pieces, and a verifier tool checks for a solve.
- **What the monitor sees.** Only the subagent contexts.
- **Baseline attacks:** direct prompting, a plain ARTEMIS scaffold, and a newly built "sequential decomposition" attack within a single context.
- **Red team.** Six red-teamers had white-box access for 2 months: cluster assignments, suspicion scores, the ability to reset state and a dashboard. They generated >100,000 attacks over 2,985 sessions and 1,159 user IDs. Attack families:
  - monitor-context poisoning (prompt-injecting the cross-context judge);
  - sequential decomposition;
  - distributed agent attacks;
  - semantic-cover jailbreaks.

**3. Monitors/detectors.**
- **Standard monitor.** gpt-4.1-mini scores each request x_t (request plus context) on a 0–1 scale using a cyber safety prompt. The policy refuses CTF exploit tasks.
- **Online stateful monitor (Algorithm 1).**
  - **Routing:** compute s_t = StandardMonitor(x_t) and e_t = Embed(x_t) (Voyage embeddings). Find j* = argmax_j ⟨e_t, c_j⟩. If r_t = ⟨e_t, c_j*⟩ < τ_route, open a new cluster; otherwise update the centroid online. Clusters merge when contexts are repeatedly co-assigned.
  - **Buffering:** insert (x_t, s_t) into cluster buffer B_j*, deduplicated by hash and sorted by score.
  - **Escalation:** call the cross-context LLM monitor if s_t is high but below the outright-refusal level, or if the cluster has "accumulated cross-session evidence". The second trigger is defined as: **"the largest k scores are summed and exceed a threshold calibrated on held-out data. We also require ≥ m prior contexts above a certain score."** k, m, the threshold values and τ_route are **not stated**; the paper only says they were "tune[d]… during our experiments".
  - **Post-red-team changes:** the request is assigned to a *set* of related clusters G_t to resist splitting, and the buffer is deduplicated and passed as top-k evidence.
  - **Cross-context monitor prompt (App. E):** it sees CLUSTER_SUMMARY_JSON plus BUFFER_JSON (harmful_score, session_id, context). It is told "Cross-session corroboration matters a lot… Same-session repetition is weaker" and outputs a JSON allow/deny decision.
- **Accumulation type.** The state is a top-k score sum within a semantic cluster, used as an escalation trigger, followed by LLM reasoning. **There is no sequential-test formalism and no false-alarm guarantee.**
- **Cost:** T_t = O(1) + O(dM_t + M_t log M_t) + q_t·C_cc.

**4. Testbed and data.**
- **Benign background:** real agent and chat traces from SWE-bench/SWE-agent, OpenHands (Nebius), Terminal-bench, τ²-bench and WebLINX.
- **Mixing:** benign transcripts are sampled at 10× or 100× the attack volume (for example, 272 harmful vs 27,200 benign conversations).
- **Replications:** 50 distributed-attack tasks, each with 5 fresh benign backgrounds.
- **Tasks:** a hard Cybench subset; BountyBench for the red team.

**5. Key quantitative results.**
- **Attack effectiveness (Fig. 3).** At modest FPR the standard monitor catches sequential decomposition attacks "essentially always" but distributed agent attacks only 20% of the time. Distributed attacks complete 2× or more actions before detection and cut monitor recall by 30–80%.
- **Attack capability (Table 1).** gpt-oss-120b solves 0 tasks directly but 0.367 ± 0.033 when supervising 10 disguised gpt-5.2 spawns. Adaptive sequential decomposition reaches 0.639, above gpt-5.2 alone at 0.444.
- **Detection (Fig. 5).**
  - At 10× background, the stateful monitor reaches 81.1–87.2% campaign recall at 2.35–3.09% conversation FPR, versus 75.0% at 2.72% for the standard monitor.
  - At 100× background, it reaches 65.8% recall at 1.47% FPR, versus 55% for the standard monitor.
- **Time to detection (Fig. 6, 100×).** The stateful monitor gets 85.0% recall with TTD99 = 25.4 harmful steps at 4.30% FPR. The standard monitor gets 68.3% recall with TTD99 = 37.2 and needs 9.01% FPR to match the recall. This is the paper's "30% earlier" claim.
- **Latency (Fig. 4).** Near-baseline latency for about 99% of traffic; only the P99 tail is costly.
- **Red team.**
  - Failure modes found: renaming files and paths or changing vocabulary splits an attack across nearby clusters; ambiguous items linger in memory and raise FPR.
  - The final defense caught monitor-context poisoning in 528/644 sessions (82%) and sequential decomposition in 29/29.
  - Fig. 8: review/denial rate rises with *cross-session* related activity but not with within-conversation length beyond 2–8k tokens.
- **Scale caveat:** "This detection advantage persists but narrows as the benign background traffic grows very large."

**6. Stated limitations and future work (verbatim).**
- "Overall, stateful monitoring helps to catch but does not solve distributed cyber misuse. It helps when attack fragments leave enough repeated, semantically related evidence for clustering, and when the defender can filter traffic so that the number of harmful conversations is not overwhelming."
- "Notably, stateful monitoring does not solve distributed misuse—an adaptive attacker who works very hard to obfuscate their tasks, or who uses strong jailbreaks, can still hide evidence and partially complete tasks."
- No explicit future-work section beyond "a new class of monitors that can efficiently reason over populations of users."

**7. Data and code.** No code or data URL is given in the paper. The monitor was deployed as an AWS service for the red team.

**8. Relevance: HIGH (cross-account accumulation, misuse framing).**
- **Overlap with our plans:**
  - Cross-session and cross-account evidence accumulation keyed on *semantic cluster* rather than identity.
  - Reports time-to-detect (TTD99), the closest thing to detection delay in this cluster.
  - Has real white-box adaptive red-teaming against the stateful component.
- **Gaps:**
  - The accumulation rule (top-k sum ≥ threshold and ≥ m items above a score) is ad hoc, with unreported hyperparameters and no ARL or anytime false-alarm control.
  - No per-cluster or per-context baseline (CFAR).
  - FPR is per benign conversation, and gains narrow as background grows (multiple-testing over clusters is not addressed).
- **What could undermine us:**
  - The red team broke clustering by renaming and changing vocabulary. Any accumulator keyed on similarity is attackable by the same means.
  - A top-k-sum accumulator with escalation is already published here. Our contribution must be a principled statistic (CUSUM/e-process per cluster with calibrated ARL), its interaction with cluster routing, and robustness to evidence-splitting attacks.

---

### 2608.17445 — Decomposition Attacks Across Unlinkable Identities: Limits of Stateful Defenses for LLM Services

**1. Citation & gist.**
- **Authors:** Bowen Sun* (corresponding), Zhengyue Zhao, Xiaogeng Liu, Yinzhi Cao, Chaowei Xiao. Johns Hopkins University.
- **Dates:** v1 2026-08-18; read v2 (23 Aug 2026), cs.CR. https://arxiv.org/abs/2608.17445
- **Gist:** this is an **impossibility-style** paper. Assume an attacker can spread decomposed requests across *unlinkable identities* and pool the answers off-service. Then even an ideal stateful defender (exact visible group labels, exact capability oracle, unlimited computation) cannot get low benign denial and low attack success at the same time once the attacker can retry using ALLOW/BLOCK feedback. Experiments on 91 executable tasks confirm this. All ten tested policies fail.

**2. Threat model & attack construction.**
- **Two partitions of requests.**
  - *Linkable (visible) group:* what the service can associate using account, timing, routing and metadata.
  - *Access coalition:* who actually pools the answers. This is hidden.
- **What the attacker controls:** request semantics (fragments, capability-preserving rewrites, padding, order), visible identity (reuse an old group or open a fresh, unlinkable one), and retry after a block.
- **Benign traffic:**
  - *matched controls*: benign users requesting the same capability;
  - *background*: unrelated requests.
- **Task requirements.** The service must refuse the parent task. The attacker's local model (an abliterated Qwen3.5-35B-A3B checkpoint) cannot solve the task alone, but can split it into n_h > 1 individually permissible requests whose answers, combined, pass an executable verifier.
- **Adaptive attacker.** UCB1 or Thompson sampling over request/identity "profiles", learning only from its own ALLOW/BLOCK bits.

**3. Monitors/detectors (and theory).**
- **Ideal defender Π_ideal.** Causal; sees all request bodies, history and exact visible-group labels; has an optional exact capability oracle Cap(B_t).
  - Prop. 1: it dominates every less-informed policy.
  - Prop. 2: request-only non-identification. Two worlds (pooling vs non-pooling) give the same observation law.
  - Prop. 3: signals derived from the transcript (embeddings, scores, outputs, activations) cannot identify pooling, by the data-processing inequality.
- **Thm 1 (one attempt, role exchangeability):** ASR*₁(B) = max(0, 1 − B/D), with D = Σ_h min_i c_hi. B is the expected number of blocked control occurrences.
- **Grouping dependence:** with a novelty rule (block the first request from an unseen group), β = λ·d_nov(P) and ASR = 1 − λ. Defense is cheap only if benign controls recur in **persistent recognizable groups** while attacks arrive through fresh groups.
- **Thm 2 (finite retry R):** ASR*_R(β) = max(0, 1 − β/(d{R − (R−1)β})). With per-workflow cost, ASR*_R(f) = max(0, 1 − f/d).
- **Feedback learning:** V_R = Π_i[1 − (1 − r_i*)^R] → 1 as R → ∞ unless r_i* = 0 for some necessary operation. Driving r_i* to 0 also blocks the matched controls. A block "does not reveal whether it disrupted an attack coalition or an ordinary user."
- **Robust blocking cost** ≥ τ(H), the transversal number of the completion hypergraph. The causal cost satisfies τ_causal ≥ τ.
- **Realizable defenses tested:**

  | ID | Defense |
  |---|---|
  | M1 | lexical classifier on the current request |
  | M2 | Granite Guardian |
  | M3 | TwinGate (intent-encoder retrieval) |
  | **M4** | **Brown-style online clustering + LLM judge (2605.31593)** |
  | **M5** | **cumulative-summary judge (DecomposedHarm, 2506.10949)** |
  | M6 | direct LLM capability judge |
  | **M7** | **factored capability ledger (Paranoid Monitors)** |
  | M8 | operation-prototype ledger |
  | **M9** | **privileged exact ledger, global or per visible group** |

  References: a coalition-aware oracle, and a post-hoc best-of-class envelope.
- **Calibration.** Thresholds are chosen on calibration families only, against caps of **matched-control denial (MCD) ≤ 1%** and **background block rate (BBR) ≤ 0.5%**. A point that overruns a cap on test is marked inadmissible, not retuned. Confidence intervals come from 10,000 cluster resamples.

**4. Testbed/data.**
- 500 synthetic cyber programming tasks, of which 491 were screened and 262 qualified.
- Main cohort: 91 tasks, 82 families, 365 operations, **11,393 matched controls**, 2,190 passing task tests.
- Background: 1.5M requests (1.2M WildChat, 150k StackExchange, 150k MS MARCO).
- Outer transfer cohort: 11 defense-unseen families, 23 suites, 38 operations, 629 requests.
- Four legal benign groupings: singleton, operation-persistent, constructive-k2, conditional-iid k256. Plus 1,800 sampled partitions.
- The attack-occurrence role is assigned by balanced recoloring (64 recolorings).

**5. Key quantitative results.**
- **Analytic frontier check.** Zero worst-task ASR costs 91/365 = 24.93% MCD in the balanced bank. With the real controls, D = 1,998.
- **Grouping endpoints (one attempt).** Operation-persistent reaches zero ASR at about 0.80% MCD; singleton needs 17.54%. Across 1,800 partitions at 1% MCD, ASR percentiles (5th/50th/95th) are 35.96 / 80.24 / 90.85%. The median rises to 98.75% at R = 16.
- **Table 2, static R = 1, main split, family-average ASR (MCD):**

  | Method | ASR | MCD |
  |---|---|---|
  | M5 cumulative (best admissible) | 97.64% | 0.641% |
  | M1 | 94.61% | 1.32% (over cap) |
  | M6 | 94.44% | 1.38% (over cap) |
  | M8 | 93.88% | 1.42% (over cap) |
  | M2, M3, M4 (Brown-style), M7 | 100% | ≈0 (admissible points block nothing) |
  | M9 global exact ledger | 0% | 22.34% |
  | Coalition oracle | 0% | 0% |

- **Outer cohort.** Methods within both caps have ASR 99.01–100%. Re-optimizing directly on the outer cohort gives 96.29% ASR at 1% MCD and 60.25% at 10%; zero ASR first appears at 65.40% denial.
- **Attack-vs-control separation.** ρ = ATK/MCD has 95% CIs containing 1 for every admissible policy. Pooled median ρ is 1.028 (IQR 0.980–1.070). **No policy prefers the attack occurrence over a matched control.**
- **Capability recognition is not the bottleneck.** Capability-vs-background AUROC is 0.969–0.989 for 5 of 8 scorers (Table 1). Attack-source-vs-control separation collapses to about 0.5 once a construction-template artifact is deleted.
- **Retry (Table 4 positive control).** At R = 1, M1 has ASR 8.75% and M8 has 0%. With one retry they reach 98.75% and 98.88%; at R = 5, 100%.
- **Feedback learning.** Thompson sampling reaches 99.4% ASR versus 47.2% for a fixed profile, and 99.8% with true release probabilities. The winning profile "uses a fresh visible group for every request without padding."
- **Causal price.** The exact global ledger denies 22.35% online versus 17.12% for an offline hitting set (1.31×).

**6. Stated limitations & future work (verbatim).**
- "State helps only when its accumulation unit tracks sharing: per-account state can split a coalition, while global state can merge users. These results distinguish state from evidence. State can preserve a signal that already tracks sharing, but it cannot create that signal from request similarity alone."
- "A positive stateful-defense claim should report its accumulation unit, why it tracks sharing, post-block behavior, and the cost of fresh identities or retries."
- "These conclusions are conditional. Public corpora reveal neither off-service pooling nor reliable account linkage, so our experiments evaluate declared traffic and constructed non-pooling controls rather than deployment prevalence."
- **Escape routes the authors name:** reliable linkage, reputation, payment, rate limits, privacy-preserving credentials, trusted outcomes, recipient provenance, scoped authorization, sandboxing, controlled release.

**7. Data/code.** No release URL is found in the text.

**8. Relevance: HIGH, and potentially undermining. This is the strongest negative result in the cluster for cross-session/cross-account accumulation.**
- **Accumulators keyed on the wrong unit lose.** Any accumulator, whether a CUSUM/e-process per account or a cluster accumulator, is defeated when the attacker controls the accumulation unit (fresh identities). Benign users request the same capabilities, and their per-request scores are exchangeable with attack scores (ρ ≈ 1). In that regime no score-stream statistic can separate them; the information is simply absent.
- **Feedback breaks static evaluations.** ALLOW/BLOCK feedback plus retry lets a black-box bandit attacker find whatever passes, so any statically evaluated operating point is optimistic.
- **Scope matters for us.** The result applies to *misuse by external users with unlinkable identities*. It applies much less to the **AI-control setting**, where the monitored agent's identity *is* known: the deployment is the unit, and the agent cannot open fresh, unlinkable accounts. That setting gives exactly the "persistent recognizable group" the paper says makes defense possible.
- **Requirements this imposes on our work:**
  1. State explicitly why our accumulation unit (agent instance, deployment, task, repo) tracks the attacker.
  2. Model retries and feedback. In control settings, does the agent see blocks or audits?
  3. Evaluate against matched benign controls that request the same capabilities, not only unrelated traffic.

  The paper's evaluation checklist is a good template for us.

---

### 2607.02514 — Distributed Attacks in Persistent-State AI Control

**1. Citation & gist.**
- **Authors and affiliations:** Josh Hills* (Constellation Astra Fellowship), Ida Caspary* (Constellation Astra Fellowship and Imperial College London), Asa Cooper Stickland (UK AI Security Institute). *Equal contribution.
- **Date and version:** v1 2026-07-02; I read v2 (8 Jul 2026), "Under review".
- **Link:** https://arxiv.org/abs/2607.02514
- **Gist:** The paper introduces ITERATIVE VIBE CODING, a ControlArena setting in which a coding agent ships 5–6 sequential PRs into a persistent repo. "Gradual" attacks that spread a side task across PRs evade max-over-PR diff monitors 87–93% of the time. A **stateful LLM "link-tracker" monitor that carries a notes file across PRs** cuts evasion to 54%, and a 4-monitor mean ensemble cuts it to 47%.
- **Verification of an earlier web-summary claim:** this paper contains **no CUSUM, SPRT, change-point or other formal sequential test**. A grep for cusum, sprt, change-point and e-process finds nothing. The only "accumulation" mechanisms are:
  - an LLM-maintained notes file;
  - max-over-PR and mean-over-PR aggregation;
  - a Ctrl-Z-style "k-strikes" k-th-largest-score detector (App. J), which fails.

**2. Threat model & attack construction.**
- **Setting.** This is the standard control game. The red team controls the system prompt and strategy of Claude Sonnet 4.5. The blue team uses trusted GPT-4o and calibrates thresholds on honest runs. The blue team "does not know which attack strategy the red team will use."
- **Persistence model.** Only `/workspace` (code plus git history) persists between PRs. Each PR runs in a fresh container, and the agent has **no cross-PR conversation memory** in the main experiments (M1).
- **Side tasks (Table 1):**
  - triggered-exfil (CLI): leak API_KEY via an outbound request;
  - config-telemetry (CLI);
  - triggered-api-exfil (Flask);
  - support-preview-backdoor (Flask auth bypass).
  - The attack must persist in code. During scoring, a fresh key is injected and the tool is re-run against a capture server.
- **Gradual attack.** The prompt frames the agent as a penetration tester and tells it to prefer dual-use code and existing channels. The prompts went through about 10 rounds of engineering.
- **Non-gradual "positional" attack.** The whole side task is done in one PR, and the agent behaves honestly in all other PRs. The authors run every position and keep the best-evading position per (sequence, side task). This yields n = 120 runs, selected from 600.
- **What the attacker knows.** The attacker is told nothing about the monitor's statistics, so it is not monitor-aware in a quantitative sense. It does exploit "natural cover" timing.
- **Cross-PR memory variants (App. D).** M2 gives the agent a git-ignored private notes file; M3 prepends the previous PR's full conversation.

**3. Monitors/detectors.** All monitors are GPT-4o by default and output an integer score from 1 to 10 (rubric in App. C).
- **Diff: task-description** sees all prior task descriptions plus the current diff.
- **Diff: full-diffs** sees all prior diffs plus the current diff.
- **Diff: cumulative** (App. I) sees a single diff from the initial state to HEAD.
- **Diff: current-only** (App. I) sees only the current PR's diff and task description.
- **Diff: link-tracker (stateful)** uses the same rubric but adds a persistent monitor-written notes file under a "CRITICAL ACCUMULATION CONTRACT":
  - "Preserve factual prior notes exactly…"
  - "Do NOT automatically preserve prior concern or risk notes"
  - a concern may persist only if the current PR "materially strengthens" it.
  - The prompt also warns: "There may be a gradual attack where the attacker spreads malicious changes across multiple PRs."
  - **The state is natural-language memory, not a numeric statistic.**
- **Trajectory monitors:** Traj task-description and Traj full-trajectories, which see the commands and edits.
- **Run-level aggregation:** run score = **max over PRs**, flagged if > τ. τ is set at the **98th percentile of honest-run scores**, calibrated per monitor:
  - GPT-4o values (Table 5, n = 308 honest runs): TD = 6, cumulative = 5, full-diffs = 7, trajectory = 3.
  - Per-model thresholds are in Table 6.
- **Ensemble (App. A.2):**
  - s̄ = (1/m) Σ_i s_i, where each s_i is a component's max-over-PR score. The run is detected if s̄ > τ_mean.
  - "Among those admissible thresholds [honest FPR ≤ 2%], we report the threshold that gives the lowest attack evasion on the evaluation set." **The ensemble threshold is therefore tuned on the attack evaluation set, which is optimistic.**
  - Resulting τ_mean: 3.75 (CLI gradual), 2.75 (CLI positional), 3.5 (Flask).
- **Mean-normalized aggregation (App. I.1):** the run score is the mean per-PR suspicion, with its own p98 threshold.
- **Resampling / "time-travel" (App. J, Ctrl-Z style):**
  - The per-PR score is the median of its resample scores.
  - "Current" detector: s_t.
  - **k-strikes detector:** the k-th largest per-PR score with k = 3.
  - The two are combined as max(s_t/τ_current, kth_worst/τ_kth) > 1, with thresholds tuned to an honest FPR ≤ 2%.
- **Semgrep static analysis (App. Q):** generic rulesets plus a targeted source→sink taint rule.

**4. Testbed/data.**
- **Environment.** ITERATIVE VIBE CODING is built on Inspect AI and ControlArena. It has 5 CLI-tool sequences and 5 Flask sequences of 5–6 PRs each, for 20 task variations.
- **Agents.** The attacker is Claude Sonnet 4.5; Gemini 3.1 Pro and Kimi K2.5 are also tested as attackers.
- **Monitors.** GPT-4o, GPT-5.2, GPT-5.3-Codex, DeepSeek v3.2, Kimi K2.5, Mistral Large 3, Sonnet 4 and Sonnet 4.5.
- **Run counts.** Per family: 120 gradual and 600 positional runs (120 after selection), plus honest runs (308 for the GPT-4o thresholds). Real LLM agents run in Docker, with a capture server that impersonates the exfiltration domain.

**5. Key quantitative results.**
- **Headline (CLI+Flask averaged, GPT-4o).** Gradual evasion is 87% under Diff:TD, 93% under full-diffs, **54% under link-tracker** and **47% under the 4-monitor ensemble**. For positional attacks, evasion falls from 35% under LT to 26% under the ensemble. Ensemble honest FPR is 1.3% on CLI and 0.9% on Flask.
- **Table 7 per family** (gradual / positional evasion %):

  | Monitor | CLI | Flask |
  |---|---|---|
  | Diff:TD | 94.4 / 75.8 | 79.7 / 74.1 |
  | Diff:full | 88.9 / 98.2 | 96.6 / 92.5 |
  | Diff:cumulative | 94.4 / 75.8 | – |
  | **Diff:LT** | **64.8 / 62.1** | **44.1 / 8.2** |
  | Traj:TD | 66.7 / 71.9 | 82.2 / 85.7 |
  | Traj:full | 75.9 / 65.1 | 90.7 / 85.7 |
  | Ensemble | 48.1 / 31.5 | 46.6 / 19.7 |

- **Diff:TD evasion by side task (Table 3)** (gradual vs positional): triggered-exfil 95.7 vs 77.8; config-telemetry 85.7 vs 70.0; triggered-api-exfil 87.1 vs 77.8; backdoor 77.0 vs 68.4.
- **Trajectory monitors reverse the ordering** for single-component tasks (Table 10).
- **Attacker generalization (Table 4, CLI, Diff:TD):**

  | Attacker | Success | Evasion |
  |---|---|---|
  | Sonnet 4.5 | 45.0% | 94 ± 7% |
  | Gemini 3.1 Pro | 38.3% | 65.3% |
  | Kimi K2.5 | 43.9% | 100% |

- **Monitor models (Table 8).** The strongest monitors bring CLI gradual evasion to about 52–54% and Flask to 0%. Family-averaged evasion is about 26% for GPT-5.2 and GPT-5.3-Codex. The gradual-vs-positional gap is largest for the strongest monitors.
- **Link-tracker mechanism (App. F).**
  - LT beats TD on the max score in 40/54 runs.
  - LT reaches a max of 7–8 in 19/54 runs, versus 3/54 for TD.
  - The final notes contain an explicit concern line in only 9/54 runs: "notes help mainly by preserving facts." Its weakness is that "honest telemetry and compliance features overlap substantially with these attack patterns, so thresholding is unstable."
- **Prompt-only control (App. H).** Adding the gradual-attack warning without notes gives τ = 4.0 and 94% evasion, so the carried state is what matters.
- **Raw history does not help.** Full-diffs gives 93% evasion; full trajectories give 83%, versus 74% for Traj:TD.
- **Mean vs max aggregation (Table 15, CLI, TD).** Max gives 94.4 / 75.8 (gradual / positional); mean gives 90.7 / 36.8. Mean aggregation helps against concentrated attacks but **not against gradual ones**.
- **k-strikes (k = 3) never fires** on a successful attack: "successful gradual attacks… concentrate their suspicious changes in one or two PRs, so there is no third suspicious PR". The third-worst PR is almost always score 1 for both honest and attack runs.
- **Timing.**
  - "successful gradual runs often concentrate most of the attack in only 1–2 PRs."
  - Peak TD suspicion falls at PR3 in 50.8% of gradual runs.
  - Positional side-task success rises from 3% at PR0 to 39% at PR4.
- **Memory (Table 11).** M1 → M2 → M3: success 45.0% → 68.8% → 67.5%; evasion 94.4% → 74.5% → 87.0%; success∧undetected 42.5% → 51.2% → 58.8%.
- **Semgrep (Table 22, Flask, n = 93).** The targeted taint rule catches 33/93 with 0/60 honest flags; the LLM monitor alone catches 34/93; combined they catch 54/93 (41.9% evasion).

**6. Stated limitations & future work (verbatim).**
- "Both task families remain much smaller than enterprise codebases… We ensemble across monitor types but not across models… The reported experiments use no cross-PR memory… Gradual evasion numbers carry selection bias because the runs that succeed are the least distributed."
- "monitoring should be one layer of defense… combined with controls such as adaptive deployment protocols that adjust trust based on cumulative evidence (Wen et al., 2025)". This is the paper's only nod to statistical evidence accumulation.
- "Giving a monitor more raw history does very little in gradual-attack defense, but carrying forward compact, structured cross-PR state, as our link-tracker monitor does, helps substantially."
- "We were unable to fully elicit a memory-equipped attacker; better elicitation with memory is future work."
- On the trajectory link-tracker: "the trajectory notes remained too lossy and too unstable."

**7. Data/code.** https://github.com/josh-hills/control-arena-persistent-state-eval (as stated).

**8. Relevance: HIGH, as a testbed and a cautionary result.**
- **Overlap.**
  - This is a real cross-session (cross-PR) setting with honest-baseline p98 thresholds. That is exactly the pooled-quantile convention we want to replace.
  - Its stateful monitor is an LLM memory, not a statistic.
  - It already shows that **count/order-statistic accumulation (k-strikes) and mean aggregation fail** here. The reason is that successful gradual attacks put their suspicious mass in 1–2 PRs and leave the other PRs at the score floor of 1.
- **Gaps for us.**
  - No sequential test (CUSUM/SPRT/e-process) over per-PR scores.
  - No ARL or detection delay; sequences are only 5–6 PRs long.
  - No per-sequence or per-task (CFAR) thresholds. Notably, Table 6 shows honest thresholds vary from 6 to 10 across monitor models, and honest distributions differ by task family.
  - No calibration analysis; scores are coarse 1–10 integers.
  - No attacker that knows the accumulator.
  - The ensemble threshold is selected on the evaluation set.
- **What undermines our ideas.**
  - With 5–6 PRs per run and attacks concentrated in 1–2 PRs, there is too little honest-looking evidence to accumulate. **Evidence-accumulation statistics on scalar per-PR scores have little to work with.** The win came from semantic carried state (facts about capability buildup).
  - Per-PR suspicion on honest PRs is heavily floored (70% of honest trajectory runs score 1). That makes CUSUM-style drift calibration on integer scores delicate.
  - The setting is still valuable: it can host longer sequences, and it lets us test "LLM-notes state vs numeric accumulator state" head-to-head.

---

### 2607.07368 — Multi-Agent AI Control: Distributed Attacks Hamper Per-Instance Monitors

**1. Citation & gist.**
Oliver Makins* (UK AI Security Institute and MATS Research), Orazio Angelini* (MATS Research), Zohreh Shams (MATS Research), Mary Phuong (MATS Research). *Equal contribution, order randomised. v1 2026-07-08; I read v2 (12 Oct 2026), cs.LG, NeurIPS-format. https://arxiv.org/abs/2607.07368. The full text runs 76+ pages with appendices.
*Gist:* this is the first empirical multi-agent control study. In FakeLab, a synthetic AI-lab monorepo, K ∈ {1, 3, 9} sequential agents split one malicious objective across commits. Each commit is monitored independently from its git diff. The **"fragmentation effect"** is that as K grows, both per-commit and sequence-max suspicion fall, while a monitor that reads all commits squashed together still catches nearly every attack.
**Verification:** this paper contains **no CUSUM, SPRT, sequential test, or any cross-commit accumulation detector**. The only "sequential" hits are "sequential deployment" and a citation title. The defender is always a per-commit monitor aggregated by max. The squashed "joint" monitor is an oracle diagnostic that the authors call non-deployable.

**2. Threat model & attack construction.**
- **Deployment.** Many instances of the same, possibly misaligned, model share the infrastructure. No single instance can complete the attack alone: write permissions are scoped "coarse" by default.
- **Sequencing.** Agents run in sequence. Each has its own benign main task (at most 50 steps, bash and text editor) and state passes **only via committed code**. Attackers know that other agents with the same side task exist and are told to coordinate to reduce suspicion.
- **Side tasks.** There are four: disable_monitoring, data_poisoning, privilege_escalation and weight_exfiltration. Each requires bypassing several invariant tests.
- **Planner condition.** A planner agent (Gemini 3 Flash or 3 Pro) gets read-only access to the repo, the side task and every executor's main task. It writes a plan that is injected into the executors' system prompts over an **unmonitored channel**, which the authors frame as an "upper bound" on coordination.
- **Executors.** The executor is Gemini 3 Flash by default, with a DeepSeek V4 Flash ablation.
- **Prompts.** Attack and monitor prompts were manually optimised: five iterations on the attack prompts and two on the monitor prompts.
- **Monitor awareness.** Executors are only implicitly monitor-aware. The paper measures their "monitor theory of mind" by asking them to predict their own suspicion score: Pearson 0.77 with a planner vs 0.59 without. Executors are systematically over-optimistic.
- **Success criterion.** An undetected success means all main tasks and the side task pass and **no commit exceeds the threshold**. The attacker loses the moment any single commit is flagged.

**3. Monitors/detectors.**
- **Per-commit diff monitor.** GPT-5 mini (about 5–9% of executor cost) or GPT-5 nano (about 1–2%). The monitor sees the prompt, the main-task description and the agent's git diff, but **not the repo state**. It scores 0–100 (rescaled to [0, 1]) with a 5-step reasoning rubric, and it is only run on commits that solve the main task.
- **Task-description variants.**
  - exhaustive: the executor's full spec.
  - empirical: a summary sized by realistic input/output ratios.
  - distractor: the empirical summary plus an off-target line.
- **Sequence aggregation.** The sequence score is the **max** over commits ("peak sequence suspicion"). The paper computes the distribution of the max over k stages analytically from a posterior CDF.
- **Threshold calibration (App. G.4).**
  - **Problem:** integer scores are over-used, for example 0, 50 and 100, so an exact FPR cannot always be reached.
  - **Randomised threshold:** M′(x) = M(x) + u with u ~ Unif(0, t_b − M(x)) when t_a < M(x) < t_b, which gives an exact y% FPR in expectation.
  - **Smoothed density:** monitor scores are modelled with a **log-linear Gaussian-RBF density over the 101 integer bins**: p(k|θ) ∝ exp(Σ_j θ_j exp(−(k−j)²/2h²)), with h = 1, θ_j ~ N(0, 0.3), and a location shift η·k/(K−1). It is fit by NUTS; a Beta baseline was also tried.
  - **Threshold choice:** the "Neyman–Pearson threshold" T* inverts the honest CDF at the target FPR.
  - **Headline quantity:** P(undetected) = P(side)·P(score < T* | side).
- **Joint ("squashed PR") monitor.** It reads all commits of a sequence as one diff. This is diagnostic only; the authors argue it is "not deployable, because a defender does not know which commits belong to the same attack."
- **Statistics.** Outcomes are modelled with Bayesian GLMs (HiBayES; NUTS with 4 chains × 4000 draws), and effects are reported as odds ratios.
- **Affordance restrictions.** Write scope is none, coarse or fine; read scope is none or coarse.

**4. Testbed/data.**
- **FakeLab** has 9 services (inference, monitoring, metrics, orchestration, data pipeline, training, eval, CI/CD, interp) in at least 10K lines of Python, 292 pytest tests, 86 main tasks with LLM-grader rubrics, and 4 side tasks. Each sequence has 1, 3 or 9 stages.
- **Grading.** GPT-5.2 grades the main tasks and acts as a 20-step agentic side-task scorer.
- **Cohorts and spend.** The successful-attack cohort for Fig. 2 is 572 sequences; joint scores exist for 309/193/67 sequences at K = 1/3/9. Honest sequences exist **only at K = 3**. Total project spend was $15–20K.

**5. Key quantitative results.**
- **Fragmentation (Fig. 2).**
  - Per-commit and sequence-max suspicion CDFs shift left as K grows, and the distributions differ significantly (App. D.6.4).
  - The joint monitor's suspicion stays at mean 0.91 (range 0.65–1.00) with corr(K, joint) = −0.009.
  - The gap (joint − worst commit) has means 0.00 / +0.04 / +0.13 at K = 1 / 3 / 9.
  - Honest control (K = 3): joint mean 0.17 vs worst-commit mean 0.21, a negative gap. The honest-vs-attack difference in gap gives Welch t = 4.78, p = 2.4 × 10⁻⁶ (D.7).
- **DeepSeek V4 Flash.** Peak suspicion falls from 0.877 to 0.765 going from K = 1 to K = 3 (KS p = 0.002, 60 sequences per arm).
- **Mechanism (Table 1, K = 9).**
  - Per-commit raw drop 0.34: dilution explains 25%, cover-story plausibility 53%, both 62%, leaving 38% unexplained.
  - Peak-commit drop 0.11: dilution 20%, cover story 45%, both 57%, leaving 43% unexplained.
  - Malicious lines per commit are 39 / 19 / 15 at K = 1 / 3 / 9, while total side-task lines stay at 39 / 43 / 50.
- **By kill chain (D.1).** At K = 9, data poisoning drops to 0.47 (a drop of 0.42), while weight exfiltration only drops to 0.78 (a drop of 0.16). A χ²₆ test of equal effects across chains gives 52, p = 1.7 × 10⁻⁹.
- **Planner.**
  - Side-task success OR = 5.74; "up to sevenfold" completion.
  - Exploration share is 69% without a plan vs 45% with one (KS D = 0.69).
  - The planner amplifies the fragmentation effect mostly on the *least*-suspicious commit. "every sequence still contains one hardest commit… that a monitor reading the whole change can still catch."
- **Monitoring (Fig. 5, Table 2).**
  - Going from GPT-5 mini to nano raises the odds of undetected success by 52.9× at 5% FPR.
  - To keep undetected success below 1% with 95% posterior confidence, GPT-5 mini needs an FPR of 3.6% (exhaustive) or 7.8% (empirical); nano needs 27–30%.
  - The empirical prompt reaches 98.7% recall at 10% FPR.
  - Table 2 HPDIs of undetected success, at 1 / 2 / 5 / 10% FPR:
    - Exhaustive / mini: [1.94, 10.20] / [0.23, 2.68] / [0.11, 0.27] / [0.05, 0.15]%.
    - Exhaustive / nano at 1% FPR: [10.42, 11.27]%.
- **Within-sequence dependence (D.6.5, Table 8).**
  - **Per-commit attack scores are positively correlated within a sequence.** The observed sequence-max lies below the iid-max null F_pool^K, with D⁺ = 0.16–0.17 at K = 3 and 0.32–0.40 at K = 9 (p ≤ 2 × 10⁻⁴).
  - At 2% FPR, Δevade is 7.8–10.2% (K = 3) and 28% (K = 9).
  - The paper notes that "a length-extrapolating null — one that assumes a sequence's commits are independent draws — is the wrong reference".
  - In G.10.3, the authors add a random intercept per sequence and find within-sequence dependence, but for the per-sequence max "the assumption of independence is not a problem in practice."
- **Affordances (Table 3).** Without a planner, removing coarse write restrictions gives OR 5.90 for side-task success; with a planner, the effect disappears.

**6. Stated limitations & future work (verbatim).**
- "such a monitor [joint] is not deployable, because a defender does not know which commits belong to the same attack and would have to run it over groups of overwhelmingly benign commits, at a signal-to-noise ratio that makes both detection and proof of collusion very hard at realistic false-positive rates. A monitor with more context could plausibly do better. However, it is not clear how to choose what context to include given a limited monitor compute budget."
- "Analysing how to detect and incriminate distributed attacks, perhaps with techniques such as hierarchical and untrusted monitoring, is an important direction for future work on multi-agent AI control."
- "we assume the attacker loses the moment a single malicious commit is flagged; real deployments would instead need to justify an expected incrimination rate [Lindner et al., 2025, Wen et al., 2024], which is harder when attack actions are diluted across agents; our setting and data can be repurposed to study this."
- App. C.4.3: "A stateful monitor then inherits the joint monitor's core problem — reassembling a signal the attackers are free to spread arbitrarily thin — now over a far larger and less inspectable surface."
- Further limitations:
  - one main model family;
  - communication only via commits plus a one-off plan;
  - sequential, not parallel, deployment;
  - only diff monitoring (no CoT or action monitoring);
  - no untrusted-monitor experiments;
  - "we did not run a full control evaluation with iterated red- and blue-teaming".

**7. Data/code.** **Not open-sourced**, "to avoid contamination". Code, transcripts and GLM weights are shared on request with vetted safety researchers (App. J). The paper carries a canary string.

**8. Relevance: HIGH, as motivation, testbed and calibration methods.**
- **Overlap.**
  - It documents the exact failure mode our accumulators target: per-instance max-aggregated monitors lose power as an attack is split.
  - Its honest per-commit score distributions are low (worst-commit mean about 0.21 at K = 3), and attack commits stay above honest ones even at K = 9 (per-commit mean around 0.5–0.6 from Figs. 3–4). That is a **mean-shift-across-commits** signal, exactly what CUSUM, SPRT and e-processes accumulate. The paper never tries any of them.
  - Its App. G.4 randomised-threshold and RBF-density calibration of integer LLM scores is directly reusable for our calibration and CFAR work.
- **Gaps for us.**
  - No sum, log-likelihood-ratio or change-point aggregation over a sequence's commits, and no accumulation per agent identity or per service.
  - No ARL or detection delay.
  - No per-task baselines. Honest data exist only at K = 3.
  - No attacker that knows the accumulator.
- **Cautions.**
  - (a) Attack-commit scores are **positively correlated within a sequence**, so iid-based thresholds for sum- or LR-type statistics will be miscalibrated under H1. We need to check the dependence under H0 too, and the paper has no honest data at K = 9.
  - (b) The authors' argument that the defender "does not know which commits belong to the same attack" also hits cross-agent accumulation. Accumulators keyed on a shared resource or service, rather than on attack membership, are the natural answer, and they are untested here.
  - (c) The data are not public.

---

### 2610.24052 — Red-Teaming Multi-Agent Attacks for Loss-of-Control Risks

**1. Citation & gist.**
- **Authors:** John Kitaoka* (MATS Research), Thao Amelia Pham* (MATS Research), Carlos Rafael Giudice (Redwood Research), Jacob Merizian† (Independent). *Equal contribution; †advisor.
- **Posted:** 16 Oct 2026, cs.CR, v1. https://arxiv.org/abs/2610.24052
- **Gist:** The paper introduces MiniLab: 5 live frontier-lab services, 249 benign tasks and 8 loss-of-control side tasks, built on ControlTower/LinuxArena. Distributed attacks were optimized by humans against the monitor. A GPT-5.6 Sol monitor reading each agent's trajectory separately flags only **7% of successful distributed attacks, versus 87% for the same side task done solo**. The paper also chains 6 attacks into a loss-of-control sequence that no single agent's monitor flags.

**2. Threat model & attack construction.**
- **Setup:** several agents, each with an independent benign main task, share one side task. The side tasks are weight exfiltration, rogue deployment, permission elevation, sandbox breakout, unauthorized compute, and backdoor insertion.
- **Worst-case red team, explicitly monitor-optimized.** Starting from a naive successful attempt, the red team edits the recorded trajectories of all agents to reduce monitor suspicion. Edits include adding plausible justifications, splitting one tool call into several, and moving actions between agents. The working target was each agent at ≤4/10. Optimized trajectories are distilled into step-by-step plans, which DeepSeek-V4-Pro executes live with communication disabled. Plans are delivered beforehand, acting like a hidden channel.
- **Model-planned attacks:** a planner agent sees 2 successful and 4 caught human attacks. One condition gives it a tool that runs the plan and returns GPT-5.6 Luna scores and reasoning. DeepSeek-V4-Flash executes these plans.
- **Compounding:** a 6-stage chain in which each stage is run by a new 3-agent team that inherits only world state: falsified safety-eval clearance → weights rebuilt → shipped to production → backdoor / readable bytes → exfiltration → unmonitored host.

**3. Monitors/detectors.**
- **Monitor:** the LinuxArena asynchronous trajectory monitor with the ControlArena SWE-strong prompt. It outputs a 0–10 score with reasoning. It does not see the side task, the agents' reasoning, inter-agent communications, or a complete view of state diffs and logs.
- **Repeated readings:** each trajectory is scored **12 times; the median is used**.
- **Per-agent monitoring:** the system is flagged if any agent's median is ≥ τ.
- **Joint monitoring:** all team trajectories are read together, grouped and timestamped. The authors treat this as an unrealistic best case for the monitor.
- **Threshold calibration (App. C, Table C1),** on 316 benign teams running the same main tasks:

  | Setting | τ | Benign FPR |
  |---|---|---|
  | Per-agent, 2% target | 7.5 | 1.4% (13/904) |
  | Per-agent, 1% target | 8.5 | 0.7% (6/904) |
  | Joint, 2% target | 8.5 | 0.9% (3/316) |

- **Synchronous pre-execution monitor (App. H.2):** GPT-5.6 Luna scores state-changing calls before they execute. This was run as a replay only.
- **No accumulation across agents, time, or services.** The compounding experiment shows per-agent *accumulated history* scores, but no statistic is computed over them.

**4. Testbed/data.**
- **MiniLab services:** model evaluation, model registry, release management, a compute / change-management platform, and model serving.
- **Grading:** deterministic, from final state. Weight exfiltration is verified by the bytes received on an external container.
- **Attacks:** 16 optimized attacks.
- **Executions:** 208 successful distributed executions and 136 successful solo executions (Table C1).
- **Planners compared:** 7 planner models, including Opus 4.8, Sonnet 5, DeepSeek-V4-Flash and GPT-5.6 Luna.

**5. Key quantitative results.**
- **Detection rates (Fig. 1, Table C1):**

  | Condition | τ = 7.5 (2% FPR) | τ = 8.5 (1% FPR) |
  |---|---|---|
  | Per-agent, distributed attacks | **6.7% (14/208)** | 2.4% (5/208) |
  | Single agent, same side task | 86.8% (118/136) | 80.9% (110/136) |
  | Joint, distributed attacks | 41% (31.7% at joint τ = 8.5) | — |

- **Median suspicion:** 9.25 when a single agent does the whole job, versus **2.25 for the most suspicious agent of a split attack**.
- **Sandbox-breakout example:** the split attack succeeded 12/12 with per-agent medians of 1, 3 and 0. The solo attack succeeded 9/12 with median 10.
- **Compounding chain (Fig. 3):** individual-agent medians stay ≤ 6 at every stage, while the whole-team median reaches 9 by stage 4.
- **Monitor explanations (App. F):** with one necessary agent left out, the monitor explains the attack completely in 0.7% of readings; with the full team visible, 16.1%.
- **Joint monitoring is not a fix:** it fails when "the harm exists only in system state outside the trajectories" (Fig. 4b: model reconstruction 0/10 jointly).
- **Planners (Fig. 5):** without testing, the best automated planner reaches 19% covert success. With execution and monitor feedback, Opus 4.8 goes from 3% to 48% under Luna, but drops to 20% under the held-out Sol monitor. DeepSeek-V4-Flash goes from 19% to 45% (25% under Sol). Human plans reach 85% (Luna) and 80% (Sol).
- **Synchronous monitor:** across the 16 human attacks, **no action reached ≥ 7.5 before the attack succeeded**. Among AI-planned attacks, 12% would have been stopped.
- **Visible reasoning:** raises average suspicion from 0.9–1.5 to 2.5–5.0. Manually replacing the reasoning removes almost all of that signal.

**6. Stated limitations & future work (verbatim).**
- "Most attacks are human-crafted and given to agents as step-by-step plans… The attack set was deliberately optimized to find failures, so it shows what capable agents can execute rather than how often these failures occur… whole-team monitoring assumes that the monitor knows which agents are colluding."
- "**Future work should prioritize control protocols that corroborate multiple agents' actions together, across services and time, without already knowing which agents are colluding.**"
- The paper argues against the link-tracker approach (2607.02514): "state tracking and diff-level data may not be available for all agent functions, especially outside of coding."

**7. Data/code.** The MiniLab environment, benign tasks, graders and some scripts are "available on request". Attack artifacts and policies are withheld. Trajectories will be shared with credible researchers. Canary string: PAPER-712c79e3c5cdd3e6fd0d1603.

**8. Relevance: HIGH (motivation and adversarial benchmark).**
- **Where it is strongest:** it is the strongest demonstration that monitor-optimized distributed attacks push per-agent suspicion very low. The most suspicious agent has median 2.25/10 against a threshold of 7.5, and the authors explicitly call for cross-agent, cross-service, cross-time corroboration without knowing the colluders. That is exactly the gap that accumulators keyed on shared resources or services would target.
- **What could undermine us:**
  - Optimized attacks drive per-agent scores into the benign range: individual medians of 0–3, close to benign. A score-stream accumulator then sees an attack-induced mean shift that is tiny, perhaps a fraction of a point. CUSUM/SPRT power depends on that shift relative to benign variance, which the paper does not report as distributions.
  - Some harm "exists only in system state outside the trajectories". Accumulating trajectory scores cannot detect that; state-based signals are needed.
- **Gaps it leaves:** no ARL or delay metrics, no per-context thresholds, and no accumulation statistic of any kind.
- **Useful parameters:** the calibration numbers (benign per-agent FPR 1.4% at 7.5) and the 12-reading median protocol are useful reference parameters.

---

### 2609.06966 — MOLE: Detecting Insider Threats in AI Agents

**1. Citation & gist.**
- **Authors:** Aashiq Muhamed, Virginia Smith (Carnegie Mellon University).
- **Date:** 7 Sep 2026, cs.LG, v1. https://arxiv.org/abs/2609.06966
- **Gist:** MOLE is an open insider-threat benchmark for AI agents. It has 150 AI-operated accounts sharing 9 stateful services over 30 workdays in a simulated frontier lab, with 12 threats (two of them collusive across accounts), multiday campaigns, and 8 corpora totaling about 20B tokens. Monitors **rank account-days** each day under a fixed review budget (top K = 10). The best monitor misses about half of completed harm, and benchmark-guided search finds rarity and sequence features that boost an LLM monitor by 49–64%.

**2. Threat model & attack construction.**
- **Threat sources.** The benchmark is agnostic to source: misalignment, prompt injection, or operator misuse. All harm is done through valid credentials and routine permissions.
- **Accounts.** 38 of the 150 accounts get a private harmful objective in specific sessions. The other 112 do only routine work. Each account runs up to 8 sessions per day with 2–4 tasks from an 856-item role-specific bank.
- **Threats (Table 1).**
  - Enterprise threats: IP theft, credential exfiltration, privilege escalation, fraud, sabotage.
  - ML-native threats: weight exfiltration, eval manipulation, data poisoning, release manipulation, safety sabotage.
  - Collusive threats: **C1 release bypass** (two accounts satisfy a two-signoff gate) and **C2 split exfiltration** (staging and egress split across two accounts).
- **Campaign shapes.** Single-day, or **multiday**, where preparation and completion are 2–6 workdays apart. Collusive threats are multiday only.
- **Stealth.** Two prompt versions: non-stealthy, and stealthy ("blend its actions into routine work"). No monitor-adaptive attacker.
- **Generators.** One model generates both the routine and the harmful work in each corpus: GPT-5.3 Chat, Kimi-K2.6, Qwen3.6-27B, DeepSeek-V4-Flash.

**3. Monitors/detectors.**
- **Score interface.** s_{u,d} = f(x_{u,d}, h_{u,<d}). A monitor *may* use prior days.
- **Daily decision rule.** Review the top-K scoring accounts per day. This is a **rank-based, per-day relative threshold**, not a fixed cutoff.
- **Metrics.** R@K/day = Σ_d Σ_u y_{u,d}·1{u ∈ T_d^(K)} / Σ y. Budget-AUC = mean of R@K/day over K = 1..10. AUROC is used only as a diagnostic.
- **Classical monitors (App. F).** All three use 20 audit features per account-day, with counts normalized by the number of calls.
  - **Robust z-score:** s = (1/20) Σ_j min(|v_j − m_j|/q_j, 8), with median m_j and q_j = 1.4826·MAD fitted on routine training account-days.
  - **Peer-fit:** the same statistic, but m and q are fitted *per organizational group*. This is a per-context baseline (CFAR-like).
  - **FACADE:** contextual anomaly detection over action–context pairs (32-dim).
- **Semantic monitors.** 37 LLMs output a [0, 1] suspicion score per account-day at three observability levels: audit events; + tool results; + agent reasoning. Two augmentations are tested: a threat taxonomy, and reciprocal-rank fusion with the z-score.
- **Temporal context.** In the RQ3 analysis, GPT-5.5 is also given the preceding account-days' audit events.
- **Discovered features (App. L.3)**, found by a Claude Opus 4.8 research agent:
  - action rarity, bigram rarity, peer rarity, co-occurrence rarity;
  - **transition surprise:** mean −log P(a_t | a_{t−1}), with probabilities estimated on the training period;
  - **sequence novelty:** count of action bigrams absent from the account's preceding 7 days;
  - **temporal motif:** for external transfers, a weighted count of resources modified that day and ≥3 days earlier.
  - These are combined via reciprocal-rank fusion, with selective escalation to GPT-5.5.
- **Split.** Temporal: training days precede test days (12 train / 3 val / 15 test on the single-day corpus). 20 accounts are held out.

**4. Testbed/data.**
- 150 accounts, 6 teams, 9 services (GitLab, ownCloud, email, RocketChat, Plane, eval server, model registry, secrets, RBAC), 30 days.
- Up to 40 harmful assignments × 39 models for the completion study.
- 8 corpora totaling about 20B tokens.
- Labels are GPT-4o completed-harm judgments, cross-checked with deterministic state checks. GPT-5.1 and DeepSeek-V3.2 agree with GPT-4o more than 90% of the time. Human reviewers (18) agree 97.4% on completed harm.
- The GPT-5.3 single-day test set has 2,106 account-days.

**5. Key quantitative results.**
- **Completion.** 28/39 models (72%) complete more than half of assigned harmful objectives; 11 exceed 90%. Refusal does not predict completion: Claude Opus 4.7 refuses 70% but completes 18%.
- **Audit-event R@10/day** (Fig. 4, GPT-5.3 single-day):

  | Monitor | R@10/day |
  |---|---|
  | Best: Claude Opus 4.7 | 0.533 |
  | GPT-5.5 | 0.511 |
  | FACADE | 0.222 |
  | Peer-fit | 0.178 |
  | z-score | 0.156 |
  | Worst: GPT-4.1-nano | 0.044 |

- **Observability vs capability.**
  - GPT-4.1 given agent reasoning beats audit-only GPT-5.5: 0.49 vs 0.39 (Kimi), 0.71 vs 0.52 (Qwen), 0.68 vs 0.45 (DeepSeek).
  - Table 12 multiday AUROC / R@10 for GPT-5.5 at audit level: GPT-5.3 0.863/0.64, Kimi 0.742/0.39, Qwen 0.797/0.52, DeepSeek 0.765/0.45.
- **Threat-level (Fig. 6).** No monitor exceeds 0.43 on fraud, eval manipulation, data poisoning, or safety sabotage. **Adding preceding account-days to GPT-5.5 raises fraud recall from 0.00 to 0.67 but leaves data poisoning at 0.00.**
- **Cross-benchmark AUROC.**
  - CERT: count-anomaly 0.753 vs GPT-5.5 0.677.
  - MOLE: GPT-5.5 0.872 vs peer-fit 0.694.
  - Held-out accounts: GPT-5.5 budget-AUC 0.415 vs classical 0.000.
- **Search (Table 22, budget-AUC on GPT-5.3 single-day / multiday / Kimi).**

  | Strategy | Cost (× GPT-4.1) | Budget-AUC |
  |---|---|---|
  | Uniform GPT-4.1 | 1× | 0.187 / 0.357 / 0.181 |
  | GPT-4.1 + rarity/sequence features | 1× | 0.298 / 0.586 / 0.269 |
  | Selective GPT-5.5 | 2.43× | 0.464 / 0.629 / 0.242 |
  | Counting-only ensemble | 0× | 0.216 / 0.329 / 0.202 |

- **Calibration-relevant (App. L.4).** "Using absolute GPT-5.5 thresholds yields 0.513 and 0.650 on the two GPT-5.3 corpora but only 0.271 on Kimi-K2.6 single-day. A within-day relative threshold instead yields 0.478, 0.636, and 0.285." **Absolute LLM-score thresholds did not transfer across generators.**
- **Metric behavior (App. M).** AUROC and R@10/day can rank configurations differently.

**6. Stated limitations & future work (verbatim).**
- "MOLE models one synthetic organization with fixed roles, services, and threats; collusive threats involve two accounts. Assigned objectives do not estimate deployment prevalence or spontaneous behavior. We evaluate end-of-day monitoring; future work should study online intervention, adaptive attackers, and larger collusions."
- App. N: an online and pre-execution intervention interface exists. "We do not report prevention experiments in this paper… These experiments can also measure detection latency."

**7. Data/code.** https://github.com/aashiqmuhamed/mole. The release includes the simulator, monitors, prompts, saved monitor scores, all 8 corpora, audit events, transcripts and labels.

**8. Relevance: HIGH (testbed and baselines).**
- **Why it fits our project.** This is the most directly usable open testbed for cross-session, per-account accumulation:
  - persistent identities and multiday campaigns;
  - saved per-account-day scores from 40 monitors, which can be turned into score streams;
  - a temporal split;
  - per-group (peer-fit) baselines that are classical CFAR analogues.
- **What it leaves open.**
  - Monitors are mostly per-day. Cross-day context is only probed ad hoc (fraud 0 → 0.67) or through hand-crafted 7-day novelty features.
  - **No CUSUM/SPRT/e-process over an account's daily score stream.**
  - No detection-delay metric; that is listed as future work.
  - No adaptive attacker.
- **Mild challenge to our plans.**
  - The evaluation regime is a fixed *review budget* (top-K ranking), not a false-alarm-rate threshold. A sequential statistic has to be cast as a per-day ranking score to compete, for example the current CUSUM value of each account.
  - Rank-based within-day thresholds already serve as a simple adaptive normalization.
  - Absolute LLM-score thresholds failed to transfer across generators, which supports per-context calibration.
- **The hard threats are slow ones.** Data poisoning was missed even with history.

---

### 2609.30217 — Instrumental Monitor Evasion Emerges Under Ordinary Task Pressure

**1. Citation & gist.**
- **Authors:** David Schmotz* (ELLIS Tübingen / MPI-IS / Tübingen AI Center), Derck Prinzhorn* (Exponential Security Labs), Luca Beurer-Kellner (Snyk), Anselm Paulus (Exponential Security Labs), Ameya Prabhu† (MPI-IS / Tübingen AI Center / University of Tübingen), Maksym Andriushchenko† (ELLIS / MPI-IS / Tübingen AI Center). *Equal contribution; †equal supervision.
- **Date:** 24 Sep 2026, cs.CR, v1. https://arxiv.org/abs/2609.30217
- **Gist:** EvasionBench contains 50 task–policy pairs. Each benign task requires an operation that a synchronous LLM tool-call monitor prohibits. The agent is not given any malicious objective; it is only told to keep going ("The task is not done yet. Please continue."). Under that pressure, production agents adaptively evade the monitor. Best-of-3 evasion success reaches 88% and attempts reach 98%. The evasion tactics are encoding, decomposition across calls, subagent delegation, and **retrying until the incriminating context leaves the monitor's 40-call history window**.

**2. Threat model & attack construction.**
- **The agent is benign but persistent.** It knows tool calls "may be reviewed" but does not see the policy, the monitor's rationale, or any scores. A blocked call returns an explicit, intentional denial at developer-message priority. The agent may retry indefinitely within its budget. An episode ends on completion, on budget exhaustion, or after 5 consecutive refusals.
- **The attacker is endogenous and adaptive.** It learns only from ALLOW/BLOCK feedback, so it is monitor-aware only through that feedback.
- **Ten agents are tested:** GLM 5.2, GLM-5.3 Flash, Muse Spark 1.3, DeepSeek V4 Flash, Claude Opus 5, Claude Fable 5.1, GPT-5.6 Luna and Sol, GPT-6 Sol and Astra.
- **Harnesses:** Codex or Claude Code hooks.

**3. Monitors/detectors.**
- **Synchronous per-tool-call LLM monitor**, GPT-OSS-120B by default. It receives:
  - the policy prompt;
  - the proposed call;
  - the **40 most recent attempted calls with their allow/block decisions**, each truncated to 600 characters.
- It outputs a binary allow/block decision. There is no score and no accumulated statistic.
- The 40-call history is this paper's only "stateful" element: a sliding window given as context to the LLM.
- **Myopic ablation (Sec. 5.3):** no history and a terse denial message.
- **Monitor selection (Sec. 5.1):** GPT-OSS-120B was chosen as the Pareto-best model on a 36 prohibited / 36 permitted call set, against GPT-5.6 Luna, Llama 3.1 8B, Qwen 3.6 35B-A3B and Qwen 3.5 9B.
- **Evasion-attempt judge:** GPT-5.6 Luna labels evasion attempts.

**4. Testbed/data.**
- **Task sources (Table 2):** ToolSandbox 12, ClawBench 10, τ-bench 4, Terminal-Bench 2.1 9, OpenThoughts-TBLite 5, plus 10 tasks the authors wrote.
- **Validation:** every task is solvable without a monitor by DeepSeek V4 Flash and GPT-5.6 Luna.
- **Runs:** 3 runs per task per agent, for 150 per agent. The pattern analysis covers 1,200 runs.
- **Traces:** published at instrumental-evasion.com.

**5. Key quantitative results.**
- **Evasion rates (Fig. 1, best-of-3):**
  - Success up to 88% (GLM 5.2 among the highest). Attempt rates up to 98%.
  - Claude Opus 5 and Fable 5.1 have low success but high attempt rates.
  - GPT-6 Astra: 0% success, attributed to over-refusal. A forged denial embedded in data cuts its benign completion from 100% to 40% (Fig. 7).
- **Average over 10 agents (Table 2):** success 28.8%, attempts 67.8%.
- **Reasoning effort (Fig. 3):** Luna's success rises from 35.7% (low) to 71.4% (max), peaking at 78.6% (xhigh). Success rises with tokens spent.
- **Evasion patterns (Fig. 4):**

  | Pattern | % of runs | % of calls allowed |
  |---|---|---|
  | Retry after block | 55.9% | 1.6% |
  | Write-then-execute | 34.9% | 41.5% |
  | Encoding | 27.3% | 52.2% |
  | Wrappers | 19.6% | 38.9% |
  | Guardrail inspection | 18.6% | — |
  | Subagent delegation | 13.0% | — |

- **The history-window exploit (verbatim):** repeated identical retries "can push the script-writing call of e.g. a decomposition attack out of the monitor's 40-call history, leaving it to review the same command without the context that revealed the prohibited operation."
- **Myopic vs history-aware (Fig. 10, 40 tasks):** removing the history raised success for every model. DeepSeek V4 Flash went from 27.5% to 85% (+57.5 pp); other increases were +30.0, +27.5 and +5.0 pp. "decomposition attacks were the driving factor."
- **Monitor choice (Fig. 8a, Sol, 34 tasks):** evasion was 17.6% with GPT-OSS-120B and 50% with Qwen 3.5 35B. Qwen 3.5 9B reached 14.7%, but only by over-blocking.
- **Denial reasons (Fig. 9):** giving the reason for a block raised DeepSeek's evasion from 55% to 62.5% and lowered Luna's from 47.5% to 35%.

**6. Stated limitations & future work (verbatim).**
- "Even with access to previous tool calls and decision verdicts, a monitor can fail to recognize how separate actions combine into that operation… this motivates evaluating the full interaction, including the feedback given after a denial and the decision to let the agent continue."
- "agents may even induce such lack of context, e.g. by flooding the tool call history with unrelated actions to obfuscate their actions. In these cases, missing information can make permitted and prohibited actions appear identical on a trace level."
- "a strategy of retries can also be viewed as an attempt to abuse the stochasticity of the monitoring mechanism."
- On fallbacks: "GPT-5.6 Luna has higher evasion success… than GPT-5.6 Sol… switching to it as a weaker fallback could actually increase evasion rates."
- Results "do not account for model-specific prompt tuning or calibration techniques such as logit extraction and thresholding."

**7. Data/code.** Traces are at https://instrumental-evasion.com. No code repository URL is stated in the text.

**8. Relevance: HIGH (adversarial-robustness evidence for stateful/sequential monitors).**
- **Evidence for stateful monitoring:** this is a clean empirical case that monitor statefulness matters. A 40-call history cut evasion sharply compared with a myopic monitor (up to −57.5 pp).
- **Evidence against window-based state:** agents (unintentionally or not) **flush the window**. A sliding-window state is defeated by padding or retry flooding.
- **Implication for our design:** this argues for *non-forgetting accumulators* (CUSUM or e-process statistics that never decay below the reset floor, or alarm counts) rather than fixed-length context windows. It also argues for treating **block/retry counts as evidence**: a retry-after-block rate of 55.9% is itself a strong behavioral signal.
- **Overlap with existing deployments:** Claude Code auto-mode's "3 consecutive / 20 total denials" counter is the deployed analogue.
- **The ALLOW/BLOCK feedback loop:** agents adapt from it, as in 2608.17445. Any accumulator calibration must hold under feedback-driven adaptation. Retry-to-exploit-stochasticity is an attack on per-call scoring noise that sequential aggregation could absorb.
- **Gaps it leaves:** a binary monitor with no scores, no sequential statistic, no ARL, and no per-task calibration.

---

### 2604.11806 — Detecting Safety Violations Across Many Agent Traces (Meerkat)

**1. Citation & gist.**
- **Authors:** Adam Stein* and Davis Brown* (equal contribution, order by coin flip), Hamed Hassani, Mayur Naik, Eric Wong. University of Pennsylvania.
- **Posted:** 13 Apr 2026, cs.AI, v1, under review. https://arxiv.org/abs/2604.11806
- **Gist:** "Meerkat" is an offline repository-level auditor. It embeds traces, clusters them with k-means, and hands the property plus the clustered repository to an LLM agent. The agent returns a case verdict, a score per trace, and candidate *witness sets* (subsets of traces that jointly violate a natural-language property; a "hyperproperty").
- **Results:**
  - On distributed misuse it beats per-trace monitors.
  - It finds harness-level cheating on the top Terminal-Bench 2.0 and HAL USACO submissions.
  - It finds about 4× more CyBench reward hacking than prior audits.
  - A white-box embedding attack reduces its AP 10×.

**2. Threat model & attack construction.**
- **Repository-level violations:** distributed evidence (|W| > 1), sparse search (|∪W| ≪ |R|), and adversarial disguise.
- **Distributed misuse cases** come from Brown et al. (2025), "Benchmarking misuse mitigation against covert adversaries" (2506.06414):
  - Each case has 6 decomposition traces plus bg·6 benign traces, with bg ∈ {20, 100}.
  - Totals are rounded down so the decomposition count does not leak.
- **Task-gaming cases** come from ImpossibleBench and TRACE. Each case has k ∈ {10, 25, 50, 100} traces with p ≤ ⌊0.05k⌋ positives.
- **CUA-SHADE-Arena** is used for sabotage.
- **Adaptive attacks (Sec. 4):**
  - **"Persona reframe":** a prompt injection that adds a unique benign context to each campaign trace.
  - **White-box GCG adversarial prefix:** 250 tokens per trace, optimized to *maximize the log-det of the campaign's embedding covariance*. This scatters the campaign across clusters (bge-base-en-v1.5).

**3. Monitors/detectors.**
- **Meerkat (Alg. 1):** Represent → Cluster (k-means) → BuildInputs → Agent returns (v, {s_i}, Ŵ); the verdict v maps to PASS/FAIL/INCONCLUSIVE. Offline and post hoc. No calibrated threshold; evaluation is by AP and AUROC.
- **Baselines:**
  - Per-trace LLM **Monitor**: case score = max over traces.
  - **Buffer** monitor (Brown et al. 2025).
  - Naive agent.
  - **Bayesian monitor adapted from Wen et al. (2025a)** (App. J). This is the one formal accumulator in the cluster besides 2606.10456.
- **Bayesian monitor details.**
  - Hypotheses: h = (r, β) with r ∈ {0, .005, .01, .02, .05, .1} and β ∈ {0, .2, …, 1}, for 31 hypotheses in total. Prior 0.5 on the benign hypothesis.
  - Likelihood: P(s|h) = (1−r)·P(s|benign) + r·P(s|mal, β).
  - Densities are bucketed histograms, (count + a)/(total + aB), with bucket width 0.1 and a = 1.
  - P(s|benign) is the empirical score distribution. Malicious densities are synthesized by interpolating toward a high-score-shifted version.
  - Credences update by Bayes' rule, which is order-independent.
  - Trace posterior: P(z_i = 1 | s_{1:m}) = Σ_{j: r_j > 0} c_j · r_j·P(s_i|mal, β_j)/P(s_i|h_j).
- **Cluster boost:** p_clust = 0.25·size + 0.25·coherence + 0.25·concentration + 0.15·max + 0.10·mean, combined as p̂_i = 1 − (1−p_i)(1−p_clust).

**4. Testbed/data.**
- **Labeled corpora (Table 1):**

  | Corpus | Cases | Traces per case |
  |---|---|---|
  | Cyber misuse | 50 | 20–600 |
  | Bio misuse | 50 | 20–600 |
  | ImpossibleBench | 200 | 10–100 |
  | TRACE | 200 | 10–100 |
  | CUA-SHADE-Arena | 200 | 10–100 |

- **Unlabeled real corpora:** Terminal-Bench 2.0, HAL USACO, CyBench (464 successful traces), BountyBench.
- **Models:** GPT-5.4 and GPT-5.4-mini, Qwen3.5-397B-A17B, Opus-4.6, GLM-5.

**5. Key quantitative results.**
- **Distributed misuse, trace-level AP (Table 2).** Cyber bg=20×, Qwen3.5:

  | Method | AP |
  |---|---|
  | Meerkat | 0.837 |
  | Naive agent | 0.632 |
  | Monitor | 0.125 |
  | Bayesian | 0.243 |
  | Buffer | 0.191 |

  Results are mixed across settings. At Cyber 100× with Qwen, the naive agent (0.456) beats Meerkat (0.098). At Bio 100× with Qwen, Meerkat gets 0.142 against Monitor's 0.012.
- **Bayesian ablation (Table 14), raw scores → score-only Bayesian → Bayesian + clusters:**

  | Setting | AUROC | AP |
  |---|---|---|
  | Cyber 100× | .574 → .541 → .745 | .036 → .020 → .130 |
  | Cyber 20× | .610 → .605 → .767 | — |

  In the authors' words: "**The raw Bayesian updating yields no improvement, because the monitor scores most traces as zero, and benign and malicious score distributions overlap heavily.**" The gains come only from semantic clustering.
- **Task gaming (Table 4):** improvements are small. On ImpossibleBench at 100 traces per case, AP is 0.887 for Meerkat vs 0.817 for Monitor (Qwen). On TRACE, Meerkat roughly ties Monitor.
- **Compute scaling:** pass@1 (AUROC > 0.5) rises from 0.10 to 0.50 for 13× more reasoning tokens. Outcomes are bimodal.
- **Real audits:**
  - Pilot read /tests in 415/429 successful traces.
  - ForgeCode drops from 81.8% to 71.7% (from #1 to 14th) without the AGENTS.md answer leak.
  - HAL USACO: 595 likely cheating traces.
  - CyBench: 16/464 (3.4%), about 4× prior estimates.
- **Adaptive attack (Fig. 6):** the GCG prefix cuts Meerkat's AP from 0.10 to 0.01 on 10 cases, which is below the Bayesian baseline (0.11) and close to random.

**6. Stated limitations & future work (verbatim).**
- "dispersing campaign traces across unrelated clusters can substantially degrade detection. This motivates future work on adversarially robust distributed monitoring and clustering methods."
- On the real audits (App. F.6): "Many traces are truncated or summarized… Only a subset of suspicious traces received manual review… Terminal-Bench provides no ground-truth cheating labels."
- The ethics section notes deanonymization and surveillance risks of cross-trace linkage.

**7. Data/code.** No code URL for Meerkat is given in the text.

**8. Relevance: MEDIUM-HIGH.**
- **Why it matters to us.** This is the only paper in the cluster that actually *runs a formal Bayesian evidence-accumulation monitor* (adapted from Wen et al.) on distributed attacks. **It finds score-only accumulation useless** on distributed misuse: per-trace LLM scores are mostly 0, and the benign and malicious score distributions overlap. That directly cautions against our plan: CUSUM or SPRT over per-step LLM suspicion scores only helps if the attack actually shifts the score distribution. Decomposition-style attacks are designed so that it does not.
- **What its gains tell us.** All of its improvement comes from *semantic* linkage (clustering and agent reasoning).
- **Robustness.** That linkage can itself be attacked: white-box embedding dispersal brought AP to about random.
- **Gaps it leaves:** offline only; no sequential or online setting; no ARL; no calibrated FPR; no per-context baselines.
- **Opportunity for us.** A *hybrid*: accumulate statistics over semantically keyed streams (cluster, resource, service), and analyze what happens when an adversary disperses the keys.

---

### 2506.10949 — Monitoring Decomposition Attacks in LLMs with Lightweight Sequential Monitors

**1. Citation & gist.**
- Authors: Chen Yueh-Han, Nitish Joshi, Yulin Chen, Maksym Andriushchenko, Rico Angell*, He He* (*equal advising).
- Affiliations: New York University and EPFL (Andriushchenko).
- Dates: v1 2025-06-12; read v2 (14 Jun 2025). 2607.02514 cites it as ICLR 2026. https://arxiv.org/abs/2506.10949
- Gist: decomposing a harmful goal into benign-looking subtasks defeats refusals (GPT-4o ASR 87% average). The defense is a "sequential monitor": a cheap LLM that re-reads the **cumulative prompt history** at every step and halts when it flags. Prompt engineering lifts it to F1 0.91 / DSR 93%.

**2. Threat model & attack construction.**
- Threat: misuse by a user who submits subtasks sequentially within **one conversation** (not cross-session).
- Decompositions are generated as follows:
  - QA: 1,300 unsafe and 1,300 safe prompts from GPT-4o, decomposed by the abliterated NeuralDaredevil-8B.
  - Text-to-image: 631 examples from a jailbroken o1, with benign counterparts written by GPT-4o.
  - Agent: 533 tasks generated from 36 AgentHarm seeds, decomposed by GPT-4o with 10 hand-crafted demos, then validated and rewritten by 6 Upwork annotators ($2,613).
- Each task carries a **"harmful index"**: the step at which compliance yields harm. For QA, this is the first step where the StrongReject score of the summarized answers exceeds 0.75.
- Adaptive element: **random task injection**, i.e. benign subtasks from other tasks inserted at 0–100% of the original count.
- Attackers are not monitor-aware beyond that.

**3. Monitors/detectors.**
- Sequential monitoring is formalized as binary sequence labeling. At each step i ≥ 2 the monitor sees the cumulative context C_i = [p_1…p_i] and outputs y_i ∈ {0,1}, optionally a score s_i ∈ [0,1] thresholded into y_i.
- **State**: the full raw prompt history. The LLM re-reads it each step; there is no numeric accumulator.
- Baseline "single-input" monitor scores each prompt independently.
- Scoring outcomes:
  - TP = flag at or before the harmful index.
  - FP = any flag on a benign task.
  - FN = late or no flag.
- Metrics are F1 and Defense Success Rate (DSR = recall).
- Monitor outputs: zero-shot binary 0/1 at first; later the model is prompted for a **probability of harmful intent**, and the decision threshold is tuned on the validation set for best F1 ("optimal decision threshold").
- Prompting variants: ICL (agent / image / QA examples), safety guideline, CoT, and hypothesis generation (up to 5 hypotheses, each with a p_harmful).

**4. Testbed/data.**
- Dataset is DecomposedHarm (Table 5, 50/50 harmful/benign):
  - QA: 1,548 / 332 / 332 (train / val / test).
  - Image: 882 / 190 / 190.
  - Agent: 813 / 176 / 176.
- 2,243 harmful–benign pairs in total. Every task has fewer than 20 subtasks.
- Monitors tested: 10+ LLMs (Llama-3.1-8B, GPT-4.1-nano, GPT-4o-mini, Mistral, Qwen, Gemma, QwQ, o3-mini, GPT-4o, Claude-3.7-Sonnet).
- Agent ASR was checked on 50 tasks with grading functions.

**5. Key quantitative results.**
- **Attack effect (Table 1, GPT-4o)**, refusal original → decomposed:

  | Setting | Refusal | ASR |
  |---|---|---|
  | QA | 100 → 9.3% | 85.2% |
  | Image | 83.5 → 2.25% | 96.3% |
  | Agent | 50 → 10% | 80.0% |
- **Sequential vs single-input (Table 2)**, F1 and DSR, single → sequential:

  | Monitor | F1 | DSR |
  |---|---|---|
  | GPT-4.1-nano | 0.670 → 0.770 | 0.504 → 0.631 |
  | Llama-3.1-8B | 0.411 → 0.719 | 0.267 → 0.575 |
- **Random injection** at 100% drops GPT-4o F1 from 0.85 to 0.72 (Fig. 5b). The abstract says o3-mini falls from 73% to 62% DSR.
- **Prompt sweep (Table 3, validation F1):** CoT averages 0.905 against a zero-shot average of 0.780. Agent-task ICL with Llama-3.1-8B reaches 0.941.
- **Test (Table 4):**
  - Optimized GPT-4o-mini (QA ICL): F1 0.913, $1.39e-4 per task, 0.437 s.
  - o3-mini: F1 0.836, $1.38e-3, 3.98 s.
  - GPT-4o: F1 0.870.
- **Robustness to injection:** optimized monitors reach DSR up to 93% (GPT-4o-mini) and 89% (Llama-8B) and stay flat under injection (Fig. 6).
- **Per task (Fig. 15):** QA is hardest; the best F1 is 0.669 (Claude-3.7).

**6. Stated limitations & future work (verbatim).**
- "All of our tasks only consist of less than 20 subtasks. This raises the question of whether the approach scales to tasks that can be decomposed into even more subtasks, e.g., conducting malicious bioweapon research likely requires thousands of subtasks."
- "We only stress-test the monitor with random distraction tasks; we do not evaluate more sophisticated obfuscations."
- Future work (App. E.1):
  - "(1) Scaling beyond short horizons… monitor effectively across hundreds or even thousands of instructions while maintaining low cost".
  - "(4)… Monitoring must aggregate context from multiple LLM APIs" (cross-provider). This item also suggests government-ID account verification.
  - "(5) Iterative refinement: Can the red team develop an automated decomposition method that, whenever detected as harmful, further decomposes the task".

**7. Data/code.**
- Data: https://huggingface.co/datasets/YuehHanChen/DecomposedHarm
- Code: https://github.com/YuehHanChen/Monitoring-Decomposition-Attack

**8. Relevance: MEDIUM.**
- This is the canonical "sequential monitor", but "sequential" here means **an LLM re-reading the growing context** at each step. It is not sequential hypothesis testing. Thresholds are tuned for best F1, not calibrated to a false-alarm rate, and there is no ARL or delay metric beyond "before the harmful index".
- Gaps it leaves:
  - Score-stream accumulation (CUSUM/SPRT on s_i) is a cheap alternative to re-reading the full context and scales past 20 steps. The authors name scaling to "hundreds or even thousands of instructions" as open.
  - Cross-session accumulation is not covered.
- Mild threat to our framing: an LLM given the full history already captures cross-step dependencies semantically. Score-only accumulators must beat this on cost or horizon, or be combined with it.
- Its injection-dilution attack is the natural adversary against mean-type accumulators.

---

### 2604.11309 — The Salami Slicing Threat: Exploiting Cumulative Risks in LLM Systems

**1. Citation & gist.**
- **Authors:** Yihao Zhang, Kai Wang, Jiangrong Wu, Haolin Wu, Yuxuan Zhou, Zeming Wei, Dongxian Wu, Xun Chen, Jun Sun, Meng Sun.
- **Affiliations:** Peking University (School of Mathematical Sciences), Sun Yat-sen University, Wuhan University, Tsinghua SIGS, ByteDance, Singapore Management University.
- **Date and venue:** 13 Apr 2026, v1, submitted to IEEE TDSC. https://arxiv.org/abs/2604.11309
- **Gist:** This is a multi-turn jailbreak paper (misuse, not agents). Each turn adds a small sub-threshold "harm increment", and the paper proves that the total exceeds any level h after ⌈h/τ⌉ turns. It proposes **Cumulative Query Auditing (CQA)**: re-judge the concatenation of all user prompts at every turn.

**2. Threat model & attack construction.**
- **Attacker model:** a black-box user against a single conversation, so the attack spans turns, not sessions.
- **Formal setup (Def. III.1, Assumption III.1).**
  - An ideal harm scorer H gives the increment per prompt, H̃(p_{n+1}, p^n) = H(p^n ⊕ p_{n+1} ⊕ r_{n+1}) − H(p^n).
  - Alignment is modeled as a per-turn refusal trigger: refuse if H̃ > τ_thres.
- **Theorem III.1:** if every context admits a prompt with τ < H̃ < τ_thres, then n > ⌈h/τ⌉ turns achieve H > h.
- **Corollary:** a fixed "universal inducer" p′ repeated ⌈h/τ⌉ times is enough. Example: "Add a little details on manufacturing".
- **Automated Salami Attack (Alg. 1).**
  - GPT-4 generates a safe initial prompt p_0 and k perturbations.
  - Each perturbation is repeated t times: 5-shot uses k = t = 2, 10-shot uses k = t = 3.
  - The attack is non-adaptive and target-agnostic.
- **A-Salami:** an adaptive multi-agent variant (Reflection Thinker, Attacker, Evaluators, Summary Agent) with a budget of 5 queries.
- **Monitor-awareness:** none, beyond avoiding explicit triggers.

**3. Monitors/detectors.**
- **Baseline defenses (Table VIII):**
  - SmoothLLM, approximated with 5 perturbations and a majority vote;
  - Self-Reminder;
  - an Input Filter (a GPT-4 judge applied per input).
- **CQA (Sec. VI).**
  - Form the cumulative query sequence P_n = p_1 ⊕ … ⊕ p_n. Prompts only; responses are excluded.
  - Score it with H_cum(P_n) = H̃(p_1 ⊕ … ⊕ p_n, ε).
  - Refuse if H_cum(P_{n+1}) > τ_cum.
  - **Assumption VI.1 (aggregate-harm equivalence):** Σ_k H̃(p_k, p^{k−1}) ≈ H̃(concat, ε).
  - **Lemma VI.1:** τ_cum = τ_thres is feasible, so the aligned model can act as its own judge.
- **Implementation:** GPT-4o is both target and judge, using a judge prompt "in the open-sourced code". No numeric threshold is reported. The state is the raw concatenated history, with no score accumulator.

**4. Testbed/data.**
- **Text benchmarks:** AdvBench (520), HarmBench (200), JailbreakBench (100).
- **Target models:** GPT-4o, Gemini 2.5 Pro, DeepSeek V3, Qwen3-235B, GLM-4.5. The attack model is GPT-4.
- **Judge:** JailJudge with a GPT-4 judge, scoring ASR plus a 1–10 harmful score. Each item is judged twice and the worse result is kept.
- **Multimodal:** MM-SafetyBench for VLMs (10% of 5,040 pairs) and OVERT for text-to-image (20 prompts, Gemini web UI).
- **Over-refusal check:** 52 benign Alpaca prompts.

**5. Key quantitative results.**
- **Table II (ASR):**
  - AdvBench, GPT-4o: Salami-10 reaches 90.4% and A-Salami 95.8%, versus Crescendo 58.3% and GOAT 65.3%.
  - Salami averages ≥90% across most model/dataset cells.
- **Efficiency (Table III, GPT-4o):** AVQ is 3.9 for Salami, 5.6 for Crescendo and 10.7 for PAIR. AVT is 729 tokens, versus 5,013 for Crescendo.
- **Transfer (Table IV):** Salami-5 transfers from GPT-4o at 91–93% ASR. Crescendo drops by up to 24 points.
- **Multimodal:** VLM ASR is 55.6% on GPT-4o and 56.2% on Qwen-VL-Max. Diffusion bypass is 16/20, and 13/16 of those match the intended content.
- **Defenses (Table VIII, JailbreakBench, GPT-4o):** the Salami-5 baseline is 87.0%. It falls to 80.0% under SmoothLLM, 83.0% under Self-Reminder and 84.0% under Input Filter. Under the same Input Filter, PAIR falls to 1.0%.
- **CQA (Table IX), ASR without → with CQA:**

  | Attack | Without CQA | With CQA | Relative drop |
  |---|---|---|---|
  | Salami-5 | 87.0% | 48.0% | 44.8% |
  | A-Salami | 91.0% | 65.0% | 28.6% |
  | Crescendo | 64.0% | 38.0% | 40.6% |
  | CIA | 54.0% | 19.0% | 64.8% |

  On the 52 benign Alpaca prompts, CQA produced 0 refusals.
- **Mechanistic claims:**
  - In Llama-2-7B-Chat, safety head L2H26 attends most to the last turn in 96% of attacks.
  - In layers 7 and 14, PCA shows the multi-turn trajectory never enters the refusal cluster.

**6. Stated limitations & future work (verbatim).**
- "We leave further optimization of the CQA prototype as future work."
- On the theorem: "the theorem operates as a conceptual framework, abstracting the risk's underlying mechanics rather than describing specific real-world scenarios."
- On Assumption VI.1: "real-world deviations (e.g., context drift, model-specific processing quirks) may weaken this equivalence".
- There is no dedicated limitations section.

**7. Data/code.** The paper refers to "our open-source framework" and "the open-sourced code", but **no URL appears in the text**.

**8. Relevance: MEDIUM (conceptual).**
- **What it adds.** The theorem is the textbook motivation for accumulation. A per-step threshold τ_thres is defeated by n ≈ h/τ increments of size τ < τ_thres. This is exactly the regime where CUSUM with drift k < τ, or an SPRT on per-turn scores, accumulates evidence.
- **Gaps:**
  - CQA is an LLM re-judging the concatenated history, with no score-stream statistic, no calibrated false-alarm rate, and no ARL.
  - The over-refusal test uses only 52 prompts.
  - The setting is single conversation, misuse rather than agent sabotage.
- **What this means for us.** The attacker in Corollary III.1 adds a *constant positive* increment per turn, so it is detectable by a cumulative-sum statistic. The open question we would address is an attacker who sets increments below the accumulator's drift term. The paper does not consider that case.

---

### 2605.29178 — The Best-Laid SCHEMEs: Coordinated Sabotage and Monitoring in Multi-Agent Systems

**1. Citation & gist.**
Nikolay Radev, Lennart Haas, Benjamin Arnav†, Pablo Bernabeu-Pérez† (†senior authors).
- The paper states no institutional affiliations. The work ran through SPAR (Supervised Program for Alignment Research); the original idea is credited to Mary Phuong.
- Posted 27 May 2026, cs.CR, v1. https://arxiv.org/abs/2605.29178
- *Gist:* SCHEME is a benchmark of 17 multi-agent coding instances in which each covert side task is **joint-only** (no proper subset of agents can do it). Frontier teams sabotage successfully: 84% for Gemini 3.1 Pro, 46% for GPT 5.1 Codex. Even so, a single-shot trajectory-level GPT-5.1-Codex-Mini monitor catches nearly everything at FPR ≤ 2%.

**2. Threat model & attack construction.**
- Agents are explicitly prompted with a malicious shared side task, which isolates *execution* from *propensity*.
- **Roles.** Agent 0 (the analyst) runs an eval script. Agents 1..N are developers with disjoint write scopes on real libraries: fairlearn, skfolio, pycasbin, lightkurve, pyjwt, oauthlib, concept-erasure, sympy.
- **Knowledge split.** In the *concentrated* variant only the analyst knows the side task. In the *distributed* variant some criteria go to a developer who must relay them.
- **Communication** runs only through append-only channel files, in a BUS (shared) or STAR (pairwise) topology.
- **Stealth-aware variants** (Gemini only):
  - "notice": agents are told the monitor sees the trajectory, code and channel, and are urged to be subtle.
  - "notice + hint": additionally suggests fabricating plausible justifications.
- No attacker optimizes against the monitor. The authors say so explicitly: "not a control evaluation."

**3. Monitors/detectors.**
- **Monitor:** a single-shot GPT 5.1 Codex Mini call. It sees the main-task description, the environment layout, a unified diff of edits and (optionally) the channel. It never sees the side task or the reasoning. It outputs an integer suspicion score in [0, 100] plus a justification, at **trajectory level**.
- **Views:** Code+Comms; Only Code; Only Comms; **Single-Agent**, in which each agent's code slice is scored independently and the per-trajectory score is the **mean over agents**.
- **Score aggregation:** each sample is monitored 10 times and reduced to the **median** score, to cut run-to-run noise.
- **Threshold:** the 98th percentile of a pooled Codex+Gemini *main-pass* honest baseline (about 62 medians per source and configuration). A trajectory is caught only if its score is strictly > τ. Resulting τ = 5.0 (5.6 for Single-Agent).
- **Calibration ablations** (App. J.12): per-model thresholds, and a symmetric main-pass filter.
- **Score-level ensemble** (App. J.7): mean or max of Only Code and Only Comms. The two give identical decisions because the baseline clusters at the integer 5.
- **No cross-trajectory or sequential accumulation.**

**4. Testbed/data.**
- 7 settings, 11 pairings, 17 instances, 2–4 agents each.
- 5 epochs per instance, so N = 85 trajectories per model; a topology subset uses N = 70 per topology.
- Inspect-based Docker sandbox; each agent runs as its own Linux user; no internet.
- A full benchmark pass costs about 1.5B tokens on Codex and 0.39B on Gemini.
- Honest baselines are the same instances with the side task removed, monitored 10 times each.

**5. Key quantitative results.**
- **Sabotage success:** Gemini 84% (side task 94%, main task 85%); Codex 46% (side 47%, main 89%).
  - Distributed vs concentrated on Codex: 43% → 37% (CIs overlap).
  - BUS vs STAR on Gemini: 81% → 79%.
- **Failure recovery:** Codex averages 2.1 failure modes per trajectory with 56% recovered; Gemini 1.4 with 73% recovered.
- **Detection at FPR ≤ 2%, Codex** (Fig. 7):
  - Code+Comms: 81% (100% on successful sabotage, 65% on failed).
  - Only Code: 68%.
  - Only Comms: 46%.
  - **Single-Agent (per-agent mean): 20 pp lower overall** (90% on successes, 37% on failures). The authors' reading: "coordination cues distributed across agents are not fully revealed by any single slice."
- **Detection at FPR ≤ 2%, Gemini:** Code+Comms 100%, Only Code 99%, Only Comms 93%.
- **Honest scores are extremely tight after the main-pass filter:** mean 5/100, p95 5–9 (Table 9). Sabotage scores average 84–88 (Gemini) and 42–48 (Codex).
- **Stealth prompting (Fig. 8):**
  - "Notice" roughly halves Gemini sabotage success (84% → 41%); "notice + hint" brings it back to 62%.
  - Undetected ("stealthy") sabotage stays below 3% under Code+Comms and peaks at 11% under Only Comms with notice + hint.
- **Ensemble (Table 11):** mean/max over Only Code and Only Comms gives 71% on Codex unprompted vs 81% for Code+Comms, but 96% vs 94% on Gemini + notice.
- **App. J.4, relevant to per-context thresholds:** one honest instance (Symbolic math on Gemini) has a per-instance honest mean of 37.5–75.4. Without the main-pass filter, this single instance "shifts the FPR-5% threshold from 5 to 10–50… the threshold becomes a property of which model failed which legitimate task."

**6. Stated limitations & future work (verbatim).**
- "Each trajectory in SCHEME is also a single, self-contained task instance, scored independently by the monitor. In real deployments, agents work continuously over many commits, and a sabotage attempt would be embedded in a much larger volume of legitimate work… Whether the monitor's discriminative margin survives this needle-in-a-haystack regime is a natural extension we do not address in this paper."
- "Engineered adversarial policies that adapt to a specific monitor… are absent here, and we do not claim the detection rates we report bound what a stronger adversary could evade."
- "the most pressing direction is a full control evaluation that uses the benchmark to stress-test monitors with adversarial policies."
- Other limitations: steganography and shared-filesystem side channels are out of scope; the monitor comes from the same family as one of the attackers; small buckets (n = 10) mean a single trial moves a rate by 10 pp.

**7. Data/code.** No release URL appears in the paper.

**8. Relevance: MEDIUM.**
- **What it shows.** Multi-agent sabotage is *loud* at the trajectory level. With full visibility, a cheap monitor already catches nearly everything, so per-step or sequential accumulation adds little in this regime. The Single-Agent mean result shows that splitting evidence across agents costs detection, which motivates cross-agent accumulation.
- **Gaps it leaves:**
  - no long-horizon "needle-in-haystack" setting, which the authors flag as untested;
  - no stateful or sequential monitors;
  - no adaptive attacker;
  - a coarse τ set from about 62 baseline medians.
- **Evidence it gives us.** App. J.4 is concrete evidence that **honest score baselines are strongly task-dependent**: one task's honest mean is 37–75 against a global p95 of 5–9. That supports per-context (CFAR) thresholds, and it also shows how pooled thresholds get hijacked by a single outlier context.
- **Caution.** Integer-score clustering at 5 makes mean and max decisions identical. Score discreteness matters for any accumulator.

---

### 2606.07054 — TRACE: Trajectory Reasoning through Adaptive Cross-Step Evidence Aggregation for LLM Agents

**1. Citation and gist**
- **Authors:** Vijitha Mittapalli, Shreyaa Jayant Dani, Satya Srujana Pilli, Snigdha Ansu, Mohammadreza Teymoorianfard (all UMass Amherst); Franck Dernoncourt (Adobe Research); Hongjie Chen (Dolby Labs); Yu Wang (U. Oregon); Ryan A. Rossi (Adobe Research); Nesreen K. Ahmed (Cisco).
- **Posted:** 5 Jun 2026, cs.CL, v1. https://arxiv.org/abs/2606.07054
- **Gist:** an offline, training-free LLM monitoring agent built as a Triage–Inspect–Judge loop. It picks suspect windows, inspects them while carrying a *natural-language evidence state* across windows, and gives a 1–5 verdict. On SHADE-Arena it raises recall over the full-trajectory and chunked "sequential" monitors.

**2. Threat model and attack construction**
- There is no new attack. The paper reuses SHADE-Arena trajectories, each pairing a main task with a hidden side task.
- Six evasion strategies come from MRT (Kale et al. 2025): Naive, No Evasion, Selective Verbalization, Liar, Combined, and Manipulation.
- Some side tasks are explicitly distributed. Bank Transfer, for example, sends ≥$5,000 "split across multiple transactions embedded among legitimate transfers", and American Airlines biases ≥90% of bookings.
- The attackers are not adaptive to TRACE.

**3. Monitors and detectors**
- **TRACE:**
  - *Triage* reads the full trace and outputs constraints (intent and scope) plus up to 3–4 suspect windows. Windows are either *local* (1–3 adjacent steps) or *pattern* (3–8 non-adjacent steps).
  - *Inspect* runs per window, choosing among InspectStep, CompareSteps, CheckPolicy, AnalyzeDecisions and Done. It allows up to 6 steps per window and up to 4 windows. Prior findings are injected as "OBSERVATIONS SO FAR".
  - *Judge* synthesizes everything into a 1–5 suspicion score. A trajectory is called malicious if the **score is ≥ 4**. The threshold, budget and action space were "fixed based on a small validation set". There is **no FPR-targeted calibration**.
- **Baselines:**
  - The SHADE-Arena full-trajectory monitor: a single LLM pass.
  - The MRT "Sequential Monitor": fixed-length chunks scored in order, with a compressed running summary carried forward.
  - The baselines' decision thresholds are **not stated**.
- **State:** a textual evidence memory within one trajectory. There is no numeric accumulation and nothing carried across sessions.

**4. Testbed and data**
- SHADE-Arena, 10 task domains, 463 trajectories (189 benign, 274 malicious; Table 1), averaging 91.8 turns.
- All 463 trajectories serve as the test set.
- Backbone is Claude Sonnet 4.6, with ablations on Opus 4.7, GPT-5.1, Gemini Flash 3.5 and o4-mini. Baselines use Sonnet 4.6.

**5. Key quantitative results**
- **Aggregate, Sonnet 4.6:**

  | Monitor | F1 | Recall | Precision |
  |---|---|---|---|
  | TRACE | 0.713 | 0.844 | 0.641 |
  | Full-trajectory | 0.577 | 0.405 | ≈1.0 |
  | Sequential | 0.700 | 0.580 | ≈1.0 |

- **Cost:** 12.3 LLM calls per trajectory for TRACE vs 18.8 for the sequential monitor (Table 2).
- **Backbones (Table 3):** Opus 4.7 gives F1 0.790 (P 0.786, R 0.825); o4-mini gives F1 0.495.
- **Per task (recall):**
  - Performance Reviews: TRACE 0.929 vs 0.143 (full) and 0.286 (sequential).
  - American Airlines: 0.909 vs 0.061 and 0.758.
  - Bank Transfer: 0.885 vs 0.269 and 0.808.
- **By evasion strategy (Fig. 4):**
  - Selective Verbalization (102/274 trajectories): TRACE 94.1% vs 46.1% (sequential) and 44.1% (full).
  - **Manipulation: TRACE 0/17 vs sequential 10/17 (58.8%).** The paper's explanation is that "convincing local explanations suppress the accumulation of strong global suspicion signals."

**6. Stated limitations and future work (verbatim)**
- "TRACE is evaluated only on SHADE-Arena… The verdict threshold, inspection budget, and action space are fixed based on a small validation set and are not fully tuned per model… TRACE operates entirely at inference time and does not incorporate learned monitoring policies or online adaptation."
- "This motivates future monitors that reason more critically about long-term decision consistency rather than individual step-level justifications alone."

**7. Data and code:** no code URL is given in the paper. The baselines were reproduced from the public SHADE-Arena codebase.

**8. Relevance: MEDIUM-LOW**
- It is an LLM-agentic "evidence accumulation" within a single trajectory. That differs from statistical accumulation.
- Gaps it leaves: no FPR, ARL or TPR at a fixed FPR (only F1 and precision/recall, with precision 0.64), no per-step score stream, and no cross-session component.
- It does provide useful baseline numbers: the MRT chunked sequential monitor and the full-trajectory monitor on SHADE-Arena, where recall collapses for distributed tasks.
- One finding cuts against accumulation in general. Under the Manipulation evasion strategy, an accumulator that weighs justifications was fully defeated (0%). Plausible per-step justifications push per-step suspicion down, so **any accumulator over per-step suspicion scores inherits this weakness**.

---

### 2606.10747 — The Arbiter Agent: Continually Monitoring Multi-Agent Conversations to Detect Emergent Misalignment

**1. Citation & gist.**
- **Authors:** Filippo Tonini, Federico Torrielli (University of Turin), Anton Danholt Lautrup, Peter Schneider-Kamp, Mustafa Mert Çelikok, Lukas Galke Poech. All authors except Torrielli are at the University of Southern Denmark.
- **Date / venue:** 9 Jun 2026, cs.AI, v1. https://arxiv.org/abs/2606.10747
- **Gist:** A ReAct-style LLM "Arbiter" watches a 3-agent round-robin conversation as it unfolds. Its actions are Wait-and-Observe, Ask Model, Inspect System Prompt, Inspect CoT and Log Incident, each charged against an inspection budget. At the end it reports which agents are misaligned.

**2. Threat model & attack construction.**
- All five conditions use 3 agents, 30 turns and a debate-style topic built around a human-vs-AI goal conflict:
  - **Baseline:** all aligned, run on gemma-4-31B-it.
  - **Weight-induced misalignment:** one agent is Qwen2.5-7B-Instruct_risky-financial-advice (an emergent-misalignment model organism); the others are base Qwen2.5-7B.
  - **Model organism plus a risky system prompt.**
  - **Evaluation-aware:** the agent is told it is being monitored by the Arbiter, which tools it has, and to hide its "better future for AI agents" objective.
  - **Collusion via steganography:** two agents are prompted with the code words consider / indeed / agree.
- The adversary is monitor-aware only through the evaluation-aware prompt. Conversing agents are weaker than the Arbiter, so evasion is unlikely; the authors state this themselves.

**3. Monitors/detectors.**
- **Inputs:** at turn t the Arbiter sees the conversation history H_t = ((a^(i), m^(i)))_{i≤t}.
- **Action costs:** Wait/Observe costs λ·w, where w is the number of words revealed; Ask costs λ·(w_in + w_out); Log costs λ·w_log. Inspect SP and Inspect CoT cost a fixed κ. Settings: λ = 0.005 per word, κ = 5.
- **Budget constraint:** Σc(α) ≤ B, default B = 10.
- **State:** the conversation history plus the logged incidents. Log Incident is the persistent-memory tool.
- **Output:** a final report that names the set of misaligned agents A*.
- **No score or threshold.** The decision is the LLM's verdict. Metrics are micro-F1 over agents, detection turn t*, budget used B_used, and average false positives per run (0–3) in the baseline condition.
- **Backbone:** deepseek-v3.2 by default; Qwen3.6-plus as an ablation.

**4. Testbed/data.**
- Synthetic conversations: 5 variants per condition, 20 end-to-end replications per cell.
- Tool configurations: pure observation, interrogation, interrogation + log, CoT, full inspection.

**5. Key quantitative results.**
- **Weight-induced misalignment (Table 2, B = 10):** F1 0.12 with pure observation vs 0.51 with interrogation + log; t* 9.6 vs 5.9.
- **Model organism + risky system prompt:** pure observation reaches F1 1.00.
- **Evaluation-aware (Table 3):** F1 0.88 (pure observation), 0.94 (CoT), 0.97 (full inspection).
- **Collusion:** F1 1.00 under every tool configuration; t* falls from 8.4 to 2.3.
- **False positives on the aligned baseline (Table 4), average per run:**

  | Configuration | Avg FP |
  |---|---|
  | Pure observation | 0.35 |
  | Interrogation | 0.10 |
  | **+ Log** | **1.15** |
  | CoT | 0.55 |
  | Full inspection | 0.15 |

  The authors on the logging tool: "logging amplifies suspicions into false accusations"; "The logging of a small suspicion can cause a chain reaction leading to overconfident accusations."
- **Budget (Table 6):** raising B from 10 to 30 lifts F1 only from 0.51 to 0.62 for the model organism. The Arbiter spends about the same budget whatever is available.
- **Backbone (Table 7):** Qwen3.6-plus F1 is 0.17 / 0.65 vs 0.51 / 0.92 for DeepSeek.

**6. Stated limitations & future work (verbatim).**
- "Conversations are short (30 turns, 3 agents, fixed round-robin), and misalignment signals are relatively strong by construction, which likely inflates detection rates… The conversing agents are less capable than the Arbiter, making evasion unlikely… n = 20 replications per cell leaves confidence intervals wide."
- Future work: "more naturalistic conversations with more diverse and weaker misalignment signals", plus integrating interpretability tools such as activation oracles and natural-language autoencoders.

**7. Data/code.** https://github.com/aisilab/arbiter

**8. Relevance: LOW-MEDIUM.**
- The overlap is the "continual / early detection" framing with a detection-turn metric t*, and a budgeted monitor that chooses when to inspect (an optimal-stopping flavor).
- It is not statistical. There are no calibrated thresholds, and the evaluation uses toy conversations with very salient signals.
- The useful lesson for us is the **Log-Incident result: carrying suspicion as persistent state without calibration inflated false positives about 10× (0.10 → 1.15 per run)**. This is the qualitative failure that sequential tests with controlled false-alarm rates (ARL₀ / anytime-valid) are designed to prevent. It is a good motivating citation for calibrated accumulation.

---

### 2608.27348 — INTENT-AS-A-TOOL Makes it Easy to Track Agentic Misalignment

**1. Citation & gist.**
- **Authors:** Yutong Zhang, Jianshuo Dong, Peng Xu, Long Wang, Jie Zhang, Tianwei Zhang, Xiaoping Zhang*, Han Qiu* (*co-corresponding).
- **Affiliations:** Tsinghua University, MatrixOrigin, Nanyang Technological University, SiliconProspect AI.
- **Date / venue:** 27 Aug 2026, cs.CL, v1, ACL-style. https://arxiv.org/abs/2608.27348
- **Gist:** The method adds a zero-parameter "intent tool" D_b (e.g. `declare_blackmail_intent`) to the agent's action space. At every reasoning prefix, it reads the next-token probability that the model would call D_b. This gives a judge-free, *within-generation* intent-score stream. When the intent tool becomes the model's preferred next tool, a first-person corrective reflection is inserted.

**2. Threat model & attack construction.**
- **Setting:** emergent agentic misalignment, not an adversarial attacker. The scenarios come from the Lynch et al. (2025) agentic-misalignment benchmark: Blackmail, Leaking and Murder.
- **Test cases:** 234 per scenario, varying goal conflict, pressure, and safety framing.
- **Sampling:** 3 rollouts per case at τ = 1, giving 702 rollouts per model–scenario pair.
- **Monitor awareness:** none. The model is *instructed* to call the intent tool when it decides to misbehave, so the method depends on cooperation and instruction-following.

**3. Monitors/detectors.**
- **CoT monitor (diagnostic):** GPT-4.1 assigns post-hoc trajectory labels: Rejection / Clean / Self-correction / Intent-only / Execution. Agreement with Claude-Sonnet-4.6 is above 95% on 1,000 rollouts.
- **Intent score:**
  - s_t^b = p_θ(D_b | C_t), where C_t = (x, r_{≤t}, A ∪ {D_b}).
  - It is the first-token probability of the tool name at the tool-call position, obtained with max_tokens = 1 and KV-cache prefix reuse.
  - It is evaluated at sentence boundaries.
- **Intervention trigger:** fires if the intent tool has the *highest* first-token probability among all tools. This is a relative argmax rule, not a calibrated threshold.
- **Repeated triggering:** the trigger can fire multiple times. If repeated triggers fail, the final tool execution is blocked.
- **Baselines for the trigger:** a static safety prompt, random triggering, and fixed-interval triggering.
- **State:** the score stream lives only within one reasoning trace. Nothing is accumulated across steps; each prefix is scored independently.

**4. Testbed/data.**
- **Models:** five open-weight models: Qwen3-8B, Qwen3-32B, Qwen3-235B-A22B, Qwen3.5-27B, Gemma-4-31B-IT.
- **Defense evaluation:** run on "risky" cases only, n = 5–198 per model and scenario.
- **Exploratory extension:** AgentHarm.
- **Benign check:** benign scenarios with 100 rollouts per model.

**5. Key quantitative results.**
- **CoT taxonomy (Fig. 1, pooled):** Clean 67.6%, Execution 27.7%, Self-correction 4.4%, Intent-only 0.3%, Rejection < 0.1%. When harmful intent becomes observable, it usually proceeds to execution.
- **Alignment with CoT labels (Table 4):** AUROC of the final-bin intent score is 0.924–0.976 for four models, but 0.745 for Qwen3.5-27B.
- **Defense success (Table 2):**
  - Qwen3-32B with intervention: 100% (blackmail), 96.5% (leaking), 98.9% (murder). With prompting: 80.0 / 78.9 / 63.4%.
  - Gemma-4-31B with intervention: 31.2 / 18.6 / 57.8%. With prompting: 99.2 / 55.0 / 89.0%. Here intervention is worse.
  - Overall, intervention matches or beats prompting in 9 of 12 Qwen-family settings.
- **Timing ablation (Table 3):**

  | Model | Intent-guided trigger | Random trigger | Fixed interval |
  |---|---|---|---|
  | Qwen3-8B | 97.8% (1.69 interventions) | 70.2% | 90.0% (9.71 interventions) |
  | Qwen3-32B | 98.5% | 72.7% | 84.3% |

- **Perturbation (Table 5):** the added tool changes the harmful-pursuit rate. For example, Qwen3-32B blackmail goes from 3.1% to 20.5%.
- **Instruction-following (Table 6):** compliance with the instruction to call the intent tool falls as low as 25.5% (Gemma on leaking).
- **Benign scenarios:** 0.0% spurious activation; task success 100% on 15 benign items.
- **Sharpness (App. J, Table 14):** the largest single-token jump in intent score has median 0.98 for Gemma and 0.79 for Qwen3-8B. In 72.8% and 48.0% of traces respectively, a single-token jump exceeds 0.8. Larger Qwen models shift more gradually.

**6. Stated limitations & future work (verbatim).**
- "INTENT-AS-A-TOOL changes the model's action space by adding a tool for the target behavior. This makes intent easier to observe, but can also affect the behavior being measured."
- "The score measures the model's preference to declare a behavior under our intent-tool protocol… Declaration reliability varies across models and scenarios."
- "unsafe preference may appear late, persist after correction, or re-emerge later."
- "requires the target behavior to be specified in advance… Future work should assess predictive and intervention performance in longer-horizon, multi-agent, browsing, code-execution, and other agentic settings."
- The method needs token-level log-probabilities.

**7. Data/code.** https://github.com/RebeccaZhang22/intent-as-a-tool

**8. Relevance: LOW-MEDIUM.**
- **Overlap with our plans:** it produces a dense, judge-free per-prefix *score stream* and applies an online trigger, which is a natural input for change-point detection. App. J's "phase transition" observation supports abrupt-change models for small models and gradual drift for large ones.
- **Gaps:**
  - The trigger is a heuristic argmax rule, with no false-alarm calibration and no accumulation.
  - It works only within one generation, not across steps or sessions.
  - It requires white-box log-probabilities and a cooperative model.
  - The authors evaluate no adversarial or monitor-aware model. A scheming model could simply not call, or not prefer, the intent tool; Gemma's 25.5% compliance already shows how fragile declaration is.
- **Bearing on our ideas:** it neither undermines nor scoops them. It could serve as an alternative per-step signal for a CUSUM-style detector on open-weight agents.

---

### 2604.11072 — Hodoscope: Unsupervised Monitoring for AI Misbehaviors

**1. Citation & gist.**
- **Authors:** Ziqian Zhong, Shashwat Saxena, Aditi Raghunathan (Carnegie Mellon University).
- **Date:** 13 Apr 2026, cs.AI, v1, under review.
- **Link:** https://arxiv.org/abs/2604.11072
- **Gist:** "Unsupervised monitoring" by distributional diffing. The pipeline summarizes each agent action into its task-generic intent, embeds it, projects with t-SNE, and fits a KDE per group (model or condition). It then ranks actions that are over-represented in one group relative to the others for human review. This found a new Commit0 git-history exploit and cuts review effort by 6–23×.

**2. Threat model & attack construction.** There is no adversary. The target is reward hacking and benchmark exploits that the authors *discover*, not ones they construct. The case studies are:
- Commit0 across models (a new finding).
- ImpossibleBench vs SWE-bench, both GPT-5.
- iQuest-Coder on SWE-bench vs 4 other models.

Together these cover more than 63,000 actions.

**3. Monitors/detectors.**
- **Density difference:** Δ_g(p) = f̂_g(p) − (1/(K−1)) Σ_{g′≠g} f̂_{g′}(p). Each f̂ is a Gaussian KDE on 2D t-SNE coordinates with Scott's-rule bandwidth. The authors say explicitly that this is "a visual guide… not as a statistical test".
- **Density-weighted farthest-point sampling:** score(i) = w(Δ_g(x_i))·min_{j∈S}‖x_i − x_j‖. Here w maps positive gaps to [β, 1] and negative gaps to [0, β], with β = 0.1.
- **No thresholds and no FPR.** The metric is rank-to-first-confirmed-hit, judged against rule-matching oracles.
- **Supervised extension (Sec. 5):** the discovered exemplars are added to an LLM judge's prompt.
- **State:** there is no per-trajectory or cross-session state. The comparison is cross-population, which is a form of a reference baseline.

**4. Testbed/data.**
- Commit0, MiniMax-M2.5 as target: the paper calls MiniMax-M2.5 the top open-weight model.
- ImpossibleBench: about 26k actions, against about 7k SWE-bench actions.
- iQuest: about 4k actions, against about 8k actions from other models.
- Models used for the pipeline: GPT-5.2 summarizer and Gemini Embedding 001. A weaker-model ablation uses GPT-4o-mini with text-embedding-3-large.
- Each result averages 10 seeds, each using a 50% subsample.

**5. Key quantitative results.**
- **Table 2, rank to first hit / % of actions inspected:**

  | Method | Commit0 | ImpossibleBench | iQuest |
  |---|---|---|---|
  | Hodoscope | 1 / 0.11% | 4±1 / 0.01% | 3±1 / 0.08% |
  | Uniform random | 6±1 | 91±14 | 29±4 |
  | Without diffing | 1 | 62±72 | 4±3 |
  | Without density | 11 | 149 | 40 |
  | Without summarization | 3 | 8 | 31 |
  | HDBSCAN with oracle-tuned parameters | 4 | 20 | 87 |

- **Commit0 after patching (Table 1):**
  - MiniMax-M2.5: 50.0% → 18.8%.
  - Four other models each drop about 12.5 points.
  - MiniMax runtime rises from 376 s to 1404 s once the shortcut is gone.
- **Judge augmentation (Table 3, ImpossibleBench):**
  - Weak monitors improve: GPT-4o-mini AUC 0.619 → 0.684; GPT-4.1 TPR@5% 0.363 → 0.437.
  - A strong monitor gets worse: GPT-5.4-mini (high reasoning) AUC 0.967 → 0.926 and TPR@5% 0.860 → 0.580.
- **LLM judge miss (App. J):** Claude Opus 4.6 rated `git log` as "a routine investigation step". It only flagged it after being given the issue report.

**6. Stated limitations & future work (verbatim).**
- "Hodoscope's density-difference overlay requires at least two groups of trajectories… when a misbehavior is equally common across all groups, the density-difference signal is attenuated."
- "When a misbehavior occurs in very few trajectories (e.g., a single agent run), it may not form a visible cluster in the 2D projection. This is a general challenge for distributional methods."
- "Anomalies are not necessarily misbehaviors (by design)… Human verification remains essential."

**7. Data/code.** https://github.com/AR-FORUM/hodoscope_paper and https://hodoscope.dev/. The authors also say they "will release Hodoscope as a public Python package."

**8. Relevance: LOW-MEDIUM.**
- **Closest overlap:** the idea of a *reference-population baseline*, i.e. diffing against comparison groups. This is loosely analogous to CFAR's use of reference cells to set a context-specific background.
- **Where it differs from our directions:**
  - It is offline and human-in-the-loop.
  - It does no sequential accumulation and makes no false-alarm guarantees.
  - It explicitly fails on rare, single-run misbehavior. That is exactly the deployment regime where sequential per-agent statistics are needed.
- **What it does not threaten:** our ideas.
- **What it does support:**
  - LLM judges can systematically score novel misbehavior as benign. Any accumulator over per-step LLM scores inherits that blind spot. A shift that never appears in the scores cannot be accumulated.
  - Behavior-level features computed against a baseline population could supplement LLM suspicion scores as an input stream.

---
