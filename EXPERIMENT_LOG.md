# Experiment log

## 2026-10-20: setup

- Background: `../BACKGROUND_SUMMARY.md` and `../IDEAS.md` (ranked ideas; tracks T1–T3 approved).
- OpenRouter is reachable from the laptop as of today, so all API work runs locally. SSH to RunPod timed out (VPN); RunPod is a fallback only.
- Balances (2026-10-20): MATS account ≈ $6,346 left; weekly1000 key has $1,000 this week. Budget for T1–T3: ≤ $500 total, enforced by the ledger.
- Monitor models:
  - `openai/gpt-4.1-mini` ($0.40/M in): returns token logprobs via OpenRouter even though metadata says no. Primary cheap monitor, using the logprob-expected score for continuous calibration.
  - `openai/gpt-4.1-nano` ($0.10/M): weak monitor.
  - Existing streams from much stronger monitors: LinuxArena sweep (12 monitors incl. opus-4-6), aksh-n Gemini-3.1-Pro.
- Data sources (see `../background/data_availability.md`):
  - LinuxArena monitor sweep: 12 monitors × 342 trajectories, per action.
  - aksh-n per-step labels.
  - MRT sequential.
  - Persistent-state per-PR.
  - MonitoringBench attacks + Honest-550.
