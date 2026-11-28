#!/usr/bin/env bash
# 2026-11-25: restart the full-run driver with near-certain-timeout datasets scheduled LAST.
# Same as 10_detached_pipeline.sh except: (1) waits for the old driver instead of refusing,
# (2) passes --defer (ordering only; every model is still run under the unchanged contract).
# Launched through WMI so it is independent of any Claude Code session and keeps WSL alive.
set -uo pipefail
REPO="$HOME/lem2_expanded"
PY="$HOME/lem2_venv/bin/python"
TOOLS=/mnt/d/Desk/LEM2_expanded_resume/tools
REPORTS=/mnt/d/Desk/LEM2_expanded_resume/reports
DEFER="OML51:openml_42732,OML51:openml_42733,OML51:openml_4135,OML51:openml_41162,OML51:openml_42734"
exec >>"$REPORTS/pipeline_detached.log" 2>&1
echo "$(date -Is) defer-pipeline start (pid $$); waiting for the previous driver and its jobs to stop"
while pgrep -f 'orchestrate.py.*--snapshot-dir' >/dev/null || pgrep -f 'lem2_runs/shards/' >/dev/null; do
  sleep 10
done
echo "$(date -Is) previous driver idle; checking code identity"
cd "$REPO" || exit 1
if [ -n "$(git status --porcelain)" ] || [ "$(git rev-parse HEAD^{tree})" != 3dc3d175d349a6acb893093a3996c78bfffeb8dc ]; then
  echo "$(date -Is) code tree mismatch; refusing to run"; exit 1
fi
echo "$(date -Is) starting full run with --defer $DEFER"
"$PY" -I "$TOOLS/orchestrate.py" --repo "$REPO" --python "$PY" \
  --main "$HOME/lem2_runs/expanded_188_42seeds" --work "$HOME/lem2_runs/shards" \
  --profile "$HOME/lem2_runs/schedule_profile.json" \
  --max-jobs 12 --max-heavy 9 --mem-budget-gb 14 --mem-reserve-gb 2.0 --audit-every-min 30 \
  --snapshot-dir /mnt/d/Desk/LEM2_expanded_resume/snapshots \
  --source-cache "$HOME/lem2_runs/source_prefetch" --defer "$DEFER" >>"$REPORTS/run_full.log" 2>&1
echo "$(date -Is) full run driver exited with code $?"
