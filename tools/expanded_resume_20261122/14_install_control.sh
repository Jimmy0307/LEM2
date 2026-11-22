#!/usr/bin/env bash
# Atomically install the live control file into the main run directory.
set -euo pipefail
MAIN="$HOME/lem2_runs/expanded_188_42seeds"
cp /mnt/d/Desk/LEM2_expanded_resume/tools/orchestrator_control.json "$MAIN/ORCHESTRATOR_CONTROL.tmp"
"$HOME/lem2_venv/bin/python" -I -c "import json,sys; json.load(open(sys.argv[1]))" "$MAIN/ORCHESTRATOR_CONTROL.tmp"
mv "$MAIN/ORCHESTRATOR_CONTROL.tmp" "$MAIN/ORCHESTRATOR_CONTROL.json"
cat "$MAIN/ORCHESTRATOR_CONTROL.json"
