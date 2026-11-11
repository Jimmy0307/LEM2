"""Exact mutually-exclusive conflict/selection decomposition from 42-seed row receipts.

Never infer intersecting conflict x true-candidate sets from marginal coverage.
Use the audited ROW_CASES_seed*.csv.gz model traces from GitHub Actions run
42644663319, and assert every metric against frozen SEED_SWEEP_8820.csv.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

POLICIES=("FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING","GLOBAL_STRENGTH",
          "POPULATION_STANDARD","POPULATION_GLOBAL")
KEYS=["dataset","seed","split_mode","system","client_count"]
def safe_ratio(n,d):
    return None if d==0 else float(n/d)

def run(inputs: Path, output: Path):
    src=pd.read_csv("docs/research/seed_sweep_1_42/tables/SEED_SWEEP_8820.csv")
    assert len(src)==8820
    files=sorted(inputs.glob("ROW_CASES_seed*.csv.gz"))
    assert len(files)==42,("missing original row evidence",len(files))
    output.mkdir(parents=True,exist_ok=True)
    rows=[]; integrity=[]
    for fname in files:
        df=pd.read_csv(fname,compression="gzip",low_memory=False)
        assert len(df)>0
        for key,part in df.groupby(KEYS,dropna=False,sort=True):
            config=dict(zip(KEYS,key))
            n=len(part)
            c=lambda m:int(m.sum())
            hit=part.n_matching_rules.astype(int)>0
            truth=part.true_in_candidate.astype(int)==1
            conf=part.conflict.astype(int)==1
            no_match=~hit
            missing=hit&~truth
            present=hit&truth
            assert ((no_match.astype(int)+missing.astype(int)+present.astype(int))==1).all()
            for policy in POLICIES:
                ok=part["correct_"+policy].astype(int)==1
                class_counts={
                    "no_match_correct":c(no_match&ok),
                    "no_match_wrong":c(no_match&~ok),
                    "matched_absent_conflict":c(missing&conf),
                    "matched_absent_nonconflict":c(missing&~conf),
                    "matched_present_conflict_correct":c(present&conf&ok),
                    "matched_present_conflict_wrong":c(present&conf&~ok),
                    "matched_present_nonconflict_correct":c(present&~conf&ok),
                    "matched_present_nonconflict_wrong":c(present&~conf&~ok),
                }
                assert sum(class_counts.values())==n
                conflict_n=c(conf)
                assert (class_counts["matched_absent_conflict"]+
                        class_counts["matched_present_conflict_correct"]+
                        class_counts["matched_present_conflict_wrong"])==conflict_n
                truth_conf=c(present&conf)
                base=src.copy()
                for col,value in config.items():base=base[base[col]==value]
                check=base[base.selection_policy==policy]
                assert len(check)==1,(config,policy,len(check))
                rec=check.iloc[0]
                correct_n=c(ok)
                assert abs(correct_n/n-float(rec.accuracy))<1e-10,(config,policy,correct_n/n,rec.accuracy)
                assert abs(c(hit)/n-float(rec.coverage))<1e-10
                assert abs(conflict_n/n-float(rec.conflict_case_rate))<1e-10
                assert abs(c(truth)/n-float(rec.true_in_candidate_rate))<1e-10
                conflict_acc=safe_ratio(c(ok&conf),conflict_n)
                if rec.conflict_resolution_accuracy==rec.conflict_resolution_accuracy:
                    assert abs(conflict_acc-float(rec.conflict_resolution_accuracy))<1e-10
                else: assert conflict_acc is None
                rows.append({**config,"policy":policy,"evaluation_rows":n,
                    "accuracy":float(rec.accuracy),
                    "balanced_accuracy":float(rec.balanced_accuracy),
                    "conflict_rate":conflict_n/n,
                    "conflict_case_count":conflict_n,
                    "conflict_resolution_accuracy":conflict_acc,
                    "conflict_with_correct_candidate":truth_conf,
                    "conflict_solvable_accuracy":safe_ratio(class_counts["matched_present_conflict_correct"],truth_conf),
                    "not_in_candidate_count":c(missing),
                    "candidate_failure_rate":c(missing)/n,
                    "no_match_count":c(no_match),**class_counts})
        integrity.append({"seed":int(df.seed.iloc[0]),"row_receipts":len(df),"configs":len(df.groupby(KEYS))})
    result=pd.DataFrame(rows)
    assert len(result)==42*3*2*5*6,len(result)
    assert result.duplicated(KEYS+["policy"]).sum()==0
    assert set(result.seed)==set(range(1,43))
    assert all(a["configs"]==30 for a in integrity)
    result.to_csv(output/"CONFLICT_TRIAGE_42SEEDS.csv",index=False)
    # Web summary: follow user controls from canonical 8820; no cross-scope averaging on the viewer.
    records=result.where(pd.notnull(result),None).to_dict(orient="records")
    summary={
        "schema_version":1,
        "source_run":"https://github.com/Jimmy0307/LEM2/actions/runs/42644663319",
        "frozen_baseline":"SEED_SWEEP_8820.csv",
        "policy_rows":len(records),"row_receipt_audit":integrity,
        "definition":"Eight mutually exclusive categories; denominators are explicit; no-match fallback is not always wrong.",
        "rows":records,
    }
    (output/"conflict_triage_42.json").write_text(
        json.dumps(summary,ensure_ascii=False,separators=(",",":"),allow_nan=False),encoding="utf-8")
    print("ALL_CONFLICT_GROUPS_7560_RECONCILED_PASS",flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument("--inputs",default="downloaded_row_evidence")
    p.add_argument("--output",default="docs/research/teacher_dashboard/data")
    a=p.parse_args();run(Path(a.inputs),Path(a.output))
if __name__=="__main__":main()
