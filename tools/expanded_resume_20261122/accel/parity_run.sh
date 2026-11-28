#!/usr/bin/env bash
# Real-data parity + speed check of the bitset acceleration (accel worktree, separate output dirs).
# Runs whole seeds (4 scenarios) with a 4 h deadline; never writes to the main run directory.
set -uo pipefail
ACC=/home/user/lem2_accel
PY=/home/user/lem2_venv/bin/python
MAIN=/home/user/lem2_runs/expanded_188_42seeds
OUT=/home/user/lem2_runs/accel_parity
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
mkdir -p "$OUT"
run_one() {  # dataset seed
  local ds="$1" seed="$2" dir dsdir
  dsdir="${ds/:/__}"
  dir="$OUT/${dsdir}_s$(printf %02d "$seed")"
  mkdir -p "$dir/checkpoints/$dsdir"
  cp "$MAIN/checkpoints/$dsdir/SOURCE.json" "$MAIN/checkpoints/$dsdir/source.pkl" "$dir/checkpoints/$dsdir/"
  echo "$(date -Is) start $ds seed $seed"
  (cd "$ACC" && "$PY" -m experiments.expanded_42seeds_20261120.run --output "$dir" --dataset "$ds" \
     --seeds "$seed" --workers 1 --timeout 14400 > "$dir/run.log" 2>&1)
  echo "$(date -Is) done $ds seed $seed exit=$?"
}
run_one OML51:openml_4541 2 &
run_one OML51:openml_42734 2 &
run_one OML51:openml_41027 2 &
wait
echo "$(date -Is) all parity runs finished"
