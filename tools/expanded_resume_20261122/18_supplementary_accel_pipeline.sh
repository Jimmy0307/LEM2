#!/usr/bin/env bash
# 2026-11-26: SUPPLEMENTARY extended-deadline run (separate output dir, separate contract).
#   code     : /home/user/lem2_accel @ accel/bitset-union-20261125 (805ade0) = 56e293c + exact bitset
#              support unions in fedrs/predict.py (bit-identical predictions; see accel/ parity evidence)
#   deadline : 14,400 s per model (main run: 2,700 s)
#   output   : $HOME/lem2_runs/expanded_accel_ext   (the main run directory is never written)
# Launched through WMI so it is independent of any Claude Code session.
set -uo pipefail
ACC="$HOME/lem2_accel"
PY="$HOME/lem2_venv/bin/python"
TOOLS=/mnt/d/Desk/LEM2_expanded_resume/tools
REPORTS=/mnt/d/Desk/LEM2_expanded_resume/reports
SUPP="$HOME/lem2_runs/expanded_accel_ext"
DATASETS="${SUPP_DATASETS:-OML51:openml_41027,OML51:openml_42734,OML51:openml_41162,OML51:openml_4135,OML51:openml_42733}"
exec >>"$REPORTS/supplementary_accel.log" 2>&1
echo "$(date -Is) supplementary start (pid $$) datasets=$DATASETS"
if pgrep -f "orchestrate.py.*--main $SUPP " >/dev/null; then
  echo "$(date -Is) a supplementary driver is already running; refusing"; exit 1
fi
cd "$ACC" || exit 1
if [ -n "$(git status --porcelain)" ] || [ "$(git rev-parse HEAD)" != 805ade097fdd3d9f9c5ef234f3e9277f41798712 ]; then
  echo "$(date -Is) accel code mismatch; refusing to run"; exit 1
fi
"$PY" -I "$TOOLS/orchestrate.py" --repo "$ACC" --python "$PY" \
  --main "$SUPP" --work "$HOME/lem2_runs/shards_accel" \
  --profile "$HOME/lem2_runs/schedule_profile.json" \
  --max-jobs 6 --max-heavy 6 --mem-budget-gb 8 --mem-reserve-gb 2.5 --audit-every-min 60 \
  --source-cache "$HOME/lem2_runs/source_prefetch" --datasets "$DATASETS" --timeout 14400 \
  >>"$REPORTS/supplementary_accel_driver.log" 2>&1
echo "$(date -Is) supplementary driver exited with code $?"
