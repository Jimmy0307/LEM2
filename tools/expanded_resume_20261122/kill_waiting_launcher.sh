#!/usr/bin/env bash
# Make sure no orphaned "start full run after speed test" waiter survives.
pkill -f '07_full_run_after_speedtest.sh' && echo "killed orphan waiter" || echo "no waiter running"
pgrep -af 'orchestrate.py' | grep -v pgrep || true
