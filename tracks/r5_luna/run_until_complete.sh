#!/bin/bash
# Resumable held-out scoring driver (nohup). Every pass re-plans from the sqlite caches and scores only missing steps,
# so a network outage only pauses the work. Two chains run in parallel: decisions (Luna frozen -> Luna full -> JEV full)
# and generative Luna (H5c). Stops when a pass has nothing left.
#   nohup tracks/r5_luna/run_until_complete.sh decisions > data/r5_luna/logs/drive_decisions.log 2>&1 &
#   nohup tracks/r5_luna/run_until_complete.sh gen       > data/r5_luna/logs/drive_gen.log 2>&1 &
cd "$(dirname "$0")/../.."
unset VIRTUAL_ENV
chain="$1"
S=tracks.r5_luna.score
AK=akshn_bash,akshn_agentdojo,akshn_iac,akshn_shade,akshn_basharena_opus46,akshn_basharena_sonnet45,akshn_linuxarena
todo() { grep -E "todo=" "$1" | sed -E 's/.*todo=([0-9]+).*/\1/' | paste -sd+ - | bc; }
for pass in 1 2 3 4 5 6 7 8 9 10; do
  echo "== pass $pass $(date)"
  L=data/r5_luna/logs/pass_${chain}.log
  : > $L
  if [ "$chain" = "decisions" ]; then
    uv run python -m $S --model luna --set eval --subset nano --sources mb,$AK --yes >> $L 2>&1
    uv run python -m $S --model luna --set eval --subset all --sources akshn_basharena_opus46 --yes >> $L 2>&1
    uv run python -m $S --model luna --set eval --mode full --subset all --sources akshn_basharena_opus46 --yes >> $L 2>&1
    uv run python -m $S --model luna --set eval --mode full --subset nano --sources akshn_linuxarena --yes >> $L 2>&1
    uv run python -m $S --model jev --set eval --mode full --subset all --only-truncated --sources akshn_basharena_opus46 --yes >> $L 2>&1
    uv run python -m $S --model jev --set eval --mode full --subset nano --only-truncated --sources akshn_linuxarena --yes >> $L 2>&1
    uv run python -m $S --model luna --set eval --subset all --sources $AK --yes >> $L 2>&1
  else
    uv run python -m tracks.r5_luna.score_gen --set h5c --yes >> $L 2>&1
  fi
  grep -E "todo=|done|Budget|Error|error" $L | cut -c1-200 | tail -30
  t=$(todo $L)
  echo "pass $pass: todo at start = $t"
  if [ "$t" = "0" ]; then echo COMPLETE; exit 0; fi
  sleep 60
done
