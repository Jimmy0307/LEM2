from fedrs.predict import POLICIES
from teacher_demo.conflict_aware_coverage_pilot import load_bundle
from experiments.full_scale_20261118.model import run_model
from experiments.full_scale_20261118.sources import Source
import pandas as pd
import pytest


def test_iris_central_model_has_twelve_valid_policy_rows():
    b, _ = load_bundle("iris")
    src = Source(b.frame, list(b.features), b.target, list(b.schema.continuous),
                 list(b.schema.categorical), "", "", len(b.frame), len(b.features), list(b.features), {}, "")
    result = run_model(src, "UCI20:iris", 1001, "CENTRALIZED")
    assert len(result["rows"]) == 12
    for variant in ("A_ALL_RULES", "B2_TRUE_AS_FALLBACK"):
        rows = [r for r in result["rows"] if r["rule_variant"] == variant]
        assert {r["selection_policy"] for r in rows} == set(POLICIES)
        assert all(r["covered_count"] + r["no_match_count"] == r["test_rows"] for r in rows)
        assert all(r["true_in_candidate_count"] <= r["covered_count"] for r in rows)
        assert max(r["accuracy_pct"] for r in rows) - min(r["accuracy_pct"] for r in rows) <= rows[0]["conflict_rate_pct"] + 1e-6


def test_seed_specific_type_conflict_with_missing_treatment_is_reported():
    frame = pd.DataFrame({"f0": list(range(10))*12 + [10], "class": ["a", "b"]*60 + ["a"]})
    src = Source(frame, ["f0"], "class", [], [], "", "", 122, 1, ["x"], {}, "", True)
    src.missing_treatments = {"f0": "DROP_NUMERIC"}
    with pytest.raises(ValueError, match="FEATURE_MISSING_TYPE_MISMATCH"):
        run_model(src, "PMLB:test", 1001, "CENTRALIZED")
