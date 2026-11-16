"""Publish finalization-audit tables to the dashboard data folder (additive only).

Copies the independent recomputation and post-hoc source-sensitivity outputs next to the
existing site CSVs and ADDS their LF-canonical SHA-256 to REDESIGN_SITE_MANIFEST.json.
Existing manifest entries are never rewritten; an existing entry with a different hash
aborts the run.

Usage: python -m experiments.redesign_20261116.publish_finalization_site_data
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .evidence_index import canonical_sha256

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "docs" / "research" / "redesign_20261116" / "data"
SITE = ROOT / "docs" / "research" / "teacher_dashboard" / "data" / "redesign_20261116"
FILES = ("G5_INDEPENDENT_RECOMPUTATION_20261116.csv", "G5_INDEPENDENT_RECOMPUTATION_20261116.json",
         "G5_POSTHOC_SOURCE_SENSITIVITY_20261116.csv")


def main() -> None:
    manifest_path = SITE / "REDESIGN_SITE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    published = manifest["published_sha256"]
    for name in FILES:
        src_hash = canonical_sha256(SRC / name)
        if name in published and published[name] != src_hash:
            raise RuntimeError(f"{name}: manifest already holds a different hash; refusing to overwrite")
        shutil.copyfile(SRC / name, SITE / name)
        if canonical_sha256(SITE / name) != src_hash:
            raise RuntimeError(f"{name}: copy hash mismatch")
        published[name] = src_hash
    manifest["finalization_additions_20261116"] = {
        "files": list(FILES),
        "hash": "sha256 of LF-normalised bytes (Git blob content)",
        "note": "Additive; earlier entries unchanged.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("published", *FILES)


if __name__ == "__main__":
    main()
