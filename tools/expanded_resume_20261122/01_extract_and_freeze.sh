#!/usr/bin/env bash
# Extract the 3566580 checkpoint into a fresh WSL run directory and freeze
# byte-identical copies of the original manifest and source records.
set -euo pipefail
ZIP_SRC=/mnt/d/Desk/LEM2_188datasets_42seeds_INCOMPLETE_checkpoint.zip
ROOT="$HOME/lem2_runs"
RUN="$ROOT/expanded_188_42seeds"
PY="$HOME/lem2_venv/bin/python"

mkdir -p "$ROOT"
if [ -e "$RUN" ]; then echo "Refusing: $RUN already exists" >&2; exit 1; fi

cp "$ZIP_SRC" "$ROOT/ORIGINAL_CHECKPOINT_3566580.zip"
sha256sum "$ZIP_SRC" "$ROOT/ORIGINAL_CHECKPOINT_3566580.zip"

mkdir -p "$RUN"
cd "$RUN"
"$PY" -I -m zipfile -e "$ROOT/ORIGINAL_CHECKPOINT_3566580.zip" .

mkdir -p ORIGINAL_3566580/source_records
for f in RUN_MANIFEST.json STATUS.json COMPLETENESS.csv MISSING.csv FAILURES.csv READ_ME.md SOURCE_REGISTRY.csv; do
  cp -p "$f" ORIGINAL_3566580/
done
for d in checkpoints/*/; do
  name="$(basename "$d")"
  if [ -f "$d/SOURCE.json" ]; then
    mkdir -p "ORIGINAL_3566580/source_records/$name"
    cp -p "$d/SOURCE.json" "ORIGINAL_3566580/source_records/$name/"
  fi
done
(cd ORIGINAL_3566580 && find . -type f | sort | xargs sha256sum) > "$ROOT/ORIGINAL_3566580.sha256"
chmod -R a-w ORIGINAL_3566580 "$ROOT/ORIGINAL_CHECKPOINT_3566580.zip"

echo "frozen_files=$(wc -l < "$ROOT/ORIGINAL_3566580.sha256")"
echo "model_checkpoints=$(find checkpoints -name 'seed*.json' | wc -l)"
echo "dataset_dirs=$(ls checkpoints | wc -l)"
