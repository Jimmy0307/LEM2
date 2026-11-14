"""Prespecified G6 statistical tests, performed only after 117 multi-seed source lock.

Primary family-cluster comparisons defined before 3-seed aggregates were
available. Nonparametric Wilcoxon, Holm across 5 pre-registered contrasts,
family-cluster bootstrap descriptive intervals, Friedman for six fixed methods.
Statistical claims are about benchmark sample, not independent real domains.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon,friedmanchisquare

IN=Path("docs/research/teacher_dashboard/data")
FIXED=(
 "FIXED_FIRST_MATCH","FIXED_SIMPLE_VOTING","FIXED_STANDARD_VOTING",
 "FIXED_GLOBAL_STRENGTH","FIXED_POPULATION_STANDARD","FIXED_POPULATION_GLOBAL"
)
PRE_REGISTERED=(
 ("IID","VALIDATION_BEST","FIXED_GLOBAL_STRENGTH"),
 ("NONIID_05","VALIDATION_BEST","FIXED_SIMPLE_VOTING"),
 ("NONIID_01","VALIDATION_BEST","FIXED_SIMPLE_VOTING"),
 ("NONIID_01","GUARDED_SKEW_V1","FIXED_SIMPLE_VOTING"),
 ("NONIID_01","LOFO_META_KNN7","FIXED_SIMPLE_VOTING"),
)

def main():
    manifest=json.loads((IN/"PMLB_117_3SEED_MANIFEST.json").read_text())
    assert manifest["status"]=="PASS_OVER_100_PUBLIC_BENCHMARK_TABLES"
    assert manifest["seeds"]==[1,7,42]
    assert manifest["successful_iid_tables"]>=101
    s=pd.read_csv(IN/"PMLB_117_3SEED_POLICY_SELECTIONS.csv")
    assert s.groupby(["scenario","seed"]).dataset.nunique().min()>=90
    x=s[s.objective.eq("balanced_accuracy")]
    out=[]
    pv=[]
    for scen,chosen,base in PRE_REGISTERED:
        group=x[(x.scenario==scen)&x.method.isin([chosen,base])]
        pair=group.pivot_table(index=["dataset","family","seed"],
                               columns="method",values="test_score_pct")
        # Full scenarios and complete 3 seed support only.
        n_by_ds=pair.groupby(level="dataset").size()
        good=set(n_by_ds[n_by_ds.eq(3)].index)
        pair=pair.loc[pair.index.get_level_values("dataset").isin(good)]
        pair=pair.dropna()
        # Treat family as independent conservative unit; seed correlations
        # and related dataset variants are averaged within family first.
        diff=(pair[chosen]-pair[base]).groupby(level="family").mean()
        arr=diff.to_numpy(dtype=float)
        assert len(arr)>=70
        assert np.all(np.isfinite(arr))
        nonzero=int((abs(arr)>1e-10).sum())
        if nonzero:
            w=wilcoxon(arr,zero_method="wilcox",alternative="greater",
                       method="auto")
            p=float(w.pvalue);stat=float(w.statistic)
        else:p=1.0;stat=0.0
        rng=np.random.default_rng(20261114)
        trials=arr[rng.integers(0,len(arr),size=(2500,len(arr)))].mean(axis=1)
        out.append({
          "scenario":scen,"candidate":chosen,"baseline":base,
          "independent_family_clusters_provisional":len(arr),
          "source_tables_with_three_seeds":len(good),
          "mean_gain_pp":float(arr.mean()),"median_gain_pp":float(np.median(arr)),
          "bootstrap_ci95_low_pp":float(np.quantile(trials,.025)),
          "bootstrap_ci95_high_pp":float(np.quantile(trials,.975)),
          "wilcoxon_statistic":stat,"wilcoxon_one_sided_unadjusted_p":p,
          "family_improved":int((arr>1e-8).sum()),
          "family_harmed":int((arr < -1e-8).sum()),
          "family_tied":int((abs(arr)<=1e-8).sum()),
          "test_direction":"candidate_higher_than_baseline",
          "comparison_was_preregistered_before_3seed_finalization":True
        })
        pv.append(p)
    # Holm-Bonferroni across 5 pre-registered one-sided contrasts.
    pvals=np.array(pv,dtype=float)
    order=np.argsort(pvals)
    adjusted=np.empty(len(pvals))
    previous=0.0
    for i,idx in enumerate(order):
        corrected=min(1.0,(len(pvals)-i)*pvals[idx])
        previous=max(previous,corrected)
        adjusted[idx]=previous
    for i,item in enumerate(out):
        item["holm_adjusted_p"]=float(adjusted[i])
        item["holm_significant_005"]=bool(adjusted[i]<.05)
    result=pd.DataFrame(out)
    result.to_csv(IN/"PMLB_117_3SEED_G6_WILCOXON_HOLM.csv",index=False,float_format="%.12f")
    friedman=[]
    for scen,g in x[x.method.isin(FIXED)].groupby("scenario"):
        # One family = one unit; average PMLB task variant and all 3 seeds.
        matrix=g.pivot_table(index="family",columns="method",values="test_score_pct")
        matrix=matrix.dropna()
        assert len(matrix)>=70 and len(matrix.columns)==6
        f=friedmanchisquare(*(matrix[p].to_numpy() for p in FIXED))
        friedman.append({
          "scenario":scen,"families":len(matrix),
          "six_fixed_methods":",".join(FIXED),
          "friedman_chisquare":float(f.statistic),"friedman_p":float(f.pvalue),
          "mean_rank_best":str(matrix.rank(axis=1,ascending=False,method="average").mean().sort_values().index[0]),
          "note":"Repeated PMLB related tasks and unknown original provenance limit independent domain inference; test uses provisional family grouping"
        })
    pd.DataFrame(friedman).to_csv(IN/"PMLB_117_3SEED_G6_FRIEDMAN.csv",index=False,float_format="%.12f")
    receipt={
      "status":"G6_THREE_SEEDS_FIVE_PRESPECIFIED_TESTS_PASS",
      "pre_registered_comparisons":len(PRE_REGISTERED),
      "holm_family":"five one-sided prespecified Balanced Accuracy gains",
      "dataset_group":"provisional family with all related tasks and repeated seeds averaged",
      "primary_seed_set":[1,7,42],
      "source_117_candidate_run_id":43576756817,
      "g6_limitations":[
       "One PMLB corpus with correlated UCI/derived/synthetic tasks, not 88 truly independent real domains",
       "Multiple comparison correction is applied to exactly five registered contrasts",
       "Formal population-level generalization needs different independent corpora and more seeds",
       "Three seeds are not 42; finite sample and IID/nonIID benchmark settings cannot claim universal optimality",
       "Statistical comparison cannot itself establish algorithmic novelty"],
      "primary_test_results":out,
      "friedman_summary":friedman
    }
    (IN/"PMLB_117_3SEED_G6_MANIFEST.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2,allow_nan=False))
    print("PMLB_117_G6_PRESPECIFIED_MULTI_SEED_TESTS_PASS")
    for z in out:
        print("G6",z["scenario"],z["candidate"],"VS",z["baseline"],
              "GAIN_PP",round(z["mean_gain_pp"],4),
              "HOLM_P",round(z["holm_adjusted_p"],6),flush=True)

if __name__=="__main__":main()
