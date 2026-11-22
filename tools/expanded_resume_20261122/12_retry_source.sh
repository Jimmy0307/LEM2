#!/usr/bin/env bash
# Retry one failed prefetch (the detached pipeline waits while this runs).
set -euo pipefail
cd "$HOME/lem2_expanded"
"$HOME/lem2_venv/bin/python" -I /mnt/d/Desk/LEM2_expanded_resume/tools/08_prefetch_sources.py \
  --repo "$HOME/lem2_expanded" --main "$HOME/lem2_runs/expanded_188_42seeds" \
  --staging "$HOME/lem2_runs/source_prefetch" --report /mnt/d/Desk/LEM2_expanded_resume/reports/08_prefetch_retry.json \
  --workers 1 --warm-openml --only "$1" >> /mnt/d/Desk/LEM2_expanded_resume/reports/prefetch.log 2>&1
