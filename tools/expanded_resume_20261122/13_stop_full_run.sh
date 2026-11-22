#!/usr/bin/env bash
# Stop the full-run driver and its job processes (checkpoint writes are atomic;
# completed models in shard dirs are recovered on the next start), then test.
set -uo pipefail
pkill -f 'orchestrate.py.*--snapshot-dir' && echo "driver stopped"
sleep 3
pkill -f 'lem2_runs/shards/' && echo "job processes stopped"
sleep 3
left=$(pgrep -fc 'orchestrate.py|lem2_runs/shards/' || true)
echo "remaining driver/job processes: ${left:-0}"
cd "$HOME" && "$HOME/lem2_venv/bin/python" -m pytest -q -p no:cacheprovider /mnt/d/Desk/LEM2_expanded_resume/tools/test_orchestrate.py | tail -1
