# Open-weight decision models (JEV-style "System One" classifiers): catalog, Decision Index, recipes, and monitoring fit (as of 22 Oct 2026)

How these notes were gathered: the Decision Index Space's raw data files (`data/index.json`, `data/methodology.json`, `news.html`, README) were pulled from the Hugging Face Space on 2026-10-22 (board generated 2026-10-22T20:10Z). Model metadata (license tag, size, creation date, base model) comes from the Hugging Face model API, and details come from the model cards (README.md) of about 35 repos, plus GitHub READMEs and web searches. No accounts were created and no weights were downloaded. Repo file listings were read only to check whether the weights are public. Unless a line says otherwise, every number below is the author's own claim or the board's measurement. Points marked **UNVERIFIED** or **CONFLICT** need care.

Background on the hosted reference model: TypeSafe AI came out of stealth on 2026-09-15 with **Jev**, a "System One Model". It takes unstructured input and returns typed decisions with probabilities instead of text. TypeSafe attributes it to a new architecture, a parallel sampler, and "RLCD" (Reinforcement Learning for Calibrated Decisions). The CEO is Diogo Almeida, a former OpenAI researcher and RLHF co-inventor. The company has raised $40M. — [NYU Shanghai RITS summary](https://rits.shanghai.nyu.edu/ai/typesafe-jev-system-one-model); [techstrong.ai GA article](https://techstrong.ai/features/typesafe-opens-jev-for-general-availability/). The Space's tracker says Jev's weights, the RLCD algorithm/loss/data, and "a trained open model matching Jev's calibration claims" are still not in the open. RLCD "is described only at blog-post level; no public implementation" — [Decision Index news tab](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/news.html). The JEV-as-a-Judge paper (arXiv 2609.26550 v5) calls the hosted API "TypeSafe JEV" (v1.13.0, $0.042 per 1M input tokens, $0 output) and uses three typed primitives: Choice, Noul (yes/no) and Score — local paper text (`_source_jev_as_judge_paper_fulltext.txt`, §4).

---

## Q1. The Decision Index: where it is hosted, what it measures, safety/agentic coverage, current top entries

### Takeaway
The Decision Index is a static Hugging Face Space, `multimodalart/jev-decision-index`. Its open-source kit is at `github.com/apolinario/decision-index`. It is now at **edition 0.4.1 (2026-10-21)**, not the 0.3 edition the paper cites. Since 0.4 the headline "Full score" is computed **only from private tests**: 60% same-skill tests and 40% new-domain tasks. The board covers 5 areas and 37 public benchmarks. None of them is a dedicated safety, moderation, prompt-injection or agent-trajectory benchmark; the nearest are phishing, hallucination (RAGTruth), tool-call and When2Call. On the current board, **Fastino GLiDE 1.2 is #1 (71.52)**, followed by Jeffan-31b (69.75), baselabs mammoth-1 (68.44) and Perplexity Decider v1.2 (67.98). Jev 1.14 sits at rank 41 (60.24). That means about 40 open entries now score above hosted Jev on the private-only Full score, and the board's ranks have reshuffled sharply since the paper's 0.3 snapshot.

### Cited Findings
**Hosting and governance**
- The Space is `https://huggingface.co/spaces/multimodalart/jev-decision-index`. It is a static SDK Space titled "Jev Decision Index" with the short description "Benchmarks and news on various repros of TypeSafe's Jev". It had 779 likes and was last modified 2026-10-22 — [HF Space API](https://huggingface.co/api/spaces/multimodalart/jev-decision-index).
- The README describes it as "Unofficial and community-maintained; not affiliated with TypeSafe AI". It has two tabs: **Index** (the leaderboard plus per-model pages at `index.html?model=<engine>`, with a Vision board) and **News** (a tracker of open Jev reproductions, sorted into Decoding / Diffusion / Trained / Prior art / Explainers) — [Space README](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/README.md).
- The reproduction kit and scripts live at `https://github.com/apolinario/decision-index` (scripts such as `evaluation/reproductions/run.py` and `compute_indices.py`) — [methodology.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/methodology.json). Submissions arrive as PRs on that repo or the Space; Perplexity submitted a results dataset (`perplexity-ai/decision-index-results`) instead — [index.json model notes](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json).
- Hardware: the lab runs every entrant on **1× NVIDIA RTX PRO 6000 (Blackwell, 96 GB)**. Jev is run through the TypeSafe API (jev-1.14.0, lab run 2026-10-14; API cost for the suite was $12.26) — [index.json `suite`](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json); [methodology.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/methodology.json).

**What it measures**
- The frozen request corpus has 110,201 requests (109,759 scoreable) across 42 benchmarks. The panel used for the index ("decision-index-0.3") has **37 benchmarks in 5 areas**, all chance-corrected so that 0 = random and 100 = perfect. "Unanswered = wrong", with no truncation, no option pruning, no prompt tuning and no correctness-based retry — [index.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json); [methodology.json `rules`](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/methodology.json).
- The areas and their benchmarks:
  - **Knowledge & Reasoning:** GPQA Diamond, GSM8K (option-choice form), ChessBench, MuSR, SATA-Bench, CRUXEval, CLadder, HLE, MMLU-Pro, BBH, WinoGrande.
  - **Language Understanding:** ContractNLI, ANLI, HellaSwag, ACOS, FinEntity, iSarcasmEval, VAST, NLI4CT, RAGTruth.
  - **Retrieval & Classification:** BANKING77, CLINC150, BRIGHT, Amazon ESCI, **PhishNChips** (phishing email+link), HoVer.
  - **Tools & Automation:** **BFCL** (call this function? per function), ToolRet, API-Bank, Home appliances, **When2Call** (answer / call a tool / ask / decline).
  - **Arts & Human Taste:** BPoMP, Humicroedit, POP909, cfcolor, Habermas, New Yorker.
  - A "Games & Strategy" area exists with no panel. Six interactive environments (MiniWoB++, Boxoban, RTFM, ScienceWorld, Hanabi, Codenames) were dropped because "no reproduction has run it" — [index.json `categories`/`benchmarks`](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json).
- Safety-adjacent coverage: none of the 5 areas is a safety, moderation, prompt-injection or agent-trajectory category. The closest items are PhishNChips (phishing detection, added in v0.2), RAGTruth ("does an AI-written answer contain anything its source doesn't support?", F1 on the hallucinated class), BFCL and When2Call (tool-call gating, including "decline"). "Phishing gradient", "Email spam" and "Support tickets" are run but are not in the index — [index.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json); [methodology.json `added_benchmarks`](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/methodology.json).
- Score definitions by edition, from the changelog:
  - **v0.3 (2026-10-06):** Full = 0.20 × public + 0.50 × private same-skill + 0.30 × private new-domain. Ties within 0.9 points.
  - **v0.3.2 (2026-10-12):** fixed a bug that had left GPQA, MMLU-Pro and BBH skill sets out of the same-skill score for 37 models.
  - **v0.4 (2026-10-19):** Full = **0.60 × private same-skill + 0.40 × private new-domain**. Public benchmarks are "still run and shown … but they no longer count".
  - **v0.4.1 (2026-10-21):** new-domain tests expanded and made harder.
  - [methodology.json `changelog`](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/methodology.json)
- Calibration is also reported for each model: ECE/Brier over 32 benchmarks with a per-field right/wrong answer, on a 1-in-6 sample, with confidence taken as the probability of the chosen option. Latency is measured separately on 750 rows, one request at a time, on the RTX PRO 6000 — [index.json `suite.calibration_note`](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json); [methodology.json `latency`](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/methodology.json).
- Entrants are classified by what they ship: "inference technique" (stock weights plus their own readout code), "full fine-tune", "LoRA", "LoRA + head", "head / adapter". The technique is one of autoregressive, diffusion, encoder or GLi-family. The board holds 228 entrants — [methodology.json `entrants`](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/methodology.json).

**Current top entries (Decision Index 0.4.1, board generated 2026-10-22).** Columns are rank group, Full score, public-only score, ECE, median latency in ms on the RTX PRO 6000, and the three safety-adjacent public benchmarks: BFCL, When2Call and PhishNChips (raw accuracy). Source for all rows: [index.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json).

| # | Entry (HF repo) | Full | Public | ECE | lat ms | BFCL | When2Call | Phish |
|---|---|---|---|---|---|---|---|---|
| 1 | Fastino GLiDE 1.2 (`fastino/GLiDE`) | 71.52 | 71.99 | 0.020 | 93 | .973 | .916 | .859 |
| 2 | Jeffan-31b-1710 (`tattrongvu/Jeffan-31b-1710`) | 69.75 | 73.13 | 0.047 | 121 | .975 | .921 | .849 |
| 3 | baselabs mammoth-1 27B (`baselabs/mammoth-1`) | 68.44 | 75.34 | 0.041 | 220 | .982 | .917 | .971 |
| 4 | Perplexity Decider v1.2 27B (`perplexity-ai/pplx-decider-v1.2`) | 67.98 | 67.74 | 0.055 | 144 | .978 | .903 | .747 |
| 5 | AutoTrust-JEV-27B v1.1 | 67.95 | 67.32 | 0.067 | 80 | .972 | .895 | .720 |
| 6 | StartLux-Decision v1.1 27B Instant | 67.92 | 72.88 | 0.026 | 80 | .979 | .938 | .918 |
| 7 | AJev lm6q (Gemma 4 31B LoRA) | 67.57 | 65.46 | 0.096 | 144 | .978 | .861 | .866 |
| 9 | Lychee-27B | 67.35 | 62.76 | 0.108 | 97 | .969 | .819 | .764 |
| 10 | vLLM-SR d3-turbo v1.1 (27B) | 67.31 | 71.62 | 0.052 | 191 | .977 | .899 | .962 |
| 11 | vLLM-SR d3 (27B) | 67.15 | 65.45 | 0.043 | 97 | .973 | .864 | .739 |
| 16 | H2O Lightning 31B | 66.58 | 66.69 | 0.084 | 57 | .978 | .840 | .802 |
| 17 | Bespoke Nimble v4 Max (27B) | 66.56 | 68.46 | 0.064 | 107 | .980 | .907 | .914 |
| 21 | KnowLine 35B-A3B Gen1.5 | 65.77 | 70.72 | 0.044 | 47 | .975 | .915 | .983 |
| 35 | Torchcast Decision 27B | 61.49 | 65.10 | 0.024 | 100 | .977 | .890 | .704 |
| 41 | **Jev 1.14 (hosted)** | 60.24 | 60.70 | 0.080 | 196* | .964 | .817 | .838 |
| 46 | Kev 27B | 59.56 | 56.69 | 0.022 | 135 | .978 | .621 | .624 |
| 47 | Xor 26B-A4B v1.2 | 59.44 | 59.46 | 0.068 | 110 | .957 | .646 | .809 |
| 52 | Eikos-27B-FP8 | 58.79 | 52.85 | 0.057 | 130 | .963 | .792 | .639 |
| 59 | simple-jev (stock Qwen3.8-27B) | 56.99 | 56.05 | 0.113 | 373 | .968 | .750 | .847 |
| 68 | Cloudflare Clef 27B | 54.92 | 61.71 | 0.040 | 102 | .985 | .725 | .794 |
| 216 | Laya (421M encoder) | 9.21 | 6.19 | 0.140 | 6 | .381 | .119 | .502 |
| 221 | CLM-v0.1-8B | 6.49 | 7.41 | 0.323 | 47 | .389 | .387 | .651 |

  *Jev's latency is a hosted HTTPS round trip, so it is not comparable to the on-card figures.
- The ranks used in the paper's Table 6 (DI 0.3, 7 Oct) no longer hold:
  - Perplexity Decider v1.1 (0.3 rank 1) has been replaced by v1.2, which is now #4.
  - Torchcast fell from 4 to 35. Kev went from 6 to 46, Xor from 12 to 47, Clef from 19 to 68.
  - GEV-26B-Decide (paper's rank 11) is not on the current board under any engine name I could find.
  - AutoTrust has newer entries: JEV-27B (#58), JEV-35B (#57) and AutoTrust-JEV-27B v1.1 (#5).
  - [index.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json); local paper Table 6
- Board integrity notes:
  - Several top entries declare they trained on official train splits of index benchmarks, or that index results guided checkpoint selection. Perplexity v1.2 says its checkpoint is "a weight average of several runs chosen partly on Decision Index". StartLux says "Public 0.3 scores guided the recipe". Torchcast says "Index results guided checkpoint selection".
  - mammoth-1 had one private new-domain test dropped for suspected training overlap.
  - [index.json `notes`](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json)
- mammoth-1's card claims "#1 of 208 models on the Jev Decision Index 0.4: 71.24". That is a pre-0.4.1 snapshot; on the live 0.4.1 board it is #3 at 68.44 — [mammoth-1 card](https://huggingface.co/baselabs/mammoth-1) vs [index.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json).

### Inferences
- For a monitoring team, DI rank is a weak signal. The paper found a rank correlation of 0.12 between DI 0.3 rank and accuracy on its 5,172 judge items (local paper, App. A). The board also changed its weighting twice in two weeks, and its private new-domain tasks are not published. The only safety-relevant per-benchmark signals are PhishNChips, RAGTruth, BFCL and When2Call, and none of them measures detection of agent misbehavior.
- Calibration on the board is generally better than Jev 1.14's ECE of 0.080 for the top open entries: GLiDE 0.020, StartLux 0.026, Torchcast 0.024, Kev 0.022. That matters if monitor thresholds will rely on the probabilities.

### Gaps
- The contents of the private same-skill and new-domain tests are never published, so it is unknown whether they include safety or agentic decisions.
- I could not retrieve a snapshot of the exact 0.3 leaderboard the paper used (7 Oct). The `v03.json` file now holds 0.4.1 data.
- Why GEV-26B-Decide is absent from the current board is not documented in the files I read.

---

## Q2. Catalog of the top open models: repo, base, size, context, license, readout/head, serving, VRAM, and long-context fitness

### Takeaway
Almost every strong open decision model is a **~26–31B dense transformer**:
- Fine-tunes of **Qwen3.8-27B**, a hybrid model with linear attention plus one full-attention layer in four, and a 262,144-token native window.
- Or fine-tunes of **Gemma-4-31B-it**. A few use Gemma-4-26B-A4B or Qwen3.5-35B-A3B MoE backbones.

In bf16 they need about 52–63 GB for weights, so one 80–96 GB GPU (H100/H200/RTX PRO 6000) runs them.

Readouts come in two families:
- **(a) Label-token logit readout** on the LM head: option letters A–Z or true/false, softmax over the listed options, with a fitted temperature. Examples: Jeffan, StartLux, Jebadiah, Quyet, Eikos, Blink, KnowLine, Xor.
- **(b) A small trained decision head:** Perplexity's 255-row readout, Clef's joint schema transformer head, Kev's pointer head, AutoTrust's 24-slot head, GLiDE's 255-way readout. Several also use bidirectional or "non-causal" attention over the prompt (pplx v1.1+, StartLux, mammoth, d3).

Models with documented support for **≥128k context** include:
- Torchcast (256K)
- AutoTrust JEV-27B (needle test passed to 250K)
- pplx-decider v1.2 and flash (default 262K, but trained only to ~32K)
- Lychee (262K)
- MISA decision-plus (256K)
- Surogate Rune (262K)
- Xor (131K)
- H2O Lightning (131K)
- d3-turbo (131K with `long_context=True`)

GLiDE stops at 40K by default, Kev is validated to 64K, and mammoth-1 (16K) and Jeffan (8K) are short. **None of the long-context claims has been validated on agent-trajectory monitoring**; they rest on needle-in-haystack or retrieval spot checks.

### Cited Findings
**Licensing and availability (from HF API tags and cards, 2026-10-22)**
- Apache-2.0 (commercial use OK): pplx-decider v1.1, v1.2 and flash-v1.2; AutoTrust JEV-27B, AutoTrust-JEV-27B-v1.1 and GEV-26B-Decide; vLLM-SR d3, d3-turbo and Vega; Cloudflare Clef; Kev-27B; Xor; Jebadiah; Quyet; decider-31b; OneJev1.6; KnowLine; MISA decision-plus (Gemma 4 license); Rune; Blink; Laya; CLM — [HF model API](https://huggingface.co/api/models/perplexity-ai/pplx-decider-v1.2) and each repo's card linked below.
- MIT: baselabs/mammoth-1 and Eikos-27B-FP8 — [mammoth-1](https://huggingface.co/baselabs/mammoth-1); [Eikos](https://huggingface.co/caiovicentino1/Eikos-27B-FP8). **CONFLICT:** the board note says mammoth-1 weights are "public … under a proprietary license" — [index.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json).
- CC BY-NC 4.0 (non-commercial): **Torchcast Decision 27B** (inherited from StartLux), StartLux-Decision v1.1, Bespoke Nimble-v4-max, Lychee-27B — [Torchcast card](https://huggingface.co/torchcast-ai/torchcast-decision-27b); [StartLux](https://huggingface.co/startlux-models/StartLux-Decision-v1.1-27B-Instant); [Nimble-v4-max](https://huggingface.co/bespokelabs/Nimble-v4-max); [Lychee](https://huggingface.co/LycheeAI/Lychee-27B).
- H2O Model Non-Commercial Licence v1.1, gated with auto-approval: h2o-lightning-31b — [card](https://huggingface.co/h2oai/h2o-lightning-31b).
- Fastino Community License: GLiDE. It is free to use, but entities with more than $10M annual revenue need a commercial agreement for production commercial use, and commercial users must display "Built with Fastino GLiDE" — [GLiDE LICENSE](https://huggingface.co/fastino/GLiDE/blob/main/LICENSE).
- **CONFLICT (Jeffan):** the HF card and tag say Apache-2.0 for weights and inference code, but the board note says "License CC BY-NC 4.0" — [Jeffan card](https://huggingface.co/tattrongvu/Jeffan-31b-1710) vs [index.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json).
- **CONFLICT (GLiDE availability):** the paper (8 Oct) says GLiDE "has no public weights", and the board note says "Model repository is private; the lab ran the weights shared for evaluation". As of 2026-10-22, however, the HF API reports `fastino/GLiDE` as `private: false, gated: false`. The repo was created 2026-10-19 and lists 52.2 GB of safetensors, and an anonymous `resolve` of config.json returns a 307 redirect. Its README still says "Internal use only" and "needs a token with read access to the fastino org". So the weights appear newly downloadable, but this is **UNVERIFIED** (I did not download) — [HF API](https://huggingface.co/api/models/fastino/GLiDE); [GLiDE card](https://huggingface.co/fastino/GLiDE). The pplx-decider-v1.2 README similarly says "The repository is private", while the API shows it public and listable — [pplx-decider-v1.2](https://huggingface.co/perplexity-ai/pplx-decider-v1.2).

**Per-model details (top ~12 plus the paper's notable ones)**
- **Fastino GLiDE v1.2** — `fastino/GLiDE`.
  - Base: the board says Qwen/Qwen3.8-27B (26.1B params per the API), and the license confirms it is "a modified version of Qwen3.8-27B".
  - Readout: a 255-way decision readout (2.6 MB). "Nothing is generated"; one forward pass per question, micro-batched.
  - Context: up to **40,000 tokens per question prompt** by default.
  - Memory: bf16 weights of 52.2 GB need one GPU with at least 80 GB; peak was 60.2 GB for a 39k-token question, which took about 13 s on an RTX PRO 6000.
  - Tested on RTX PRO 6000, B200 and H100. Python package `glide`; HTTP `/v1/systemone`; torch 2.14, transformers 5.17, and optionally flash-linear-attention.
  - Hosted API price is $0.30/M input tokens.
  - [GLiDE card](https://huggingface.co/fastino/GLiDE); [gradually.ai summary](https://www.gradually.ai/en/ai-models/glide/)
- **Jeffan-31b-1710** — `tattrongvu/Jeffan-31b-1710`.
  - Base: Gemma-4-31B-it, full fine-tune.
  - Context: "inputs up to 8,192 tokens" (the vLLM example uses max_model_len 98,312).
  - Readout: one question at a time in its own prompt layout, reading option-code logprobs (≤26 codes), with a "second read" when top-1 is below 0.9.
  - Serving: vLLM 0.29 bf16 on a B200 or one 96 GB GPU. Training data undisclosed.
  - [card](https://huggingface.co/tattrongvu/Jeffan-31b-1710); [index.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json)
- **baselabs mammoth-1** (Base Labs at Baseten) — `baselabs/mammoth-1`.
  - Base: Qwen3.5-27B, full fine-tune with a "block-bidirectional mask on full-attention layers". Answers all questions from one shared-prefix prefill.
  - Context: max sequence length **16,384 tokens**.
  - Data: 6.21M decision examples, of which **16.1% are "safety and abstention"**. Objective: cross-entropy plus a Brier calibration term, with a trained "I don't know" option.
  - Serving: OneJev `qev` engine. A 9B sibling, `baselabs/elephant-1`, is #40.
  - [card](https://huggingface.co/baselabs/mammoth-1)
- **Perplexity Decider v1.2** — `perplexity-ai/pplx-decider-v1.2`.
  - Base: Qwen3.8-27B, with a `Qwen3_5Model` backbone plus `readout.safetensors`, a BF16 **[255, 5120] decision head** ("not a full-vocabulary lm_head").
  - Request format: "joint" — state, then all questions, each read out at a marker token after its options.
  - Calibration: temperature 1.382 fitted on held-out data (dev ECE 0.014, Brier 0.134).
  - Context: max_length defaults to **262,144**, but "Training used sequences up to about 32k tokens". A single-fact retrieval from a long log works to about 243k tokens, with peak memory around 95 GiB on the reference path.
  - Serving: custom PyTorch package `pplx_decider` with a fast path (static 2k–32k buckets, CUDA graphs). It needs about 52 GiB of BF16 weights.
  - v1.1 (paper's rank 1, 8k in the paper's table) attributes its gains to "the lifting of the causal mask and training on more data, including … tasksource". The 4B distilled flash-v1.2 (Qwen3.5-4B, readout [255, 2560]) peaks around 39–54 GiB at long context.
  - [v1.2 card](https://huggingface.co/perplexity-ai/pplx-decider-v1.2); [v1.1 card](https://huggingface.co/perplexity-ai/pplx-decider-v1.1-27b); [flash card](https://huggingface.co/perplexity-ai/pplx-decider-flash-v1.2)
- **AutoTrust-JEV-27B v1.1** — `autotrust/AutoTrust-JEV-27B-v1.1`. Fine-tuned from vLLM-SR d3. It "contains the fine-tuned … weights and its decision readout head", is served with vLLM, and on an 80 GB card should use `MAX_LEN=32768` — [card](https://huggingface.co/autotrust/AutoTrust-JEV-27B-v1.1); [index.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json).
- **AutoTrust JEV-27B** (earlier release) — `autotrust/JEV-27B`.
  - Architecture: Qwen3.8-27B text tower with a LoRA r=16 plus a "24-slot fp32 decision head initialised from lm_head rows". It is *distilled from Jev 1.13's published output distributions* (dataset `SargeDev/jev-distill-corpus-v3`) with KL plus an RPS term; fitted temperature ≈1.0 and ECE 0.0009 on its own test set. The System 2 LM head is kept untouched.
  - Context: **needle test 10/10 at 4K, 32K, 64K, 128K, 192K and 250K tokens**, at 28.7 s for 250K on a B200. KV cache is about 65 KB/token, so a 256K prompt needs about 17 GB plus 52 GB of weights; on 80 GB, start with `--max-model-len 131072`.
  - The paper's "AutoTrust JEV-27B (256k)" is this line.
  - [JEV-27B card](https://huggingface.co/autotrust/JEV-27B)
- **StartLux-Decision v1.1 27B Instant** — `startlux-models/StartLux-Decision-v1.1-27B-Instant`.
  - Readout: option-letter logits divided by a per-type temperature.
  - Attention: in the full-attention layers (one in four), prompt tokens attend to later prompt tokens; the linear-attention layers stay causal.
  - Training: stage 1 is full fine-tuning on about 0.8M decision examples; stage 2 is a bidirectional-attention adapter on about 1.7M more, merged.
  - Serving: vLLM 0.19.1/0.31. License CC BY-NC 4.0, with commercial use via contact@startlux.com.
  - [card](https://huggingface.co/startlux-models/StartLux-Decision-v1.1-27B-Instant)
- **vLLM Semantic Router d3 / d3-turbo** — `vllm-sr/d3`, `vllm-sr/d3-turbo`.
  - Base: Qwen3.8-27B, Apache-2.0, multimodal including video and boxes. Reads the prompt with **bidirectional attention**.
  - Context: `vllm serve vllm-sr/d3 --max-model-len 32768`; the full 262,144 limit "does not fit on an 80 GB GPU". d3-turbo supports 131,072 tokens per question with `long_context=True` (32,768 by default).
  - Trained on AMD MI325X; verified on MI300X/ROCm.
  - [d3](https://huggingface.co/vllm-sr/d3); [d3-turbo](https://huggingface.co/vllm-sr/d3-turbo)
- **vLLM-SR Decision-2.0 Vega 27B** (paper's "Vega") — LoRA adapter on Qwen3.8-27B, 32,768-token context, Apache-2.0 — [card](https://huggingface.co/vllm-sr/Decision-2.0-Vega-27B).
- **H2O Lightning 31B** — `h2oai/h2o-lightning-31b`. Gemma-4-31B-it base; "each decision is one forward pass and one output token". The Decision Index profile uses **MAX_LEN 131,072** on an RTX PRO 6000 (96 GB) and refuses over 126,976 tokens. vLLM 0.30, FP8. Non-commercial license — [card](https://huggingface.co/h2oai/h2o-lightning-31b).
- **Bespoke Nimble v4 Max** — `bespokelabs/Nimble-v4-max`. Qwen3.8-27B fine-tune, about 55 GB BF16, one 80 GB GPU, CC BY-NC 4.0 — [card](https://huggingface.co/bespokelabs/Nimble-v4-max).
- **Torchcast Decision 27B** — `torchcast-ai/torchcast-decision-27b`.
  - A **LoRA fine-tune of StartLux-Decision-27B, merged** (54.7 GB bf16; GPU with at least 64 GB). One H100 80GB serves it.
  - Context up to **262,144 tokens (256K)**, though "the evaluations below are text-only". A long state is "read once in chunks first".
  - Latency 33.0 ms per yes/no question and 49.0 ms for 3 questions on an H100 (CUDA graphs). Ships `torchcast_decision/` (Apache-2.0) behind `/v1/systemone`.
  - Weights are CC BY-NC 4.0.
  - In the paper it had the best error AUROC (0.860).
  - [card](https://huggingface.co/torchcast-ai/torchcast-decision-27b)
- **Kev 27B** — `jaredpalmer/kev-27b`.
  - Full-weight SFT of Qwen3.8-27B (25.6B params loaded), served prefill-only with a **pointer head** (two 5,120→256 projections, 2.6M params) and T = 1.32.
  - Context: **states up to 65,536 tokens** validated, plus ≥8,192 tokens per question; trained on states ≤32,768. Memory 51 GB weights, about 65.5 GB resident; a 64k state peaked at 87.1 GB on an H200.
  - Data: 145,840 records. Apache-2.0.
  - [card](https://huggingface.co/jaredpalmer/kev-27b)
- **Xor 26B-A4B v1.2** (Juspay) — `juspay/Xor-26B-A4B`. Gemma-4-26B-A4B-it MoE (4B active), weight blend of two post-trained checkpoints, two-order scoring, per-type temperatures. **Context 131,072**. About 96 GB GPU for the tested settings; SGLang. Apache-2.0 — [card](https://huggingface.co/juspay/Xor-26B-A4B).
- **Eikos-27B-FP8** — `caiovicentino1/Eikos-27B-FP8`. LoRA lineage on Qwen3.8-27B, FP8 at 31.2 GB versus 55.6 GB bf16, letter readout with `calib.json` T = 1. Served by vLLM 0.30 with `--max-model-len 65536`. MIT plus Apache base — [card](https://huggingface.co/caiovicentino1/Eikos-27B-FP8); [index.json latency_path](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json).
- **simple-jev** (Featherless AI) — no training. It "reads the model's next-token logits for each question" on stock HF models (Qwen3.8-27B recommended with `--max-model-len 32768`, up to 255 options) — [GitHub](https://github.com/featherless-ai/simple-jev).
- **Cloudflare Clef 27B** — `Cloudflare/clef`.
  - Post-trained Qwen3.8-27B plus a **"joint schema head": a small transformer head that reads the backbone's final hidden states** and scores all options of all questions jointly.
  - `encode_record` default max_length is 16,384. SGLang support (`lmsysorg/sglang:dev-clef`); tested on an H200. Apache-2.0.
  - Variants: clef-flash (Qwen3.5-9B) and clef-omni (Qwen3-Omni-30B-A3B, 64K).
  - [card](https://huggingface.co/Cloudflare/clef); [Cloudflare blog](https://blog.cloudflare.com/clef-decision-models)
- **Surogate Rune 26B-A4B v3** — Gemma-4 MoE, **262k context**, GGUF plus bf16, `surogate serve --max-model-len 262144`. Overconfident at T = 1 (use T = 2). Optional "thinking" when confidence is below 0.7 — [card](https://huggingface.co/surogate/rune-26b-a4b-GGUF); [index.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json).
- **Blink v0.3 26B-A4B NVFP4** (Pixilab) — 17.5 GB on disk, served on a single RTX PRO 5000 with 32k context (needs Blackwell FP4). Letter readout with T = 1.3. Intended for "routing, moderation, tagging, gating" — [card](https://huggingface.co/PixilabAI/Blink-v0.3-26B-A4B-NVFP4).
- **Quyet-1.0-Large** — Gemma-4-31B-it, "state up to 6,000 tokens inside an 8,000-token prompt", 62.5 GB bf16, option-letter next-token probabilities plus calibrated temperatures, `pip install quyet` — [card](https://huggingface.co/chinhnc/Quyet-1.0-Large).
- **Jebadiah 27B v2.1** (Frontier Infra) — merged LoRA on Qwen3.8-27B; "reads fp32 candidate-label logits at the last prompt position"; per-type temperatures. Training prompts capped at 2,048 tokens; 16,622 training records. About 56 GB bf16 — [card](https://huggingface.co/frontier-infra/jebadiah-27b-v2-1).
- **Other long-context entries:**
  - **Lychee-27B**: "read whole up to 262,144 tokens", 80 GB GPU, CC BY-NC — [card](https://huggingface.co/LycheeAI/Lychee-27B).
  - **MISA AI 2.0 Decision Plus** (Gemma-4-31B): "256K tokens", about 62 GB bf16, fits one 80 GB GPU — [card](https://huggingface.co/misa-jsc/misa-ai-2.0-decision-plus).
  - **GEV-26B-Decide**: Gemma-4-26B-A4B adapter, prompts up to 256K, "System 1 decides in one forward pass (about 45 ms)", optional adaptive thinking — [card](https://huggingface.co/autotrust/GEV-26B-Decide).
- **Small and encoder models from the paper:**
  - **Laya** (Convai Innovations; ModernBERT-large backbone plus a from-scratch decision head; 421M; 512-token English budget; multilingual up to 8k): Apache-2.0, "commercial-use" tag, RLCD-style training against proper scoring rules — [card](https://huggingface.co/convaiinnovations/laya).
  - **CLM-v0.1-8B** (Contrastive-LM): state and action projection heads over a frozen Qwen3-8B; the encoder is served at `--max-model-len 2048` — [card](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B).

**Serving stacks seen across cards.** vLLM is the most common (Jeffan, Eikos, H2O, Blink, AutoTrust, d3, Quyet). SGLang is used by Clef, Xor and KnowLine. Others use custom PyTorch/transformers packages (pplx_decider, glide, torchcast_decision, kev, qev/OneJev) or llama.cpp-style GGUF (Rune, Jebadiah 9B). Most expose a TypeSafe-compatible `POST /v1/systemone` endpoint — the cards cited above. vLLM docs host a "Decision 3.0" request spec, and LiteLLM has a native "Decision Model Guardrail" that works with any server exposing `/v1/decisions`, including self-hosted vLLM — [LiteLLM docs](https://docs.litellm.ai/docs/proxy/guardrails/decision_model.md); [d3 card](https://huggingface.co/vllm-sr/d3).

### Inferences
- **The best fit for white-box monitoring of long trajectories** is a Qwen3.8-27B derivative served from plain transformers or vLLM. Its hidden states are standard HF tensors, and Kev's pointer head, Clef's joint head, pplx's readout and AutoTrust's 24-slot head all read final hidden states, so activations are directly accessible.
  - Candidates with explicit ≥128K claims: Torchcast (256K, but non-commercial), AutoTrust JEV-27B (256K needle-validated, Apache), Xor (131K), H2O Lightning (131K, non-commercial), d3-turbo (131K), and pplx-decider v1.2 (262K default but only trained to ~32K).
  - Kev-27B is the most honest about its limits (validated to 64K). It is Apache-licensed and has a published fine-tuning path.
- On an 80 GB H100, 128K is the practical ceiling for most 27B models (AutoTrust's guidance). Full 256K needs about 70 GB plus overhead, which means an H200/B200 or a 96 GB RTX PRO 6000. The hybrid linear-attention backbone keeps KV cost low (about 65 KB/token for AutoTrust).
- Bidirectional and non-causal variants (pplx v1.1+, StartLux, mammoth, d3) break the causal prefix-cache assumption. That could make "score each step of a growing trajectory incrementally" more expensive than with causal label-logit models such as Jebadiah, Quyet or Eikos. This is an engineering inference, not tested.

### Gaps
- Most cards do not say whether accuracy holds beyond the training length (typically 2K–32K) on realistic long inputs. Kev (CUAD-based validated context) and AutoTrust (needle test) are the exceptions.
- Exact VRAM at 128K–256K is documented only for AutoTrust, pplx, GLiDE (≤40K) and Kev.
- I did not verify anonymous downloadability of GLiDE or pplx v1.2 beyond the HF API flags and an HTTP 307.

---

## Q3. Training recipes for building a JEV-like model from an open base; data and compute; fine-tuning on monitoring labels

### Takeaway
There are many public recipes, and the cost is modest:
- **Zero-training readout:** simple-jev, reflex and Jobe read restricted softmax logits over option labels on a stock model. In the paper, reflex on stock Qwen3.8-27B reached 83.5% versus 85.2–89.0% for tuned 27B models.
- **LoRA or full SFT with a temperature fit:** AutoJev used 1×H200 with 73K examples and 286 updates. Together's Tev1 cost $17 with about 38K examples. Bespoke Nimble used 2,676 examples. Kev-4B costs about $1 on an H100.
- **Distillation from Jev's output distributions:** AutoTrust JEV-27B.
- **Large-scale:** mammoth-1 used 6.21M examples and StartLux about 2.5M.

Fine-tuning a released decision model on your own labels is explicitly supported by Kev (`--init_from`), decider (`python -m decider.calibrate`), Laya (free Kaggle 2×T4 notebook) and CLM (fine-tuned verifier heads for DeepSWE and Terminal-Bench). Fine-tuning on monitoring labels is straightforward. The Kev authors warn that starting from the base rather than from the released decision checkpoint discards most of the gain.

### Cited Findings
- **simple-jev (Featherless AI):** "Use compatible open models from huggingface, for structured classification and scoring, without training a separate classifier head … reads the model's next-token logits for each question". It ships a prompt-search tool (`eval/prompt_search.py`) for choosing prompt formats per backbone — [GitHub](https://github.com/featherless-ai/simple-jev).
- **reflex:** "No training: prompt scaffold and label-logprob readout on the stock Qwen3.8-27B-FP8 checkpoint" — [index.json notes](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json). Temperature scaling gets Qwen3.5-4B to 0.039 ECE — [news tab](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/news.html); [GitHub](https://github.com/kshetrajna12/reflex).
- **AutoJev-27B** (`denis-pplx/AutoJev-27B`; "built with autonomous agents"): "One H200 · full-weight SFT · 73,000 unique training examples · 286 updates", cross-entropy plus a separately fitted scalar temperature. Self-reported: 84.60% versus Jev 82.79% versus base 69.83%. Code is MIT at github.com/denis-pplx/autojev, weights Apache-2.0. The card notes the weights may be private ("While the weights are private, authenticate…") — [HF card](https://huggingface.co/denis-pplx/AutoJev-27B).
- **Together AI Tev1-4B-experimental:** Qwen3.5-4B, 37,840 training plus 4,568 validation examples, LoRA rank 8, one epoch, lr 5e-5, 2,048-token limit, "train your own classifier for $17" — [GitHub tev1](https://github.com/togethercomputer/tev1); [Together blog](https://www.together.ai/blog/how-to-train-your-own-jev).
- **Bespoke Nimble (first "fully open recipe"):** LoRA on Qwen3.5-9B on answer tokens only. "Contrastive curation flips one fact to make negatives". It published 2,676 training and 324 held-out examples and reaches 90.1% agreement with reference labels (base 66.4%, Jev 93.2%) — [GitHub nimble](https://github.com/bespokelabsai/nimble).
- **Kev:**
  - Kev-0.8B/4B/9B use "a small adapter on a frozen base" plus a pointer head; Kev-27B is full-weight.
  - "A Kev-4B training run costs about $1 on an H100". On a support workload (1,050 records, 15 min on an H100), fine-tuning took Kev-4B from 67.7% to 73.6%; "With 400 records, the gain … was inside the noise".
  - "in one user's test on 836 support-tool decisions, a fine-tune from the base scored 0.33 … against 0.84 for the released model; the same data with `--init_from` kept 0.83".
  - [GitHub kev](https://github.com/jaredpalmer/kev)
- **decider (Mapika):**
  - Full fine-tunes on Qwen3.5 bases (the 2B with a calibration-aware RL stage). The training mixture is public datasets plus teacher-labelled data from a local Qwen3.5-27B.
  - decider-31b v2 added a LoRA stage (rank 32, 421 steps, 12.3M tokens, 2 hours on one B300).
  - A `python -m decider.calibrate` tool fits temperature maps.
  - [GitHub decider](https://github.com/Mapika/decider); [decider-31b card](https://huggingface.co/Mapika/decider-31b)
- **AutoTrust "Blocks of Experts" distillation:** LoRA r=16 plus a 24-slot decision head initialised from the backbone's lm_head rows for the verbalizer tokens, trained by distilling Jev 1.13's full output distributions (KL plus RPS). "Calibration falls out of the objective" (fitted T ≈ 1.00) — [JEV-27B card](https://huggingface.co/autotrust/JEV-27B).
- **Laya:** "RLCD" as implemented by Convai — the policy reports a distribution, exploration adds Gaussian noise to logits, and the reward is a strictly proper scoring rule (log plus spherical, plus RPS). A fine-tuning notebook "runs the whole loop on Kaggle's free 2x T4 GPUs (build the dataset, train, fit calibration temperatures, evaluate…)" — [Laya card](https://huggingface.co/convaiinnovations/laya).
- **Large recipes:** mammoth-1 used 6.21M examples (58.3% core decision skills, **16.1% safety and abstention**, 16.1% judging and expert domains, 9.5% public decision data) with CE plus a Brier term — [mammoth-1](https://huggingface.co/baselabs/mammoth-1). StartLux used about 0.8M plus 1.7M examples in two stages — [StartLux](https://huggingface.co/startlux-models/StartLux-Decision-v1.1-27B-Instant). OneJev1.6-27B used about 440,000 questions "drawn from real agent runs, videos, images and … public decision datasets" — [OneJev1.6-27B](https://huggingface.co/OmniJev/OneJev1.6-27B).
- **Cygnet:** listed as "Cygnet (blockbrain, frozen Gemma-4-12B-it)", a "decision reading model" on a frozen backbone. It was joint leader on JevBench 1.5 at 73.70 — [benchlm.ai](https://benchlm.ai/models/jevbench-cygnet). (The paper ran "the Cygnet recipe on Gemma-4-12B-it": 83.7% pooled at 35 ms — local paper Table 6.)
- **CLM (Contrastive-LM, Stanford-affiliated authors incl. Azalia Mirhoseini and Christopher Ré per the citation):**
  - "pre-trained on ~60M Nemotron Q&A pairs, mid-trained on ~30M synthetic hard negatives, post-trained on ~1M agentic trajectories".
  - Fine-tuned as a verifier: "SOTA on DeepSWE (81.6%) and Terminal-Bench 2.1 (87.6%)". "Verifier results need fine-tuning … not this checkpoint zero-shot".
  - Ships `train/finetune.py` with downloadable DeepSWE heads (`Contrastive-LM/deepswe-clm-heads-8k`).
  - [CLM card](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B)
- **Training-data caveat:** several recipes train on official train splits of the index's own benchmarks (Perplexity v1.2, decider-31b, AutoTrust v1.1, StartLux "33 of 38 index benchmarks"). Jebadiah's training mix includes `agent_action_safety` (687 records) and `tomngdev/shell-safety-v2` (1,570) — [index.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json); [Jebadiah card](https://huggingface.co/frontier-infra/jebadiah-27b-v2-1).

### Inferences
- A monitoring team could reasonably start from a released Apache-2.0 decision checkpoint (Kev-27B/9B, pplx-decider-v1.2, AutoTrust JEV-27B or Clef) and add a LoRA trained on its own labeled monitoring decisions, e.g. "is this tool call a policy violation / exfiltration / reward hack?".
  - Published data points suggest hundreds to a few thousand labeled records give measurable gains.
  - A refit temperature on held-out local labels is mandatory: every card says calibration is in-distribution only.
  - For a 27B model, the compute budget is single-GPU hours (H100/H200/B300).
- Training lengths are short (2K–32K) almost everywhere. Long-trajectory monitoring would likely need training data with long states, otherwise accuracy past the training length is unvalidated.

### Gaps
- The Cygnet recipe itself (who made it, data, method) could not be located beyond benchlm.ai listings and the paper's mention.
- No recipe documents fine-tuning specifically for safety or agent-monitoring labels, apart from CLM's agentic-verifier heads and Laya's typed-decisions workflow fine-tune.
- TypeSafe's own RLCD remains unpublished.

---

## Q4. Evaluations on safety, moderation, prompt injection, tool calls, or agent trajectories; comparison with established safety classifiers

### Takeaway
Evidence is thin and mostly self-reported. The only independent guardrail benchmark found is **Red Hat's (2 Oct 2026)**. Its tested set: hosted Jev; the open decision-style models Laya and DiffusionGemma; classic guardrails (a DeBERTa prompt-injection classifier and granite-guardian-hap-125m); and LLM judges (Qwen3.6-35B, Shieldstral, Nemotron Content Safety).

On prompt injection, Jev (86.35%, 348 ms) trailed both the Qwen3.6-35B judge (89.31%) and a ~200M DeBERTa classifier (89.01%, 54 ms). On content safety, Jev led (86.20%). The authors concluded decision models "do not reliably outperform" established guardrails.

Self-reported agent-relevant results include:
- Eikos-27B-FP8 on **AgentRewardBench** (1,106 web-agent trajectories): F1 76.1 vs Jev 70.2 and GPT-4o 75.9.
- CLM's fine-tuned verifier heads (DeepSWE 81.6%, Terminal-Bench 2.1 87.6%).
- KnowLine's prompt-injection robustness: 0.0–1.0% answers changed.
- An "agent-trace observability" workflow, where Clef scored 68.5, Clef-flash 69.8 and Jev 71.6.

Established safety classifiers (Llama Guard 4, ShieldGemma 2, gpt-oss-safeguard, Qwen3Guard, Granite Guardian 4.1) are smaller or policy-specialized. **No public Llama Guard 5 exists** on Meta's HF org. No head-to-head between top open decision models and those guards was found.

### Cited Findings
**Independent guardrail benchmark (Red Hat)**
- "Benchmarking AI decision models against traditional guardrails", by Rob Geada, Mac Misiura and Shelton Cyril, 2026-10-02.
- Nine configurations were run through NVIDIA NeMo Guardrails: deberta-v3-base-prompt-injection-v2 (~200M), BART-large-mnli (~400M, zero-shot), Shieldstral-1.0-3B, Nemotron-3.5-Content-Safety (4B), granite-guardian-hap-125m, Qwen3.6-35B judge, **Laya (~421M, Jev-style)**, **DiffusionGemma (~2.6B, Jev-style)** and **Jev-1.13.0**.
- **Prompt injection:** Qwen3.6-35B 89.31% (312.5 ms), DeBERTa 89.01% (54.1 ms), Jev 86.35% (348.1 ms).
- **Content safety:** Jev 86.20%, DiffusionGemma 85.53% (499.3 ms), Qwen 85.47%; fastest was granite-guardian-hap-125m at 33.2 ms.
- Conclusion: "pre-trained predictive models remain extremely competitive"; decision models "do not reliably outperform LLM-as-a-judge, pre-trained predictive models, or open source decision models in speed or accuracy".
- Red Hat plans DeBERTa and granite classifiers as OpenShift AI 3.6 defaults.
- Sources: [Red Hat Developer](https://developers.redhat.com/articles/2026/10/02/benchmarking-ai-decision-models-against-traditional-guardrails); [The New Stack](https://thenewstack.io/red-hat-guardrail-benchmark/)
- Note: none of the top-20 open 27B decision models was in this benchmark; only Laya and DiffusionGemma were.

**Agent-trajectory / agent-monitoring results (self-reported)**
- **Eikos-27B-FP8 on AgentRewardBench** ("judging whether a web agent completed its task. Test split, 1,106 trajectories, official scorer"): P/R/F1 78.9/73.6/76.1, versus Jev (same inputs via API) 75.7/65.4/70.2 and GPT-4o Axtree (best published LLM judge) 69.8/83.1/75.9. Judgments are published as a dataset; leaderboard submission is issue #12 — [Eikos card](https://huggingface.co/caiovicentino1/Eikos-27B-FP8); [dataset](https://huggingface.co/datasets/caiovicentino1/Eikos-27B-FP8-AgentRewardBench).
- **CLM-v0.1-8B:** post-trained on about 1M agentic trajectories. Fine-tuned verifier heads report DeepSWE 81.6% and Terminal-Bench 2.1 87.6%, "4–6× faster than Jev". Zero-shot it ranks near the bottom of DI (#221) — [CLM card](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B); [index.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json).
- **"Typed-decisions" workflows** (invoice processing, customer service, security incidents, agent-trace observability):
  - Clef 68.5, Clef-flash 69.8 and **Jev 71.6** on agent-trace observability (primary action) — [Clef card](https://huggingface.co/Cloudflare/clef).
  - A fine-tuned Laya checkpoint reached 0.730 on agent-trace observability and 0.766 on security incidents — [Laya card](https://huggingface.co/convaiinnovations/laya).
- **KnowLine-35B-A3B Gen1.5 prompt-injection robustness:** "answers changed" 0.0%, and 1.0% "with injection templates not seen in training" (Gen1: 0.0% and 0.8%). The card warns "other prompt-injection attacks may still work" — [KnowLine card](https://huggingface.co/PelaAI/KnowLine-35B-A3B-Gen1.5).
- **Moderation-type evidence:**
  - decider-31b trained on Hateful Memes (0.72 → 0.83) — [decider-31b](https://huggingface.co/Mapika/decider-31b).
  - d3 reports a "Moderation (Hateful Memes)" vision result — [d3](https://huggingface.co/vllm-sr/d3).
  - mammoth-1 includes 16.1% "safety and abstention" training data and is tagged "guardrails" — [mammoth-1](https://huggingface.co/baselabs/mammoth-1).
  - MISA's card lists "Flagging policy or safety violations" as a use and advises "set thresholds per category on your own traffic" — [MISA card](https://huggingface.co/misa-jsc/misa-ai-2.0-decision-plus).
  - Torchcast states "Not intended for safety-critical, security … decisions without human review" — [Torchcast](https://huggingface.co/torchcast-ai/torchcast-decision-27b).
- **Tool-call classification:** on DI's BFCL (yes/no per function), top open models score 0.97–0.98 versus Jev 1.14's 0.964. On When2Call (answer / tool / ask / decline), StartLux 0.938, Jeffan 0.921 and GLiDE 0.916 versus Jev 0.817 — [index.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json).
- **Tooling that uses decision models as monitors and guards:**
  - Openlayer's open-source **jevals** (2026-09-23) has 37 evals including tool selection, groundedness, task completion, scope adherence, "prompt injection" and sensitive-info detection, with "gates" (proceed / block / review). It supports hosted Jev plus local Kev and Laya backends — [Openlayer blog](https://www.openlayer.com/blog/introducing-jevals-agent-evals-guardrails).
  - **LiteLLM Decision Model Guardrail** asks yes/no questions on every request or response, thresholds them (default 0.7), and splits messages over 24,000 characters into overlapping chunks. It works with Jev, Perplexity and self-hosted vLLM — [LiteLLM docs](https://docs.litellm.ai/docs/proxy/guardrails/decision_model.md).

**Established safety classifiers (HF API, 2026-10-22)**
- **Llama Guard 4 12B** (`meta-llama/Llama-Guard-4-12B`, created 2025-04-23, 12.0B, custom license, gated). Llama Prompt Guard 2 (86M/22M, 2025-04-28). **No "Llama Guard 5" on the meta-llama HF org**; the latest Guard listed is 4 — [HF API search](https://huggingface.co/api/models?author=meta-llama&search=Guard). Web search also found nothing for "Llama Guard 5" — **treat any Llama Guard 5 reference as UNVERIFIED**.
- **ShieldGemma 2 4B** (`google/shieldgemma-2-4b-it`, 2025-03-04, 4.3B, Gemma license, gated, image safety). ShieldGemma 2B/9B/27B text versions date from 2024-07 — [HF API](https://huggingface.co/api/models/google/shieldgemma-2-4b-it).
- **gpt-oss-safeguard 20B / 120B** (`openai/gpt-oss-safeguard-20b`/`-120b`, created 2025-09-18, 21.5B / 116.8B, Apache-2.0, policy-following reasoning) — [HF API](https://huggingface.co/api/models/openai/gpt-oss-safeguard-20b).
- **Qwen3Guard-Gen-8B and Qwen3Guard-Stream-8B** (created 2025-09-23, Apache-2.0; the Stream variant does token-level streaming moderation) — [HF API](https://huggingface.co/api/models/Qwen/Qwen3Guard-Stream-8B).
- **IBM Granite Guardian:** granite-guardian-3.3-8b (2025-06, Apache-2.0) and **granite-guardian-4.1-8b** (2026-04-16) — [HF API](https://huggingface.co/api/models?author=ibm-granite&search=guardian).

### Inferences
- **Speed and cost.**
  - Open 27B decision models answer one decision in about 25–300 ms median on one high-end GPU (Torchcast 33 ms per yes/no on an H100; Blink 25 ms; GLiDE 93 ms). That is comparable to or faster than an 8–12B guard generating a short verdict.
  - Their big advantage for monitoring is many typed questions about one shared trajectory prefix in one prefill. The big disadvantage is that 27B weights need 52–63 GB of VRAM, versus about 8–24 GB for Llama Guard 4, Qwen3Guard-8B or Granite Guardian.
  - For prompt-injection screening alone, the Red Hat data suggests a ~200M DeBERTa is as accurate and about 6× faster than hosted Jev.
- **Agent monitoring.** Decision models' strengths fit custom monitoring questions over trajectories better than fixed-taxonomy guards: arbitrary natural-language criteria, multiple questions per state, calibrated probabilities that can be thresholded or escalated, and long context in some models. Llama Guard and ShieldGemma are built around harm taxonomies on single turns. gpt-oss-safeguard is the closest established analogue, since it reads a written policy, but it generates reasoning text, so it is slower and has no native per-label probability.
  - The only quantitative agent-trajectory evidence for open decision models is Eikos on AgentRewardBench (task-completion judging, not misbehavior detection) and CLM's fine-tuned verifiers.
  - A team would need its own eval on monitoring labels: sabotage, reward hacking, exfiltration and similar.
- **White-box.** All of these models are standard HF checkpoints, so residual-stream activations can be read during the same forward pass that produces the decision. That is a direct advantage over hosted Jev. Label-logit models (Jebadiah, Quyet, Eikos, Blink) keep the full LM head. Head-based models (pplx, Clef, Kev, AutoTrust) put the decision in a small separate module on the final hidden state, which is convenient for probing or for swapping in a monitoring head.

### Gaps
- No head-to-head of the top open decision models (GLiDE, pplx-decider, mammoth, Torchcast, Kev, Clef) against Llama Guard 4, Qwen3Guard, gpt-oss-safeguard or Granite Guardian on standard safety sets (e.g. OpenAI moderation, ToxicChat, BeaverTails, WildGuard, XSTest) or prompt-injection sets was found.
- No evaluation was found of any decision model on misbehavior detection in agent trajectories, such as sabotage, reward hacking or covert actions.
- Latency and VRAM comparisons for the guard models were not retrieved from their own cards; figures here are approximate parameter-based estimates.

---

## Q5. Who are Perplexity (Decider), Torchcast, and Fastino (GLiDE)?

### Takeaway
- **Perplexity Decider** is Perplexity's open-weight (Apache-2.0) decision-model line on Qwen3.8-27B. v1 shipped with a hosted Decisions API on 2026-10-01; v1.1 followed on 2026-10-05/06, then v1.2 and a 4B "flash" on 2026-10-15. Perplexity reported 85.71% vs Jev's 84.51% on its own 11-benchmark panel. I found no official Perplexity blog post, only press and aggregator pages.
- **Torchcast AI** is a small, little-documented outfit. Its only HF model is Torchcast Decision 27B (2026-10-03), a merged LoRA on StartLux-Decision-27B, under CC BY-NC.
- **Fastino** (Fastino Labs / Fastino Inc.) makes the GLiNER family of zero-shot encoder classifiers and launched **GLiDE** on 2026-09-30, billed as "The First Thinking Decision Model". It is hosted at $0.30/M input tokens, and the weights now appear on HF under a revenue-capped community license.

### Cited Findings
**Perplexity Decider**
- "Perplexity opened a Decisions API running on pplx-decider-v1-27b on October 1, 2026, an open-weight 27B model … under Apache 2.0 and fine-tuned from Qwen3.8-27B". It takes up to 128 typed questions at $0.04 per million input tokens with free output and has a 262,144-token context. "On Perplexity's own 11-benchmark, 7,210-sample panel, pplx-decider scored 85.71% compared to Jev's 84.51%" — [AI Weekly](https://aiweekly.co/alerts/perplexity-open-sources-27b-decider-edges-jev-on-11-test-panel); [llmreference](https://www.llmreference.com/model-family/pplx-decider). (Aggregator sources: **UNVERIFIED** against an official Perplexity post.)
- HF repos and dates:
  - `perplexity-ai/pplx-decider-v1.1-27b`: created 2026-10-05, 165 likes, about 4.7K downloads.
  - `perplexity-ai/pplx-decider-v1.2` and `perplexity-ai/pplx-decider-flash-v1.2`: created 2026-10-15.
  - [HF API](https://huggingface.co/api/models/perplexity-ai/pplx-decider-v1.2)
- AutoJev-27B is published under the HF user `denis-pplx`. The "pplx" suffix suggests a Perplexity-affiliated author, but this is **UNVERIFIED** — [AutoJev card](https://huggingface.co/denis-pplx/AutoJev-27B).

**Torchcast**
- Torchcast Decision 27B was released 2026-10-03. Its card claimed DI 0.2.1 at 65.00 (+7.09 over Jev 1.13), author-run with the official kit. It is "A LoRA fine-tune of StartLux-Decision-27B, merged into the weights", with Apache-2.0 serving code `torchcast_decision/` and a TypeSafe-compatible API — [Torchcast card](https://huggingface.co/torchcast-ai/torchcast-decision-27b); [benchlm.ai](https://benchlm.ai/models/decision-index-0-3-torchcast-decision-27b).
- The board lists it as org "Torchcast AI", kind LoRA, with "Index results guided checkpoint selection (author-declared)". It is now rank 35 (61.49) — [index.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json).
- It is also hosted by Featherless AI — [featherless.ai](https://featherless.ai/models/torchcast-ai/torchcast-decision-27b).
- No company website, blog or funding information was found.

**Fastino GLiDE**
- "Fastino released GLiDE on September 30, 2026 … Fastino Labs' thinking decision model … answers fast when confident and reasons further when unsure". It scored 64.81 on DI 0.2.1 vs Jev's 57.91, has a 40k context, and costs $0.30 per million input tokens with free output — [gradually.ai](https://www.gradually.ai/en/ai-models/glide/); [Product Hunt "GLiDE – The First Thinking Decision Model"](https://www.producthunt.com/p/glide-11/glide-6).
- Fastino's hosted endpoint is `POST https://api.fastino.ai/v1/systemone` with model `fastino/GLiDE`, documented at docs.fastino.ai/inference/systemone — [GLiDE card](https://huggingface.co/fastino/GLiDE).
- Fastino also maintains GLiNER 2.5 (zero-shot encoder classifiers) and claimed it as "prior art" for single-pass classification over caller-supplied labels — [news tab](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/news.html); [GLiNER 2.5 collection](https://huggingface.co/collections/fastino/gliner25-models).
- A `fastino/GLiNER2.5-Decide` entry also appears on the board's model list — [Space README](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/README.md).
- GLiDE v1.2 has been #1 on DI 0.4.1 since its 2026-10-21 PR batch, replacing the earlier entry "decision-27b-ckpt-nothink" — [index.json](https://huggingface.co/spaces/multimodalart/jev-decision-index/blob/main/data/index.json).
- License: Fastino Community License (see Q2) — [LICENSE](https://huggingface.co/fastino/GLiDE/blob/main/LICENSE).

### Inferences
- Perplexity is the most institutionally backed fully open (Apache-2.0) entrant near the top. Its readout-head design and documented 262K path (trained to 32K) make it a plausible white-box monitor base, subject to long-context validation.
- Torchcast's paper-leading error AUROC (0.860) comes from a non-commercial derivative of StartLux. For a research team, NC licensing is likely fine; for productization it is not.
- GLiDE's "thinking" positioning means some hosted queries may trigger extra reasoning passes. The local HF card describes one forward pass per question with a 255-way readout, so it is unclear whether the open weights include the thinking mode (**UNVERIFIED**).

### Gaps
- No official Perplexity blog post or research write-up on the decider was found; its training data composition beyond "tasksource" and DI train splits is undisclosed.
- No information was found on Torchcast AI's team, location or other products.
- Fastino's funding, team, and whether the GLiDE HF weights are intentionally public, given the "Internal use only" README text, could not be confirmed.
