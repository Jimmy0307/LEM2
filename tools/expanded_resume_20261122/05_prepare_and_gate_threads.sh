#!/usr/bin/env bash
# Unit tests for the driver, scheduling profile, and a repeat of the fidelity
# gate under the single-threaded BLAS environment the driver uses.
set -euo pipefail
REPO="$HOME/lem2_expanded"
PY="$HOME/lem2_venv/bin/python"
TOOLS=/mnt/d/Desk/LEM2_expanded_resume/tools
REPORTS=/mnt/d/Desk/LEM2_expanded_resume/reports
SCR=/mnt/c/Users/user/AppData/Local/Temp/claude/323912f3baf0066a/927c8470-6cae-4755-ab93-0f984bf1ee42/scratchpad

echo "--- driver unit tests"
cd "$HOME" && "$PY" -m pytest -q -p no:cacheprovider "$TOOLS/test_orchestrate.py" 2>&1 | tail -2

echo "--- scheduling profile"
"$PY" -I "$TOOLS/build_profile.py" "$SCR/fs_timings_.csv" "$SCR/fs_timings_retry_44465026637.csv" "$SCR/fs_failures.csv" \
  "$HOME/lem2_runs/schedule_profile.json"
cp "$HOME/lem2_runs/schedule_profile.json" "$REPORTS/schedule_profile.json"

echo "--- fidelity gate with single-threaded BLAS env"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
cd "$REPO"
"$PY" -I "$TOOLS/03_fidelity_gate.py" --repo "$REPO" --python "$PY" --output "$HOME/lem2_runs/expanded_188_42seeds" \
  --gate-root "$HOME/lem2_runs/gate_3566580_threads1" --report "$REPORTS/03b_fidelity_gate_threads1.json" | tail -1
