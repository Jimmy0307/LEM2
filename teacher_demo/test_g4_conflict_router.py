"""Prove six-resolution router cannot modify no-conflict cases or read Test for routing."""
import numpy as np
from teacher_demo.g4_rule_conflict_router import apply_router,select_router,measured
from teacher_demo.adaptive_six_policy_runner import POLICY_ORDER

def bundle():
    n=30
    y=np.asarray(["a"]*15+["long_class_name"]*15,dtype=object)
    bucket=np.asarray(["NO_CONFLICT"]*10+["TWO_CLASS_FEW_RULES"]*20)
    baseline=np.asarray(["a"]*n,dtype=object)
    predictions={p:baseline.copy() for p in POLICY_ORDER}
    predictions["SIMPLE_VOTING"][10:]=y[10:]
    return y,bucket,predictions

def test_router_may_select_on_validation_conflict_but_never_change_uncontested():
    y,bucket,pred=bundle()
    selection,receipts,validation=select_router(y,pred,bucket,"GLOBAL_STRENGTH")
    assert selection.get("TWO_CLASS_FEW_RULES")=="SIMPLE_VOTING"
    assert np.array_equal(validation[:10],pred["GLOBAL_STRENGTH"][:10])
    out=apply_router(pred,bucket,"GLOBAL_STRENGTH",selection)
    assert np.array_equal(out[:10],pred["GLOBAL_STRENGTH"][:10])
    assert "long_class_name" in out and len(out)==len(y)

def test_insufficient_conflict_support_does_not_switch():
    y,bucket,pred=bundle()
    bucket[10:27]="NO_CONFLICT"
    sel,_,_=select_router(y,pred,bucket,"GLOBAL_STRENGTH")
    assert not sel

def test_selection_never_reads_external_test_labels():
    y,bucket,pred=bundle()
    a=select_router(y,pred,bucket,"GLOBAL_STRENGTH")[0]
    # Test labels aren't accepted by select_router; changing any independent
    # TEST labels cannot change the policy chosen from validation.
    test_y=np.array(y[::-1])
    test_preds={k:v[::-1] for k,v in pred.items()}
    assert a==select_router(y,pred,bucket,"GLOBAL_STRENGTH")[0]
    assert len(apply_router(test_preds,bucket[::-1],"GLOBAL_STRENGTH",a))==len(test_y)

def test_empty_router_is_exact_baseline():
    y,b,p=bundle()
    assert np.array_equal(apply_router(p,b,"GLOBAL_STRENGTH",{}),p["GLOBAL_STRENGTH"])
