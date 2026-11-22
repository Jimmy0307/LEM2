#!/usr/bin/env bash
# Wait for the speed-test driver (single writer rule), then start the full run.
set -euo pipefail
while pgrep -f 'orchestrate.py.*--seeds 1' >/dev/null; do sleep 20; done
exec bash /mnt/d/Desk/LEM2_expanded_resume/tools/06_launch.sh full \
  --max-jobs 20 --mem-budget-gb 12 --mem-reserve-gb 1.5 --audit-every-min 30 \
  --snapshot-dir /mnt/d/Desk/LEM2_expanded_resume/snapshots
