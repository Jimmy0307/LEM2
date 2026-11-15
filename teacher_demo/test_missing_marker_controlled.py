"""B treatment guards: never learn replacement from Validation/Test."""
from __future__ import annotations
import numpy as np
import pandas as pd
from roughset.adapters import DatasetBundle
from roughset.schema import DatasetSchema
from teacher_demo.missing_marker_controlled_runner import transform,identify

def baseline_fixture():
    f=["age","workclass"]
    raw=pd.DataFrame({"age":[20,30,50,60,45,53],"workclass":["?","A","A","B","?","C"],"class":["x","y","x","y","x","y"]})
    schema=DatasetSchema(target="class",features=f,continuous=["age"],categorical=["workclass"])
    b=DatasetBundle("toy",raw,f,"class",schema,"fixture")
    train=raw.iloc[:4].copy();val=raw.iloc[[4]].copy();test=raw.iloc[[5]].copy()
    return b,train,val,test
def test_only_training_mode_used_and_test_label_unchanged():
    b,d,v,t=baseline_fixture()
    b1,x,y,z,markers,choices=transform(b,d,v,t,"TRAIN_MODE")
    assert choices["workclass"]=="A"
    assert x.iloc[0]["workclass"]=="A"
    assert y.iloc[0]["workclass"]=="A"
    assert z.iloc[0]["workclass"]=="C"
    assert z.iloc[0]["class"]==t.iloc[0]["class"]
    assert markers["workclass"]==2
    assert b1.features==b.features
def test_missing_as_feature_adds_only_train_observable_indicators():
    b,d,v,t=baseline_fixture()
    b1,x,y,z,_,_=transform(b,d,v,t,"INDICATOR")
    assert len(b1.features)==3
    assert "workclass__was_missing" in b1.schema.categorical
    assert x["workclass__was_missing"].tolist()==["1","0","0","0"]
    assert y["workclass__was_missing"].tolist()==["1"]
    assert z["workclass__was_missing"].tolist()==["0"]
    assert x["workclass"].tolist()==d["workclass"].tolist()
def test_preserve_baseline_does_not_change_dataframe():
    b,d,v,t=baseline_fixture()
    b1,x,y,z,_,_=transform(b,d,v,t,"PRESERVE")
    assert x.equals(d) and y.equals(v) and z.equals(t)
    assert b1.features==b.features
def test_unknown_string_is_not_automatically_missing():
    df=pd.DataFrame({"a":["unknown","?","N/A","",None,"__MISSING_FEATURE__"]})
    assert identify(df,["a"])["a"]==5
