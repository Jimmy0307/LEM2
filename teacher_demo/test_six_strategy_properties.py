"""Executable G7 structural invariants, not claims of new theoretical novelty."""
import numpy as np
import pandas as pd

from roughset.core import Rule
from roughset.evaluation import (
    matching_rules,predict_with_policy,predict_table,
)
from teacher_demo.full_factorial_matrix import POLICIES

RULES=[
    Rule((("x","A"),),"yes"),
    Rule((("x","A"),),"no"),
    Rule((("x","B"),),"yes"),
    Rule((("x","D"),),"no"),
    Rule((("x","D"),),"yes"),
]
TABLE=pd.DataFrame({"x":["A","B","C","D","C","B","D","A"],
                    "class":["no","no","yes","yes","yes","yes","no","yes"]})
SUPPORT={r.key:{i} for i,r in enumerate(RULES)}
WEIGHTS={r.key:float(i+2) for i,r in enumerate(RULES)}
CLASS_COUNTS={"yes":20,"no":20}

def predict(policy):
    labels=[]
    for _,row in TABLE.iterrows():
        p,_=predict_with_policy(row,RULES,"yes",policy=policy,
                               rule_weights=WEIGHTS,
                               rule_support_sets=SUPPORT,class_sizes=CLASS_COUNTS)
        labels.append(str(p))
    return np.asarray(labels,dtype=object)

def structural():
    matched=[matching_rules(row,RULES) for _,row in TABLE.iterrows()]
    covered=np.array([bool(m) for m in matched])
    conflict=np.array([len({str(r.decision) for r in m})>1 for m in matched])
    true_candidate=np.array([str(y) in {str(r.decision) for r in m}
                             for y,m in zip(TABLE["class"],matched)])
    return matched,covered,conflict,true_candidate

def test_all_six_have_invariant_exact_coverage_and_conflict_definition():
    matches,covered,conflict,_=structural()
    assert len(POLICIES)==6
    for policy in POLICIES:
        got=predict(policy)
        assert len(got)==len(TABLE)
        assert np.array_equal(covered,np.array([bool(m) for m in matches]))
        assert np.array_equal(conflict,np.array([
            len({str(r.decision) for r in m})>1 for m in matches
        ]))
    assert int(covered.sum())==6
    assert int(conflict.sum())==4

def test_six_policy_disagreement_occurs_only_on_multi_decision_conflict():
    _,_,conflict,_=structural()
    preds={p:predict(p) for p in POLICIES}
    for p in POLICIES:
        for q in POLICIES:
            disagree=preds[p]!=preds[q]
            assert np.all(~disagree | conflict),(p,q,disagree,conflict)
            assert np.mean(disagree)<=np.mean(conflict)+1e-12
            acc_p=np.mean(preds[p]==TABLE["class"].to_numpy())
            acc_q=np.mean(preds[q]==TABLE["class"].to_numpy())
            assert abs(acc_p-acc_q)<=np.mean(conflict)+1e-12

def test_no_matching_rule_or_wrong_only_candidates_cannot_be_repaired_by_voting():
    matched,covered,conflict,true_candidate=structural()
    # C: all six policies return the same Train-majority fallback, not a
    # formal reject; B: only 'yes' rule fires, even when truth is 'no'.
    for ix in [2,4]:
        assert not matched[ix]
        assert all(predict(p)[ix]=="yes" for p in POLICIES)
    assert matched[1] and TABLE.loc[1,"class"]=="no" and not true_candidate[1]
    assert all(predict(p)[1]=="yes" for p in POLICIES)

def test_accuracy_bound_by_candidate_union_plus_fallback_correct_cases():
    matched,covered,conflict,true_candidate=structural()
    correct_on_nomatch=int(sum(
       (not bool(matched[i])) and TABLE.loc[i,"class"]=="yes"
       for i in range(len(TABLE))))
    bound=(true_candidate.sum()+correct_on_nomatch)/len(TABLE)
    for p in POLICIES:
        score=np.mean(predict(p)==TABLE["class"].to_numpy())
        assert score<=bound+1e-12
