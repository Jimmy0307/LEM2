"""PR #6 publication guards; audit published summaries rather than rerunning raw OpenML.

Confirmatory runs were already performed. This suite independently verifies:
- paired primary hypotheses and 51/37 study provenance;
- exact arithmetic and direction of all reported external comparators;
- old source-name exclusions (not original-row-level de-duplication);
- preserved source manifests and caveats.
This is NOT independent execution of 10,710 raw-data tasks.
"""
from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "docs" / "research" / "redesign_20261116" / "data"
HISTORY = ROOT / "docs" / "research" / "teacher_dashboard" / "data" / "TEACHER_DATASET_MASTER_20261114.csv"
REPORT = ROOT / "docs" / "research" / "redesign_20261116" / "RESEARCH_REPORT_20261116.md"
SOURCE_NOTE = ROOT / "docs" / "research" / "redesign_20261116" / "SOURCE_INDEPENDENCE_REVIEW_20261116.md"
REGIMES = ("IID", "NONIID_05", "NONIID_01")


def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def near(a, b, tol=1e-10):
    return math.isclose(float(a), float(b), abs_tol=tol, rel_tol=tol)


def test_confirmation_manifest_and_preregistration():
    m = json.loads((D / "REDESIGN_G5_CONFIRMATORY_MANIFEST.json").read_text(encoding="utf-8"))
    a = json.loads((D / "G5_ANALYSIS_MANIFEST.json").read_text(encoding="utf-8"))
    assert (m["tasks"], m["succeeded"], m["failed"], m["sources"]) == (10710, 10710, 0, 51)
    assert (a["tasks_total"], a["tasks_failed"], a["datasets"]) == (10710, 0, 51)
    assert m["git_commit"] == a["git_commit"]
    assert m["preregistration"] == "docs/research/redesign_20261116/PREREGISTRATION_CONFIRMATORY_20261116.md"
    prereg = (ROOT / m["preregistration"]).read_text(encoding="utf-8")
    assert "M2" in prereg and "M0" in prereg and "1001" in prereg and "1010" in prereg
    # Documented commit ordering is not an independent proof of no earlier peeking.
    amendments = (ROOT / "docs/research/redesign_20261116/PREREGISTRATION_AMENDMENTS_20261116.md").read_text(encoding="utf-8")
    assert "2,200" in amendments and "float_precision" in amendments


def test_primary_claims_are_source_and_seed_paired():
    rows = read_csv(D / "G5_PRIMARY_HYPOTHESES.csv")
    assert len(rows) == 4
    assert Counter(x["hypothesis"] for x in rows) == {"H1": 3, "H2": 1}
    for x in rows:
        assert int(x["n_datasets"]) == 51
        assert int(x["n_paired_replicates"]) == 510
        assert int(x["min_replicates_per_unit"]) == 10
        assert int(x["wins"]) + int(x["ties"]) + int(x["losses"]) == 51
        assert near(float(x["mean_diff"]), float(x["mean_treatment"]) - float(x["mean_baseline"]))
        assert 0 < float(x["ci95_low"]) < float(x["ci95_high"])
        assert 0 < float(x["holm_p"]) < 0.05
        assert x["passed"] == "True"
    assert {(x["hypothesis"], x["regime"]) for x in rows} == {
        ("H1", "IID"), ("H1", "NONIID_05"), ("H1", "NONIID_01"), ("H2", "NONIID_01")
    }


def test_secondary_comparison_signs_match_arm_means():
    means = {x["regime"]: x for x in read_csv(D / "G5_ARM_MEANS.csv")}
    assert set(means) == set(REGIMES)
    secondaries = read_csv(D / "G5_SECONDARY_DESCRIPTIVE.csv")
    for regime in REGIMES:
        for other in ("R1", "C1", "C2"):
            matched = [x for x in secondaries if x["policy_method"] == "VALIDATION_BEST"
                       and x["regime"] == regime and x["baseline"] == "M2"
                       and x["treatment"] == other]
            assert len(matched) == 1, (regime, other)
            row = matched[0]
            assert near(row["mean_diff"], float(means[regime][other]) - float(means[regime]["M2"]))
            assert near(row["mean_baseline"], means[regime]["M2"])
            assert near(row["mean_treatment"], means[regime][other])
    # M2 minus C2: negative IID / alpha=.5, positive alpha=.1.
    assert (float(means["IID"]["M2"]) - float(means["IID"]["C2"])) < 0
    assert (float(means["NONIID_05"]["M2"]) - float(means["NONIID_05"]["C2"])) < 0
    assert (float(means["NONIID_01"]["M2"]) - float(means["NONIID_01"]["C2"])) > 0
    # M2 is lower on average than central R1 in all three regimes.
    assert all(float(means[r]["M2"]) < float(means[r]["R1"]) for r in REGIMES)


def test_report_has_corrected_direction_and_limitation():
    report = REPORT.read_text(encoding="utf-8")
    banned = (
        "M2 在 IID 甚至高 +1.77 pp",
        "M2 在 IID +3.27 pp",
        "M2 −0.84 pp",
        "相對集中式辨識切點參考**：不輸",
        "在 IID／α=0.5 輸給 M2",
    )
    for old in banned:
        assert old not in report, old
    for new in ("**−3.27 pp**", "**−2.08 pp**", "**+0.84 pp**",
                "**−1.77 pp**", "SOURCE_INDEPENDENCE_REVIEW_20261116.md",
                "未進行非劣性或等效檢定"):
        assert new in report, new


def test_source_registry_cross_check_is_name_level_only():
    previous = read_csv(HISTORY)
    current = read_csv(D / "CONFIRMATORY_SOURCE_REGISTRY.csv")
    assert len(previous) == 161 and len(current) == 112
    included = [x for x in current if x["status"] == "ELIGIBLE_PREPARED"]
    assert len(included) == 51
    assert len({x["family"] for x in included}) == 37
    assert len({int(x["did"]) for x in included}) == 51
    assert len({x["raw_sha256"] for x in included}) == 51
    assert len({x["prepared_sha256"] for x in included}) == 51
    for row in included:
        assert re.fullmatch(r"[0-9a-f]{64}", row["raw_sha256"])
        assert re.fullmatch(r"[0-9a-f]{64}", row["prepared_sha256"])
        assert int(float(row["prepared_rows"])) >= 20
    def norm(x):
        return re.sub(r"[^a-z0-9]", "", x.lower())
    known = {norm(v) for item in previous for v in (item["name"], item["domain_family"]) if v}
    exact = [row["name"] for row in included if norm(row["name"]) in known]
    assert exact == [], f"Overlapping previously registered dataset/family names: {exact}"
    note = SOURCE_NOTE.read_text(encoding="utf-8")
    for caution in ("Fashion-MNIST", "jungle_chess", "GesturePhaseSegmentationProcessed",
                    "不是原始列級去重", "37個來源家族"):
        assert caution in note, caution


def test_source_level_h1_sensitivity_remains_disclosed():
    family = read_csv(D / "G5_H1_FAMILY_SENSITIVITY.csv")
    assert len(family) == 3
    for row in family:
        assert int(row["n_datasets"]) == 37
        assert float(row["mean_diff"]) > 0
        assert float(row["holm_p"]) < 0.05


def test_website_published_csv_manifest_preserved():
    import hashlib
    manifest_path = ROOT / "docs/research/teacher_dashboard/data/redesign_20261116/REDESIGN_SITE_MANIFEST.json"
    site = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert not site.get("missing")
    for name, expected in site["published_sha256"].items():
        path = manifest_path.parent / name
        assert path.exists(), f"Missing published site evidence {name}"
        # Canonical = Git blob bytes (LF). Windows autocrlf checkouts hold CRLF; normalise line endings only.
        actual = hashlib.sha256(path.read_bytes().replace(bytes([13, 10]), bytes([10]))).hexdigest()
        assert actual == expected, (name, actual, expected)


def test_evidence_sha256_index_matches_every_research_file():
    from experiments.redesign_20261116.evidence_index import INDEX, verify
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    assert index["n_files"] == len(index["files"]) >= 90
    assert verify(index) == []


def test_independent_recomputation_reproduces_published_g5_tables():
    meta = json.loads((D / "G5_INDEPENDENT_RECOMPUTATION_20261116.json").read_text(encoding="utf-8"))
    assert meta["crosscheck_pass"] is True and meta["uses_fedrs_stats"] is False
    rows = read_csv(D / "G5_INDEPENDENT_RECOMPUTATION_20261116.csv")
    signed = {(x["comparison"], x["regime"]): round(100 * float(x["mean_diff"]), 2) for x in rows}
    assert signed[("H1", "IID")] == 6.09 and signed[("H1", "NONIID_05")] == 5.60
    assert signed[("H1", "NONIID_01")] == 4.33 and signed[("H2", "NONIID_01")] == 0.53
    assert signed[("SEC_M2_minus_R1", "IID")] == -1.77 and signed[("SEC_M2_minus_C2", "NONIID_01")] == 0.84
    assert signed[("SEC_M2_minus_C1", "NONIID_01")] == -7.22 and signed[("SEC_M2_minus_C2", "IID")] == -3.27


def test_posthoc_source_sensitivity_is_labelled_and_does_not_replace_primary():
    rows = read_csv(D / "G5_POSTHOC_SOURCE_SENSITIVITY_20261116.csv")
    assert {x["evidence_level"] for x in rows} == {"POST_HOC_SENSITIVITY_NOT_PREREGISTERED"}
    assert {x["posthoc_scenario"] for x in rows} == {"EXCLUDE_ADA_GINA", "EXCLUDE_ADA_GINA_SYLVINE"}
    primary = [x for x in rows if x["holm_family"]]
    assert all(x["passed_prereg_rule"] == "True" for x in primary)
    # preregistered table keeps all 51 sources
    assert all(int(x["n_datasets"]) == 51 for x in read_csv(D / "G5_PRIMARY_HYPOTHESES.csv"))
    audit = read_csv(D / "G5_SOURCE_METADATA_AUDIT_20261116.csv")
    verdict = {x["did"]: x["manual_verdict"] for x in audit}
    assert len(audit) == 51 and all(x["row_level_verified"] == "False" for x in audit)
    assert verdict["41156"].startswith("LIKELY_SHARED_UPSTREAM") and verdict["41158"].startswith("LIKELY_SHARED_UPSTREAM")
