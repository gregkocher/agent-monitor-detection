#!/bin/bash
# Resumable nohup driver for the preregistered r5watch held-out scoring: MB evaluation set, then (if r5watch spend
# <= $70 after MB) the aksh-n LinuxArena nano subset. Each pass re-plans from the sqlite cache.
cd "$(dirname "$0")/../.."
unset VIRTUAL_ENV
CFG=$(python3 -c "import json;print(json.load(open('results/r5_watch/dev_choice.json'))['config'])")
drive () {
  src=$1
  for pass in 1 2 3 4 5 6 7 8 9 10 11 12; do
    echo "== $src pass $pass $(date)"
    L=data/r5_watch/logs/pass_$src.log
    uv run python -m tracks.r5_watch.score --set eval --config $CFG --sources $src --yes --concurrency ${CONC:-96} --usd-per-step 0.00052 > $L 2>&1
    grep -E "todo=|== $src|BudgetExceeded" $L | cut -c1-300
    t=$(grep -E "todo=" $L | head -1 | sed -E 's/.*todo=([0-9]+).*/\1/')
    echo "$src pass $pass: todo at start = $t"
    if [ "$t" = "0" ]; then echo "$src COMPLETE"; return 0; fi
    if grep -q BudgetExceeded $L; then echo "$src BUDGET"; return 1; fi
    sleep 60
  done
  return 1
}
drive mb || exit 1
spent=$(uv run python -c "from amd.common.openrouter import ledger_totals; print(ledger_totals()[1].get('r5watch',0))")
echo "r5watch spend after MB: $spent"
if python3 -c "import sys; sys.exit(0 if $spent <= 70 else 1)"; then
  drive akshn_linuxarena
else
  echo "LinuxArena dropped (spend > 70)"
fi
echo ALL_DONE
