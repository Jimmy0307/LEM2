"""Gate 0 parity: fedrs must reproduce the original pipeline EXACTLY.

Compares, on real UCI prepared sources and the original nested protocol:
  * equal-width-3 discretized tables,
  * the global UNION rule list (keys and order, incl. TRUE -> d rules),
  * all six policies' validation predictions (vs roughset.app._run_split),
  * all six policies' outer-test predictions (vs roughset.evaluation.evaluate_rule_model),
  * the published G4 router Test BA / coverage / conflict (historical CSV).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from roughset.app import _run_split  # noqa: E402
from roughset.evaluation import evaluate_rule_model  # noqa: E402
from roughset.preprocessing import apply_preprocessor  # noqa: E402
from teacher_demo.conflict_aware_coverage_pilot import load_bundle  # noqa: E402
from teacher_demo.continuous_controlled_runner import root_config  # noqa: E402

from fedrs.experiment import evaluate, fit_model, nested_split  # noqa: E402
from fedrs.partition import original_partition  # noqa: E402
from fedrs.predict import POLICIES, resolve  # noqa: E402

CASES = [("iris", 11, "NONIID_05"), ("covertype", 11, "NONIID_01"), ("german_credit", 23, "NONIID_05")]
HISTORICAL = ROOT / "docs/research/teacher_dashboard/data/G4_ROUTER_UCI20_NEW_SEEDS_RESULTS.csv"


@pytest.mark.parametrize("name,seed,regime", CASES)
def test_fedrs_reproduces_original_pipeline(name, seed, regime):
    bundle, _ = load_bundle(name)
    dev, val, test = nested_split(bundle.frame, bundle.target, seed)
    cfg = root_config(seed, regime)
    original = _run_split(bundle, dev, val, cfg, quiet=True, prediction_policies=POLICIES, fold=1)
    art = original["structural_artifact"]

    raw_clients = original_partition(dev, bundle.target, 3, seed, regime)
    fm = fit_model(bundle.features, bundle.schema.continuous, bundle.schema.categorical, bundle.target,
                   raw_clients, dev, val, test, "EQUAL_WIDTH_3")

    # discretization identical
    orig_val = apply_preprocessor(val, original["preprocessor"], bundle.target)
    for col in fm.cond_cols:
        assert (fm.frames["val"][col].astype(str).to_numpy() == orig_val[col].astype(str).to_numpy()).all(), col

    # rules identical, same order
    assert [r.key for r in fm.rules] == [r.key for r in art.global_rules]
    assert fm.ctx.default_class == str(art.default_class)

    res = evaluate(fm, regime)
    Mv, Mt = res["matrices"]["val"], res["matrices"]["test"]
    outer = apply_preprocessor(test, original["preprocessor"], bundle.target)
    for policy in POLICIES:
        expected_val = np.asarray([str(x) for x in original["policy_results"][policy]["federated"]["predictions"]], dtype=object)
        assert (resolve(Mv, fm.ctx, policy) == expected_val).all(), ("val", policy)
        ref = evaluate_rule_model(outer, art.global_rules, art.default_class, art.target, prediction_policy=policy,
                                  rule_weights=art.global_rule_weights, rule_support_sets=art.global_rule_support_sets,
                                  class_sizes=art.global_class_sizes)
        assert (resolve(Mt, fm.ctx, policy) == np.asarray([str(x) for x in ref["predictions"]], dtype=object)).all(), ("test", policy)

    # published historical router numbers reproduced
    hist = pd.read_csv(HISTORICAL)
    row = hist[(hist.dataset == name) & (hist.seed == seed) & (hist.scenario == regime)
               & (hist.method == "CONFLICT_BUCKET_ROUTER_V1")].iloc[0]
    mine = [r for r in res["policies"] if r["rule_variant"] == "A_ALL_RULES" and r["method"] == "CONFLICT_BUCKET_ROUTER_V1"][0]
    assert abs(mine["test_ba"] - row.outer_test_balanced_accuracy) < 1e-9
    st = [r for r in res["structure"] if r["split"] == "test" and r["rule_variant"] == "A_ALL_RULES"][0]
    assert abs(st["coverage"] - row.outer_test_coverage) < 1e-9
    assert abs(st["conflict_rate"] - row.outer_test_conflict) < 1e-9
