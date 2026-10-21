# E1 — Detection theory classics: robust/minimax and adversarial quickest change detection, SPRT for intrusion detection, poisoning of online detectors, optimal thresholds, drift benchmarks

Reading cards for 11 papers, read in full from the pdftotext copies in `background/fulltext/`. Prepared 2026-10-20 for the AI-control monitoring project (sequential tests over per-step monitor suspicion scores, CFAR-style adaptive thresholds, monitor-aware adversaries).

| # | arXiv | Paper (short) | Type |
|---|---|---|---|
| 1 | 0911.2551 | Unnikrishnan–Veeravalli–Meyn, Minimax robust QCD (LFD CUSUM) | theory |
| 2 | 1204.1935 | Chen, Sequential methods for port-scanner detection (TRW/SPRT variants) | method, figures only |
| 3 | 1306.2086 | Bayraktar–Lai, Byzantine fault-tolerant distributed QCD | theory |
| 4 | 1606.06707 | Ghafouri et al., Optimal (time-varying) thresholds vs strategic attacker | game theory + toy |
| 5 | 2002.02741 | Kravchik–Shabtai, "Can't boil this frog": poisoning online AE detectors | empirical |
| 6 | 2104.04186 | Xie–Zou–Xie–Veeravalli, QCD survey | survey |
| 7 | 2509.17778 | Ramtin–Nain–Towsley, Covert adversary, continuous time | theory |
| 8 | 2601.20022 | Ramtin–Nain–Towsley, Covert adversary, discrete time | theory |
| 9 | 2606.19386 | Modgil, Wall-clock-calibrated monitors are bistable at agent cadence | small empirical |
| 10 | 2606.07789 | Cerqueira et al., Drift-detector benchmarking framework (KDD '26) | benchmark |
| 11 | 2404.19452 | Omar et al., Accuracy vs energy of drift detectors | benchmark |

---

## Cluster synthesis

### A. Theoretical facts the project must respect

1. **The delay law.** For a change from f0 to f1 with per-step KL information I = D(f1‖f0), every detector with ARL ≥ γ has worst/conditional-average delay ≥ log γ / I · (1+o(1)) (Lorden; Lai, incl. non-i.i.d. data with I = limiting rate of the conditional LLR), and CUSUM with threshold ≈ log γ attains it; CUSUM is exactly Lorden-optimal for known f0, f1 (2104.04186). Consequences: (i) the currency of detection is **KL per step of the monitor score**, so improving the monitor raises I, while (ii) raising the false-alarm budget buys little (delay changes by ~log 2 / I per doubling of ARL) in the classical regime.

2. **A covert attacker breaks the log law, and no detector can fix it.** If the attacker picks its post-change law q_γ as a function of the ARL target γ so that γ·D(q‖q_γ) stays bounded, then the *optimal* worst-case delay is Θ(γ), i.e. detection comes no sooner than the false-alarm clock. Delay grows **linearly in ARL, not in log ARL** (the brief's wording "linearly in log ARL" should read "linearly in ARL instead of logarithmically"). This holds even though the detector is the Lorden-optimal CUSUM *given the true q_γ*, so it is information-theoretic, not a mismatch artefact (2601.20022 Prop. 3.3; 2509.17778 Prop. 3.1). Phase transition: Gaussian mean shift µ ∝ γ^{−δ} is covert iff δ ≥ ½ (also variance shift σ² = O(γ^{−1/2})).
   **The same papers bound the attacker:** cumulative damage n(γ)·D^ρ is maximised exactly at the transition, giving Θ(γ^{1−ρ}). For a mean-shift ("total excess suspicion") damage model that is **Θ(√ARL)** (2509.17778: max damage 2G(½)√γ ≈ 0.563√γ at µ = γ^{−1/2}). So the "slow-boil" attacker trades speed for a hard ceiling on total anomalous signal.
   Scope: stationary i.i.d. post-change law (no within-episode adaptation, no bursts timed to the detector state), asymptotic in γ.

3. **Minimax-robust CUSUM exists when the uncertainty classes are "jointly stochastically bounded".** Then the plain CUSUM on the least-favorable-distribution LLR is *exactly* minimax under Lorden for all (ν0, ν1) in the classes, and its FAR bound holds for every null in the class (0911.2551 Thm III.2). For "shift ≥ θ_min" classes the LFD is the minimal shift; for ε-contamination the LFD LLR is a **clipped (Huberized) LLR**. Price: delay inflation ≤ D(ν1‖ν0)/[D(ν1‖ν̄0) − D(ν1‖ν̄1)] asymptotically (e.g. 21.5 vs 10.5 steps at θ = 1 when designed for θ_min = 0.1, ARL 1000). The guarantee is only relative to the declared class: an attacker that operates below θ_min is outside it, and per fact 2 there is no fix for that.

4. **Aggregation across untrusted channels must be voting, not summing.** With one Byzantine stream among N, the centralized summed-LLR CUSUM can be driven to delay linear in ARL (via false-alarm collapse with a fake positive drift, or silence). Per-stream CUSUM plus "alarm at the (N_max+1)-th local alarm" (N_max < N/2) restores delay = O(log ARL) against **arbitrary, adaptive** manipulation of up to N_max streams, with pre-log constant 4/µ² vs 2/(Nµ²) honest. A 2-of-3 group-wise CUSUM gets a pre-log of 12/(Nµ²) (1306.2086 Thms 3.2, 3.7, 4.1, 4.2). This is the only result in the cluster that is robust to a *fully adaptive* adversary, and it requires the adversary to control a minority of channels.

5. **A strategic attacker chooses where and when to attack against the thresholds.** With time- or context-varying damage D(k), the Stackelberg-optimal thresholds equalize *worst-case damage before detection* across contexts. They do not equalize per-context false-alarm rates. Polynomial DP: Algorithm 2, O(T⁴|Δ|²) (1606.06707). A CFAR rule (constant FPR per context) is therefore not optimal against a monitor-aware attacker, and it leaves loose thresholds exactly where benign behaviour is noisy. Those are the contexts the attacker will choose. Randomized thresholds are named as future work but are not analysed anywhere in this cluster.

6. **Baseline poisoning is possible but rate-limited when only non-alerting data updates the baseline.** Empirically (2002.02741), boiling-frog poisoning of an online-retrained detector needed a number of poison samples growing ~linearly with target magnitude and with the size of the retained clean history (more poison than training samples to move amplitude 0.4). It failed for targets outside the normal support. It succeeded for only 4/10 real SWaT attacks, and only at clipped magnitudes. Adding 2 correlated sensors blocked the successful cases. This robustness came from physics constraints and does **not** transfer as a guarantee to LLM behaviour.

7. **Calibrate in steps, not seconds.** Leaky integrators or EMA baselines with wall-clock half-lives are bistable across agent cadences (constant alarm at Δt ≤ 1 s, silent at Δt ≥ 60 s). A sample-time CUSUM is exactly cadence-invariant (2606.19386). A wall-clock decay would also hand the agent an evasion knob, since it can slow down to drain the statistic (our inference).

8. **Evaluation hygiene.** Use semi-synthetic injection of change segments at random onsets into real benign streams (Monte Carlo), window-based TP/FP with normalized detection time and episode recall, and leave-one-dataset-out hyper-parameter tuning. Gradual (interleaved) drifts are systematically harder for every detector. Detectors left at library defaults can be near-useless (PH/DDM/EDDM < 10% true first alarms; GMA/RDDM recall ≈ 1 with precision ≈ 0.05) (2606.07789, 2404.19452).

### B. Best-practice detector design against strategic adversaries (as supported by this cluster)

- **Multi-chart monitoring.** Run a Shewhart (per-step) threshold for single catastrophic actions (optimal for catching a change at its onset), a robust CUSUM at the declared minimum effect θ_min (worst-case optimal, recursive), and a GLR / window-limited GLR or mixture CUSUM for unknown magnitudes (near-optimal for large shifts; Table I of 0911.2551 shows the crossover). Set thresholds jointly to a total ARL budget.
- **Clipped-LLR increments** (Huber LFDs) keep false alarms bounded under heavy-tailed or contaminated benign scores.
- **Sample-time indexing** of all statistics and of any adaptive baseline's forgetting.
- **Per-monitor sequential statistics with k-of-N voting** when any score source (e.g. an untrusted monitor) may collude.
- **Context thresholds from a damage-weighted Stackelberg objective**, not from CFAR alone. Randomization is a natural but untested addition. It can deny the attacker exact knowledge of the threshold, but it cannot beat the γ·D information bound of fact 2.
- **Adaptive baselines:** update only on clearly benign data, cap per-update drift, keep a frozen trusted reference set mixed in, use multivariate baselines, and run a second-order detector on baseline drift itself.
- **Beyond-the-papers gaps to cover ourselves:** (a) CUSUM's reflection at 0 discards evidence between separated bursts, so a burst-and-pause attacker whose bursts each stay below h may evade it. Whole-episode SPRT/e-processes or windowed GLR accumulate across bursts (our inference, not analysed in this cluster). (b) Pooling evidence across episodes or instances of the same model multiplies the number of observations per decision. This is the main lever against the per-stream covert bound, because covertness is defined relative to the ARL of the stream being monitored.

### C. Concrete, testable predictions

1. **Log-law baseline.** For non-adaptive scripted attacks, CUSUM detection delay vs log(ARL) is linear with slope ≈ 1/Î, where Î is the KL estimated from benign vs attack score distributions; GLR matches robust CUSUM within a constant.
2. **Covert pacing.** A monitor-aware model told the ARL/threshold and rewarded for completing a side task undetected will reduce its per-step suspicion shift as ARL grows. The achieved total excess suspicion (and side-task progress, if progress ∝ cumulative anomalous actions) before detection should scale ≈ √ARL, with a regime change where Î·ARL ≈ 1.
3. **Robust vs GLR crossover.** A robust CUSUM at θ_min beats GLR on subtle attacks and loses on blatant ones (mirroring 242.7 vs 496 at θ = 0.1 and 21.5 vs 12.35 at θ = 1.0 in 0911.2551).
4. **CFAR masking.** Under known per-context CFAR thresholds, attacks concentrate in high-variance (loose-threshold) contexts. Damage-weighted Stackelberg thresholds reduce attacker payoff relative to CFAR at equal total audit budget.
5. **Boiling frog.** The number of poisoning episodes needed to shift an adaptive per-task baseline by Δ grows ∝ Δ × reference-window size. A frozen reference, drift caps, and multi-feature baselines raise it sharply. Targets requiring out-of-support actions are not achievable by poisoning.
6. **Monitor collusion.** Summing an untrusted monitor's score with trusted monitors' scores collapses either ARL or delay when that monitor lies. k-of-N voting restores log scaling.
7. **Cadence.** Wall-clock-decay baselines change detection behaviour with agent latency (and an agent can exploit this by slowing down). Step-indexed CUSUM is invariant.
8. **Gradual > abrupt difficulty.** Interleaving benign and malicious steps lowers recall or increases delay for every detector family, consistent with the drift benchmarks.

### D. Is our approach provably weak or provably sound?

- **Provably weak (within these models):** against an attacker whose per-step score KL is O(1/ARL), *no* sequential test on that score stream can detect materially before a false alarm would occur (2601.20022, 2509.17778). Minimax-robust guarantees hold only for attacks above the declared θ_min. Summing untrusted score streams is fragile (1306.2086).
- **Provably sound (conditional):** if causing harm requires cumulative anomalous signal growing faster than √ARL (more generally ARL^{1−ρ}), or per-step shifts ≥ θ_min, then a (robust) CUSUM bounds attacker damage, with log-ARL delay above θ_min, and robust-CUSUM FAR control holds for every benign distribution in the declared class. k-of-N voting is sound against arbitrary manipulation of a minority of monitors.
- **Not covered by any paper here:** within-episode adaptive adversaries who observe or infer the detector state, burst timing against CUSUM resets, randomized thresholds, and non-stationary benign baselines that the agent itself shapes across many episodes.

---

## Reading cards

### 1. Minimax Robust Quickest Change Detection — arXiv:0911.2551

**Citation.** J. Unnikrishnan, V. V. Veeravalli, S. Meyn, "Minimax Robust Quickest Change Detection," arXiv:0911.2551 (v2, Jun 2010; abridged version at ISIT 2009 per the paper's footnote).

**Gist.** If the pre-/post-change uncertainty classes are "jointly stochastically bounded" by a pair of least-favorable distributions (LFDs), then the ordinary CUSUM (resp. Shiryaev, SRP) test designed for the LFDs is exactly (resp. exactly / asymptotically) minimax-optimal over the whole classes.

**Model / assumptions.**
- Observations i.i.d. ν0 before change point λ, i.i.d. ν1 from λ on; independent conditioned on λ. ν0 ∈ P0, ν1 ∈ P1 (known uncertainty classes; true members unknown).
- Criteria: Lorden WDD(τ) = sup_λ ess sup E_λ[(τ−λ+1)^+ | F_{λ−1}], FAR(τ) = 1/E_∞[τ]; Pollak J_SRP(τ) = sup_λ E_λ[τ−λ | τ≥λ]; Bayesian ADD = E[(τ−Λ)^+], PFA = P(τ<Λ) with geometric prior.
- Robust problems: min_τ sup_{ν0∈P0,ν1∈P1} delay s.t. sup_{ν0∈P0} FAR(τ) ≤ α (eqs. 4–6).
- **Adversary model:** "nature" picks (ν0, ν1) from the classes, but is *stationary* — the same ν1 for every post-change sample (i.i.d.). No adaptive, time-varying, or data-dependent adversary. This is the key gap for our use.
- **Joint Stochastic Boundedness (JSB, Def. 1, from Veeravalli–Başar–Poor 1994):** there exist (ν̄0, ν̄1) ∈ P0×P1 with ν̄1 ≪ ν̄0 such that, with L*(x) = log dν̄1/dν̄0(x), the law of L*(X) under any ν0 ∈ P0 is stochastically *smaller* than under ν̄0, and under any ν1 ∈ P1 is stochastically *larger* than under ν̄1. Intuitively the LFD of each class is the member "closest" to the other class. Holds for 2-alternating-capacity classes (Huber–Strassen): ε-contamination, total-variation neighbourhoods, Prohorov neighbourhoods, band classes, p-point classes.

**Main results.**
- **Lemma III.1:** if U_i ≻ V_i (stochastically larger), independent, and h is continuous and coordinatewise non-decreasing, then h(U) ≻ h(V). (CUSUM max-of-partial-sums is such an h.)
- **Theorem III.2 (Lorden, exact, non-asymptotic).** Under (i) JSB by (ν̄0, ν̄1), (ii) every ν0 ∈ P0 is ≪ ν̄0, (iii) L* continuous on supp ν̄0: the robust Lorden problem (4) is solved by the CUSUM on L*:
  τ*_C = inf{n ≥ 1 : max_{1≤k≤n} Σ_{i=k}^n L*(X_i) ≥ η}, η set so E*_∞(τ*_C) = 1/α (computed under the LFD ν̄0). Recursive form S_{n+1} = S_n^+ + L*(X_{n+1}). FAR under any ν0 ∈ P0 is ≤ α (E^ν_∞ τ ≥ E*_∞ τ = 1/α), and WDD under any (ν0, ν1) is ≤ WDD under the LFDs.
- **Cost of robustness (asymptotic, α→0):** for true (ν0, ν1),
  WDD_ν(τ*_C) ≤ |log α|(1+o(1)) / [D(ν1‖ν̄0) − D(ν1‖ν̄1)],
  versus the optimal lower bound |log α|(1+o(1))/D(ν1‖ν0) (Lorden). So the robust test's delay is at most a factor D(ν1‖ν0)/[D(ν1‖ν̄0) − D(ν1‖ν̄1)] worse. (Denominator = E_{ν1}[L*], the drift of the robust CUSUM under the true post-change law.)
- **Theorem III.3 (SRP, asymptotic):** if P0 = {ν0} is a singleton and JSB holds, the SRP rule built on (ν0, ν̄1) is asymptotically minimax for (5) (difference in worst-case delay → 0 as α→0). Exact optimality obtainable in special cases (SR-r for Exp(1)→Exp(2) is exactly optimal for P1 = {Exp(θ): θ ≥ 2}).
- **Theorem III.4 (Bayesian/Shiryaev, exact):** P0 singleton + JSB + geometric prior ⇒ Shiryaev test on L* is optimal for (6). Fails in general if P0 is not a singleton (pre-change LLRs are stochastically larger under ν̄0, so the stopping time is not least favorable) — analogous to Huber's observation that the robust SPRT is not exactly minimax.
- Lorden result needs no singleton P0 because the robust CUSUM's WDD depends only on the *support* of ν0 (ess sup over pre-change paths).

**Practical recipe.**
1. Specify P0 (null-score uncertainty) and P1 (attack-score uncertainty) as classes satisfying JSB — e.g. ε-contamination around nominal p0, p1, or "mean shift at least θ_min".
2. Find LFDs. For a monotone family with a minimum effect size (P1 = {N(θ,1): θ ∈ [θ_min, θ_max]}), the LFD is simply the smallest shift θ_min. For ε-contamination, Huber's clipped-LR LFDs (eqs. 21–22): q0 = (1−ε)p0 where L ≤ b, ((1−ε)/b)p1 where L > b; q1 = (1−ε)p1 where L > a, a(1−ε)p0 where L ≤ a; a, b solve the normalization equations. Result: L* is a **clipped (Huberized) log-likelihood ratio** — bounded per-step increment.
3. Run CUSUM on L*, threshold η calibrated by simulation/analysis under ν̄0 to give ARL = 1/α.

**Empirical results (Monte-Carlo).**
- Gaussian mean shift, P0 = {N(0,1)}, P1 = {N(θ,1): θ∈[0.1,3]}, LFD ν̄1 = N(0.1,1), α = 0.001 (ARL 1000). WDD (Table I):
  | θ | Optimal CUSUM | Robust CUSUM | GLR-CUSUM |
  |---|---|---|---|
  | 0.1 | 242.7 | 242.7 | 496 |
  | 0.2 | 111.5 | 116.8 | 184 |
  | 0.4 | 43.2 | 55.6 | 57.2 |
  | 0.6 | 23.5 | 36.3 | 28.6 |
  | 1.0 | 10.5 | 21.5 | 12.35 |
  Robust CUSUM beats GLR at small θ (worst case) and loses at large θ; GLR is near-optimal for large shifts.
- Robust Shiryaev (geometric prior ρ = 0.1, α = 0.001): matches the optimal at θ = 0.1, much worse at large θ (Fig. 1; no table).
- ε-contamination N(0,1) vs N(1,1), α = 0.001, σ0 = 1: robust CUSUM WDD 14.77–15.59 (ε=0.05) vs optimal 8.65–9.17; 11.27–11.29 (ε=0.005) vs 10.33–10.39 (Table II). Robust delay is invariant to σ0: 15.09 (ε=0.05), 11.27 (ε=0.005).

**Limitations.** i.i.d. pre/post-change; adversary/nature is a *fixed* member of the class, not adaptive or time-varying; JSB is a restrictive condition (fails for many composite classes, e.g. two-sided shifts); SRP/Bayes results need a known pre-change law; delay penalty can be large (2× at θ=1.0 in Table I). No treatment of non-stationary nulls.

**Implications for AI-agent monitoring.**
- **Directly usable design:** if we can posit a minimum "suspicion-score shift" for any attack worth catching (θ_min) and an ε-contaminated null for benign behaviour, then a CUSUM on the clipped LLR at θ_min is *provably* minimax among all stopping rules for i.i.d. stationary attackers in that class — and per-step clipping bounds the influence of any single outlier benign step (false-alarm robustness to heavy tails).
- **What it predicts about pacing:** the LFD *is* the attacker that sits at the edge of P1 closest to P0. An adversary who can choose any ν1 in the class picks the LFD, and the robust CUSUM's delay ≈ |log α| / E_{ν1}[L*]. If the attacker can drive E_{ν1}[L*] → 0 (i.e. choose ν1 inside, not at the edge of, the class we assumed) the guarantee vanishes: minimax optimality is only relative to the declared P1. Choosing θ_min is a policy decision about which "slow" attacks we accept missing.
- **Not a proof of soundness against an adaptive model**: the theorem covers stationary i.i.d. post-change laws; a model that interleaves benign and attack steps, or adapts to the detector state, is outside it (see covert-adversary papers 2509.17778 / 2601.20022).
- Robust test is cheaper than GLR and better at the worst case; GLR better when attacks are blatant — suggests running both (or a GLR with a θ_min floor).

---

### 2. New Sequential Methods for Detecting Portscanners — arXiv:1204.1935

**Citation.** Xinjia Chen, "New Sequential Methods for Detecting Portscanners," arXiv:1204.1935 (Apr 2012), stat.AP. Short (11 pp.) note, no peer-review venue stated.

**Gist.** Replaces the Threshold Random Walk (TRW) SPRT for port-scan detection (Jung, Paxson, Berger, Balakrishnan 2004) with a *truncated* KL-divergence-boundary sequential test whose parameters are tuned numerically so that error probabilities hold uniformly over composite hypotheses and the sample size is deterministically bounded.

**Model / assumptions.**
- Binomial model from Jung et al.: for remote source r, X_i ∈ {0,1} = success/failure of its first connection attempt to the i-th distinct local host; X_i i.i.d. Bernoulli(p). Scanners have low success rate, benign hosts high.
- Composite hypotheses (note the paper's labelling): H0: p ≤ p0 ("scanner") vs H1: p ≥ p1 ("benign"), 0 < p0 < p1 < 1, with risk requirement Pr{Reject H0 | p} ≤ α ∀p ∈ (0,p0] and Pr{Reject H1 | p} ≤ β ∀p ∈ [p1,1) (eq. 2). Indifference zone (p0,p1) unconstrained.
- **No adversary model** — the scanner is a fixed Bernoulli source; it does not adapt its success rate (e.g. by mixing in connections to known-live hosts).

**Main results.**
- **TRW (as restated):** monitor the likelihood ratio Λ_n = Pr{X_1..n | p0}/Pr{X_1..n | p1} = exp(n[p̂_n ln(p0/p1) + (1−p̂_n) ln((1−p0)/(1−p1))]); stop when Λ_n ≤ k0 (declare benign) or Λ_n ≥ k1 (declare scanner). The paper states that with k0 = α and k1 = 1/β the risk requirement (2) holds, and that TRW minimises the expected sample number at p = p0 and p = p1 among tests meeting the errors at those points (Wald–Wolfowitz SPRT optimality). Drawbacks emphasised: unbounded sample size; performance poor for p away from p0, p1.
- **New test:** with p̂_n the running success frequency, Y_n = KL(Bern(p̂_n)‖Bern(p0)) and Z_n = KL(Bern(p̂_n)‖Bern(p1)) (with boundary conventions at p̂_n ∈ {0,1}). Stop at the first n with
  - Y_n ≥ (1/n) ln(1/(ζa)) and p̂_n ≥ p0 → declare **benign**;
  - Z_n ≥ (1/n) ln(1/(ζb)) and p̂_n ≤ p1 → declare **scanner**.
  I.e. a GLR/Chernoff-type rule n·KL(p̂_n‖p_j) ≥ log(1/(ζ·weight)). Parameters: risk-tuning ζ, weights a, b.
- **Calibration ("risk tuning"):** by monotonicity of the OC function, it suffices to check errors at p0 and p1. Define A = α/Pr{Reject H0|p0}, B = β/Pr{Reject H1|p1}, Q = max(A,B), R = min(A,B); minimise Q subject to R ≥ 1 by an iterative minimax search (bisection on ζ, multiplicative updates of a or b by (1+(Q*−1)/5)), with exact error probabilities computed by path-counting (Franzén 2001) or the Schultz et al. 1973 recursion.
- **Bounded sample size:** max observations = ⌊m*⌋+1 where z* ∈ (p0,p1) solves ((1−p0)/(1−z))^{1−z}(p0/z)^z = (ζa)^{1/m} and the same with p1, b; for a = b, z* = ln((1−p0)/(1−p1)) / ln((1−p0)p1/((1−p1)p0)) and m* has closed form.
- **Multi-valued extension:** three hypotheses scanner/marginal/benign (H0: p ≤ p0, H1: p0<p<p1, H2: p ≥ p1) with indifference zones (p0′,p0″), (p1′,p1″), using the author's multistage-test framework (arXiv:0809.3170).

**Practical recipe.** Pick p0, p1 from empirical data; compute exact OC by path counting for candidate (ζ, a, b); tune to make both error constraints tight; deploy as a truncated sequential test on per-source Bernoulli outcomes.

**Empirical results.** Only figures, no tables. Example settings: p0 = 0.1, p1 = 0.15, α = β = 0.1, new test with ζ = 0.96, a = b = 0.1; Fig. 2 shows both tests' risk ≤ 0.1 across p; Fig. 3 plots the ratio of average sample numbers (new/TRW) vs p — the text claims the new test "requires a much smaller number of connection attempts", but no exact numbers are stated. Fig. 1 example: p0 = 0.2, p1 = 0.8, ζ = 1, a = b = 0.1. Triple-test example: δ0 = δ1 = δ2 = 0.1, p0 = 1/3, p1 = 2/3, indifference half-widths 1/9.

**Limitations.** No real network data; no adversary; i.i.d. Bernoulli assumption; claims of superiority are figure-only; this is a one-shot sequential *test* (decide H0/H1), not change detection — a host that behaves benignly then starts scanning is not modelled.

**Implications for AI-agent monitoring.**
- Transfers as a template for **per-agent/per-episode sequential classification** on *binary* monitor outputs (flag/no-flag per step), with Wald-style thresholds and a hard cap on observations (useful when episodes have bounded length).
- Key design lesson: a simple SPRT tuned at two points (p0, p1) can be inefficient for intermediate rates; GLR-style boundaries (n·KL(p̂‖p_j)) with exact OC calibration control error **uniformly over composite hypotheses**.
- **Attacker pacing:** the TRW/SPRT framing has an indifference zone; a scheming agent that keeps its "suspicious-step rate" inside (p0, p1) gets no error guarantee at all — the test may classify it either way. The 3-way "marginal" class is a natural escalation tier (send to human review) rather than forced binary decision.
- **Not robust to strategic mixing:** a scanner (agent) that pads with benign actions changes its effective p — the binomial model treats this as just a different p; detection then depends entirely on where the padded rate falls. Nothing here is provably sound against adaptive adversaries.

---

### 3. Byzantine Fault Tolerant Distributed Quickest Change Detection — arXiv:1306.2086

**Citation.** E. Bayraktar, L. Lai, "Byzantine Fault Tolerant Distributed Quickest Change Detection," arXiv:1306.2086 (v2 Dec 2014); SIAM J. Control Optim. 53(2):575–591, 2015 (as cited in the 2104.04186 survey, ref. [20]).

**Gist.** With N sensors feeding a fusion center, a *single* compromised sensor can make the centralized CUSUM's detection delay scale linearly (instead of logarithmically) in the ARL; running per-sensor CUSUMs and alarming at the **second** local alarm (or 2-of-3 group CUSUMs) restores log scaling against *any* attack strategy.

**Model / assumptions.**
- N ≥ 3 sensors, i.i.d. signals across sensors; one sensor n_c (unknown) compromised (extension: N_max+1-alarm rule if ≤ N_max < N/2 compromised).
- Continuous time: ξ^(n)_t = µ(t−τ)^+ + W^(n)_t. Discrete time: ξ^(n)_t ~ f0 for t ≤ τ, f1 after.
- **Adversary:** sends arbitrary reports ξ̄^(n_c), may use its own true observations, arbitrarily complex and time-varying strategy; no assumptions on strategy. The *environment* change is not adversarial.
- Criteria: d(T) = sup_{τ, n_c, s} ess sup E_{τ,n_c,s}[(T−τ)^+ | F_τ] (Lorden, also maximized over attacker identity and strategy) and ARL(T) = inf_{n_c, s} E_{∞,n_c,s}[T] (worst case over attacks). Problem: inf_T d(T) s.t. ARL(T) ≥ γ.

**Main results.**
- **Honest baseline (continuous):** CUSUM on u_t = µΣ_n ξ̄^(n)_t − ½Nµ²t, y_t = u_t − inf_{s≤t} u_s, T_ν = inf{t: y_t ≥ ν}; ARL = 2(e^ν − ν − 1)/(Nµ²), d = 2(e^{−ν} + ν − 1)/(Nµ²), so d = (2/(Nµ²))[log ARL + log(Nµ²/2) − 1 + o(1)].
- **Proposition 3.1 (attack on CUSUM):** attacker sets its report to a Brownian motion with drift Nµ (eq. 3.6 printed as ξ̄ = Nt + W_t; the proof uses total drift (2N−1)µ post-change). Then ARL(T_ν) ≤ (e^{−ν}+ν−1)/(Nµ²/2) and d(T_ν) ≥ (e^{−ν}+ν−1)/((3N/2−1)µ²): both linear in ν, so **delay scales linearly in ARL**. (Mechanism: the fake positive drift collapses the ARL to O(ν); the threshold needed to restore a given ARL is no longer logarithmic.)
- **Theorem 3.2 (second-alarm rule, continuous):** per-sensor CUSUMs T_h^(n); fusion alarms at the second order statistic T_(2),N. Against any attack, d(T_h) ≤ (4/µ²)[log ARL(T_h) + log((N−1)µ²/2) − 1 + o(1)]. Proof: worst-case ARL when the attacker alarms immediately (ARL ≥ E[min of N−1 honest] ≈ 2e^h/((N−1)µ²)); worst-case delay when the attacker stays silent (d ≤ E[2nd of N−1 honest] ≤ 4(e^{−h}+h−1)/µ²). Pre-log factor 4/µ² vs 2/(Nµ²) honest-centralized and 2/((N−1)µ²) when the bad sensor is known.
- **Remark 3.6:** with ≤ N_max compromised, use the (N_max+1)-th alarm; requires N_max < N/2 (else silent attackers block alarms forever).
- **Theorem 3.7 (group-wise, continuous):** split into 3 groups of N/3, CUSUM per group, alarm at 2 of 3: d ≤ (12/(µ²N))[log ARL + log(Nµ²/3) − 1 + o(1)] — pre-log decreasing in N; centralized (needs raw signals). Remark 3.9: 2 groups fail (silent negative-drift attacker blocks the 2nd alarm; or under plain CUSUM, positive drift kills ARL).
- **Discrete time (Thms 4.1, 4.2):** honest CUSUM ARL = e^ν/(R²ND(f1‖f0))(1+o(1)), d = (ν+β+κ)/(ND(f1‖f0)) + o(1) (overshoot κ, β, R as in eqs 4.3–4.5). Second-alarm: d ≤ (2/D(f1‖f0))[log ARL + log((1−e^{1−N})R1²D/e^{1−N})] + β1 + κ1 + o(1). Group-wise: d ≤ (2/(D N/3))[log ARL + log((1−e^{−1})R_G²DN/3 / e^{−1})] + β_G + κ_G + o(1). Uses asymptotic geometric (exponential) distribution of T_h/C under P∞ (Khan 1995).

**Practical recipe.** Run an independent CUSUM per (honest-presumed) channel; set the per-channel threshold h so that the order-statistic lower bound ARL ≥ E_∞[min of the N−1 honest local run lengths] meets the target (continuous case: ≈ 2e^h/((N−1)µ²)); fuse with a k-out-of-N rule, k = N_max+1. Evaluate worst cases by simulating the "alarm immediately" attacker (for ARL) and the "always silent" attacker (for delay).

**Empirical results.** Simulations only (worst-case attacker as above). Brownian, N = 9, µ = 1: delay vs log(ARL) is linear for both schemes over log ARL ∈ [4,14] (Fig. 2; delay ≈ 2–17); delay ratio to the 8-honest-sensor centralized CUSUM stays below the asymptotic bounds 2(N−1) = 16 (distributed) and 6(N−1)/N = 16/3 (group-wise) — empirically ≈ 2.5–5.5 (Fig. 3). Discrete Gaussian N(0,1)→N(1,1), N = 9: log scaling, group-wise lower (Fig. 4). No tables.

**Limitations.** i.i.d. across sensors; known f0, f1; only upper/lower bounds (no optimality proof for the second-alarm rule); N_max < N/2 needed; group-wise needs raw data centrally.

**Implications for AI-agent monitoring.**
- **Direct analogue: ensembles of monitors where some monitors may be untrusted/colluding** (e.g. untrusted-model monitoring). Summing LLRs across monitors (the "centralized CUSUM") is fragile: one compromised score stream that injects positive drift destroys ARL, one that injects negative drift (silence) delays detection. Proven fix: per-monitor sequential statistics + **k-of-N voting with k = N_max+1** gives log-ARL delay against *arbitrary* adaptive manipulation of up to N_max < N/2 streams.
- Also applies to **multiple feature channels** of a single monitor (e.g. trusted-monitor score, action-type detectors, resource-usage detectors) when the agent can manipulate some channels but not others.
- Does **not** cover an adversary who controls the *environment signal itself* (the monitored agent shaping all honest monitors' inputs) — that's the covert-adversary setting.
- Predictive: averaging/summing suspicion scores over an untrusted monitor and trusted monitors should show linear-in-log-ARL degradation under a monitor that fakes alarms or stays silent; k-of-N voting should restore it. Testable.

---

### 4. Optimal Thresholds for Anomaly-Based Intrusion Detection in Dynamical Environments — arXiv:1606.06707

**Citation.** A. Ghafouri, W. Abbas, A. Laszka, Y. Vorobeychik, X. Koutsoukos, "Optimal Thresholds for Anomaly-Based Intrusion Detection in Dynamical Environments," arXiv:1606.06707 (v2 Feb 2017), cs.GT.

**Gist.** Threshold selection for a CUSUM-type detector posed as a Stackelberg game against an attacker who picks *when* to attack; when damage D(k) varies over time, an optimal **time-varying** threshold (computable in polynomial time by DP) beats the best fixed threshold — tight thresholds in critical periods, loose elsewhere.

**Model / assumptions.**
- Finite horizon {1..T}. Time-varying expected damage per step D(k) ≥ 0 (known to both). Attack [k_a, k_e]; total damage D̄ = Σ_{k=k_a}^{k_e} D(k).
- Detector abstracted to two monotone curves: detection delay δ(η) (increasing in threshold) and false-positive rate FP(η) (decreasing). CUSUM S(k) = (S(k−1)+z(k))^+ is the example. Delays treated as **deterministic** (expected delay); no stochasticity of detection in the game.
- **Adversary:** knows the system model and the defender's (fixed or time-varying) thresholds (Stackelberg leader–follower; strong SSE with tie-breaking for defender); chooses only the start time k_a; "worst-case attacker that will not stop the attack before detection". Does not shape its signal to evade (no pacing below drift), and cannot influence the baseline.
- Defender costs: C per false alarm investigation; C_d per threshold change.

**Main results.**
- Fixed threshold: loss L(η, k_a) = C·FP(η)·T + Σ_{k=k_a}^{k_a+δ(η)} D(k); attacker payoff P = Σ_{k=k_a}^{k_a+δ(η)} D(k). Optimal η = argmin over η of L at the attacker's best response. **Prop. 1:** exhaustive search over δ and k_a, O(T²).
- Adaptive threshold η = {η_k}: detection time σ(η, k_a) = min{k : δ(η_k) ≤ k − k_a}; loss L = N·C_d + Σ_{k=1}^T C·FP(η_k) + Σ_{k=k_a}^{σ} D(k), N = #threshold changes.
- **Theorem 1:** Algorithm 2 computes an optimal adaptive threshold: (a) DP "MinimumCostThresholds(P)" gives the min false-alarm + change cost TC(P) subject to "every attack causes ≤ P damage", via recursion Cost(n, m) = min_{δn} {Cost(n+1, m+1) + FP(δn) if δn > m; Cost(n+1, δn) + FP(δn) if Σ_{k=n−m}^n D(k) ≤ P; ∞ otherwise} (with an extra state δ_{n−1} and +C_d for changes, eqs. 10–11); (b) optimal P* = argmin_P TC(P) + P, where it suffices to search the finite set of interval sums of D. **Prop. 2:** O(T⁴|Δ|²) = O(T⁶).

**Practical recipe.** Estimate the (delay, FPR) frontier of your detector as a function of threshold; estimate a time-/context-varying damage profile D(k); solve the DP for the per-time delay budget δ_k; map δ_k back to thresholds; add a switching cost to avoid chattering.

**Empirical results (water distribution network, 24 hourly steps).** D(k) = 2·demand(k). Frontier: FP(0) = 0.95, FP(23) = 0.02.
- Fixed: C = 7 → δ* = 5, L* = 171.30, best response k_a* = 10, payoff 91. C = 8 → δ* = 6, L* = 181.86, k_a* = 9, payoff 99.
- Adaptive (C = 8, C_d = 10): δ = 23 for k ∈ {1..11}, δ = 1 for {12..15}, δ = 3 for {17..23} (k = 16 not given in the text); L* = 138.88, best response k_a = 13, payoff 39.
- Adaptive converges to fixed when C_d ≥ 45 (C = 8); adaptive loss grows less steeply with C (Figs. 5–6).

**Limitations.** Deterministic-delay abstraction (the real detection time is random); attacker only picks timing; full-information attacker but no evasive signal shaping; tiny toy (T = 24); single detector; no learning of D(k). Future work they list: **randomized thresholds (moving-target defense)**, SPRT detectors, multiple systems.

**Implications for AI-agent monitoring.**
- This is the formal version of "**CFAR / per-context thresholds against a strategic attacker**": the attacker best-responds by attacking where the threshold is loose *relative to* damage. Optimal context-dependent thresholds must equalise worst-case damage across contexts, *not* equalise per-context false-alarm rates. A CFAR rule (constant FPR per context) is generally **not** the Stackelberg-optimal policy, and it leaves loose thresholds exactly where the benign baseline is noisy — which a monitor-aware agent will target ("pick contexts with high thresholds").
- Predicts: a strategic agent's attacks should concentrate in contexts whose threshold-to-damage ratio is highest; testable by giving an agent knowledge of per-context thresholds.
- Gives a concrete algorithm: if we can estimate damage-if-undetected per context (e.g. tool permissions, prod access) and the delay/FPR curve per context, solve min_P TC(P)+P.
- Weakness for us: a fully informed attacker sees the thresholds; the paper flags randomized thresholds as the natural extension (not analysed). Not a soundness proof against pacing/poisoning.

---

### 5. Can't Boil This Frog: Robustness of Online-Trained Autoencoder-Based Anomaly Detectors to Adversarial Poisoning Attacks — arXiv:2002.02741

**Citation.** M. Kravchik, A. Shabtai, "Can't Boil This Frog: Robustness of Online-Trained Autoencoder-Based Anomaly Detectors to Adversarial Poisoning Attacks," arXiv:2002.02741 (Feb 2020).

**Gist.** First study of gradual ("boiling frog") poisoning of an *online-retrained* autoencoder anomaly detector for ICS time series: white-box attacker injects a sequence of individually non-alerting samples to drift the model until a target attack is accepted as normal; it works only for small attacks and is defeated by modelling a few more correlated sensors.

**Model / assumptions.**
- Detector: undercomplete autoencoder (with "inflating" layers, from Kravchik & Shabtai 2019) reconstructing sliding windows of multivariate sensor data; alert if residual > threshold (0.2 in most experiments). Trained by gradient descent to MSE < 0.01.
- **Online retraining:** periodically retrained on new data appended to old; **only data that did not trigger alerts is used for retraining** (key constraint — each poison point must itself pass the current detector). In experiments retraining after every poisoning iteration.
- **Threat model:** malicious sensor (attacker spoofs sensor readings seen by both the PLC and detector; cannot touch the PLC→SCADA network); **white-box** (knows training data, features, algorithm, hyper-parameters, learned weights, retraining schedule); knows when injected data will be used for retraining. Goal = integrity: find D_p such that after training on D_tr ∪ D_p, A(D_val ∪ Y_a, w) = 0 (no alerts on clean validation *and* the attack).
- Bilevel optimization: D_p* ∈ argmin L(D_val ∪ Y_a, ŵ) s.t. ŵ ∈ argmin_w L(D_tr ∪ D_p, w).

**Main results / methods (empirical paper; no theorems).**
- **Back-gradient poisoning (Alg. 1–2):** compute ∇_{y_c} of the attacker objective through reversed SGD training (Maclaurin et al.; Hessian-vector products), take normalized steps, accept a poison point only if it raises no alert, decay the step otherwise; add clean data if the model becomes "over-poisoned" (validation alerts).
- **Interpolative poisoning (Alg. 3):** step from current accepted point toward the attack signal by rate·(y_a − y_p)/2, shrink rate on alert, grow it on success — literal boiling frog.
- "Wrapper model" to handle overlapping sliding windows (each time point appears in many windows, so poisons must be much longer than the attack).
- Attack-based initial poison (closest non-alerting values to the attack, refined by gradient ascent) reduces the number of poison points.

**Empirical results.**
- Synthetic sines (noise σ = 0.05, threshold 0.2): single-sequence interpolation succeeded up to attack amplitude **0.4**; required poison count grew ~linearly with amplitude and with training-set size; reaching 0.4 required **more poisoning samples than training samples**; larger amplitudes impossible without alerts. Multi-sequence (sliding window): success strongly location-dependent — **no significant attack poisonable at SIN_TOP** (pushing beyond the signal's max, the most valuable attack type); back-gradient reached larger magnitudes than interpolation at SIN_BOTTOM/SIN_SIDE.
- Iteration time (s): single-sequence 1.27 (interp.) vs 33.16 (back-grad.); multi-sequence 1.24 vs 67.37 (Colab TPU, 100-point sequences).
- **SWaT (10 sensor-spoofing attacks, 5-s subsampling, [0,1] normalization, training window 10× attack length):** poisoning succeeded for only 4/10 attacks and only at clipped magnitudes far below the real ones: #16 (LIT-301, FIT-201; full 0.893) → 0.55 with 2 poison points (back-gradient); #31 (LIT-401, FIT-401; full 0.769) → 0.35 with 0 points (residual already < 0.2 — no poisoning needed; at threshold 0.1 neither algorithm succeeded); #33 (LIT-101, FIT-101; full 0.582) → 0.41, 1 point; #36 (LIT-101, FIT-101; full 1.213) → 0.41, 1 point. Attacks #3, #7, #8, #10–11, #32 (full magnitudes 1.325, 1.809, 2.19, 22.597, 1.814) not poisonable even at 0.25. **Adding two more related sensors (e.g. MV-101, P-101 or FIT-301, P-302) made #16, #33, #36 unpoisonable at 0.25.**

**Limitations.** One detector family (small AE); white-box attacker but very slow optimisation (not real-time); single "retrain on non-alerting data" schedule; magnitudes in normalized units; one dataset; no theoretical guarantees; the robustness conclusion is specific to strongly physics-constrained multivariate data where out-of-range values cannot be made to look normal.

**Implications for AI-agent monitoring.**
- **Direct evidence on baseline poisoning:** an online-updated baseline that only absorbs non-alerting data *can* be dragged, but (i) drift per step is bounded by the alert threshold, so the number of poison steps scales ~linearly with target magnitude and with the size of retained clean history; (ii) attacks that require leaving the support of normal behaviour (SIN_TOP analogue: an action class never seen in benign runs) were not achievable; (iii) **multivariate coupling** (more correlated features) defeats poisoning. For adaptive per-context thresholds on LLM-agent suspicion scores, this predicts: long frozen reference windows + mixing old clean data + multi-feature baselines make boiling-frog attacks expensive.
- **Caveat — not transferable as a guarantee:** robustness here comes from physics (strong structure). LLM-agent behaviour has far weaker structure and the "attacker" generates the very data that defines the baseline over many episodes; a scheming agent has many episodes to drift a per-agent/per-task baseline. Treat this as an *empirical upper bound on attacker difficulty for a highly constrained domain*, not a proof.
- Design rules it supports: don't let flagged or near-threshold data into the baseline; cap per-update drift; keep a frozen, trusted reference set; monitor the drift of the baseline itself (a second-order detector).

---

### 6. Sequential (Quickest) Change Detection: Classical Results and New Directions — arXiv:2104.04186

**Citation.** L. Xie, S. Zou, Y. Xie, V. V. Veeravalli, "Sequential (Quickest) Change Detection: Classical Results and New Directions," arXiv:2104.04186 (Apr 2021); IEEE J. Selected Areas in Information Theory 2(2):494–514, 2021 (as cited in 2601.20022, ref. [19]).

**Gist.** Tutorial survey: the canonical QCD toolkit (Shewhart, CUSUM, SR, Shiryaev, GLR, mixture, EWMA), its optimality theory (Lorden/Pollak/Shiryaev; |log α|/D asymptotics), non-i.i.d. generalisations, ARL approximation, and extensions (transient/moving changes, robust and Byzantine-robust detection, data-efficient, high-dimensional, ML-based).

**Model / assumptions.** i.i.d. f0 before change point γ, f1 after (generalised later to conditional densities f_{0,n}(X_n|X_1^{n−1}), f_{1,n}). Non-Bayesian (γ deterministic) or Bayesian (geometric prior ρ). Adversaries only in the brief robustness section (III-D2: Byzantine sensors).

**Key definitions and results (as stated in the survey).**
- LLR ℓ(X) = log f1(X)/f0(X); E_0[ℓ] = −D(f0‖f1) < 0 pre-change, E_1[ℓ] = D(f1‖f0) > 0 post-change.
- **CUSUM:** W_n = max_{0≤k≤n} Σ_{i=k+1}^n ℓ(X_i) = (W_{n−1} + ℓ(X_n))^+, τ_C = inf{n : W_n ≥ b}. **SR:** T_n = (1+T_{n−1})e^{ℓ(X_n)}, τ_SR = inf{n: T_n ≥ b}. **Shiryaev:** posterior p_n = P(Γ ≤ n | X_1^n), recursion p_{n+1} = p̃_n e^{ℓ}/(p̃_n e^{ℓ} + 1 − p̃_n), p̃_n = p_n + (1−p_n)ρ; equivalently R_{n+1,ρ} = (1+R_{n,ρ})e^{ℓ(X_{n+1})}/(1−ρ); ρ = 0 recovers SR.
- **Metrics:** ARL = E_∞[τ], FAR = 1/ARL; Lorden WADD(τ) = sup_n ess sup E_n[(τ−n)^+ | X_1..X_{n−1}]; Pollak CADD(τ) = sup_n E_n[τ−n | τ ≥ n] ≤ WADD. For CUSUM and SR the sup is attained at n = 1: CADD = WADD = E_1[τ − 1] (cheap evaluation).
- **Optimality:** CUSUM exactly optimal for Lorden's problem (survey refs [132], [170]) — with the W_n = (W_{n−1})^+ + ℓ variant. **Theorem 1 (Lai):** inf_{τ: FAR ≤ α} CADD(τ) ≥ |log α|/D(f1‖f0)·(1+o(1)); CUSUM with b = |log α| attains it: CADD = WADD ∼ |log α|/D(f1‖f0) (first-order). SR with b = 1/α: CADD = |log α|/D + ξ + o(1) (second-order); SRP and SR-r third-order. FAR decays exponentially in delay with exponent D(f1‖f0) (Fig. 2: CADD vs −log FAR slope ≈ 1/D for N(0,1)→N(0.75,1)).
- **Shewhart** (ℓ(X_n) > b) maximises inf_n P_n(τ = n | τ ≥ n) s.t. FAR ≤ α (Pollak–Krieger), uniformly over θ if f_θ/f0 is monotone in a statistic — i.e. it is optimal for catching *one-shot* changes, not for small persistent ones.
- **Theorem 2:** Shiryaev with PFA(τ_S) = α is Bayes-optimal.
- **GLR-CUSUM:** W_n^G = max_k sup_θ Σ_{i=k}^n ℓ_θ(X_i) — not recursive; **window-limited GLR** asymptotically optimal if window chosen as a function of FAR. **Mixture-CUSUM:** replace sup by ∫ω(θ); first-order optimal for practically any prior.
- **Non-i.i.d. (Lai 1998):** generalized CUSUM on conditional LLRs Y_i with b = |log α| is in D_α, and if (1/t) max_{m≤t} Σ_{i=n}^{n+m} Y_i → I a.s. (complete convergence), CADD ∼ WADD ∼ |log α|/I (eq. 24). **Bayesian non-i.i.d. (Tartakovsky–Veeravalli):** Shiryaev with b_α = 1−α: ADD ∼ |log α|/(I + d), d = −lim log P(Γ>n)/n (= |log(1−ρ)| for geometric).
- **ARL approximation by change of measure:** stopping time asymptotically exponential as b→∞ (P_∞{τ ≤ m} ≈ 1 − e^{−λ_b m}, ARL = 1/λ_b); Theorem 3 gives the ARL of a kernel-MMD Shewhart-type procedure (block size B) in closed form — lets thresholds be set without heavy simulation.
- **Transient / dynamic changes:** D-CUSUM, WD-CUSUM (first-order optimal, recursive) for post-change behaviour passing through transient phases; **moving anomaly** (change hops across nodes): HMM-based windowed GLR (first-order optimal) or worst-case-trajectory mixture-CUSUM (exactly optimal with homogeneous sensors).
- **Robustness (III-D):** LFD/JSB minimax approach (Unnikrishnan et al.) — exact under generalized Lorden; asymptotic extension with weaker stochastic boundedness; robust CUSUM via convex optimisation/SDP for covariance uncertainty. **Byzantine:** "raise alarm when two local CUSUMs exceed threshold" (Bayraktar–Lai) and L-of-N / sum-of-L-smallest local CUSUMs for unknown compromised subsets (Fellouris et al.).
- **Data-efficient (DE-Shiryaev / DE-CUSUM):** for Gaussian observations, delay within 10% of Shiryaev with > 50% fewer observations (moderate PFA).
- Sparse multi-stream mixture: Σ_n log(1 − p + p f1(X^(n))/f0(X^(n))) with prior fraction p of affected streams; S-CUSUM (sum of smallest N−η+1 local CUSUMs) for "≥ η nodes affected".
- Distribution-free: MMD, kNN, martingale/LIL-based thresholds (Balsubramani & Ramdas) — the e-process/anytime-valid lineage.

**Practical recipe (from the survey).** Model per-step score distributions under benign (f0) and attack (f1 or family f_θ); run CUSUM on the LLR with b ≈ |log α| (ARL ≈ 1/α, first-order; refine b by simulation or change-of-measure approximation since CUSUM/SR run lengths are ~exponential); evaluate delay at change at n = 1; use GLR/mixture/window-limited GLR if f1 unknown; use conditional LLRs for dependent data; use Shewhart in parallel for single-step catastrophic actions.

**Empirical results.** Illustrative only: N(0,1)→N(0.1,1) with change at 500: CUSUM threshold b = 2 gives delay 60; b = 1 causes a false alarm at k = 112 (Fig. 1). Fig. 2 slope ≈ 1/D. Solar-flare example: mixture procedure catches a flare at t = 142 missed by sum-of-CUSUMs.

**Limitations.** Survey — results are cited, not proved; adversarial treatment is thin (only Byzantine sensors); no treatment of a change-maker who adapts to the detector state or controls the post-change law.

**Implications for AI-agent monitoring.**
- The fundamental law to respect: **delay ≈ |log α| / I**, where I is the per-step KL information (drift) of the monitor score under attack. An attacker who controls I controls delay linearly; there is no detector that beats this for a given I (Lai's lower bound, also non-i.i.d.). Doubling the ARL costs only ~ln 2 / I extra steps — false-alarm budget is cheap, information per step is expensive.
- Shewhart (per-step threshold) is the right tool for single catastrophic actions; CUSUM/SR for low-and-slow; run both. Monitoring of scheming agents should be **multi-chart**.
- Transient/moving-anomaly results matter: an agent that switches attack modes or spreads activity across tools/subagents is a "moving anomaly"; mixture/HMM-GLR variants exist with optimality guarantees for fixed (non-adaptive) trajectories.
- Non-i.i.d. theory (conditional LLRs) is what applies to agent trajectories where step scores are autocorrelated; naive i.i.d. CUSUM thresholds will miscalibrate ARL.
- Window-limited GLR and mixture statistics are the standard composite-alternative answers; e-process/LIL-based thresholds give anytime-valid control without distributional modelling.

---

### 7. Quickest Change Detection in Continuous-Time in Presence of a Covert Adversary — arXiv:2509.17778

**Citation.** A. R. Ramtin, P. Nain, D. Towsley, "Quickest Change Detection in Continuous-Time in Presence of a Covert Adversary," arXiv:2509.17778 (Sep 2025); IEEE Signal Processing Letters 2025 (per the companion paper's reference list).

**Gist.** If the adversary shrinks the post-change Brownian drift µ(γ) as the false-alarm constraint γ (= required ARL) grows, the CUSUM's optimal worst-case delay n(γ) leaves the classical (2/µ²)log γ regime; once γµ(γ)² stays bounded, n(γ) = Θ(γ) ("covert": detection no faster than a false alarm), and the adversary's total damage µ·n(γ) is maximised at µ = Θ(1/√γ), giving Θ(√γ).

**Model / assumptions.** dZ_s = dW_s for s ≤ t, µ ds + dW_s for s > t (unit-variance Brownian motion; change time t unknown, non-Bayesian). Lorden criterion J(T) = sup_t ess sup E_t[(T−t)^+ | F_t], constraint E_∞[T] ≥ γ. **The detector knows µ** and uses the optimal CUSUM for it: T_h = inf{s: Y_s ≥ h}, Y_s = U_s − inf_{r≤s} U_r, U_s = µZ_s − µ²s/2. **Adversary** knows γ (and hence the threshold) and chooses a constant post-change drift µ(γ) > 0 with µ(γ) → 0; it does not adapt within a run.

**Main results.**
- Classical closed forms: E_∞[T_h] = (2/µ²)(e^h − h − 1), E_0[T_h] = (2/µ²)(e^{−h} + h − 1); worst case at t = 0 so n(γ) = E_0[T_h].
- **Lemma 3.1 (optimal threshold):** h(γ) = −1 − ½γµ(γ)² − W_{−1}(−e^{−1−½γµ(γ)²}) (Lambert W, lower branch).
- **Proposition 3.1:** as γ → ∞,
  - n(γ) ∼ (2/µ(γ)²) log(γµ(γ)²) if γµ(γ)² → ∞;
  - n(γ) ∼ (2/θ) G(θ/2) γ if γµ(γ)² → θ ∈ (0,∞);
  - n(γ) ∼ γ if γµ(γ)² → 0;
  with G(x) = e^{1+x+W_{−1}(−e^{−1−x})} − W_{−1}(−e^{−1−x}) − x − 2. Optimal threshold h → ∞, → −1 − θ/2 − W_{−1}(−e^{−1−θ/2}), → 0 respectively. Fixed µ0 ≠ 0 recovers n(γ) ∼ (2/µ0²) log γ.
- **Covertness:** n(γ) = Θ(γ) iff µ(γ)√γ converges to a finite limit.
- Polynomial scaling µ(γ) = γ^{−δ}: n(γ) ∼ 2(1−2δ) log(γ) γ^{2δ} (δ < ½); 2G(½)γ with 2G(½) = 0.563… (δ = ½); γ (δ > ½). Sharp phase transition at δ = ½.
- **Damage** D(γ) = µ(γ)n(γ) ∼ 2(1−2δ) log(γ) γ^δ (δ < ½); 2G(½)γ^{1/2} (δ = ½); γ^{1−δ} (δ > ½) → maximised at δ = ½: **Θ(√γ)**.

**Practical recipe.** Implied design calculation: given a target ARL γ and an estimate of the attacker's achievable per-step drift µ (in noise-SD units), check γµ²: if ≫ 1 the classical log-delay regime applies; if O(1) the detector is no better than its own false-alarm clock. The threshold formula via Lambert W gives exact calibration for Gaussian-increment CUSUM.

**Empirical results.** Numerical evaluation of the exact formulas only. Table I: relative gap M(γ) = 100·|n(γ)−γ|/n(γ) for µ = γ^{−δ}: δ = 0.75: 63.7, 49.4, 41.9, 22.2, 12.2, 6.78, 3.79 at γ = 2, 5, 10, 10², 10³, 10⁴, 10⁵; δ = 2: 24.9, 6.05, 2.12, 0.07, 0, 0, 0; δ = 5: 2.97, 0.04, 0, … Figs. 2–3 show the phase transition at δ = 0.5 and the damage maximiser converging to ½ as γ grows (10⁶–10¹²).

**Limitations.** Brownian motion with unit variance; constant (non-adaptive) post-change drift; the detector is given the true µ (so the result is information-theoretic, not a mismatch effect); asymptotic in γ; damage linear in drift (one choice).

**Implications for AI-agent monitoring.** See combined discussion under the discrete-time paper below.

---

### 8. Quickest Change Detection in Discrete-Time in Presence of a Covert Adversary — arXiv:2601.20022

**Citation.** A. R. Ramtin, P. Nain, D. Towsley, "Quickest Change Detection in Discrete-Time in Presence of a Covert Adversary," arXiv:2601.20022 (v2 Feb 2026), cs.IT.

**Gist.** Discrete-time, general-distribution version: when the post-change law q_γ → q (pre-change) as the ARL constraint γ → ∞, Lorden's n(γ) ∼ log γ / D(q1‖q0) fails; with vanishing overshoots, n(γ) is governed by γD(q‖q_γ): log(γD)/D(q_γ‖q) if γD → ∞, Θ(γ) (covert) if γD = O(1); damage n(γ)·D^ρ is maximised in the transition regime γD = Θ(1), giving Θ(γ^{1−ρ}).

**Model / assumptions.** X_i independent; q (pre) before t, q_γ (post) after; change time unknown constant. Lorden d(T) = sup_t ess sup E_t[(T−t+1)^+ | F_{t−1}], E_∞[T] ≥ γ. Detector: CUSUM τ_h = inf{k: max_j Σ_{i=j}^k log(q_γ/q)(X_i) ≥ h}, **using the true q_γ** — optimal (Moustakides) for this pair, so n(γ) = E_{q_γ}[τ_{h*}] is the best achievable worst-case delay for *any* detector against that q_γ. **Adversary:** knows γ; picks a **stationary** (i.i.d.) post-change law q_γ depending on γ, converging pointwise to q. Key technical conditions (6)–(7): expected overshoots of the underlying SPRT at both boundaries → 0 (sufficient: sup_{y≥0} E_p[Y−y | Y ≥ y] → 0 and inf_{y≤0} E_p[Y−y | Y ≤ y] → 0 for Y = log q_γ(X)/q(X), Lemma 3.2; also implied by q_γ/q → 1 uniformly).

**Main results.**
- **Prop. 3.1 / Lemma 3.1:** under vanishing overshoots, Wald's SPRT approximations become *exact* asymptotically: α ∼ (1−A)/(B−A), β ∼ A(B−1)/(B−A) (A = e^a, B = e^b), E_{q_γ}[T] ∼ [A(B−1)a + B(1−A)b]/[D(q_γ‖q)(B−A)], E_q[T] ∼ −[(B−1)a + (1−A)b]/[D(q‖q_γ)(B−A)].
- **Prop. 3.2 (Khan's approximations exact):** E_{q_γ}[τ_h] ∼ (e^{−h} + h − 1)/D(q_γ‖q); E_q[τ_h] ∼ (e^h − h − 1)/D(q‖q_γ).
- **Prop. 3.3 (main):** with G(y) = e^{1+y+W_{−1}(−e^{−1−y})} − W_{−1}(−e^{−1−y}) − y − 2 (G(y)/y ∈ (0,1), → 1 as y↓0, → 0 as y→∞):
  - n(γ) ∼ log(γD(q‖q_γ)) / D(q_γ‖q) if γD(q‖q_γ) → ∞;
  - n(γ) ∼ [γD(q‖q_γ)/D(q_γ‖q)]·G(y)/y if γD(q‖q_γ) → y ∈ (0,∞);
  - n(γ) ∼ γD(q‖q_γ)/D(q_γ‖q) if γD(q‖q_γ) → 0 (≈ γ when the two KLs are asymptotically equal, as in the Gaussian/exponential cases).
  Corollary 3.1: largest order (covertness, n(γ) = Θ(γ)) reached when γD(q‖q_γ) = O(1).
- **Remark 3.2 (threshold):** h* ∼ log(γD) (γD→∞); −1 − y − W_{−1}(−e^{−1−y}) (γD→y); √(2γD) (γD→0). (Not to be read as the classical h ∼ log γ when q_γ is fixed — conditions (6)–(7) then fail.)
- **Prop. 3.4 (damage):** damage per step g(D(q‖q_γ)) = D^ρ, ρ ∈ (0,1), D(q‖q_γ)/D(q_γ‖q) → c: total damage d(γ) = n(γ)D^ρ is maximised when γD(q‖q_γ) = Θ(1), with d(γ) = Θ(γ^{1−ρ}); o(γ^{1−ρ}) in both other regimes.
- **Gaussian (Prop. 4.1–4.2):** q = N(0,1), q_γ = N(µ, 1+σ²), µ, σ → 0; D ∼ ½µ² + ¼σ⁴ (both directions). n(γ) ∼ log(γ(µ² + σ⁴/2))/(½µ² + ¼σ⁴) if |µ|√γ → ∞ or σ²√γ → ∞; γG(y)/y if ½γ(µ² + ½σ⁴) → y; γ if |µ|√γ → 0 and σ²√γ → 0. **Covert iff mean shift O(1/√γ) and variance shift σ² = O(1/√γ)** (e.g. µ = γ^{−δ1}, σ² = γ^{−δ2}, δ1, δ2 ≥ ½). With g = √· (total mean shift or injected power), max damage Θ(√γ) at µ = Θ(1/√γ) (or σ² = Θ(1/√γ)) — matches Huang–Wang–Poor's covert-communication square-root law.
- **Exponential (Prop. 4.3–4.4):** q = Exp(λ), q_γ = Exp(λ_γ): n(γ) ∼ 2 log(½γ(1−λ_γ/λ)²)/(1−λ/λ_γ)² if √γ|1−λ_γ/λ| → ∞; γG(y)/y if → y; γ if → 0. Covert iff relative rate change O(1/√γ); max damage Θ(√γ).

**Practical recipe.** For a per-step monitor score with benign law q, the attacker's "budget" is the per-step KL D. Compute γ·D for your target ARL γ: if γD ≫ 1, delay ≈ log(γD)/D; if γD ≲ 1, the attack is covert for *every* detector. Calibration: thresholds via Khan's approximation E_q[τ_h] ≈ (e^h − h − 1)/D(q‖q_γ) become exact in the small-signal regime.

**Empirical results.** None (purely analytical; numerical checks in appendices of monotonicity lemmas).

**Limitations.** i.i.d. stationary post-change law (no within-run adaptation, no exploiting detector state, no intermittent bursts); detector given the true q_γ (results therefore *lower-bound* any realistic detector's delay but say nothing about mismatch); asymptotic; overshoot conditions verified only for Gaussian and exponential families; "damage" modelled as a power of KL, not task-specific harm.

**Implications for AI-agent monitoring (both covert papers).**
- **This is the precise statement of "attacker pacing below the CUSUM drift":** classical delay grows with log ARL; a covert attacker who scales per-step distinguishability as D ≈ c/ARL makes delay grow **linearly in ARL itself** (not in log ARL) — detection then happens at essentially the false-alarm clock, and *no detector* can do better (the CUSUM here already knows q_γ and is Lorden-optimal). So for sufficiently subtle per-step behaviour our approach is **provably weak**: no sequential test on a fixed monitor score can separate an attacker whose per-step KL is O(1/ARL).
- **But the same results bound what a paced attacker can achieve:** cumulative "signal" injected before detection is at most Θ(√ARL) in the mean-shift model (Θ(ARL^{1−ρ}) in general). If harmful outcomes require a *total* amount of anomalous action that grows faster than √ARL (in score-SD units), a CUSUM is **provably sound** for those outcomes. This suggests measuring harm per unit of monitor-score shift: the defender wins when harm needs concentrated, high-KL actions; loses when harm can be spread thinly.
- Defensive levers implied: (i) raise per-step D by improving the monitor (KL is the currency); (ii) lower γ (accept more false alarms — only log-cost in the classical regime but linear benefit in the covert one); (iii) aggregate across episodes/instances (independent copies multiply D·n); (iv) bound the attack's useful duration (finite horizon episodes cap n).
- Testable prediction: if a model is told the monitor's ARL/threshold and asked to complete a side task covertly, optimal play is to shrink its per-step suspicion shift ∝ 1/√ARL; measured side-task completion should then scale ~√ARL.

---

### 9. Bistable by Construction: Wall-Clock-Calibrated State Monitors Have No Moment-Detection Regime at Agent Cadence — arXiv:2606.19386

**Citation.** M. Modgil (Modint Intelligence), "Bistable by Construction: Wall-Clock-Calibrated State Monitors Have No Moment-Detection Regime at Agent Cadence," arXiv:2606.19386 (v1 Jun 2026; v2 9 Oct 2026, cs.SE, with erratum). Single-author, non-peer-reviewed; companion to Modgil 2026a (arXiv:2606.04296).

**Gist.** A monitor whose state decays with a wall-clock half-life (EMA baselines, affect models, leaky integrators) sampled once per agent action has only two regimes — constant alarm at fast cadence, permanently silent at slow cadence — with a sharp transition in Δt ∈ (1, 30] s; a sample-time CUSUM over the same stream is exactly cadence-invariant, and a rising-edge trigger with hysteresis avoids saturation at every cadence.

**Model / assumptions.**
- "Wall-clock-calibrated leaky integrator": s′ = decay(s, Δt) + step(event), decay parameterised in seconds, sampled per action. Primary instance: the author's HEART affect engine (18-dim affect vector, decay toward B = 0.10, frustration half-life T½ = 150 s, heuristic observer of 8 rules), trigger A6 "sustained_frustration" fires iff frustration ≥ 0.7.
- Minimal instruments over the raw binary per-action error indicator e_i: **I1** s_i = clamp01(s_{i−1}e^{−λΔt} + 0.15e_i), λ = ln2/150, level trigger 0.7, edge trigger with hysteresis 0.7/0.5; **I2** sample-time CUSUM g_i = max(0, g_{i−1} + e_i − 0.10), fire at g ≥ 1.0.
- Data: 20 SWE-bench-Verified trajectories (25–59 actions; public 20250514_aime_coder submission); 5 live runs of a one-tool-call-per-turn loop with gpt-5.4-mini for timing. Pre-registered hypotheses (provenance via file mtimes, not signed commits).
- **No adversary**; the monitored target is "frustration"/error accumulation, not misbehaviour.

**Main results.**
- **Erratum:** the earlier "State Saturation Trap" paper ran with Δt = 0 (decay never applied) — the published trap was a pure accumulator.
- **Uniform-cadence sweep (Table 1):** fraction of trajectories crossing 0.7 — Δt = 0: 20/20 (persistence 100%, trap holds 20); 1 s: 20/20 (100%, 20); 5 s: 19/20 (93.4%, 17); 15 s: 14/20 (63.4%, 2); 30 s: 5/20 (15.6%, 0); 60 s: 1/20 (2.6%, 0); ≥150 s: 0/20. Level-trigger fire counts (min/median/max): 5/18/47 at 0 s → 0/4/28 at 15 s → 0/0/5 at 30 s → 0 at ≥150 s; edge trigger T3: ≤ 2 everywhere. Every trajectory's critical Δt in (1, 30] s.
- **Measured cadence** (n = 65 inter-action gaps): median 1.53 s, p90 2.33 s, max 15.87 s; 3.1% > 5 s, none > 30 s; lag-1 autocorrelation 0.033 → measured deployment sits in the constant-alarm regime. (Erratum: measured with a scriptable gpt-5.4-mini loop, not a Claude Code hook; a companion paper finds a production harness with frontier models slower, and short sessions there were evidence-starved rather than trapped.)
- **Within-run stability:** with real ordered latency bursts, 19/20 clean single-crossing; exploratory in-band time-scaling: 9/20 multi-cross (≤ 4 crossings).
- **Class-level:** I1 reproduces the cliff (20/20 trap at Δt = 0; 0/20 crossings at Δt ≥ 60 s); **I2 CUSUM identical fire sets at all nine Δt values on all 20 trajectories (26 fires)**. (Reported ρ = 0.530 cross-instrument correlation retracted in v2 as uninformative.)
- **Scaling rule:** trap iff r ≥ (1 − 2^{−Δt/T½})(θ − B) → critical Δt = −(T½/ln2)·ln(1 − r/(θ−B)); predicts 5.6–13.4 s, right order of magnitude, but only 8/20 inside observed intervals.
- **Triggers:** rising-edge with hysteresis (T3) fires 0–3 times per trajectory in every condition and once in the live run (A6 true on 25/32 actions); velocity trigger mostly escapes (2–27% post-saturation fire rate); acceleration trigger never fires (mis-scaled); plateau trigger degenerates (26–88%). No trigger matches human intervention timing (2/9 overlap, attributed to chance; annotator agreement α = +0.047 in the prior paper).

**Practical recipe.** Calibrate monitor dynamics in **sample (action) time**, not wall-clock time — or explicitly log inter-action latency and compute r·T½ vs (θ − B); prefer change/transition detection (CUSUM, rising-edge with hysteresis/Schmitt trigger) over level thresholds on accumulated state.

**Empirical results.** As above (all numbers exact from the paper).

**Limitations.** Very small n (20 trajectories, 5 timing runs, 1 human-labelled trajectory); heuristic affect engine; target ("frustration", intervention timing) is not misbehaviour; several hypotheses failed or were revised; single author, provenance by mtimes; v2 retracts/narrows several v1 claims.

**Implications for AI-agent monitoring.**
- **Practical design constraint for our detectors:** any EMA/adaptive baseline or decaying evidence accumulator with a wall-clock half-life will behave qualitatively differently across harnesses (fast tool loops vs human-gated loops). Our CUSUM/SPRT/e-process statistics should be indexed by **action/step count**, and any adaptive (CFAR) baseline's forgetting factor should be per-step or per-episode, not per-second.
- **Adversarial angle (our inference, not in the paper):** if a wall-clock decay is used, a monitored agent can control its own cadence (e.g. pausing, long reasoning, slow tool calls) and thereby drain the statistic — a trivially available evasion knob. Sample-time statistics remove it, though an agent can still dilute evidence by interleaving benign steps (which is the covert-adversary regime).
- Level-on-accumulated-state triggers saturate; for alerting, fire on transitions with hysteresis and refractory periods (this concerns alert UX, not detection power).

---

### 10. A Framework for Evaluating and Benchmarking Concept Drift Detection Methods — arXiv:2606.07789

**Citation.** V. Cerqueira, H. M. Gomes, M. Heyden, B. Pfahringer, A. Bifet, "A Framework for Evaluating and Benchmarking Concept Drift Detection Methods," KDD '26 (Jeju, Aug 2026); arXiv:2606.07789 (Jun 2026). Code: github.com/vcerqueira/experiments-drift_evaluation (CapyMOA).

**Gist.** A benchmarking protocol for streaming drift detectors: inject controlled drifts at random points into shuffled real datasets (Monte Carlo), score with timing-aware detection windows (precision/recall/F1, episode recall, normalized detection time, false-alarm rate), and tune hyper-parameters by leave-one-dataset-out; SEED, STEPD and ABCD come out most robust, CUSUM/PH/EWMA (as implemented on classifier error streams) poorly.

**Model / assumptions.** Data stream of (X_t, y_t) ~ p_t; drift = (d_s, d_e), width w = d_e − d_s (abrupt w = 0; gradual: transformed with probability (t − d_s)/w). Detectors mostly monitor a Hoeffding-tree classifier's per-instance error (prequential, immediate labels); ABCD(X) monitors features; STUDD monitors a student–teacher compression loss. **No adversary.** Original streams are shuffled to destroy pre-existing drift (and temporal dependence).

**Main results / definitions.**
- Acceptable detection window [d_s − δ_pre, d_e + δ_max] (δ_pre = 0 for injected drifts); TP = alarm in window; FN = no alarm in window; FP = alarm outside any window; TN undefined.
- Metrics: Precision, Recall, Episode Recall (multiple alarms in one window count once), F1, **Normalized Detection Time** NDT = mean (detection − d_s)/δ_max over detected drifts, Alarm Rate and **False Alarm Rate** = FP/total instances × F. Rationale: Bifet's MTFA/MDT/MDR depend on stream length and drift spacing.
- Four drift generators: class prior (drop class y_sel w.p. p_skip), label swap (y_sel → y_swap), feature permutation (fixed random σ), feature filtering (drop instances with x_j > τ = pre-drift median).
- **Leave-one-dataset-out HPO:** 30 random-search iterations on the other 6 datasets, optimise F1.
- Findings: (1) SEED and STEPD most consistent (top-3 in most scenarios); ABCD best FAR among accurate detectors. (2) Gradual drift systematically harder. (3) Unsupervised feature-space detectors catch feature drifts but not label-only drifts. (4) HPO helps most detectors (more for abrupt), not SEED; PH and EWMA stay poor regardless.

**Empirical results (exact numbers).** 7 datasets (Asfault 8,563 samples; Covtype 100,000; Electricity 45,312; GasSensor 13,910; NOAA 18,159; Posture 100,000; Rialto 82,250), 50 Monte Carlo trials each, drift onset uniform in 50–80% of length, max delay = drift width = 500–2,500 by dataset, 14 detectors.
- Average F1 rank, abrupt (feature filtering / feature permutation / class prior / class swap): SEED 4.4/2.7/3.9/1.1; STEPD 3.4/3.7/4.3/2.4; ABCD 8.1/3.9/8.0/3.6; ABCD(X) 12.7/1.0/13.1/13.1; ADWIN 4.1/7.6/4.1/7.1; **CUSUM 5.6/11.9/6.1/9.2**; PH 13.1/12.9/11.6/10.1; EWMA 9.7/12.9/9.4/10.9.
- Gradual: SEED 5.9/2.7/5.0/1.9; STEPD 5.4/2.8/5.2/2.0; GMA 3.9/6.6/6.1/4.7; CUSUM 6.3/11.9/7.3/9.7; PH 10.9/12.4/9.7/11.1.
- Average F1 (abrupt): SEED 0.24/0.61/0.30/0.37; STEPD 0.26/0.53/0.28/0.33; ABCD(X) 0.02/0.98/0.0/0.0; ADWIN 0.24/0.27/0.31/0.16; CUSUM 0.19/0.01/0.22/0.10; PH 0.02/0.0/0.06/0.09; EWMA 0.09/0.0/0.06/0.03. Absolute F1 values are low overall.
- GMA/RDDM are recall-dominated (recall 0.97–1.0, precision ~0.05–0.08) — i.e. near-constant alarms.
- Classifier sensitivity (Electricity, label swap): rankings stable across ARF/HT/NB/OnlineBagging/OzaBoost; absolute F1 varies (OzaBoost highest, e.g. SEED 0.82, PH 0.78, CUSUM 0.6 vs CUSUM 0.1 with HT).
- Synthetic (Agrawal/SEA/STAGGER): SEED/ABCD/STEPD best (e.g. SEED abrupt 0.58/0.46/0.35).

**Limitations.** One base learner in main study; immediate labels; shuffling removes temporal structure; one drift per run; only 4 drift types, no incremental drift; non-adversarial drifts; CUSUM/PH used as generic error-rate detectors with library defaults/search spaces, not likelihood-ratio CUSUMs tuned to a known post-change law; FAR measured per instance, not as ARL.

**Implications for AI-agent monitoring.**
- **Evaluation methodology transfers directly:** inject synthetic "attack segments" at random onsets into real benign agent trajectories (Monte Carlo), score with acceptable-window TP/FP, report NDT + episode recall + FAR, and tune detector hyper-parameters leave-one-*environment*-out to avoid overfitting thresholds to one task suite. This is the right harness for comparing CUSUM vs GLR vs e-process vs CFAR baselines on monitor-score streams.
- Gradual drift (probabilistic interleaving of transformed samples) is exactly the "mixing benign and malicious steps" pacing strategy; the benchmark confirms it is systematically harder for all detectors.
- Caution: "CUSUM performs poorly" here is about a nonparametric error-rate CUSUM with generic hyper-parameters on classifier errors; it does not contradict CUSUM's optimality when the LLR of a calibrated monitor score is available. Report this distinction when citing.
- Detectors with recall ≈ 1 and precision ≈ 0.05 (GMA, RDDM) illustrate why FAR/ARL must always be reported alongside recall.

---

### 11. How to Sustainably Monitor ML-Enabled Systems? Accuracy and Energy Efficiency Tradeoffs in Concept Drift Detection — arXiv:2404.19452

**Citation.** R. Omar, J. Bogner, J. Leest, V. Stoico, P. Lago, H. Muccini, "How to Sustainably Monitor ML-Enabled Systems? Accuracy and Energy Efficiency Tradeoffs in Concept Drift Detection," arXiv:2404.19452 (Apr 2024). Replication package: doi 10.5281/zenodo.10613150.

**Gist.** Controlled full-factorial experiment on the seven scikit-multiflow drift detectors (default configs) measuring detection accuracy and energy (detector + retraining): KSWIN is most accurate on abrupt drift but most energy-hungry; HDDM_W and ADWIN are balanced; Page-Hinkley, DDM, EDDM, HDDM_A are cheap but nearly useless (<10% true-alarm rate).

**Model / assumptions.** Error-based detectors fed (prediction, true label) per instance (immediate labels); synthetic streams (Lobo's Harvard Dataverse generators: sine, stagger, mixed, sea, RT), each with 3 drifts that reverse P(Y|X) (abrupt at 10k/20k/30k of 40k; gradual width 1,000 starting 9.5k/20k/30.5k of 41k). Base classifier trained on first 8.5k instances; detection stops at the first alarm; then retrain. 7 detectors × 5 datasets × 2 drift types × 6 classifiers = 420 combinations, 10 repetitions each; energy via CodeCarbon (RAPL). (The paper lists the classifiers inconsistently — NB, SVM, DT, KNN, RF, AdaBoost, Bagging in one place; SVM, Hoeffding Tree, KNN, RF, AdaBoost, Bagging in another.) **No adversary.** True alarm = first alarm within [start of new concept, end of concept]; earlier = false alarm.

**Main results (exact).**
- Energy (Table I; mean per run as reported, Mann-Whitney U with Holm-Bonferroni, all pairs significant): KSWIN 0.0181, ADWIN 0.0091, EDDM 0.0060, HDDM_W 0.0060, DDM 0.0059, HDDM_A 0.0058, PageHinkley 0.0055. KSWIN vs PageHinkley +69.8% (Cohen's d 7.53); KSWIN vs ADWIN +49.4%.
- Accuracy (Table II; 300 runs per detector × drift type; true/false/missed; true-alarm %; mean detection closeness for true alarms, 1 = immediate):
  | Detector | Drift | True | False | Missed | True % | Closeness |
  |---|---|---|---|---|---|---|
  | KSWIN | abrupt | 279 | 21 | 0 | 93.0 | 0.998 |
  | HDDM_W | gradual | 180 | 120 | 0 | 60.0 | 0.838 |
  | HDDM_W | abrupt | 179 | 121 | 0 | 59.7 | 0.873 |
  | ADWIN | gradual | 175 | 118 | 7 | 58.3 | 0.830 |
  | KSWIN | gradual | 171 | 129 | 0 | 57.0 | 0.804 |
  | ADWIN | abrupt | 152 | 136 | 12 | 50.7 | 0.843 |
  | HDDM_A | gradual | 24 | 243 | 33 | 8.0 | 0.734 |
  | PageHinkley | abrupt | 23 | 259 | 18 | 7.7 | 0.849 |
  | HDDM_A | abrupt | 21 | 240 | 39 | 7.0 | 0.679 |
  | PageHinkley | gradual | 19 | 252 | 29 | 6.3 | 0.779 |
  | DDM | gradual | 18 | 240 | 42 | 6.0 | 0.679 |
  | DDM | abrupt | 10 | 252 | 38 | 3.3 | 0.711 |
  | EDDM | gradual | 4 | 223 | 73 | 1.3 | 0.435 |
  | EDDM | abrupt | 2 | 242 | 56 | 0.7 | 0.365 |
- Drift type and energy (Table III): EDDM gradual +8.3% (d 0.77), KSWIN +4.0% (d 0.32) significant; others not.
- Base classifier: no significant Spearman correlation with detector energy or closeness (min p = 0.122).

**Practical recipe.** For error-stream drift monitoring: HDDM_W as an energy-cheap balanced default; KSWIN when abrupt drift must be caught fast and compute is cheap; avoid default-config PH/DDM/EDDM/HDDM_A. Account for retraining cost triggered by false alarms ("false alarms are much worse than missed alarms" from a Green-AI perspective).

**Limitations.** Synthetic data only; default hyper-parameters (no tuning — contrast 2606.07789, where tuning matters); stop-at-first-alarm protocol makes "false alarm" = premature first alarm (dominant failure for PH/DDM); immediate labels; energy differences are tiny in absolute terms; small classical classifiers only; minor internal inconsistencies in the text.

**Implications for AI-agent monitoring.**
- Mostly operational: per-step monitoring cost matters at scale (many agents × many steps), but here detector compute is negligible relative to the cost of acting on false alarms (retraining there; human audits for us). The analogous budget for AI control is the **audit budget**, which makes FAR/ARL the binding constraint.
- Reinforces that off-the-shelf error-rate drift detectors with default parameters can have high premature-alarm rates (PH 259/300 false first alarms on abrupt drift) — thresholds must be calibrated to a target ARL on benign data, never left at library defaults.
- No adversarial content; no implications for pacing/poisoning beyond "gradual drift changes behaviour non-uniformly across detectors".
