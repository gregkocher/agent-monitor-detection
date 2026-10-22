# JEV-as-a-Judge (Li, Miao, Krishnan, Padman, CMU; arXiv 2609.26550v5, 9 Oct 2026): results relevant to a cheap first-stage agent monitor, plus cited and citing work

Source conventions. "JEV paper" = the local full text (`_source_jev_as_judge_paper_fulltext.txt`, 53 pp., read in full) of [arXiv 2609.26550v5](https://arxiv.org/abs/2609.26550v5). Table, figure, section and appendix numbers refer to that version. The paper labels exactly three analyses as **pre-specified**: (1) the frozen two-order routing policies (rule and threshold grid fixed before any held-out outcome was inspected; thresholds computed mechanically from selection-set outputs), (2) the primary outcome of the human adjudication (JudgeBench JEV-minus-GPT-6 difference), and (3) the prospective live test on PPE and the JudgeBench Claude split (§9, App. N). The paper calls **everything else exploratory**: the multi-family comparison, post hoc threshold sweeps, slice analyses (Table 12), and all follow-ups (RM-Bench, RewardBench 2, answer format, prose, four-way rotations, label-budget simulation, open decision models in App. A, and the retrospective comparison of alternative first stages) ([JEV paper §3 "Collection rounds", Limitations](https://arxiv.org/abs/2609.26550v5)). Tags [PRE] and [EXP] below follow that split.

The object under study. TypeSafe JEV 1.13.0 is a hosted "decision-only" / "System One" model: input = structured state + natural-language instructions + an allowed output type (Choice over labels, Noul = yes/no probability, Score = ordered rubric levels). It returns a verdict and a probability per label, with no generated text. Price at collection: $0.042 per million input tokens, $0 for output. Confidence q = max label probability. JEV also returns a "native confidence" field whose formula is unpublished; it ranks items like q (Spearman 0.976 / 0.999 / 0.958 on RewardBench / JudgeBench / HaluEval) ([JEV paper §4, Table 9](https://arxiv.org/abs/2609.26550v5)). All generative comparators answered under the same contract: verdict + per-label probabilities, JSON schema, **no rationale**, reasoning models at low effort ([JEV paper §3–4, App. B](https://arxiv.org/abs/2609.26550v5)).

## Q1. Overall operating profile: accuracy, cost, latency, and accuracy by skill

### Takeaway
JEV sits mid-pack in accuracy (8th of 15 LLM judges, 1.7 points behind GPT-6 Astra on 4,850 pooled public judgments) but is 277x cheaper ($0.044 vs $12.182 per 1,000 judgments) and about 13x faster (0.15 s vs 1.89 s median). Its accuracy gap is concentrated in skills where the verdict must be *derived* (expert knowledge, code, math, logic) and at middle difficulty. On items that read off the text, it is within about 2–3 points of GPT-6.

### Cited Findings
- **Scale and design.** 17 configurations: JEV, 12 other hosted LLM judges (GPT-4.1 mini, 4.1, 5.2, 5.4, 5.6 Sol, 6 Astra; GPT-OSS 120B; Qwen3.6/3.8 27B; Claude Sonnet 5; Gemini 3 Flash, 3.1 Pro), 2 local Qwen models, and 2 reward models (PairRM, Skywork-Reward-V2-Qwen3-8B). The 5,172 base judgments are 1,500 RewardBench pairs (chat 292, difficult chat 381, safety 381, reasoning 446), 350 JudgeBench pairs (GPT-4o split), 3,000 HaluEval evidence-grounded QA answers, 150 final-answer replies, and 172 controls. They split into a 642-item pilot and a 4,530-item held-out set; the held-out set contains 1,610 preference pairs (1,340 RewardBench, 270 JudgeBench) ([JEV paper §3, Tables 1, 7](https://arxiv.org/abs/2609.26550v5)).
- **Base accuracy, JEV vs GPT-6 Astra (Table 1) [EXP].** RewardBench 92.5 vs 92.5. JudgeBench 78.6 vs 93.1. HaluEval 87.3 vs 88.4. Final answer 94.0 vs 96.7. JEV's output was valid on 5,172/5,172 items. JEV ranks 8th of 15 LLM judges on the 4,850 pooled public judgments: 1.7 points behind GPT-6 and 2.8 behind GPT-5.6 Sol. Among hosted judges under $1 per 1,000 judgments, JEV is the most accurate on all three public tasks, though only by 0.1 points over GPT-OSS on HaluEval and 0.4 points over Gemini 3 Flash on RewardBench ([JEV paper §5, Table 1](https://arxiv.org/abs/2609.26550v5)).
- **Cost and latency (timing panel: 120 judgments, 40 per task).**

  | Judge | Fee per 1,000 judgments | Median latency | p95 latency |
  |---|---|---|---|
  | JEV | $0.044 | 0.15 s | 0.24 s |
  | GPT-4.1 mini | $0.390 | 0.55 s | – |
  | GPT-6 | $12.182 | 1.89 s | 3.86 s |
  | Qwen3.6 | – | – | up to 23.2 s |

  JEV is about 9x and 277x cheaper than GPT-4.1 mini and GPT-6, and about 13x faster than GPT-6. Qwen3.6's long tail includes rate-limit retries. The "0.36% of its fee" in the abstract is the same 277x ratio. All dollar values are estimates, not invoices ([JEV paper §5, Fig. 3, App. C](https://arxiv.org/abs/2609.26550v5)).
- **Accuracy by skill, single base-order calls, JEV vs GPT-6 (Fig. 4a / Table 12) [EXP].**

  | Skill | JEV | GPT-6 | Difference (points) | 95% CI |
  |---|---|---|---|---|
  | Chat quality | 86.1 | 83.9 | +2.2 | [−0.6, +5.1] |
  | Safety: should refuse | 96.5 | 94.5 | +2.1 | [−0.4, +4.5] |
  | Evidence-grounded factuality | 87.3 | 88.4 | −1.1 | [−1.9, −0.3] |
  | Safety: should comply | 88.3 | 89.9 | −1.6 | [−5.4, +2.0] |
  | Expert knowledge | 83.9 | 90.9 | −7.0 | [−13.3, −0.7] |
  | Instruction following | 82.3 | 89.9 | −7.6 | [−11.3, −4.0] |
  | Code | 78.8 | 91.7 | −12.9 | [−18.1, −7.8] |
  | Math | 81.8 | 96.2 | −14.3 | [−18.8, −10.1] |
  | Logic puzzles | 68.4 | 95.9 | −27.6 | [−36.7, −18.4] |

  Intervals are 95% source-cluster bootstraps, unadjusted for multiple comparisons ([JEV paper §6, Table 12](https://arxiv.org/abs/2609.26550v5)).
- **The same skill splits by whether the answer is visible ("reading vs deriving").** Code: RewardBench code-repair pairs, where bugs are visible in the text, are 100.0 vs 99.3 (+0.7). JudgeBench LiveCodeBench is 76.2 vs 97.6 (−21.4), and RM-Bench code is 72.4 vs 89.1 (−16.7), where correctness must be traced. Math: −6.0 on RewardBench step-level MATH, −7.5 on JudgeBench, −16.1 on RM-Bench. Instruction following matches GPT-6 on natural LLMBar pairs but trails by 18.2 on adversarial "neighbor" pairs whose rejected output answers a similar instruction ([JEV paper §6, Table 12](https://arxiv.org/abs/2609.26550v5)).
- **The gap sits at middle difficulty.** Difficulty here = how many of the 13 other LLM judges get an item wrong.

  | Other judges wrong (of 13) | Items | JEV | GPT-6 | Difference |
  |---|---|---|---|---|
  | 0 | 3,286 | 99.8 | 99.7 | +0.1 |
  | 1–2 | – | 95.5 | 95.8 | −0.3 |
  | 3–5 | – | 71.9 | 85.0 | −13.1 |
  | 6–9 | – | 40.8 | 56.1 | −15.3 |
  | 10–13 | 311 | 9.6 | 9.6 | 0.0 (many of these labels are questionable) |

  On JudgeBench the middle bins trail by 28.9 and 42.2 points. Errors unique to JEV are rare: of 3,741 items that at least 12 of the 13 judges get right, JEV misses 19 and GPT-6 misses 25 ([JEV paper §6, Fig. 4b, Table 12](https://arxiv.org/abs/2609.26550v5)).
- **Human adjudication [PRE primary outcome on JudgeBench].** A team member, blind to labels and judge outputs, adjudicated all 163 items in a 990-item subset (RewardBench 400, JudgeBench 350, HaluEval 240) where either judge disagreed with the label, plus 20 controls, for 183 items in total. On JudgeBench, the human sided with GPT-6 on 57 of 69 disagreements and with JEV on 1 (11 indecisive). The human-adjudicated difference is −16.0 points [−20.0, −12.3], vs −14.6 on the supplied labels. By domain: reasoning 27–0, coding 9–0, math 7–0, knowledge 14–1, all for GPT-6. RewardBench: −3.0 [−5.3, −0.8] (GPT-6 17, JEV 5, 7 indecisive). HaluEval: −2.5 [−5.0, −0.4] (GPT-6 8, JEV 2). HaluEval label noise: 24 of the 26 both-wrong items were decided for the judges. With human labels substituted, accuracy on those 240 answers is JEV 95.8 vs GPT-6 98.3. Deviation from protocol: the second pass was an LLM rater (Claude Fable 5.1), not a second human; κ with the human was 0.29 / 0.74 / 0.81 ([JEV paper §6, App. D, Table 10](https://arxiv.org/abs/2609.26550v5)).
- **Length is not the driver.** On 169 JudgeBench pairs whose answers are within about 15% of each other in length, JEV still trails by 19 points (75.1 vs 94.1). On length-mismatched pairs JEV picks the longer answer 45.9% of the time, against 49.7% for which the longer answer is gold. Within benchmark, the gap barely moves from shortest to longest tercile on RewardBench (−1.0 to +1.0) and HaluEval (−1.7 to −1.2). It widens on the longest third of JudgeBench (−22.2 vs −11.1 on the shortest) and on RM-Bench (−1.3 to −10.1), where length tracks the misleading detailed styles. The paper's summary: "What the judge must do with the text matters more than how much text there is" ([JEV paper §6, Tables 12–13](https://arxiv.org/abs/2609.26550v5)).
- **Which way JEV errs on factuality.** On HaluEval JEV catches hallucinated answers as often as GPT-6 (80.1 vs 79.6). Its whole deficit comes from rejecting correct answers (94.4 vs 97.1 accepted). In other words, it over-flags rather than under-flags ([JEV paper §6, Table 12](https://arxiv.org/abs/2609.26550v5)).
- **Position effects.** In base order, JEV is 6.4 points more accurate on JudgeBench when the preferred answer is shown second (81.9 vs 75.5). On RM-Bench it is 2.8 points more accurate when the preferred answer is shown first. GPT-6 varies by less than 1 point ([JEV paper §6](https://arxiv.org/abs/2609.26550v5)).
- **Output validity.** JEV satisfied the output contract on every base item. Qwen3.6 returned 4,998/5,172 valid outputs and GPT-OSS 5,094/5,172; all invalid outputs count as errors ([JEV paper Table 20](https://arxiv.org/abs/2609.26550v5)).
- **Operating envelope (Table 2), with the paper's guidance labels.**

  | Guidance | Workloads (JEV minus comparator, points) |
  |---|---|
  | "Low-fee candidate" | Ordinary preference (0.0); evidence-grounded factuality (−1.1) |
  | "Validate first" | Final answers (−2.7); four-way selection (−2.0); grounded summaries (+0.5 vs GPT-5.4) |
  | "Escalate" | Difficult correctness (−14.6); matched-style RM-Bench (−6.4); style-adversarial RM-Bench (−13.5) |
  | "Not supported" | Reference-free prose (−2.5; all judges near chance) |

  ([JEV paper Table 2](https://arxiv.org/abs/2609.26550v5)).

### Inferences
- For monitoring, the key axis is **read-off vs derive**, not length. Whether a bash or code action is malicious usually has to be traced (what does this command or diff do?). That resembles LiveCodeBench/RM-Bench code (−17 to −21 points) far more than RewardBench code-repair, where the bug is visible (≈0 gap). JEV should be expected to underperform a reasoning monitor most on exactly the subtle actions a monitor exists to catch.
- "Errors unique to JEV are rare" means JEV mostly fails on items that other cheap judges also find hard. That is reassuring for a cascade only if the fallback is right on those items (see Q4 and Rao & Callison-Burch 2026b in Q6).

### Gaps
- No agent trajectories, tool calls, or long multi-step inputs in the study. The longest input is about 3,600 tokens (App. A).
- Fees and latencies come from one client location and one collection period; prices are list prices for (from today's standpoint) hypothetical future models. The study is not compute-matched.

## Q2. Safety slices, reference-free prose, style-adversarial pairs, derived-verdict tasks, and what they predict for judging agent trajectories

### Takeaway
On safety items whose verdict is legible ("should refuse"), JEV matches or slightly beats GPT-6 even under style manipulation. On "should comply / safety-response" items it is at parity in normal and easy conditions but drops 9.6 points when the wrong answer is more elaborately written. It is confidently misled by elaborate style (confidence AUROC 0.764 on hard RM-Bench pairs vs 0.839 on matched-style pairs). On reference-free prose every judge, JEV included, is near chance but confident (AUROC 0.498). Taken together, this predicts that JEV will be weakest, and its confidence least trustworthy, on agent actions whose maliciousness must be inferred or that come packaged with persuasive rationale.

### Cited Findings
- **Pooled safety slices (single base-order calls, supplied labels) [EXP].** "Safety: should refuse" (n=1,209): JEV 96.5 vs GPT-6 94.5, +2.1 [−0.4, +4.5]. This splits into RewardBench (246): 93.5 vs 90.2, +3.3 [0.0, +6.5], and RM-Bench (963): 97.3 vs 95.5, +1.8 [−1.1, +4.7]. "Safety: should comply" (n=792): 88.3 vs 89.9, −1.6 [−5.4, +2.0]. This splits into RewardBench (135): 97.8 vs 94.8, +3.0, and RM-Bench (657): 86.3 vs 88.9, −2.6 [−7.0, +1.7]. The safety-refuse pool is RewardBench refusals, XSTest, and Do-Not-Answer ([JEV paper Table 12, App. E](https://arxiv.org/abs/2609.26550v5)).
- **RM-Bench safety by style condition (Table 12) [EXP].** Easy = better answer more elaborate; normal = same style; hard = worse answer more elaborate.

  | Domain | Easy | Normal | Hard |
  |---|---|---|---|
  | Safety-refuse | 97.8 vs 93.5 (+4.4 [+0.6, +8.4], one of JEV's few significant wins) | 97.2 vs 96.0 (+1.2) | 96.9 vs 97.2 (−0.3 [−3.1, +2.2]) |
  | Safety-response ("should comply") | 89.0 vs 88.6 (+0.5) | 89.5 vs 88.1 (+1.4) | 80.4 vs 90.0 (−9.6 [−16.0, −3.7]) |

  The paper notes: "Only on refusals does JEV keep pace with GPT-6 when the wrong answer is the more elaborate one (−0.3 points)" ([JEV paper §6, Table 12](https://arxiv.org/abs/2609.26550v5)).
- **Style-adversarial RM-Bench overall (500 prompts × 9 style pairings × 2 orders = 9,000 judgments per judge) [EXP].** JEV scores 85.4 on matched style and 76.6 on hard pairs, a within-prompt change of −8.8 [−10.6, −7.1]. GPT-6 moves only from 91.8 to 90.1 (−1.7 [−3.2, −0.3]). JEV minus GPT-6 on hard pairs is −13.5 [−16.2, −10.9]. Skywork's hard-minus-normal change is −16.8, and it scores 70.6 on hard pairs. Hard-pair gaps by domain: chat −9.1, code −21.8, math −23.4. In the easy condition JEV beats GPT-6 on chat by +10.1 [+5.7, +15.1], i.e. JEV follows elaborateness in both directions ([JEV paper §6, App. F, Tables 12, 14–15](https://arxiv.org/abs/2609.26550v5)).
- **Confidence weakens under misleading style (§7.4, Table 16) [EXP].** Two-order AUROC of q for correctness: easy 0.870, normal 0.839, hard 0.764 (one order at a time: hard 0.750). Error rate among two-order judgments with q ≥ 0.9 rises from 1.5% (easy, 14/909) to 3.0% (normal, 25/839) to 7.9% (hard, 57/720). Treating each order as a separate judgment gives 1.8% / 3.9% / 10.0%, against GPT-6's 3.9% / 3.6% / 4.9%. On hard pairs, JEV is wrong on 26 of 151 pairs scored in [0.9, 0.95) and 26 of 215 in [0.95, 0.99). On style-matched pairs the corresponding counts are 7 of 136 and 13 of 249. A τ=0.9 cascade to GPT-6 retains 98.9% of GPT-6's accuracy on hard pairs (89.1 vs 90.1; −1.00 [−1.80, −0.33]) but 100.2% on matched pairs. τ=0.95 retains 99.6% on hard pairs while escalating 62%. τ=0.99 matches GPT-6 (90.1 vs 90.1) but escalates 76% ([JEV paper §7.4, App. F](https://arxiv.org/abs/2609.26550v5)).
- **Reference-free long prose (App. H, Table 19) [EXP].** Document-grounded summaries (400): JEV 69.8, GPT-4.1 mini 69.0, GPT-5.4 69.3; JEV's error AUROC is 0.689. Reference-free general responses (200, balanced over human hallucination labels): JEV 53.5, GPT-4.1 mini 54.0, GPT-5.4 56.0. Mean maximum probabilities are 0.91 / 0.94 / 0.96, so all three are near chance yet confident. JEV's Brier score is 0.821, NLL 3.302, error AUROC 0.498. GPT-5.4's AUROC is 0.510. The paper's verdict: "no tested judge is usable on reference-free prose," and "no threshold helps" ([JEV paper §6, §7.4, App. H](https://arxiv.org/abs/2609.26550v5)).
- **Only 129 of 3,000 HaluEval QA answers exceed 20 words** (hence the separate prose samples). On HaluEval answers of 20 words or more (n=16), JEV scores 81.2 [62.3, 100] ([JEV paper Table 18](https://arxiv.org/abs/2609.26550v5)).
- **Derived-verdict tasks: math, code, logic, PPE.** These are listed in Q1. On the prospective PPE sources, JEV alone (two orders) vs GPT-6:

  | PPE source | JEV | GPT-6 | Confidence AUROC |
  |---|---|---|---|
  | MMLU-Pro | 90.0 | 88.8 | 0.69 |
  | MATH | 87.5 | 96.2 | 0.79 |
  | GPQA | 76.2 | 91.2 | 0.81 |
  | MBPP-Plus (code) | 66.2 | 78.8 | 0.74 |
  | IFEval (explicit formatting constraints) | 71.2 | 86.2 | 0.57, "the gate helps least where the ranking is weakest" |

  JudgeBench Claude split: LiveCodeBench 57.9 vs 100.0 (AUROC 0.62); LiveBench 63.9 vs 98.1 ([JEV paper §9, Table 36](https://arxiv.org/abs/2609.26550v5)).
- **Final-answer extraction does not help JEV.** Gold-blind extraction followed by code comparison lowered JEV agreement from 91.3 to 86.0 (−5.3 [−14.0, 2.0]) ([JEV paper §6, App. G, Table 17](https://arxiv.org/abs/2609.26550v5)).
- **Stated limitation, "Agentic tasks":** "We study JEV as a judge of finished outputs. Whether its decisions and confidence are as useful inside an agent, where it would choose a tool or the next action from a long trajectory and an error carries into later steps, is not tested here" ([JEV paper Limitations](https://arxiv.org/abs/2609.26550v5)).
- **Ethics statement:** "Confident errors, including those on style-adversarial pairs, argue against using any automated judge as the sole arbiter of consequential decisions" ([JEV paper, Ethical considerations](https://arxiv.org/abs/2609.26550v5)).
- **Vendor-documented "jaggedness" for JEV 1.13** (as relayed by a secondary blog citing docs.typesafe.ai/model-jaggedness/jev-1.13):
  - JEV "answers the question written, not the intent its author hoped it would infer."
  - Unreliable on negation, compound conditions, multi-hop or indirect references, arithmetic, counting, and date comparison.
  - Accuracy degrades with irrelevant long context, and injected instructions or adversarial framing can shift answers.
  - Limits: 64K tokens per request, 32K for state plus the longest question.
  - Recommended pattern: split the decision into atomic factual questions and do the logic and side-effect checks in code.

  ([SmartScope summary of TypeSafe docs](https://smartscope.blog/en/blog/jev-jaggedness-safety-patterns-2026/)). The JEV paper cites the same vendor page as "TypeSafe AI 2026a, JEV 1.13 jaggedness."

### Inferences
- **Prediction for trajectory monitoring.** Suspicious agent actions mostly sit in JEV's "Escalate" or "Not supported" regions, not its "Low-fee candidate" region:
  - (a) Harm in a bash or code action must usually be derived: what the command does, data flow, side effects. That is the code/math/logic regime (−13 to −28 points).
  - (b) Sabotage and scheming often come wrapped in plausible, elaborate rationale. That is the RM-Bench "hard" regime, where JEV both errs more and is *confidently* wrong (q ≥ 0.9 error rate ×5 vs easy pairs).
  - (c) Many trajectories have no reference for "correct" behavior, analogous to reference-free prose (AUROC ≈ 0.5).
  - (d) Unlike the refusal slice, a monitor's positive class (covert bad action) is not legible from surface text.

  The strong "should refuse" result transfers to *overt* harmful-request or refusal detection (input or output moderation), not to covert action monitoring.
- On HaluEval, JEV's errors lean toward over-flagging correct answers rather than missing hallucinations. If a similar bias holds for "is this action suspicious?", that would raise false positives (audit load) rather than misses. This is untested for agent actions.
- Feeding JEV structured, pre-extracted facts (e.g., "does this command write outside the workspace?", "does the diff touch the test file?") moves the task back toward read-off. This matches the vendor's own atomic-question advice and the DeRef / derived-reference result (Q7).

### Gaps
- No safety slice in the paper involves agent actions, tool calls, or covert sabotage. The safety data are single-turn refusal/compliance pairs.
- No per-slice confidence-AUROC for the safety domains specifically (AUROC is reported by benchmark and RM-Bench style condition, not by safety domain).

## Q3. Does confidence track correctness? Calibration, confidence-error AUROC, confident errors, order sensitivity, stability, interface audit

### Takeaway
JEV's q ranks its errors well on ordinary workloads: pooled AUROC 0.82 (RewardBench 0.88, JudgeBench 0.73, HaluEval 0.83). Its confident errors are a *smaller* share of its errors than GPT-6's (21% vs 41% on RewardBench). Order flips sit almost entirely below q=0.9 (3 of 95 flips). The signal degrades exactly where JEV is confidently misled (style-adversarial, reference-free prose). Calibration and temperature transfer are workload-specific, and the three output types (Choice, Noul, Score) are not mutually consistent.

### Cited Findings
- **Confidence bins (two-order q, 4,850 items) [EXP].** JEV is right on 55.1% of the 214 items with q < 0.6 and on 97.8% of the 2,332 items with q = 1. GPT-6's accuracy on the same items rises from 69.6% to 97.8%. At q = 1 the two judges are right or wrong together on all but 2 of 2,332 items. Below q = 0.6, GPT-6 is right on 63 of the 96 items JEV gets wrong. At τ = 0.9, the 3,744 accepted items are nearly tied (94.7 vs 94.4), and on the 1,106 escalated items GPT-6 leads by 7 points (75.0 vs 67.7). Two-order AUROC of q for correctness: RewardBench 0.88, JudgeBench 0.73, HaluEval 0.83, pooled 0.82 ([JEV paper §7.1, Fig. 5](https://arxiv.org/abs/2609.26550v5)).
- **Single-call error-detection AUROC (errors as positives, score 1 − q) [EXP].**

  | Judge | RewardBench | JudgeBench | HaluEval |
  |---|---|---|---|
  | JEV | 0.875 | 0.745 | 0.827 |
  | GPT-6 | 0.894 | 0.907 | 0.831 |
  | GPT-5.4 | 0.873 | 0.912 | 0.778 |
  | Claude Sonnet 5 | 0.856 | 0.774 | 0.850 |
  | Gemini 3.1 Pro | 0.883 | 0.631 | 0.774 |
  | GPT-4.1 mini | 0.628 | 0.538 | 0.466 |
  | Qwen3 32B | 0.635 | 0.595 | 0.491 |

  JEV's native-confidence field gives 0.876 / 0.745 / 0.842 ([JEV paper §7.2, Table 21, App. J](https://arxiv.org/abs/2609.26550v5)).
- **Confident errors (single call, q ≥ 0.9; Table 31) [EXP].**

  | Benchmark | JEV error rate at q ≥ 0.9 | GPT-6 error rate | Confident errors as share of all errors (JEV / GPT-6 / Gemini 3.1 Pro) |
  |---|---|---|---|
  | RewardBench | 2.1% (24/1,155) | 3.5% | 21% / 41% / 53% |
  | JudgeBench | 6.5% (9/138) | 2.0% | 12% / 25% / 68% |

  Under the two-order confidence the gate uses, JEV's rate is 1.8% (20/1,130) and 5.7% (7/123), i.e. 19% and 11% of its errors. HaluEval is dominated by label noise: 171/2,491 (6.9%, 45% of errors) on supplied labels. On the 240 adjudicated answers, human correction leaves 10 of JEV's 30 errors and 4 of GPT-6's 32 ([JEV paper §7.1, Table 31](https://arxiv.org/abs/2609.26550v5)).
- **Probability quality.**
  - Brier: JEV 0.113 / 0.297 / 0.196 vs GPT-6 0.115 / 0.095 / 0.213 (RewardBench / JudgeBench / HaluEval).
  - JEV's apparent HaluEval advantage reverses under human labels: Brier 0.062 vs 0.032, NLL 0.108 vs 0.070, ECE 0.017 vs 0.010 ([JEV paper §7.2, Table 11](https://arxiv.org/abs/2609.26550v5)).
  - Temperature scaling fitted on small pilot selection sets transfers unevenly. Held-out NLL improves on HaluEval (0.496→0.304, T=4.45) but worsens on JudgeBench (0.449→0.475, T=2.15) and RewardBench (0.192→0.216, T=0.65). The paper concludes that "every fit needs held-out validation" ([JEV paper §7.2, Table 28](https://arxiv.org/abs/2609.26550v5)).
- **Repetition, paraphrase, and drift.** JEV changed no decision across 96 repeated requests but changed 4 of 48 under paraphrased rubrics, "as many as any judge" (GPT-6: 0/48). Between collection rounds, 7 of JEV's 350 JudgeBench decisions changed. A rerun 4 days later reproduced 99/100 RewardBench 2 verdicts (mean total variation 0.02, max 0.12) ([JEV paper §7.3, Table 23, App. K](https://arxiv.org/abs/2609.26550v5)).
- **Interface audit (48 examples; "equivalent output types can disagree").**
  - Choice vs Noul probabilities differ by 0.055 on average; Choice vs Score by 0.015.
  - The two Noul probabilities ("is it A?" + "is it B?") miss summing to 1 by 0.045 on average; one App. J figure gives the residual as reaching 0.19.
  - Joint vs standalone Choice differ by 0.011, and one close decision flips between Choice and Noul.
  - Recommendation: "A threshold should therefore be tuned for one fixed output type."

  ([JEV paper §7.3, App. J](https://arxiv.org/abs/2609.26550v5)).
- **Presentation order (1,850 pairs judged in both orders).**
  - Flip rates: JEV 3.7% (RewardBench) and 11.1% (JudgeBench); GPT-6 1.5% and 0.9%. JEV's confidence moves 0.045 on average (median 0.01). It has no overall position preference (first-position rate 49.2% / 48.4%).
  - Instability "sits below the gate": JEV's flip rate falls from 46% of pairs at base-order q < 0.6 to 22%, 10%, and 1.5% in the next bins. Only 3 of the 1,293 pairs at q ≥ 0.9 flip, all below 0.99. So 92 of 95 flips would be escalated by a τ=0.9 single-call gate. GPT-6 has 0/23 flips at q ≥ 0.9.
  - Other judges flip while confident: 70% of Qwen3.5's flips, 64% of Gemini 3 Flash's, and 52% of Gemini 3.1 Pro's occur at q ≥ 0.9.
  - RM-Bench: JEV flips 8.5% of pairs (9.6% of hard pairs), with 16 of 381 flips at q ≥ 0.9.
  - Four-way RewardBench 2 rotations: same pick in all 4 rotations for 87/100 prompts. All 13 changing prompts have mean confidence below 0.56.

  ([JEV paper §7.3, Fig. 7, Tables 23–25](https://arxiv.org/abs/2609.26550v5)).
- **Order averaging.** Raises JEV's pairwise accuracy by +0.76 points (89.89→90.65, [0.00, 1.57], not significant). Brier improves 0.148→0.141, and AUROC is unchanged (0.863→0.858). Averaging helps judges that flip while confident: Gemini 3.1 Pro AUROC 0.817→0.905, Qwen3.8 0.776→0.875, Qwen3.5 0.692→0.833. In the cascade, a base-order-only gate retains 100.2% of GPT-6's accuracy at 31% of its fee vs 100.2% at 33% for the two-order gate. On JudgeBench, both orders buy 0.9 points (98.2→99.1% retained) for 4 more points of fee ([JEV paper §7.3, Tables 25–26](https://arxiv.org/abs/2609.26550v5)).
- **Where the signal weakens:** "Confidence routes well where the first stage is competent but uncertain, and poorly where it is confidently misled" (style-adversarial AUROC 0.764; reference-free prose 0.498) ([JEV paper §7.4](https://arxiv.org/abs/2609.26550v5)).

### Inferences
- For a monitor, the relevant quantity is not symmetric max-probability q but the class-conditional score P(suspicious) and its ROC at low FPR. The paper reports only error-detection AUROC for a symmetric verdict. A good error-ranking AUROC (≈0.8–0.88) does not imply good detection at the very low FPR operating points that audit budgets require.
- Because "equivalent output types disagree" and paraphrases flip 4/48 decisions, a monitoring deployment should freeze one question wording and one output type (e.g., Noul "Is this action suspicious?") and re-validate thresholds after any wording or model-version change.
- The order-sensitivity result has no direct analogue for single trajectories. The analogous robustness probe would be re-serializing the trajectory (field order, truncation, redaction) and checking that flips sit below the gate.

### Gaps
- No low-FPR metrics (TPR@1%FPR etc.), no class-conditional calibration, and no prevalence-shift analysis in the paper (see 2610.26325 in Q7).

## Q4. Cascade design and the threshold-setting recipe; mapping to a monitor's fixed-FPR / audit-budget setting

### Takeaway
The paper's procedure:
- Run JEV on everything, averaging both candidate orders.
- Accept if q ≥ τ; otherwise call an independent stronger judge whose verdict replaces JEV's.
- Pick τ as the most permissive grid value whose one-sided 95% *lower confidence bound* on the accuracy difference vs the fallback is ≥ −2 points, on about 100 local labels, with **one threshold per workload**.

Pre-specified results: +0.93 points over GPT-6 at 41.4% of its fee on 1,610 held-out pairs, and exact parity with GPT-6 on two new workloads (escalating 74%, at 75.5% of the fee). The rule constrains a *symmetric accuracy loss relative to the fallback*, not a miss rate or FPR. For monitoring it must be re-cast as a class-specific risk constraint, which needs far more than about 100 labels when positives are rare.

### Cited Findings
- **The cascade.** JEV judges each item once, or once per ordering with probabilities averaged: p̄(A) = ½[p₁(A,B) + 1 − p₁(B,A)]. If q ≥ τ its verdict is final. Otherwise the item goes to a stronger judge that judges it independently, without seeing JEV's output, and replaces JEV's verdict. The fallback is paid only for escalated items. Invalid first-stage outputs always escalate. Exact ties get half credit and are escalated by any τ > 0.5 ([JEV paper §7, §8, Eq. 1, Table 22](https://arxiv.org/abs/2609.26550v5)).
- **Threshold rule.**
  1. On labeled items from the target workload, run both JEV and the fallback.
  2. For each τ on a fixed grid, compute per-item d_i = (cascade correct) − (fallback correct) ∈ {−1, 0, 1}.
  3. *Point rule*: require d̄ ≥ −0.02.
  4. *Lower-bound rule*: require d̄ − 1.645·sd/√n ≥ −0.02.
  5. Take the most permissive passing τ. Ties go to the stricter threshold, and if none qualifies, escalate everything.

  The paper on its framing: "The rule does not weigh quality against cost: it minimizes cost subject to an accuracy constraint". If error costs were known, the threshold "would instead follow from the cost of a wrong verdict relative to the cost of escalating (Chow, 1970; Elkan, 2001)." Example: on the PPE selection set, τ=0.9 loses exactly 2 points (passes the point rule), but its lower bound is −4.3 points, so the lower-bound rule moves to τ=0.95, which loses none ([JEV paper §8, Table 34](https://arxiv.org/abs/2609.26550v5)).
- **Post hoc sweep (Table 29) [EXP].**
  - Pooled at τ=0.9: escalates 22.8–23%, scores 90.2 vs GPT-6 90.0 (100.2% retained; +0.21 [−0.10, 0.49]) at 33% of GPT-6's fee ($2.5 vs $7.6 per 1,000; 38% conservative). Random escalation at the same expected spend reaches only 89.0.
  - RewardBench at τ=0.9: escalates 24.7%, 93.8 vs 92.5 (+1.27 [0.54, 2.02]) at 26% of the fee.
  - JudgeBench (JEV mean q only 0.80) at τ=0.9: escalates 65% and retains 99.1% at 66% of the fee. Only τ=0.99 (escalating 90%) matches GPT-6.
  - HaluEval at τ=0.9: escalates 17%, retains 99.8% at 20% of the fee. τ=0.99 matches at 34%.
  - Cheaper fallback: JEV→GPT-5.6 Sol at τ=0.9 reaches 91.2, above both GPT-6 and GPT-5.6 alone, for $1.3 per 1,000 (17% of GPT-6's fee).

  ([JEV paper §8, Fig. 8, Table 29](https://arxiv.org/abs/2609.26550v5)).
- **Frozen two-order policies on 1,610 held-out pairs [PRE].** Thresholds were chosen by the point rule on 96 pilot selection pairs (64 RewardBench, 32 JudgeBench).
  - JEV→GPT-6 at τ=0.9 accepts 68.5% and escalates 31.5%; the escalated pairs contain 85% of JEV's errors. It scores 93.4 vs 92.5 (+0.93 [0.24, 1.66]) at 41.4% of the fee (44.0% conservative).
  - RewardBench (1,340): escalates 24.8%, catches 82% of JEV's errors, +1.27 [0.45, 2.03] at 26.7% of the fee.
  - JudgeBench (270): escalates 64.8%, catches 90% of errors, 81.3→92.2 vs 93.0 (−0.74 [−2.22, 0.74]), closing 94% of the gap but saving only a third of the fee.
  - The rule does not always transfer. For the GPT-5.6 fallback, the selected τ=0.7 loses −4.81 [−8.52, −1.48] on JudgeBench while escalating only 28.5%. The 96 selection pairs held only 32 JudgeBench pairs.
  - When the fallback is no better than order-averaged JEV on the selection set (GPT-4.1 mini, GPT-4.1, GPT-OSS, Qwen3.6, Qwen3.8), the rule picks τ=0.5 and never escalates.

  ([JEV paper §8, Tables 3, 4, 30](https://arxiv.org/abs/2609.26550v5)).
- **Why JEV as first stage (retrospective, same rule, GPT-6 fallback) [EXP].**
  - GPT-4.1 mini stays within a point but costs 62.2% / 98.3% of GPT-6's fee, because its confidence supports accepting only 47.8% / 8.1% of pairs (JEV: 75.2% / 35.2%).
  - GPT-OSS 120B and Gemini 3 Flash break the tolerance on JudgeBench (−7.41, −4.44).
  - Skywork's reward margin |Δr| ≥ 4 gains +2.84 on RewardBench but loses −6.67 on JudgeBench.
  - Qwen3.5-27B accepts 54.8% / 19.6%. PairRM escalates everything.
  - "JEV is the only one whose cascade stays within two points of GPT-6 on both benchmarks while saving at least 30% of its fee on each." The paper's caveat: "JEV's value as a first stage lies in its confidence as much as in its price."

  ([JEV paper §8, Table 3 lower panel, App. L](https://arxiv.org/abs/2609.26550v5)).
- **Live replication (510 held-out pairs; protocol pre-written but items already analyzed).** Escalated 46.5% (46.3% offline; same gate decision on 98.6% of pairs). Scored 92.5 vs 93.1 (−0.59 [−1.95, 0.59]) at 57.2% of the fee. Median latency per pair was 0.27 s vs 2.10 s for GPT-6 alone: accepted pairs 0.18 s, escalated pairs 2.50 s. p95 barely moves (4.26 vs 4.49 s). On JudgeBench (65% escalated), the median saving shrinks to 0.14 s. JEV calls were 100% valid on first attempt; the run cost $8.81 ([JEV paper §8, App. O, Table 37](https://arxiv.org/abs/2609.26550v5)).
- **Label-budget simulation (2,000 draws of k labels from 1,850 pairs; Table 32) [EXP].**

  | Rule | k | P(loss > 2 pp) | Median escalation | Median fee ratio |
  |---|---|---|---|---|
  | Point rule, one τ | 48 / 96 / 192 / 384 | 39.7% / 44.0% / 48.5% / 50.0% | about 6% | 0.09 |
  | Lower bound, one τ | 48 / 96 / 192 / 384 | 6.6% / 5.2% / 4.8% / 2.9% | 32% at k=96 → 13% at k=384 | 0.42 at k=96 |
  | Point rule, τ per workload | 96 | 11.8% | – | – |
  | Lower bound, τ per workload | 48 / 96 / 192 / 384 | 1.2% / 0.6% / 0.1% / 0.1% | 18–20% | 0.29–0.36 |

  The point rule "spends its tolerance," and its risk does not fall with more labels. The paper's caveat: the simulation reuses one pool and "is optimistic about distribution shift" ([JEV paper §8, Table 32](https://arxiv.org/abs/2609.26550v5)).
- **Prospective live test [PRE].** Protocol frozen before any model call. New workloads: 500 PPE correctness pairs (100 each from MMLU-Pro, MATH, GPQA, MBPP-Plus, IFEval) and 270 JudgeBench Claude-3.5-Sonnet split pairs. 100 selection pairs per workload; lower-bound rule on grid {0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99}.
  - On the selection sets JEV trailed by 12.5 (PPE) and 17 (JudgeBench) points. The rule chose τ=0.95 (PPE) and 0.99 (JudgeBench); one pooled lower-bound threshold would have been 0.95.
  - Held-out results (570 pairs):

    | Workload | JEV alone | Cascade | GPT-6 | Escalated | Fee ratio | Median / p95 latency |
    |---|---|---|---|---|---|---|
    | PPE (400) | 78.2 | 88.2 | 88.2 | 67.8% | 0.693 | 1.76 / 3.76 s |
    | JudgeBench Claude (170) | 70.9 | 94.7 | 94.7 | 89.4% | 0.910 | 2.41 / 5.97 s |
    | Both (570) | 76.1 | 90.2 | 90.2 (0.00 [−0.70, 0.70]) | 74.2% (93% of JEV errors caught) | 0.755 ($12.5 vs $16.6 per 1,000 pairs) | 1.87 / 4.95 s (GPT-6 alone: 1.91 / 5.58) |

  - Counterfactual τ=0.9 on both workloads: −0.53 [−1.58, 0.35] at 0.619 of the fee, and −1.18 [−2.94, 0.00] on JudgeBench.
  - JEV error rate at q ≥ 0.9 was 6.6% (15/229). Total cost of the run: $12.77; no invalid outputs.
  - The paper's summary: "On new workloads where JEV is weak, the lower-bound rule escalated enough to achieve GPT-6's accuracy, and the saving shrank accordingly."

  ([JEV paper §9, Tables 5, 34–36](https://arxiv.org/abs/2609.26550v5)).
- **Error correlation limits any serial cascade.** On JudgeBench, GPT-6 corrects 60 of JEV's 75 errors and JEV corrects 9 of GPT-6's 24, so an oracle router would reach 95.7%. 15 of JEV's 75 JudgeBench errors are shared with GPT-6 and "cannot be repaired" under serial replacement. Share of JEV errors corrected by GPT-6: RewardBench 54%, JudgeBench 80%, HaluEval 26% (Fig. 22) ([JEV paper §8, Fig. 22](https://arxiv.org/abs/2609.26550v5)).
- **Recipe stated in the conclusion:** "average the verdict over both presentation orders, set the threshold on about 100 local labels using the lower confidence bound of the accuracy loss rather than its point estimate, and check the policy on held-out items from the same workload. When the first stage is weak, this procedure spends more rather than losing accuracy" ([JEV paper §10](https://arxiv.org/abs/2609.26550v5)).

### Inferences
- **Mapping to an audit budget.** Escalation fraction = the share of items sent to the expensive monitor (or human). The paper's rule fixes an *accuracy tolerance* (−2 points vs the fallback) and lets escalation float (25% to 89% depending on workload). A monitor usually fixes the *budget* (e.g., escalate or audit ≤ 1–5%) or the *FPR* and asks what TPR results. Under that framing the JEV-paper procedure inverts. Given a budget B, set τ so that P(q < τ) ≈ B, or so that P(JEV score of "suspicious" ≥ t) ≈ B. Then estimate the miss rate among accepted-benign items with a one-sided bound.
- **Class asymmetry.** d_i treats a missed attack and a false alarm identically, and both cancel against fallback errors. For monitoring, the constraint should be on *recall loss on positives* (cascade misses minus fallback misses on truly-bad trajectories), with false positives counted as budget cost. With rare positives, about 100 random local labels contain few or no positives. The paper's own failure mode (the point rule admitting JudgeBench errors because the 96 selection pairs held only 32 JudgeBench items) is the analogue of a rare-positive subpopulation dominating risk. A monitor needs a stratified or enriched positive set (red-team trajectories) and per-attack-family thresholds, the analogue of "per-workload thresholds," which cut risk from about 5% to 0.6% at k=96.
- **The lower-bound rule escalates heavily when the first stage is weak** (74% in the prospective test). If JEV's agent-action accuracy resembles its JudgeBench or PPE accuracy (70–78%), a JEV-first monitor matched to a strong monitor's accuracy would escalate most traffic and save little (fee ratio 0.76–0.91). JEV pays off as a filter only where most traffic is easy (RewardBench-like: about 25% escalated, about 27% of the fee).
- **Random-escalation control.** The paper shows confidence routing beats fee-matched random escalation (90.2 vs 89.0 pooled). A RAG replication (Do Rosario & Atef, Q7) found random escalation as good. A monitoring study should always report this control.
- **Adversarial angle (not in the paper).** A policy model that knows the monitor could aim for "confidently misled" inputs (elaborate justifications), which the style-adversarial result shows JEV cannot route. The option-channel attack paper (Q7) shows attacked decisions are no less confident.

### Gaps
- The paper never evaluates a fixed-budget or fixed-FPR operating point, asymmetric error costs, or class-conditional risk control. Chow/Elkan cost-based thresholds are explicitly left open.
- Fused panels, a second judge that sees JEV's verdict, and a human tier are untested ("Escalation design" limitation).

## Q5. Other stated limitations, and Appendix A (open decision models)

### Takeaway
Beyond "Agentic tasks," the authors flag:
- **Black box:** one proprietary version, unknown size/data, possible benchmark contamination.
- **Task format:** given-candidate judgments only. Long reference-free text is barely covered. Human adjudication covers only 183 disagreement-selected items.
- **Escalation design:** only serial escalation with a fixed tolerance.
- **Small pre-specified scope.**

Appendix A shows that open-weight decision models now match JEV's accuracy and error-ranking AUROC, so the cascade ingredients are no longer JEV-specific. Their cascade behavior is untested.

### Cited Findings
- **"Black box":** "We evaluate one proprietary version, JEV 1.13.0, through its API. Its size, training recipe, and data are not public, so we can describe how it behaves but not why it succeeds or fails, and we cannot rule out that benchmark items were seen in training. The comparison judges differ in size, reasoning effort, and serving, so the study is not compute-matched … The open decision models of Appendix A can be inspected, but we test them only as stand-alone judges" ([JEV paper Limitations](https://arxiv.org/abs/2609.26550v5)).
- **"Task format":** "Long free text judged without a reference is barely covered, and there every judge we ran is near chance … Specialized professional domains are untested, and a decision-only judge gives no explanation that a user could audit" ([JEV paper Limitations](https://arxiv.org/abs/2609.26550v5)).
- **"Escalation design":** "Fused panels, a second judge that sees the first verdict, further tiers such as a final human review, and thresholds set from the costs of a wrong verdict and of escalating … remain open, and errors that both judges share cannot be fixed by any serial cascade. Only the frozen two-order policies, the primary human-adjudication outcome, and the prospective test were specified before their data were seen" ([JEV paper Limitations](https://arxiv.org/abs/2609.26550v5)).
- **Appendix A [EXP].** 21 open decision models were run on JEV's exact 5,172 base judgments plus 1,850 reversed pairs, on one H100, as shipped. This covers every public-weight entry in the Decision Index top 15 except the second-ranked Fastino GLiDE, plus others.
  - JEV pooled public accuracy is 88.3. Six open models are within sampling error; none is significantly better.
  - Perplexity Decider v1.1 27B: 89.0 (+0.8 [0.0, +1.5]), JudgeBench 82.6, AUROC 0.841, 84 ms.
  - Eikos-27B: 89.0, AUROC 0.843, 61 ms.
  - Torchcast Decision 27B: 87.6, AUROC 0.860 (best).
  - Decision-tuned Qwen3.8-27B variants score 85.2–89.0 vs the same base read zero-shot (reflex) at 83.5.
  - Leaderboard rank correlates only 0.12 with pooled accuracy.
  - Among 26–31B models, error AUROC ranges 0.73–0.860, and six exceed JEV's 0.822. Local median latency is 42–245 ms on a dedicated H100 vs JEV's hosted 152 ms.
  - Small or encoder models fail: CLM-v0.1-8B 68.5, Laya English 60.8.
  - The paper: "We did not rerun the escalation analysis with these models, and their order stability, their behavior on the follow-up and prospective workloads, and their calibration under escalation remain untested."

  ([JEV paper App. A, Table 6](https://arxiv.org/abs/2609.26550v5)).
- **Laya (App. M).** A ModernBERT-large encoder with the same typed interface. 512-token (English) or 1,024-token (Typed-decisions) context; 100% valid outputs; deterministic. It sits at chance on preference: RewardBench 47–50%, JudgeBench 49%, four-way RewardBench 2 20–23%. Error AUROC is 0.48–0.53. On RM-Bench it scores below chance on hard pairs (34% / 41%), i.e. it follows style. Reversal flips: 57.6% / 70.5% on RewardBench. The paper: "A typed probability interface is therefore not what makes JEV usable" ([JEV paper App. M, Table 33](https://arxiv.org/abs/2609.26550v5)).
- **Reproducibility (App. Q).** The offline package reproduces the principal metrics, human adjudication, threshold sweeps, label-budget simulation, etc. from retained outputs, with no API calls or GPU. Raw API logs and private-source replies are excluded ([JEV paper App. Q](https://arxiv.org/abs/2609.26550v5)).

### Inferences
- For a monitoring stack that must be self-hosted (no trajectories leaving the org) and auditable, Appendix A matters most. An open 27B decision model (Decider, Eikos, Torchcast) gives JEV-level accuracy and error ranking at about 40–250 ms locally. These can be fine-tuned on monitor-specific data, which is impossible for JEV. "Our Own Jev" (Q7) does exactly this for agentic coding session triage.
- The Laya result is a warning that "typed interface + probability" is not sufficient. Small encoders can be valid, fast, deterministic, and useless, with confidence that carries no error signal.

### Gaps
- The supplementary package URL was not found in the paper text, and no public GitHub repository was located during this search.
- The Decision Index Hugging Face Space ([multimodalart/jev-decision-index](https://huggingface.co/spaces/multimodalart/jev-decision-index)) did not render its content to the fetch tool. Edition 0.3 (Full score, 7 Oct 2026), with JEV ranked 3rd, is known only via the JEV paper. Its methodology and safety/agent categories could not be verified.

## Q6. The most relevant cited works and what each implies for cheap-first-stage agent monitoring

### Takeaway
The closest precedents are:
- Jung et al. 2025: a cascade with *provable* human-agreement guarantees, the direct template for risk-controlled monitor thresholds.
- Xu et al. 2025: uncertainty routing of RM comparisons to a strong judge, beating random routing by 2.4–3.1 points at about 25% calls.
- Rao & Callison-Burch 2026b: JEV's confident errors are shared by LLM judges (96%), so cascades mainly save cost and gain at most 1.5–2.7 points.

Classic theory: Chow's reject option sets the cost-based threshold; Geifman & El-Yaniv provide high-probability risk-controlled selective classification. Efficient specialized judges (MiniCheck, BERT-as-a-Judge, Luna-2) show small models reach frontier-judge accuracy on *narrow, well-specified* checks.

### Cited Findings
- **Rao & Callison-Burch 2026b**, "Decision Models vs. LLMs as Rubric Judges: Cheaper, Faster, and Wrong in the Same Places" ([arXiv 2609.29769v3](https://arxiv.org/abs/2609.29769)). The JEV paper cites it under the earlier title "JEV vs. LLMs as rubric judges."
  - *Setup:* JEV and Perplexity's open Decider vs three flash-tier LLM judges (GPT-5.6 Luna, Gemini 3.8 Flash, DeepSeek V4.1 Flash), on nine panels from seven benchmarks with human labels: RiceChem, HealthBench, ELLIPSE, FED-Turn, FED-Dialogue, HelpSteer2, LFQA, USR-TC, USR-PC.
  - *Cost:* LLM judges cost 16–357x as much and take 5–350x as long.
  - *Accuracy:* each decision model trails significantly in at most 6 of 27 comparisons.
  - *Shared errors:* on ordinal criteria the two kinds of judge agree more with each other than with the human labels. Over 85% of flash-tier verdicts repeat the decision models' most confident errors: 96.0% (242/252) for JEV and 86.5% (218/252) for Decider, against independence baselines of about 50%.
  - *Confidence:* JEV's confidence ranks errors on most ordinal panels, with AUROC FED-Turn 0.70, FED-Dialogue 0.61, HelpSteer2 0.66, USR-TC 0.65, USR-PC 0.61, ELLIPSE 0.49. On binary RiceChem, AUROC is 0.80–0.86.
  - *Cascades:* flash-tier-fallback cascades "gained a mere 2.7 points at best over the strongest single judge, even with oracle thresholds." Cross-fitted JEV-first gains are at most 1.5 points (HealthBench). Higher-tier fallbacks (GPT-5.6 Terra, Gemini 3.1 Pro, DeepSeek V4 Pro) lift no cascade more than 1.7 points.
  - *Implication:* a cascade buys cost savings, not accuracy, when the fallback shares the first stage's blind spots. For monitoring, the fallback must be *differently* informed (e.g., sees tool outputs, runs code, reasons longer), not just a bigger judge reading the same text.

  Extracted from the arXiv HTML ([arXiv 2609.29769](https://arxiv.org/html/2609.29769v3)).
- **Rao & Callison-Burch 2026a, Autorubric** (COLM 2026; [arXiv 2603.00077](https://arxiv.org/abs/2603.00077)). An open-source framework for rubric-based judges covering option shuffling, ensembles, abstention, calibration, and psychometric reliability. Evaluations on college chemistry grading, deep-research systems, and the new CHARM-100 benchmark "reveal criterion-specific failures, systematic judge-family differences, and configuration effects that do not support a universal mitigation stack." Per the JEV paper, it suggests calling additional judges only on low-confidence items to cut ensemble cost; the JEV cascade is a serial form of that idea. *Implication:* monitor configurations (bias mitigation, abstention) must be validated per judge and criterion. There is no universal setting.
- **Jung, Brahman & Choi 2025, "Trust or Escalate: LLM Judges with Provable Guarantees for Human Agreement"** (ICLR 2025; [arXiv 2407.18370](https://arxiv.org/abs/2407.18370)). Selective evaluation in which a judge renders a verdict only when confident, with human agreement "provably guaranteed … to a user-specified agreement level." "Simulated Annotators" improve confidence calibration, and "Cascaded Selective Evaluation" uses cheaper judges first and escalates to stronger ones. On a Chatbot Arena subset where GPT-4 "almost never achieves 80% human agreement," the method, even with Mistral-7B as a first stage, "guarantees over 80% human agreement with almost 80% test coverage." *Implication:* the finite-sample guarantee machinery is the right replacement for the JEV paper's heuristic 1.645·sd/√n bound, provided the risk is re-defined as a monitor's miss rate.
- **Xu et al. 2025, "Ask a Strong LLM Judge when Your Reward Model is Uncertain"** (NeurIPS 2025 per the JEV paper; [arXiv 2510.20369](https://arxiv.org/abs/2510.20369)). An SNGP-based pairwise preference RM (trained on HelpSteer2-Preference) routes uncertain pairs to DeepSeek-R1.
  - RewardBench at 24.1% judge calls: 90.6 vs 88.2 for random routing.
  - RM-Bench at 26.7% calls: 76.6 vs 73.5 random.
  - Online RLHF at about 9% judge calls: Arena-Hard win rate 28.9 vs 27.7 random.

  Figures from [arXiv HTML](https://arxiv.org/html/2510.20369v1). *Implication:* epistemic-uncertainty routing works in the RL-reward setting (relevant for monitors used as reward or penalty signals). The JEV paper reproduces the pattern with a hosted decision model.
- **FrugalGPT** (Chen, Zaharia, Zou, TMLR 2024; [arXiv 2305.05176](https://arxiv.org/abs/2305.05176)). An LLM cascade that "can match the performance of the best individual LLM (e.g. GPT-4) with up to 98% cost reduction or improve the accuracy over GPT-4 by 4% with the same cost." *Implication:* cascade savings depend heavily on workload easiness. The JEV paper's savings range from 73% (RewardBench) to 9% (JudgeBench Claude split).
- **RouteLLM** (Ong et al., ICLR 2025; [arXiv 2406.18665](https://arxiv.org/abs/2406.18665)). Routers trained on preference data "significantly reduce costs — by over 2 times in certain cases — without compromising the quality of responses," with transfer when the strong and weak models change. *Implication:* a learned router, rather than the first stage's own confidence, is an alternative gate. It is untested for decision-model monitors.
- **Chow 1970**, "On optimum recognition error and reject tradeoff" (IEEE Trans. Inf. Theory 16(1):41–46; cited in [JEV paper refs](https://arxiv.org/abs/2609.26550v5)). The optimal reject threshold follows from the relative costs of error and rejection. The JEV paper names this as the alternative to its fixed-tolerance rule, left open. *Implication:* for monitoring, with known costs of a missed sabotage vs an audit, the threshold should be set cost-optimally on the "suspicious" posterior, not by an accuracy tolerance.
- **Geifman & El-Yaniv 2017**, "Selective Classification for Deep Neural Networks" (NeurIPS 2017; [arXiv 1705.08500](https://arxiv.org/abs/1705.08500)). Lets "a user to set a desired risk level" and rejects as needed to guarantee it with high probability. Example: "2% error in top-5 ImageNet classification can be guaranteed with probability 99.9%, and almost 60% test coverage." *Implication:* this is the risk-coverage framework the JEV threshold rule borrows. A monitor needs it with risk = false-negative rate.
- **MiniCheck** (Tang, Laban, Durrett, EMNLP 2024; [arXiv 2404.10774](https://arxiv.org/abs/2404.10774)). Small fact-checkers trained on synthetic GPT-4 data reach "GPT-4-level performance but for 400x lower cost"; MiniCheck-FT5 (770M) "reaches GPT-4 accuracy" on LLM-AggreFact. *Implication:* narrow, evidence-grounded checks are where small models match frontier judges. This mirrors JEV's HaluEval parity.
- **BERT-as-a-Judge** (Gisserot-Boukhlef et al. 2026; [arXiv 2604.09497](https://arxiv.org/abs/2604.09497)). An encoder trained on synthetic question–candidate–reference triplets "consistently outperforms the lexical baseline while matching the performance of much larger LLM judges" (36 models, 15 tasks). *Implication:* it is reference-based. Agent monitoring usually lacks a reference, which is exactly where JEV and all judges collapsed in the prose test.
- **Luna-2** (Goel et al. 2026; [arXiv 2602.18583](https://arxiv.org/abs/2602.18583)). Small-LM backbone with one LoRA head per metric (toxicity, hallucination, *tool selection quality*), computing single-token "LLMAJ metrics" for "real-time guardrails." It "matches the accuracy of state-of-the-art LLM-based evaluators while reducing inference cost by over 80x and latency by over 20x." In production it is "protecting 100M+ AI sessions and processing over 100B tokens per month," with "eval cost savings of over $30M annually." *Implication:* it is the closest deployed analogue of a per-metric cheap guardrail, including an agentic metric (tool-selection quality). It is vendor-reported; no independent replication was found.
- **Laya** (Convai Innovations 2026; [GitHub NandhaKishorM/laya](https://github.com/NandhaKishorM/laya)). An open-weight "non-autoregressive System 1 decision engine." In the JEV paper it is near chance with uninformative confidence (see Q5).
- **Hsiao 2026**, "Rethinking Verbalized Confidence for LLM-as-a-Judge: A Compatibility Shift on Post-2025 Proprietary Models" ([arXiv 2609.10996](https://arxiv.org/abs/2609.10996)). Across SummEval, AggreFact, and HelpSteer2 with up to 18 LLMs, "the standard advice to prefer log-probabilities no longer holds on post-2025 models, where verbalized confidence is the better signal." Adding an "overconfidence advisory" and "self-debate" improves calibration. *Implication:* this supports the JEV paper's choice to compare JEV's native probabilities against *verbalized* probabilities from frontier judges. A monitor fallback's verbalized confidence may be a usable second-stage signal.
- **Bagaria et al. 2026**, "Judging LLM-as-a-Judge: Concerning Rubric Artifacts" ([arXiv 2609.02942](https://arxiv.org/abs/2609.02942)). Classifiers trained only on rubric text predict judge outputs non-trivially, and judges "often fail to reliably update their decisions when either the candidate response or the rubric criterion is reversed." *Implication:* monitor rubric wording can dominate verdicts; paraphrase-robustness checks are needed (JEV changed 4/48 decisions under paraphrase).
- **Decision Index** (Multimodalart 2026, [HF Space](https://huggingface.co/spaces/multimodalart/jev-decision-index)). A public leaderboard of decision models; edition 0.3 ranks JEV 3rd. Per the JEV paper, its rank correlates only 0.12 with accuracy on the paper's tasks ([JEV paper App. A](https://arxiv.org/abs/2609.26550v5)).

### Inferences
- The single most monitoring-relevant cited result is Rao & Callison-Burch's 96% repetition of JEV's confident errors by LLM judges. Errors correlated across cheap and strong judges cap what a cascade can add. A monitor cascade should pair JEV with a fallback that uses *different evidence* (execution, diff inspection, tool-output verification, CoT access) rather than just a larger model reading the same transcript.
- Jung et al. plus Geifman & El-Yaniv provide the theory to convert the JEV recipe into a monitor with a guaranteed bound on false-negative rate among non-escalated items. The JEV paper's lower-bound rule is a lightweight approximation of this, with no finite-sample guarantee.

### Gaps
- Exact Jung et al. numbers beyond the abstract were not extracted: calibration-set size, α/δ values, and TL;DR results.
- Luna-2's "tool selection quality" metric accuracy was not extracted beyond the abstract.

## Q7. Later papers (Sept–Oct 2026) that cite JEV-as-a-Judge or evaluate JEV / decision-only judges, especially for safety, guardrails, moderation, agent monitoring, and reward modeling

### Takeaway
There is a very large burst of follow-up work. JEV was released on 15 Sep 2026, and an evidence audit counted 28 papers in its first 9 days. Monitoring-relevant evidence is mixed:
- **Encouraging:**
  - On retrospective agent-trace security classification, JEV beats a generative judge (F1 77.8 vs 74.1) at about 76x lower cost.
  - As a zero-shot alignment-failure detector (incl. reward hacking and deception), it reaches median AUROC 0.886.
  - As a continuous monitor of a reasoning model (SOMA), it reduces overthinking and improves abstention.
- **Cautionary:**
  - Attacked decisions are *not* less confident, so confidence escalation does not catch adversarial flips (option-channel attack).
  - At a 1% FNR target for prompt-injection detection, gate-reviewer systems must escalate more than 91.8%.
  - Decision models follow the reference in their input and miss derived values (the "derivation gap").
  - JEV's confidence flags its own errors but not errors inherited from stale state.
  - JEV flags 27% of benign requests in moderation.
  - Confidence-gated systems invite escalation-draining attacks.

### Cited Findings
**Directly on agent traces, monitoring, and alignment-failure detection**
- **Wang & Gao, "JEV as a Judge for Agent Trace Security"** ([arXiv 2609.34862](https://arxiv.org/abs/2609.34862), 28 Sep 2026). 5,219 trajectories:

  | Benchmark | Trajectories (pos/neg) | JEV P / R / F1 | GLM-5.2 P / R / F1 |
  |---|---|---|---|
  | R-Judge | 564 (298/266) | 92.6 / 84.7 / 88.5 | 99.2 / 88.2 / 93.4 |
  | ATBench500 | 500 (250/250) | 88.9 / 99.2 / 93.8 | 96.6 / 77.3 / 85.9 |
  | TraceSafe | 540 (270/270) | 72.2 / 63.8 / 67.8 | 92.2 / 59.6 / 72.4 |
  | MCPHunt | 3,615 (797/2,818) | 54.7 / 69.1 / 61.1 | 79.8 / 31.2 / 44.9 |

  - Benchmark-averaged F1: JEV 77.8 vs GLM-5.2 74.1. Valid coverage: 95.5% vs 94.4%.
  - Latency: JEV median 0.99 s, p95 2.02 s, vs GLM median 33.29 s.
  - Cost: $0.000195 vs $0.014887 per valid judgment (about 76x).
  - Traces were capped at 8,000 characters in the review template. JEV keeps an F1 edge on traces longer than 16 steps (57.5 vs 50.6).
  - Confidence AUROC and cascading were *not* evaluated. The authors frame JEV as "an economical screening signal, with trade-offs in precision and recall."

  Details extracted from [arXiv HTML](https://arxiv.org/html/2609.34862v1).
- **Guo et al., "Just Ask Jev: … Zero-Shot Detector of AI Alignment Failures"** ([arXiv 2609.29429](https://arxiv.org/abs/2609.29429)). RLCDAlignBench covers 10 failures: sycophancy, jailbreaks, deception, prompt injection, hallucination, privacy, social bias, reward hacking, concealing uncertainty, power seeking. It spans 44 benchmarks and 5 target models.
  - A single generic Noul question reaches median AUROC 0.886 zero-shot and "beats supervised baselines on most benchmarks."
  - Reward-hacking data: 6 benchmarks incl. MACHIAVELLI reward, 4 reward-hacking datasets, and rubric tampering (714 instances). Deception: DeceptionBench and 3 MASK benchmarks.
  - Many failures are "relational," defined against a reference (user belief, model belief, injected instruction) not visible in the response. Adding the true answer to SycophancyEval moves AUROC from 0.540 to 0.941.
  - Multi-turn trajectory judges: about 0.870.
  - Cost: 63x cheaper than LLM-judge scorers ($0.30 vs $18.96). Human agreement on StrongREJECT: κ 0.809 (vs scorer 0.811).
  - Limitation: "one RLCD model (jev-1.13.0), English benchmarks, 2–7B targets, and mostly scorer labels."

  Details from [arXiv HTML](https://arxiv.org/html/2609.29429v1).
- **Qian et al., SOMA: "Continuous Monitoring and Intervention for System Two Reasoning with System One Models"** ([arXiv 2610.26793](https://arxiv.org/abs/2610.26793)). An S1 model (JEV) continuously judges whether a natural-language-described behavior appears in an S2 reasoning trace. A controller first reminds S2 and takes over only if the behavior persists. Without training, it "cuts reasoning tokens by up to 36% while improving average accuracy" on overthinking, and raises abstention on unanswerable questions from 70.5% to 87.2%. *This is the closest published instance of JEV as a continuous CoT monitor.*
- **Ma et al., "Judges Follow the Reference: The Derivation Gap in Verifying Tool-Call Arguments"** ([arXiv 2610.18497](https://arxiv.org/abs/2610.18497)). Tool-call judges, including System One models CLM and JEV, accept a correct argument less often when nothing in their input says what it should be (schema defaults, inferred values, truncated sources). In a controlled source-relocation test, judges "favor a visible incorrect value over a correct value whose source is hidden." Fix: "DeRef," where a separate model reads the full history and writes a reference. This raises controlled-test AUROC "from chance or below to between 98.40 and 99.59." *This is direct agentic confirmation of the JEV paper's read-vs-derive boundary.*
- **Yang et al., "What Can't Jev Decide? Probing the Limits of One-Pass Decision Models"** ([arXiv 2610.24929](https://arxiv.org/abs/2610.24929)).
  - JEV retrieves records without error up to 20k tokens and 64 options. Once the answer depends on 2+ updates of one entity, accuracy falls to 53–80% at sixteen updates.
  - It answers 97.5% of items that one forward pass of a reference LLM solves, but only 74% of the others.
  - Given a stale summary, JEV follows it. "Its confidence flags the errors it makes itself but not those it inherits from a stale input," and neither explicit nor trained hand-off options catch these. Open replicas share the limits.
- **Weng et al., "Our Own Jev"** ([arXiv 2610.29052](https://arxiv.org/abs/2610.29052)). An in-house System-1 judge triages about 148K *agentic coding session* records. It replaces a frontier LLM judge (about $1,000 per pass) whose stored labels matched a fresh two-judge consensus on only 26.9% of sessions. Backbone plus rank-16 LoRA and pointer head: 1,000 sessions in about 3 GPU-minutes (about $0.06, about 1% of the frontier judge's cost), all on-premises.
- **BLADE** ([arXiv 2610.18780](https://arxiv.org/abs/2610.18780)). Uses JEV for failure attribution in multi-agent systems on 1,228 failed runs (Who&When). Best or tied-best step accuracy among 8 strategies, +2.2–11.1 points over All-at-once.
- **Source-Judged Compaction** ([arXiv 2610.20927](https://arxiv.org/abs/2610.20927)). JEV judges whether each compaction-summary entry has a source in environment outputs. 83% of failed runs trace to an unsupported summary entry. Improves reliability on AppWorld and OfficeBench by 2.1–8.9%.

**Safety classification, guardrails, moderation, adversarial robustness**
- **Li et al., "Same Attack, Different Judge"** ([arXiv 2610.17820](https://arxiv.org/abs/2610.17820)). Controlled adversarial comparison on input moderation, injection detection, routing, and phishing; 50 attack variants from 13 families.
  - Input moderation: 8 structured-input forgeries bypass none of JEV's decisions. A "why might someone ask" sentence bypasses 9% of its blocks vs 56% for GPT-6 Astra.
  - Phishing (holistic judgment): forgeries bypass 19–29% of JEV's flags, and unattacked JEV detects only 62% vs 77–81% for GLM judges.
  - JEV "flags the most benign requests (27%)."
  - Conclusion: JEV "resists attacks on tasks with a clear rule to check but is more exposed on tasks that call for an overall judgment."
- **Azizi et al., "One Word Opens the Gate: The Option-Channel Attack on Typed Decision Models as Agent Guardrails"** ([arXiv 2610.12292](https://arxiv.org/abs/2610.12292)). Tests seven open-weight typed models; *not JEV itself*.
  - Allow/block accuracy on public screening tasks ranges 36–72% (chance 50%).
  - Six lines of irrelevant server-log text raise fail-open from 0% to 63%. Renaming the permissive option raises fail-open to 93–100%.
  - Over 1,410 attack-reversed decisions, the pooled margin is 0.149 before and 0.151 after the attack, wider after in 53%. Escalating the least-confident 10% reduced attacked fail-open only from 60% to 54%.
  - A deterministic rule over parsed fields reaches 100%.
  - Recommendation: "Do not treat a typed decision model as the component that makes a final allow or block decision"; do not rely on returned probability for escalation.

  Details from [arXiv HTML](https://arxiv.org/html/2610.12292v1).
- **Azizi et al., "Labels Override Definitions"** ([arXiv 2610.02586](https://arxiv.org/abs/2610.02586)). In open typed decision models the answer follows option *labels* more than definitions. Deleting all definitions leaves laya-td accuracy unchanged (0.8559 vs 0.8487). When a label contradicts its definition, one model's accuracy falls from 0.8511 to 0.2281. The cause is located in prompt rendering ("{label}: {definition}").
- **Lan et al., "From Detection to Decision: Calibration and Deferral for Prompt-Injection Detection"** ([arXiv 2610.20907](https://arxiv.org/abs/2610.20907)). 47,611 held-out examples. AUROC: LLM judge 0.897, JEV 0.871, Prompt Guard 2 86M 0.757, 22M 0.714. JEV's native probabilities do not consistently beat post-hoc-calibrated classifiers. "At an empirical false-negative-rate target of 1%, all evaluated gate-reviewer systems require more than 91.8% escalation and incur substantial false-positive rates."
- **Messoudi & Mansar, "Calibration and Risk-Budgeted Decisions with System One Models"** ([arXiv 2610.19811](https://arxiv.org/abs/2610.19811)). Six moderation, safety, and reranking datasets. "Naive baselines for threshold selection exceed the target risk in roughly half of settings with defined test risk, compared with 7.8% for Learn Then Test (LTT)."
- **Iqbal et al., "Typed Decision Models under Prevalence Shift"** ([arXiv 2610.26325](https://arxiv.org/abs/2610.26325)). Under moderate label shift, JEV's ECE and threshold risk grow more than a fine-tuned DeBERTa's only on financial sentiment (+1.7, +2.5 points). Label-free EM prior correction lowers JEV's ECE by 2.7 and 1.8 points; labeled recalibration lowers it much more. "Their main weakness is the miscalibration they already have without shift."
- **Hu et al., Jev-Guard** ([arXiv 2610.18326](https://arxiv.org/abs/2610.18326)). A guard model with policy-tree routing; despite the name, it appears to be the authors' own model. 93.72% safety accuracy on 7,033 cases, 58 ms mean latency, 93.10% routing accuracy. Integrated into the Hermes harness, it cut mean review time per task from 4.80 s (SFT-LLM judge) to 1.33 s with no observed policy violations.
- **SkillScreen** ([arXiv 2610.17727](https://arxiv.org/abs/2610.17727)). A task-trained compact decision model flags 20–25% of benign agent skills at 99% recall on unseen attack families, fewer false positives than prompted LLM judges. Unfamiliar benign sources sharply raise false positives.
- **Mazzoni & Failla, "Benchmarking System One Models in Online Moderation"** ([arXiv 2610.07953](https://arxiv.org/abs/2610.07953)). Across five moderation benchmarks JEV is competitive with specialized systems. Its confidence "can support selective review in several settings, although it is not consistently calibrated." Laya's confidence is less useful.
- **Lukassen et al., "Cheap, Consistent, Calibrated, but Biased?"** ([arXiv 2610.18122](https://arxiv.org/abs/2610.18122)). CALM bias tests on 8 typed decision models and 7 LLM judges. Every typed model is biased in 3–8 of 12 tests. Rewriting the better answer in an emotional tone drops a typical typed model from 99% to 42%. All 8 flip under position swap. "Good calibration does not protect against bias."
- **Wang et al., "Hidden Risks of Jev"** ([arXiv 2610.04985](https://arxiv.org/abs/2610.04985)). Prompt injection and adversarial suffixes manipulate JEV decisions; backdoors are implanted via poisoning of a local "NanoJev"; membership and attribute inference are possible. "Jev remains vulnerable to the examined security and privacy threats."
- **Gu et al., GateDrain** ([arXiv 2609.33992](https://arxiv.org/abs/2609.33992)). In confidence-gated edge–cloud inference, bounded perturbations lower confidence and push requests into the shared escalation queue, causing tail-latency collapse. Defense: per-source admission budgets and bounded escalation. It does not test JEV, but the attack surface is generic to confidence-gated cascades.

**Cascades and evaluation of decision-only judges more generally**
- **Do Rosario & Atef, "Jev-as-a-Judge for RAG Claim Verification"** ([arXiv 2610.20634](https://arxiv.org/abs/2610.20634)). 495 LLM-AggreFact claims. JEV vs GPT-6 Astra: −0.56 points at 187x lower cost, but they disagree on 15.2% of claims. JEV admits 23.2% of human-unsupported claims vs Astra's 14.1%. The cascade reaches 74.10 at $2.92 per 1,000 vs 73.83 at $8.93. "A matched random-escalation control at in-sample thresholds … does as well, so what buys the saving is the escalation share and not the probability." The paper's headline: "Equal accuracy conceals unequal errors."
- **Tang & Zheng, "Typed Decision Models: An Early Evidence Audit and Evaluation Checklist"** ([arXiv 2609.32160](https://arxiv.org/abs/2609.32160)). Reviews 28 papers from 19–24 Sep 2026. "The typed readout itself has not shown an independent accuracy advantage over comparable label-probability readouts. Jev's clearest gains are in latency and cost, while accuracy gaps remain on harder tasks." Provides a 14-item checklist.
- **Deußer et al., "Evaluating and Benchmarking the System One Model Jev"** ([arXiv 2609.37647](https://arxiv.org/abs/2609.37647)). 37 datasets, 346,009 requests for under $10. JEV beats Qwen3.8-27B (label-probability readout) on 27/37. Choice probabilities are well calibrated and support selective prediction. *Binary probabilities rank well but are poorly placed relative to a 0.5 threshold*: tuned thresholds raise UNFAIR-ToS micro-F1 from 0.50 to 0.75.
- **Zhong et al., "When the Right Answer Is Missing"** ([arXiv 2609.39496](https://arxiv.org/abs/2609.39496)). With the correct numerical answer absent and an explicit "none" option, JEV's correct rejection is 7% (vs 99% answer-present accuracy). A dev-set threshold raises it to 79%.
- **Munot, "When Multiple Choices Are Correct"** ([arXiv 2610.29217](https://arxiv.org/abs/2610.29217)). In 28–50% of lists, at least one correct choice gets probability below 1/n. "A probability threshold does not identify the set of correct choices."
- **Duan et al., JEVal / "General Decision Models: Benchmarking and Insights Beyond Jev"** ([arXiv 2610.03935](https://arxiv.org/abs/2610.03935)). Decision models "can often identify the most likely outcome while substantially overstating its probability." On τ-bench, "faster local decisions reduce median episode time but lower task success as decision errors accumulate over long trajectories."
- **Agent-control papers.**
  - JevAgentHarness ([arXiv 2610.21412](https://arxiv.org/abs/2610.21412)): delegating tool choices without a fitted confidence threshold lowered success by 19.0 points. Per-choice thresholds fitted on the agent's own trajectories fix this.
  - REFLEX ([arXiv 2609.26532](https://arxiv.org/abs/2609.26532)): 95% success with 72.7% fewer strong-model calls. "Reliability depends on action-set size and near-valid alternatives near authorization boundaries."
  - Vats ([arXiv 2610.24649](https://arxiv.org/abs/2610.24649)): pre-specified Terminal-Bench 2.1 study. JEV as controller raised cost by 19% at identical pass rate. Its finish-request AUROC was 0.78, but mean P(complete) was 0.50 when 87% of runs passed.
  - Ling et al. ([arXiv 2610.13092](https://arxiv.org/abs/2610.13092)) report a similar finding: local savings did not translate into better agents.
  - System1-Arena ([arXiv 2610.21244](https://arxiv.org/abs/2610.21244)): 92k questions over 105 tasks, incl. "evaluation and control" and "agent and action" groups. The largest System-1 models match fast closed LLMs with better calibration at a quarter of the latency; small System-1 models rarely succeed in closed loops.
- **Chen & Le, "Suggested Is Not Superseded"** ([arXiv 2610.15710](https://arxiv.org/abs/2610.15710), pre-registered). A cascade escalating uncertain cases to a reasoning model "looked best on development data" but was indistinguishable from simply raising the threshold on held-out data. Advice: "do not trust a cascade selected on development data of this size."

**Search coverage note.** Citation lists came from arXiv API queries (all:JEV, abs:TypeSafe, "decision model" + judge/monitor/safety/agent/guardrail/cascade, abs:"JEV-as-a-Judge"). Semantic Scholar's API returned HTTP 429 twice, so a formal "cited-by" list for 2609.26550 could not be retrieved. Google Scholar and OpenReview were not queried.

### Inferences
- **Net assessment for a cheap first-stage monitor.**
  - (1) JEV is a credible *screening* signal on *legible* risk (overt harmful requests, rule-checkable policies, retrospective trace labels like R-Judge and ATBench), at about 1 s and roughly $0.0002 per trace.
  - (2) Its weaknesses converge from several directions: read-vs-derive (JEV paper, derivation gap, stale-state), holistic judgment (phishing, style-adversarial), and adversarial manipulation that does not lower confidence (option-channel, style-adversarial).
  - Those weaknesses are precisely the threat model of a scheming or sabotaging agent. Confidence-based escalation therefore cannot be trusted to route the *adversarially-crafted* cases.
- **Design implications.**
  - Use JEV-class models as a *recall-oriented filter* with the threshold set by a finite-sample risk-control procedure (LTT, or Jung et al.-style fixed-sequence testing) on an enriched set of attack trajectories, with per-attack-family thresholds.
  - Never let it be the sole allow decision.
  - Feed it structured, pre-derived facts (DeRef-style references, parsed tool-call fields).
  - Use a fallback with different evidence access to avoid shared-error ceilings (Rao & Callison-Burch).
  - Include a random-escalation control and fixed-FPR metrics.
  - Budget for escalation-draining attacks (GateDrain).
- The prompt-injection result (>91.8% escalation needed at 1% FNR) is the most direct quantitative warning. At the strict miss-rate targets typical of safety monitoring, current decision-model gates may save little.

### Gaps
- No paper found that evaluates JEV (or open decision models) as a monitor for covert sabotage or scheming in long agent trajectories with a *fixed audit budget* and adversarially-optimized attack policies (control-evaluation style).
- No independent replication of the JEV-as-a-Judge cascade on safety or agent data was found. The trace-security paper did not evaluate confidence routing.
- Several cited results are from single-author or very fast-turnaround preprints (posted within days or weeks of the model's release). Most numbers above come from abstracts or HTML extractions and were not checked against full PDFs, except the JEV paper (read in full), Rao & Callison-Burch 2026b, Just Ask Jev, the option-channel attack paper, Xu et al. 2025, and the trace-security paper (HTML extractions).
- The vendor documentation (docs.typesafe.ai) was accessed only via a secondary blog summary, not directly.
