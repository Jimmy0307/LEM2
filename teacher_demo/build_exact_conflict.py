"""Aggregate exact 42-seed row-level conflict intersections; no invented percentages.

Input: unmodified GZIP row traces from validated GitHub Actions run 42644663319.
Output: policy-level mutually exclusive status and conflict outcome counts,
each reconciled to frozen 8,820 summary. Does not redefine conflict itself.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

POLICIES=("FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING","GLOBAL_STRENGTH","POPULATION_STANDARD","POPULATION_GLOBAL")
KEY=["dataset","seed","split_mode","system","client_count"]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",default="downloaded_traces")
    ap.add_argument("--output",default="docs/research/teacher_dashboard/data/CONFLICT_EXACT_42SEEDS.csv")
    args=ap.parse_args()
    files=sorted(Path(args.input).rglob("ROW_CASES_seed*.csv.gz"))
    assert len(files)==42,("missing trace artifact",len(files))
    frozen=pd.read_csv("docs/research/seed_sweep_1_42/tables/SEED_SWEEP_8820.csv")
    outputs=[]
    for file in files:
        df=pd.read_csv(file)
        assert not df.duplicated(KEY+["row_id"]).any()
        for key,group in df.groupby(KEY,dropna=False):
            key_map=dict(zip(KEY,key))
            no=group.no_match.astype(bool)
            have=group.true_in_candidate.astype(bool)
            conflict=group.conflict.astype(bool)
            n=len(group)
            a=int(no.sum())
            b=int((~no&~have&~conflict).sum())
            c=int((~no&have&~conflict).sum())
            d=int((~no&have&conflict).sum())
            e=int((~no&~have&conflict).sum())
            assert a+b+c+d+e==n,("partition not exhaustive",key)
            none=frozen
            for k,v in key_map.items():none=none[none[k]==v]
            assert len(none)==7
            base=none.loc[none.selection_policy=="NONE"].iloc[0]
            assert n==int(base.evaluation_rows)
            assert a==int(base.no_match_count)
            assert int(conflict.sum())==int(base.conflict_case_count)
            assert int(have.sum())==int(base.true_in_candidate_count)
            for policy in POLICIES:
                correct=group["correct_"+policy].astype(bool)
                winner=group["prediction_"+policy].astype(str)
                output={
                    **key_map,"selection_policy":policy,"evaluation_rows":n,
                    "no_match_count":a,
                    "matched_no_true_count":b,
                    "single_candidate_true_count":c,
                    "conflict_true_candidate_count":d,
                    "conflict_no_true_candidate_count":e,
                    "conflict_total_count":d+e,
                    "fallback_correct_count":int((no&correct).sum()),
                    "fallback_wrong_count":int((no&~correct).sum()),
                    "candidate_absent_wrong_count":b+e,
                    "single_candidate_true_correct_count":int((~no&have&~conflict&correct).sum()),
                    "single_candidate_true_wrong_count":int((~no&have&~conflict&~correct).sum()),
                    "conflict_true_correct_count":int((conflict&have&correct).sum()),
                    "conflict_true_wrong_count":int((conflict&have&~correct).sum()),
                    "conflict_no_true_wrong_count":int((conflict&~have&~correct).sum()),
                    "overall_correct_count":int(correct.sum())
                }
                assert output["conflict_true_correct_count"]+output["conflict_true_wrong_count"]==d
                assert output["conflict_no_true_wrong_count"]==e
                assert int(correct.sum())==int(round(float(none.loc[none.selection_policy==policy,"accuracy"].iloc[0])*n))
                outputs.append(output)
    result=pd.DataFrame(outputs)
    assert len(result)==7560 and not result.duplicated(KEY+["selection_policy"]).any()
    assert set(result.seed)==set(range(1,43))
    dest=Path(args.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    result.sort_values(KEY+["selection_policy"]).to_csv(dest,index=False)
    print("CONFLICT_EXACT_42_SEEDS_PASS",len(result),flush=True)
if __name__=="__main__":main()
