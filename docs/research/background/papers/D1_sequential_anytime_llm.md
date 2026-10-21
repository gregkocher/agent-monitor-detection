# D1: Sequential testing, anytime-valid inference, and conformal methods applied to LLMs/agents

Reading cards from full texts (pdftotext of the arXiv PDFs in `../fulltext/`), read 2026-10-20.
Papers: 2503.17587, 2505.04608, 2512.03109, 2601.05427, 2605.07002, 2605.12947, 2605.19193, 2605.19779, 2607.02510, 2610.11843, 2610.14365.

Notation used throughout: "null" = the hypothesis whose false rejection is controlled; "alarm" = rejecting the null. In AI-control terms the natural null is "this trajectory/session/agent is benign", and the false-alarm rate is the audit cost spent on benign work.

---

## Cluster synthesis

### Practical toolbox: which method for which job

| Job in an AI-control monitor | Tool from this cluster | Guarantee | What it rests on |
|---|---|---|---|
| Turn one per-step suspicion score into a calibrated per-step p-value | Split-conformal p-value against benign-only calibration scores, `p = (1 + #{s_i >= s})/(n+1)` (ConformalGuard, Cho & Sun, WATCH) | `P(p <= a | benign) <= a` (marginal over calibration draw) | Exchangeability of benign calibration and test scores; or Cho & Sun's weaker *one-sided stochastic dominance* of a "hard" reference pool over online benign scores |
| Group-conditional/context-adaptive threshold (CFAR-like) | Mondrian conformal (separate quantile per stratum): only AgentPulse uses it, for leaderboard intervals, not detection. Weighted conformal (WATCH) reweights calibration scores by an estimated density ratio | Per-stratum coverage under within-stratum exchangeability; weighted version valid if weights are correct | Strata fixed before calibration; enough calibration points per stratum; correct density ratio |
| Per-trajectory alarm with false-alarm control over the whole trajectory (unknown length) | (a) Threshold on running max/min of score, calibrated by conformal risk control or a Hoeffding–Bentkus UCB (Schirmer et al. 2607.02510); (b) learned density-ratio statistic + PAC threshold on its running max (e-valuator 2512.03109) | P(ever alarm on benign trajectory) <= alpha (in expectation, or w.p. 1-delta over calibration) | Benign calibration trajectories i.i.d. with deployment trajectories; no assumption on within-trajectory dependence (the max is a trajectory-level statistic) |
| Accumulate weak per-step / per-response evidence, anytime-valid, unbounded horizon | Test supermartingale / e-process + Ville: product of per-observation e-values, alarm at `1/alpha`. Constructions seen here: likelihood ratio (Gauthier; Zhou et al.; Morandi; ConSol), p-to-e power calibrator `c*min(u^-eta, M)` (Cho & Sun), conformal betting `1 + eps(p - 0.5)` with composite-jumper mixture (WATCH), Bernoulli betting `1 + lambda(A - q+)` with KT plug-in lambda (Ortega-Fernandez et al.), regret increments `1 - lambda X` with mixture over lambda (Gauthier) | `P_null(sup_t E_t >= 1/alpha) <= alpha` for every stopping rule | Conditional e-value property `E[e_t | past] <= 1` under the null at every step; bets predictable. Calibration error adds an additive term (weight-exfil: `alpha + gamma`) or a multiplicative drift factor (Cho & Sun: `alpha(1+M eps)^T`) |
| Detect onset of misbehavior mid-stream (change point), ARL control | Shiryaev–Roberts sum of restarted e-processes / e-detectors (WATCH Eq. 16; Zhou et al. SR-LR(-UI)) | WATCH: `E_null[tau] >= c` (ARL); Zhou et al.: SR as weighted sum of e-processes is itself an e-process (type-I control) | Same as e-processes |
| Many simultaneous hypotheses (many agents, many deviation types) | Union-bound FWER (threshold `m/alpha`) or e-BH FDR on stopped e-values (Gauthier); BH on conformal p-values (AgentPulse) | FWER/FDR at alpha | e-BH: valid under arbitrary dependence; BH: PRDS/independence |
| Two-sided decision (stop/continue), minimal expected sample size | Wald SPRT with `A = (1-beta)/alpha`, `B = beta/(1-alpha)` (ConSol; Morandi) | Type I/II bounded by alpha/beta | i.i.d. observations from two *simple*, correctly specified hypotheses; Morandi shows AR(1) dependence inflates type-I from 0.015 to 0.065 at rho = 0.6 (nominal 0.05) |
| Fixed-budget monitor threshold for tiered actions (auto-clear / review / escalate / block) | Conformal p-value tiers (ConformalGuard) | Cumulative benign-event rate of each tier <= its alpha | Exchangeability; fails under source shift (FPR 0.021 at alpha = 0.01) |
| Auditing a system (or a monitor) for failure subgroups with an adaptive red-team | Dueling e-processes (Zhou et al. 2605.07002) | Type-I control under *arbitrary adaptive sampling* by the auditor | Scores i.i.d. conditional on input; certifying "no failure mode" additionally needs an asymptotically consistent auditor |

### Guarantees vs. assumptions (the recurring pattern)

1. **Every false-alarm guarantee in this cluster lives on the null (benign) side.** None of them depends on the attacker's behaviour; an adversary can only reduce *power*. This is a strong selling point for control: a scheming agent cannot inflate the audit rate on benign traffic. The exception is the threat explicitly flagged by ConformalGuard and the weight-exfil paper: if the adversary can influence the *benign calibration data* (calibration-pool poisoning, behaving differently during a calibration window), the guarantee breaks. For a scheming model that generates both benign and malicious trajectories, "trusted benign calibration" is the load-bearing assumption.
2. **Exchangeability is the weak point, and three papers offer different escapes:** (i) weighted conformal for modelled shifts (WATCH, needs a correct density ratio plus a "bag sufficiency" condition that v1–v4 of WATCH erroneously omitted); (ii) one-sided stochastic dominance against a deliberately conservative "hard" reference pool (Cho & Sun), with an explicit finite-horizon drift bound `alpha(1+M eps)^T`; (iii) TV-distance bounds `alpha + eps` (ConformalGuard; one shot). Weight-exfil states its null as a conditional-mean inequality `E0[A_j | G_{j-1}] <= q_m` that holds marginally over the calibrated prompt distribution and explicitly says adaptive prompt selection can violate it.
3. **Within-trajectory dependence** is handled in two ways: by testing a trajectory-level statistic (running max: Schirmer, e-valuator's PAC threshold), which needs i.i.d. trajectories but nothing within; or by conditional-validity constructions (Cho & Sun's dominance is conditional on the history; weight-exfil's null is conditional on past rounds). Plain SPRT with i.i.d. per-step likelihoods (Morandi, ConSol) has no such protection.
4. **Score granularity matters.** Zero-shot LLM judges emit 10–11 distinct values (ConformalGuard). With ties, a conformal p-value cannot fall below the tie block: in Cho & Sun, a perfect 30/30 score maps to p = 25/171 ≈ 0.146, so no single step can ever reach alpha = 0.1, and only accumulation (e-process) makes release possible. Averaging 3 stochastic LLM scorings raised GPT-4o's unique values from 33 to 105 and conformal recall from 0.285 to 0.732 at FPR ~0.005.
5. **The monitor is only as good as its signal.** Schirmer (PRM vs log-prob: power >0.9 vs ~0.5 near eps = 0.3), Morandi (judge KL ≈ 0 on MMLU → 99.5% capped), e-valuator (verifier AUC 0.59–0.70) all make this point; the statistical wrapper buys validity, not discrimination.
6. **Simple can beat fancy on delay.** Schirmer et al. find a single calibrated threshold on the raw score detects incorrect/harmful outputs *earlier* than e-valuator's density-ratio e-process, with comparable power, and e-valuator-anytime (exact Ville threshold on an *estimated* ratio) violated its FAR bound on Mistral at eps in {0.05, 0.1}.

### What has already been applied to agents / LLM safety

- **Per-trajectory online monitoring of LLM/agent outputs with false-alarm control:** e-valuator (agent tool-call trajectories + reasoning; verifier = Claude Haiku 3.5 judge or Math-Shepherd PRM; target = task failure, not misbehavior); Schirmer et al. (math correctness via PRM; harmlessness via Llama Guard on Anthropic red-teaming dialogues and FineHarm token-level). Schirmer et al. cite Greenblatt et al. "AI control" in related work but do not run a control setting.
- **Adversarial, cross-response accumulation in an AI-security setting:** Ortega-Fernandez/Kowalczyk/Warr (MATS + Anthropic), weight exfiltration through the sampler; e-process over responses, seed-blind and seed-aware attackers, capacity vs. detectability.
- **Strategic deviation detection (game-theoretic, not LLM):** Gauthier/Bach/Jordan, equilibrium and policy-compliance testing for multi-agent systems.
- **Release/stop rules in generate-verify loops:** Cho & Sun (coding agent, MBPP+), ConSol (self-consistency), Morandi (multi-agent debate).
- **Auditing LLM pipelines with adaptive sampling:** Zhou et al. (clinical-note SDoH extraction).
- **Calibrated action gating for LLM classifiers:** ConformalGuard (phishing).
- **Deployment-stream shift monitoring:** WATCH (tabular/image, not LLM; explicitly lists foundation models and agents as future work).

None of these monitors a *scheming/misaligned* agent in a control setting (e.g. BashBench/APPS backdoors/LinuxArena), uses a monitor-aware attacker optimised against the sequential statistic, or does per-context (Mondrian/CFAR) calibration of a sequential detector.

### Open space (what would be novel beyond this cluster)

1. **Sequential detectors over per-step suspicion in actual control settings**, with safety-vs-audit-budget curves rather than FPR/power on task-correctness labels. The cluster's targets are "trajectory will fail" or "output harmful"; none use attack-policy trajectories with a red team.
2. **Attacker-aware design:** the weight-exfil paper is the only one with an adaptive attacker, and its attacker is a fixed codec, not optimised against the e-process. Open: the attacker's choice between *concentrating* (one very suspicious step: beaten by max-threshold) and *diluting* (many weak steps: beaten by accumulation) suggests mixtures of a max/threshold component and an accumulation/CUSUM-SR component (weight-exfil's fixed average of K e-processes costs at most log K in log-evidence, a usable template), plus minimax analysis of what a monitor-aware attacker can achieve per unit of evidence (cf. weight-exfil's capacity-vs-detectability curves; Gauthier's `E[tau] ~ log(b)/KL`).
3. **Per-context adaptive thresholds (CFAR/Mondrian) inside a sequential test.** Schirmer et al. list per-step thresholds as future work; AgentPulse uses Mondrian only for interval coverage; WATCH's weighted conformal is the closest machinery (context = covariate, density-ratio weights). A Mondrian-conformal p-value per (task type, tool, step position) fed into a conformal test martingale / e-detector is not done here.
4. **Cross-session / fleet-level accumulation for an untrusted model.** Weight-exfil accumulates over responses of one server; Gauthier gives e-BH across many hypotheses. Not done: e-processes that accumulate across sessions of the same untrusted model with per-session restarts (SR/e-detector) and e-BH across instances or task families.
5. **Validity of benign calibration under a possibly-scheming generator.** Cho & Sun's dominance pool and drift bound, weight-exfil's "trusted window", and ConformalGuard's TV bound are the available tools; how to obtain benign calibration data that a scheming policy cannot shape (trusted-model trajectories, honeypot-verified windows, conservative "hard benign" pools) is open.
6. **Dependence-robust sequential tests on LLM-judge scores.** Morandi's AR(1) simulation quantifies type-I inflation for naive SPRT; conditional-validity constructions (betting on conformal/dominance p-values) avoid it, but nobody has compared them on agent trajectories with realistic autocorrelated suspicion scores.
7. **Coarse LLM monitor scores** (0–10 integer suspicion) limit per-step evidence; resampling the monitor (ConformalGuard's averaging) or randomized tie-breaking (WATCH, which uses randomized p-values for exact validity) interact with sequential power. Not studied in a monitoring context.

---

## Card 1 — 2503.17587 ConSol

**1. Citation / gist.** Lee, Qi, Neeley, Liu, Jeong (Baylor College of Medicine), "ConSol: Sequential Probability Ratio Testing to Find Consistent LLM Reasoning Paths Efficiently", arXiv 2503.17587 v1, 2025-03-22. Gist: replace fixed-size self-consistency voting with a Bernoulli SPRT / mixture SPRT that stops sampling once the top answer dominates the runner-up.

**2. Setup.** Each sampled final answer `Y_i ~ Categorical(p)` i.i.d. Reduced to the two most frequent answers: `p' = p_first / (p_first + p_second)`. Test `H0: p' = 0.5` vs `H1: p' > 0.5` (SPRT uses a simple alternative). Observations `X = 1` if a sample matches the current top answer, 0 if it matches the second. Assumes independent samples. Note: "first" and "second" are chosen from the data being tested, which the paper does not account for.

**3. Method.**
- SPRT likelihood ratio `Lambda_{n'} = (1.2)^{n_first} (0.8)^{n_second}` (worked example with `p1 = 0.6`); text also states `H1: p' = 0.5001`, and Section 3.3.2 lists "p1 = 5.001" (evidently a typo). Thresholds (Appendix A): reject H0 if `Lambda >= A = (1-beta)/alpha`, accept if `Lambda <= B = beta/(1-alpha)`.
- mSPRT: Beta(10^6, 10^6) prior truncated to (0.5, 1], `Lambda = Int_{0.5}^1 p'^{n_first}(1-p')^{n_second} pi(p') dp' / 0.5^{n'}`.
- Deliberately extreme type-II tolerance: `beta ≈ 1 - alpha` (SPRT beta = 0.949976; mSPRT beta = 0.94994), so the test stops early with weak evidence of "no dominant answer".
- Algorithm computes the minimal number of further samples needed in the best case and queries them concurrently. Max generations raised to 256.
- Guarantees: classical Wald error bounds only under i.i.d. and correctly specified simple hypotheses; no anytime-valid argument beyond SPRT. Baseline "sequential p-value" (binomial test at 0.05 after each sample) is used to illustrate peeking inflation.

**4. Domain/data.** AIME24 (o3-mini low/medium/high), GPQA Diamond (o3-mini-low), GSM8K (gpt-4o-mini). No labels needed for stopping; accuracy uses benchmark answers. "Consistency score" measured in simulation using categorical distributions estimated from 40 samples.

**5. Results (Table 1).** Accuracy: AIME24 o3-mini-low Self-Cons@40 70.0% vs SPRT 80.0% / mSPRT 76.7%; o3-mini-medium 90.0 vs 90.0/90.0; high 96.7 all; GPQA 68.2 vs 66.7/70.2; GSM 94.2 vs 93.5/93.9. Token reduction vs Self-Cons@40: SPRT 63.9% (AIME low), 84.8% (medium), 84.5% (high), 86.2% (GPQA), 88.6% (GSM); mSPRT 57.3/76.8/82.2/83.6/88.7%. Adaptive-Consistency 47.9–82.8%; p-value baseline 49.3–79.2%.

**6. Limitations.** Parameter sensitivity acknowledged; short-answer tasks only. Statistically, the alternative is data-selected, beta ≈ 0.95 removes any meaningful type-II control, and the AIME gains rest on 30 problems. No adversarial or shift considerations.

**7. Code.** https://github.com/LiuzLab/consol ; `pip install consol`.

**8. Transfer to AI control.** Low overlap. Useful only as an example of SPRT on LLM outputs and of the "peeking inflates type-I" baseline. Nothing about monitoring, adversaries, or calibration.

---

## Card 2 — 2505.04608 WATCH (weighted-conformal test martingales)

**1. Citation / gist.** Prinster, Han, Liu, Saria (JHU), "WATCH: Adaptive Monitoring for AI Deployments via Weighted-Conformal Martingales", ICML 2025 (PMLR 267); arXiv v6, 2026-09-11. Gist: generalise conformal test martingales (CTMs) to weighted-conformal p-values so a deployment monitor can adapt to benign covariate shift while still alarming on concept shift or extreme covariate shift, and diagnose which occurred.

**2. Setup.** Stream of labelled deployment points `Z_t = (X_t, Y_t)` after calibration set `Z_{1:n}`, pre-trained predictor `mu`, nonconformity score `S(x,y)` (e.g. `|y - mu(x)|`). Standard CTM null: exchangeability `H0^ex`. WATCH null (Eq. 14) `H0^(cs)`: `(X_i,Y_i) iid F_{Y|X} x F_X` before adaptation time `t_ad`, and `iid F_{Y|X} x G_X^(w)` after, where `w(x)` is the learned density ratio — i.e. "Y|X invariant AND the density-ratio estimate is correct". General `H0(f)`: any assumption set sufficient for the computed weights to equal oracle weights, conjoined with **bag sufficiency** (Def. 3.2: `Z_t ⟂ (Z_1..Z_{t-1}) | bag of past values`). Remark 3.5: v1–v4 stated Theorem 3.3 without bag sufficiency, which was false (counterexample Prop. B.3); experiments unaffected because it holds under `H0^(cs)`.

**3. Method.**
- Randomised conformal p-value: `p_{n+1} = (#{v_i > v_{n+1}} + u #{v_i = v_{n+1}})/(n+1)`, `u ~ U[0,1]`.
- Weighted p-value (Eq. 9): `p^w = Sum_i w_i [1{v_i > v_{n+1}} + u 1{v_i = v_{n+1}}]`, weights sum to 1; oracle weights `w_i^o = P{Z_{n+1} = z_i | bag}`. Under covariate shift `w_i ∝ w_hat(X_i)` (Eq. 18), with calibration set frozen after `t_ad`.
- Theorem 3.3: under `H0(f)` (incl. bag sufficiency) the online weighted p-values are i.i.d. U[0,1].
- Martingale: betting function `h_eps(p) = 1 + eps(p - 0.5)`, `eps in {-1, 0, 1}`, mixture over betting sequences via Vovk's "composite jumper" Markov chain (Eq. 7). Prop 3.6 (Ville): `P(∃t: M_t/M_0 >= c) <= 1/c`.
- Scheduled monitoring: Shiryaev–Roberts on the WCTM, `tau_k = min{t > tau_{k-1}: Sum_{i=tau_{k-1}}^{t-1} M_t/M_i >= c}`; Prop 3.7: `E[tau_1] >= c` (ARL control).
- Practical WATCH: weights from an online probabilistic classifier (MLP or logistic) distinguishing source vs target; a secondary X-only CTM (nearest-neighbour score) triggers the start of adaptation when it crosses an adaptation threshold; root cause: both alarm → extreme covariate shift; only WCTM alarms → concept shift.
- Complexity O(t) vs O(t^2) for Podkopaev–Ramdas changepoint detection.

**4. Domain/data.** Tabular regression (MEPS, Bike Sharing, Superconduct; 1/3 train, 1/3 calibration; shift by exponential-tilting bias sampling, lambda = 5; changepoint after 500th test point of 3000), image classification (MNIST-C, CIFAR-10-C with brightness/other corruptions at levels 1/3/5 mixed with clean samples). Labels assumed available online (monitoring needs Y). Not LLMs.

**5. Results.** Table 1 average detection delay (200 seeds), weighted vs standard CP: anytime-valid WCTM/CTM 115.8 / 114.8 (MEPS), 190.0 / 192.4 (Bike), 173.2 / 169.7 (Superconduct) vs Podkopaev–Ramdas sequential test 475–813; SR-WCTM 102.1 / 101.8, 155.6 / 157.4, 142.8 / 142.3 vs PR-CD-online 111.0–192.9 and PR-CD-50 194.5–289.1. Anytime-valid comparison at false-alarm 0.01; SR at ARL 20,000. Qualitatively: under benign MEPS shift the standard CTM alarms, WCTM does not; on CIFAR-10-C, WCTM avoids alarms for level-1 (>50% clean) and level-3 (40% clean) but alarms at level-5 (30% clean).

**6. Limitations.** Needs labels to compute nonconformity; validity requires correct density-ratio weights (robustness to approximate weights listed as future work) and bag sufficiency; X-CTM adaptation threshold is heuristic. Nothing on adversarial data: a strategic agent that shifts covariates in ways the density-ratio model treats as "benign" would be adapted to rather than detected (the method is designed to *absorb* covariate shift).

**7. Code.** https://github.com/aaronhan223/watch

**8. Transfer.** Medium. The weighted-conformal p-value is the right primitive for *context-adaptive* calibration (CFAR-like: reweight benign calibration scores toward the current task/context distribution), and CTM/SR give anytime-valid or ARL-controlled stream monitors. In control, "Y" could be a trusted label (audit outcome) or the score itself monitored for change. Overlap with our ideas: medium (shift-adaptive calibration, SR change detection). Novel beyond it: per-trajectory/per-agent misbehavior detection (WATCH monitors population drift, not individual episodes), adversarial agents exploiting the adaptation mechanism, label-free variants using only suspicion scores, Mondrian rather than density-ratio weighting.

---

## Card 3 — 2512.03109 E-valuator

**1. Citation / gist.** Sadhuka, Prinster, Fannjiang, Scalia, Berger, Regev, Wang (Genentech/MIT/JHU/Stanford), "E-valuator: Reliable Agent Verifiers with Sequential Hypothesis Testing", arXiv v2 2026-05-28. Gist: wrap any black-box per-step verifier score into a sequential test that flags trajectories that will end unsuccessfully, with high-probability control of the false-alarm rate (flagging a successful trajectory at any step).

**2. Setup.** Trajectory `H_t = (o_0, a_1, o_1, ..., a_t, o_t)`, verifier score `S_t = v(H_t)`, random length T, final label Y (1 = correct). `P1, P0` = distributions of score sequences given Y = 1/0. Test `H_N: S ~ P1` (successful) vs `H_A: S ~ P0`. FAR control (Eq. 1): `Pr_{H_N}[∃t in [T]: M_t > c_alpha] <= alpha`. No independence across steps assumed; trajectories in calibration assumed i.i.d. from the null.

**3. Method.**
- Statistic: density ratio `M_t = p0(S_{1:t}) / p1(S_{1:t})` — a test martingale under H_N and log-optimal (Prop. 2: maximises `E_{H_A}[log M_tau]` among e-processes). Estimated by Bayes' rule with a per-step classifier: `M_hat_t = (1 - g_t(S_{1:t}))/g_t(S_{1:t}) * pi_hat_1/(1 - pi_hat_1)`; `g_t` = scikit-learn logistic regression (default), one per step t.
- Because `M_hat` is not an exact e-process, the threshold is set by **PAC thresholding** (Alg. 1) on the running max over successful calibration trajectories: `M^(i) = max_t M_t^(i)`, sort, `k* = min{k: Pr[Bin(n, 1-alpha) >= k] <= delta}`, `c_alpha = M_(k*)`; if `(1-alpha)^n > delta` return infinity. Prop 1: `Pr_D( Pr_{H_N}(∃t: M_t > c_alpha | D) <= alpha ) >= 1 - delta`; marginally `<= alpha + delta`; need `n >= log(delta)/log(1-alpha)`. Valid for *any* scoring process `f_t(S_{1:t})`.
- Calibration split 50/50 into density-ratio and threshold sets; experiments use 20% of data for calibration, `alpha' = 0.9 alpha`, `delta = 0.1 alpha`.
- Baselines: raw verifier (reject when `S_t < alpha`), isotonic-calibrated verifier, PAC verifier (`f_t = 1 - S_t` + Alg. 1), randomized Ville (threshold `1/alpha`, final step `Z/alpha`).
- Appendix toy example: a marginally calibrated verifier does not control FAR.

**4. Domain/data.** Agents: Aviary and OctoTools tool-calling agents (verifier = Claude Haiku 3.5 asked after each tool call for a text probability of success), Claude Sonnet 4 step-by-step reasoning (verifier = Math-Shepherd PRM). Datasets: GSM8K, MATH, AIME, HotpotQA, MedQA, MMLU-Pro. Labels = final-answer correctness. Verifier quality (Table 2, AUC / ECE): MedQA 0.700/0.021, MATH 0.692/0.184, HotpotQA 0.654/0.137, AIME 0.624/0.083, GSM8K 0.602/0.053, MMLU-Pro 0.592/0.086.

**5. Results.** E-valuator controlled FAR at every alpha on all datasets (50 random splits, 95% CI). HotpotQA at alpha = 0.4: e-valuator power 0.78 at FAR 0.31; raw verifier power 0.84 at FAR 0.60; randomized Ville 0.84 at FAR 0.41; PAC verifier 0.36 at FAR 0.12. MATH at alpha = 0.3: average run length under H_A 5.5 steps vs >= 6.8 for all baselines. Token efficiency: MATH 49% accuracy (86% of the original 57%) using 84% of 381,804 tokens; other verifiers need >98% of tokens for comparable accuracy; MMLU-Pro 53% accuracy with 282,316 tokens vs >300,000. Calibration-size ablation on MATH (5000 trajectories): FAR controlled at all sizes; 100 labelled trajectories (2%) noisier. Logistic vs SVM density-ratio estimators similar. HotpotQA alpha = 0.4: 3.2 vs 4.3 steps (PAC verifier).

**6. Limitations.** Per-step classifiers over the full prefix `S_{1:t}` need enough calibration trajectories at each length; the guarantee is about task failure, not misbehavior; requires labelled unsuccessful trajectories to learn `p0` (for control: attack trajectories from a red team, so power is tied to the red team's attack distribution). Validity requires i.i.d. null trajectories (no shift between calibration and deployment). Schirmer et al. (2607.02510) found e-valuator-anytime (Ville threshold on the estimated ratio) violates FAR on Mistral at eps in {0.05, 0.1}, and that e-valuators detect later than a single calibrated threshold. No adversarial analysis; "early detection of unsafe or harmful trajectories" is listed as future work.

**7. Code.** https://github.com/shuvom-s/e-valuator ; PyPI `e-valuator`.

**8. Transfer.** High. This is the closest existing per-trajectory sequential detector over per-step monitor scores with a trajectory-level false-alarm guarantee: substitute "benign trajectory" for "successful" and "attack" for "unsuccessful". The PAC-on-running-max trick gives FAR control for *any* hand-designed statistic (CUSUM, SR, learned ratio), which we can reuse directly. Novel beyond it: monitor-aware attackers that shape `S_{1:t}` to keep `M_hat` low; per-context thresholds; cross-session accumulation; robustness when `p0` is learned from one attack family and tested on another; comparison against max-threshold baselines on control metrics.

---

## Card 4 — 2601.05427 Anytime detection of strategic deviations in multi-agent systems

**1. Citation / gist.** Gauthier, Bach, Jordan (Inria/ENS; Berkeley), "Anytime Detection of Strategic Deviations in Multi-Agent Systems", ICML 2026 (PMLR 306), arXiv v3 2026-05-22. Gist: e-process tests that repeated play is consistent with (Nash/correlated/coarse-correlated) equilibrium, with FWER and e-BH FDR control, and likelihood-ratio compliance tests against a target policy in stochastic games.

**2. Setup.** Repeated finite normal-form game, joint action profile i.i.d. per round from unknown joint strategy pi. `H0: ∀i, a'_i: E[u_i(a_i,a_-i)] >= E[u_i(a'_i, a_-i)]` (Nash); `H1: ∃ i, a'_i` with gap `>= eta > 0` (eta-approximate; App. E shows eta > 0 is necessary). Payoffs in [0,1]; requires observing counterfactual payoffs `u_i(a'_i, a_-i)` but not pi. Stochastic games: compliance test `H0`: player i follows `pi_i(.|s)` vs alternative `pi^(1)`.

**3. Method.**
- Regret increment `X_t^{(i,a')} = u_i(a_{i,t}, a_{-i,t}) - u_i(a'_i, a_{-i,t})`; per-round e-value `E_t = 1 - lambda X_t`, lambda in (0,1] (Lemma 2.2); product is a nonnegative supermartingale (Lemma 2.3). Kelly-optimal worst-case `lambda* = eta` (Prop 2.4). Mixture over lambda: `M_t(nu) = Int Prod_s (1 - lambda X_s) d nu(lambda)` (Cor 2.5).
- FWER: alarm when any `M >= Sum_i |A_i| / alpha` (Thm 2.6, union bound + Ville).
- Detection time with uniform nu: `E_{H1}[tau] <= 12(log b + log(4/eta) + log(3/2))/eta^2` (Thm 2.7), i.e. `O(log(Sum|A_i|/alpha))` for fixed eta.
- FDR: e-BH on all e-processes stopped at the first time e-BH rejects anything (Alg. 2, Thm 2.8); with uniform weights, FDR stopping time <= FWER stopping time a.s. (Prop 2.9).
- Stochastic games: per-round likelihood ratio `E_{i,t} = pi^(1)_i(a_{i,t}|s_t) / pi_i(a_{i,t}|s_t)`, martingale (Lemma 3.2), FWER threshold `n/alpha` (Thm 3.3); `E[tau_i] <= (log b + C_i)/KL_bar_i(mu)` with stationary-weighted KL and overshoot constant `C_i` (Thm 3.4); mixture over a prior on alternatives (Remark 3.5) keeps the scaling.
- App. G: likelihood-ratio variant when pi is known but payoffs are not.

**4. Domain/data.** Synthetic: 2x2 game with weak balanced deviations (eta ≈ 0.033), alpha = 0.2, lambda = 0.05, 300 runs x 4000 rounds; population Rock-Paper-Scissors with 20 players (m = 60 hypotheses, 5 players biased to Rock (0.6, 0.2, 0.2)), 200 trials x 3000 rounds; 5x4 grid soccer; 10x10 predator–prey with unknown mixture weight epsilon. No LLMs.

**5. Results.** 2x2: mean stopping time FWER 1765 vs FDR 1546 (FDR speedup 1.15x; FDR never later in any run); under H0 empirical FWER 0.01 (3/300 runs) vs nominal 0.2. RPS (m = 60): mean stopping FWER 2025, FDR 1248, split-FWER 1438, split-FDR 802 (screening window T0 = 50, keep K = 10). Stochastic games: empirical detection time follows `O(1/eps^2)` in both the known-eps grid-soccer and unknown-eps predator–prey (mixture) experiments.

**6. Limitations.** i.i.d. play across rounds (stationary strategies); needs counterfactual payoffs (normal-form) or known target policy likelihoods (stochastic); analysis of stationary deviations only, response of learning agents to detection is future work. No adaptive adversary that knows the test (a deviator could keep regret just below eta).

**7. Code.** https://github.com/GauthierE/anytime-detection-deviation

**8. Transfer.** Medium. Two reusable pieces: (i) *policy compliance testing* via likelihood ratios of the untrusted agent's actions under a reference policy (e.g. trusted model's action distribution) vs a deviation mixture — requires action likelihoods we may have for open models; (ii) e-BH across many simultaneous e-processes (many agents/instances/deviation types) with a single global stopping time, plus the screen-then-test split. Novel beyond it: LLM agents with non-stationary, history-dependent behavior; strategic deviators that know the test; per-step suspicion scores instead of payoffs/likelihoods.

---

## Card 5 — 2605.07002 Adaptive auditing with anytime-valid guarantees

**1. Citation / gist.** Zhou, Vossler, Sivaraman, Mai, Feng (UCSF; Stanford), "Adaptive auditing of AI systems with anytime-valid guarantees", arXiv 2605.07002 v1, 2026-05-07. Gist: formalise adaptive red-teaming/auditing as two "dueling" hypothesis tests run as simultaneous e-processes that stay valid under arbitrary adaptive sampling and stopping.

**2. Setup.** Inputs X with measure mu, score Y (e.g. correctness) i.i.d. conditional on X; subgroup performance `V(S) = E[Y | X in S]`; failure mode = subgroup with `mu(S) >= eps` and `V(S) < q`. Model's null `H0^mod: ∀S in S_eps, V(S) >= q`. Auditor's null with budget m `H0^aud,[m]: ∃tau in [m], ∀t >= tau: V(S_t^pi) < q` (the auditor's strategy keeps finding failures). Theorem 1: with an asymptotically consistent auditor the two hypotheses are asymptotic complements. Theorem 2: no anytime-valid test of the auditor's null has power > alpha before time m, so that test starts at m with simplified null `H0^aud,m: ∀t >= m, V(S_t) < q`.

**3. Method.**
- Model's null: LR e-process `E^LR_{j:t} = Prod_{k=j}^t p(Y_k; q - delta)/p(Y_k; q)` (Bernoulli); LR-UI with predictable plug-in `gamma_hat_{k-1}` (EWAF forecaster) in the numerator; SR variants `E^SR_t = Sum_{j<=t} w_j E_{j:t}` with weights summing to one (hedges an unknown learning delay of the auditor).
- Auditor's null: `Prod_{k=m}^t p(Y_k; q + delta')/p(Y_k; q)` for t >= m (or UI plug-in).
- Dual procedure: stop when either exceeds `1/alpha`; since at most one null is true, FWER = alpha without Bonferroni (Thm 3).
- Validity holds for any adaptive auditor because each Y given the past has mean >= q under the model's null whatever subgroup is chosen.

**4. Domain/data.** (1) Semi-synthetic GPQA strata (3 domains x 3 education levels) with simulated failure in Chemistry at higher levels (None/Small/Medium/Large), budget 250, m = 40 (ablations m = 10, 70), 100 trials; two settings: select from unlabelled pool, or generate test cases with an LLM. (2) Real LLM pipeline extracting 28 social-determinants-of-health categories from 81 clinical notes (2268 comparisons; overall LLM–human agreement 88%, category accuracy 58%–100%), q = 0.83, max 400, n_init = 20, 40 replicates. (3) CUB-200-2011 (appendix). Adaptive auditor: NN ensemble on sentence-transformer embeddings + UCB exploration.

**5. Results.** SR-LR-UI had the highest power among adaptive procedures; UI > fixed-probability; Oracle auditor rejects in 15–25 observations; pre-specified (stratified/pre-learned) auditors had low power and often "passed" the audit. On the SDoH pipeline the adaptive auditor's sampling frequency correlated with category accuracy at Spearman rho = -0.84. Power and stopping times are reported only in figures (no tables of exact power).

**6. Limitations.** Binary scores; requires i.i.d. Y given X (the audited system is not adversarial towards the auditor); certification needs a consistent auditor; human-in-the-loop auditors not studied.

**7. Code.** https://www.github.com/jjfenglab/safe-active-testing

**8. Transfer.** Medium, for *evaluating monitors* rather than running them: e.g. an adaptive red team searching for attack strategies on which a monitor's catch rate falls below q, with anytime-valid conclusions from tens of expensive episodes; the dueling-nulls framing cleanly separates "monitor has a hole" from "this red team failed to find one". Novel beyond it: applying this to control evaluations where the audited monitor faces a learning attacker (non-i.i.d. Y), and to subgroup-conditional catch-rate certification.

---

## Card 6 — 2605.12947 Always-valid release for generate–verify workflows

**1. Citation / gist.** Cho, Sun (Purdue), "When Should an AI Workflow Release? Always-Valid Inference for Black-Box Generate-Verify Systems", arXiv v1 2026-05-13. Gist: calibrate each adaptive verifier score against a pool of high-scoring failures (hard negatives) to get conditionally valid p-values without exchangeability, then accumulate them with an e-process to decide when to release.

**2. Setup.** Per task x: candidates `C_t`, verifier scores `S_t`, history filtration `G_t`; latent feasibility F (1 = pipeline can solve the task). Null = infeasible (F = 0); "release" = rejection. Target `P(D = 1 | F = 0) <= alpha`, `D = 1{tau <= T_max}`. Prop 1 bounds the release-conditional failure rate `R_out` via `pi_0`, alpha and feasible-side quantities. Prop 2 (naive stopping fails): if per-step `P(p_t <= alpha | G_{t-1}, F = 0) >= c_t`, then `P(tau_naive <= T | F = 0) >= 1 - exp(-Sum c_t)`. Explicitly: neither likelihood models nor exchangeability are available because scores are history-dependent.

**3. Method.**
- Offline pool R: generate candidates on a calibration set, keep those a stronger adjudicator judges incorrect, retain the upper `100q%` of their verifier scores (`Gamma_q`; main choice top55). Diagnostic: empirical CDF of held-out incorrect p-values must lie on/below the diagonal.
- **Assumption 1 (failure-side calibration dominance):** `P(S_t >= s | G~_{t-1}, F = 0) <= P(S~ >= s | sigma(R))` for all t, s, where `S~` is a draw from the empirical pool.
- p-value `p_t = (1 + Sum_i 1{R_i >= S_t})/(n+1)`; Thm 1: `P(p_t <= u | G~_{t-1}, F = 0) <= u` (conditionally super-uniform).
- p-to-e: `E_t = Prod_s f_s(p_s)` with predictable non-increasing `f`, `Int_0^1 f <= 1` (Prop 3: e-process). Implementation: truncated power calibrator `f^(eta,M)(u) = c * min(u^{-eta}, M)`; eta = 0.7 main. Release when `E_t >= 1/alpha` (Prop 4: `P(D=1|F=0) <= alpha`).
- Power: Prop 5 `P(D_T=1|F=1) <= P(D_T=1|F=0) + TV(P1^T, P0^T)`; with calibrated log-gain `Z_t = log f(p_t) - log f(1)` and Assumption 2 (`Sum E[Y_t Z_t | ., F=1] >= B_T`), Thm 2: `P(tau <= T | F=1) >= 1 - exp(-2 Delta^2/(T Z_max^2))`, `Delta = B_T - (log(1/alpha) - T log f(1))`.
- Calibration drift, Thm 3: if `TV(Q_{t,0}, P0) <= eps` each step and `e_t in [0, M]`, then `P(tau <= T | R, F = 0) <= alpha(1 + M eps)^T`.

**4. Domain/data.** MBPP+ with Qwen2.5-Coder-7B-Instruct (T = 0.7, top_p 0.95, 240 max new tokens), 10 sequential candidates per task; tasks with >= 100 usable tests, split 30 visible (verifier = visible pass rate) / 70 hidden (correctness oracle). Task splits: bank (pool), select (pool diagnosis), final (reporting). Empirical F0 = tasks with no hidden-correct candidate in 10 steps (n = 30), F1 otherwise (n = 148). Top55 pool = 170 hard negatives, 24 of which have perfect visible score.

**5. Results (Table 1, N_test = 30).** Ours alpha = 0.20: false release 0.0333 on F0, F1 release 0.8041, failure|release 0.0000, mean step 4.30; alpha = 0.10: 0.0000, 0.7703, 0.0000, 6.27; alpha = 0.05: 0.0000, 0.7432, 0.0091, 7.22. First_p (one-step threshold on same p-values): alpha = 0.20 false release 0.0667, F1 release 0.9932; alpha <= 0.10 never releases (perfect score maps to p ≈ 0.146). Entropy baseline false release 0.7667; Stability 0.2333. Trajectory examples: persistent deceptive score 0.967 → p = 0.216, wealth 5.469 after 10 steps (< threshold 10, no release); correct solution at p = 0.146 each step → wealth 13.617 at t = 7 (release). Betting exponent sweep: eta = 0.9 gives nonzero false release at alpha = 0.10; eta = 0.3 inactive at alpha <= 0.10.

**6. Limitations.** Dominance is untestable in general (only a held-out CDF diagnostic); pool selection is a tuning choice; F0 has only 30 tasks so false-release estimates are coarse; drift bound grows exponentially in T; a single small model and benchmark. An adversarial generator that produces higher-scoring failures than the pool violates Assumption 1 directly.

**7. Code.** No repository link found in the paper.

**8. Transfer.** High (methodologically). Flip roles: null = benign agent behavior, pool = "hard benign" steps (highest-suspicion benign actions from trusted calibration), p-value = how extreme the current suspicion is relative to hard benign, e-process accumulates within a trajectory or across sessions. The dominance assumption is exactly the kind of conservative, history-conditional calibration needed when per-step scores are non-exchangeable, and the drift theorem gives an explicit budget for calibration mismatch. Their observation that tied, coarse scores cap per-step evidence (p ≈ 0.146) and only accumulation crosses the threshold maps directly onto 0–10 LLM suspicion scores. Novel beyond it: per-context (Mondrian) pools, attackers that try to stay inside the pool's tail, and cross-session accumulation.

---

## Card 7 — 2605.19193 Sequential consensus for multi-agent LLM debates

**1. Citation / gist.** Morandi (Cisco), "Sequential Consensus for Multi-Agent LLM Debates: A Wald-SPRT compute governor with calibration-based failure detection", arXiv v1 2026-05-18. Gist: Wald SPRT on per-round LLM-judge consensus scores with Beta likelihoods decides when to stop a debate; the calibration KL doubles as a diagnostic for whether the judge signal is informative.

**2. Setup.** K agents debate; after round r a judge emits `s_r in [0,1]`. `H0`: not (usefully) converged, `H1`: converged. Scores assumed conditionally i.i.d. given the hypothesis, `s_r ~ f0` or `f1`.

**3. Method.** `f_k = Beta(a_k, b_k)` fit by method of moments on calibration debates; per-round LLR `log B(a0,b0)/B(a1,b1) + (a1-a0) log s + (b1-b0) log(1-s)`; `Lambda_R = Sum` LLR; stop at `A = log((1-beta)/alpha)` (accept H1) or `B = log(beta/(1-alpha))` (accept H0), else continue to hard cap `R_max` (default 8). alpha = beta = 0.05 → A = 2.94. Wald guarantees under i.i.d.; asymptotic `E[R|H1] ≈ [(1-beta)A + beta B]/D(f1||f0)`. Real-LLM calibration is correctness-conditioned (f0 from debates whose capped aggregate is wrong).

**4. Domain/data.** Monte-Carlo with "planning-target" Beta pairs (reverse-engineered, not fitted): MMLU Beta(3.5,6.0)/Beta(6.0,3.0), GSM8K Beta(3.5,5.5)/Beta(4.5,2.0), JudgeBench Beta(2.0,5.0)/Beta(4.0,2.5); N = 50,000 trajectories per hypothesis. Real: 200 MMLU + 200 GSM8K items, agents gpt-5, claude-opus-4-6, gemini-2.5-pro; judge claude-opus-4-6; n = 40 disjoint calibration items per task.

**5. Results.** Simulation (Table I): avg rounds 2.38 / 2.61 / 2.49 vs fixed-5, classification accuracy 98.3 / 98.1 / 98.2%. Non-i.i.d. AR(1) (Gaussian copula) at nominal 0.05: rho = 0 → (alpha_hat, beta_hat) = (0.015, 0.017); 0.2 → (0.026, 0.029); 0.41 → (0.044, 0.048); 0.6 → (0.065, 0.072); rounds 2.38 → 2.69. Difficulty tertiles: KL 3.80/1.99/0.70 → rounds 1.54/2.38/4.68, cap rate 0/0.4/14.2%. Real (Table III): GSM8K SPRT 97.0% accuracy, 1.01 rounds, 4.06 calls vs fixed-5 99.0%, 15 calls; fitted f0 = Beta(13.21, 21.25), f1 = Beta(0.55, 0.10), KL(f1||f0) = 9.80. MMLU: f0 = Beta(2.65,0.14), f1 = Beta(1.26,0.10), KL ≈ 0 → capped on 99.5% of items, 31.96 calls, 94.2% vs 93.8% (fixed-5) and 94.4% (single-round vote). No pairwise accuracy difference is significant (±4.4pp CI).

**6. Limitations.** Author lists: i.i.d. violation; adversarial debates ("a worst-case agent could game the rule by producing high-consensus-looking but incorrect answers ... not stress-tested"); static likelihoods; judge–agent overlap; Goodhart risk if agents are optimised for judge scores. Beyond that: simulation headline numbers come from hand-chosen Beta parameters, so they validate the SPRT arithmetic, not the LLM setting.

**7. Code.** Paper says the harness, JSONL logs and calibration artifacts are shipped, but gives no URL.

**8. Transfer.** Low–medium. A clean, cheap baseline for "SPRT on per-step LLM-judge scores with Beta likelihoods", and the AR(1) table is a useful quantitative warning about type-I inflation from autocorrelated scores — relevant to any SPRT/CUSUM on monitor suspicion. The "calibration KL as go/no-go diagnostic" idea transfers directly (estimate KL between benign and attack suspicion-score distributions per context before deploying a sequential test).

---

## Card 8 — 2605.19779 AgentPulse: conformal UQ for continuous agent evaluation

**1. Citation / gist.** Gao, Wang, Yu (OpenMesh; UPenn; Columbia), "Distribution-Free Uncertainty Quantification for Continuous AI Agent Evaluation", ICML 2026 AgenticUQ workshop poster, arXiv v1 2026-05-19. Gist: split conformal, ACI and Mondrian conformal intervals for hourly forecasts of a composite "agent quality" score built from benchmarks, adoption, sentiment and ecosystem signals, plus conformal abstention for leaderboard rankings.

**2. Setup.** Composite `AP(a) = 0.35 B + 0.25 A + 0.20 S + 0.20 E` for 50 agents, hourly, 19 sources (abstract says 18 signals). Mean-reversion forecast `AP_hat_{t+h} = AP_t + lambda (AP_bar - AP_t) h`, lambda = 0.003. Coverage target for `AP_{t+h}`.

**3. Method.** Split conformal: 70/30 train/calibration of each agent's history, residual `|AP - AP_hat|`, quantile at level `ceil((1-alpha)(n+1))/n`. ACI: `alpha_{t+1} = alpha_t + gamma(alpha - err_t)`. Mondrian: separate quantiles for "stable" (sigma_cross < 0.04, n = 35) vs "volatile" (>= 0.04, n = 15) agents, where sigma_cross is the cross-source sentiment std. Pairwise abstention when 0 is in the conformal interval for the score difference; BH at q = 0.20 over 1,225 pairs. Pipeline bounds `sqrt(s1^2 + s2^2)` vs `s1 + s2`.

**4. Domain/data.** Public signals about 50 coding/AI agents (GitHub stars, downloads, social sentiment via VADER/TextBlob/FinBERT/DistilBERT, benchmark scores). No misbehavior labels.

**5. Results.** Calibration error < 0.02 at 24h. Table 1 (alpha = 0.2) conformal coverage 82/83/81/80/79% at 1/6/24/48/72h, widths 0.016–0.195; parametric 94–78%. Bootstrap 84% (24h), 74% (72h). ACI widens 35% after an agent release, reconverges over 48h; 8% wider than split conformal in stable periods. Per-agent coverage mean 80.4%, 90% of agents in [72%, 90%]. Mondrian lifts volatile-group coverage from 64.6% (11/15 below 75%) to 80.4% (2/15 below 75%), with 22% wider intervals. Abstention: 847/1,225 pairs ranked at alpha = 0.2; 612 after BH. sigma_cross predicts ranking instability r = 0.64.

**6. Limitations.** Treats an hourly autocorrelated time series with a chronological split as if exchangeable while claiming "exact finite-sample guarantees"; Mondrian strata are defined from the same data's volatility; per-pair false-ranking claim relies on exchangeability of difference residuals. No adversarial component. Anytime-valid e-processes are listed as future work.

**7. Code.** States "Code and data are released under CC BY 4.0"; no URL in the paper.

**8. Transfer.** Low. Only relevant as a worked example of Mondrian stratification fixing group-conditional under-coverage (64.6% → 80.4%) and ACI reacting to a release-driven regime change. Our per-context CFAR idea would use the same Mondrian mechanism, but for benign-score quantiles inside a detector.

---

## Card 9 — 2607.02510 Online safety monitoring for LLMs

**1. Citation / gist.** Schirmer, Jazbec, Timans, Naesseth, Waldron, Nalisnick (UvA; UW-Madison; JHU), "Online Safety Monitoring for LLMs", ICML 2026 Workshop on Hypothesis Testing, arXiv v1 2026-07-02. Gist: a single time-invariant threshold on a streaming verifier signal, calibrated by conformal risk control (in expectation) or a Hoeffding–Bentkus UCB (high probability), is competitive with e-valuator and alarms earlier.

**Verification of the "per-context calibration" claim:** the full text does **not** do per-context calibration. The monitor uses "a single, time-invariant threshold lambda applied uniformly across all signals s_t" (Sec. 3.2), calibrated on one pooled calibration set. The only related statements are in the Limitations: the method "ignores temporal structure", and future work "may (iv) calibrate a per-step threshold using more advanced procedures such as Pareto testing". No context, prompt-type, or group-conditional thresholds appear anywhere.

**2. Setup.** Prompt x, output sequence `o_{1:T}` (tokens, reasoning steps, or conversation turns), safety label y (1 = safe). Signal `s_t` = verifier probability of safety given `o_{1:t}`. Monitor `Phi_t = 1{∃k <= t: s_k < lambda}` (alarm = first step below threshold, i.e. a threshold on the running min). False-alarm risk `R_I(lambda) = P(∃t: s_t < lambda | y = 1)`; missed-detection risk `R_II(lambda) = P(∀t: s_t >= lambda | y = 0)` (App. B). Calibration set `D_cal` of n labelled sequences exchangeable with deployment.

**3. Method.**
- CRC (in expectation, Eq. 4): `lambda_hat = max{lambda: n/(n+1) R_hat_I(lambda; D_cal) + 1/(n+1) <= eps}` → `E_D[R_I(lambda_hat)] <= eps`.
- UCB (high probability, Eq. 6): `lambda_hat = max{lambda: U(lambda, n, delta) <= eps}` with Hoeffding–Bentkus UCB → `P_D(R_I(lambda_hat) <= eps) >= 1 - delta`.
- Missed-detection control: same with the smallest valid lambda on unsafe calibration samples (n0) — the paper notes no prior LLM monitor (including e-valuator) gives a missed-detection guarantee.
- Baselines: e-valuator-anytime (Ville threshold on estimated ratio) and e-valuator-PAC (App. C summarises).
- Metrics: false-alarm rate, power, detection delay = mean fraction of sequence before a correct alarm.

**4. Domain/data.** Factuality: MATH step-by-step solutions from Claude Haiku 4.5 (90% correct) and Mistral-7B-Instruct-v0.3 (26% correct); labels via o3-mini comparison with ground truth; signal = Qwen2.5-Math-PRM-7B per-step probability. Harmlessness: Anthropic Red Teaming multi-turn dialogues (signal = Llama Guard probability of "safe" on the conversation prefix; label = attack success rating) and FineHarm (signal = SCM verifier, Qwen2.5-1.5B fine-tuned for token-level harmfulness). Cost ablation: per-step minimum token log-probability of the generator. 10 runs; eps swept {0.05, 0.1, 0.2, 0.3, 0.4, 0.5}.

**5. Results.** UCB, e-valuator-PAC controlled FAR; e-valuator-anytime violated its bound at eps in {0.05, 0.1} on Mistral; CRC met its in-expectation guarantee. On MATH, CRC/UCB flag incorrect sequences after about half the sequence, earlier than e-valuators; e-valuator-anytime had highest power at small eps (with violation); e-valuator-PAC ≈ UCB; CRC > UCB in power. Red Teaming: e-valuator-PAC had highest power; Llama Guard power stays below 0.8; FineHarm: CRC/UCB highest power, near 1. Log-prob signal: near eps = 0.3, PRM monitors exceed 0.9 power vs about 0.5 for log-prob. Most numbers are figure-only.

**6. Limitations.** Authors: monitor only as good as its signal (informativeness, cost, adversarial robustness); ignores temporal structure. Also: guarantee needs exchangeable labelled calibration sequences; no attacker; calibration set sizes not stated in the main text.

**7. Code.** https://github.com/monasch/llm-monitor

**8. Transfer.** High (as the baseline to beat). This is exactly the standard control-literature "audit if max suspicion exceeds a threshold calibrated on benign trajectories", given finite-sample CRC/UCB guarantees; any sequential/CFAR detector we propose must beat it on detection delay and safety at fixed audit budget. The paper's own future-work list (per-step thresholds, combining signals, temporal structure) is a direct pointer to our contributions: per-context/per-step thresholds with risk control, accumulation for diffuse attacks, adversarial robustness.

---

## Card 10 — 2610.11843 Anytime-valid detection of LLM weight exfiltration

**1. Citation / gist.** Ortega-Fernandez (MATS), Kowalczyk (NASK, MATS), Warr (Anthropic), "Anytime-valid detection of LLM weight exfiltration", NeurIPS 2026 Workshop "E-Values: From Statistics to ML", arXiv v1 2026-10-08. Gist: a prompt-level e-process over whole-response token-mismatch events (replayed on a trusted verifier with the committed sampling seed) detects steganographic weight exfiltration by a compromised inference server, combining weak evidence across responses with anytime false-alarm control.

**2. Setup.** Served token `y_{j,t}` vs seed-prescribed `Y*_{j,t} = argmax_i (l_{j,t,i}/T + g_{j,t,i})` (Gumbel–Max); mismatch `F_{j,t}`; seeded margin `Delta_{j,t}` (gap between the two leading perturbed logits). Benign mismatches come from GPU nondeterminism at near-ties. K nested response-level events `A_{j,m} = 1{∃t: F_{j,t} = 1 and Delta_{j,t} >= b_m}`, thresholds `0 = b_0 < ... < b_{K-1}` fit on a separate benign split. Null (Eq. 4): `E0[A_{j,m} | G_{j-1}] <= q_m` for all j, m — marginal over prompts from the calibration distribution. No independence among tokens within a response assumed. Threat model: attacker knows model, prompt, logits, sampler and detector, controls only emitted tokens; seed-blind vs seed-aware variants.

**3. Method.**
- Calibration: `k_m` = number of calibration responses with event m out of n; Clopper–Pearson upper bound `q_m^+` at level `eta = gamma/K` (Eq. 3); simultaneous coverage w.p. >= 1 - gamma by union bound.
- Per-threshold e-process `M_{J,m} = Prod_j (1 + lambda_{j,m}(A_{j,m} - q_m^+))` (Eq. 5). Bet: KT estimate `r_hat = (S_{j-1,m} + 1/2)/j`, `lambda_tilde = (r_hat - q^+)/(q^+(1 - q^+))` (plug-in of the growth-optimal fixed bet), clipped to `[0, c/q^+]`, c = 0.5 so factors >= 0.5.
- Combination: fixed average `M_J = (1/K) Sum_m M_{J,m}` (costs at most log K in log evidence; no threshold chosen on attack data).
- Guarantee (Eq. 7, App. B proof): `P0(sup_J M_J >= 1/alpha) <= alpha + gamma`.
- Settings: K = 7 (margin percentiles 2, 5, 10, 20, 40, 70%), alpha = gamma = 0.005 → alarm at 200, overall 1% bound; 125 benign responses fit thresholds, 125 calibrate rates, 250 matched test prompts; 1,000 bootstrap streams of 250 responses.
- Baseline: Rinberg et al. (2025) three-tier per-token classifier (fixed-seed likelihood score threshold tau = -5, raw-logit rank R = 8), alarm at first "dangerous" token.

**4. Domain/data.** LMSYS-Chat-1M prompts (<= 512 tokens), responses up to 512 tokens, temperature 1, top-k 50, top-p 0.95. Models: Llama-3.2-3B, OLMoE-1B-7B, Qwen3-32B, Qwen3-30B-A3B. Seed-blind attacker: arithmetic coding over up to 16 candidates within 0.5 logits of the max. Seed-aware attacker: binary choice between prescribed token and runner-up at positions with score gap `<= d_max in {.02, .05, .1}`. Labels: none needed beyond a trusted benign window.

**5. Results (Table 1).** Seed-blind: e-process alarms on 100% of attack streams at median 6 / 10 / 9 / 14 responses (Llama / OLMoE / Qwen3-32B / Qwen3-30B-A3B) with 0% benign alarms; Rinberg baseline 0% attack, 100% benign alarms. Seed-aware (attack % / benign %): Llama d = .02 (0.0069 bits/tok) 0/0; .05 (0.0182) 45.9/0, median 172; .1 (0.0357) 100/0, median 28. OLMoE: 0/0, 0/0, 1.7/0. Qwen3-32B: 5.6/0 (median 204), 100/0 (85), 100/0 (30). Qwen3-30B-A3B: 0/0 at all d_max (up to 0.0304 bits/token). Rinberg baseline alarms on 98.4–100% of benign streams in the seed-aware experiments. Benign burden (Table 2): responses with >= 1 mismatch 41.2% / 87.2% / 79.2% / 74.8%; benign per-token mismatch falls from ~10–40% in the tightest margin cell to < 0.1% in the widest.

**6. Limitations.** Calibration-transfer assumption (same prompt distribution, model, hardware, serving stack; trusted benign window); "prompt shift, adaptive prompt selection, or a serving-stack change may require stratified calibration or recalibration"; low-rate seed-aware attacks (hundredths of a bit per token) undetected within 250 responses — fine for slowing bulk weight theft, not for small secrets; binary events discard mismatch counts and margin magnitudes; bootstrap streams resample one 250-response pool (not independent runs); attacker is a fixed codec, not optimised against the e-process.

**7. Code.** No repository link found in the paper.

**8. Transfer.** High. Closest in spirit to our agenda: an AI-security monitor with an explicit attacker model, cross-response (≈ cross-session) accumulation of weak evidence, calibration on a trusted benign window with finite-sample (Clopper–Pearson) correction folded into the guarantee, a growth-rate-optimal predictable bet, and a mixture over K detection thresholds so no tuning on attack data. The capacity-vs-detectability framing (bits/token vs time-to-alarm) is the right analogue for "attack intensity vs detection delay" against a diluting scheming agent. Novel beyond it: continuous per-step suspicion scores instead of binary events (the authors list "betting on the continuous score" as future work), stratified/per-context calibration (they flag prompt shift as needing stratified calibration), adaptive attackers optimised against the e-process, and agentic trajectories.

---

## Card 11 — 2610.14365 ConformalGuard

**1. Citation / gist.** Bista, Jadhav, Choudhary, Saxena, Perumal (independent), Subedi (Astha.ai), Ammineni (UMass Amherst), "ConformalGuard: False-Positive-Controlled Action Gating for LM Classifiers", COLM 2026, arXiv v1 2026-10-09. Gist: conformal p-values computed against benign-only calibration scores give pre-deployment FPR control and tiered action thresholds for LLM classifiers, and coarse zero-shot LLM score grids make temperature scaling and isotonic regression operationally identical to raw thresholding.

**2. Setup.** Frozen scorer g(x) in [0,1]; benign-only calibration `C0` (n = 2,000 legitimate emails); `p(x) = (1 + Sum_i 1[s_i >= s(x)])/(n+1)`; Prop 1: `Pr(p(X) <= alpha | Y = 0) <= alpha` under exchangeability with a fixed g (deterministic ties are conservative). Shift: if `TV(cal, test legit) = eps` then bound `alpha + eps`.

**3. Method.** Tiers: p > 0.10 auto-clear; 0.01 < p <= 0.10 analyst review; 0.005 < p <= 0.01 specialist escalation; p <= 0.005 reversible autonomous blocking; each tier-or-stricter has benign rate <= its alpha. Compared to raw validation threshold, temperature scaling, isotonic regression. Stochastic averaging of 3 GPT-4o runs to refine score grid. Randomised tie-breaking examined in appendix.

**4. Domain/data.** 39,935 emails (Nazario, Phishing Pot, SpamAssassin, Enron-Spam AUEB); splits train 26,202 / val 3,742 / cal 2,000 legit / test 7,991. Scorers: fine-tuned BERT (1,176 unique scores), zero-shot Claude Sonnet 4 (11 unique values), zero-shot GPT-4o (10). Positive class is 28.7% phishing, 71.3% spam; a source classifier distinguishes corpora at 97.7%.

**5. Results (alpha = 0.01, Table 3).** BERT: raw FPR 0.008 / conformal 0.006, recall 0.996 / 0.995; isotonic overshoots (0.013). Claude: raw/temperature/isotonic all FPR 0.040, recall 0.938; conformal FPR 0.008, recall 0.875. GPT-4o: raw/TS/iso FPR 0.015, recall 0.887; conformal FPR 0.001, recall 0.564. Stochastic GPT-4o (Table 4): 1 run 33 unique values, conformal recall 0.285 at FPR 0.0049; 3-run mean 105 values, recall 0.732 at FPR 0.0051 (raw threshold FPR 0.0194). Randomised tie-breaking: recall 0.800, mean FPR 0.011, 17.2% of decisions depend on the random draw. 2% prevalence (BERT): 83 → 58 false positives per 10,000 emails (95% CI of reduction [10, 43]). Calibration size: n = 100 mean FPR 0.006 ± 0.006. Cross-source shift (Table 7): BERT Enron→SpamAssassin FPR 0.021; GPT-4o SpamAssassin→Enron 0.017 at alpha = 0.01.

**6. Limitations.** Authors: no recall/adversarial/fairness guarantees; "calibration-pool poisoning and legitimate-distribution attacks directly threaten exchangeability"; shift breaks validity; corpus artefacts. Single-shot (no sequential component).

**7. Code.** https://github.com/bishnubista/conformalguard-colm-2026

**8. Transfer.** Medium (calibration layer, not detection). Directly applicable to calibrating per-step or per-trajectory monitor thresholds against benign-only data and mapping p-values to control actions (allow / defer to trusted / audit / block). The coarse-grid finding is important for LLM suspicion monitors that output 0–10 integers: post-hoc calibration cannot fix ties, conformal picks a valid but possibly low-recall boundary, and monitor resampling increases resolution. Overlap with our CFAR/calibration ideas: medium; novelty beyond it: group-conditional (Mondrian) versions, sequential accumulation, and adversarial shaping of the benign calibration pool.
