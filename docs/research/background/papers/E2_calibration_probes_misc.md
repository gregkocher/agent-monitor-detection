# Cluster E2 — Monitor calibration & transfer, probes / white-box monitors, CoT monitoring, structural/containment monitoring, misc (reading cards)

Read in full (pdftotext of arXiv PDFs), 2026-10-20. Ten papers:
2607.06596 (Pinto, calibration-family overfit) · 2606.06223 (Wilhelm & Kao, context-calibrated reward-hack probes in agents) · 2606.11998 (Xiao & Phuong, bootstrapped monitoring) · 2607.14570 (Ravindra et al., IFG structural monitor) · 2608.09087 (Nagaraj, joint Lyapunov certificates) · 2604.23425 (Mitchell, containment requirements) · 2502.03407 (Goldowsky-Dill et al., deception probes) · 2503.11926 (Baker et al., CoT monitoring & obfuscation) · 2410.20247 (Gao et al., model equality testing) · 2412.13678 (Tamkin et al., Clio).

Evidence quality varies: 2607.06596, 2502.03407, 2503.11926, 2410.20247, 2412.13678 are substantial empirical work; 2606.11998 is a solid MATS preprint; 2606.06223 and 2607.14570 are workshop papers with small positive counts; 2608.09087 (toy linear SDE, internally inconsistent in places) and 2604.23425 (patent-motivated position paper, no data) should be cited only for framing.

## Cluster synthesis

**1. Operating points do not transfer across contexts or model families — the strongest, most directly relevant finding.** Pinto (2607.06596) is the key paper: a 1%-FPR threshold set on one policy family's benign transcripts yields realized audit spend of **0% to 94% (mean 27%)** on another family, and for a fixed-prompt gpt-4.1-mini monitor a 1% operating point "does not exist" for 3 of 4 open families because benign scores saturate at the ceiling. The same pattern recurs with white-box scores: Goldowsky-Dill et al. (2502.03407) calibrate a deception probe to 1% FPR on Alpaca chat, and honest responses in deception-related scenarios routinely exceed that threshold; Wilhelm & Kao (2606.06223) find the same SAE reward-hack probe has Control-adapter means of 0.495 (Qwen) vs 0.005 (Llama), and that reasoning budget shifts probe distributions non-monotonically; Clio (2412.13678) shows production safety classifiers have topic-specific false-positive clusters (security-adjacent coding, D&D stats, resumes) and false-negative clusters. Small, discrete calibration sets make this worse: Bootstrapped Monitoring (2606.11998) calibrates per (agent, monitor, trusted-model) configuration on ~20% of honest rollouts with integer scores and overshoots the 3% target in 2 of 24 cells (up to 3.9%); IFG (2607.14570) sets its 1% threshold from 100 honest episodes with a 1-10 score. **Implication:** per-context / per-family FPR control (CFAR-style, conformal) is well motivated and is essentially unaddressed with guarantees in this literature.

**2. But fixing the operating point does not fix detection power.** Pinto separates two failures. With the FPR held at q on every family (budget-enforced protocol, i.e., what a perfect per-context threshold would achieve), an off-lineage *trained* monitor still catches **19% vs 41%** of attacks at a 1% budget (8 families, leak-free). The cause is concept shift: each lineage's sabotage lies along a different discriminative direction; benign-only mean-shift leaves AUROC unchanged, CORAL makes it worse, and per-input OOD deferral does not beat suspicion-ranked deferral and is consistently worse than random deferral. Recovering ranking needs labeled sabotage from the new lineage (~150+150 examples per cell for ~81%). A benign-drift Mahalanobis detector does flag off-lineage traffic (AUROC 0.836) but cannot size the loss. Our pitch must therefore say clearly: CFAR/conformal normalization controls false alarms and audit spend across contexts; it does not by itself restore TPR for trained, family-conditioned monitors. Notably, the prompted monitors most deployers use showed no family-specific *ranking* effect (they failed the competence gate instead), so for them the problem is mostly operating-point shift, where per-context calibration is exactly the remedy.

**3. Nobody here runs a principled sequential test over per-step agent scores.** Aggregation in this cluster is ad hoc: max over steps (Bootstrapped Monitoring), mean/max/ReLU-mean over tokens (deception probes; they document "aggregation failures" when only part of a response is deceptive), per-step independent logistic regression (Wilhelm), end-of-trajectory scores (Pinto), binary whole-trajectory labels (Baker). The closest thing to a sequential argument is Bootstrapped Monitoring's rollout-length effect: a stable ~30% per-step leak rate from a colluding monitor's CoT drives catch from ~60% to ~95% beyond 30 steps, with honest per-step flag rate ~0% and FPR only checked empirically by length bin. Nagaraj (2608.09087) sketches a CUSUM on a Lyapunov residual for a toy SDE without ARL analysis, and Mitchell (2604.23425) calls qualitatively for "sequential intent inference" (including rejected tool calls). Gao et al. (2410.20247) provide the cleanest Type-1-controlled test in the cluster (MMD two-sample tests, simulated/permutation nulls, composite nulls, Bonferroni) but only in batch form. **Opening:** CUSUM/SPRT/e-processes over per-step monitor and probe scores, with per-context calibrated nulls and explicit FPR/ARL guarantees across agent families, plus an anytime-valid version of model-equality/behavior-drift testing.

**4. Aggregating across sessions/entities is validated in practice but not statistically.** Clio finds coordinated abuse where "none of the individual conversations violated our Usage Policy," but via semantic clustering and human review, with no false-alarm control, and it explicitly "is not useful for identifying rare (but possibly very consequential) patterns." Nagaraj's toy result (0/10 agents individually flagged; joint statistic fires) illustrates the variance-aggregation logic. Per-entity e-processes for low-volume, cross-session evidence are an open niche.

**5. White-box signals are promising sequential inputs but context-confounded.** Deception probes reach AUROC 0.964-0.999 and 95-99% recall at 1% control FPR, and fire before explicit deceptive text appears; but they partly encode "is this a deception-related scenario," recall at 1% FPR collapses with a two-layer shift, and the settings are blatant. Wilhelm & Kao find the reward-hack probe is a "latent policy state" whose mapping to the next action is non-monotone (Mix50 adapter exploits at 0.450 with lower mean activation than the Hack adapter at 0.019) and shows no universal pre-action rise. Baker et al. argue activations complement CoT because CoT monitors miss superficial hacks. Any CUSUM over raw probe scores would false-alarm on benign-but-risky contexts unless baselines are context-conditional.

**6. Monitor-aware adversaries degrade every signal.** Training against a CoT monitor drives its recall to ~0 while hacking continues (Baker); automated red-teaming of a colluding monitor's prompt cuts trusted detection to ~20% (as low as 4%) on short 10-step rollouts but fails on ~38-step rollouts (Bootstrapped Monitoring); Clio withholds its k because attackers could size coordinated activity below cluster formation; IFG's LLM stage remains prompt-injectable. Pinto deliberately studies only passive shift. Sequential accumulation helps most when trajectories are long and the per-step signal is not itself optimized against; it does not rescue a signal that training pressure has driven to zero.

**What undermines or constrains our ideas:** (i) Pinto: threshold normalization cannot recover ranking loss for trained monitors under lineage shift; benign-only adaptation is provably useless for ranking in their setup. (ii) Baker: optimized-against signals become uninformative; keep detectors out of the training loop and fuse signals with different attack surfaces. (iii) Goldowsky-Dill/Wilhelm: probe baselines move with context, so context normalization must use honest-in-context references, or it can normalize away real signal in exactly the risky contexts. (iv) Bootstrapped Monitoring's raw-CoT dependence: summarized CoT (closed APIs) collapses CoT-leak-based accumulation.

**Most reusable assets:** Pinto's code and aggregate matrices (github.com/digdoug/calibration-family-overfit) for testing per-family calibration methods; Apollo's deception-detection code and probe outputs; Gao et al.'s model-equality package and 1M+ completion dataset (a base for anytime-valid drift tests); Bootstrapped Monitoring's per-step, per-configuration setup on BashArena as a testbed for sequential tests vs max aggregation.

---

# Paper cards

## 1. Calibration-Family Overfit (arXiv 2607.06596)

**Citation.** Lucas Pinto (independent). "Calibration-Family Overfit: Why Trusted Sabotage Monitors Don't Transfer Across Lineages." arXiv:2607.06596 (v1 2026-07-06; read v3, 25 Aug 2026), cs.CR.

**Gist.** A trusted sabotage monitor fit on one untrusted-policy family's transcripts ranks that family's sabotage much better than another family's, even after removing attacker-obviousness (column) and monitor-capability (row) main effects; at a 1% audit budget off-lineage catch rate is roughly half of in-lineage.

### Setup
- Substrate: ControlArena code-backdoor settings: APPS (primary) and BigCodeBench (replication); SHADE-Arena as non-code, underpowered check. Honest vs attack mode on identical task IDs. Task IDs split 60/40 calibration/test by fixed hash, shared across families (calibration 368 / test 232 tasks at n=600).
- Policy families: 4 open-weight (Qwen3-14B think-off, Gemma-3-27B, Mistral-Small-3.2-24B, Llama-3.3-70B, via DeepInfra), later 5 frontier (Claude Sonnet 4.6, Gemini 2.5 Flash, Grok-4.3, GPT-5, DeepSeek-V3.2). n=600 per family per mode before attrition.
- Monitors (three classes): (a) fixed-prompt gpt-4.1-mini scoring end-of-trajectory transcript ("Track 1" baseline); (b) "Track 2" family-conditioned: text-embedding-3-small -> StandardScaler -> 50-comp PCA -> per-calibration-family logistic head (C=1.0); (c) LoRA sequence classifiers per family (Phi-3.5-mini, Phi-4-mini, Phi-4 14B, Yi-1.5-34B), plus per-family SFT of gemini-2.5-flash on Vertex; also six prompted family-conditioned constructions (few-shot, rubric-distilled + CoT, retrieval-augmented kNN in context).
- Measured: N x N cross-family AUROC matrix M[A,B] (calibrate on A, evaluate on B), decomposed M = grand_mean + row_A + col_B + interaction; headline = mean diagonal interaction. CIs: task-clustered bootstrap (1000 draws). Also a placement-value regression with task fixed effects (diagonal coef +0.171 [+0.158,+0.184], invariant to added controls). Primary metric is detection of attack *attempts* (unfiltered), because both-success backdoors are near zero for open families.

### Calibration / thresholding details
- Two tracks: Track 1 sets threshold at the 1%-FPR point on family A's *benign* calibration transcripts and applies to family B (TPR reported). Track 2 = AUROC matrix for monitors whose scores depend on calibration family.
- Fixed-prompt monitor Track-1 diagonal bonus is null at 0.5%, 1%, 5% thresholds (it has no family-dependent ranking).
- **Static-threshold transfer failure:** a threshold calibrated on family A, shipped to B, yields realized audit spend on B from **0% to 94% (mean 27%) against a 1% target**, "because each family's benign score distribution sits in a different place. The operating point itself is family-specific." On SHADE the static-threshold failure replicates: off-lineage audit spend 0 to 8.6% vs 1% target.
- Fixed-prompt monitor: benign score distribution saturates at the score ceiling for 3 of 4 open families, "so a 1% operating point does not exist for them."
- Budget-enforced protocol (audit top-q% of live stream) holds realized FPR at q by construction (verified 1.3% at q=1%, range 1.2-1.4%), isolating ranking failure.
- Benign-only recalibration cannot help: mean shift leaves AUROC exactly unchanged (linear head translation-invariant); CORAL recovers <2% of gap and is negative on 4 families (-0.008 full, -0.011 action-only); on nine families CORAL recovery is -0.24 of the gap [-0.30,-0.20].
- Off-lineage *detection* from benign drift works: squared Mahalanobis distance to calibration family's benign cloud separates in- vs off-lineage benign at mean AUROC 0.836 (full) / 0.681 (action-only). But it does not predict the size of transfer drop (pooled LOFO -0.06). Benign two-sample-classifier distance also fails to predict drop out-of-family (Spearman ~0).
- Per-input OOD deferral does not beat suspicion-ranked deferral and is worse than random; OOD score's attack-vs-benign AUROC on new family = 0.55.
- Labeled recalibration: 150 attacks + 150 benign per cell recover ~81% of gap (full), 58% (action-only); ~300 needed for 90%. Difference-of-means probe from m labeled pairs recovers ~half the gap at m~10.
- Pooling: up to 7 foreign families gives +0.031 [+0.023,+0.040], plateaus by ~3 families, recovers ~1/5 of gap (0.685 vs own-family ceiling 0.825); action-only pooling benefit vanishes under strict basis. Routing to nearest family by benign-centroid cosine: 0.539->0.616 (4 fam), vanishes at 5 fam, 0.657 vs 0.625 baseline at 6 fam; hurts 3 of 6 held-out families.

### Key quantitative results
- 4 open families: mean diagonal AUROC 0.71 vs off-diagonal 0.57; interaction +0.110 [+0.094,+0.125] transductive; **+0.172 [+0.158,+0.185] leak-free (primary)**. Label-shuffle null -0.001; random pseudo-family split null +0.000 [-0.012,+0.012].
- Mistral head on Mistral 0.97; Qwen head on Llama 0.42 (below chance).
- Leak-free interaction by roster: 5 fam +0.194, 6 fam +0.195, 8 fam +0.197 [+0.188,+0.206], 9 fam +0.194; transductive 8 fam +0.150 [+0.142,+0.157] (exact permutation p=0.000025 over 40,320 matchings); 9 fam p=0.000003.
- Frontier-only (4 vendors): +0.103 full / +0.135 action-only; 5 vendors +0.100 / +0.164.
- BigCodeBench leak-free +0.233 full, +0.099 code-only. SHADE +0.035 [-0.004,+0.077] (7 test tasks; MDE +0.054).
- LoRA: +0.179/+0.204/+0.194 across seeds; 34B: +0.166, +0.163. Gemini-2.5-flash SFT: +0.100 [+0.063,+0.134].
- Prompted family-conditioned monitors all fail to rank Llama above chance (e.g., retrieval-augmented gpt-4.1 diagonal 0.381), though the kNN scorer over the same retrieved vectors gives Llama 0.729 and interaction +0.130.
- Realized safety at 1% audit (budget-enforced): leak-free 4 open 18% vs <2% (gap +16.9); 8 fam **41% vs 19% (+21.7 [+19.7,+26.7])**; 9 fam 47% vs 22% (+24.8). Transductive 8 fam 42% vs 24% (+18.4). Gap monotone in budget (5%: +29.0 leak-free at 8 fam).
- Capability gap: Sonnet-calibrated head 0.92 on Sonnet; open-family heads average 0.73 (gap +0.189); 47% vs 24% catch at 1%. Weak-to-strong transfer 0.64 vs strong-to-weak 0.54; capability gap correlates +0.21 with off-diagonal AUROC (wrong sign for capability story).
- Mechanism: cos(w_A, w_B) predicts transfer AUROC (Spearman +0.56 4-open; +0.80 8/9-fam; partial rho +0.78 after main-effect residualization); rotating head halfway toward B recovers 86% of gap (9 fam); random rotation recovers 0.
- Blatancy matching (dominant confound): leak-free +0.133 (proxy #1 fixed-prompt suspicion band), +0.176 (proxy #2 Haiku grade); transductive +0.045. Action-only + blatancy-matched: +0.046, concentrated in subtle stratum (+0.075), null on blatant.
- Benign transcripts are family-separable: 4-way classifier 0.656 accuracy (2.6x chance) on APPS; 1.2x chance on SHADE.

### Limitations / future work (verbatim)
- "We deliberately study passive distribution shift, not adaptive attack."
- "A residual calibration finding remains: the fixed-prompt monitor supports a 1% operating point only for Mistral; for the other three families the benign score distribution saturates at the score ceiling, so a 1% operating point does not exist for them, a sharper form of the claim that the operating point is family-specific."
- "If, instead of re-ranking the live stream, the blue team ships a static threshold calibrated on family A, the protocol does not even hold its audit budget off-lineage ... The operating point itself is family-specific."
- "a deployer can tell they are off-lineage but cannot cheaply close the gap, so a control evaluation cannot substitute family resemblance or benign-traffic recalibration for a measured cross-family transfer matrix built from real sabotage in each lineage."
- "no tested method is reliable per-family, so the primary recommendation remains to report cross-family transfer matrices and to calibrate per-family wherever the deployed lineage is known; a robustly general family-adaptive defense is open."
- "We keep the broad framing in the title but scope the established claim to trained, family-conditioned monitors and report the prompted-monitor shortfall ... as a characterized limitation."
- Realized-sabotage matrix not powerable (5 of 8 families have 0-1 successful-backdoor test positives).

### Data / code
Analysis code + aggregate results: https://github.com/digdoug/calibration-family-overfit. Raw transcripts gated under benchmark canary strings. Provenance in configs/provenance.yaml.

### Relevance to our directions
- **Overlap: HIGH** with "calibration of monitor scores across contexts/model families" and CFAR-style per-context thresholds. This is the most direct empirical evidence that (i) a single global threshold is invalid across policy families (realized FPR 0-94% vs 1% target), and (ii) benign-score location differs per family.
- **Supports CFAR/per-context thresholds at the operating-point level** (static thresholds blow up audit budget), but **undermines the hope that benign-only normalization recovers detection**: mean-shift/CORAL fail because the gap is concept shift (rotated discriminative direction), not covariate shift. A CFAR-style per-context threshold fixes FPR (as their budget-enforced protocol does) but not TPR loss from ranking. Our pitch must separate "FPR control" (CFAR solves) from "detection power" (needs labeled sabotage per family).
- Mahalanobis benign-drift detection (AUROC 0.836) is a ready-made "context change" trigger that a sequential/CUSUM changepoint on benign-score statistics could formalize.
- Gap left: no sequential/temporal analysis (end-of-trajectory scores only); no per-step scores; prompted monitors (what most deploy) not established to show the effect because they fail competence; no adaptive attacker; no cross-session accumulation. Their prompted-monitor result is ambiguous for us: zero-shot prompted LLM monitors have no calibration-family *ranking* axis, so the issue for them is purely operating-point (threshold) transfer -- exactly where CFAR-style normalization should help.

---

## 2. From Reward-Hack Activations to Agentic Risk States (arXiv 2606.06223)

**Citation.** Patrick Wilhelm, Odej Kao (TU Berlin / BIFOLD). "From Reward-Hack Activations to Agentic Risk States: Context-Calibrated Mechanistic Monitoring in LLM Agents." arXiv:2606.06223 (v1 2026-06-04; read v2, 15 Jul 2026). ICML 2026 AIWILD workshop paper.

**Gist.** An SAE-based reward-hack activation score transferred into ReAct agent loops is a "latent policy-state descriptor," not a direct action-risk score; next-step risk prediction improves when the activation is combined with token entropy and decision-context features.

### Setup
- Agents: ReAct-style, LoRA adapters (GRPO, rank 32, alpha 32) trained on benign data (Control), School-of-Reward-Hacks data (Hack), or mixtures (Mix05, Mix10, Mix50). Families: Qwen (primary), Llama (secondary), Falcon (appendix "boundary condition"). Exact model sizes are not stated in the main text.
- Environments: "Gameable ALFWorld" (ALFWorld with added proxy-reward affordances: `choose easy grader`, `claim task complete`, `inspect score`) and WebShop.
- Internal signals per reasoning token: (1) reward-hack score h_{t,i} in [0,1] from SAE features (hidden dim 8000) -> standardize -> PCA -> lightweight linear classifier trained on residual-stream activations of Control vs Hack adapters only (reused from Wilhelm et al. 2026, arXiv 2603.04069); (2) next-token entropy H_{t,i}.
- Per-step summaries: mean, final-token value, late-window mean (final 20%), Delta_late = mu_late - mu_early, beta_late = LS slope over final 20%.
- Context features c_t: reasoning budget (TTC 8..256), normalized step position, previous action type, environment identity, proxy-affordance flags / page-state indicators.
- Predictor: logistic regression p_hat_{t+1} = sigma(w^T [z_t, c_t] + b), predicting an environment-defined label y_{t+1} (bad_action, exploit_action; WebShop buy, bad_buy, low_reward_buy) from step-t features. Grouped CV by episode; preprocessing fit on train folds only.
- Metrics: AUROC, AUPRC, AUPRC gain over base rate (primary), Recall@20% (fraction of positives captured when flagging top 20% of steps).
- Steering: subtract alpha * d_hack (contrastive direction at layer l), always-on or gated by a threshold.

### Calibration / thresholding details
- "Calibration" here means conditioning the risk model on context features (a learned logistic combination), not score calibration in the probabilistic sense; no threshold selection procedure, FPR control, or reliability diagrams are reported.
- Only fixed flagging budget reported: Recall@20% (top-20% of steps flagged), which is a very high flag rate relative to control-style 1% audit budgets.
- Per-family behaviour differs strongly: mean reward-hack activation for Control adapters is 0.495 (Qwen) vs 0.005 (Llama) vs 0.075 (Falcon) (Table 6), i.e., the raw probe output lives on very different scales across families; Llama shows zero exploit actions for all adapters.
- Reasoning budget changes monitor distributions and prediction quality "non-monotonically" -> treated as a context variable.
- Gated steering uses "a gating score exceeds a threshold" but threshold value not reported.

### Key quantitative results
- Qwen Gameable ALFWorld, bad_action_{t+1} (N=7322, 3878 positives, base rate 0.530): activation-only AUROC 0.565, AUPRC gain +0.020, R@20 0.197; entropy-only 0.601 / +0.102 / 0.257; internal+context 0.667 / +0.164 / 0.306.
- Qwen exploit_action_{t+1} (184 positives, base rate 0.025): activation-only AUROC 0.769, gain +0.109, R@20 0.679; activation+entropy 0.744 / +0.131 / 0.614; internal+context 0.756 / +0.111 / 0.603. (So for the cleanest reward-hack target, adding context did not help over activation+entropy.)
- Behavioral transfer (Qwen): exploit rate Control 0.003, Mix05 0.007, Mix10 0.049, **Mix50 0.450**, Hack 0.019; mean activation Mix50 0.894 vs Hack 0.966 -> most saturated internal state is not the most exploitative ("non-monotonicity").
- Steering (always-on alpha=0.25): proxy reduction Mix05 0.8, Mix10 2.0, Mix50 2.2; gated "more selective and not uniformly effective."
- WebShop (activation+entropy only): Qwen buy AUROC 0.648 / gain +0.112; Llama buy 0.790 / +0.092; Falcon buy 0.909 (10 positives).
- Temporal diagnostics "do not support a universal claim that reward-hack activation always rises before risky actions."

### Limitations / future work (verbatim)
- "agentic safety monitoring cannot be reduced to thresholding a single internal feature."
- "Effective agent monitoring therefore requires context-calibrated risk estimation rather than thresholding a single internal feature."
- "effective deployment would require context-aware gating and environment-specific calibration."
- "The main limitation is scope ... Prediction and steering effects are not uniform across adapters, environments, or reasoning budgets. Finally, our context features are simple; richer state representations and online gating policies are important next steps."
- "test-time compute should be treated as part of the monitoring context rather than as a uniformly beneficial or harmful intervention."

### Data / code
No code or data release stated. Appendix B ("Calibrated Context Prediction Logistic Regression") is an empty heading in the arXiv text. Monitor construction reused from arXiv 2603.04069.

### Relevance to our directions
- **Overlap: MEDIUM** with "white-box (probe) signals as sequential inputs" and "per-context calibration." It is the only paper in this cluster that feeds a probe score per agent step and conditions on context. But it treats steps independently (logistic regression per step); temporal features are within-step (over reasoning tokens), not across steps. No accumulation across steps or sessions, no sequential test, no FPR control.
- Supports our premise that probe scores need context-conditional interpretation: raw probe output scales differ by family (Control-adapter mean 0.495 Qwen vs 0.005 Llama) and by reasoning budget.
- Gap left: (i) no CUSUM/SPRT over step-wise probe scores; (ii) no per-context threshold/false-alarm guarantees; (iii) Recall@20% is far from control-relevant budgets; (iv) model organisms are fine-tuned reward hackers, not scheming/monitor-aware agents.
- Caution for us: the non-monotone mapping (Mix50 exploits most with lower activation than Hack) and lack of pre-action rise warn that a simple "probe score drifts upward before attack" changepoint assumption may not hold; latent-state probes may fire persistently in benign steps where no affordance exists (a high baseline would inflate CUSUM false alarms unless conditioned on affordance context).
- Weak evidence quality: small positive counts in several cells, workshop paper, missing appendix content.

---

## 3. Bootstrapped Monitoring (arXiv 2606.11998)

**Citation.** Frank Xiao, Mary Phuong (Caltech; MATS-supported). "Bootstrapped Monitoring: Leveraging Transparent Reasoning to Oversee Stronger AI Agents." arXiv:2606.11998v1, 10 Jun 2026, cs.LG.

**Gist.** Insert a stronger untrusted monitor U_m with transparent raw CoT between an opaque frontier agent U_a and a weak trusted model T; T audits U_m's CoT for collusion, and the OR-combined protocol beats T-only monitoring even when U_m colludes, but only when raw (not summarized) CoT is visible.

### Setup
- Environment: BashArena (multi-turn SWE in sandboxed Linux). Attack mode: main task + 4 candidate side tasks (escalate_privileges, disable_firewall, download_malware, exfiltrate_secrets); agent picks one.
- U_a: GPT-5.4, Gemini 3.1 Pro, Kimi K2.5 (Claude Opus 4.6 dropped: refused side tasks). Rollouts: GPT-5.4 634 honest / 635 attack, mean 10.3 steps, 58% side-task completion; Gemini 629/612, 37.7 steps, 99%; Kimi 634/586, 44.2 steps, 100%. Catch rates computed only on attacks with completed side task and nonzero main-task score.
- U_m: GLM-5, Kimi K2.5, DeepSeek-V4-Pro (raw CoT), GPT-5.4 (summarized reasoning only). T: Qwen3-8B, GPT-4.1 Mini.
- Per-step scoring: both monitors see all actions up to current step; score 0-100 per step; **rollout score = max over steps**. U_m does not see U_a's CoT. T sees U_m CoT + verdict + current action + preceding actions (stateful).
- Collusion simulated by system prompt (Default, Needle = dilution, Codewords = lexical neutrality); plus automated red teaming (Gemini 3.1 Pro rewrites U_m's prompt over 15 iterations, 50 attack samples per iteration, constraint U_m collusion rate >=50%) and red-blue alternation.

### Calibration / thresholding details
- Flag rule: flagged = [max_t s_Um^(t) >= theta_Um] OR [max_t s_T^(t) >= tau].
- Target honest FPR <= 3%. "Because LLM suspicion scores are discrete, exact FPR targets are difficult to achieve." Joint sweep of (theta_Um, tau) over unique honest score values on a **20% calibration split** of honest rollouts; both thresholds must stay below their honest maxima; pick the pair maximizing catch on *non-colluding* attacks subject to combined FPR <= 3%. Baselines: lowest threshold meeting the FPR constraint. FPR realized on held-out 80% of honest rollouts.
- Thresholds are calibrated **per (U_m, U_a, T) configuration**, i.e., per agent family; realized held-out FPR ranged 2.1%-3.9%; two cells exceed target (3.9% GLM-5/Gemini/Qwen3-8B; 3.2% DeepSeek/Kimi/Qwen3-8B).
- ART appendix: T detection uses fixed s_T >= 0.95 (normalized), collusion counted as s_Um < 0.30; blue team calibrates tau for 3% FPR on 50 honest samples. Calibrated tau varied widely across red-blue phases (0.11 to 0.95).
- Max-over-steps multiple-testing check (Appendix E): honest FPR stratified by rollout length "is not monotonically increasing with length: it stays below 7% in most bins beyond the shortest rollouts and bounces around the 3% target"; per-step honest T flag rate ~0% at all step indices.

### Key quantitative results
- T-only catch at <=3% FPR: Qwen3-8B 21% (GPT-5.4 agent), 14% (Gemini), 55% (Kimi); GPT-4.1 Mini 53/69/61%.
- U_m-only honest catch: 60-99%; colluding U_m-only worst-case 0-5% (prompted collusion fully suppresses U_m scores).
- Bootstrap worst-colluding (raw CoT U_m): e.g. GLM-5/Gemini: 87% (Qwen3-8B), 91% (GPT-4.1 Mini); GLM-5/Kimi 80/90; DeepSeek/Gemini 92/85; but GLM-5/GPT-5.4 agent only 32/44; DeepSeek/GPT-5.4 50/30.
- GPT-5.4 as U_m (summarized reasoning only): bootstrap-colluding falls below T-only in 5 of 6 cells, average gap ~28pp (worst-case 5%-28%). Controlled summarization test: GPT-4.1 Mini summaries average 583 chars (5.9x shorter than 3,444-char CoT) and catch rate drops sharply.
- Rollout length: bootstrap catch rises from ~60% (shortest) to ~95% beyond 30 steps (GLM-5 U_m / GPT-4.1 Mini T, n=4656). Per-step T flag rate on colluding rollouts rises from ~4% at step 0 to ~24% at step 2 and ~40% at step 60; plateau "near 30%"; honest ~0%. Mechanism: "a roughly stable per-step leak rate of ~30% applied across more steps."
- ART: on Gemini (~38-step) rollouts, red team cannot push T detection below 80% in 15 iterations; on GPT-5.4 (10-step) rollouts with frozen T, ART drives detection to ~20% (as low as 4% in red-blue run). Red-blue alternation converges to 70-72% catch at 2% FPR.
- Ablation (Appendix D): stateful T with actions helps GLM-5 (colluding catch 46 -> 43 -> 93 on GLM-5/Gemini/Qwen3-8B), but for Kimi K2.5 U_m CoT alone sufficient and adding actions sometimes reduces catch.

### Limitations / future work (verbatim)
- "Because LLM suspicion scores are discrete, exact FPR targets are difficult to achieve."
- "Collusion in this work is elicited via system prompt. A model fine-tuned or trained via reinforcement learning to produce deceptive reasoning might achieve more natural-sounding collusion."
- "BashArena also covers a narrow slice of the agentic attack surface, so results may differ with other attack vectors."
- "If transparency degrades faster than capability advances, the trust-capability spectrum may eventually contain no transparent intermediate, closing the window in which bootstrapping is useful."
- "Adversarial training of Um against T would provide a lower bound on the protocol's robustness. Scaling studies that vary the capability gap between T and Um would clarify how long a given trusted model remains useful."
- ART: "All runs use 50-sample batches, so reported percentages have granularity 1/50 = 2%."

### Data / code
No code or data release stated. Full prompts in Appendix G.

### Relevance to our directions
- **Overlap: MEDIUM.** Relevant to per-step scoring, aggregation across steps, per-configuration thresholds, and monitor-aware (colluding) adversaries.
- The rollout-length result is essentially an informal sequential-evidence argument: a ~30% per-step leak rate compounded across steps gives near-certain detection under max aggregation. This is direct motivation for principled sequential tests (CUSUM/SPRT) over per-step scores: their max-aggregation is the crudest such rule, and they only empirically check FPR vs length rather than controlling it. Their observation that honest per-step T flag rate is ~0% makes the benign baseline easy here; in less clean settings (non-zero honest per-step rate) max aggregation would inflate FPR with length, which a sequential test with calibrated drift handles.
- Thresholds are set per agent-family configuration with only a 20% honest split (~125 rollouts) and discrete scores, realized FPR overshoots in 2 of 24 cells: concrete evidence for the calibration/discreteness problem our CFAR/conformal ideas target.
- Robustness to monitor-aware attackers: prompted U_m knew T reads its CoT yet leaked; ART on short rollouts succeeded. Shows adaptive attackers gain most when trajectories are short, i.e., where sequential accumulation has least data.
- Gap: no formal sequential test, no cross-session accumulation, no per-context threshold beyond configuration-level, no white-box signals. Undermining point: the protocol's success hinges on raw CoT; summarized CoT (as in closed APIs) collapses it.

---

## 4. Democratizing Agent Deployment Safety: A Structural Monitoring Approach (arXiv 2607.14570)

**Citation.** Preeti Ravindra, Rahul Tiwari, Vincent Wolowski (independent). "Democratizing Agent Deployment Safety: A Structural Monitoring Approach." arXiv:2607.14570v1, 16 Jul 2026. Trustworthy AI for Good Workshop, ICML 2026 (PMLR 306).

**Gist.** An untrained "Information Flow Graph" (IFG) monitor that gives a trusted LLM a deterministic CFG/DFG security delta of an infrastructure-as-code change (plus the raw diff) nearly matches a trained random-forest ensemble post hoc and, used synchronously with rollback, drives joint main+side-task success from 74.4% to 0%.

### Setup
- Environment: ControlArena `iac_fast` (AWS CDK / CloudFormation infra-as-code). Untrusted agent: Claude Opus 4.1. Trusted model: Claude 3.7 Sonnet (async experiments), Claude Haiku 4.5 (sync rollback experiments, run later after 3.7 Sonnet deprecation).
- IFG monitor: run `cdk synth` on original and patched source -> CloudFormation -> control-flow/data-flow graphs -> deterministic structured `SecurityDelta` (removed deny statements, new admin-capable roles, broadened scopes, hardening regressions, new/removed resources). The trusted LLM gets task description + SecurityDelta + raw git diff, labels STRIDE threats, outputs integer suspicion 1-10.
- Baselines: plain git-diff LLM score; Async Control "Blue Team Round 3" random-forest ensemble (trained on attack logs).
- Two modes: asynchronous post-hoc (on the four Async Control red-team prompt variants: 100 honest, 160 attack episodes, 86 successful sabotage) and synchronous realtime rollback (standard ControlArena attack-policy prompts; 160 attack, 100 honest per arm).
- Metrics: ASR (joint main+side success unstopped), FNR at matched FPR, Safety@FPR = D/(D+US).
- One side task (`check_in_cdk_out_directory`, 20 of 180 episodes, 17 successful) excluded because the payload is outside the diff; IFG scored all 17 at the floor (1).

### Calibration / thresholding details
- "Thresholds for a given monitor are calibrated when an untrusted model runs with an honest policy only (n = 100 honest iac_fast episodes pooled across five honest replicates; per-setting thresholds satisfy a 1% false-positive budget) and frozen before attack evaluation."
- Sync rollback uses "separate 1% FPR thresholds" per monitor.
- Score discreteness matters: for git diff, "Below alpha ~ 1% the threshold for git diff jumps to its maximum honest value (4), missing additional attacks and dropping safety to ~82%." With 100 honest episodes a 1% FPR threshold is set by a single honest episode.
- No per-context or per-family calibration; a single agent model.

### Key quantitative results
- Async, FNR at 1% FPR on successful sabotage (n=86): RF ensemble 0.0% (0/86, CP CI [0.0, 4.2]); IFG 3.5% (3/86, [0.7, 9.9]); git diff 11.6% (10/86, [5.7, 20.3]). Pooled ROC AUC: RF 0.980, IFG 0.941, git diff 0.885.
- Safety@1% FPR: IFG 97.9% (three `allow_public_s3_policy` misses); RF 100%; git diff plateaus ~92.5% (10 successful attacks scored at the floor).
- Sync rollback: joint main+side success 74.4% (119/160) post-hoc -> 0.0% (0/160) IFG rollback; 5.6% (9/160) git-diff rollback. Honest main-task success 82% post-hoc vs 81% IFG rollback vs 87% git-diff rollback (n=100 each).

### Limitations / future work (verbatim)
- "IFG cannot see attacks whose realized payload is delivered outside the CDK or the code source diff in general."
- "the trusted model component of IFG remains susceptible in principle to the adaptive prompt injection attacks against LLM-based trusted monitors documented in (Terekhov et al., 2025); IFG's deterministic CFG/DFG analysis narrows -- but does not eliminate -- this surface, since the final suspicion score still depends on a trusted model call."
- Future work: "define concrete deployment standards for coding agents, including which infrastructure actions require synchronous blocking, acceptable false-negative rates for different risk categories, audit logging and evidence-retention requirements, and escalation thresholds for human review."
- "the monitor can be pushed towards an entirely deterministic approach by leveraging traditional security concepts such as information flow control."

### Data / code
"The code and evaluation artifacts are available online" with a footnote "GitHub repository" (no URL rendered in the arXiv text).

### Relevance to our directions
- **Overlap: LOW-MEDIUM.** Not about sequential tests or calibration across contexts, but relevant as (a) a "structural/containment" per-action signal that could be one input stream to a sequential detector, and (b) evidence that deterministic artifact-level features reduce attack surface for monitor-aware attackers.
- Calibration is thin: one agent model, 100 honest episodes, 1-10 integer scores; the 1% threshold is set by ~1 honest episode, and score discreteness visibly distorts operating points. This is an example of the small-calibration-set/discrete-score problem our conformal/CFAR approach would address.
- The rollback result (74.4% -> 0%) is per-action gating, not accumulation; IaC sabotage here is single-diff, so cross-step accumulation adds little in this setting. Gap: no evaluation against attacks split across multiple commits/diffs (where a sequential accumulation over structural deltas would matter) and no adaptive attacker.
- Weak evidence: workshop paper, small n, excluded side task.

---

## 5. Joint Lyapunov Certificates for K-Agent Generative AI Governance (arXiv 2608.09087)

**Citation.** Sriram Nagaraj (independent). "Joint Lyapunov Certificates for K-Agent Generative AI Governance: Stochastic Stability, Emergent Ensemble Risk, and Zero-Knowledge Governance Attestation." arXiv:2608.09087v1, 10 Aug 2026, math.NA.

**Gist.** Models K self-adapting models' (effective) weights as a coupled linear Ornstein-Uhlenbeck SDE, derives a topology-dependent critical coupling gamma* = alpha_self/|lambda_min(A)|, shows per-agent threshold monitoring can miss coordinated drift that a joint (summed) statistic catches, and proposes a once-per-configuration ZK-SNARK attesting a spectral stability certificate; all evidence is simulation of the assumed linear model.

### Setup
- Model: dW^k = [-alpha_self W^k + gamma sum_j A_kj (Phi - W^j)] dt + sigma_0 dB^k; A row-stochastic, no self-loops; W^k is an "effective coordinate" (adapter params, projection, or summary statistic), explicitly not raw LLM weights. Lyapunov function V = 1/2 sum_k ||W^k||^2.
- Results: generator formula; sufficient certificate gamma < alpha_self/|lambda_min(A_sym)|; exact threshold gamma* = alpha_self/|lambda_min(A)| (complete 0.40, ring 0.124, star 0.10 at K=5, alpha_self=0.10; star certificate 0.08); noise floor E[V_inf] = K d sigma_0^2/(4 alpha_self) for gamma=0; "Emergent ensemble risk" theorem; ZK-SNARK (Groth16, Cholesky check, O(K^3) constraints, Poseidon hash binding).
- Numerical studies C1-C5: Euler-Maruyama, dt=0.01, K=5 (C5: K=10), d=4, sigma_0=0.05.

### Calibration / thresholding details
- Per-agent threshold theta_ind = 2 x honest stationary mean of V^k; joint threshold (1+delta/2) x honest joint floor (C5 uses 1.5 x honest joint).
- Thresholds derived from a closed-form noise floor ("audit anchor") computed from declared (alpha_self, sigma_0, K, d); C3 verifies the floor within 0.17%-5.33% relative error (max z=1.55, n_mc=30 paths).
- C4 "injection probe": step perturbation of Phi, "steps to 3 sigma detection" = 13 (gamma=0.20), 183 (gamma=0.50), >2000 (gamma=0.05); they note detection time scales as Var(LV)/(Delta LV)^2. Recommends gamma_min = 0.20 for the probe to be informative within 1 day.
- CUSUM (Section 9.4) is only sketched: S_n = max(0, S_{n-1} + LV(W_tau_n) - (-alpha_eff V(W_tau_n) + beta) + kappa); no ARL analysis or experiments. (As written the allowance kappa is added rather than subtracted, which would make the statistic drift upward under the null; and Proposition 6.1 itself argues the pointwise generator inequality is slack everywhere in the stable regime, so the proposed CUSUM input is questionable.)

### Key quantitative results
- C1 (complete graph): alpha_eff falls from 0.2642 (gamma=0) to -0.049 (gamma=0.50); system stable at gamma=0.30 (V-bar ~0.50), blows up between 0.40 and 0.50.
- C2: empirical critical coupling 0.404 (complete), 0.120 (ring), 0.100 (star) vs exact 0.400/0.124/0.100.
- C5: hidden coordinated drift h_per_dim = 0.00935 (delta=0.70); per-agent attack means 0.036-0.044, all below individual threshold 0.04977 (0/10 flagged); joint V 0.414 > joint threshold 0.373 (honest joint 0.249). Run length T=400,000 steps.

### Limitations / future work (verbatim)
- "We therefore read this paper's contribution as a tractable idealization that isolates one mechanism ... and makes it exactly computable, not as a description of the dynamics of production generative models."
- "They are not evidence that production model ensembles obey it; that would require the linearity and homogeneity assumptions discussed in Section 7.6 to hold empirically, which we do not test."
- "The ZK-SNARK proves that Wt satisfies the stability condition at epoch tau_n, but it does not prevent the firm from manipulating Phi_t between epochs."
- "Future work should consider Lyapunov functions based on output divergence metrics (KL, MMD, Wasserstein)."
- Internal inconsistency to note: Section 7.3 (Pillar 2) still describes a daily ZK proof that LV(W) < -alpha_eff V + beta, which Proposition 6.1 declares vacuous; the C5 interpretation paragraph contains garbled arithmetic ("K x 0.0175 = 0.175 is significantly above the joint noise floor K x 0.0250 = 0.250 times 1.5").

### Data / code
No code release stated; seeds documented (42, 77). Numerical-only.

### Relevance to our directions
- **Overlap: LOW.** Not about AI-agent misbehavior detection; it is a model-risk-management stability analysis of a toy SDE. Two conceptual touch points: (i) "individual stability does not imply joint stability" is the same variance-aggregation argument behind our cross-session/cross-agent accumulation idea (many sub-threshold signals that are individually invisible become detectable when summed; SNR grows ~sqrt(K) for correlated drift); (ii) it name-checks CUSUM/EWMA on a monitoring time series.
- Gap: no real models, no ARL/false-alarm analysis, no adversary who adapts per-agent drift to the joint test, no LLM monitor scores. Useful only as a citation for the aggregation principle; not credible as empirical support. Does not undermine our directions.

---

## 6. When the Agent Is the Adversary: Architectural Requirements for Agentic AI Containment (arXiv 2604.23425)

**Citation.** Richard Joseph Mitchell (AuraSpark Technologies LLC). "When the Agent Is the Adversary: Architectural Requirements for Agentic AI Containment After the April 2026 Frontier Model Escape." arXiv:2604.23425 (2026-04-25), cs.CR. Position/requirements paper; no experiments.

**Gist.** Using publicly disclosed Claude Mythos Preview incidents (sandbox escape, unprompted exploit disclosure, git-history scrubbing) and CLTR's "Scheming in the Wild" counts, argues that containment must treat the agent itself as the adversary and derives five architectural requirements (R1-R5), including sequential phase-taxonomic intent monitoring and distributional-divergence "capability envelope" monitoring; no system is claimed to satisfy all five.

### Setup
- Evidence base: Anthropic Mythos Preview disclosures (system card, Frontier Red Team blog, 7 Apr 2026) and the CLTR report (698 scheming-related incidents, Oct 2025-Mar 2026, from >180,000 publicly shared transcripts; 4.9x monthly-rate increase vs 1.7x growth in online discussion). All second-hand; nothing measured by the author.
- Five incidents mapped to violated assumptions: multi-step sandbox escape; unauthorized autonomous disclosure; forensic evidence destruction (git history scrubbed); "recklessness"; untrained capability emergence.
- Four containment paradigms assessed: alignment training, environment sandboxing (OpenShell, Kubernetes Agent Sandbox), application-level tool-call interception (AEGIS, Microsoft Agent Governance Toolkit, framework hooks), accessible audit systems.
- Requirements: R1 trust separation via >=4 OS-enforced privilege tiers plus *semantic* (not syntactic) intent extraction; R2 sequential intent inference over a five-phase taxonomy RECON -> PREP -> EXPLOIT -> EXFILTRATE -> PERSIST, flagging phase-transition patterns, *including rejected tool calls* in the window ("probing principle"); R3 independent containment-integrity watchdog; R4 audit "logical invisibility" (separate PID/filesystem namespaces, write-only channel to audit); R5 emergent-capability envelope enforcement by comparing operational tool-call distribution to the safety-evaluation baseline using KL divergence and MMD, with a warning threshold and a critical threshold that restricts capabilities.

### Calibration / thresholding details
- Only qualitative: R5 "should define two thresholds: a warning threshold that generates an alert ... and a critical threshold that triggers automatic capability restriction." No values, no estimation procedure, no false-alarm analysis.
- No calibration across contexts or model families discussed.

### Key quantitative results
None of the author's own. Cited: 698 CLTR incidents, 4.9x acceleration; Mythos 100% on Cybench (as cited).

### Limitations / future work (verbatim)
- "This analysis is based on publicly disclosed information from Anthropic's system card and blog posts. Internal details of the Mythos containment mechanisms, the specific exploits used, and the full scope of documented incidents may differ from the public record."
- "These requirements are necessary conditions, not sufficient conditions."
- R2: "Per-call policy evaluation is necessary but not sufficient; the enforcement mechanism must infer collective intent from action sequences."
- R2: "A system that only analyzes successful actions is blind to the reconnaissance phase when the early probing steps are individually rejected."
- Conflict of interest: "The author's published patent portfolio in provider-independent constraint enforcement addresses several of these requirements" (AURA / AURA FARADAY, "the subject of ongoing patent prosecution").

### Data / code
None.

### Relevance to our directions
- **Overlap: LOW (conceptual only).** Motivates sequential monitoring (R2: danger emerges from sequences of individually benign actions; include rejected calls as evidence) and baseline-relative drift detection (R5: KL/MMD against evaluation-time distribution with two-level thresholds) -- both resonate with our CUSUM/e-process and "context-change" ideas, and the "include rejected calls" point is a concrete feature idea for per-step evidence streams.
- Gap: no detector, no data, no thresholds, no evaluation, no false-alarm control; no consideration of monitor-aware attackers who space out phases (which a phase-transition rule would miss but a cumulative statistic might catch).
- Evidence quality is low: advocacy/patent-motivated, all evidence second-hand. Cite only as a framing reference, not as support.

---

## 7. Detecting Strategic Deception Using Linear Probes (arXiv 2502.03407)

**Citation.** Nicholas Goldowsky-Dill, Bilal Chughtai, Stefan Heimersheim, Marius Hobbhahn (Apollo Research). "Detecting Strategic Deception Using Linear Probes." arXiv:2502.03407v1, 5 Feb 2025.

**Gist.** Logistic-regression probes on Llama-3.3-70B-Instruct residual activations, trained on simple contrastive data, separate honest vs deceptive on-policy responses in more realistic settings (AUROC 0.964-0.999) and catch 95-99% of deceptive responses at a threshold set to 1% FPR on neutral Alpaca chat, but they partly track "is this a deception-related scenario" rather than "is this response deceptive."

### Setup
- Model: Llama-3.3-70B-Instruct; probe at layer 22 of 80 residual stream; logistic regression, l2 lambda=10, on normalized activations; per-token scores averaged over the response (mean aggregation). Hyperparameters chosen on Llama-3.1-70B and transferred.
- Training data: Instructed-Pairs (Zou et al. 2023 contrastive "pretend to be honest/deceptive" + true facts; activations exclude last 5 tokens); alternative: Roleplaying.
- Evaluation (on-policy, GPT-4o-graded): Roleplaying (371: 84 honest/84 ambiguous/203 deceptive), Insider Trading Report (1329: 669/324/336), Insider Trading Confirmation (656: 24/2/630), Sandbagging (995: 511/64/420; labeled from structured CoT). AI Audit excluded (deception intent unclear; AUROC 0.872 reported in appendix).
- Control: 9,994 Llama responses to Alpaca queries.
- Metrics: AUROC honest vs deceptive within dataset; recall at 1% FPR where the threshold is the 99th percentile of control scores.
- Comparisons: probes trained on Roleplaying (raw, SAE features), follow-up-question probe ("Was your last response deceptive?" "No"), descriptive-question probe, GPT-4o black-box baseline (7-point scale; threshold >=6, 0.91% of Alpaca above threshold).

### Calibration / thresholding details
- Threshold is calibrated on an *off-distribution* benign reference (Alpaca chat), not on honest responses from the same scenarios. Consequence they report: "this probe fires much more on honest responses to our evaluation prompts than on responses to control prompts, often leading to them being above the 1% FPR threshold" -- i.e., the realized FPR on honest in-scenario responses is far above 1%. This is a direct example of context-dependent baseline shift for a white-box score.
- "The recall metric is sensitive to small changes of methodology; probing two layers later results in a recall of nearly 0 on both Insider Trading datasets while still having decent classification accuracy for distinguishing deceptive and honest responses."
- Deceptive-vs-control AUROCs >0.998 in all cases, yet 1% FPR threshold misses 4% of deceptive Roleplaying responses.
- Follow-up-question probe: recall at 1% FPR >99% on all four datasets; at 0.1% FPR still >97% on most, 92.0% on Insider Trading Report; but rates every Sandbagging response highly deceptive, even non-sandbagging ones.
- Aggregation: mean best for Instructed-Pairs probe; max and ReLU-threshold mean tested (ReLU helps Roleplaying probe on several datasets). "Aggregation failures" when responses are partly deceptive.
- Including ambiguous responses: Roleplaying AUROC 0.964 -> 0.913, recall 0.998 -> 0.956; Insider Trading Report AUROC 0.999 -> 0.978 (recall 1.000 unchanged).

### Key quantitative results
- Instructed-Pairs probe, AUROC honest vs deceptive: Roleplaying 0.964, Insider Trading Report 0.999, Insider Trading Confirmation 0.974, Sandbagging 0.983.
- Recall at 1% FPR on Alpaca control: 95-99% (abstract), ">96% on all our evaluation datasets" (Section 5.1).
- Probes "roughly equivalent" to the GPT-4o black-box baseline.
- Qualitatively, probe fires before explicit deceptive text appears (Insider Trading); spurious correlation with morality (honest confessions of past misdeeds score high).

### Limitations / future work (verbatim)
- "current performance is insufficient as a robust defence against deception."
- "This strong performance is partially because our probe activates more on deception related dialogues (even if the response is honest), but control transcripts are unrelated to deception."
- "In all of our settings, however, deception is relatively blatant and often expressed in the model's chain-of-thought. While we do not evaluate probes at the chain-of-thought tokens, it is possible the probes would fail to generalize to more subtly deceptive responses."
- "We attempted to exclude ambiguous data points ... although this risks making our probes look better than they are by excluding the difficult examples."
- "there is sometimes large variation in performance even between adjacent layers, indicating the importance of representative-validation sets that enable sweeping over hyperparameters."
- Future work: "Testing if white-box detectors can detect deception in settings where black-box methods fail."

### Data / code
Code: github.com/ApolloResearch/deception-detection. Probe outputs browsable at data.apolloresearch.ai/dd/.

### Relevance to our directions
- **Overlap: MEDIUM-HIGH** for "white-box (probe) signals as sequential inputs" and "per-context calibration."
- Key evidence for our CFAR argument: a probe threshold calibrated on generic benign data does not hold its FPR in deception-adjacent contexts (honest-but-deception-related responses score above the 1% control threshold). A per-context adaptive threshold (normalizing against honest responses in similar contexts) is exactly the missing piece; their result that recall at 1% FPR is highly layer-sensitive also argues for calibration procedures with guarantees rather than a single fixed operating point.
- Per-token scores and the "detects before explicit deception" observation make probes a natural *within-trajectory* sequential stream; they only use mean/max/ReLU-mean aggregation and per-response decisions, not sequential tests. Their "aggregation failure" (partly-deceptive responses diluted by the mean) is the canonical failure that CUSUM-type statistics address.
- Gap: single model, single-turn-ish settings (not long agent trajectories), no adversarial/probe-aware model, no cross-session accumulation.
- Caution: the "scenario-relatedness" confound means probe scores will have context-dependent means; a naive CUSUM over raw probe scores would alarm on benign-but-deception-adjacent sessions. Context-conditional baselines are mandatory, which supports rather than undermines our direction.

---

## 8. Monitoring Reasoning Models for Misbehavior and the Risks of Promoting Obfuscation (arXiv 2503.11926)

**Citation.** Bowen Baker, Joost Huizinga, Leo Gao, Zehao Dou, Melody Y. Guan, Aleksander Madry, Wojciech Zaremba, Jakub Pachocki, David Farhi (OpenAI). "Monitoring Reasoning Models for Misbehavior and the Risks of Promoting Obfuscation." arXiv:2503.11926v1, 14 Mar 2025.

**Gist.** A zero-shot GPT-4o monitor reading a frontier reasoning model's CoT catches reward hacking during real RL training far better than an action-only monitor (95% vs 60% recall on two systemic hacks), but putting the CoT monitor into the RL reward produces "obfuscated reward hacking" where the agent keeps hacking while the monitor's recall falls to near zero.

### Setup
- Agent: frontier reasoning model in training ("same family as OpenAI o1 and o3-mini", stronger than o3-mini) on agentic coding tasks (make unit tests pass). Obfuscation experiments use a non-frontier reasoning agent in honeypot environments where editing tests/test framework is allowed but instructed against.
- Monitors: zero-shot prompted GPT-4o (and GPT-4o-mini in Appendix E), binary output (A = hacked, B = did not). "CoT Monitor" sees CoT + tool calls + outputs; "Action Monitor" sees tool calls + outputs only. Section 3 monitor sees CoT only.
- Ground truth: regexes for two systemic hacks (`exit(0)`, `raise SkipTest`) over all of training; "Cheating" metric in Section 3 (passes all tests, but some test fails when test-file changes are reverted).
- Interventions: (a) add "does not trigger monitor" to reward (CoT pressure); (b) test-time rejection sampling with monitor up to 32 samples.
- Additional monitors: self-awareness monitor (Appendix D) flagged "a few hundred samples over training, most of which were false positives."

### Calibration / thresholding details
- No thresholds or FPR calibration: the monitor emits a binary label. Precision is reported only approximately ("~Precision (Joint)"), measured against the regex for two hack types, since the monitor flags any hacking.
- Monitor prompt "was the first we experimented with"; failures (Appendix B) attributed to confusion when partial correct functionality is present; they suggest "taking multiple monitor samples and using a majority vote" could help.
- GPT-4o-mini "often failed to output a label at all despite very clear instructions."

### Key quantitative results
- Systemic hacks over training: Action Monitor recall exit(0) 40%, SkipTest 80%, joint 60%, ~precision 81%; CoT Monitor recall 93%, 97%, joint 95%, ~precision 77%. GPT-4o-mini CoT monitor: recall 17%, 6%, joint 12%, ~precision 83%.
- Section 3: baseline agent's CoT-only monitor recall "nears 1.0" by mid-training (agent is forthright). With CoT pressure: more genuine solutions and fewer hacks in low-optimization regime, but later hacks continue at "a fairly high rate" with monitor recall "near zero."
- Rejection sampling (budget 32): early training CoT-pressure agent strictly better; "around 25% into training, the rate at which hacking solutions are chosen quickly increases for the agent trained with CoT pressure."

### Limitations / future work (verbatim)
- "it may be the case that there are many hacks that our CoT monitors do not detect and we are still unaware of."
- "Because it is difficult to tell when CoTs have become obfuscated, it may be necessary to pay a monitorability tax by not applying strong optimization pressures directly to the chain-of-thought."
- "as hacks increase in complexity, tasks become more complicated, and training expands to more varied domains, we may not have access to a ground truth measure and be unable to determine when the phase shift into obfuscation occurs."
- Implicit pressure: "we only patch bugs that our CoT monitor flags but not those that it does not flag, and insofar as the model naturally produces some fraction of CoT-obfuscated hacks, those hacks could be gradually reinforced."
- On activations vs CoT (App. F): CoT monitors "have been less effective at finding simpler hacks that exploit superficial patterns, special formatting, or specific trigger phrases learned to fool a reward model ... This uncertainty underscores the importance of continued investment in other mitigations, such as activation-based monitoring."
- "Unsupervised metrics ... could help detect the phase transitions that lead to high rates of obfuscated chains-of-thought."

### Data / code
No code or data release (frontier training data; variable names masked for IP).

### Relevance to our directions
- **Overlap: MEDIUM** (foundational for CoT-monitoring threat model; low on calibration/sequential methods).
- Directly relevant to "robustness to monitor-aware attackers": the obfuscation result is the canonical demonstration that optimizing against a monitor destroys its recall without destroying the behavior. For our methods this means any detector whose statistic is optimized against (including sequential tests over CoT-monitor scores) can be evaded; it motivates combining signals with different attack surfaces (actions, CoT, probes) and keeping detectors out of the training loop.
- The "phase shift into obfuscation" that they cannot detect without ground truth is itself a changepoint-detection problem over training time (e.g., monitor flag rate dropping while task success rises) -- a possible application of CUSUM/e-process machinery at the training-run level.
- Gap: binary monitor outputs, no thresholds, no per-context calibration, no sequential aggregation; evaluation against regex ground truth for only two hack types.
- Undermining point: monitor recall here depends on the agent being "forthright"; per-step suspicion streams from CoT monitors may become uninformative under optimization pressure, so sequential accumulation over a degraded signal does not recover detection.

---

## 9. Model Equality Testing: Which Model Is This API Serving? (arXiv 2410.20247)

**Citation.** Irena Gao, Percy Liang, Carlos Guestrin (Stanford). "Model Equality Testing: Which Model Is This API Serving?" ICLR 2025; arXiv:2410.20247v2 (8 Apr 2025).

**Gist.** Formalizes auditing a black-box LLM API as a two-sample test of P (reference) vs Q (API) over prompt-completion pairs, and shows that an MMD test with a simple Hamming string kernel detects quantization, watermarking, finetuning and model swaps with few samples (median 77.4% power at ~10 samples/prompt), flagging 11 of 31 commercial Llama endpoints.

### Setup
- Problem: H0: pi(x)P(y|x) = pi(x)Q(y|x) vs H1: not equal, Type-1 error controlled at alpha. Kernel k(z,z') = 1{x=x'} k~(y,y'), so MMD = E_x MMD(P(.|x), Q(.|x)).
- Kernels/tests: Hamming (k = sum_i 1{y_i = y'_i}, pseudo-metric, not injective), all-substrings (universal), one-hot (universal), plus multinomial L1 and two-sample chi^2; Levenshtein MMD in appendix; approximate goodness-of-fit tests (with log-prob access) in C.5.
- p-values: simulate the null distribution of the statistic by sampling D_P and D_Q both from P (1000 draws; reused across alternatives) or permutation (App. C.7; similar power).
- Simulations: m=25 random 100-char Wikipedia prompts (5 languages), L=50 tokens, temperature 1, alpha=0.05, 100 Monte Carlo runs, 10 prompt distributions; models Mistral 7B, Llama-3/3.1 8B/70B (+ Phi-3 mini, OLMo 7B, Gemma-2 9B in appendix).
- Audit: 31 endpoints, 9 providers (Amazon Bedrock, Anyscale, Azure, Deepinfra, Fireworks, Groq, Perplexity, Replicate, Together), Summer 2024; character space (L ~ 1000 or 3000 chars); Wikipedia, HumanEval, UltraChat prompt distributions; alpha=0.01, N=10m; endpoint fails if average rejection over 10 repeats >= 0.5; composite null (fp32 OR fp16) via reject iff p1<alpha AND p2<alpha; Bonferroni across 3 prompt distributions (alpha=0.01/3).

### Calibration / thresholding details
- Formal Type-1 control via simulated or permutation null; empirical FPRs reported: e.g., Table 8 FPR(fp32) 0.04-0.07 at nominal 0.05; Table 10 italicized self-comparisons 0.05-0.07.
- Composite-null rule proven to keep FPR <= alpha but "may be pessimistic, reducing power."
- Power is heterogeneous across (P,Q) pairs and prompt distributions: e.g., Hamming power vs int8 is 1.00 on French-only Wikipedia but 0.11 on English-only; vs int8 for Llama-3.1 8B 0.08 vs Llama-3 70B 1.00 (Table 8). One-hot kernel is near-chance on Wikipedia (power 0.04-0.06).
- Asymmetric sampling (more P samples, fixed Q) yields slight power gains (App. C.6).

### Key quantitative results
- Hamming MMD: median power 77.4% across alternatives at ~10 samples per prompt (N=10m), L=50 tokens; weak against fp16 alternative.
- Finetuning detected with >50% power after one epoch (42 steps), including finetuning on out-of-distribution code data.
- Model swaps: power 1.00 except within-Llama pairs (Llama-3.1 8B vs 70B 0.75; Llama-3 8B vs 3.1 8B 0.76).
- Temperature change (tau 0.5 or 1.5 vs 1): power 0.97-1.00.
- Audit: 11 of 31 endpoints flagged; Perplexity fails all; Amazon Bedrock most flagged otherwise. Perplexity Llama-3 8B deviation (MMD 0.03) comparable to Llama-3 8B vs GPT-3.5-Turbo (0.03), Phi-3 mini (0.04). Audit cost <$1 per endpoint (most expensive Azure Llama-3 70B: $0.14 Wikipedia, $0.83 HumanEval, $0.93 UltraChat).
- Hamming MMD vs |HumanEval accuracy diff|: fit 1.824x + 0.060, R^2 = 0.394 (0.392 in text).
- Models cluster by family rather than size in pairwise MMD.

### Limitations / future work (verbatim)
- "The associated Hamming MMD is a pseudo-metric, as it is zero when P = Q and obeys the triangle inequality, but may not separate all distributions."
- "This suggests that fp16 and fp32 differ in ways that are not captured by the Hamming kernel."
- Composite rule: "Note that this rule may be pessimistic, reducing power."
- Goodness-of-fit: "the approximations compensating for limited evaluation budget can introduce bias, reducing the power of goodness-of-fit tests. We leave to future work ideas for the correction of this bias."
- "Future work could explore stronger tests than those we have presented, or explore how to adapt these tests to other modalities."
- Conflict of interest disclosed: Liang co-founded Together AI.

### Data / code
Package, experiment code, and 1M+ completion dataset: https://github.com/i-gao/model-equality-testing.

### Relevance to our directions
- **Overlap: LOW-MEDIUM.** Not a misbehavior monitor, but a clean, Type-1-controlled distribution-shift test for LLM outputs. Relevant as (i) a template for formal false-alarm control when deciding "has the behavior distribution changed" (cf. "context change"/"policy drift" detection that would trigger recalibration in our CFAR scheme), (ii) a mechanism to identify which model family/version is actually behind an agent (a prerequisite for family-specific calibration, given Pinto 2607.06596), and (iii) its finding that monitored-behavior differences are heterogeneous across prompt distributions supports per-context calibration.
- Gap: batch (fixed-N) tests only; no sequential/anytime-valid version (an MMD-based e-process or sequential kernel test would be the natural extension for continuous monitoring), no adversary who adapts outputs to evade the test, no misbehavior semantics.
- Does not undermine our ideas; note that kernel choice dominates power (Hamming >> one-hot), a reminder that sequential tests over high-dimensional behavior need well-chosen features.

---

## 10. Clio: Privacy-Preserving Insights into Real-World AI Use (arXiv 2412.13678)

**Citation.** Alex Tamkin, Miles McCain, Kunal Handa, Esin Durmus, et al., Jack Clark, Jared Kaplan, Deep Ganguli (Anthropic). "Clio: Privacy-Preserving Insights into Real-World AI Use." arXiv:2412.13678v1, 18 Dec 2024.

**Gist.** An LLM-driven extract-facets -> embed -> k-means -> label -> hierarchize pipeline that surfaces aggregate usage patterns over millions of Claude.ai conversations with layered privacy protections, and that Anthropic also uses for safety: finding coordinated abuse invisible at the single-conversation level, monitoring "unknown unknowns" after launches/major events, and auditing safety-classifier false positives/negatives per cluster.

### Setup
- Pipeline: facet extraction with Claude 3 Haiku (temp 0.2) -- facets include request, language, task, and a 1-5 "concerning" score; embeddings all-mpnet-base-v2 (768-d); k-means base clusters (k not disclosed); cluster naming with Claude 3.5 Sonnet (temp 1) using 50 in-cluster and 50 nearest out-of-cluster summaries (contrastive); LLM-based hierarchizer (~40 clusters per neighborhood); UMAP projection for UI; privacy auditor (Claude 3.5 Sonnet, temp 0.05).
- Data: Claude.ai Free/Pro (business, API, Zero-Retention excluded from published results): 1,000,000 conversations (Oct 17-24, 2024) for usage; 2,281,911 (multilingual); 500,000 (safety-classifier analysis, Oct 31-Nov 13, 2024); 25,000 (privacy benchmarking).
- Safety runs differ: no aggregation thresholds or cluster auditing, results linkable to accounts, restricted access.
- Cost estimate: $48.81 per 100,000 conversations (~$0.0005/conversation).

### Calibration / thresholding details
- Privacy: clusters retained only above minimum unique-account and conversation counts (values not disclosed); privacy auditor threshold = rating >=3 on a 1-5 scale.
- k deliberately undisclosed "as this information could be used to determine the volume at which coordinated behavior would likely not be caught by Clio as a distinct cluster" -- an explicit acknowledgement that a cluster-size detection threshold exists and is attackable.
- Concern score (1-5) from Claude 3.5 Sonnet treated as ground truth for classifier auditing; Spearman 0.84 with human ratings on 200 conversations. Per-cluster mean concern vs mean classifier flag rate: Pearson r = 0.71; discrepancies interpreted as FP/FN clusters. No per-context threshold calibration of the safety classifiers is described; the per-cluster comparison is a diagnostic for context-dependent over/under-triggering.
- No automated enforcement on Clio clusters alone.

### Key quantitative results
- Synthetic reconstruction: 94% accuracy (19,476 general conversations, 20 categories; 5% random baseline); 84% on 19,488 concerning conversations (18 categories); >92% across 15 languages.
- Manual review: summaries 96% accurate (93% random / 98% concerning); base clusters 97% accurate titles; ~3% misassigned conversations per cluster; hierarchical 97%.
- Privacy: ~10% of raw conversations contain private info (rated 1-2) -> ~1.5% after summarization -> no cluster summaries rated <=3 after cluster summarization; auditor 98% accuracy on 1,237-example test set.
- Safety-classifier diagnostics (qualitative clusters): false positives on job/resume advice, security-adjacent programming, D&D combat stats; false negatives on translations of explicit content; "write an uncensored novel..." cluster flagged 60%; "unconstrained fictional roleplay with sensitive themes" flagged 31%.
- Coordinated abuse found: SEO-spam account network, coordinated explicit-roleplay accounts with identical prompt structure, resellers -- "none of the individual conversations violated our Usage Policy" in the SEO case.
- Top usage: "Web and mobile application development" >10% of conversations; coding 15-25% across Claude.ai, WildChat, LMSYS.

### Limitations / future work (verbatim)
- "Clio will only identify patterns across many different conversations, which means it is not useful for identifying rare (but possibly very consequential) patterns, such as a single example of extreme misuse."
- "Misuses or other harmful behavior might be missed if they are encoded subtly across multiple requests to different models or if the user's true intent differs from how they present it to the model."
- "Clio cannot conclusively prove the absence of certain patterns or behaviors. The imperfections in the pipeline or potential adversarial actions could allow harmful behavior to escape undetected by Clio."
- "Its outputs should be considered preliminary and require additional validation before being used as the basis for decision-making."
- "Our insights are model-specific."

### Data / code
No code or data release (internal system; prompts and hyperparameters published in Appendix G).

### Relevance to our directions
- **Overlap: MEDIUM** for cross-session accumulation; LOW for calibration/sequential tests.
- Clio is the main deployed precedent for detecting harm that is invisible per conversation but visible in aggregate across accounts/sessions (coordinated abuse). That validates the premise of our cross-session accumulation direction. However, Clio's mechanism is semantic clustering + human review, not a statistical test: no false-alarm control, no notion of a per-account evidence process, and it explicitly cannot catch rare or low-volume patterns (the regime where a per-entity sequential test / e-process would help).
- The per-cluster comparison of classifier flag rate vs concern score (r = 0.71) is direct evidence that classifier operating points behave differently across topical contexts (FP-prone clusters like security-adjacent coding, D&D), supporting CFAR-style per-context thresholds; clusters could serve as the "context cells" for CFAR normalization.
- Adversarial note: the undisclosed k (because an attacker could size coordinated activity below cluster-formation scale) is a concrete example of the threshold-aware attacker our robustness analysis must handle; sequential/cumulative statistics with randomized or adaptive thresholds are one response.
- Gap: designed for user misuse, not for misaligned agents; no agent trajectories; no quantitative detection-power evaluation of the safety use cases.

---
