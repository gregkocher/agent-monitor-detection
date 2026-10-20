# agent-monitor-detection

Detection-theoretic decision rules for AI-agent monitors. Three experiment tracks:

| Track | Question | Directory |
|---|---|---|
| **T1: matched-budget decision rules** | At equal trajectory-level FPR / ARL, do sequential statistics (CUSUM, Shiryaev–Roberts, GLR, conformal e-processes) beat max-aggregation on real per-step monitor score streams? Does accumulation only help on history-free ("innovation") monitors because history-aware monitors already integrate evidence? Also covers cross-session (per-PR) accumulation. | `tracks/t1_matched_budget/` |
| **T2: per-context thresholds** | How much do honest score distributions vary by context? Do per-context (CFAR / Mondrian-conformal / partially pooled) thresholds beat a global threshold at a fixed global audit budget, and how do they fare against attack selection and baseline poisoning, compared with damage-equalizing (Stackelberg) allocation? | `tracks/t2_per_context/` |
| **T3: monitor-aware attackers** | Can an LLM that knows the detector restructure real multi-step attacks to evade sequential monitors without breaking them? Does undetected damage follow the covert-adversary √ARL prediction? Does a multi-chart (max + CUSUM + e-process) detector close the gap? | `tracks/t3_aware_attacker/` |

## Layout

```
amd/common/      schema (Trajectory, ScoreStream), JSONL I/O, OpenRouter client + spend ledger
amd/data/        loaders: public datasets -> data/processed/<source>/{trajectories,scores}.jsonl
amd/scoring/     monitor prompts and the per-step re-scoring runner (OpenRouter, resumable cache)
amd/detectors/   trajectory decision statistics (max, k-th max, top-k, CUSUM, SR, GLR, e-process, ...)
amd/evaluation/  matched-FPR calibration, ARL / delay, bootstrap CIs, Logit-ROC extrapolation, per-context thresholds
tracks/          experiment scripts and configs per track
results/         small result tables / figures (committed); raw outputs gitignored
data/            raw + processed data (gitignored)
```

## Budget and safety rules

- OpenRouter spend is capped by `amd/common/openrouter.py`: $500 global; t1 $130, t2 $70, t3 $200, dev $15, reserve $100. Every call is logged to `results/spend_ledger.jsonl` with the cost OpenRouter reports. Check with `uv run python -m amd.common.openrouter`.
- Keys are read from disk at call time and never logged or committed.
- Experiments run locally. Monitor scoring and attack rewriting are stateless API calls over fixed trajectories. The only executed agent code (T3 replay validation) runs in per-sample Docker sandboxes via Inspect.
- Raw third-party data stays in `data/` (gitignored). The MonitoringBench attack `.eval` headers contain a leaked third-party token, so never commit or republish raw headers.

## Setup

```bash
unset VIRTUAL_ENV   # if another venv is active
uv sync
uv run pytest -q
```

See `EXPERIMENT_LOG.md` for the running log of decisions and results.
