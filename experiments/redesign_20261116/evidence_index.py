"""Checkout-independent SHA-256 index of every redesign research evidence file.

Why: CSVs were written on Windows (CRLF) and committed with core.autocrlf=true, so Git
stores LF. A raw-byte SHA therefore differs between a Windows checkout and Linux CI.
The canonical hash here is SHA-256 of the file with CRLF normalised to LF, which equals
the bytes stored in the Git blob. Only line endings are normalised; any other byte change
fails verification.

Usage:
  python -m experiments.redesign_20261116.evidence_index --write   # (re)build index
  python -m experiments.redesign_20261116.evidence_index           # verify, exit 1 on mismatch
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "docs" / "research" / "redesign_20261116" / "RESEARCH_DATA_SHA256_INDEX_20261116.json"
SCOPES = (
    "docs/research/redesign_20261116/data",
    "docs/research/teacher_dashboard/data/redesign_20261116",
)
TEXT_SUFFIXES = {".csv", ".json", ".md", ".html", ".txt"}


def canonical_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    return data.replace(b"\r\n", b"\n") if path.suffix.lower() in TEXT_SUFFIXES else data


def canonical_sha256(path: Path) -> str:
    return hashlib.sha256(canonical_bytes(path)).hexdigest()


def collect() -> dict[str, dict]:
    files = {}
    for scope in SCOPES:
        for path in sorted((ROOT / scope).rglob("*")):
            if path.is_file():
                rel = path.relative_to(ROOT).as_posix()
                files[rel] = {"sha256_lf": canonical_sha256(path), "bytes_lf": len(canonical_bytes(path))}
    return files


def verify(index: dict) -> list[str]:
    errors = []
    current = collect()
    for rel, meta in index["files"].items():
        if rel not in current:
            errors.append(f"MISSING {rel}")
        elif current[rel]["sha256_lf"] != meta["sha256_lf"]:
            errors.append(f"CHANGED {rel}")
    errors += [f"UNINDEXED {rel}" for rel in current if rel not in index["files"]]
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Redesign evidence SHA-256 index")
    parser.add_argument("--write", action="store_true", help="rebuild the index instead of verifying")
    args = parser.parse_args(argv)
    if args.write:
        files = collect()
        INDEX.write_text(json.dumps({
            "hash": "sha256 of file bytes with CRLF->LF (equals Git blob content for text files)",
            "scopes": list(SCOPES), "n_files": len(files),
            "total_bytes_lf": sum(x["bytes_lf"] for x in files.values()), "files": files,
        }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {INDEX.relative_to(ROOT)} ({len(files)} files)")
        return 0
    errors = verify(json.loads(INDEX.read_text(encoding="utf-8")))
    print("EVIDENCE_INDEX", "PASS" if not errors else "FAIL", *errors[:50], sep="\n")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
