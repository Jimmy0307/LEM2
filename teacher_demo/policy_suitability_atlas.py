"""Evidence-only atlas of when six LEM2 prediction policies work.

Input source A: 20 DISTINCT UCI domains, seed42, 2 architectures, 6
policy predictions + 1 NONE per architecture.
Input source B: original 3 UCI data sets, 42 seeds, IID and client
Dirichlet alpha 0.5, 0.1; all C2-C5 compared (central only in other files).

Do NOT train a selector against test-derived conflict or candidate coverage:
those are retrospective DIAGNOSTICS, not deployment features. Metadata
class distribution in the UCI prepared set is also retrospective; train-only
profiling is a prerequisite before deploying any adaptive policy selection.

Use fractional wins for ties and always preserve number of matched
competitions; not statistical independent observations across seeds.
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
from teacher_demo.public_20_registry import REGISTRY

DATA=Path("docs/research/teacher_dashboard/data")
POLICIES=("FIRST_MATCH","SIMPLE_VOTING","STANDARD_VOTING","GLOBAL_STRENGTH",
          "POPULATION_STANDARD","POPULATION_GLOBAL")
OBJECTIVES=("accuracy","balanced_accuracy","macro_f1")
GROUPS=("feature_mode","skew_band","class_band","conflict_band","architecture")
REGIMES=("STRATIFIED_IID","DIRICHLET_NON_IID")

def assert_ok(value,reason):
    if not bool(value):raise AssertionError(reason)

def group_value(field,r):
    if field=="feature_mode":return r["feature_mode"]
    if field=="skew_band":
        v=float(r["majority_share"])
        return "majority_ge_90pct" if v>=.9 else "majority_75_to_90pct" if v>=.75 else "majority_under_75pct"
    if field=="class_band":
        n=int(r["class_count"])
        return "binary" if n==2 else "three_to_seven" if n<=7 else "eight_plus"
    if field=="conflict_band":
        v=float(r["test_conflict_pct"])
        return "none" if abs(v)<1e-12 else "under_10pct" if v<10 else "10_to_40pct" if v<40 else "40pct_plus"
    if field=="architecture":return "CENTRALIZED" if int(r["client_count"])==0 else "FEDERATED_C3"
    raise KeyError(field)

def public_twenty():
    raw=pd.read_csv(DATA/"PUBLIC20_BASE_RESULTS.csv")
    evidence=json.loads((DATA/"PUBLIC20_MANIFEST.json").read_text(encoding="utf-8"))
    assert_ok(evidence["passed_count"]==20 and evidence["failed_count"]==0,"Incomplete 20 dataset pilot")
    m={p["key"]:p for p in evidence["datasets"]}
    assert_ok(len(m)==len(REGISTRY)==20,"New source count mismatch")
    assert_ok(len(raw)==280,"Expected 20 x 2 x 7 source observations")
    assert_ok(raw.seed.eq(42).all(),"One seed, not 42!")
    result=[]
    for (ds,client),block in raw.groupby(["public_dataset_key","client_count"],sort=True):
        assert_ok(ds in m and len(block)==7,ds+" missing policies")
        u=m[ds];counts=np.asarray(list(u["observed_classes"].values()),dtype=float)
        freq=counts/counts.sum()
        assert_ok(set(block.selection_policy)==set(POLICIES)|{"NONE"},"Policy missing")
        assert_ok(int(counts.sum())==u["used_rows"],"Class totals mismatch")
        assert_ok(int(block.dataset_rows.iloc[0])==u["used_rows"],"Model inputs don't match data")
        assert_ok(set(block.source_sha256)=={u["prepared_sha256"]},"Source hash mismatch")
        one=block[block.selection_policy.eq("NONE")].iloc[0]
        compare=block[block.selection_policy.ne("NONE")].copy()
        assert_ok(compare.shape[0]==6 and not compare.selection_policy.duplicated().any(),"Six-policies set")
        for obj in OBJECTIVES:
            hi=compare[obj].max()
            assert_ok(pd.notna(hi),"Missing objective "+obj)
            leaders=compare[np.isclose(compare[obj].astype(float),hi,rtol=1e-10,atol=1e-12)].selection_policy.tolist()
            assert_ok(len(leaders)>=1,"No winner")
            for _,p in compare.iterrows():
                result.append({
                  "dataset":ds,"uci_id":u["uci_id"],"domain":u["domain"],"feature_mode":u["feature_mode"],
                  "research_trait":u["trait"],"seed":42,
                  "architecture":"CENTRALIZED" if client==0 else "FEDERATED_C3","client_count":int(client),
                  "source_rows":int(u["source_rows"]),"model_rows":int(u["used_rows"]),
                  "feature_count":int(u["used_feature_count"]),
                  "class_count":int(len(counts)),"majority_share":float(freq.max()),"minority_share":float(freq.min()),
                  "normalized_class_entropy":float(-(freq*np.log(freq)).sum()/np.log(len(freq))) if len(freq)>1 else 0.0,
                  "test_coverage_pct":100*float(one.coverage),
                  "test_conflict_pct":100*float(one.conflict_case_rate),
                  "test_candidate_coverage_pct":100*float(one.true_in_candidate_rate),
                  "rule_count":int(one.rule_count),
                  "objective":obj,"policy":p.selection_policy,"objective_score_pct":100*float(p[obj]),
                  "sole_win":int(p.selection_policy in leaders and len(leaders)==1),
                  "tied_win":int(p.selection_policy in leaders),
                  "fractional_win":float(1/len(leaders)) if p.selection_policy in leaders else 0.,
                  "winning_policy_count":len(leaders),
                  "status":"DESCRIPTIVE_POSTHOC_ONE_SEED_NOT_SELECTOR"
                })
    out=pd.DataFrame(result)
    assert_ok(len(out)==20*2*6*3,"Expected 720 winner rows (40 configurations ×6 policies ×3 objectives)")
    assert_ok(out.groupby(["dataset","client_count","objective"]).fractional_win.sum().between(.999999,1.000001).all(),"Tie credits not 1")
    assert_ok(out.groupby(["dataset","client_count","objective"]).size().eq(6).all(),"Incomplete comparisons")
    out.to_csv(DATA/"POLICY_SUITABILITY_20_MATCHUPS.csv",index=False,float_format="%.10f")
    groups=[]
    for group_by in GROUPS:
        out["group_value"]=[group_value(group_by,record) for record in out.to_dict("records")]
        for (value,objective,policy),rows in out.groupby(["group_value","objective","policy"],sort=True):
            competitors=int(len(rows))
            unique_datasets=rows.dataset.nunique()
            groups.append({
              "group_type":group_by,"group_value":value,"objective":objective,"policy":policy,
              "matchups":competitors,"unique_datasets":unique_datasets,
              "fractional_wins":float(rows.fractional_win.sum()),
              "win_share_pct":100*float(rows.fractional_win.mean()),
              "sole_wins":int(rows.sole_win.sum()),
              "co_wins":int(rows.tied_win.sum()),
              "tied_matchup_count":int((rows.winning_policy_count>1).sum()),
              "source_evidence":"20_UCI_1_SEED_POSTHOC",
              "warning":"No statistical significance. Test conflict/candidate features retrospective only."
            })
    summarized=pd.DataFrame(groups)
    assert_ok(summarized.matchups.ge(1).all(),"Empty group")
    summarized.to_csv(DATA/"POLICY_SUITABILITY_20_GROUPS.csv",index=False,float_format="%.10f")
    return out,summarized

def original_42():
    n=json.loads((DATA/"NONIID_42_SUMMARY.json").read_text(encoding="utf-8"))
    assert_ok(n["fully_complete"] and n["valid_rows"]==7056 and n["invalid_configurations"]==0,
              "Non IID 42-seed source not fully valid")
    c=pd.DataFrame(n["comparisons"])
    win=pd.read_csv(DATA/"POLICY_WINS_BY_DATASET.csv")
    target_win={"accuracy_pct":"accuracy","balanced_accuracy_pct":"balanced_accuracy","macro_f1_pct":"macro_f1"}
    out=[]
    for regime,alpha in [("STRATIFIED_IID",None),("DIRICHLET_NON_IID",.5),("DIRICHLET_NON_IID",.1)]:
      df=c[c.dirichlet_alpha.eq(.1 if regime=="STRATIFIED_IID" else alpha)]
      assert_ok(len(df)==4*7,"Missing Alpha comparison clients")
      for objective in OBJECTIVES:
        # 42-seed IID comparisons are copied from same-alpha IID reference
        # in the non-IID summary; only C2-C5, no centralized mixing.
        col=("delta_" if False else "")+objective+("_iid" if regime=="STRATIFIED_IID" else "_noniid")
        for policy in POLICIES:
            p=df[df.selection_policy.eq(policy)]
            assert_ok(len(p)==4,"Policy missing in four client counts")
            v=float(p[col].mean())*100
            # The available policy win table on IID includes CENTRALIZED;
            # DO NOT attach it to the Fed-only mean as if denominators matched.
            if regime=="STRATIFIED_IID":
                win_rows=win[(win.regime=="STRATIFIED_IID") & (win.metric.eq(objective+"_pct")) & (win.winning_policy.eq(policy))]
                assert_ok(len(win_rows)==3,"Missing three IID win rows")
                win_scope="IID_C0_C2_C5_630_CONFIGS_NOT_DIRECTLY_COMPARABLE_TO_FED_ONLY_MEAN"
            else:
                win_rows=win[(win.regime=="DIRICHLET_NON_IID") & (win.metric.eq(objective+"_pct")) &
                             (win.winning_policy.eq(policy)) &
                             np.isclose(win.dirichlet_alpha.astype(float),float(alpha))]
                assert_ok(len(win_rows)==3,"Missing three nonIID win rows")
                win_scope="FED_C2_C5_504_CONFIGS"
            share=float(win_rows.fractional_wins.sum()/win_rows.opportunities.sum())*100
            out.append({"distribution":regime,"alpha":alpha,"objective":objective,
               "policy":policy,"metric_mean_pct":v,
               "fractional_win_share_pct":share,
               "win_competitions":int(win_rows.opportunities.sum()),
               "win_scope":win_scope,
               "source_method":"Classical positive-region reduct + LEM2",
               "datasets":3,"seed_count":42,"client_counts":"C2,C3,C4,C5",
               "status":"42_SEED_SOURCE_COMPLETE"})
    df=pd.DataFrame(out)
    assert_ok(len(df)==54,"3 regimes × 3 outcomes × 6 strategies")
    df.to_csv(DATA/"POLICY_SUITABILITY_42_DISTRIBUTIONS.csv",index=False,float_format="%.10f")
    return df

def main():
    b,g=public_twenty()
    d=original_42()
    sha_manifest={
       "status":"PASS_GROUNDED_DESCRIPTIVE_ATLAS",
       "source_research_branch":"research/report-ready-dashboard-20261109",
       "n_uci_20":20,"one_seed_pilot":42,"n_policy_comparisons":40,"twenty_rows":len(b),
       "twenty_groups":len(g),"n_original_42":3,"original_42_seeds":42,
       "original_42_regimes":["IID-C2-C5","nonIID-alpha=0.5-C2-C5","nonIID-alpha=0.1-C2-C5"],
       "original_42_rows":len(d),
       "no_claims":[
        "A feature type does not independently cause a certain policy to win",
        "Twenty datasets each have only one holdout seed, many tied winners",
        "Original 42-seed domains are only Balance Scale, Car Evaluation, Hayes-Roth",
        "Class ratios in PUBLIC20 manifest profile the complete prepared subset, not train-only meta-features",
        "Conflict and candidate coverage in this atlas are TEST diagnostic metrics, must never be fed into a deployed selector",
        "Class imbalance and per-client label skew are different dimensions",
        "Original 42 non-IID experiment varies label allocation using Dirichlet alpha; quantity/feature/time drift not validated",
        "Zero conflict yields identical six-policy predictions by design",
        "No-match training-majority fallback is not explicit abstention"
       ],
       "next_valid_design":[
        "For each dataset and seed, outer holdout stays untouched",
        "Compute feature type, train-only entropy, minority share, condition value cardinality, class count, client label JS divergence, client row count CV, and rule structural stats using only train",
        "Fit six policies using the same frozen induction rules; evaluate on INNER validation",
        "Learn a policy selector on meta-features and validate leave-one-dataset-out; evaluate only after lock",
        "Compare against globally fixed-best and six-method-oracle diagnostic (oracle never deployed)",
        "Report Balanced Accuracy, Macro-F1, minority recall, regret, runtime, and coverage/conflict separate"
       ],
       "outputs":["POLICY_SUITABILITY_20_MATCHUPS.csv","POLICY_SUITABILITY_20_GROUPS.csv",
                  "POLICY_SUITABILITY_42_DISTRIBUTIONS.csv"]
    }
    (DATA/"POLICY_SUITABILITY_MANIFEST.json").write_text(
      json.dumps(sha_manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print("POLICY_SUITABILITY_ATLAS_PASS",len(b),len(g),len(d),flush=True)

if __name__=="__main__":main()
