"""Metadata-level source-independence audit of the 51 confirmatory OpenML sources (finalization).

Post-hoc, descriptive only. It NEVER changes the preregistered 51-source sample.
For each confirmatory source it records OpenML metadata (upstream URL, citation, creator,
collection date) and screens the 161 historical sources by
  (a) shared upstream URL host+path tokens,
  (b) identical shape signature (original rows, original features, classes),
  (c) normalised-name containment (already reported in SOURCE_INDEPENDENCE_REVIEW).
A screen hit is a lead for manual review, not proof of shared rows; absence of a hit is not
proof of independence (no row-level fingerprinting is done here).

Outputs: data/G5_SOURCE_METADATA_AUDIT_20261116.csv (+ _FAILURES.csv for unreachable metadata)
Usage:   python -m experiments.redesign_20261116.source_metadata_audit
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "research" / "redesign_20261116" / "data"
HISTORY = ROOT / "docs" / "research" / "teacher_dashboard" / "data" / "TEACHER_DATASET_MASTER_20261114.csv"
OUT = DATA / "G5_SOURCE_METADATA_AUDIT_20261116.csv"
FAIL = DATA / "G5_SOURCE_METADATA_AUDIT_20261116_FAILURES.csv"
API = "https://www.openml.org/api/v1/json/data/{did}"
HEADERS = {"User-Agent": "research-provenance-audit/1.0"}
FIELDS = ("original_data_url", "citation", "creator", "collection_date", "upload_date", "paper_url", "default_target_attribute")
# Manual adjudication (finalization audit, 2026-11-16). Evidence is literature/metadata, not row matching.
MANUAL = {
    41156: ("LIKELY_SHARED_UPSTREAM_ADULT",
            "ALvsPK challenge (Guyon 2007): ADA is the agnostic version of UCI Adult; OpenML 41156 has the same "
            "48-feature representation as ada_agnostic (OpenML 1043; 4562 rows vs 4147 here). Historical: adult (PMLB), Adult Income (UCI)."),
    41158: ("LIKELY_SHARED_UPSTREAM_MNIST",
            "ALvsPK: GINA is an agnostic subset of MNIST (odd vs even two-digit numbers); same 970-feature representation "
            "as gina_agnostic (OpenML 1038; 3468 rows vs 3153 here). Historical: mnist (PMLB)."),
    41146: ("UNVERIFIED_LEAD_COVERTYPE",
            "ALvsPK SYLVA is a forest-cover task; whether AutoML 'sylvine' (21 features) derives from it or from UCI "
            "Covertype could not be confirmed (Guyon et al. 2019 dataset table not accessible). Historical: Covertype (UCI)."),
    40996: ("DISTINCT_SAME_SHAPE",
            "Fashion-MNIST (Zalando product images) is a drop-in replacement with MNIST's shape (70000x784x10); different images."),
    1478: ("DISTINCT_NAME_ARTEFACT", "'har' substring of 'character' in Letter Recognition; HAR is smartphone activity data."),
    41027: ("DISTINCT_NO_EVIDENCE", "Jungle chess endgame tables vs PMLB chess (King-Rook vs King-Pawn); different games."),
    4538: ("DISTINCT_NO_EVIDENCE", "Gesture phase segmentation vs Statlog image segmentation; only the word 'segmentation' is shared."),
}
STOP = {"https", "http", "www", "org", "com", "edu", "html", "php", "index", "datasets", "dataset", "data", "ml",
        "archive", "ics", "uci", "machine", "learning", "databases", "openml", "github", "tree", "blob", "the", "and"}


def fetch(did: int, retries: int = 3) -> dict:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(API.format(did=did), headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))["data_set_description"]
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"metadata unavailable for did={did}: {last!r}")


def tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", str(text).lower()) if len(t) >= 4 and t not in STOP and not t.isdigit()}


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def main() -> None:
    reg = pd.read_csv(DATA / "CONFIRMATORY_SOURCE_REGISTRY.csv")
    inc = reg[reg.status == "ELIGIBLE_PREPARED"]
    hist = pd.read_csv(HISTORY)
    hist_url_tokens = {r.id: tokens(r.source_url) for r in hist.itertuples()}
    hist_shape = {(int(r.original_rows), int(r.original_features), int(r.classes)): r.id
                  for r in hist.itertuples()
                  if pd.notna(r.original_rows) and pd.notna(r.original_features) and pd.notna(r.classes)}
    hist_names = {r.id: {norm(r.name), norm(r.domain_family), norm(r.id)} - {""} for r in hist.itertuples()}
    rows, failures = [], []
    for r in inc.itertuples():
        try:
            meta = fetch(int(r.did))
        except RuntimeError as exc:
            failures.append({"did": int(r.did), "name": r.name, "error": str(exc)})
            meta = {}
        up = meta.get("original_data_url", "") or ""
        up_tok = tokens(up)
        url_hits = sorted(h for h, t in hist_url_tokens.items() if up_tok and len(up_tok & t) >= 2)
        shape = (int(r.openml_rows), int(r.openml_features) - 1, int(r.openml_classes))
        shape_hit = hist_shape.get(shape, "")
        n = norm(r.name)
        name_hits = sorted(h for h, ns in hist_names.items() if any(len(x) >= 5 and (x in n or n in x) for x in ns))
        rows.append({"did": int(r.did), "name": r.name, "family": r.family,
                     **{f: str(meta.get(f, ""))[:400] for f in FIELDS},
                     "metadata_fetched": bool(meta), "upstream_url_token_hits": ";".join(url_hits),
                     "shape_signature": f"{shape[0]}x{shape[1]}x{shape[2]}", "shape_signature_hit": shape_hit,
                     "name_containment_hits": ";".join(name_hits),
                     "screen_flag": bool(url_hits or shape_hit or name_hits),
                     "verdict": "LEAD_FOR_MANUAL_REVIEW" if (url_hits or shape_hit or name_hits) else "NO_METADATA_LEAD",
                     "manual_verdict": MANUAL.get(int(r.did), ("", ""))[0],
                     "manual_evidence": MANUAL.get(int(r.did), ("", ""))[1],
                     "row_level_verified": False})
        time.sleep(0.3)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    pd.DataFrame(failures, columns=["did", "name", "error"]).to_csv(FAIL, index=False)
    df = pd.DataFrame(rows)
    print(df[["did", "name", "upstream_url_token_hits", "shape_signature_hit", "name_containment_hits"]][df.screen_flag].to_string())
    print(f"fetched={int(df.metadata_fetched.sum())}/{len(df)} flagged={int(df.screen_flag.sum())} failures={len(failures)}")


if __name__ == "__main__":
    main()
