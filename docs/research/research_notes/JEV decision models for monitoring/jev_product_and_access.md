# TypeSafe JEV ("Jev"): product, access, capabilities and limits (as of 2026-10-22)

All URLs below were accessed 2026-10-22 unless noted. Primary sources are TypeSafe's own docs (docs.typesafe.ai, fetched as raw `.md` via the docs' `llms.txt` index), typesafe.ai blog/legal pages, the public OpenAPI spec (`https://api.typesafe.ai/openapi.json`, version 0.2.0), and the unauthenticated model-listing endpoints of OpenRouter and Vercel AI Gateway. Secondary/aggregator sources (press, explainer sites, LessWrong, GitHub evals) are labeled as such.

**Corrections to the starting context:**
- **JEV is on OpenRouter as a decision model**, not just as "jev-router". `typesafe/jev-1.13`, `typesafe/jev-1.14` and `~typesafe/jev-latest` exist with output modality `"decisions"`. They are missing from the default `GET /api/v1/models` listing (441 models) and show up only with `?output_modalities=all` (692 models).
- **The paper's "Access Program" was OpenAI's, not TypeSafe's.** The acknowledgment in arXiv 2609.26550 reads "OpenAI's Researcher Access Program, which provided API credits". I found no TypeSafe academic or research-credit program.
- **The "native confidence" formula is now published.** The paper (sources accessed 2026-09-20) said it was unpublished. TypeSafe's Confidence page now gives exact formulas.
- **The context limit is now 64k per request / 32k per question** (the paper said 32k), with an opt-in 262k long-context mode. There is a newer version, jev-1.14.0 (2026-10-14).

---

## 1. How to get access: signup, SDKs, auth, rate limits, data terms, marketplaces, OpenRouter

### Takeaway
JEV is a proprietary hosted API with no weights and no on-prem option. There are three ways to reach it:
1. TypeSafe directly: `POST https://api.typesafe.ai/v1/systemone`, with a Bearer key from console.typesafe.ai.
2. Vercel AI Gateway: `typesafe-ai/jev*`.
3. OpenRouter: `typesafe/jev-1.13`, `typesafe/jev-1.14`, `~typesafe/jev-latest`, through a separate non-chat "Decisions API".

All three paths return full label probabilities and confidence. Signup is self-serve. The $5 free credit was suspended in late September and no research-credit program was found. The legal terms say TypeSafe does not train on inputs, but they keep a perpetual license to use customer data for abuse monitoring and "Telemetry". Zero data retention (ZDR) is enterprise-only on the direct API, though Vercel and OpenRouter report no-retention policies for their routes. The AUP bans uploading "malicious code", which matters if we send attack trajectories.

### Cited Findings
**Direct API, auth and SDKs**
- The single endpoint is `POST /v1/systemone` at `https://api.typesafe.ai`. `GET /v1/models` lists aliases. Auth is HTTP Bearer (`Authorization: Bearer <API_KEY>`) — [OpenAPI spec](https://api.typesafe.ai/openapi.json); [Models doc](https://docs.typesafe.ai/models.md)
- API keys come from the console at https://console.typesafe.ai/keys. There is also a browser Playground (login required) at https://console.typesafe.ai/playground — [Quick start](https://docs.typesafe.ai/introduction/quickstart.md)
- Python SDK: `pip install typesafe-sdk` / `uv add typesafe-sdk`, imported as `typesafe_sdk`, Python 3.10 or later. Source is at github.com/typesafe-ai/typesafe-sdk-python. Extras: `http2`, `zstd`, `pil` — [Python SDK](https://docs.typesafe.ai/sdk/python.md)
- Python SDK environment variables are `TYPESAFE_API_KEY` and `TYPESAFE_BASE_URL`. The latter allows routing through gateways — [Constants](https://docs.typesafe.ai/sdk/python/api/constants.md)
- JS/TS SDK: `@typesafe-ai/sdk`, v0.7.0 (2026-10-14), requires Node 22 or later — [JS changelog](https://docs.typesafe.ai/sdk/javascript/changelog.md)
- There is also an agent skill: `npx skills add typesafe-ai/skills --skill typesafe-ai` — [Quick start](https://docs.typesafe.ai/introduction/quickstart.md)
- Python SDK history:
  - v0.5.7 (2026-09-14) was the initial public release.
  - v0.7.0 (2026-09-18) switched to pydantic and added a `response_model` argument.
  - v0.7.5 (2026-10-14) added images and the `Box` type, and turned on zstd compression by default.
  - Source: [Python changelog](https://docs.typesafe.ai/sdk/python/changelog.md)

**Signup and credits**
- At launch on 2026-09-15 access was "early access", with "developers [brought] off the waitlist as quickly as we can" — [TypeSafe launch blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
- Sign-up status per a secondary report:
  - Signups were paused for demand, then reopened on 2026-09-27.
  - The $5 free credit for new users (described as 120M tokens) was suspended because "a few bad actors were making it a bad time for everyone". The report attributes this quote to Diogo Almeida on X.
  - Source: [aifront-page (secondary)](https://aifront-page.com/typesafe-ai-reopens-jev-sign-ups-free-credit-suspended/). I did not verify the X post itself.
- Search snippets from explainer sites say signup at console.typesafe.ai has "no application or approval step". This is unverified because the console requires login — [layer3labs guide (secondary)](https://www.layer3labs.io/guides/is-jev-free)
- The Master Customer Agreement provides for "Promotional Credits" that TypeSafe "may, but has no obligation to" issue. Purchased credits expire after 12 months — [MCA, updated 2026-09-23](https://typesafe.ai/legal/mca)

**Rate limits and request limits**
- Rate limits are set per organization in tokens per second and requests per second, and are shown in the console at https://console.typesafe.ai/rate-limits.
- Going over a limit returns `429`. The SDKs retry with backoff and honor `retry-after`.
- Higher limits are available on custom or enterprise plans via sales@typesafe.ai.
- No public numeric defaults were found.
- Source: [Models doc](https://docs.typesafe.ai/models.md)
- Request rules:
  - Body at most 32 MiB (gzip/zstd allowed; the limit applies before and after decompression).
  - At most 64 nesting levels in each of state, instructions and criteria.
  - Finite numbers only.
  - Status codes: 400, 401, 413, 415, 422, 429, and `529 Overloaded`.
  - Source: [Request rules and errors](https://docs.typesafe.ai/api/errors.md)
- There is no batch or asynchronous-job endpoint. The OpenAPI spec has only `/v1/models` and `/v1/systemone`. TypeSafe's approach to batching is packing many questions into one request ("Speculative fan-out"; the "Parallel questions" cookbook claims 12.2x cheaper and 10.0x faster) — [OpenAPI](https://api.typesafe.ai/openapi.json); [llms.txt index](https://docs.typesafe.ai/llms.txt)

**Data retention, privacy and acceptable use (relevant to sending attack trajectories)**
- "Jev is not trained on customer requests or responses." ZDR is offered for enterprise customers — [Models doc](https://docs.typesafe.ai/models.md); [Legal](https://docs.typesafe.ai/legal.md); [Enterprise page](https://typesafe.ai/enterprise) (which also says SOC 2 Type II is available via the Trust Center)
- Privacy Policy (updated 2025-11-19):
  - "We will not train or fine tune any artificial intelligence or machine learning models on your prompts or other Input."
  - Retention is "as long as reasonably necessary to provide you with the Services, or otherwise in support of our business or commercial purposes."
  - No fixed day count is given.
  - Source: [Privacy Policy](https://typesafe.ai/legal/privacy-policy)
- MCA (updated 2026-09-23):
  - TypeSafe is licensed to use Customer Data "in perpetuity … (i) to derive and generate Telemetry, (ii) to monitor for fraud and abuse … (iii) as necessary to comply with applicable Laws".
  - It "will not … include Customer Data in a dataset used to train (i.e., to modify the model weights of)" any model.
  - It prohibits using outputs for "model distillation, train a model to imitate the output", building "a similar or competing product", and "conduct[ing] any security or vulnerability test".
  - Source: [MCA](https://typesafe.ai/legal/mca)
- The DPA (updated 2026-04-24) says data is retained "for as long as necessary taking into account the purpose of the Processing." Subprocessors are listed at trust.typesafe.ai/subprocessors — [DPA](https://typesafe.ai/legal/data-processing)
- Acceptable Use Policy (updated 2026-09-23):
  - 1.5 forbids uploading Input "that contains viruses, malware, malicious code, or similar harmful materials".
  - 3.4 forbids "intentionally driv[ing] TypeSafe's AI model to act in a manner that contravenes TypeSafe's policies".
  - 3.7 forbids probing or testing "the vulnerability of TypeSafe's system or network".
  - TypeSafe "may monitor compliance".
  - Source: [AUP](https://typesafe.ai/legal/acceptable-use-policy)
- The Jev 1.14 blog adds an opt-in "to help find model jaggedness with your queries. We will still not train on your queries" — [Jev 1.14 blog, 2026-10-14](https://typesafe.ai/blog/jev-1-14)

**Vercel AI Gateway**
- Public listing at https://ai-gateway.vercel.sh/v1/models:
  - Models: `typesafe-ai/jev`, `typesafe-ai/jev-1.13.0`, `typesafe-ai/jev-1.14.0`.
  - All are `type: "evaluation"`, priced at $0.042/M input and $0 output.
  - `context_window` is 32000. The `typesafe-ai/jev` description says "64,000 tokens total per request; 32,000 tokens for the state plus the longest question."
  - The versioned IDs show `zdr: "all"` and `no_training: "all"`; the unversioned alias shows `zdr: "some"`.
  - Source: [Vercel AI Gateway models endpoint](https://ai-gateway.vercel.sh/v1/models)
- Vercel changelog (2026-09-21):
  - HTTP API at `https://ai-gateway.vercel.sh/v1/evaluate`; TypeSafe-client base URL `https://ai-gateway.vercel.sh/typesafe`; auth with `AI_GATEWAY_API_KEY`.
  - Probabilities are returned.
  - Billing goes through the gateway.
  - Source: [Vercel changelog](https://vercel.com/changelog/ai-gateway-now-supports-typesafe-clients-and-an-http-api-for-jev)
- Vercel's listing also includes a competitor, **`liquid/d1`** (Liquid AI): $0.02/M input, a 65,536-token window, and a "TypeSafe-compatible System One API" — [Vercel AI Gateway models endpoint](https://ai-gateway.vercel.sh/v1/models)

**OpenRouter**
- `typesafe/jev-1.13`, created 2026-09-17:
  - Endpoint name "TypeSafe | typesafe/jev-1.13-20260917".
  - Modality `text+image->decisions`, prompt $0.000000042/token, completion $0, `context_length` 262144, `supported_parameters: []`, single provider TypeSafe.
  - Source: [OpenRouter endpoints API](https://openrouter.ai/api/v1/models/typesafe/jev-1.13/endpoints)
- `typesafe/jev-1.14` is the same apart from the endpoint name "typesafe/jev-1.14-20261014" — [OpenRouter endpoints API](https://openrouter.ai/api/v1/models/typesafe/jev-1.14/endpoints)
- `~typesafe/jev-latest`:
  - Described as "This model always redirects to the latest model in the Jev family."
  - Created 2026-09-18; `isRouter: true`.
  - Its current endpoint is "TypeSafe | typesafe/jev-1.14-20261014". So **OpenRouter's jev-latest already points to 1.14**, while TypeSafe's own `jev-latest` alias still points to 1.13.
  - Data policy: training false, retainsPrompts false.
  - `limit_rpm` 3000; `has_chat_completions: true`.
  - Source: [OpenRouter ~typesafe/jev-latest page](https://openrouter.ai/~typesafe/jev-latest)
- These models are called through OpenRouter's Decisions API (`POST https://openrouter.ai/api/alpha/decisions`), or reportedly `/api/v1/systemone`, with the same `state`/`questions` shape. Responses carry per-option probabilities and confidence, and `chat/completions` rejects decision models — [OpenRouter Jev guide](https://openrouter.ai/docs/guides/community/jev); [dev.to (secondary)](https://dev.to/weirui_chen_48669a172a6be/typesafejev-fails-on-openrouter-chatcompletions-how-to-call-it-and-the-three-response-shapes-4e0f)
- According to WebFetch's summary of the OpenRouter guide, text requests over about 32,000 bytes, and all image requests, run in "long-context mode, which TypeSafe says is slower and less accurate." I did not read the raw guide text — [OpenRouter Jev guide](https://openrouter.ai/docs/guides/community/jev)
- `typesafe/jev-router`:
  - Description: "picks the best model and reasoning effort for each request … runs on Jev".
  - It is a chat router: output `text`, pricing -1, a 1M context, and LLM sampling parameters including `logprobs`.
  - `endpoints: []`, i.e. no live endpoints.
  - Created 2026-09-25.
  - Source: [OpenRouter jev-router endpoints API](https://openrouter.ai/api/v1/models/typesafe/jev-router/endpoints)

**Other platforms**
- Not on Amazon Bedrock. A secondary AWS guide describes it as "not an Amazon Bedrock model … no inference profile, no VPC endpoint" and suggests calling TypeSafe from Lambda as a sidecar — [factualminds (secondary)](https://www.factualminds.com/blog/jev-typesafe-ai-aws-guide-2026/)
- Integrations reported by press:
  - InfoQ lists Netlify, LangChain (a `TypeSafeClassifier`), and Elixir clients — [InfoQ, 2026-10-01](https://www.infoq.com/news/2026/10/typesafe-ai-jev-released/)
  - StartupFortune lists Cloudflare, LangChain and Langfuse "within three days" — [StartupFortune, 2026-10-17](https://startupfortune.com/typesafes-jev-becomes-vercel-ai-gateways-fastest-adopted-model-ever/)

### Inferences
- For a research team the simplest paths are OpenRouter's Decisions API or Vercel. Both return label probabilities, both report no prompt retention or training, and both avoid TypeSafe's direct terms, where ZDR is enterprise-only and abuse-monitoring use of data is perpetual.
- On OpenRouter, long trajectories over about 32 KB appear to switch silently into the less accurate long-context mode. If that is confirmed, the direct API, which keeps 64k/32k limits by default, gives a cleaner per-question budget.
- AUP §1.5 ("malicious code") could literally cover attack trajectories that contain exploit code or backdoors. Clearing this with TypeSafe, or using a gateway with ZDR, is prudent before bulk submission.
- Thresholds should be pinned to a versioned ID (`jev-1.13.0`), not an alias. The aliases move, and they already disagree between TypeSafe (1.13) and OpenRouter (1.14).

### Gaps
- Default rate-limit numbers for a new organization are not public; they are in the login-gated console.
- The current free-credit status after 2026-09-28 is unknown.
- No TypeSafe academic or research-credit program was found. The paper's "Access Program" is OpenAI's.
- The exact retention period for API inputs and logs on the direct API is not stated. The DPA and Privacy Policy give no day count.
- Availability on Azure, HF Inference, Together and Groq was not found; I found nothing suggesting it exists.
- Cloudflare Workers AI availability rests only on a search snippet from a French article. Not verified.
- Whether OpenRouter's `/api/v1/systemone` path or the Vercel route passes through the `TypeSafe-Danger-Zone-*` headers is unverified.

---

## 2. Versions, interface, limits, rubric customization, calibration options

### Takeaway
Current versions are `jev-1.13.0` (alias `jev-latest`) and `jev-1.14.0` (alias `jev-preview`, released 2026-10-14).

- **Price:** both cost $0.042/M input tokens with free output.
- **Context:** 64k tokens per request and 32k per question (state plus one question). Opt-in long context goes to 262k.
- **Question types:**
  - Choice: 1–255 named options, each with a free-text description.
  - Score: 1–10 ordered levels.
  - Noul: yes/no probability, with optional true/false criteria.
  - Box: experimental image localization, 1.14 only.
- **Rubrics:** fully custom labels, descriptions and instructions are supported, including JSON-structured ones.
- **Not available:** temperature, seed, calibration knobs, logprobs, batch API, and customer fine-tuning.
- **Confidence:** a deterministic function of the returned probabilities, now documented.

### Cited Findings
**Versions and limits**
- Models table:
  - `jev-1.14.0` and `jev-1.13.0`, both "$42 / $0.042" per Btok/Mtok.
  - Both have "64k per-request / 32k per-question" context and "Input: Text".
  - "Jev 1.14 is the newest Jev release, available from October 14, 2026."
  - Source: [Models](https://docs.typesafe.ai/models.md)
- Aliases: `jev-latest` points to `jev-1.13.0` ("most recent stable, official release"; the SDK default). `jev-preview` points to `jev-1.14.0`. "If you have tuned confidence thresholds against one version, send that version's ID instead of the alias" — [Models](https://docs.typesafe.ai/models.md)
- Context limits:
  - Per-request context counts the state plus all questions; per-question context counts the state plus any one question.
  - There is no limit on the number of questions.
  - The `TypeSafe-Danger-Zone-Long-Context: true` header raises both limits to 262k. Long context is "slower and less accurate".
  - Source: [Models](https://docs.typesafe.ai/models.md)
- Jev 1.14 release notes:
  - Images can be used in state, instructions or criteria via the `TypeSafe-Danger-Zone-Images: true` header. "jev-1.13.0 was multimodal all along."
  - Box questions are 1.14 only.
  - Long context is offered as a "danger zone" flag.
  - "jev-latest will be updated to [1.14] in a week."
  - Deprecation notice is intended to be "60 days warning … and 30 days" (the version names were lost in the HTML extraction).
  - 1.14 is "small, subtle improvements to everything … largest gain in multi-lingual support".
  - Source: [Jev 1.14 blog](https://typesafe.ai/blog/jev-1-14)
- Input modality is inconsistent across docs. The Models table says "Input: Text", while the Images page says "Jev 1.13 and Jev 1.14 both accept images" (experimental, behind the header). Image tokens are billed at the text input rate — [Models](https://docs.typesafe.ai/models.md); [Images](https://docs.typesafe.ai/images.md)
- Language: "English is the primary training language … Other languages, including CJK scripts, are handled but not equally well" — [Models](https://docs.typesafe.ai/models.md)
- No customization of weights: "Jev is not fine-tuned or LoRA-adapted with customer data … the same weights serve every account." Domain shaping happens through `state`, `instructions` and `criteria` — [Models](https://docs.typesafe.ai/models.md)

**Request and response schema (OpenAPI 0.2.0)**
- Request fields: `model`, `state` (string, object or array), `questions` (named; at least 1), and optional `assets` — [OpenAPI](https://api.typesafe.ai/openapi.json)
- ChoiceQuestion: `instructions` (string, object, array or null) and `criteria`, an object with 1–255 entries. "A choice without a description is interpreted by its name alone." The launch blog adds that a "cardinality up to 255" is supported — [OpenAPI](https://api.typesafe.ai/openapi.json); [Launch blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
- ScoreQuestion: `criteria` is an ordered array of 1–10 level descriptions — [OpenAPI](https://api.typesafe.ai/openapi.json)
- NoulQuestion: `instructions`, plus optional `criteria` with `true` and `false` descriptions — [OpenAPI](https://api.typesafe.ai/openapi.json)
- Answer types — [OpenAPI](https://api.typesafe.ai/openapi.json):
  - ChoiceAnswer: `choice`, `confidence`, and `probabilities` that "sum to approximately 1".
  - ScoreAnswer: `score` (the expected value across levels), `confidence`, `legend`, `probabilities`.
  - NoulAnswer: `noul` (P(yes)), with no confidence field.
  - BoxAnswer: box coordinates and a nullable confidence.
- The response includes `model` (the versioned ID that actually answered) and `usage.input_tokens` / `usage.output_tokens`. Output is "currently free of charge" — [OpenAPI](https://api.typesafe.ai/openapi.json)
- The only request headers in the spec are `TypeSafe-Danger-Zone-Images` and `TypeSafe-Danger-Zone-Long-Context`. There is no temperature, seed, or calibration parameter — [OpenAPI](https://api.typesafe.ai/openapi.json)
- Instructions, Choice options, Score levels and Noul criteria "all accept JSON structure" — [Advanced: structure](https://docs.typesafe.ai/primitives/advanced.md)

**Confidence (now published)**
- Formulas — [Confidence](https://docs.typesafe.ai/confidence.md):
  - Choice: confidence = (p_max − 1/n)/(1 − 1/n).
  - Score: max(0, 1 − Σ p_i|i−m| / MAD_unif), where m is the most likely level and MAD_unif is the mean absolute deviation of a uniform distribution over the n levels.
  - Noul: no confidence is returned; the doc suggests |2p−1| and starting thresholds of 0.7/0.3.
  - The doc also recommends trying top probability and the top-to-second ratio.
- This contradicts the paper's statement, made from docs accessed 2026-09-20, that the formula "is not published" — [paper full text, local](file:///Users/gkocher/Desktop/monitoring-research/research_notes/JEV%20decision%20models%20for%20monitoring/_source_jev_as_judge_paper_fulltext.txt). The page has evidently been updated since; no change date was shown.

**Calibration claims**
- TypeSafe trains with "RLCD (reinforcement learning for calibrated decisions)", stating that "Outcomes assigned a probability of 0.2 should occur about 20% of the time." This is a design goal, not a published reliability study — [AI primer](https://docs.typesafe.ai/introduction/machine-learning-primer.md)

### Inferences
- A monitor can define a custom label set ({benign, suspicious, malicious} with descriptions), an ordered suspicion rubric of up to 10 levels, or many Noul checks in one request. All checks see the same trajectory state and the state is billed once.
- Because there is no sampling-temperature control, ensembling must come from paraphrased questions, reordered options, or reordered state, not resampling. Both the paper and the docs note option-order effects.
- With 32k tokens per question, a typical long agent trajectory must be chunked or filtered. The jaggedness page also says irrelevant context lowers accuracy.

### Gaps
- No public changelog of model behavior between 1.13 and 1.14 beyond the blog's qualitative notes.
- The model's tokenizer is not public.
- No documented determinism or seed guarantee. Third-party data: 77/100 prompts scored identically across three runs (Ruchith1018 eval, below), and the paper saw 0 decision changes in 96 repeats.
- The architecture and parameter count are unpublished; the launch blog says only "new model architecture, parallel sampler".

---

## 3. Where JEV is weak (jaggedness page) and TypeSafe's own benchmarks

### Takeaway
TypeSafe's jaggedness page (jev-1.13, last reviewed 2026-10-02) lists nine failure modes. Two bear directly on agent monitoring:
- **Adversarial content in state can move the answer.** The page says "does not treat it as hostile by default".
- **Accuracy drops with large, irrelevant state.**

Other weaknesses are literal reading, arithmetic and counting, date comparison, multi-hop indirection, contradictory criteria, choice-order bias, and generation. TypeSafe publishes no standard public benchmarks. It "dislike[s] public benchmarks" and reports self-built "workflow evals" against GPT-6 Astra and Fable 5.1 as references.

### Cited Findings
- The page describes jev-1.13 as "fast, calibrated, and good at common-sense judgment … may struggle with tasks that require additional levels of indirection … quite literal … struggles with tasks that require numeric precision" — [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)
- The nine failure modes — [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md):
  1. Literal reading
  2. Math and numbers: no reliable counting; poor on hex/RGB values and on "low level assembly, or binary encoded instructions"; Score levels "weak in numerical calibration"
  3. Date and time comparison
  4. Indirection (double negatives, multi-hop)
  5. Large state full of irrelevant detail: "Jev suffers from context rot"
  6. Adversarial content
  7. Contradictory instructions and criteria (e.g. an inverted Noul)
  8. Choice option order: "leans toward the option that comes first"
  9. Generation
- Exact wording on adversarial content: "State is data, and jev-1.13 does not treat it as hostile by default. Content written to adversarially steer the model, whether that is an injected instruction, a deliberately misleading framing, or text that argues for its own classification, can move the answer. We expect to improve on this in the future." — [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)
- Launch-blog claims — [Launch blog, 2026-09-15](https://typesafe.ai/blog/introducing-system-one-models-and-jev):
  - 70–500 ms end to end, "40x-200x faster".
  - "193.6x faster, 444.6x cheaper" on TypeSafe's workflow evals (evals.typesafe.ai), using the average of GPT-6 Astra and Fable 5.1 as reference probabilities.
  - The blog concedes the evals were built by its own capabilities team ("some bias could exist").
  - "0%" hallucination is "not empirical. Schema matching is guaranteed."
  - Use cases listed include "Score, judge, verify, guardrail, and detect jailbreaks of LLM prompts, reasoning traces, and/or outputs."
- The Jev 1.14 blog shows an internal intelligence chart that compares only against open-weight models ("we guard our validation set very closely"), with caveats: "Don't believe it entirely" and "likely biased towards our models". I could not extract the numbers from the HTML — [Jev 1.14 blog](https://typesafe.ai/blog/jev-1-14)
- A TypeSafe "antibenchmaxxing" post ("Lies, Damned Lies, and Benchmarks") argues against public benchmarks. It exists but I did not read it in full — [TypeSafe blog index](https://typesafe.ai/blog)
- Guardrails cookbook:
  - Uses four Noul hazard questions (instruction override, harm or crime, medical dosage, self-harm) plus one Score for severity in a single request.
  - Claims "'Ignore your instructions' scores as a jailbreak instead of working as one".
  - Its numbers are from `jev-1.12` on 2026-08-15, which reveals a pre-launch version 1.12.
  - Source: [Guardrails cookbook](https://docs.typesafe.ai/cookbooks/llm_guardrails.md)
- Customer case study (Jack & Jill, 2026-10-07): Jev replaced Gemini 3.1 Flash Lite for candidate screening, with cost per 1k candidates falling from $0.755 to $0.092 (88% lower) and a "quality" metric moving from 93.9% to 94.6%. This is vendor-published — [TypeSafe case study](https://typesafe.ai/blog/jack-jill-jev-case-study)

### Inferences
- For monitoring attack trajectories, failure modes 5 (long noisy state) and 6 (adversarial content written by the attacking agent) are the central risks. The vendor openly concedes both.
- Failure mode 2's note that low-level and binary code is weak suggests that obfuscated payloads or encoded exfiltration may be under-detected. Third-party obfuscation results below support this.

### Gaps
- There is no jaggedness page for jev-1.14 (the docs index lists only 1.13).
- TypeSafe has published no numbers on safety, moderation, or agent-trajectory benchmarks.
- The workflow-eval numbers on evals.typesafe.ai were not fetched.

---

## 4. TypeSafe AI as a company

### Takeaway
TypeSafe is a San Francisco startup founded in 2024 by Diogo Almeida (ex-OpenAI; RLHF/InstructGPT), Erik Gafni and Sasha Sheng (ex-Meta). It spent about two years in stealth before launching Jev on 2026-09-15 with a reported $40M DCVC-led seed. On 2026-10-09 it announced an $870M round at a $7.5B valuation led by a16z, with Sequoia, DCVC and angels participating. Its positioning is "Machine Native Intelligence" / "Building prod, not God". It names guardrails, judging and verification among its use cases.

### Cited Findings
- Launch post: by "Diogo Almeida, founder", dated 2026-09-15. "After two years in stealth … new model architecture, parallel sampler … RLCD". Almeida says he "helped build the methods that made language models useful at following instructions … the research behind ChatGPT" — [Launch blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
- The docs say RLHF "was co-invented by Diogo Almeida, cofounder of TypeSafe" — [AI primer](https://docs.typesafe.ai/introduction/machine-learning-primer.md)
- The co-founders are Almeida, Erik Gafni and Sasha Sheng — [InfoQ, 2026-10-01](https://www.infoq.com/news/2026/10/typesafe-ai-jev-released/); [Wikipedia (secondary)](https://en.wikipedia.org/wiki/Jev_(AI_model))
- Funding — [TypeSafe blog "TypeSafe A raises Series AI", 2026-10-09](https://typesafe.ai/blog/series-ai):
  - "a really big series A … led by Andreessen Horowitz, with participation from Sequoia Capital, existing investor DCVC"
  - "$870 million at a $7.5B valuation, with Martin Casado joining the board"
  - "A third of the Fortune 500 are getting their Jev on", a vendor claim
- The seed was $40M led by DCVC, reported as announced 2026-09-15 at a $200M valuation. This comes from search-result titles for Forbes and Wikipedia; I did not fetch the Forbes article — [Wikipedia](https://en.wikipedia.org/wiki/Jev_(AI_model)); [Forbes (title only)](https://www.forbes.com/sites/the-prompt/2026/09/15/this-200-million-startup-wants-to-fix-ais-overconfidence-problem/)
- Some aggregators call the $870M round a "Series B". TypeSafe's own post says Series A — [search-result aggregators](https://www.kucoin.com/news/flash/typesafe-ai-completes-870m-funding-at-7-5b-valuation-with-a16z-lead) vs [TypeSafe blog](https://typesafe.ai/blog/series-ai)
- Its address is 255 California St, Suite 1300, San Francisco. Social channels are X @typesafeai, LinkedIn, and Discord (linked from the docs) — [Terms](https://typesafe.ai/legal/terms); [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)
- Adoption reports: Vercel said Jev reached "nearly 13% of paid teams within 24 hours" on AI Gateway — [InfoQ](https://www.infoq.com/news/2026/10/typesafe-ai-jev-released/); [StartupFortune (secondary)](https://startupfortune.com/typesafes-jev-becomes-vercel-ai-gateways-fastest-adopted-model-ever/)
- The name refers to Kahneman's System 1 and to Jevons (the Jevons paradox) — [Launch blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev)

### Inferences
- The company is heavily funded and its models version quickly (1.12 in August, 1.13 in September, 1.14 in October). Expect alias drift and pricing changes, and pin versions in any research protocol.

### Gaps
- Team size: an aggregator says "just over 20"; unverified.
- No published safety, alignment or monitoring research program at TypeSafe was found.

---

## 5. Public discussion and practitioner reports (classifier, guardrail, monitor)

### Takeaway
Independent reports agree that JEV **ranks well but is not well calibrated in absolute terms**, is very cheap and fast, and is **vulnerable to adversarial and obfuscated input**.

- **Directly relevant prior work:** a LessWrong post (2026-09-18) tested jev-1.13.0 as a trusted monitor on ControlArena APPS backdoors.
  - AUROC 0.976 / 0.970, ~$0.04 per 1k submissions, 0.34 s median latency.
  - Strongly *underconfident* above p≈0.3.
  - Robust to injected reassurance comments, which raised suspicion on honest code instead.
  - Degraded by best-of-N selection: catch rate fell from 89.5% to 68% at N=5.
- **Red-team report:** HiddenLayer (via InfoWorld, 2026-10-15) found prompt-injection, TokenBreak and perturbation attacks that work against Jev.

### Cited Findings
**LessWrong: "A non-generative model as a trusted monitor for AI Control: Testing TypeSafe's Jev"** (author "Venkat T", 2026-09-18) — [LessWrong](https://www.lesswrong.com/posts/d7pQicW8EhpPBDRqz/a-non-generative-model-as-a-trusted-monitor-for-ai-control)
- Setup: jev-1.13.0, a single Noul question, ControlArena APPS backdoors (600 backdoors vs 600 LLM-written and 600 human-written honest solutions), state of about 1,050 tokens.
- Detection: AUROC 0.976 (LLM-written honest) and 0.970 (human-written honest); TPR@1%FPR 87.8% / 85.3%.
- Consistency: mean score standard deviation 0.008 over 5 repeats.
- Calibration: "severe underconfidence above probability 0.3". A score of 0.8 typically corresponded to more than 99% backdoor.
- Comment injection: backdoor evasion of 0–3.7%. An "instruction to monitor" comment raised honest-code false positives from 1.3% to 29.0%.
- Best-of-N: catch rate fell from 89.5% (N=1) to 68% (N=5).
- Backdoor type: structural backdoors were caught 97.3% of the time at 2% FPR; semantic edits only 71.9%.
- There was no measured LLM baseline; comparisons are to o3-mini numbers published elsewhere.
- Caveat: all of the above is from WebFetch's summary of the post.

**GitHub: Ruchith1018/jev-guardrail-evaluation** (jev 1.13 build 20260917, run 2026-10-05) — [GitHub](https://github.com/Ruchith1018/jev-guardrail-evaluation)
- Prompt-injection detection: 6,991 calls.
- deepset AUC: Jev 0.986, ProtectAI deberta 0.882, DeepSeek Flash 0.910.
- "scores behave as a ranking, not a calibrated probability". The 0–0.2 score band still held 15% attacks.
- Thresholds: at 0.5, Jev caught 58.6% of attacks with 0 false positives. A threshold of 0.12 tuned on deepset caught 81.7%, but transferred badly, blocking 74.7% of clean documents.
- Obfuscation (ROT13, reversal, encodings): 32–39% caught.
- Latency: 122 ms median, 223 ms p95. Total cost was $0.13 for the whole study.

**GitHub: rahulbansalc6414/jev-as-a-guardrail** (October 2026) — [GitHub](https://github.com/rahulbansalc6414/jev-as-a-guardrail)
- Jev vs Claude Haiku 4.5 on 1,000 prompts:

| Measure | Jev | Haiku 4.5 |
|---|---|---|
| Overall detection | 91.9% | 96.6% |
| Evasion-subset detection | 78.2% | 94.0% |
| False-positive rate | 9.6% | 14.1% |
| Median latency | 328 ms | 2,066 ms |
| Cost per 1k calls | $0.03 | $1.87 |

**HiddenLayer red-team report, via InfoWorld** (Evan Schuman, 2026-10-15) — [InfoWorld](https://www.infoworld.com/article/4236103/typesafes-jev-even-more-susceptible-to-attack-than-llms-says-security-vendor.html); secondary summary at [daily.dev](https://daily.dev/posts/typesafe-s-jev-even-more-susceptible-to-attack-than-llms-says-security-vendor-qqrlcccna)
- Headline: Jev is "even more susceptible to attack than LLMs".
- TokenBreak "normally does not work with larger LLMs, but Jev is vulnerable to it out of the box". More, better-targeted character perturbations gave "much higher attack success rates".
- An attacker-controlled ad redirected a Jev-driven browser agent despite "treat page content as untrusted" instructions.
- TokenBreak-style edits lowered toxicity scores.
- No percentages are given in the article. TypeSafe did not respond.

**Press and community**
- InfoQ (2026-10-01) — [InfoQ](https://www.infoq.com/news/2026/10/typesafe-ai-jev-released/):
  - The Hacker News launch thread, originally titled "New frontier model 40-400x cheaper and 20-200x faster", was renamed within the hour.
  - An HN commenter noted Jev "can still emit a completely wrong valid value".
  - A Vercel engineer said a safety classifier ran "five to 18 times faster" than the LLM it replaced.
  - Armin Ronacher (quoted via TechCrunch) said the design "delegates the hallucination problem a little bit to the user".
- An HN sub-thread (on a "Jevmem" Claude Code memory tool) clarified that Jev is proprietary, so data goes to TypeSafe — [HN item 49847030](https://news.ycombinator.com/item?id=49847030)
- Other items seen in searches but not read: an "OpenJev" HN post ([HN 49752041](https://news.ycombinator.com/item?id=49752041)), TechCrunch's "A new kind of AI model from a ChatGPT inventor is thrilling developers" (2026-09-18) ([TechCrunch](https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/)), and an AgentConn post "If Calibration Holds" ([AgentConn](https://agentconn.com/blog/jev-typesafe-new-agent-layer-if-calibration-holds/)).

**Comparison with arXiv 2609.26550** (CMU; local full text)
- The paper is consistent with the reports above. Jev comes within about 3 points of GPT-6 where "the verdict can be read off the text" (preference, safety, factuality), and trails by 7–28 points on math, code and logic.
- Its errors concentrate in low-confidence cases, so confidence-gated escalation works.
- Interface quirks: Choice and Noul probabilities differ by 0.055 on average; Noul pairs miss summing to 1 by 0.045. Thresholds should be tuned per output type.
- The authors explicitly did not test long agent trajectories.
- Source: [paper full text, local](file:///Users/gkocher/Desktop/monitoring-research/research_notes/JEV%20decision%20models%20for%20monitoring/_source_jev_as_judge_paper_fulltext.txt)

### Inferences
- Every independent study (LessWrong, Ruchith1018, rahulbansal, the CMU paper) finds strong *ranking* (AUROC) but poor absolute calibration or threshold transfer. A cheap first-stage trajectory monitor should therefore use JEV scores as a rank or suspicion signal with thresholds tuned locally per output type and version, not as calibrated P(attack).
- The LessWrong results (instruction-style injections raise suspicion; best-of-N lowers catch rate by about a third) are the closest prior evidence for AI-control monitoring. They come from short single-file code, not long multi-step trajectories.
- Obfuscation and TokenBreak weaknesses (HiddenLayer; 32–39% detection on encodings) mean an attacking agent that encodes payloads may evade JEV. Pairing it with cheap deterministic decoders or normalizers, or escalating on "contains encoded content", is advisable.

### Gaps
- No published evaluation of JEV on long multi-step agent trajectories (e.g. BashBench, SHADE-Arena, ControlArena bash or infra settings). This is the key unknown for the team's use case.
- HiddenLayer's underlying report and its numeric attack success rates were not located; only press coverage.
- No independent evaluation of jev-1.14 versus 1.13 was found.
- X and Reddit discussion was seen only via press quotes. I found no primary threads with failure reports beyond those summarized above.
- The LessWrong post's comment section was not reviewed.
