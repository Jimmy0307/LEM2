"""Audit grouped Hayes-Roth splits for exact train/test disjointness and diversity."""
import hashlib
from pathlib import Path
import pandas as pd
from teacher_demo.teacher_hayes_remediation import source_bundle,grouped_partition

def main():
    bundle=source_bundle();records=[]
    for seed in range(1,43):
        train,test=grouped_partition(bundle,seed)
        a=set(map(tuple,train[bundle.features].astype(str).to_numpy()))
        b=set(map(tuple,test[bundle.features].astype(str).to_numpy()))
        assert not(a&b)
        h=hashlib.sha256(",".join(str(i) for i in sorted(test["__row_id__"])).encode()).hexdigest()
        records.append({"seed":seed,"test_fingerprint":h,"train_n":len(train),"test_n":len(test),
                        "n_test_classes":test[bundle.target].nunique(),
                        "feature_overlap_with_train":len(a&b)})
    df=pd.DataFrame(records)
    root=Path("docs/research/teacher_dashboard/data");root.mkdir(parents=True,exist_ok=True)
    df.to_csv(root/"HAYES_GROUP_SPLIT_AUDIT_42SEEDS.csv",index=False)
    print("GROUP_SPLIT_UNIQUE=",df.test_fingerprint.nunique(),"OF",len(df),flush=True)
    print("GROUP_SPLIT_DISJOINT_VERDICT=PASS",flush=True)
if __name__=="__main__":main()
