from __future__ import annotations
import pandas as pd
from roughset.adapters import DatasetBundle
from roughset.schema import DatasetSchema
from roughset.paper import run_paper_protocol


def test_paper_protocol_runs_on_small_deterministic_table():
    df=pd.DataFrame({
        'A':[0,0,0,0,1,1,1,1],
        'B':[0,1,0,1,0,1,0,1],
        'class':['N','N','N','N','Y','Y','Y','Y'],
    })
    schema=DatasetSchema(target='class',features=['A','B'],categorical=['A','B'])
    bundle=DatasetBundle('demo',df,['A','B'],'class',schema,'local:demo')
    out=run_paper_protocol(bundle,cv_folds=2,seed=42)
    assert out['reduct']==['A']
    assert out['full_data_rule_count']==2
    assert out['accuracy']==1.0
    assert out['prediction_policy']=='GLOBAL_STRENGTH'
