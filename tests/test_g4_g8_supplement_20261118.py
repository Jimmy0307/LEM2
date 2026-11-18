"""Coverage intervention tests: no test-label use in supplement fitting."""
from __future__ import annotations

from fedrs.experiment import fit_model, nested_split
from fedrs.noise import synthetic_table
from fedrs.partition import original_partition
from fedrs.supplement_exploratory import build_supplements, supplement_test


def fitted():
    df=synthetic_table(360, "balanced", 41)
    dev,val,test=nested_split(df,"class",5)
    cl=original_partition(dev,"class",3,5,"IID")
    return fit_model(["x1","x2","x3","c1","c2"],["x1","x2","x3"],["c1","c2"],
                     "class",cl,dev,val,test,"EQUAL_WIDTH_3")


def test_supplement_candidates_depend_only_on_development_client_tables():
    fm=fitted()
    a=build_supplements(fm,min_support=5,min_purity=.9)
    old=fm.frames["test"]["class"].copy()
    # Replacing ALL test labels must not change supplement generation.
    fm.frames["test"]["class"]="artificial_test_only_label"
    b=build_supplements(fm,min_support=5,min_purity=.9)
    assert a == b
    fm.frames["test"]["class"]=old


def test_augmented_strict_coverage_not_lower_and_original_rules_preserved():
    fm=fitted()
    old=tuple(r.key for r in fm.rules)
    result=supplement_test(fm,min_support=5,min_purity=.9)
    assert result["augmented_strict_coverage"] >= result["strict_nonempty_coverage"]
    assert result["supplement_rescued"] >= 0
    assert result["explicit_abstain_if_not_accepted"] == (
        1 - result["augmented_strict_coverage"]
    )
    assert tuple(r.key for r in fm.rules)==old
    assert -100 <= result["test_ba_gain_pp"] <= 100


def test_invalid_thresholds_refused():
    fm=fitted()
    for kwargs in ({"min_support":0},{"min_purity":0.0},
                   {"min_purity":1.1},{"cap":0}):
        try:
            build_supplements(fm,**kwargs)
        except ValueError:
            continue
        raise AssertionError("Bad supplement threshold accepted")
