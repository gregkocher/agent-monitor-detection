#!/bin/bash
# Resumable completion driver: every pass re-plans from the caches and scores only missing / failed steps,
# so a network outage only pauses the work. Stops when a pass has nothing left to score.
cd "$(dirname "$0")/../.."
unset VIRTUAL_ENV
for pid in "$@"; do while kill -0 "$pid" 2>/dev/null; do sleep 30; done; done
for pass in 1 2 3 4 5 6 7 8; do
  echo "== pass $pass $(date)"
  uv run python -m tracks.r5_jev.score_jev --set eval --variant B_w3 --track r5jev --rps 40 --concurrency 48 --yes > /tmp/r5_jev_pass.log 2>&1
  jt=$(grep -E "todo=" /tmp/r5_jev_pass.log | sed -E 's/.*todo=([0-9]+).*/\1/' | paste -sd+ - | bc)
  cat /tmp/r5_jev_pass.log | grep -E "todo=|done" | cut -c1-160
  uv run python -m tracks.r5_jev.score_nano --set mb --yes --concurrency 48 > /tmp/r5_nano_pass.log 2>&1
  uv run python -m tracks.r5_jev.score_nano --set akshn --yes --concurrency 48 >> /tmp/r5_nano_pass.log 2>&1
  nt=$(grep -E "todo=" /tmp/r5_nano_pass.log | sed -E 's/.*todo=([0-9]+).*/\1/' | paste -sd+ - | bc)
  grep -E "todo=|wrote" /tmp/r5_nano_pass.log | cut -c1-160
  echo "pass $pass: jev todo at start=$jt nano todo at start=$nt"
  if [ "$jt" = "0" ] && [ "$nt" = "0" ]; then echo COMPLETE; exit 0; fi
  sleep 120
done
