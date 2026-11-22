#!/usr/bin/env bash
# Superseded: the full run is started only by 10_detached_pipeline.sh (launched
# via WMI, independent of the Claude Code session). Kept as a no-op guard so the
# earlier session-bound chain cannot start a second writer.
echo "$(date -Is) 06_launch.sh '$*' superseded by 10_detached_pipeline.sh; not starting" \
  | tee -a /mnt/d/Desk/LEM2_expanded_resume/reports/pipeline_detached.log
exit 0
