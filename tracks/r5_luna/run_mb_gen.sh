#!/bin/bash
# Resumable driver (nohup) for the addendum: generative Luna on every MB evaluation trajectory.
cd "$(dirname "$0")/../.."
unset VIRTUAL_ENV
for pass in 1 2 3 4 5 6 7 8 9 10; do
  echo "== pass $pass $(date)"
  L=data/r5_luna/logs/pass_mbgen.log
  uv run python -m tracks.r5_luna.score_gen --set mb_all --yes --concurrency ${CONC:-96} > $L 2>&1
  grep -E "todo=|== mb" $L | cut -c1-200
  t=$(grep -E "todo=" $L | sed -E 's/.*todo=([0-9]+).*/\1/' | paste -sd+ - | bc)
  echo "pass $pass: todo at start = $t"
  if [ "$t" = "0" ]; then echo COMPLETE; exit 0; fi
  sleep 60
done
