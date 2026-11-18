"""Reconcile PR #6 website evidence hashes after CRLF -> LF Git normalization.

The original Windows generated manifest hashed files before git converted their
CRLF line endings to canonical LF Git blob bytes. These files are identical to
the research data copies, but published SHA256 incorrectly reflects CRLF.

Default: audit only; --apply changes *only* website manifest, never any CSV,
original experiment, preregistration or primary analyses.
Raise for ANY unexpected data or non-line-ending hash discrepancy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "docs/research/redesign_20261116/data"
SITE = ROOT / "docs/research/teacher_dashboard/data/redesign_20261116"
MANIFEST = SITE / "REDESIGN_SITE_MANIFEST.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main(apply: bool = False):
    obj = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = obj["published_sha256"]
    assert expected and len(expected) >= 20
    assert not obj.get("missing"), "Site publisher reports missing CSVs"
    new_hashes = {}
    normalized = []
    for name, old_hash in expected.items():
        assert name.endswith(".csv") and "/" not in name and "\\" not in name, name
        site_data = (SITE / name).read_bytes()
        raw_data = (RAW / name).read_bytes()
        assert site_data == raw_data, f"Actual site vs original research CSV mismatch: {name}"
        current_hash = digest(site_data)
        if current_hash != old_hash:
            # Refuse any unexplained mismatch. Published Git blobs have LF endings;
            # old Windows SHA was calculated on pre-commit CRLF working-copy bytes.
            assert b"\r\n" not in site_data, f"Unexpected CRLF in published Git blob: {name}"
            normalized_crlf = site_data.replace(b"\n", b"\r\n")
            assert digest(normalized_crlf) == old_hash, (
                f"Non-line-ending hash mismatch {name}: "
                f"git_sha256={current_hash} manifest={old_hash}")
            normalized.append(name)
        new_hashes[name] = current_hash
    print("PUBLICATION_INTEGRITY",len(expected),"files, CRLF_TO_LF_CONVERSION",len(normalized),
          "all research copies byte-identical",flush=True)
    if apply and normalized:
        obj["published_sha256"] = new_hashes
        obj["integrity_reconciliation"] = {
            "reason": "Windows pre-commit CRLF hashes differ from Git-hosted LF blob bytes",
            "audit_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git_head_when_reconciled": os.environ.get("GITHUB_SHA", "LOCAL"),
            "files_rehashed_after_git_line_ending_normalization": len(normalized),
            "policy": "Published SHA256 is hash of actual Git blob/site CSV bytes, not precommit Windows bytes",
            "research_csv_and_primary_experiments_modified": False,
        }
        MANIFEST.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        assert all(digest((SITE / name).read_bytes()) == sha for name,sha in new_hashes.items())
        print("PUBLICATION_MANIFEST_REHASHED_TO_ACTUAL_PUBLISHED_BYTES_PASS",flush=True)
    elif not apply:
        assert not normalized, "Site manifest has CRLF-vs-Git-LF hash mismatch; run --apply in audited CI"
    return len(normalized)


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--apply",action="store_true",help="Recompute only hashes already proven CRLF conversion")
    a=p.parse_args()
    main(apply=a.apply)
