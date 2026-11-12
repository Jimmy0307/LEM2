"""Small deterministic tests for Train/Test coverage definitions and failure modes."""
from __future__ import annotations
import math
import pandas as pd
from roughset.core import Rule
from teacher_demo.train_test_coverage_audit import inspect_rows

def test_no_match_and_fallback_do_not_count_as_coverage():
    data=pd.DataFrame({"a":["red","blue","green"],"class":["A","B","A"]})
    rules=(Rule((("a","red"),),"A"),Rule((("a","blue"),),"B"))
    stat,classes,rows=inspect_rows(data,rules,"class",default_class="A")
    assert stat["rows"]==3
    assert stat["covered_count"]==2
    assert stat["no_match_count"]==1
    assert stat["no_match_default_correct_count"]==1
    assert stat["no_match_default_accuracy"]==1.0
    assert math.isclose(stat["coverage"],2/3)
    assert math.isclose(stat["true_candidate_rate"],2/3)
    assert stat["conflict_count"]==0
    assert rows[-1]["covered"]==0
    assert len(classes)==2

def test_conflicting_rule_matches_are_covered_but_not_necessarily_correct():
    data=pd.DataFrame({"a":["red","red","blue"],"class":["A","C","C"]})
    rules=(Rule((("a","red"),),"A"),Rule((("a","red"),),"B"))
    stat,by_class,rows=inspect_rows(data,rules,"class",default_class="C")
    assert stat["covered_count"]==2
    assert stat["conflict_count"]==2
    assert stat["true_candidate_count"]==1
    assert stat["no_match_default_correct_count"]==1
    assert by_class[0]["target_class"]=="A"
    assert rows[1]["true_candidate"]==0 and rows[1]["conflict"]==1

def test_empty_rule_set_does_not_imply_zero_predictive_accuracy():
    data=pd.DataFrame({"a":[1,2],"class":["X","X"]})
    stat,_,_=inspect_rows(data,[],"class",default_class="X")
    assert stat["coverage"]==0.0
    assert stat["no_match_count"]==2
    assert stat["no_match_default_correct_count"]==2
    assert stat["no_match_default_accuracy"]==1.0

if __name__=="__main__":
    test_no_match_and_fallback_do_not_count_as_coverage()
    test_conflicting_rule_matches_are_covered_but_not_necessarily_correct()
    test_empty_rule_set_does_not_imply_zero_predictive_accuracy()
    print("TRAIN_TEST_COVERAGE_CONTRACT_UNIT_PASS")
