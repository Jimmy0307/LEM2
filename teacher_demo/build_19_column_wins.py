"""Reconcile the requested 19 COLUMN table (not 19 separate tables).

18 core headers + conflict_rate_pct as column #19. Six strategy win counts
are computed within exactly paired dataset/seed/distribution/alpha/C groups;
ties share fractional credit, no fictitious independent datasets are implied.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path("docs/research/teacher_dashboard/data")
B=Path("docs/research/seed_sweep_1_42/tables/SEED_SWEEP_8820.csv")
N=ROOT/"NONIID_42_RESULTS.csv"
RESULTS=ROOT/"CLASSICAL_19_COLUMNS_42SEEDS.csv"
WINS=ROOT/"SIX_POLICY_WIN_COUNTS_BY_DATASET.csv"
SUMMARY=ROOT/"SIX_POLICY_WIN_COUNTS_AGGREGATED.csv"
METRICS=["accuracy","balanced_accuracy","macro_f1","conflict_resolution_accuracy"]
POLICIES=["FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING","GLOBAL_STRENGTH","POPULATION_STANDARD","POPULATION_GLOBAL"]
HEADERS=[
    "dataset",                 # 1
    "seed",                    # 2
    "distribution",            # 3
    "dirichlet_alpha",         # 4
    "split_mode",              # 5
    "system",                  # 6
    "client_count",            # 7
    "selection_policy",        # 8
    "train_rows",              # 9
    "test_rows",               # 10
    "rule_count",              # 11
    "no_match_count",          # 12
    "covered_count",           # 13
    "test_coverage_pct",       # 14
    "true_in_candidate_count", # 15
    "candidate_coverage_pct",  # 16
    "accuracy_pct",            # 17
    "balanced_accuracy_pct",   # 18
    "conflict_rate_pct",       # 19 ONLY extra Conflict header
]

def load():
    base=pd.read_csv(B)
    non=pd.read_csv(N)
    assert len(base)==8820 and len(non)==7056
    base=base[(base.split_mode=="HOLDOUT_80_20") & base.selection_policy.isin(POLICIES)].copy()
    non=non[non.selection_policy.isin(POLICIES)].copy()
    assert len(base)==3780 and len(non)==6048
    assert not base.duplicated(["dataset","seed","system","client_count","selection_policy"]).any()
    assert not non.duplicated(["dataset","seed","client_count","dirichlet_alpha","selection_policy"]).any()
    base["distribution"]="STRATIFIED_IID"
    base["dirichlet_alpha"]=np.nan
    non["distribution"]="DIRICHLET_NONIID"
    join=pd.concat([base,non],ignore_index=True)
    assert len(join)==9828
    assert set(join.seed)==set(range(1,43))
    assert (join.covered_count+join.no_match_count).eq(join.evaluation_rows).all()
    assert join.true_in_candidate_count.le(join.covered_count).all()
    frame=pd.DataFrame({
       "dataset":join.dataset,
       "seed":join.seed.astype(int),
       "distribution":join.distribution,
       "dirichlet_alpha":join.dirichlet_alpha,
       "split_mode":join.split_mode,
       "system":join.system,
       "client_count":join.client_count.astype(int),
       "selection_policy":join.selection_policy,
       "train_rows":join.train_rows.astype(int),
       "test_rows":join.evaluation_rows.astype(int),
       "rule_count":join.rule_count.astype(int),
       "no_match_count":join.no_match_count.astype(int),
       "covered_count":join.covered_count.astype(int),
       "test_coverage_pct":100*join.covered_count/join.evaluation_rows,
       "true_in_candidate_count":join.true_in_candidate_count.astype(int),
       "candidate_coverage_pct":100*join.true_in_candidate_count/join.evaluation_rows,
       "accuracy_pct":100*join.accuracy,
       "balanced_accuracy_pct":100*join.balanced_accuracy,
       "conflict_rate_pct":100*join.conflict_case_count/join.evaluation_rows
    })[HEADERS]
    assert len(frame.columns)==19 and frame.columns[-1]=="conflict_rate_pct"
    assert frame.conflict_rate_pct.between(0,100).all()
    assert frame.test_coverage_pct.between(0,100).all()
    assert frame.candidate_coverage_pct.between(0,100).all()
    assert np.allclose(frame.conflict_rate_pct/100,join.conflict_case_rate,atol=1e-12)
    return frame,join

def build_wins(join):
    # Each winning comparison is one fixed dataset/seed/topology/regime/alpha:
    # six policies operate on EXACTLY SAME rule-set configuration.
    group=["dataset","seed","distribution","dirichlet_alpha","system","client_count"]
    rows=[]
    count_groups=0
    for config,table in join.groupby(group,dropna=False):
        if len(table)!=6 or set(table.selection_policy)!=set(POLICIES):
            raise AssertionError("Expected six policies per group "+str(config))
        count_groups+=1
        for metric in METRICS:
            scores=pd.to_numeric(table[metric],errors="coerce")
            viable=table[scores.notna()].copy()
            if viable.empty:continue
            mx=float(viable[metric].max())
            winners=viable[np.isclose(viable[metric],mx,rtol=0,atol=1e-12)]
            tied=len(winners)>1
            for policy in POLICIES:
                won=policy in set(winners.selection_policy)
                rows.append({**dict(zip(group,config)),"metric":metric,"selection_policy":policy,
                             "win":int(won),"sole_win":int(won and not tied),
                             "tied_win":int(won and tied),"fractional_win":1.0/len(winners) if won else 0.0,
                             "leader_count":int(len(winners)),"best_score":mx,
                             "score":float(table.loc[table.selection_policy==policy,metric].iloc[0])})
    assert count_groups==1638, count_groups
    allrows=pd.DataFrame(rows)
    assert not allrows.duplicated(group+["metric","selection_policy"]).any()
    assert allrows.groupby(group+["metric"],dropna=False).fractional_win.sum().sub(1).abs().lt(1e-9).all()
    aggregate=(allrows.groupby(["dataset","distribution","dirichlet_alpha","system","client_count","metric","selection_policy"],dropna=False)
          .agg(compared_seed_count=("seed","nunique"),win_count=("win","sum"),
               sole_win_count=("sole_win","sum"),tied_win_count=("tied_win","sum"),
               fractional_wins=("fractional_win","sum"),mean_score=("score","mean"),
               mean_best_score=("best_score","mean")).reset_index())
    assert aggregate.compared_seed_count.eq(42).all()
    return aggregate

def main():
    original,raw=load()
    ROOT.mkdir(parents=True,exist_ok=True)
    original.to_csv(RESULTS,index=False,float_format="%.10f")
    aggregate=build_wins(raw)
    aggregate.to_csv(WINS,index=False,float_format="%.10f")
    table=(aggregate.groupby(["dataset","distribution","dirichlet_alpha","metric","selection_policy"],dropna=False)
           .agg(evaluated_seed_topologies=("compared_seed_count","sum"),
                total_wins=("win_count","sum"),
                sole_wins=("sole_win_count","sum"),
                tied_wins=("tied_win_count","sum"),
                fractional_wins=("fractional_wins","sum")).reset_index())
    table.to_csv(SUMMARY,index=False,float_format="%.10f")
    manifest={
      "status":"VERIFIED","rows":len(original),"columns":HEADERS,"column_count":len(HEADERS),
      "seed_range":"1..42","datasets":sorted(original.dataset.unique().tolist()),
      "scope":"All predictive Classical LEM2 HOLDOUT_80_20 configs: IID Central+Fed, non-IID Fed alpha 0.1/0.5",
      "method":"Classical positive-region reduct + LEM2 (not DRSA/LERS)",
      "winner_definition":"Per dataset, seed, regime, alpha and client_count; best of six decision policies using exact same rule set",
      "tie_handling":"Each tied top policy receives win=1 AND fractional credit 1/n_tied; report solo wins separately",
      "accuracy_ranking":"Accuracy, Balanced Accuracy, Macro-F1 and conflict-only accuracy are separate rankings",
      "independence_warning":"A seed is repeated partitioning of the same source dataset, not a new independent dataset",
      "no_match_note":"Fallback prediction exists; NoMatch rate is not the actual rejection/abstention rate.",
      "files":{"19col":RESULTS.name,"wins_by_topology":WINS.name,"wins_by_dataset":SUMMARY.name}
    }
    (ROOT/"CLASSICAL_19_COLUMNS_MANIFEST.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print("CLASSICAL_19_COLUMNS_AND_WINS_PASS",len(original),len(aggregate),len(table),flush=True)

if __name__=="__main__":main()
