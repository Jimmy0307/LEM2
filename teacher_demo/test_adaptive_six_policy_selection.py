"""Critical invariants: six-policy selector trains on validation, never test."""
import numpy as np
import pandas as pd
import pytest

from teacher_demo.adaptive_six_policy_runner import OBJECTIVES,POLICY_ORDER
from teacher_demo.adaptive_six_policy_aggregate import (
    META_FEATURES,choose,global_validation_selector,knn_selector,
    dataset_bootstrap_ci
)

def make_reference():
    rows=[]
    for k in range(19):
      ds=f"other{k:02d}"
      for seed in (1,7,42):
       for policy in POLICY_ORDER:
        x={f:float(k+i%3) for i,f in enumerate(META_FEATURES)}
        x.update(dataset=ds,seed=seed,client_count=3,policy=policy)
        # deterministic results per reference domain, no target test
        for obj in OBJECTIVES:
          x["inner_val_"+obj] = 0.95 if policy=="SIMPLE_VOTING" else 0.2
          x["outer_test_"+obj] = 0.0 if policy=="SIMPLE_VOTING" else 1.0
        rows.append(x)
    return pd.DataFrame(rows)

def target():
    x={f:0.0 for f in META_FEATURES}
    x.update(dataset="heldout",seed=42,client_count=3)
    return pd.Series(x)

def test_policy_ties_are_deterministic():
    assert choose({p:0.5 for p in POLICY_ORDER})==POLICY_ORDER[0]
    assert choose({p:(0.8 if p=="GLOBAL_STRENGTH" else 0.4) for p in POLICY_ORDER})=="GLOBAL_STRENGTH"

def test_lodo_meta_excludes_target_dataset_and_never_reads_outer_test():
    ref=make_reference()
    choice,neighbors,forecast=knn_selector(target(),ref,"balanced_accuracy")
    fixed,_=global_validation_selector(target(),ref,"balanced_accuracy")
    assert choice=="SIMPLE_VOTING"
    assert fixed=="SIMPLE_VOTING"
    assert len(neighbors)==5 and "heldout" not in neighbors
    assert forecast["SIMPLE_VOTING"]>forecast["GLOBAL_STRENGTH"]
    # If every single outer TEST answer in the reference meta-database
    # changes, training/validation-based selection MUST remain identical.
    ref.loc[:,"outer_test_balanced_accuracy"]=np.random.default_rng(3).random(len(ref))
    assert knn_selector(target(),ref,"balanced_accuracy")[0]==choice
    assert global_validation_selector(target(),ref,"balanced_accuracy")[0]==fixed

def test_meta_fails_if_target_dataset_is_in_reference():
    ref=make_reference()
    row=ref.iloc[0].copy()
    row["dataset"]="heldout"
    ref=pd.concat([ref,pd.DataFrame([row])],ignore_index=True)
    with pytest.raises(AssertionError):
        knn_selector(target(),ref,"balanced_accuracy")

def test_meta_fails_without_19_other_independent_domains():
    x=make_reference()
    with pytest.raises(AssertionError):
        global_validation_selector(target(),x[x.dataset!="other00"],"accuracy")

def test_dataset_bootstrap_groups_multiple_seeds_as_one_domain():
    rows=[]
    for ds in range(20):
        for seed in (1,7,42):
            for client in (0,3):
                rows.append(dict(dataset=f"d{ds}",seed=seed,client_count=client,
                                method="LODO_META_KNN_5",outer_test_score_pct=70+ds*.01))
                rows.append(dict(dataset=f"d{ds}",seed=seed,client_count=client,
                                method="FIXED_GLOBAL_STRENGTH",outer_test_score_pct=65+ds*.01))
    stats=dataset_bootstrap_ci(pd.DataFrame(rows),"LODO_META_KNN_5","FIXED_GLOBAL_STRENGTH")
    assert stats["n_independent_dataset_clusters"]==20
    assert abs(stats["mean_gain_pp"]-5)<1e-9
    assert stats["dataset_improved"]==20
    assert 4.99<stats["ci95_low_pp"]<=stats["ci95_high_pp"]<5.01
