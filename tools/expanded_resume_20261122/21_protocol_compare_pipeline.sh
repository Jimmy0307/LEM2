#!/usr/bin/env bash
# 2026-11-28: PROTOCOL COMPARISON run: 80/20 holdout vs nested 80(64/16)/20 (separate dir/contract).
#   code     : /home/user/lem2_accel @ accel/bitset-union-20261125 (805ade0) = 56e293c + exact bitset
#              support unions in fedrs/predict.py (bit-identical predictions; see accel/ parity evidence)
#   deadline : none in practice (1e9 s; main run: 2,700 s) -- user decision 2026-11-26
#   output   : $HOME/lem2_runs/expanded_accel_nolimit (main run directory is never written)
# Launched through WMI so it is independent of any Claude Code session.
set -uo pipefail
ACC="$HOME/lem2_protocol"
PY="$HOME/lem2_venv/bin/python"
TOOLS=/mnt/d/Desk/LEM2_expanded_resume/tools
REPORTS=/mnt/d/Desk/LEM2_expanded_resume/reports
SUPP="$HOME/lem2_runs/protocol_compare_20261128"
DATASETS="$(cat $HOME/lem2_runs/protocol_compare_20261128/DATASETS.txt)"
DEFER="OML51:openml_41027,OML51:openml_41162,OML51:openml_4135,OML51:openml_42733,OML51:openml_42734,OML51:openml_42742,UCI20:adult_income"
exec >>"$REPORTS/protocol_compare.log" 2>&1
echo "$(date -Is) supplementary start (pid $$) datasets=$DATASETS"
if pgrep -f "orchestrate.py.*--main $SUPP " >/dev/null; then
  echo "$(date -Is) a supplementary driver is already running; refusing"; exit 1
fi
cd "$ACC" || exit 1
if [ -n "$(git status --porcelain)" ] || [ "$(git rev-parse HEAD)" != d24d1cc6b23106b7218c1516352e9639dc2c05a5 ]; then
  echo "$(date -Is) protocol code mismatch; refusing to run"; exit 1
fi
"$PY" -I "$TOOLS/orchestrate.py" --repo "$ACC" --python "$PY" \
  --main "$SUPP" --work "$HOME/lem2_runs/shards_protocol" \
  --profile "$HOME/lem2_runs/schedule_profile.json" \
  --max-jobs 8 --max-heavy 6 --mem-budget-gb 10 --mem-reserve-gb 2.0 --audit-every-min 60 \
  --source-cache "$HOME/lem2_runs/source_prefetch" --datasets "$DATASETS" --timeout 1000000000 --defer "$DEFER" --module experiments.protocol_compare_20261128.run \
  >>"$REPORTS/protocol_compare_driver.log" 2>&1
echo "$(date -Is) supplementary driver exited with code $?"
