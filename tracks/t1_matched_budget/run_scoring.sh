#!/bin/bash
# Round 2 scoring: Honest-550 then the attack sample, gpt-4.1-mini, history full and none.
# Each step is cached, so the script is resumable: re-running it only pays for missing steps.
# The second pass of every job retries steps whose API call failed.
cd "$(dirname "$0")/../.."
unset VIRTUAL_ENV
L=tracks/t1_matched_budget/logs
for SET in honest attack; do
  for PASS in 1 2; do
    uv run python tracks/t1_matched_budget/score.py --set $SET --history none --yes --concurrency 40 >> $L/${SET}_none.log 2>&1 &
    P1=$!
    uv run python tracks/t1_matched_budget/score.py --set $SET --history full --yes --concurrency 40 >> $L/${SET}_full.log 2>&1 &
    P2=$!
    wait $P1 $P2
  done
  echo "$(date) $SET done" >> $L/run_scoring.log
done
