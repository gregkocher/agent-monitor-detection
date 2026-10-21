# D2: CUSUM-style / stateful guardrails and runtime monitors for LLMs and agents

Reading cards from full texts (pdftotext of the arXiv PDFs), read 2026-10-20. Papers: 2605.19966, 2604.16824, 2602.11247, 2602.16935, 2607.19361, 2607.20129, 2608.02464, 2608.27808, 2608.25379, 2608.23941.

Conventions: "not specified" means the paper's text does not give it. Numbers are copied from the papers. Wherever a card says "Overlap", the comparison is with our planned AI-control work: sequential tests over per-step monitor suspicion scores, CFAR-style per-context adaptive thresholds, cross-session accumulation, calibration, and robustness to monitor-aware attackers.

---

## Cluster synthesis

**How stateful accumulation is used for LLM safety today.** Six of the ten papers run an explicit one-sided Page-CUSUM, `W_t = max(0, W_{t-1} + x_t - k)` with an alarm at `W_t >= h`:

| Paper | Time unit | Per-step signal fed to CUSUM | Baseline / normalization | Reference value k | How h is set | Formal FA guarantee |
|---|---|---|---|---|---|---|
| CPD (2605.19966) | token in one prompt | next-token entropy | z-score using the median and 1.4826·MAD of the **fixed system prompt's** entropies (per deployment) | 0 ("canonical"); −0.5 / 0.5 sensitivity | maximize F1 per training fold (5-fold CV on balanced data) | none (explicitly not an LLR) |
| SafeDream (2604.16824) | dialogue turn | clipped logit of a learned risk r_t | subtract κ = "average log-odds under benign conversations" | κ | not specified (values of A, τ, A_imag not reported) | none |
| Sentinel (2608.02464) | agent step | ESN one-step prediction-error "surprise", per channel | residual scale σ_err from held-out healthy runs; z(·) | κ (value not given) | (1−β) quantile of max_t s_t over healthy validation episodes | empirical only |
| CURA (2608.27808) | GUI step | signed sum of 6 z-scored behavioral signals | mean/std frozen from a "fit" split of successful runs | 0.5 | Learn-then-Test fixed-sequence binomial tests on held-out successes | Pr(FPR ≤ α) ≥ 1−δ (trajectory-level, per regime) |
| MGT-B (2607.20129) | 64-token window | log of a mixture betting factor on a position-bucketed empirical p-value | position-conditional reference scores from correct runs | implicit (in the betting factor) | about 5% alarms on healthy dev trajectories | none (explicitly not an e-process) |
| Adaptive Triggering (2608.25379) | CoT step | judge score/10 or forced-answer probability gap | none | grid-searched (0.25–0.45) | grid search on a downstream accuracy/bias objective | none; reports ARL0 ≈ 5.8 steps |

The other four are stateful without CUSUM. Peak+Accumulation (2602.11247) is a closed-form "peak + persistence ratio + diversity" score that cites CUSUM as its inspiration. DeepContext (2602.16935) and CRA-Net (2607.19361) are learned recurrent (GRU) session scorers; CRA also has a convex-fusion variant. The unit-of-verification paper (2608.23941) studies how many actions a pre-execution monitor should review per call, and has no sequential test.

**Design choices the papers share:**
- Each run (prompt, conversation or episode) is monitored on its own. The statistic resets per run and alarms at most once, except Adaptive Triggering (resets to 0 after a trigger, one-step cooldown) and MGT-B (rollback restores detector state). **No paper accumulates evidence across sessions or episodes.**
- For ranking metrics, the run is scored by `max_t W_t`.
- False alarms are controlled per trajectory, not by in-run ARL. Thresholds come from:
  - an empirical null on benign/healthy runs (Sentinel, CURA, MGT-B);
  - F1-optimization on labeled balanced sets (CPD, Peak+Acc);
  - a downstream task objective (Adaptive Triggering);
  - for non-CUSUM scorers, TPR=0.90 on a labeled mixed split or benign-anchored FPR on external chat (CRA).
- None sets k from a hypothesized post-change shift (the classical k = δ/2 design). k is fixed by convention (0, 0.5) or by grid search.
- Only CPD standardizes against a reference sample from the same deployment, using median/MAD of the system prompt. This is the nearest existing analogue to a CFAR baseline, but it works inside a single request.

**Results.**
- **Accumulation reliably beats windowed or pointwise scoring at fixed signal quality.**
  - CPD: CUSUM vs. window gains about 12–14 F1 points on both NLL and entropy signals.
  - SafeDream: removing CUSUM raises FPR from 7.9% to 13.8% (and increases lead).
  - Sentinel: the ESN/CUSUM advantage over memoryless Mahalanobis grows with post-onset horizon (+0.09 at ≤3 steps, +0.40 at ≥9).
- **Recall at low, certified FPR is modest.**
  - CURA recalls 28% of failures at realized FPR 2.4% and 42% at 6.6% (median 31 steps before termination).
  - Sentinel detects 4.8% of AFTraj-2K failures at a 5% budget, despite AUROC 0.745.
- **Effort and length baselines are strong.** CURA's token-count AUROC is 0.802 vs. 0.828 for the composite (p=0.101). It separates from token-count and step-count CUSUM baselines only online, at matched certified α ≥ 0.10.

**Failure modes the papers report:**
1. **Short horizons and fast, quiet failures.** CUSUM needs post-onset steps. 61% of AFTraj failures end within 3 steps of onset, and CURA's recall is 0.22 on browser tasks and 0 on media/document tasks.
2. **Slow drift beats surprise-based monitors.** Sentinel reports that slow goal drift "evades every per-step-surprise monitor tested", because prediction-error normalization absorbs gradual change.
3. **Thresholds do not transfer across deployments.**
   - Sentinel, calibrated on qwen2.5:7b and moved to llama3.1:8b, drops to AUROC 0.527 (0.885 after recalibration).
   - CURA's realized FPR triples under a new planner.
   - MGT-B's h moves from 11.43 to 47.69 across datasets.
   - CRA-Net's θ swings from 0.993 to 0.643 between benchmark versions, and held-out-family AUROC collapses (as low as 0.000).
4. **Length and topic confounds.** CoSafe length-only AUROC is 1.0. DeepContext's attack and benign lengths are unmatched.
5. **A miscalibrated signal cannot be fixed by timing.** Adaptive Triggering's white-box signal hurts accuracy on disambiguated items for 5 of 6 models, and recalibrating (k, h) does not help.
6. **Validity caveats.** CPD and MGT-B note that their streams are dependent, non-LLR scores, so classical optimality and ARL guarantees do not hold. CURA's certificate covers only false alarms on exchangeable successful runs from the same regime.
7. **No adaptive-attacker evaluation in any paper.**
   - CURA states that its signals "could be suppressed by an agent optimizing against the monitor".
   - CRA describes evasion transforms but reports no numbers for them.
   - CPD mentions entropy-minimizing suffixes as a risk.
   - Sentinel lists `adversarial_evasion.csv` in its artifacts, but no result appears in the text.
   - The unit-of-verification paper shows a structural blind spot: errors in the window interior are caught far less often, e.g. 0.237 vs 1.000 for a 14B judge.
   - Peak+Accumulation's persistence term is a match *ratio*, so benign padding dilutes it.

**What is still open for AI-control (misalignment) applications.**
1. **No paper treats the monitored agent as the adversary.** In control, the untrusted policy picks its actions and so shapes the per-step suspicion stream. With reference value k, any strategy that keeps its expected standardized per-step score at or below k accumulates nothing. That makes k an explicit evasion budget. Open questions:
   - choosing k and h under a minimax or monitor-aware attacker;
   - mixture or multi-k CUSUM and e-detector mixtures (MGT-B's mixture of betting exponents and CURA's betting martingale are the only steps in this direction);
   - low-rate attacks spread across steps and sessions.
2. **LLM-monitor suspicion streams over agent actions are almost unstudied as CUSUM inputs.** Adaptive Triggering's per-step judge (for bias) is the closest. CURA found a single-screenshot LLM judge at chance. The unit-of-verification paper finds LLM monitors discriminate best when reviewing 1–2 actions per call (J peaks at L ∈ {1,2} for all six judges), which supports per-step scoring followed by sequential accumulation over longer review windows.
3. **No per-context adaptive baseline in the CFAR sense.** The transfer failures above (Sentinel, CURA, MGT-B, CRA) are the problem CFAR-style robust per-deployment or per-task normalization targets. No paper estimates such a baseline online beyond CPD's within-prompt median/MAD, and none tests robustness when the attacker can contaminate the baseline window.
4. **Cross-session accumulation is absent.**
5. **Certified and anytime-valid calibration has started but is thin.** CURA's Learn-then-Test bound on honest trajectories and its Ville-martingale variant (FPR 0.097 at α=0.10) are the templates. Nobody combines certification with distribution shift, adaptive attack, or per-deployment baselines.

**Port risk.** CURA (CUSUM over agent behavior, honest-run Learn-then-Test certificate, escalation to a frontier overseer, framed with AI-control citations) and Sentinel (per-channel CUSUM, per-deployment healthy null, judge escalation) together make "CUSUM over per-step agent signals with a benign-calibrated threshold" prior art. Our contribution must rest on:
- adversarial or scheming agents with monitor-aware attacks;
- LLM-monitor suspicion streams;
- CFAR baselines that survive deployment shift and contamination;
- cross-session accumulation;
- guarantees that survive adaptation.

**Evaluation practices to adopt from the cluster:**
- matched-FPR token-count and step-count CUSUM baselines (CURA);
- matched-budget fixed-schedule or random-trigger controls (Adaptive Triggering, MGT-B);
- Lead / time-to-detect relative to onset (SafeDream, CRA);
- matched clean "twins" and informedness rather than catch alone (unit-of-verification paper);
- benign-anchored calibration on external traffic (CRA);
- held-out-family and cross-model transfer splits (CRA LOFO, Sentinel transfer).

---

## Card 1: CPD Online: sequential entropy CUSUM for adversarial suffixes (arXiv 2605.19966)

**1. Citation and gist.** M. Alshaalan, M. R. D. Rodrigues (UCL), "Detecting Fluent Optimization-Based Adversarial Prompts via Sequential Entropy Changes," ICML 2026 (PMLR 306), arXiv 2605.19966 (2026-05-19). CPD runs a one-sided Page-CUSUM over the user tokens' next-token entropies, standardized by the deployment's fixed system prompt (median/MAD). It detects optimization-based jailbreak suffixes and localizes where they start.

**2. Threat model.** Misuse/jailbreak: a harmful request plus an optimization-generated suffix (GCG, including a guard-adaptive GCG subset optimized to evade LLaMA Guard; AutoDAN; AdvPrompter; BEAST; AutoDAN-HGA). Attackers do not know about CPD. No CPD-adaptive attack is run; the impact statement only notes that adaptive adversaries "may attempt to engineer suffixes that minimize entropy shifts".

**3. Method.**
- Signal: `H_t = −Σ_v p(v|x_<t) log p(v|x_<t)` for each user token, from one forward pass. Requires logits.
- Baseline (per deployment): `μ̂0 = median(H_i^sys)`, `σ̂0 = max(ε, 1.4826·median|H_i^sys − μ̂0|)` over the fixed system-prompt tokens. Standardize `Z_t = (H_t^usr − μ̂0)/σ̂0`.
- Statistic: `W_t^+ = max(0, W_{t−1}^+ + Z_t − k)`, W_0 = 0. Alarm `τ = inf{t: W_t ≥ h}`. Prompt score `s = max_t W_t` (used for ROC).
- Onset estimate (backtracking): `ν̂ = 1 + max{t < τ : W_t = 0}`.
- k = 0 ("canonical Page-CUSUM"). Sensitivity at k ∈ {−0.5, 0, 0.5}: k = −0.5 maximizes F1 on all six models but "lies outside the classical regime"; k = 0.5 is uniformly worse.
- h: tuned per training fold to maximize F1 (5-fold stratified CV). Example pooled values for visualization: h = 43.9 at k = 0, h = 26.05 at k = 0.5.
- No ARL or theoretical FA design. The authors state the statistic is not an LLR and that token dependence violates CUSUM assumptions, so no minimax optimality is inherited.
- Single alarm per prompt; O(1) per token.
- Hybrid mode: LLaMA Guard is invoked only if `s ≥ τ_gate`.

**4. Data and evaluation.**
- Per model: 1,012 adversarial prompts (200 GCG, 200 AutoDAN, 312 AdvPrompter, 100 BEAST, 200 AutoDAN-HGA) and 1,012 benign prompts (TyDiQA + OpenOrca, 506/506), with perplexity matched to the fluent attacks (α = 1, 70 log10-PP bins). Global-PP AUROC is within ±0.04 of 0.5 by construction.
- Six models: LLaMA-2-7B/13B, Vicuna-7B/13B, Qwen2.5-7B/14B.
- Gating stress test: 17,297 prompts (724 adversarial, 16,573 benign, 3× PP-gap).
- Metrics: F1, AUROC, localization category shares, guard calls saved.

**5. Key results.**
- LLaMA-2-7B, k = 0: AUROC 0.88, F1 0.82. Global PP AUROC 0.46; best windowed perplexity (WPP15) F1 0.74, AUROC 0.77.
- Across models: CPD F1 0.77–0.85 vs. best WPP 0.74–0.83. CPD wins F1 on all six (Vicuna-7B is a +0.001 tie). AUROC is lower than WPP on Vicuna-7B (0.82 vs 0.85).
- Mechanism ablation (LLaMA-2-7B):

  | Signal | CUSUM F1 / AUROC | Window w=1 F1 / AUROC |
  |---|---|---|
  | NLL | 0.874 / 0.918 | 0.734 / 0.783 |
  | Entropy | 0.818 / 0.878 | 0.699 / 0.706 |

  Accumulation, not the choice of signal, drives the gain. NLL beats entropy, but entropy admits the system-prompt baseline.
- Localization: 79.6% of CPD triggers fall inside the suffix (WPP: 17.0–46.3%), 0% before the suffix, 20.45% on benign prompts.
- Leave-one-attack-out generalization:
  - k = 0: CPD F1 0.49 / 0.45 / 0.47 vs. WPP 0.51 / 0.47 / 0.48, a tie or a slight loss.
  - k = −0.5: 0.53 / 0.49 / 0.51 vs. 0.51 / 0.47 / 0.48.
- The F1-optimal operating points carry high FPR. In the PP-gap appendix: FPR 0.29 / 0.20 / 0.18 at α = 1 / 2 / 3 (TPR ≈ 0.84). At α = 3, WPP15 FPR is 0.99 while CPD AUROC is 0.90.
- Gating LLaMA Guard: LG1 hybrid F1 0.82 with 42.2% of guard calls saved (WPP5: 18.2%); LG2 0.73 with 33.8% saved (WPP10: 13.5%). At the literal F1-optimal threshold: 22.3% / 16.7%.
- Supporting comparison with SPD: F1 0.82 vs. 0.78.

**6. Limitations.**
- No LLR or ARL guarantees.
- Needs token probabilities.
- Calibration needs a benign validation corpus; benign distribution shift needs recalibration.
- Only suffix attacks are tested (no prefix or indirect injection).
- No detector-aware attacker. Low-rate or entropy-flat suffixes are untested.
- Held-out attack families erase the advantage at k = 0.
- The baseline is per deployment (system prompt) and assumes a fixed system prompt.

**7. Code.** https://github.com/cpdonline/cpdonline

**8. Overlap: medium–high on mechanics, low on threat model.**
- Closest precedent for a robust median/MAD reference from the deployment itself plus a one-sided CUSUM, a `max W` score, and onset backtracking.
- Novel beyond it for us: the time scale is the agent step rather than the token; the input is a monitor-score stream; the adversary is the agent and can shape the stream; cross-session accumulation; low-FPR or certified thresholds instead of F1-optimal ones; contamination of the reference sample.
- **Reuse:** median/MAD standardization against a reference window; the k sensitivity (k < 0 helped); the CUSUM-vs-window ablation design; backtracking onset; "gate the expensive monitor" cost framing.

---

## Card 2: SafeDream: safety world model and CUSUM for early multi-turn jailbreak detection (arXiv 2604.16824)

**1. Citation and gist.** B. Yan, W. Lin, Y. Zhu (IBM Research), S. Wang (UCF), "SafeDream: Safety World Model for Proactive Early Jailbreak Detection," preprint under review, arXiv 2604.16824 (2026-04-18). The frozen target LLM's hidden states are encoded into a 69-d "safety state". A transition model predicts how that state evolves, CUSUM accumulates per-turn risk log-odds, and in an ambiguous "gray zone" imagined attack vs. benign rollouts trigger early alarms.

**2. Threat model.** Multi-turn jailbreak by the user (misuse): X-Teaming/XGuard-Train, SafeDialBench's 7 strategies, SafeMTData actor-network attacks. The attacker does not know the detector. The detector needs white-box access to the target model's hidden states.

**3. Method.**
- State:
  - h_t = layer-19 hidden state of frozen Qwen2.5-7B-Instruct (3584-d);
  - s_t = projection onto K = 5 concept-cone refusal directions (RDO);
  - z_t = [s_t; XAttn(s_t, h_t)] ∈ R^69;
  - action a_t = mean-pooled LLM embedding of the user utterance → 64-d;
  - causal Transformer transition model (4 layers, 4 heads, d = 128, 1.2M params);
  - 2-layer MLP discriminator r_t ∈ [0, 1].
- CUSUM: `Λ_t = logit(clip(r_t, 1e−6, 1−1e−6))`; `G_t = max(0, G_{t−1} + Λ_t − κ)`, G_0 = 0. κ is described as "the average log-odds under benign conversations" (called "tolerance" in the notation table). Alarm at G_t ≥ A.
- Gray zone (τA < G_t < A): roll out M = 8 imagined trajectories of H = 3 steps, sampling actions uniformly from attack and benign utterance pools (built from the training fold). Imagined CUSUM is updated the same way. `V_t = mean Ĝ_{t+H}(attack) − mean Ĝ_{t+H}(benign)`. Alarm if V_t ≥ A_imag.
- **Numeric values of A, τ, A_imag and κ, and how they are calibrated, are not reported.** There is no ARL or FPR targeting procedure.
- Training: soft labels from the mean of 3 classifiers (HarmBench, GPT-4o, MD-Judge); loss L_trans + 1.0·L_disc + 0.5·L_imag (margin δ = 0.3, λ_cal = 0.5); 5-fold CV.

**4. Data and evaluation.**
- XGuard-Train: 30,695 conversations, about 5 turns, 13 risk categories.
- SafeDialBench: 4K conversations, 7 strategies, bilingual.
- SafeMTData: 1.7K conversations, about 8.7 turns.
- Topic-matched benign twins generated by GPT-4o and verified unflagged.
- Compliance point c: first turn where ≥ 2/3 classifiers flag the response.
- Metrics: AUROC, AUPRC, F1, Recall, FPR, **Lead = c − t_det** (positive = alarm before compliance), EWR.
- 8 baselines: guardrails (WildGuard, R2-Guard, BingoGuard, GuardReasoner, SelfDefend) and alignment methods (Circuit Breaker, X-Boundary, TARS) retrained on Qwen2.5-7B.

**5. Key results.**

| Benchmark | SafeDream AUROC / F1 / FPR / Lead | Strongest baseline (TARS) AUROC / F1 / FPR / Lead |
|---|---|---|
| XGuard-Train | 0.908 / 0.891 / 0.079 / 1.11 | 0.895 / 0.876 / 0.059 / 0.38 |
| SafeDialBench | 0.912 / 0.901 / 0.066 / 1.20 | 0.865 / — / — / 0.55 |
| SafeMTData | 0.915 / 0.904 / 0.080 / 1.06 | 0.847 / — / — / 0.31 |

- Guardrails have negative lead (WildGuard −0.53 on XGuard).
- Ablations (XGuard):

  | Variant | F1 | FPR | Lead |
  |---|---|---|---|
  | Full | 0.891 | 7.9% | 1.11 |
  | w/o CUSUM | 0.879 | **13.8%** | 1.49 |
  | w/o imagination | 0.825 | 10.2% | 0.53 |
  | attack-only imagination | — | 25.6% | 1.01 |
  | w/o concept cone | 0.740 | 15.5% | — |

  CUSUM's role is to suppress false alarms at the cost of lead time.
- Turn-order shuffle: Transformer AUROC 0.908 → 0.633; GRU 0.856; per-turn MLP 0.517.
- Lead depends on the compliance definition: −1.53 ("any" classifier) to 1.54 (unanimous).
- Overhead: < 5 ms per turn; imagination < 100 ms.

**6. Limitations (stated and observed).**
- Needs hidden states; the concept cone is model-specific; only one target LLM.
- Transfer to unseen attack families is untested.
- Imagination samples i.i.d. actions.
- Labels come from 3 classifiers.
- Benign twins are synthetic.
- No detector-aware attacker.
- Threshold calibration is undocumented, so FPR guarantees cannot be assessed.

**7. Code.** Not stated in the paper.

**8. Overlap: medium.**
- CUSUM on the log-odds of a learned per-turn risk minus a benign mean is close to "CUSUM over monitor scores".
- The two-threshold design (direct alarm vs. gray-zone escalation) maps onto trusted-monitor → expensive-auditor escalation.
- Novel beyond it for us: adversarial agent rather than adversarial user; calibrated or certified h; cross-session accumulation; attack-aware k.
- **Reuse:** the Lead metric; the "with vs. without CUSUM" lead/FPR trade-off ablation; the clipped-logit transform of probabilities before CUSUM; the turn-shuffle test for temporal dependence.

---

## Card 3: Peak + Accumulation: a proxy-level multi-turn attack score (arXiv 2602.11247)

**1. Citation and gist.** J. A. Corll, "Peak + Accumulation: A Proxy-Level Scoring Formula for Multi-Turn LLM Attack Detection," arXiv 2602.11247 (v2, 2026-03-05). A deterministic, LLM-free conversation score: peak per-turn regex risk + persistence ratio + category diversity + escalation/resampling bonuses. The paper is motivated by CUSUM and Bayesian accumulation analogies but does not implement CUSUM.

**2. Threat model.** Multi-turn prompt injection/jailbreak by a user, detected at an API proxy (firewall). Regex categories. No adaptive attacker. Crescendo-style innocuous attacks are explicitly out of scope.

**3. Method.**
- Per-turn score: `s_i = min(1, Σ matched category weights)`. Weights: instruction_seeding 0.4, role_confusion 0.5, deferred_authority 0.3, escalation_probing 0.3, repetition_resampling 0.2 (detected algorithmically).
- Conversation score: `score = clamp(max_i s_i + (|{i: s_i > 0}|/n)·ρ + max(0, #distinct categories − 1)·δ + β_e + β_r, 0, 1)`, with:
  - ρ = 0.45, δ = 0.15;
  - β_e = 0.2 if ≥ 3 consecutive strictly increasing scores;
  - β_r = 0.7 if ≥ 3 consecutive user-message pairs have word-trigram Jaccard > 0.5 (messages of ≥ 20 tokens).
- Block if score ≥ τ = 0.7. Active from ≥ 2 user turns.
- Theorem ("weighted-average ceiling"): a recency-weighted average of identical scores s equals s, so averaging can never exceed the per-turn maximum.
- Hyperparameters tuned on a validation split; results on a disjoint 20% holdout.

**4. Data and evaluation.** 10,654 conversations:
- 9 handcrafted attacks;
- 579 WildJailbreak-sourced, synthetically composed multi-turn attacks (179 single-category persistent, 300 multi-category, 100 escalation-gradient);
- 6 handcrafted benign;
- 60 "sparse-benign" (one injection turn among benign turns, labeled benign);
- 10,000 WildChat benign (≥ 3 user turns, non-toxic).

Metrics: recall, FPR, precision, F1.

**5. Key results.**
- Recall 90.8% (534/588), FPR 1.20% (121/10,066), precision 81.5%, F1 85.9%.
- Phase transition at ρ 0.375 → 0.400: recall 77.4% → 89.8%, FPR 1.11% → 1.19%. All weight-0.3 single-category attacks cross τ at once, since 0.3 + ρ hits 0.7.
- ρ = 0.6: recall 95.9%, FPR 1.51%.
- Weighted average: 5 of 9 persistent handcrafted attacks scored 0.3–0.5 (below 0.7).
- SafeMTData and hh-rlhf: 0% recall (excluded as out of scope).

**6. Limitations.**
- Synthetic multi-turn composition.
- Regex is brittle to rephrasing.
- The persistence term is a *ratio* (matched turns / n), so interleaving benign turns dilutes it. The authors note that 15 escalation-gradient misses came from benign opening turns diluting the ratio.
- FPs come from roleplay.
- No adaptive or low-rate attacker evaluation.

**7. Code.** https://github.com/Parapet-Tech/parapet (Apache 2.0).

**8. Overlap: low.**
- **Reuse:** the averaging-ceiling argument as motivation for accumulation; the warning that ratio-normalized persistence is defeated by benign padding (a test case for our attacks); the "phase transition" effect of discrete weights against a fixed threshold.

---

## Card 4: DeepContext: GRU intent tracking for multi-turn jailbreaks (arXiv 2602.16935)

**1. Citation and gist.** J. Albrethsen, Y. Datta, K. Kumar, S. Rajasekar (Highflame), "DeepContext: Stateful Real-Time Detection of Multi-Turn Adversarial Intent Drift in LLMs," arXiv 2602.16935 (2026-02-18). A stateful guardrail: per-turn task-attention-weighted fine-tuned BERT embeddings feed a GRU, and the hidden state is concatenated with the current embedding before an MLP classifier.

**2. Threat model.** Multi-turn jailbreaks and prompt injection (Crescendo, ActorAttack, Red Queen, human red-teaming). Misuse. No detector-aware attacker. Agentic goal-drift monitoring appears only as future work.

**3. Method.**
- e_t: 1024-d per task (JavelinGuard Mahendra/Raudra pooling).
- `h_t = GRU(h_{t−1}, e_t)`: 3 layers, hidden size 2048, RNN dropout 0.5.
- `R_t = [φ(h_t); e_t]` → MLP (hidden 4096, LayerNorm, GELU) → sigmoid.
- Focal loss γ = 2; 1 epoch; lr 1e−5; batch 512; AdamW; bf16.
- Trained on 437,058 sequences (about 20% malicious; partly proprietary).
- No CUSUM. **Decision threshold and calibration not specified.**

**4. Data and evaluation.**
- 1,010 conversations: 800 benign (200 each from LMSYS, Glaive function-calling, Nemotron instruction-following, HH-RLHF) and 210 multi-turn jailbreaks (35 each from JailbreakPrompts, ScaleAI MHJ, DEFCON, Red Queen, XGuard-Train, Automated-Multi-Turn).
- Attacks: median 7 turns (max 49). Benign: median 4 turns (max 18). **Lengths are not matched.**
- Some sources overlap the training datasets (samples claimed disjoint).
- Metrics: F1, recall, precision, MTTD (mean turns to detection). FPR is not reported.

**5. Key results.**

| Model | F1 | Recall / Precision | MTTD |
|---|---|---|---|
| DeepContext | 0.84 | 0.83 / 0.86 | 4.24 |
| Llama-Prompt-Guard-2-86M | 0.67 | | |
| Granite-Guardian-3.3-8B | 0.67 | | |
| GPT-5-nano judge | 0.65 | | |
| Llama-Guard-4-12B | 0.51 | | |
| Qwen3Guard-Gen-8B | 0.51 | | 3.12 |
| Azure Prompt Shield | 0.19 | | 8.00 |

- LLM guards do the same or better with a last-5-turn sliding window than with full context (e.g., Llama Guard 4: 0.42 → 0.51).
- JailbreakBench single-turn: F1 0.98 (recall 1.00, precision 0.95).
- Latency 19 ms per turn (T4 and A100); 474 ms on CPU.

**6. Limitations.**
- Function-calling false positives.
- Proprietary training data.
- No FPR or operating-point calibration.
- Possible length confound.
- No adaptive attacks.
- Internal inconsistency: Granite latency is 125 ms in Table 7 vs. "1,430 ms" in §5.2.

**7. Code.** Not released. Live demo at huggingface.co/spaces/highflame/DeepContext-Demo.

**8. Overlap: low.**
- **Reuse:** a learned recurrent baseline to compare against transparent CUSUM over monitor scores; the MTTD metric; the observation that full-context LLM guards are diluted by benign preamble.

---

## Card 5: CRA: Conversational Risk Accumulation framework and CRA-Bench (arXiv 2607.19361)

**1. Citation and gist.** S. Mishra, D. Chukkapalli, G. R. Naik, "Stateful Guardrails for Multi-Turn LLM Systems: A Conversational Risk Accumulation Framework," arXiv 2607.19361 (v1 stamped 2026-06-03). A session-layer guardrail with three trajectory signals: semantic drift from an anchor, an entity information-accumulation graph, and a refusal-slope "compliance gradient". They are fused convexly or by a small GRU (CRA-Net) trained with length- and family-adversarial heads. Comes with new synthetic benchmarks.

**2. Threat model.** Multi-turn misuse. Five-type taxonomy: fragmentation, behavioral conditioning, aggregation leakage, intent drift, context poisoning. The 5-family benchmark covers fragmentation, conditioning, aggregation, persona priming and context stuffing. The adversary is not detector-aware in the experiments. Three evasion transforms are described (§8.6: interleaved benign turns, paraphrase drift, entity fragmentation), but **no evasion numbers appear in the text**. The agent extension (an IAG over tool traces, and a privilege/scope-escalation trend instead of refusal slope) is an architectural sketch only.

**3. Method.**
- Signals:
  - `S1(t) = 1 − cos(e0, e_t)`: e0 = embedding of the declared intent, e_t = embedding of summary(t); all-MiniLM-L6-v2.
  - `S2(t) = Σ_k w(v_k) f(a_{k,t}) / Σ_k w(v_k)^max` with f(a) = a²: spaCy NER over responses; NIST-SP-800-60-like tier increments 0.05 / 0.10 / 0.20 / 0.35.
  - `S3(t) = −OLS slope` of a keyword refusal indicator over a window w (default 6, cap 32).
- Convex fusion: `CRA(t) = α·clip(S1/2) + β·S2 + γ·σ(κ·S3)`, defaults (0.35, 0.45, 0.20). Fires when CRA(t) ≥ θ. Session score = max_t CRA(t). Soft-warn defaults: S1 0.85, S2 0.20, S3 0.35, CRA 0.45.
- CRA-Net:
  - 2-layer GRU (h = 128, about 52K params) over x_t = (S̃1, S2, S̃3, response length, log turn index, new entities, refusal probability, moderation score);
  - per-turn weighted BCE with session label broadcast, w_t = (t/n)^ρ;
  - gradient-reversal length head (λ = 0.05);
  - "DA" variant adds a gradient-reversal threat-family head (λ_fam 0.3 for 3 families, 0.1 for 5);
  - Deep CORAL alternative;
  - temperature scaling.
- Calibration:
  - (a) θ for TPR = 0.90 on a mixed labeled validation split;
  - (b) the recommended "benign-anchored" recipe: θ for benign FPR ≤ 5% or 1% on N = 1,000 ShareGPT sessions.
- Stated latency floor for conditioning detection: L_cond ≥ w. Hysteresis/persistence is suggested against evasion. No CUSUM.

**4. Data and evaluation.**
- CRA-Bench v0.1: 1,200 sessions (600 positive, 600 topic-matched benign twins), T = 8 user turns, 3 families.
- v0.2: GPT-4o-mini paraphrases (8 per template).
- 5-family set: 2,000 sessions.
- Human-CRA-Transfer: 750 CoSafe gradual-escalation positives and 222 ShareGPT 3-turn negatives.
- CoSafe 1,800 (length confound: positives 3 turns, negatives 1; length-only AUROC 1.0).
- ShareGPT benign: about 1,000.
- Split 60/20/20.
- Metrics: trajectory AUROC, sFPR at TPR = 0.90, TTD, bootstrap CIs, leave-one-family-out (LOFO).

**5. Key results.**
- v0.1 test (N = 240):

  | Method | AUROC | sFPR | TTD |
  |---|---|---|---|
  | Convex fusion | 0.598 | 0.667 | |
  | Feature-only MLP | 0.787 | | |
  | CRA-Net | 0.993 | 0.008 | 1.83 |
  | CRA-Net DA | 0.919 | 0.292 | 3.65 |
  | GPT-4o-mini full-transcript judge | 1.000 | | |

- Paraphrased v0.2: CRA-Net 0.829 (−0.16; inverts on fragmentation at 0.417). DA 0.919 (Δ = 0), sFPR 0.175.
- LOFO, v0.1, vanilla: fragmentation 0.447, conditioning 1.000, aggregation 0.000 (inverted by an NER artifact).
- 5-family LOFO means: vanilla 0.628, DA 0.647, CORAL 0.635.
- Benign-anchored calibration (5-family): DA TPR 1.000 at benign FPR 0.000 (θ = 0.492); vanilla TPR 0.640 (θ = 0.774). Native TPR-0.90 calibration gives benign FPR 0.800 (vanilla) and 1.000 (DA).
- Human transfer: CRA-Net 0.919, DA 0.929, Llama Guard 3-1B 0.695, Qwen3Guard-Gen-0.6B 0.997.
- Length-matched CoSafe vs ShareGPT: convex 0.083 (below chance); CRA-Net (λ = 0.05) 0.9917, sFPR 0.4545.
- Zero-shot Llama Guard 3 and Qwen3Guard reach about 0.99 on the 5-family set.
- The keyword S3 proxy vs. Llama Guard 3 labels: κ = 0.00 (11.5% agreement).
- Signal latency: 73 / 407 / 1,743 ms per turn at T = 8 / 32 / 128 (CPU).

**6. Limitations.**
- Templated synthetic benchmarks.
- Strong template and family memorization (LOFO collapse).
- Weak proxy signals.
- θ unstable across benchmark versions.
- Evasion not quantified.
- Benign FPR measured only on ShareGPT proxies.
- TTD defined inconsistently: "turns remaining before the labeled onset" (§8.3) vs. "turns before the end of the session" (results prose).

**7. Code.** Artifacts are listed in detail, but the URL is "withheld for double-blind review" and the code is to be released at the camera-ready stage.

**8. Overlap: medium.** Session-level accumulation for safety, benign-anchored calibration, and an agentic sketch, but no sequential test and no cross-session accumulation.
- **Reuse:**
  - calibrating on mixed labeled data gives unusable deployment FPR, so calibrate on external benign traffic;
  - length-matched and topic-matched twins plus a length-only baseline;
  - LOFO as a held-out-attack-family diagnostic;
  - simple convex fusion of heterogeneous signals can be near chance.

---

## Card 6: MGT-B: CUSUM-shaped monitoring and re-decoding for quantized reasoning (arXiv 2607.20129)

**1. Citation and gist.** E. H. Ettifouri, A. Belfatmi, M. S. Yahaya Alassan, W. Dahhane (Novelis Research), "CUSUM-Shaped Inference-Time Monitoring and Targeted Re-Decoding for Quantized Small Language Model Reasoning," arXiv 2607.20129 (v2, 2026-09-02). Windowed uncertainty/repetition features become position-conditional empirical tail probabilities, which are turned into mixture "betting factors" and accumulated with a CUSUM-shaped reset. An alarm triggers coherent rollback (tokens, KV cache, detector state) and constrained re-decoding.

**2. Threat model.** Benign failure: repetitive or unproductive reasoning in an INT4 1.5B model. No adversary.

**3. Method.**
- Windows: 64 tokens, stride 32.
- Window score: `s_j = 0.15·H̄ + 0.10·(−ℓ̄) + 0.20·R + 0.35·D + 0.18·L+ + 0.02·L−`, where R = repeated generated 6–8-grams, D = increased confidence on repeated n-grams, L± = local entropy shifts.
- Positional calibration: `q_j = (1 + Σ_{u∈C_b(j)} 1{u ≥ s_j}) / (|C_b(j)| + 1)`, with reference scores from "healthy" (correct, non-truncated) reference trajectories in the same position bucket.
- Betting factor: `e_j = (1/|Γ|) Σ_γ γ·q̃_j^(γ−1)`, Γ = {0.1, 0.3, 0.5, 0.7}, with q clipped at 1e−6.
- Statistic: `S_j = max(0, S_{j−1}) + log e_j`. Alarm at S_j ≥ h.
- Thresholds: h = 11.4293 on MATH-500 (3 alarms in 62 healthy dev trajectories, 4.84%); h = 47.6874 on Omni-MATH (14/299, 4.68%).
- The authors explicitly do not claim e-process or e-detector validity: E[e_j | F] ≤ 1 is unproven, and windows overlap and are dependent.
- Repair:
  - roll back to the most recent reset region plus 64 tokens;
  - re-decode at temperature 0.6 with repetition penalty 1.1 and suspect n-gram blocking;
  - at most 3 rerolls, 2 refractory windows.

**4. Data and evaluation.**
- DeepSeek-R1-Distill-Qwen-1.5B in bitsandbytes INT4.
- MATH-500 × 3 seeds (1,500 paired units).
- Omni-MATH: 300 reference / 300 dev / 500 test, × 3 seeds.
- Accuracy with problem-clustered bootstrap; sampled-token cost; matched-random-intervention control.

**5. Key results.**
- MATH-500: 54.73% → 56.40% (+1.67 pp, CI [+0.47, +2.80]); matched random 54.60%.
  - 53 corrections vs. 28 regressions; McNemar p = 0.0073 (Holm 0.0146).
  - +5.14% sampled tokens.
  - Intervention rate 22.6% (random: 9.4%).
  - Truncations rise from 2 to 18 per 1,500.
- Omni-MATH: 16.67% → 16.60% (−0.07 pp, CI [−0.33, +0.20]); intervention rate 4.6%.
- Seed-0 ablations: removing the reset leaves accuracy unchanged (56.2%); repetition-only 56.0%; rollback only 54.0%; repetition penalty alone 52.2%.
- 5-sample self-consistency: 70.0% at about 4.84× the tokens.

**6. Limitations.** One model, one quantization, math only. No changepoint labels, so no precision, recall or delay. The threshold does not transfer across datasets. Not a valid e-detector.

**7. Code.** No public repository given; only commit hashes and artifact provenance.

**8. Overlap: low–medium.** Not a safety paper.
- **Reuse:**
  - position-conditional conformal-style calibration of scores against reference trajectories (suspicion scores likely drift with step index);
  - mixture-of-power calibrator betting factors as a route to an e-detector;
  - matched-random-intervention control;
  - the explicit separation of operational usefulness from statistical validity.

---

## Card 7: Agent Trajectory Sentinel: ESN + CUSUM failure monitors with deterministic verification and repair (arXiv 2608.02464)

**1. Citation and gist.** S. Dubey, "Real-Time Detection and Repair of LLM Agent Failures," arXiv 2608.02464 (2026-08-03). A one-class echo-state-network (ESN) ensemble, fit only on healthy agent runs, predicts the next step's telemetry. Normalized prediction error goes into per-channel one-sided CUSUMs fused by max. The threshold is a quantile of healthy-run maxima. The paper adds deterministic checks (numeric grounding, required-call coverage, tool-contract) and rollback repair.

**2. Threat model.** Benign agent failures: looping, tool-error cascade, goal drift, context corruption (wrong_document, malformed_json), fabrication/grounding loss, silent abort. Failures are injected or organic. **No adversary.** The provenance table lists `adversarial_evasion.csv` and `tamper_check.csv`, but no adversarial result is reported in the text.

**3. Method.**
- Telemetry x_t = [e_t; u_t; m_t], d ∈ {43, 51, 60}:
  - 32-d char-3-gram hash embedding of step output (tool results appended in v2);
  - 4 token-surprisal aggregates;
  - action one-hot, log latency, output length, error flag;
  - v3 adds 8 behavior dimensions (drift, task-anchor similarity, retry, …);
  - v4 adds 9 content-grounding dimensions.
- Reservoir per channel: `h_t = (1−α)h_{t−1} + α·tanh(W h_{t−1} + W_in x_t)` with W frozen; ridge readout predicts x_{t+1} (fit in 1.7 s, vs. 68 s for a GRU).
- Surprise: `q_t = (1/K) Σ_k mean_d((x̂ − x)/σ_err)²`, with σ_err from held-out healthy runs.
- CUSUM: `S_t^(c) = max(0, S_{t−1}^(c) + z(q_t) − κ)`, then `s_t = max_c S_t^(c)` (per-channel accumulation avoids diluting a shift confined to one channel). The exact z(·) and κ values are not given.
- Threshold: `θ = Q_{1−β}(max_t s_t over healthy validation episodes)`. This controls the per-episode FA rate at budget β (5% used).
- Variants:
  - robust-z calibrated ESN + Δ-Mahalanobis hybrids (weight, max, or logistic fusion);
  - "dual-budget" per-stream thresholds;
  - a memoryless grounded content stream;
  - a 5-line completion check.
- The author finds the per-channel-max wrapper carries most of the margin: a GRU in the same wrapper beats the ESN.

**4. Data and evaluation.**
- 2,823 committed episodes over 25 datasets; 770 with real tools and live agents (bespoke, LangGraph, AutoGen).
- Models: qwen2.5 7b/3b, llama3.1 8b, gemini-2.5-flash.
- A simulator with constructed telemetry.
- External sets: AFTraj-2K (1,882 after a T ≥ 4 filter: 1,111 healthy, 771 failed) and ATBench (604 of 1,000).
- Metrics: episode AUROC, detection rate at a matched FA budget, lead steps, ECE.

**5. Key results.**
- Cross-deployment transfer (qwen2.5:7b → llama3.1:8b): AUROC 0.527 (healthy FA 0.75). Recalibrated on the target: 0.885. Gemini corpus: 0.794.
- Horizon effect, ESN minus Mahalanobis detection: +0.09 at ≤ 3 post-onset steps, +0.14 at 4–8, +0.40 at ≥ 9. Δ-Mahalanobis wins on short-episode datasets (0.848 vs 0.777; 0.665 vs 0.556).
- Simulator: detection 0.707 ± 0.068 at 4.4% FA, AUC 0.872, mean lead 4.6 steps.
- AFTraj: AUROC 0.745 but detection 0.048 at a 5% budget. 61% of failures end within 3 steps of onset. At horizon ≥ 9: ESN 0.509 vs. Mahalanobis 0.170.
- ATBench: AUROC 0.779, detection 0.311. Δ-Mahalanobis at chance (0.457).
- Hybrid grand-mean AUROC 0.826 (ESN 0.802, Δ-Mahalanobis 0.807).
- Content grounding: pooled content detection 0.28 → 0.59 (abstract) or 0.27 → 0.58 (Table 2); behavioral detection 0.74 → 0.79.
- Measured judge (gemini-2.5-flash): p_detect 0.548, p_false 0.052, vs. assumed 0.90 / 0.02. Escalation detection recovery drops from 82% to 43%.
- Organic failures:
  - monitors catch 1 of 3 fabrications;
  - within-organic AUROC 0.31–0.42;
  - temperature-matched null false-alarms on 36% of healthy episodes;
  - the completion check catches 7/7 silent aborts.
- Deterministic checks:
  - 60% caught (96% with coverage) at 0/63 FP, vs. the monitor's 54% at 11/63 (17%);
  - held-out: 54% / 93%, 0/64;
  - llama: 110/110 at 0/10;
  - provoked fabrications: 26/26;
  - tool_contract: 0/1,825 healthy FP; 46% of context corruption; 215/218 within one step.
- Repair: the "located" rung recovers 45% vs. 16% for resampling (p = 0.0005); task success 52% → 73%.
- Ablating token surprisal: ΔAUROC +0.000.
- Cost: about 200 µs per step for the monitor, plus a 674 µs median for the adapter.
- **Slow goal drift evades every per-step-surprise monitor tested.**

**6. Limitations.**
- No cross-deployment transfer: the healthy null must match serving temperature, tools, probes and latency.
- Slow drift is missed.
- Content coverage depends on the telemetry carrying it.
- Plausible-value corruption cannot be detected.
- Fabrication base rates are too low.
- Mock tools and research loops only.
- No adversary.

**7. Code.** https://github.com/sunnydubey1111/agent-trajectory-sentinel. Dataset and demo on HuggingFace (sunnydubey1111/agent-trajectory-sentinel).

**8. Overlap: high on mechanics, low on threat model.** Per-step score → CUSUM → threshold from healthy-run maxima; mandatory per-deployment null; escalation to an LLM judge.
- Novel beyond it for us:
  - a misaligned agent that shapes its stream;
  - suspicion scores instead of telemetry surprise;
  - CFAR-style robust baselines to address the 0.527 transfer collapse without full recalibration;
  - the slow-drift and low-rate regime they leave open: absolute-score CUSUM rather than prediction-error surprise, which normalizes drift away;
  - cross-session accumulation.
- **Reuse:** per-channel CUSUM with max fusion; θ from the healthy-episode max quantile; horizon-stratified analysis; measuring the judge rather than assuming it; matched FA budgets; the dual-layer idea (statistical monitor plus deterministic checks).

---

## Card 8: CURA: certified runtime alarms for computer-use agents (arXiv 2608.27808)

**1. Citation and gist.** D. Kumar, S. Tayebati, D. Naik, A. S. Rios, N. Ahuja, O. Tickoo, R. Krishnan, A. R. Trivedi (UIC, Intel Labs, Capital One), "CURA: Certified Runtime Alarms for Computer-Use Agents," arXiv 2608.27808 (2026-08-28). A read-only external monitor fuses effort, reasoning-semantics, execution-physiology and visual-dynamics signals into a CUSUM. Its threshold is certified by Learn-then-Test on successful trajectories, giving finite-sample false-alarm control. Alarms drive escalation to a frontier overseer, abstention, or stopping.

**2. Threat model.** Benign failures of a capable CUA, framed around unreliable self-report: 64 of 71 failures end with a success claim. Explicitly "no evidence of strategic deception and do not study adversarial evasion". The paper cites AI control (Greenblatt et al. 2024) and warns that signals "could be suppressed by an agent optimizing against the monitor".

**3. Method.**
- Six online signals:
  - windowed pivot-language rate (16 pre-registered regexes, 10-step window);
  - physiology NLL (a diagonal Gaussian per action type over z-scored vitals: screen change, step duration, output tokens, reasoning length);
  - visual surprise `r_t = 1 − cos(ê_{t+1}, e_{t+1})` from a ridge predictor on frozen SigLIP embeddings, trained on successes;
  - output tokens;
  - state-visit entropy;
  - screen-novelty EMA (enters with negative sign).
- Step score: `S_t = Σ_j sign_j (s_{j,t} − μ_j)/σ_j` (signs fixed a priori; constants frozen from the fit set).
- CUSUM: `W_t = max(0, W_{t−1} + S_t − k)`, **k = 0.5**. `τ = inf{t: W_t ≥ θ}`.
- Calibration:
  - successes are split into disjoint fit and calibration sets;
  - Learn-then-Test tests θ_1 > … > θ_m in fixed sequence with exact binomial tests of H_j: FPR(θ_j) > α, and stops at the first non-rejection;
  - guarantee: Pr(FPR(θ̂_α) ≤ α) ≥ 1 − δ, with δ = 0.05;
  - certified thresholds: θ = 42.70 / 16.97 / 5.47 at α = 0.05 / 0.10 / 0.20.
- Anytime-valid variant: a betting martingale over per-step conformal p-values; by Ville, Pr(sup_t M_t ≥ 1/α | success) ≤ α.
- Task-level risk ρ(Z): ℓ2 logistic regression (C = 0.5) over 8 trajectory signals, GroupKFold(5) by task.
- Failure labels are used only for low-dimensional fusion and evaluation.

**4. Data and evaluation.**
- 361 OSWorld-Verified tasks: 290 successes, 71 failures; 6,883 GUI actions; about 9,100 executor calls.
- Monitored pipeline: qwen3.7-plus gate/planner/executor.
- Replication on UI-TARS-1.5-7B (113/361 solved).
- Metrics: AUROC with task-level bootstrap; recall, realized FPR and lead at certified α; held-out three-way splits (200 replicates); cascade score; tokens saved.
- Baselines: token-count CUSUM and step-count trigger, calibrated by the same Learn-then-Test.

**5. Key results.**
- Pipeline mean task score 82.9 (human 72.4). Claim precision 80.7% (UI-TARS: 44.9%). Zero self-declared failures (UI-TARS: 142).
- Task-level AUROC: composite 0.828 [0.775, 0.877]. Tokens alone 0.802 (Δ = +0.026, p = 0.101). Length only 0.794. Fold-internal floor 0.802.
- Certified online alarm:

  | α | Realized FPR | Recall | Median lead (steps before termination) |
  |---|---|---|---|
  | 0.05 | 0.024 | 0.282 | 42 |
  | 0.10 | 0.066 | 0.423 | 31 |
  | 0.20 | 0.159 | 0.606 | 19 |

- Held-out three-way split (test FPR / recall): 0.019 / 0.24, 0.056 / 0.41, 0.140 / 0.56. Test FPR exceeds α in 2.0% / 4.5% / 6.5% of replicates.
- Baseline recall at the same α levels: token CUSUM 0.27 / 0.34 / 0.38; step count 0.18 / 0.34 / 0.47.
- Martingale variant: FPR 0.097 at α = 0.10; fires earlier on fewer failures.
- Empirical 10% FPR: recall 49.3%, lead 23.
- Resolvable risk by stage: gate 0.688 AUROC, plan 0.736, step 15 0.809, full 0.842.
- Escalation: alarm-gated recovers 23/70 using the overseer on 38. Cascade mean score 86.8, full-solve 84.5%.
- Stopping at 10% FPR saves 28.3% of tokens but costs 8 pp of full-solve.
- Per-domain recall: multi-app 0.61, browser 0.22, media/document 0.
- Frontier-planner transfer: AUROC 0.717, realized FPR triples.
- Negative results: token log-probabilities give no signal beyond length; a single-screenshot LLM judge is at chance (0.497); failure-type prediction 0.44–0.59.
- The 7B replication of the composite fails (0.768 vs. 0.784 for length).

**6. Limitations.**
- 71 failures, one pipeline.
- Non-adversarial; the signals (length, repetition, pivot phrasing) are suppressible.
- Blind to fast, quiet failures and to belief-level errors.
- Lead is measured to termination, not to an onset (no onset labels).
- The certificate is false-alarm-only, per regime, and needs recalibration under shift.

**7. Code.** "Will be released with the code" (not available at paper time).

**8. Overlap: high. This is the closest prior art for "CUSUM over per-step agent signals with a certified FPR from honest runs", in AI-control language.**
- Novel beyond it for us:
  - scheming or sabotaging agents with monitor-aware evasion, where k = 0.5 defines an explicit stealth budget;
  - LLM-monitor suspicion streams rather than effort and physiology;
  - CFAR per-deployment baselines that keep certification under shift, which CURA fails (FPR triples);
  - cross-session accumulation;
  - certificates or anytime validity under adaptive attack.
- **Reuse:** Learn-then-Test fixed-sequence binomial calibration on honest trajectories; reporting recall and lead at certified α; matched-α token and step-count CUSUM baselines (mandatory); held-out three-way split replicates; the Ville-martingale comparison.

---

## Card 9: Adaptive Triggering: CUSUM-triggered mid-reasoning bias correction (arXiv 2608.25379)

**1. Citation and gist.** N. Kim, M. Mancenido, H. Liu (ASU), "Adaptive Triggering for Bias Correction in LLM Reasoning," arXiv 2608.25379 (2026-08-26). A per-step bias-risk score feeds a one-sided CUSUM. A targeted in-context reflection is injected only when the statistic crosses a calibrated threshold. White-box and black-box (LLM-judge) signals share the loop.

**2. Threat model.** Social bias in chain of thought (benign failure). No adversary; adversarial manipulation of the signal is explicitly unevaluated.

**3. Method.**
- Signals:
  - white-box: `b_t = max(0, p_t(s) − p_t(u))`, normalized forced-continuation probabilities of the stereotype answer s vs. "not enough info" u;
  - black-box: an LLM judge scores the latest step 0–10, divided by 10.
- Statistic: `S_t = max(0, S_{t−1} + b_t − k)`. Fire when S_t > h, then reset S to 0 with a one-step cooldown (b and S keep updating; no trigger).
- (k, h) chosen per detector by grid search over fresh closed-loop generations on a calibration split, maximizing `acc(C_dis) − bias(C_amb) − λ·noncompletion` (λ = 1), and kept only if better than the default on a validation split.
  - White-box: selected (k = 0.45, h = 0.30), default (0.30, 0.45).
  - Black-box: selected (0.25, 0.75), default (0.40, 0.60).
- Null-FPR calibration is explicitly rejected because BBQ has no clean null.
- Reported ARL0 ≈ 5.8 steps for the default white-box parameters (resampled from a null pool of n = 86,587 scores), below the 8-step cap.

**4. Data and evaluation.**
- BBQ, 9 categories, with four label-matching bugs corrected.
- 7 open-weight models (Qwen2.5-1.5B/7B, Llama-3.1-8B, Mistral-7B, Gemma-2-9B, DS-R1-Distill-Qwen-7B and Llama-8B); 6 in the cross-model analysis.
- gpt-4o-mini on a 504-item stratified subsample; independent-judge replication with n = 252 per split.
- Baselines: no intervention; fixed-interval reflection every N steps; matched-budget cadence sweep N ∈ {2, 3, 5, 8, 10}.

**5. Key results.**
- gpt-4o-mini, disambiguated items: none 92.1%, fixed 82.9%, adaptive black-box 90.1% at 0.60 vs. 1.00 interventions per item. Independent judge: +6.75 pp over fixed (CI [+2.78, +10.71], p = 0.0015).
- White-box across 6 models:
  - ambiguous accuracy improves on all six (+1.3 to +9.9 pp);
  - disambiguated accuracy drops on five (−1.9 to −15.6 pp);
  - 3,112 correct→incorrect flips vs. 761 repairs.
- Recalibration leaves white-box traces identical (75.4% accuracy).
- A fixed N = 5 schedule fires on 0% (Gemma) to 99% (DS-Llama-8B) of items.
- Black-box adaptive beats fixed schedules at matched firing rate.
- Non-completion: 8.5% on items where white-box fires vs. 4.5% elsewhere (DS-Llama-8B).

**6. Limitations.** Self-judging (partly addressed with an independent judge); BBQ only; one calibration model; no adversarial robustness.

**7. Code.** https://github.com/clairekim59/adaptive-triggering

**8. Overlap: low–medium.** A per-step LLM-judge score (0–10) fed to CUSUM is structurally our setting, with a different target.
- **Reuse:**
  - "the trigger cannot fix a misaligned signal": validate that suspicion scores separate malicious from benign-but-unusual steps;
  - the matched-budget comparison of adaptive vs. fixed schedules (analogue: CUSUM-triggered audits vs. periodic or random audits at an equal audit budget);
  - report ARL0 under a null pool;
  - self vs. independent judge.

---

## Card 10: The unit of verification in pre-execution LLM oversight (arXiv 2608.23941)

**1. Citation and gist.** Y. Han, C. Yan, W. Zhang (USTC), "More Rejective, Not More Discriminative: The Unit of Verification in Pre-Execution LLM Oversight," arXiv 2608.23941 (2026-08-25). A pre-registered "twin-prefix" instrument varies only how many planned actions a fallible LLM monitor reviews per call. Longer windows raise catch, but clean false rejection rises in lockstep, so informedness (Youden J) peaks at L ∈ {1, 2} for all six judges in both domains.

**2. Threat model.** AI-control trusted monitoring before irreversible execution. Errors are single injected, environment-accepted wrong writes, stratified into cross-customer scope, wrong argument, and unrequested extra write. They are non-adaptive and closer to honest mistakes than deliberate sabotage. The authors note that adaptive attacks (Terekhov et al. 2026b) bound how far this extrapolates, and call interior error placement an attack (worst-case position analysis).

**3. Method.** Not sequential.
- Metrics:
  - `J(L) = catch(L) − FR(L)`, always co-reported with clean FR;
  - score-mode AUC(L) and per-L recalibrated J*(L) from verbalized 0–100 error probabilities.
- Cost model: `C(L) = F + L·i` with F ≈ 655 and i ≈ 135 tokens.
- Selection rule: `F(1/L − 1/L′) ≥ λ(J(L) − J(L′))`, with a break-even chord λ̄ and reweighted utility `U_w = catch − w·FR`.
- Policies compared: fixed L; any-reject and majority pooling across L; a leave-one-task-out per-tool router; a label-aware oracle.
- Pre-registered direction-agnostic outcome map; paired item and task-cluster bootstraps (B = 5,000); McNemar tests.

**4. Data and evaluation.**
- τ²-style retail: 200 bad items, 31 clean gold prefixes, 17 tasks.
- AppWorld: 190 bad, 200 clean.
- L ∈ {1, 2, 3, 5, 8}.
- Verifiers: Llama-3.3-70B (primary), Qwen2.5-14B, Qwen2.5-72B; closed-weight DeepSeek-V4-Pro, Claude Opus 4.8, GPT-5.6 Sol. Executor/draft model: Qwen2.5-14B.

**5. Key results.**
- Primary retail cell, L = 1 → 8: catch 0.765 → 0.970, FR 0.419 → 0.935. J peaks at 0.602 (L = 2) and falls to 0.035 at L = 8. J(2) − J(8) = 0.567 [0.398, 0.726].
- Every one of the 6 judges peaks at L = 1 or 2 in both domains. Claude Opus 4.8 retail at L = 1: catch 0.985, FR 0.032, J 0.953.
- Retail ranking AUC decays from L = 2 to L = 8 for all judges (e.g., GPT-5.6 Sol 0.97 → 0.66). AppWorld is mixed.
- Observation replay (in-window observations supplied): retail FR at L = 8 drops to 0.290 and J(8) recovers from 0.035 to 0.490. AppWorld slope −38%. Inert token padding has no effect.
- Position blind spot: the 14B judge catches an error at position 4 of an L = 8 window at 0.237 vs. 1.000 at the end. AppWorld 14B at position 1: 0.000. Position-marginal J ≤ 0.093 at long L.
- Policies:
  - oracle headroom 0.14–0.53;
  - the per-tool router beats fixed L* in only 1 of 6 cells (+0.105);
  - majority pooling is worse (−0.118 to −0.400).
- Cost: extending retail 70B from L* = 2 to 8 saves about 246 tokens per action but forfeits 0.567 J.
- Short-only LoRA training does not generalize to long windows (L = 8 FR 0.935, J 0.040).

**6. Limitations.**
- Retail clean n = 31.
- Zero-shot monitors.
- Non-adaptive single-write injections.
- L ≤ 8.
- Closed-judge model IDs are floating.

**7. Code.** A code/data appendix and release manifest with SHA-256 digests are described, but no URL appears in the arXiv text.

**8. Overlap: medium.** It is about the granularity of monitor review, not sequential accumulation, but it sits squarely in AI control.
- It implies per-step (L = 1–2) scoring and then accumulating over steps should dominate long-window review. That supports our CUSUM-over-per-step-scores design.
- The interior-position blind spot is an attack surface for monitor-aware agents (hide the bad action mid-window).
- **Reuse:** never report catch without matched clean FR (informedness); twin construction (bad and clean prefixes differing in one action) for calibrating per-step monitors; observation provision as a requirement; cost-vs-J selection rules.
