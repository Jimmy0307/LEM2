"""Auditable row-level rule matching and winner scores, reusing the frozen LEM2 pipeline.

One seed: 3 datasets x 2 splits x (centralized + C2..C5).
No alternative LEM2 implementation and no extra preprocessing.
Produces GZIP traces, per-class metrics, and a rule catalog for direct lookup.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
import numpy as np
import pandas as pd
from roughset.app import _run_split
from roughset.evaluation import matching_rules, population_support_summary
from teacher_demo.seed_sweep_runner import pinned_bundles
from teacher_demo.full_factorial_matrix import _split_raw, POLICIES

ROOT = Path("docs/research/seed_sweep_1_42/tables/SEED_SWEEP_8820.csv")

def rule_id(rule):
    payload = json.dumps(
        {"conditions": sorted((str(k), str(v)) for k,v in rule.conditions),
         "decision": str(rule.decision)}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

def score_context(matched, weights, supports, sizes):
    """Every decision's T,U,N,P and all six score components (FIRST uses order)."""
    grouped = {}
    for r in matched:
        grouped.setdefault(str(r.decision), []).append(r)
    summaries=population_support_summary(matched, supports, sizes)
    result={}
    for decision, rr in grouped.items():
        q=summaries.get(decision, {})
        t=float(q.get("total_support_occurrences",0.0))
        u=float(q.get("unique_population",0.0))
        n=float(q.get("class_size",0.0))
        population=(u/t if t else 0.)
        result[decision]={
            "n_matching_rules":len(rr),
            "T":t,"U":u,"N":n,"P":population,
            "SIMPLE_VOTING":float(len(rr)),
            "STANDARD_VOTING":float(sum(weights.get(r.key,0.) for r in rr)),
            "GLOBAL_STRENGTH":u/n if n else 0.,
            "POPULATION_STANDARD":u,
            "POPULATION_GLOBAL":u*u/(n*t) if n and t else 0.,
            "FIRST_MATCH_first_rule":rule_id(rr[0]),
        }
    return result

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--seed",type=int,required=True)
    pa.add_argument("--output",default="outputs/teacher_row_evidence")
    args=pa.parse_args()
    if args.seed not in range(1,43):raise ValueError("seed must be 1..42")
    base=json.loads(Path("config.json").read_text(encoding="utf-8-sig"))
    base["evaluation"]["seed"]=args.seed
    golden=pd.read_csv(ROOT)
    golden=golden[golden.seed==args.seed]
    assert len(golden)==210
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    cases=[];rules_out=[];class_rows=[];audit=[]
    for bundle in pinned_bundles():
        for split_mode in ("FULL_DATA","HOLDOUT_80_20"):
            raw_train, raw_test = _split_raw(bundle,split_mode,args.seed,float(base["evaluation"]["test_ratio"]))
            for nclients in (0,2,3,4,5):
                cfg=deepcopy(base)
                cfg["evaluation"]["mode"]=split_mode
                cfg["federated"]["n_clients"]=nclients
                cfg["federated"]["run_client_sweep"]=False
                cfg["federated"]["order_sensitivity_max_permutations"]=1
                cfg["experiment"]["run_centralized"]=nclients==0
                cfg["experiment"]["run_federated"]=nclients>0
                obj=_run_split(bundle,raw_train,raw_test,cfg,quiet=True,
                               prediction_policies=POLICIES,fold=1)
                art=obj["structural_artifact"]
                sys="CENTRALIZED" if nclients==0 else "FEDERATED"
                which="centralized" if nclients==0 else "federated"
                rs=art.central_rules if nclients==0 else art.global_rules
                weights=art.central_rule_weights if nclients==0 else art.global_rule_weights
                supports=art.central_rule_support_sets if nclients==0 else art.global_rule_support_sets
                sizes=art.central_class_sizes if nclients==0 else art.global_class_sizes
                default=art.central_default_class if nclients==0 else art.default_class
                pred={p:obj["policy_results"][p][which]["predictions"] for p in POLICIES}
                run_key={"dataset":bundle.name,"seed":args.seed,"split_mode":split_mode,
                         "system":sys,"client_count":nclients}
                ref=golden[(golden.dataset==bundle.name)&(golden.split_mode==split_mode)&
                           (golden.system==sys)&(golden.client_count==nclients)]
                assert len(ref)==7, (run_key,len(ref))
                assert len(rs)==int(ref.rule_count.iloc[0])
                for rule in rs:
                    src=art.rule_provenance.get(rule.key,()) if nclients else ("Centralized",)
                    rules_out.append({**run_key,"rule_id":rule_id(rule),
                        "conditions_json":json.dumps([(str(k),str(v)) for k,v in rule.conditions],ensure_ascii=False),
                        "decision":str(rule.decision),"source_clients":";".join(map(str,src)),
                        "standard_weight":float(weights.get(rule.key,0.)),
                        "true_support_size":len(supports.get(rule.key,()))})
                start=len(cases)
                for pos,(_,row) in enumerate(art.test.iterrows()):
                    m=matching_rules(row,rs)
                    cand=sorted(set(str(r.decision) for r in m))
                    truth=str(row[bundle.target])
                    matched_ids=[rule_id(r) for r in m]
                    scores=score_context(m,weights,supports,sizes)
                    d={**run_key, "row_id":int(row["__row_id__"]),
                       "true_class":truth,"default_class":str(default),
                       "n_matching_rules":len(m),"n_candidates":len(cand),
                       "candidate_labels":";".join(cand),"matched_rule_ids":";".join(matched_ids),
                       "score_by_decision_json":json.dumps(scores,sort_keys=True,ensure_ascii=False),
                       "no_match":int(len(m)==0),
                       "covered_true_not_candidate":int(bool(m) and truth not in cand),
                       "true_in_candidate":int(truth in cand),
                       "conflict":int(len(cand)>1),
                       "features_json":json.dumps(
                          {f:str(row[f]) for f in bundle.features},ensure_ascii=False)}
                    for policy in POLICIES:
                        prediction=str(pred[policy][pos])
                        d["prediction_"+policy]=prediction
                        d["correct_"+policy]=int(prediction==truth)
                        d["fallback_correct_"+policy]=int(not m and prediction==truth)
                        d["candidate_present_but_wrong_"+policy]=int(truth in cand and prediction!=truth)
                    cases.append(d)
                run_cases=pd.DataFrame(cases[start:])
                for cls,grp in run_cases.groupby("true_class"):
                    r={**run_key,"true_class":cls,"n":len(grp),
                       "covered_count":int((grp.no_match==0).sum()),
                       "no_match_count":int(grp.no_match.sum()),
                       "candidate_covered_count":int(grp.true_in_candidate.sum()),
                       "covered_true_not_candidate_count":int(grp.covered_true_not_candidate.sum()),
                       "conflict_count":int(grp.conflict.sum())}
                    for p in POLICIES:
                        r["correct_"+p]=int(grp["correct_"+p].sum())
                        r["fallback_correct_"+p]=int(grp["fallback_correct_"+p].sum())
                        r["candidate_present_but_wrong_"+p]=int(grp["candidate_present_but_wrong_"+p].sum())
                    class_rows.append(r)
                # Validate directly against original 8,820-run metrics (same algorithm outputs)
                n=len(run_cases)
                for p in POLICIES:
                    actual=float(run_cases["correct_"+p].mean())
                    saved=float(ref.loc[ref.selection_policy==p,"accuracy"].iloc[0])
                    if not np.isclose(actual,saved,atol=1e-12,rtol=1e-12):
                        raise AssertionError((run_key,p,"accuracy",actual,saved))
                none=ref[ref.selection_policy=="NONE"].iloc[0]
                for k,ours,theirs in (
                   ("coverage",float((run_cases.no_match==0).mean()),none.coverage),
                   ("conflict",float(run_cases.conflict.mean()),none.conflict_case_rate),
                   ("true_candidate",float(run_cases.true_in_candidate.mean()),none.true_in_candidate_rate)):
                    if not np.isclose(ours,float(theirs),atol=1e-12,rtol=1e-12):
                        raise AssertionError((run_key,k,ours,theirs))
                audit.append({**run_key,"evaluation_rows":n,"rules":len(rs),"verified":True})
                print("TRACE_BLOCK_PASS",run_key,n,flush=True)
    assert len(audit)==30 and len(pd.DataFrame(audit))==30
    paths={"ROW_CASES":pd.DataFrame(cases),
           "RULE_CATALOG":pd.DataFrame(rules_out).drop_duplicates(
                ["dataset","seed","split_mode","system","client_count","rule_id"]),
           "PER_CLASS":pd.DataFrame(class_rows),
           "RUN_AUDIT":pd.DataFrame(audit)}
    for name,frame in paths.items():
        file=out/f"{name}_seed{args.seed:02d}.csv.gz"
        frame.to_csv(file,index=False,compression="gzip")
        print(name,len(frame),file,flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
