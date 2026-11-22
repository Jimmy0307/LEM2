#!/usr/bin/env bash
# 1) driver unit tests  2) prefetch every source via run.run_dataset(seeds=[])
# 3) wait for the speed-test driver to exit (single writer)  4) full run.
set -euo pipefail
REPO="$HOME/lem2_expanded"
PY="$HOME/lem2_venv/bin/python"
TOOLS=/mnt/d/Desk/LEM2_expanded_resume/tools
REPORTS=/mnt/d/Desk/LEM2_expanded_resume/reports
STAGING="$HOME/lem2_runs/source_prefetch"

(cd "$HOME" && "$PY" -m pytest -q -p no:cacheprovider "$TOOLS/test_orchestrate.py" | tail -1)

cd "$REPO"
"$PY" -I "$TOOLS/08_prefetch_sources.py" --repo "$REPO" --main "$HOME/lem2_runs/expanded_188_42seeds" \
  --staging "$STAGING" --report "$REPORTS/08_prefetch.json" --workers 6 2>&1 | tee -a "$REPORTS/prefetch.log"
echo "PREFETCH_DONE" | tee -a "$REPORTS/prefetch.log"

while pgrep -f 'orchestrate.py.*--seeds 1' >/dev/null; do sleep 20; done
exec bash "$TOOLS/06_launch.sh" full \
  --max-jobs 20 --mem-budget-gb 12 --mem-reserve-gb 1.5 --audit-every-min 30 \
  --snapshot-dir /mnt/d/Desk/LEM2_expanded_resume/snapshots --source-cache "$STAGING"
