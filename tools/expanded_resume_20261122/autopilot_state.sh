#!/usr/bin/env bash
# One-line JSON state of the main and protocol runs (read only). Used by 23_autopilot.ps1.
count() { find "$1/checkpoints" -name 'seed*__*.json' 2>/dev/null | wc -l; }
main=$(count /home/user/lem2_runs/expanded_188_42seeds)
prot=$(count /home/user/lem2_runs/protocol_compare_20261128)
PYPAT='^/home/user/lem2_venv/bin/python -I /mnt/d/Desk/LEM2_expanded_resume/tools/orchestrate.py --repo'
md=$(pgrep -fc "$PYPAT /home/user/lem2_expanded " || true)
pd=$(pgrep -fc "$PYPAT /home/user/lem2_protocol " || true)
ml=$(pgrep -fc '^bash /mnt/d/Desk/LEM2_expanded_resume/tools/17_detached_pipeline_defer.sh' || true)
pl=$(pgrep -fc '^bash /mnt/d/Desk/LEM2_expanded_resume/tools/21_protocol_compare_pipeline.sh' || true)
echo "{\"main_decided\": ${main:-0}, \"protocol_decided\": ${prot:-0}, \"main_driver\": ${md:-0}, \"protocol_driver\": ${pd:-0}, \"main_launcher\": ${ml:-0}, \"protocol_launcher\": ${pl:-0}}"
