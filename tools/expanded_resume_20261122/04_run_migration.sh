#!/usr/bin/env bash
# Negative contract check, gated manifest migration, idempotency check,
# and integrity check of the frozen originals.
set -euo pipefail
REPO="$HOME/lem2_expanded"
RUN="$HOME/lem2_runs/expanded_188_42seeds"
PY="$HOME/lem2_venv/bin/python"
TOOLS=/mnt/d/Desk/LEM2_expanded_resume/tools
REPORTS=/mnt/d/Desk/LEM2_expanded_resume/reports
ARGS=(--repo "$REPO" --output "$RUN"
      --original-commit 35665809f9173d5e7dccb93e69c4ed15b006d372
      --expected-tree 3dc3d175d349a6acb893093a3996c78bfffeb8dc
      --source-report "$REPORTS/02_source_verification.json"
      --gate-report "$REPORTS/03_fidelity_gate.json")
cd "$REPO"

echo "--- negative check on a throwaway copy (expect contract rejection)"
T="$(mktemp -d)"
cp "$RUN/ORIGINAL_3566580/RUN_MANIFEST.json" "$T/"
chmod u+w "$T/RUN_MANIFEST.json"
"$PY" -m experiments.expanded_42seeds_20261120.run --output "$T" --dataset UCI20:iris --seeds 1 2>&1 | tail -1 || true
rm -rf "$T"

echo "--- migration"
"$PY" -I "$TOOLS/04_migrate_manifest_revision.py" "${ARGS[@]}"
echo "--- idempotency"
"$PY" -I "$TOOLS/04_migrate_manifest_revision.py" "${ARGS[@]}"
echo "--- frozen originals"
(cd "$RUN/ORIGINAL_3566580" && sha256sum -c --quiet "$HOME/lem2_runs/ORIGINAL_3566580.sha256" && echo intact)
echo "--- current manifest git_revision"
grep git_revision "$RUN/RUN_MANIFEST.json"
