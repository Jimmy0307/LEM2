"""A new *separate* LEM2 evaluation; never rewrites frozen 188x42 results.

All arms use the exact same outer 20% Test for each source/seed.
Selection is fitted on 60% Development and 20% Validation. The winning
policy is frozen before an optional re-fit on the outer 80% Training rows.
Test truth is passed only to final metrics, never to policy selection.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from fedrs.experiment import fit_model
from fedrs.metrics import scores
from fedrs.partition import constrained_partition, original_partition
from fedrs.predict import POLICIES, candidate_profile, match_matrix, resolve_scalable, variant_matrix
from roughset.preprocessing import detect_feature_types
from roughset.splitting import stratified_train_test_split

SCENARIOS = ("CENTRALIZED", "FED_IID", "FED_A05", "FED_A01")
REGIME = {"FED_IID": "IID", "FED_A05": "NONIID_05", "FED_A01": "NONIID_01"}
VARIANTS = ("A_ALL_RULES", "B2_TRUE_AS_FALLBACK")
# Must be frozen BEFORE observing validation and test. Stable tie breaks.
POLICY_TIE_ORDER = (
    "STANDARD_VOTING", "SIMPLE_VOTING", "GLOBAL_STRENGTH",
    "POPULATION_STANDARD", "POPULATION_GLOBAL", "FIRST_MATCH",
)
assert set(POLICY_TIE_ORDER) == set(POLICIES)


@dataclass
class SplitContract:
    outer_train: pd.DataFrame
    dev60: pd.DataFrame
    val20: pd.DataFrame
    dev64: pd.DataFrame
    val16: pd.DataFrame
    test20: pd.DataFrame


def make_splits(frame: pd.DataFrame, target: str, seed: int) -> SplitContract:
    """60/20/20 and 64/16/20 share the identical *original* 80/20 Test.

    25% of outer80 = 20% of source; 20% of outer80 = 16% of source.
    Both splits are stratified using exactly the original repo function.
    """
    if target not in frame:
        raise KeyError(target)
    df = frame.copy().reset_index(drop=True)
    df["__row_id__"] = np.arange(len(df), dtype=int)
    outer80, test20 = stratified_train_test_split(df, target, .20, seed=seed)
    dev60, val20 = stratified_train_test_split(outer80, target, .25, seed=1000 + seed)
    dev64, val16 = stratified_train_test_split(outer80, target, .20, seed=1000 + seed)
    all_ids = set(df["__row_id__"])
    assert all_ids == set(outer80["__row_id__"]) | set(test20["__row_id__"])
    assert not (set(outer80["__row_id__"]) & set(test20["__row_id__"]))
    for dev, val in ((dev60, val20), (dev64, val16)):
        assert set(dev["__row_id__"]).isdisjoint(set(val["__row_id__"]))
        assert set(dev["__row_id__"]) | set(val["__row_id__"]) == set(outer80["__row_id__"])
    return SplitContract(outer80, dev60, val20, dev64, val16, test20)


def choose_by_validation(
    y_val: Sequence[str], predictions: Mapping[str, Sequence[str]],
    metric: str = "ba",
) -> tuple[str, dict[str, float]]:
    """Never accepts test labels or test predictions; only Val ground truth.

    Accuracy and Balanced Accuracy may select different policies.
    """
    if metric not in ("accuracy", "ba"):
        raise ValueError("selection metric must be accuracy or ba")
    if not len(y_val):
        raise ValueError("Validation must be nonempty")
    if set(predictions) != set(POLICY_TIE_ORDER):
        raise ValueError("all six policy predictions required")
    performance = {p: float(scores(y_val, predictions[p])[metric]) for p in POLICY_TIE_ORDER}
    best = max(POLICY_TIE_ORDER, key=lambda p: performance[p])
    return best, performance


def _clients(dev: pd.DataFrame, target: str, scenario: str, seed: int):
    if scenario == "CENTRALIZED":
        return {"central": dev}, "CENTRALIZED"
    if scenario not in REGIME:
        raise ValueError("unsupported scenario: " + str(scenario))
    try:
        return original_partition(dev, target, 3, seed, REGIME[scenario]), "ORIGINAL"
    except ValueError:
        clients, attempts, status = constrained_partition(dev, target, 3, seed, REGIME[scenario])
        if clients is None:
            raise RuntimeError(f"PARTITION_FAILED attempts={attempts}, status={status}")
        return clients, "CONSTRAINED_" + status


def _fit(features, continuous, categorical, target, dev, val, test, scenario, seed):
    clients, partition_status = _clients(dev, target, scenario, seed)
    t0 = perf_counter()
    fm = fit_model(features, continuous, categorical, target, clients, dev, val, test,
                   discretizer="EQUAL_WIDTH_3", induction="CLASSICAL", beta=1.0)
    return fm, partition_status, perf_counter() - t0


def _variant_match(fm, split: str, variant: str):
    return variant_matrix(match_matrix(fm.frames[split], fm.rules), fm.ctx, variant)


def _test_metrics(fm, matrix, policy):
    truth = fm.frames["test"][fm.target].astype(str).to_numpy()
    pred = resolve_scalable(matrix, fm.ctx, policy)
    return scores(truth, pred)


def _row(dataset, seed, scenario, variant, contract, arm, train, validation,
         fm, partition_status, policy, selected_policy, selection_metric,
         validation_scores, selected_on_validation, selection_fit_s):
    M = _variant_match(fm, "test", variant)
    pred = _test_metrics(fm, M, policy)
    profile = candidate_profile(M, fm.ctx, fm.frames["test"][fm.target].astype(str).to_numpy())
    baseline = np.full(len(M), fm.ctx.default_class, dtype=object)
    y = fm.frames["test"][fm.target].astype(str).to_numpy()
    base_scores = scores(y, baseline)
    return {
        "dataset": dataset, "seed": seed, "scenario": scenario,
        "rule_variant": variant, "split_contract": contract,
        "arm": arm, "train_rows": len(train), "validation_rows": len(validation),
        "test_rows": len(fm.frames["test"]), "client_partition": partition_status,
        "selection_metric": selection_metric, "selected_policy_on_val": selected_policy,
        "policy_used_on_test": policy,
        "selected_validation_mean": selected_on_validation if selected_policy else np.nan,
        "val_stv": validation_scores.get("STANDARD_VOTING", np.nan),
        "test_accuracy": float(pred["accuracy"]),
        "test_ba": float(pred["ba"]), "test_macro_f1": float(pred["macro_f1"]),
        "majority_only_test_accuracy": float(base_scores["accuracy"]),
        "majority_only_test_ba": float(base_scores["ba"]),
        "test_conflict": float(profile["multi"].mean()),
        "test_coverage": float((~profile["no_hit"]).mean()),
        "test_candidate_coverage": float(profile["truth_in_candidates"].mean()),
        "rule_count": len(fm.rules), "select_fit_seconds": selection_fit_s,
    }


def run_one(frame: pd.DataFrame, target: str, features: Sequence[str],
            dataset: str, seed: int, scenario: str, variant: str = "B2_TRUE_AS_FALLBACK",
            selection_metric: str = "ba", include_legacy: bool = False) -> list[dict]:
    """Produces comparable test rows without reading Test when selecting.

    Main contrast:
    REFIT80_VAL_SELECTED vs FIXED80_STV uses identical fitted 80% rules.
    Therefore its paired delta isolates policy selection, not training size.
    """
    if scenario not in SCENARIOS or variant not in VARIANTS:
        raise ValueError("Invalid scenario/variant")
    feature_list = list(features)
    if not 1 <= len(feature_list) <= 6:
        raise ValueError("This pilot accepts 1-6 features only; >6 is a separate ablation")
    if target in feature_list or len(set(feature_list)) != len(feature_list):
        raise ValueError("Target leakage or repeated feature")
    if frame[feature_list + [target]].isna().any().any():
        raise ValueError("Missing-value algorithm is not specified: no silent imputation")
    cuts = make_splits(frame[feature_list + [target]], target, seed)
    continuous, categorical = detect_feature_types(cuts.dev60, feature_list, unique_numeric_threshold=10)
    stage, stage_status, stage_fit_seconds = _fit(feature_list, continuous, categorical, target,
        cuts.dev60, cuts.val20, cuts.test20, scenario, seed)
    M_val = _variant_match(stage, "val", variant)
    y_val = stage.frames["val"][target].astype(str).to_numpy()
    val_predictions = {p: resolve_scalable(M_val, stage.ctx, p) for p in POLICY_TIE_ORDER}
    selected, val_scores = choose_by_validation(y_val, val_predictions, selection_metric)
    val_best = val_scores[selected]
    rows = [_row(dataset, seed, scenario, variant, "60_20_20", "STAGED60_VAL_SELECTED",
                 cuts.dev60, cuts.val20, stage, stage_status, selected, selected,
                 selection_metric, val_scores, val_best, stage_fit_seconds)]
    empty_validation = cuts.outer_train.iloc[:0].copy()
    full, full_status, full_fit_seconds = _fit(feature_list, continuous, categorical, target,
        cuts.outer_train, empty_validation, cuts.test20, scenario, seed)
    for arm, policy in (("REFIT80_VAL_SELECTED", selected), ("FIXED80_STV", "STANDARD_VOTING")):
        rows.append(_row(dataset, seed, scenario, variant, "80_20", arm,
            cuts.outer_train, empty_validation, full, full_status, policy, selected,
            selection_metric, val_scores, val_best, full_fit_seconds))
    if include_legacy:
        old, old_status, old_fit_s = _fit(feature_list, continuous, categorical, target,
            cuts.dev64, cuts.val16, cuts.test20, scenario, seed)
        old_matrix = _variant_match(old, "val", variant)
        old_truth = old.frames["val"][target].astype(str).to_numpy()
        old_predictions = {p: resolve_scalable(old_matrix, old.ctx, p) for p in POLICY_TIE_ORDER}
        old_selected, old_scores = choose_by_validation(old_truth, old_predictions, selection_metric)
        for arm, policy in (("LEGACY64_VAL_SELECTED", old_selected), ("LEGACY64_FIXED_STV", "STANDARD_VOTING")):
            rows.append(_row(dataset, seed, scenario, variant, "64_16_20", arm,
                             cuts.dev64, cuts.val16, old, old_status, policy,
                             old_selected, selection_metric, old_scores, old_scores[old_selected], old_fit_s))
    # In all arms Test remains byte-for-byte identical source rows for the seed.
    return rows
