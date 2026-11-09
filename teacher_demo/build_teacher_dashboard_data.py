"""Build GitHub Pages evidence JSON only from the verified canonical 42-seed CSV."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

SOURCE=Path("docs/research/seed_sweep_1_42/tables/SEED_SWEEP_8820.csv")
OUTPUT=Path("docs/research/teacher_dashboard/data/baseline_8820.json")
KEY=["dataset","seed","split_mode","system","client_count","selection_policy"]
COLS=KEY+["rule_count","coverage","conflict_case_rate","true_in_candidate_rate",
          "accuracy","balanced_accuracy","macro_f1"]
POLICIES={"NONE","FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING",
          "GLOBAL_STRENGTH","POPULATION_STANDARD","POPULATION_GLOBAL"}
def main():
    df=pd.read_csv(SOURCE)
    assert len(df)==8820 and not df.duplicated(KEY).any()
    assert set(df.seed)==set(range(1,43))
    assert set(df.selection_policy)==POLICIES
    for seed,g in df.groupby("seed"):
        assert len(g)==210,(seed,len(g))
        assert int((g.selection_policy=="NONE").sum())==30
        assert int((g.selection_policy!="NONE").sum())==180
    assert df[df.selection_policy=="NONE"][["accuracy","balanced_accuracy","macro_f1"]].isna().all().all()
    assert df[df.selection_policy!="NONE"][["accuracy","balanced_accuracy","macro_f1"]].notna().all().all()
    # Correctly preserve missing metrics as null, never as 0.
    records=df[COLS].where(pd.notnull(df[COLS]),None)
    rows=[]
    for item in records.itertuples(index=False,name=None):
        values=[]
        for v in item:
            if v is None or pd.isna(v):values.append(None)
            elif hasattr(v,"item"):values.append(v.item())
            else:values.append(v)
        rows.append(values)
    data={"schema_version":1,"source":str(SOURCE),"rows":rows,"columns":COLS,
          "validated_seeds":42,"validated_rows":len(rows),"baseline_frozen":True}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print("DASHBOARD_DATA_BUILD=PASS",len(rows),"bytes",OUTPUT.stat().st_size,flush=True)
if __name__=="__main__":
    main()
