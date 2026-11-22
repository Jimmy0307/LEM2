#!/usr/bin/env bash
# Lock-free event poller for the Monitor tool: opens each log only briefly every
# 60 s (no persistent tail -F handle that could block Windows writers) and exits
# by itself after ~29 minutes so no orphan survives an expired monitor.
R=/d/Desk/LEM2_expanded_resume/reports
FILES=("$R/run_full.log" "$R/publish.log" "$R/pipeline_detached.log" "$R/host_watchdog.log")
PATTERN='"kind": "(audit|audit_error|final_audit|job_error|published|push_deferred|push_blocked|publisher_error|publisher_io_retry)"|"conflicts": \["|SOURCE_CONFLICT|"source": "SOURCE_FAILURE"|Traceback|refusing|exited|Killed|MemoryError|EMERGENCY|restored|failed'
declare -A seen
for f in "${FILES[@]}"; do seen[$f]=$(wc -l < "$f" 2>/dev/null || echo 0); done
end=$((SECONDS + 29 * 60))
while [ $SECONDS -lt $end ]; do
  sleep 60
  for f in "${FILES[@]}"; do
    n=$(wc -l < "$f" 2>/dev/null || echo 0)
    if [ "$n" -gt "${seen[$f]}" ]; then
      tail -n +"$((seen[$f] + 1))" "$f" | head -n "$((n - seen[$f]))" | grep -E "$PATTERN" | cut -c1-400
      seen[$f]=$n
    fi
  done
done
