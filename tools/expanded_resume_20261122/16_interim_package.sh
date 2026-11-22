#!/usr/bin/env bash
# Build a consistent interim package from the live run WITHOUT writing to it:
# copy checkpoints (no raw data) -> run.py --audit on the copy -> interim analysis.
set -euo pipefail
REPO="$HOME/lem2_expanded"
PY="$HOME/lem2_venv/bin/python"
MAIN="$HOME/lem2_runs/expanded_188_42seeds"
STAMP="$(date +%Y%m%dT%H%M%S)"
TMP="$HOME/lem2_runs/interim_$STAMP"
OUT="/mnt/d/Desk/LEM2_expanded_resume/interim/$STAMP"
mkdir -p "$TMP/checkpoints" "$OUT"

trap 'rm -rf "$TMP"' EXIT
cp -p "$MAIN/RUN_MANIFEST.json" "$MAIN/SOURCE_REGISTRY.csv" "$TMP/"
for d in "$MAIN"/checkpoints/*/; do
  n=$(basename "$d"); mkdir -p "$TMP/checkpoints/$n"
  find "$d" -maxdepth 1 -type f \( -name 'seed*.json' -o -name 'SOURCE.json' -o -name 'SOURCE_FAILURE.json' \) \
    -exec cp -p {} "$TMP/checkpoints/$n/" \;
done
echo "copied model files: $(find "$TMP/checkpoints" -name 'seed*.json' | wc -l)"

cd "$REPO"
"$PY" -m experiments.expanded_42seeds_20261120.run --audit --output "$TMP" | tail -1
"$PY" -I /mnt/d/Desk/LEM2_expanded_resume/tools/interim_findings.py "$TMP" "$OUT"

cp -p "$TMP"/{STATUS.json,COMPLETENESS.csv,MISSING.csv,FAILURES.csv,PAIRED_SUMMARY.csv,SOURCE_REGISTRY.csv} "$OUT/"
for f in RESULTS PAIRED_COMPARISONS TIMINGS; do gzip -9 -c "$TMP/$f.csv" > "$OUT/$f.csv.gz"; done
# Partial datasets' per-model checkpoints (finished datasets are already published individually).
"$PY" -I -c "import shutil,sys; shutil.make_archive(sys.argv[1], 'zip', sys.argv[2], 'checkpoints')" \
  "$OUT/checkpoints_all_completed_models" "$TMP"
echo "$STAMP" > "$OUT/SNAPSHOT_STAMP"
ls -la "$OUT"
rm -rf "$TMP"
