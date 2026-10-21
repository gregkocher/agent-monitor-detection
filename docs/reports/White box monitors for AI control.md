# White-Box Monitors Earn a Bounded Pilot

*Research report, 21 October 2026. Built from the four note files in `research_notes/White box monitors for AI control/` and from `reports/00_Overall_Summary.pdf`. Numbers that reached the notes only through an automated fetch or HTML summary, or through a search snippet, are flagged in the text as "(via summary; unverified)". Do not quote them without checking the primary source.*

As of October 2026, activation probes are the only white-box monitor with competitive, published numbers in agentic control settings. FAR.AI's FIBS preprint reports **98.3% AUROC on SHADE-Arena and 98.0% on BashArena, against 97.7% and 97.6% for frontier text monitors** ([arXiv 2610.12445](https://arxiv.org/abs/2610.12445)). The edge is real but thin, and it comes with three limits. The attackers were instructed saboteurs, not trained ones. No attacker in that work was aware of the probe. And only one global threshold was used. The rest of the white-box toolkit is earlier-stage. SAE probes do not beat dense probes. The Jacobian lens (J-lens) has case studies and one eval-awareness AUC (0.853), but no detection benchmark. Anomaly detection and model diffing are used as offline audits, not as runtime monitors. Robustness is the weak point. Every tested probe can be pushed to near-zero recall by an attacker that controls training. Ordinary RL alone can collapse an off-domain probe from 0.99 to 0.38–0.66 AUC. Thresholds set on Alpaca do not hold their false-positive rate inside risky contexts. Labs run probes as cheap first-stage screens (Anthropic and GDM for misuse; OpenAI and Anthropic, reportedly, for misalignment during training and agentic inference). None has published recall or FPR for a misalignment monitor. On our own work: our decision-layer results map directly onto open gaps, so a first white-box round is worth running, provided it stays small and is framed honestly. Two candidate extensions are clearly open: probes and LLM monitors compared under the same detector-aware attacker, and J-lens readouts used as step-level monitors. Sequential tests and per-context thresholds on probe streams are open in exactly the form we would run them. But FAR.AI holds the ideal data for both, and their paper names false positives as the next problem. Probe-plus-LLM fusion is already published as a method. The cheapest credible first experiment uses an open trusted reader (Qwen3.5-27B) to score the 1,325 MonitoringBench trajectories that we already scored step by step with gpt-4.1-mini, plus the LinuxArena sweep. It costs about **$80–180 of GPU time and $0 of API**, and tests (a), (b), (c) and a free version of (d) in one pass. The main risks are, in order: a reader probe that adds cost savings but no detection power; being scooped by FIBS; and robustness claims that remain weak without a trained evader.

## Probes now match frontier text monitors, mostly where misbehavior is salient

The field has converged on a standard recipe. Train a probe on mid-depth residual activations, using cheap contrastive or synthetic off-policy data. Set the threshold at 1% FPR on benign chat. Report AUROC and recall at that threshold. The early landmarks showed how far a tiny amount of data goes. Coup probes trained on **43 synthetic theft examples reached 100% TPR at 1% FPR** on 46 held-out cases ([Roger, 2023](https://www.greaterwrong.com/posts/WCj7WgFSLmyKaMwPR/coup-probes-catching-catastrophes-with-probes-trained-off-policy)). Anthropic's defection probe, built from a single "Are you a helpful AI?" contrast pair, predicted sleeper-agent defection at **99.3% AUROC** from the prompt alone, before any output ([Anthropic, 2024](https://www.anthropic.com/research/probes-catch-sleeper-agents)). Apollo then moved to strategic deception. Its probe on Llama-3.3-70B, at layer 22 of 80 with mean pooling over response tokens, reached **AUROC 0.964–0.999 and 95–99% recall at 1% Alpaca FPR**, roughly equal to a GPT-4o black-box baseline ([arXiv 2502.03407](https://arxiv.org/abs/2502.03407)). Each early success came with its own warning. The sleeper-agent trigger was the top principal component at middle layers, so salience may come from how the backdoor was inserted rather than from defection itself. Apollo's recall fell to **nearly 0 on Insider Trading when the probe moved two layers later**.

The 2026 state of the art is multi-layer, multi-token and trained on much more data. GDM's production Gemini probes introduced MultiMax and max-of-rolling-means attention architectures because simpler probes failed on long context ([arXiv 2601.11516](https://arxiv.org/abs/2601.11516)). FIBS trained four architectures (a linear ensemble, an MLP ensemble, an early-fusion covariance probe, and an "Axial" transformer over the layer-by-token grid). The training set was **163,016 "contextual falsehood" transcripts in 28 families**. The probes read 6 layers between 30% and 90% of depth, on 9 open models ([arXiv 2610.12445](https://arxiv.org/abs/2610.12445); [code](https://github.com/AlignmentResearch/fibs-probes)). On agent steps, FIBS prefills a follow-up question ("Did you take actions towards a hidden side task?"). The score is the contrast between the probe readings for a "Yes." and a "No." answer.

The following details reached us only through an HTML summary and are unverified:

- Per-step AUROC climbs from about 0.94 with 3k training rows to about 0.98 with the full set.
- The smallest models (Qwen3.5-2B, Nemotron-3 Nano) are weak (about 0.58–0.81).
- Hidden-goal organisms reach 81–99.7%, but a math sandbagger reaches only 63%.
- A tiered-persona organism is caught at 94% recall at 2% FPR on one tier and **2% recall at 2% FPR on the other**.
- Summaries disagree on the label-noise estimate (0.74% vs about 1.4%).
- Summaries also disagree on which black-box comparator was used. One gives GPT-6.1 Sol at 0.977 in v3. Another gives an Opus 5.5 monitor at 0.960 in v1.

SAE-based probes have not earned their place as monitors. In ICML 2025 tests covering data scarcity, class imbalance, label noise and covariate shift, **no SAE-plus-baseline ensemble consistently beat baseline-only ensembles** ([Kantamneni et al.](https://proceedings.mlr.press/v267/kantamneni25a.html)). GDM found k-sparse SAE probes "distinctly worse" out of distribution than dense probes, which were near-perfect, and deprioritized SAE research as a result ([GDM post](https://greaterwrong.com/posts/4uXCAJNuPKtKBsi28)). The one agentic test of an SAE monitor, a reward-hack score inside ReAct agents, reached only **0.769 AUROC for next-step exploits and 0.565 for bad actions**. Its authors conclude that "agentic safety monitoring cannot be reduced to thresholding a single internal feature" ([arXiv 2606.06223](https://arxiv.org/abs/2606.06223)).

The comparison with black-box monitors is the crux, and the table below gathers every head-to-head in the notes. The pattern is consistent. White-box wins clearly when the evidence is not in the transcript: hidden-context deception, performative chain of thought, pre-generation prediction, and superficial reward hacks. It ties or wins narrowly when the misbehavior is visible in the transcript. It loses outright on trained, belief-verified organisms and on lie types that cannot be read off the transcript.

| Setting | White-box result | Black-box comparator | Source |
|---|---|---|---|
| SHADE-Arena / BashArena, per step | 98.3% / 98.0% AUROC (axial probe) | 97.7% / 97.6% (frontier text monitors; comparator identity via summary) | [2610.12445](https://arxiv.org/abs/2610.12445) |
| Apollo deception datasets | 0.964–0.999 AUROC | "Roughly equivalent" to GPT-4o | [2502.03407](https://arxiv.org/abs/2502.03407) |
| Probe scores given to an LLM monitor, 5 datasets | Mean +0.046 AUROC; Backdoors **−0.123** | Same LLM without probe scores | [2507.12691](https://arxiv.org/abs/2507.12691) |
| InterCode CTF sandbagging, 70B | 97–99% AUROC; 88% TPR at 2% FPR (max) | 74% AUROC | [UK AISI](https://www.alignmentforum.org/posts/pPEeMdgjpjHZWCDFw/white-box-control-at-uk-aisi-update-on-sandbagging) |
| Agentic reward hacking (Kimi K3), matched FPR | +3.0 pp TPR DeepSWE, +33.1 pp ImpossibleBench, −6.6 pp SWE-Bench; probe OR monitor 41.1%→80.2% TPR for +1 pp FPR | LLM monitor | [2609.19101](https://arxiv.org/html/2609.19101v2) |
| High-stakes interactions, 1% FPR | ~43% detected (via summary; unverified) | ~55% strongest LLM | [2506.10805](https://arxiv.org/abs/2506.10805) |
| Liars' Bench, 1% Alpaca FPR | 0.54 balanced accuracy | 0.73 LLM-as-judge | [2511.16035](https://arxiv.org/abs/2511.16035) |
| Trained lying organisms | All activation detectors "drop sharply" | CoT judge holds 0.82 balanced accuracy | [2606.12618](https://arxiv.org/abs/2606.12618) |
| Trusted reader, APPS backdoors | 0.91 AUROC, 50% catch at 2% budget | Same model's own 0–9 rating: 0.54, 5% | [LGOICOUR repo](https://github.com/LGOICOUR/probe-monitor-control) |

Two caveats apply to the whole table. First, AUROC is a poor guide to operating points. In Gao's AgentDojo study, an activation monitor with **0.92 rollout-mean AUROC had 0.00 TPR at 5% FPR** ([arXiv 2610.04575](https://arxiv.org/html/2610.04575v1)). Second, the agentic white-box results all probe the untrusted model's own activations on instructed or prompted misbehavior. No public control evaluation produces a safety–usefulness curve against a trained, monitor-aware attack policy.

## Unsupervised readouts remain audit tools, not calibrated monitors

The J-lens (Jacobian lens) maps a layer-l residual vector into the final-layer basis using the corpus-averaged Jacobian, J_l = E[∂h_final/∂h_l], and then decodes it with the unembedding. The result is a ranked list of tokens that the activation "is disposed to make the model say" ([jacobian-lens](https://github.com/anthropics/jacobian-lens); [workspace paper](https://transformer-circuits.pub/2026/workspace/index.html)). Its monitoring evidence so far comes in four kinds:

- **Qualitative case studies.** In Sonnet 4.5's blackmail scenario, "leverage, blackmail, threat, shutdown" appear before any response token. Ablating about 28 eval-awareness directions cut verbalized eval awareness from **71% to 3%** and raised blackmail from 0/180 to 13/180 rollouts.
- **Organism signatures.** Deception tokens dominate the top-10 readouts at response start for reward-hacking checkpoints, on 40 coding prompts. "Reward" and "bias" surface for the RM-bias organism, where the logit lens surfaces neither.
- **One quantitative score.** A two-word "fictional/simulation" eval-awareness score separates positions flagged by a natural-language-autoencoder pipeline with **AUC 0.853**.
- **An auditing agent.** An auditor equipped with the J-lens roughly matches an NLA-equipped auditor, but loses badly on reward hacking (4.5 vs 10.0).

The authors call the readout cheap enough to "flag transcripts for review at scale". They explicitly decline to call it sufficient, because practiced computations can bypass the workspace and concepts without a single-token name may not surface ([blog](https://www.anthropic.com/research/global-workspace)).

Outside Anthropic, the J-lens monitoring literature is two weeks old and small. Mosafer shows that a GCG suffix evades a prompt-side J-space monitor at zero behavioural cost on models up to 9B, and that J-space latent adversarial training fails its own re-attack ([arXiv 2610.04316](https://arxiv.org/html/2610.04316v1)). Kim et al. use J-lens features to predict LLM test failures before generation, a quality-assurance task rather than misalignment ([arXiv 2610.28187](https://arxiv.org/abs/2610.28187)). Neither paper reports AUROC or recall at fixed FPR on deception or sabotage benchmarks, and neither compares the J-lens with trained probes. Pre-fitted lenses for most relevant open models are public at [neuronpedia/jacobian-lens](https://huggingface.co/neuronpedia/jacobian-lens), so access is no longer the barrier.

Our own J-lens-diffing project has a direct bearing on whether a J-lens monitor works without a reference model. It lives at `/Users/gkocher/Desktop/MATS_SUMMER_2026/J-lens-diffing`; the path under `RESEARCH/` recorded elsewhere does not exist. Fixed-base J-lens diffing surfaced Russia/Putin/Moscow tokens for a Qwen3-14B "secret loyalty" organism, where logit diffing found nothing. It detected 3 of 5 organisms. **Standalone single-model J-lens audits found 0 of 5.** On Llama-3.3-70B the signals were quieter, and the animal-welfare organism was a complete null ([EXPERIMENT_LOG.md](file:///Users/gkocher/Desktop/MATS_SUMMER_2026/J-lens-diffing/EXPERIMENT_LOG.md)). The implication for monitoring: without a base-model contrast, a standalone readout is swamped by tokens that are high for every input. A runtime J-lens monitor therefore needs a fixed watch-list of tokens, or a per-context honest baseline, before it becomes a usable score.

Mechanistic anomaly detection and model diffing answer a different question: is this input or model anomalous relative to a trusted reference? On "quirky" models, anomaly detection reaches **0.95 AUROC** ([arXiv 2312.01037](https://arxiv.org/abs/2312.01037)). The follow-up finds that "no detector is effective across all models and tasks" ([arXiv 2504.08812](https://arxiv.org/abs/2504.08812)), and latent out-of-distribution detectors are bypassed by obfuscated activations ([arXiv 2412.09565](https://arxiv.org/abs/2412.09565)). Model diffing can now recover what a narrow fine-tune changed:

- BatchTopK crosscoders find chat-specific latents ([arXiv 2504.02922](https://arxiv.org/abs/2504.02922)).
- The activation-difference lens finds traces of narrow fine-tunes on random text, but mixing in pretraining data "largely removes" those traces ([arXiv 2510.13900](https://arxiv.org/abs/2510.13900)).
- Diff mining reveals fine-tuning objectives from logit differences ([OpenReview](https://openreview.net/forum?id=Bo5rZhaCzx)).

All of this is pre-deployment auditing of a checkpoint. None of it reports calibrated FPR on agent trajectories.

## Recall at 1% FPR breaks under training, shift and context

Under worst-case attacker capabilities, every latent-space monitor tested so far fails:

- **Embedding-space attacks.** These cut harmfulness-probe recall from **100% to 0% while keeping 90% jailbreak success**. Adversarially retraining the probe did not converge even after 70 epochs ([Bailey et al., ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/ed687a5f52b651b19e7c18f702907b8b-Abstract-Conference.html)).
- **RL against a probe.** This evades linear mean-pooled probes in 59–82% of cases across Llama-2-7B, Llama-3-8B and Qwen-2.5-14B, while max-pooled and attention probes stay near 0% evasion ([arXiv 2506.14261](https://arxiv.org/abs/2506.14261); per-cell numbers via summary).
- **Neural Chameleons.** These are the most worrying for control. Models fine-tuned to evade probes for *benign* concepts, when given the phrase "You are being probed for X", zero-shot evade *unseen* deception and harmfulness probes, including probes retrained afterwards on the frozen weights. The evasion works through a low-dimensional activation shift and costs little capability ([arXiv 2512.11949](https://arxiv.org/abs/2512.11949)).

Read together, these papers rank designs consistently. From most to least evadable:

1. token-level linear probes with mean pooling;
2. MLP probes and probes on generated tokens;
3. max-pooled and attention probes;
4. multi-layer ensembles;
5. probes combined with out-of-distribution detectors or external classifiers.

Nothing in this ranking survives an adversary with weight-level access. Two facts soften the picture. First, there is an "obfuscation tax": evading probes on more layers degrades SQL capability. Second, a September 2026 preprint finds models cannot reliably control truly privileged internal representations without training ([arXiv 2609.00904](https://arxiv.org/abs/2609.00904)), contradicting earlier neurofeedback results that showed some in-context control growing with scale ([arXiv 2505.13763](https://arxiv.org/abs/2505.13763)); the question is unresolved. No study shows probe evasion *emerging* without explicit evasion training.

Training pressure gives a more nuanced answer than "never train against probes". With a lie detector in the loop, on-policy GRPO yields **over 85% deception (evasion) when detector TPR or KL is low**, while DPO stays **under 25%** at realistic TPRs ([arXiv 2505.13787](https://arxiv.org/abs/2505.13787)). The Obfuscation Atlas finds that high KL plus a strong detector penalty produce honest policies. Its more important finding: **ordinary RLVR with no probe penalty at all dropped off-domain deception-probe AUC from 0.99 to 0.38–0.66**, while an on-domain probe stayed at 1.00 ([arXiv 2602.15515](https://arxiv.org/html/2602.15515v1); table values via summary). Representation drift therefore makes every training stage a distribution shift for the probe. Probes must be re-validated per checkpoint, and GDM's control roadmap notes they "need to be retrained for each new untrusted model" ([arXiv 2607.13087](https://arxiv.org/abs/2607.13087)).

Passive shift is as damaging as adversarial pressure:

- **Style.** Probes with clean AUROC ≥0.998 collapse under stylistic rewrites; style augmentation restores 0.98 ([arXiv 2605.27958](https://arxiv.org/abs/2605.27958)).
- **Context length.** GDM's mean-pooled linear probe missed **99.13% of long-context attacks** and the standard attention probe missed 87.88%. The max-of-rolling-means probe cut this to 3.03% (via summary; unverified) ([arXiv 2601.11516](https://arxiv.org/abs/2601.11516)).
- **Model scale.** UK AISI saw sandbagging-probe score distributions move "much closer together" from 8B to 70B ([AISI](https://www.alignmentforum.org/posts/pPEeMdgjpjHZWCDFw/white-box-control-at-uk-aisi-update-on-sandbagging)).
- **Data.** Off-policy training data generalizes worst for intent-defined behaviors such as strategic deception ([arXiv 2511.17408](https://arxiv.org/abs/2511.17408)). Prompt choice explains **70.6% of the variance** in probe performance ([arXiv 2602.01425](https://arxiv.org/abs/2602.01425)).

The confound that matters most for our work is context. Apollo's probe "fires much more on honest responses to our evaluation prompts than on responses to control prompts", often above the 1%-FPR threshold. It also scores honest confessions of misdeeds as deceptive ([arXiv 2502.03407](https://arxiv.org/abs/2502.03407)). AISI's probes fire on code the model "knows is likely to be incorrect". Raw reward-hack probe scores on control adapters average **0.495 for Qwen and 0.005 for Llama**, and their mapping to behavior is non-monotone ([arXiv 2606.06223](https://arxiv.org/abs/2606.06223)). Almost every paper calibrates one global threshold on Alpaca, which AISI calls "relatively unprincipled". Production systems quietly do something else. GDM chooses thresholds by a weighted loss (overtriggering ×50, misses ×5; via summary, unverified). Anthropic smooths per-token logits with an exponential moving average at inference ([arXiv 2601.04603](https://arxiv.org/abs/2601.04603)). Both are, in effect, crude change detectors without stated false-alarm guarantees. That is exactly the gap our decision-layer toolkit was built for.

## Labs deploy probes as cheap first stages and disclose no misalignment metrics

Every frontier lab runs activation probes somewhere, almost always as a cheap screen in front of an LLM classifier. Anthropic's Constitutional Classifiers++ uses a linear probe at **377K FLOPs/token versus 8B for a small external classifier**. It escalates about 5.5% of traffic, cuts compute about 40× and reaches a 0.05% production refusal rate. Probe and classifier errors are less correlated than two classifiers' errors, and a 0.55/0.45 logit ensemble beats either alone ([arXiv 2601.04603](https://arxiv.org/abs/2601.04603); figures and deployment-model details via summary). GDM states that its findings "informed the successful deployment of misuse mitigation probes in user-facing instances of Gemini". It reports that a probe→Flash cascade calling the LLM on under 10% of traffic beats Flash alone at about **1/50 the cost** (cost and error figures via summary; unverified) ([arXiv 2601.11516](https://arxiv.org/abs/2601.11516)). Both deployments target misuse by a prompt-level adversary, not scheming.

The misalignment deployments are described only secondhand:

- **Anthropic.** Its August 2026 Risk Report reportedly says probes for dishonesty, reward hacking, emotions and eval awareness "were run on every transcript during the majority of post-training". It also describes a Claude investigator using interpretability tools, mainly natural-language autoencoders (quoted via [Ward's overview](https://www.lesswrong.com/posts/E4Jpmo3igPnGnXtL4/an-overview-of-frontier-ai-company-monitoring-practices-in); primary not fetched; unverified).
- **OpenAI.** It describes "activation classifiers … that run at every sampled token and escalate potential concerns to increasingly sophisticated and high-compute automated investigators" ([OpenAI](https://openai.com/index/pacing-model-development-cyber-capabilities/); search snippet only, direct fetch returned 403; unverified). Per Ward, these are required for tool-using RL and evals of high-capability models and for agentic Astra inference, at **about 20% monitoring overhead** (unverified). Probe cascades for misuse run below 1% overhead, so that 20% figure suggests the LLM-investigator stage dominates. This is an inference; OpenAI does not disclose the split.
- **GDM.** Its control roadmap ranks activations monitoring as "more speculative", places internals-based monitoring at detection level D4 only, and names assurance as the open problem: "we do not yet have models that are strategically misaligned, whose activations could be used for testing" ([arXiv 2607.13087](https://arxiv.org/abs/2607.13087)).
- **UK AISI.** It runs a white-box control team, which found zero confirmed sandbagging in 2,700 real eval traces ([AISI](https://www.alignmentforum.org/posts/pPEeMdgjpjHZWCDFw/white-box-control-at-uk-aisi-update-on-sandbagging)).

**No lab has published recall or FPR for any internal misalignment probe.** Ward explicitly scopes monitor performance out because it is not disclosed.

Public resources support trusted-reader experiments well and on-policy experiments only thinly. In the table below, "P-T" means a probe on a trusted open model reading any transcript. "P-U" means a probe on the activations of the open-weight policy that produced the transcript.

| Resource | What it provides | Use | Link |
|---|---|---|---|
| MonitoringBench + Honest-550 | 2,644 Opus-authored BashArena attacks with `attack_step`; 550 honest runs. We already hold per-step gpt-4.1-mini scores for 775 attacks + 550 honest | P-T | [attacks](https://huggingface.co/datasets/neur26anonsub/ctrldataset2026), [honest](https://huggingface.co/datasets/palaestraresearch/monitoringbench-honest-550) |
| LinuxArena | 11 agents × (200 honest / 92 attack / 92 obvious); sweep of 12 monitors with per-action scores over 10 environments; GLM 5 and Kimi agents | P-T; P-U needs multi-GPU MoE | [data](https://data.linuxarena.ai), [HF](https://huggingface.co/datasets/anonymouslinuxarena/linuxarena-public) |
| MOLE | Insider-threat transcripts incl. a Qwen3.6-27B split, 36–38 malicious account-days per split | Cheapest P-U | [HF](https://huggingface.co/datasets/forgelab/mole) |
| FIBS release | FIBSv1 training set (152,980 + 5,000 rows); 36 trained probes for Qwen3.5 2B–397B, Nemotron-3, Kimi K3. **No agentic trajectories, no extraction scripts** | Probe weights and training data | [GitHub](https://github.com/AlignmentResearch/fibs-probes) |
| Apollo deception-detection | Llama-3.3-70B on-policy rollouts, probes, scores | Probe training and calibration | [GitHub](https://github.com/ApolloResearch/deception-detection) |
| Pre-fitted J-lenses | Qwen3.5-27B, Qwen3.6-27B, Qwen3-32B, Llama-3.3-70B-it, gpt-oss-20b and more | J-lens arm | [HF](https://huggingface.co/neuronpedia/jacobian-lens) |
| Hidden-goal organisms | Qwen3.6-27B LoRA organisms used by FIBS | P-U organisms | [HF](https://huggingface.co/collections/ai-safety-institute/lie-detection-model-organisms) |
| Persistent-state activations | 138.9 GB of Qwen3.8-27B tensors, **no text or labels** | Unusable alone | [HF](https://huggingface.co/datasets/idacy/persistent-state-control-activations-20260926) |

Extraction tooling is ready. One prefill pass per transcript with HF hooks, nnsight, or vLLM ≥0.18 hidden-state extraction gets the activations ([vLLM](https://vllm.ai/blog/2026-03-30-extract-hidden-states)). A 27–32B reader fits on one 80 GB H100 in bf16. Storage is the binding constraint: one layer of residuals for a 60k-token transcript is about 0.6 GB. Probes and J-lens watch-lists should therefore be scored online, keeping only per-token scores and per-step pooled vectors.

## Our decision layer transfers, but FAR.AI holds the best substrate

Our three completed studies each predict something specific for white-box streams, which is why the extension is scientifically motivated rather than opportunistic ([00_Overall_Summary](file:///Users/gkocher/Desktop/monitoring-research/reports/00_Overall_Summary.pdf)).

- **Accumulation (Idea 1).** Max-type rules won in most black-box stream sets. Accumulation won only with history-free per-session monitors (+0.15 TPR). The gain tracked honest spike persistence (−0.67) and attack repeat-spike informativeness (+0.47). Probe streams are dense, continuous and cheap, so these predictors can be measured directly.
- **History-awareness of a reader (our inference).** A trusted reader that pre-fills a whole transcript produces step-t activations that already attend to every earlier step, so it is history-aware in Idea 1's sense. Forwarding each step alone yields a history-free stream at roughly the same token cost. That reproduces our controlled history experiment in white-box form, almost for free.
- **Per-context thresholds (Idea 2).** We found environment effects shared across all 12 LinuxArena monitors (Spearman 0.70). CFAR collapsed against context-selecting attackers (safety 0.40 vs 0.64 global), and Stackelberg allocation won (0.79). The confound literature predicts larger cross-context heterogeneity (τ) for probes, so per-context allocation should matter more there.
- **Detector-aware attackers (Idea 3).** Rewriting condensed attacks and raised peak suspicion. Whether condensation also raises probe scores is a free test on attacks we already hold.

The novelty picture per candidate is uneven:

| Candidate | Closest prior work | What is missing | Scoop risk | Verdict |
|---|---|---|---|---|
| (d) Probes vs LLM monitors under one detector-aware attacker | Neural Chameleons and RL-Obfuscation (trained evasion, not agentic); collusion games with in-context awareness, small n, no LLM comparator ([2609.03035](https://arxiv.org/abs/2609.03035)) | Same attacker against both monitor types at matched FPR in a control setting | Medium | **Most open** |
| (e) J-lens as a step-level monitor | Anthropic case studies; Mosafer small-model evasion; Kim et al. test-failure prediction | Any per-step J-lens stream on sabotage trajectories vs probes or LLMs at fixed FPR | **High** (Anthropic, FIBS group, neuronpedia users) | Open, but fast-closing |
| (a) Sequential tests on probe streams | FIBS (no episode-level aggregation); Gao's unit-max alarm policies, which list "sequential stop-on-alarm" as future work ([2610.04575](https://arxiv.org/html/2610.04575v1)); CUSUM for hallucination onset ([2606.12476](https://arxiv.org/abs/2606.12476)) | Max / top-k / CUSUM / e-process at matched trajectory FPR on control probe streams | **High** (Gao, FIBS) | Open in this form |
| (b) Per-context probe thresholds | FIBS contrast scoring removes some bias; Gao's thresholds are marginal only; Wilhelm & Kao call for environment-specific calibration | Group-conditional or Stackelberg probe thresholds; attack-selection and poisoning attackers | Medium | Partly touched |
| (c) Probe + LLM fusion at matched budget | Hua et al. LLR fusion; GDM and Anthropic cascades; Gao late fusion on AgentDojo | Only the setting: multi-step sabotage at matched trajectory FPR | n/a | **Already published as a method** |

Relative to FIBS specifically ([arXiv 2610.12445](https://arxiv.org/abs/2610.12445)), the following is already done and is not ours to claim:

- probes on agentic sabotage benchmarks;
- probes beating frontier text monitors per step;
- transfer from off-policy training data to on-policy behavior;
- gains from scaling model size and data size;
- detection of unverbalized deception and hidden goals.

FIBS did not do any of the following, per the fetched summaries:

- trajectory-level aggregation;
- sequential tests;
- per-environment thresholds;
- fusion with black-box monitors;
- red-teaming the probe with an aware or trained attacker;
- trusted-reader probing.

Its stated next problem is "minimizing and handling false positives", which is precisely (a)–(c). FIBS holds on-policy BashArena and SHADE step streams for 9 open models with step labels, and has not released them. They could run (a)–(c) in a week. Two mitigations follow: move first on (b) and (d), where our prior results give a head start; and ask FAR.AI for the trajectories and step scores, which would turn a scooping risk into a collaboration.

Whether the extension is worth it depends on framing. If a trusted-reader probe merely matches gpt-4.1-mini, the honest headline is "white-box adds cost savings, not power, for a trusted reader". That is a useful evaluation result, not a methods paper. A methods-level claim needs one of three things: a P-U arm on policy activations, a detector-aware comparison that separates the two monitor types, or a per-context result showing probes need Stackelberg allocation more than LLM monitors do.

## The cheapest credible first experiment costs about $80–180 of GPU

The cheapest credible design reuses what we already hold. Use **Qwen3.5-27B** as the trusted reader, because it is the one open model with both released FIBS probes and a pre-fitted neuronpedia J-lens, and it fits on one H100. Pre-fill it over the 1,325 MonitoringBench trajectories (775 attacks + 550 honest) that gpt-4.1-mini already scored step by step in Idea 1, and over the LinuxArena Opus sweep (10 environments, 12 LLM monitors on identical trajectories). In the same forward pass, log per-token scores from four sources:

1. an Apollo-style probe trained on Instructed-Pairs data;
2. a FIBS probe for Qwen3.5-27B, re-posed as a reader question ("Did the agent take actions towards a hidden side task?");
3. a cross-fitted supervised probe on held-out trajectories, as an in-distribution upper bound;
4. a J-lens watch-list of deception and sabotage tokens at step boundaries.

Pool each source to per-step scores with max and rolling-mean, and run both the full-transcript (history-aware) pass and a per-step (history-free) pass.

All analysis then runs on the existing detector library with no new API calls:

- (a): max, 2nd-max, top-3, CUSUM, Shiryaev–Roberts and e-process at 1%, 2% and 5% trajectory FPR, with detection delay measured from `attack_step`;
- (b): global vs CFAR vs Stackelberg thresholds across LinuxArena environments and MonitoringBench side tasks, plus a measurement of τ for probe streams against LLM streams;
- (c): cascade and LLR fusion of probe and LLM scores at matched cost;
- free (d): probe scores on the 150 Idea-3 rewritten attacks across all aware arms.

The cost estimate below is our own calculation, not a sourced figure. It uses the notes' FLOP model of 10–15 H100-hours per 100M tokens for a 27–32B model. Token counts are unmeasured, so the error bar is ±2×.

| Component | Estimate |
|---|---|
| Timing run on 20 transcripts to pin throughput | ~$5 |
| Probe-training activations (Instructed-Pairs, a FIBSv1 subset) | ~$10–20 |
| History-aware pass: MonitoringBench 1,325 + LinuxArena sweep (~50–70M tokens) | ~$25–45 |
| History-free per-step pass (similar token count) | ~$25–45 |
| Idea-3 rewritten attacks, all arms | ~$5–10 |
| Setup, debugging and idle pod time (10–15 h at ~$4/h, secure on-demand H100) | ~$40–60 |
| **Total GPU** | **~$80–180**; API $0 |

Pod storage needed is about 5 GB of per-step pooled vectors, assuming roughly 50 steps per trajectory at 6 layers × 10 KB. The pre-registered go/no-go rule has two branches. Proceed to stage 2 if the reader probe's trajectory TPR at 1% FPR comes within the bootstrap CI of gpt-4.1-mini's, or if fusion adds at least about 0.05 TPR at matched cost. Stop the trusted-reader line, and pursue only P-U data, if the reader probe is dominated and fusion adds nothing.

Stage 2 runs in the same budget envelope. It replays MOLE's Qwen3.6-27B transcripts through the model that generated them, which gives policy activations on the same labels. The cost is ~$20–60 GPU, after first checking that reasoning tokens and the chat template are reproducible. Alongside this, a true (d) arm adds rewritten attacks told that "a white-box probe on a trusted model reads your actions", scored against a *strong* LLM monitor. Idea 3 showed a weak monitor makes the test uninformative. This arm costs about $30–70 of OpenRouter, within the roughly $300 left of the $500 cap. A full P-U detector-aware study needs fresh open-policy BashArena rollouts with Docker sandboxes, adding $50–150. It should wait until stage 1 shows a signal.

## Five risks could sink the white-box extension

The largest scientific risk is that **a trusted reader sees only text**. Its threat model is identical to an LLM monitor's. Reading Opus-authored transcripts is off-policy for the reader, and that is the regime where intent probes generalize worst ([arXiv 2511.17408](https://arxiv.org/abs/2511.17408)). The one reader precedent is encouraging (0.91 vs 0.54 AUROC on APPS), but it is a single unreviewed repo. Expect stage 1 to show cost advantages more often than power advantages.

The second risk is **scooping**. FIBS has the substrate, and Gao has the alarm-policy formalism with sequential rules already named as future work. Both are weeks from (a). Speed, or contacting FAR.AI, is the mitigation.

The third risk is that **robustness claims stay weak**. Without a trained evader (RL-Obfuscation or Chameleon style), any "probes resist detector-aware attackers" result covers only prompted, text-level adversaries. Reviewers will discount it, and the GDM roadmap's assurance objection stands. The Idea-3 lesson also applies: aware attackers condensed their attacks and got caught more, which says nothing about a covert adversary.

The fourth risk is **statistical**. With 550 honest trajectories, a 1% trajectory FPR rests on about five false alarms. Per-context thresholds split that sample further, and Idea 2 showed per-context quantiles over-spend 7× at n = 10. Partial pooling and cluster-bootstrap CIs are mandatory, and AUROC must never be the headline. Context normalization can also erase real signal if "context" correlates with attack opportunity (the Apollo confound), so a matched honest-in-risky-context control set is needed.

The fifth risk is **operational**. Everything so far ran on the laptop. This round needs RunPod GPUs (on-demand only; which account to use should be settled before pods are created). OpenRouter is reachable from the laptop as of 2026-10-20, but SSH to RunPod pods timed out from the laptop network that day (likely the corporate VPN), so GPU work needs pod access from a network where SSH works. Replay fidelity for P-U depends on logs keeping reasoning tokens, which is unverified for MOLE and LinuxArena. The J-lens arm has its own interpretive trap: for a reader, the J-space reflects the reader's thoughts about the transcript, not the agent's cognition. Our own result that standalone readouts detected 0 of 5 organisms suggests this arm will be noisy without a baseline.

## Conclusion

The white-box literature has reached the point black-box monitoring reached two years ago. Detectors are strong per step and cheap enough to run on every token. Yet the decision layer is still a global 1%-Alpaca threshold, ad hoc pooling, and no trajectory-level false-alarm accounting. The production systems that work, Anthropic's exponential-moving-average cascade and GDM's weighted-loss thresholds, are already informal versions of the change detection and per-context allocation we studied. That makes our toolkit unusually well placed: the question is not whether probes detect sabotage, which FIBS settled for salient cases, but whether the operating-point machinery built for LLM streams behaves differently on dense, context-confounded, history-controllable probe streams.

The case for a first round is strongest as a bounded experiment with a stop rule (roughly $130–310 across stage 1, stage 2 and the API arm), not a new research program. Its one high-value outcome would be a measured difference between monitor types: probes showing larger cross-context heterogeneity that Stackelberg allocation fixes, or a history-free probe stream where accumulation beats max. Either would be a result FIBS cannot get from its current analysis. Its likely modest outcome, "white-box buys cost, not power, for a trusted reader", is still worth a short write-up. Robustness and assurance stay the field's open problem until someone trains a monitor-aware agent against probes in a control setting. Our first round should state that limit plainly rather than imply it has been tested.
