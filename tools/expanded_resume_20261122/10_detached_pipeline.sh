#!/usr/bin/env bash
# Detached full run: no stdout/stderr dependency on any Windows pipe.
# Launched through WMI so it is independent of the Claude Code session; the
# launching wsl.exe stays attached and keeps the WSL instance alive.
set -uo pipefail
REPO="$HOME/lem2_expanded"
PY="$HOME/lem2_venv/bin/python"
TOOLS=/mnt/d/Desk/LEM2_expanded_resume/tools
REPORTS=/mnt/d/Desk/LEM2_expanded_resume/reports
exec >>"$REPORTS/pipeline_detached.log" 2>&1
echo "$(date -Is) pipeline start (pid $$)"

if pgrep -f 'orchestrate.py.*--snapshot-dir' >/dev/null; then
  echo "$(date -Is) a full-run driver is already running; refusing to start a second writer"; exit 1
fi
# Single-writer rule: wait for prefetch, the speed-test driver and its job processes.
while pgrep -f '08_prefetch_sources.py' >/dev/null \
   || pgrep -f 'orchestrate.py.*--seeds 1' >/dev/null \
   || pgrep -f 'lem2_runs/shards/' >/dev/null; do
  sleep 20
done
echo "$(date -Is) prerequisites idle; checking code identity"
cd "$REPO" || exit 1
if [ -n "$(git status --porcelain)" ] || [ "$(git rev-parse HEAD^{tree})" != 3dc3d175d349a6acb893093a3996c78bfffeb8dc ]; then
  echo "$(date -Is) code tree mismatch; refusing to run"; exit 1
fi
echo "$(date -Is) starting full run"
"$PY" -I "$TOOLS/orchestrate.py" --repo "$REPO" --python "$PY" \
  --main "$HOME/lem2_runs/expanded_188_42seeds" --work "$HOME/lem2_runs/shards" \
  --profile "$HOME/lem2_runs/schedule_profile.json" \
  --max-jobs 16 --max-heavy 8 --mem-budget-gb 12 --mem-reserve-gb 1.5 --audit-every-min 30 \
  --snapshot-dir /mnt/d/Desk/LEM2_expanded_resume/snapshots \
  --source-cache "$HOME/lem2_runs/source_prefetch" >>"$REPORTS/run_full.log" 2>&1
echo "$(date -Is) full run driver exited with code $?"
