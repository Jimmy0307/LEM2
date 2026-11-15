"""Unit/contract tests for experimental continuous discretization and guard."""
from __future__ import annotations
import numpy as np
import pandas as pd
import pytest
from roughset.preprocessing import fit_shared_preprocessor,apply_preprocessor
from teacher_demo.continuous_binning_methods import MODES,fit_mode
from teacher_demo.continuous_controlled_runner import guard_select,GUARDS
from teacher_demo.g4_rule_conflict_router import select_router,apply_router
from teacher_demo.adaptive_six_policy_runner import POLICY_ORDER

def training():
    return pd.DataFrame({"x":[0,0,0,1,2,3,7,8,9,100,101,102],
       "y":[0,1,0,1,0,1,0,1,0,1,0,1],"cat":["a"]*6+["b"]*6,
       "class":["n","n","y","y","n","y","n","y","n","y","n","y"]})
def test_equal_width_3_matches_frozen_canonical():
    df=training()
    original=fit_shared_preprocessor({"c1":df},"x y cat".split(),"class",
            ["x","y"],["cat"],3)
    newer=fit_mode({"c1":df},"x y cat".split(),"class",
            ["x","y"],["cat"],3,mode="EQUAL_WIDTH_3")
    for x in ("x","y"):
        assert np.array_equal(original["bin_edges"][x],newer["bin_edges"][x])
        assert original["bin_labels"][x]==newer["bin_labels"][x]
    assert apply_preprocessor(df,original,"class").equals(apply_preprocessor(df,newer,"class"))
@pytest.mark.parametrize("mode",tuple(MODES))
def test_all_strategies_fit_only_training_and_bounds_are_legal(mode):
    tr=training();test=tr.iloc[[0,9]].copy()
    test.loc[test.index[0],"x"]=-100000
    test.loc[test.index[1],"x"]=1000000
    result=fit_mode({"c1":tr.iloc[:6],"c2":tr.iloc[6:]},"x y cat".split(),
      "class",["x","y"],["cat"],3,mode=mode)
    for x in ("x","y"):
        edges=result["bin_edges"][x]
        assert np.isfinite(edges).all() and np.all(np.diff(edges)>0)
        assert len(result["bin_labels"][x])==len(edges)-1
    assert apply_preprocessor(test,result,"class")[["x_bin","y_bin"]].notna().all().all()
    assert result["features"]==["x","y","cat"]
def test_quantiles_collapse_on_ties_without_invalid_duplicate_edges():
    tr=pd.DataFrame({"x":[0]*95+[10]*5,"class":["a"]*50+["b"]*50})
    q=fit_mode({"a":tr},["x"],"class",["x"],[],3,mode="EQUAL_FREQUENCY_5")
    assert np.all(np.diff(q["bin_edges"]["x"])>0)
    assert len(q["bin_labels"]["x"])==len(q["bin_edges"]["x"])-1
def test_absurd_test_outlier_does_not_change_dev_edges():
    dev=training()
    original=fit_mode({"c":dev},["x"],"class",["x"],[],3,mode="EQUAL_FREQUENCY_3")
    test=pd.DataFrame({"x":[1e12],"class":["n"]})
    after=apply_preprocessor(test,original,"class")
    assert len(original["bin_edges"]["x"])<=4
    assert after["x_bin"].notna().all()
    assert original["bin_edges"]["x"][-1]==102
def test_router_original_guard_parity_and_no_conflict_changes():
    y=np.asarray(["a"]*12+["b"]*12,dtype=object)
    buckets=np.asarray(["NO_CONFLICT"]*8+["TWO_CLASS_FEW_RULES"]*16,dtype=object)
    predictions={p:np.asarray(["a"]*24,dtype=object) for p in POLICY_ORDER}
    predictions["GLOBAL_STRENGTH"][8:]=y[8:]
    chosen,val=guard_select(y,predictions,buckets,"SIMPLE_VOTING",GUARDS["ORIGINAL_G4"])
    legacy,_,v=select_router(y,predictions,buckets,"SIMPLE_VOTING")
    assert chosen==legacy and np.array_equal(val,v)
    out=apply_router(predictions,buckets,"SIMPLE_VOTING",chosen)
    assert np.array_equal(out[:8],predictions["SIMPLE_VOTING"][:8])
def test_guard_noswitch_baseline():
    y=np.asarray(["a"]*10+["b"]*10,dtype=object)
    buckets=np.asarray(["TWO_CLASS_FEW_RULES"]*20)
    preds={p:y.copy() for p in POLICY_ORDER}
    preds["SIMPLE_VOTING"][:]=["a"]*20
    which,p=guard_select(y,preds,buckets,"SIMPLE_VOTING",GUARDS["GUARD_NOSWITCH"])
    assert not which and np.array_equal(p,preds["SIMPLE_VOTING"])
