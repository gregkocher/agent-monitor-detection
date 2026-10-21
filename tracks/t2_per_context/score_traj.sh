#!/bin/bash
# T2 round 2(c): trajectory-mode re-scoring of MonitoringBench attacks + Honest-550 by two
# cheap monitor families (adds monitor contexts and a task-cluster dataset). Billed to t2.
set -u
cd "$(dirname "$0")/../.."
unset VIRTUAL_ENV
for m in openai/gpt-4.1-nano openai/gpt-4.1-mini; do
  for s in mb_honest monitoringbench; do
    echo "### $m $s $(date)"
    uv run python -u -m amd.scoring.run --source $s --model $m --history trajectory --track t2 \
      --concurrency 16 --yes
  done
done
echo "### done $(date)"
