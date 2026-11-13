"""Contract tests for leakage-free staged supplement selection and conflict metrics."""
import numpy as np
from teacher_demo.conflict_aware_coverage_pilot import EvalView,gate_select
from teacher_demo.supplementary_rule_coverage_pilot import Supplement


def projection(y,exact=None,original=None,cands=None):
    n=len(y)
    if exact is None:exact=[False]*n
    if original is None:original=["A"]*n
    if cands is None:cands=[set()]*n
    return {
      "n":n,"true":np.asarray(y,dtype=object),
      "exact":np.asarray(exact,dtype=bool),
      "pred":np.asarray(original,dtype=object),
      "candidates":cands
    }


def supp(label="B",purity=1.0,correct=9):
    return Supplement((("f","v"),),label,10,correct,purity,1)


def test_good_candidate_improves_validation_coverage_and_accuracy():
    p=projection(["A","B","B","B","A"],exact=[True,False,False,False,False],
                 cands=[{"A"},set(),set(),set(),set()])
    v=EvalView(p,[supp()],np.asarray([[False],[True],[True],[True],[False]],dtype=bool),"A")
    selected,base,allv,gated,events=gate_select(v)
    assert selected==[0]
    assert gated["coverage_pct"]>base["coverage_pct"]
    assert gated["accuracy_pct"]>base["accuracy_pct"]
    assert gated["active_conflict_count"]==0
    assert allv["accuracy_pct"]==gated["accuracy_pct"]
    assert events[0]["accepted"]


def test_validation_harm_is_rejected_even_if_coverage_increases():
    p=projection(["A"]*5)
    v=EvalView(p,[supp("B")],np.ones((5,1),dtype=bool),"A")
    selected,base,allv,gated,events=gate_select(v)
    assert selected==[]
    assert allv["coverage_pct"]==100
    assert allv["accuracy_pct"]<base["accuracy_pct"]
    assert gated["accuracy_pct"]==base["accuracy_pct"]
    assert not events[0]["accepted"]


def test_additional_rule_creating_conflict_but_no_new_coverage_is_rejected():
    p=projection(["B"]*5)
    a=supp("B",.98,12)
    b=supp("A",.99,13)
    v=EvalView(p,[a,b],np.ones((5,2),dtype=bool),"B")
    selected,base,allv,gated,events=gate_select(v)
    assert selected==[0],selected
    assert allv["active_conflict_pct"]==100
    assert gated["active_conflict_pct"]==0
    assert gated["accuracy_pct"]==100
    assert not events[1]["accepted"]


def test_active_vs_shadow_conflict_and_exact_rule_precedence():
    p=projection(["A"],exact=[True],original=["A"],cands=[{"A"}])
    v=EvalView(p,[supp("B")],np.ones((1,1),dtype=bool),"A")
    out=v.measure([0])
    assert out["coverage_pct"]==100
    assert out["active_conflict_pct"]==0
    assert out["shadow_conflict_pct"]==100
    assert out["accuracy_pct"]==100


def test_stratified_validation_choice_not_affected_by_test_labels():
    p=projection(["B","B","A"],exact=[False,False,False])
    cand=[supp("B")]
    mask=np.asarray([[True],[True],[False]],dtype=bool)
    selection=gate_select(EvalView(p,cand,mask,"A"))[0]
    test1=EvalView(projection(["A","A","B"]),cand,mask,"A").measure(selection)
    test2=EvalView(projection(["B","B","A"]),cand,mask,"A").measure(selection)
    assert selection==[0]
    assert test1["accuracy_pct"]!=test2["accuracy_pct"]
    # Test labels change metrics but cannot alter earlier selected rule IDs.


def test_class_label_longer_than_majority_not_truncated():
    p=projection(["unstable","stable"],original=["stable","stable"])
    v=EvalView(p,[supp("unstable")],np.asarray([[True],[False]]),"stable")
    out=v.measure([0])
    assert out["predictions"][0]=="unstable"
    assert out["accuracy_pct"]==100
