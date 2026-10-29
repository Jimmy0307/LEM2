from __future__ import annotations

import argparse
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from roughset.app import _run_split, discover_datasets
from roughset.evaluation import matching_rules
from roughset.splitting import stratified_train_test_split


POLICIES: tuple[str, ...] = (
    "FIRST_MATCH",
    "SIMPLE_VOTING",
    "STANDARD_VOTING",
    "GLOBAL_STRENGTH",
    "POPULATION_STANDARD",
    "POPULATION_GLOBAL",
)

SPLIT_MODES: tuple[str, ...] = ("FULL_DATA", "HOLDOUT_80_20")
DEFAULT_CLIENT_COUNTS: tuple[int, ...] = (2, 3, 4, 5)


def no_selection_metric_contract() -> dict[str, Any]:
    """Metrics that are undefined when no unique decision winner is requested."""
    return {
        "selection_layer": "NONE",
        "prediction_defined": False,
        "accuracy": float("nan"),
        "balanced_accuracy": float("nan"),
        "macro_f1": float("nan"),
    }


def build_factorial_design(
    datasets: Sequence[str],
    *,
    client_counts: Sequence[int] = DEFAULT_CLIENT_COUNTS,
) -> list[dict[str, Any]]:
    """Return the exact requested design before any model is executed.

    Per dataset / split mode:
      CENTRALIZED: NONE + 6 policies = 7 rows
      FEDERATED: 4 C values x (NONE + 6 policies) = 28 rows
      Total = 35 rows
    2 split modes x 3 datasets = 210 rows.
    """
    rows: list[dict[str, Any]] = []
    selections = ("NONE", *POLICIES)
    for dataset in datasets:
        for split_mode in SPLIT_MODES:
            for policy in selections:
                rows.append(
                    {
                        "dataset": dataset,
                        "split_mode": split_mode,
                        "system": "CENTRALIZED",
                        "client_count": 0,
                        "selection_policy": policy,
                    }
                )
            for client_count in client_counts:
                for policy in selections:
                    rows.append(
                        {
                            "dataset": dataset,
                            "split_mode": split_mode,
                            "system": "FEDERATED",
                            "client_count": int(client_count),
                            "selection_policy": policy,
                        }
                    )
    return rows


def _candidate_diagnostics(artifact, system: str) -> dict[str, Any]:
    rules = artifact.central_rules if system == "CENTRALIZED" else artifact.global_rules
    total = len(artifact.test)
    covered = 0
    conflicts = 0
    true_in_candidate = 0
    matched_rule_counts: list[int] = []
    candidate_counts: list[int] = []

    for _, row in artifact.test.iterrows():
        matched = matching_rules(row, rules)
        candidates = {str(rule.decision) for rule in matched}
        matched_rule_counts.append(len(matched))
        candidate_counts.append(len(candidates))
        if matched:
            covered += 1
        if len(candidates) > 1:
            conflicts += 1
        if str(row[artifact.target]) in candidates:
            true_in_candidate += 1

    no_match = total - covered
    return {
        "coverage": covered / total if total else float("nan"),
        "covered_count": covered,
        "no_match_count": no_match,
        "no_match_rate": no_match / total if total else float("nan"),
        "conflict_case_count": conflicts,
        "conflict_case_rate": conflicts / total if total else float("nan"),
        "true_in_candidate_count": true_in_candidate,
        "true_in_candidate_rate": true_in_candidate / total if total else float("nan"),
        "mean_matching_rules": float(np.mean(matched_rule_counts)) if matched_rule_counts else float("nan"),
        "mean_candidate_decisions": float(np.mean(candidate_counts)) if candidate_counts else float("nan"),
    }


def _structural_fields(artifact, system: str) -> dict[str, Any]:
    metrics = artifact.structural_metrics
    if system == "CENTRALIZED":
        rule_count = len(artifact.central_rules)
        reduct_size = (
            artifact.central_reduct_result.minimum_reduct_size
            if artifact.central_reduct_result is not None
            else len(artifact.condition_columns)
        )
        mean_local_reduct_size = float("nan")
        mean_local_rule_count = float("nan")
    else:
        rule_count = len(artifact.global_rules)
        reduct_size = float("nan")
        mean_local_reduct_size = metrics.get("mean_local_reduct_size", float("nan"))
        mean_local_rule_count = metrics.get("mean_local_rule_count", float("nan"))

    return {
        "rule_count": rule_count,
        "reduct_size": reduct_size,
        "mean_local_reduct_size": mean_local_reduct_size,
        "mean_local_rule_count": mean_local_rule_count,
        "rule_heterogeneity": metrics.get("rule_heterogeneity", float("nan")),
        "pairwise_rule_jaccard_full": metrics.get("pairwise_jaccard_full_rule", float("nan")),
        "pairwise_rule_jaccard_antecedent": metrics.get("pairwise_jaccard_antecedent", float("nan")),
    }


def _base_row(
    *,
    bundle,
    split_mode: str,
    system: str,
    client_count: int,
    artifact,
) -> dict[str, Any]:
    evaluation_scope = "RESUBSTITUTION_IN_SAMPLE" if split_mode == "FULL_DATA" else "HOLDOUT_OUT_OF_SAMPLE"
    return {
        "dataset": bundle.name,
        "source": bundle.source,
        "dataset_rows": len(bundle.frame),
        "system": system,
        "split_mode": split_mode,
        "evaluation_scope": evaluation_scope,
        "train_rows": len(artifact.train),
        "evaluation_rows": len(artifact.test),
        "client_count": client_count,
        "seed": artifact.seed,
        **_structural_fields(artifact, system),
        **_candidate_diagnostics(artifact, system),
    }


def _none_row(base: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **base,
        "selection_layer": "NONE",
        "selection_policy": "NONE",
        "prediction_defined": False,
        "accuracy": float("nan"),
        "balanced_accuracy": float("nan"),
        "macro_f1": float("nan"),
        "resolver_coverage": float("nan"),
        "conflict_resolution_accuracy": float("nan"),
        "conflict_balanced_accuracy": float("nan"),
        "conflict_macro_f1": float("nan"),
    }


def _policy_row(base: Mapping[str, Any], policy: str, output: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **base,
        "selection_layer": "ENABLED",
        "selection_policy": policy,
        "prediction_defined": True,
        "accuracy": output.get("accuracy"),
        "balanced_accuracy": output.get("balanced_accuracy"),
        "macro_f1": output.get("macro_f1"),
        "resolver_coverage": output.get("coverage"),
        "conflict_resolution_accuracy": output.get("conflict_resolution_accuracy"),
        "conflict_balanced_accuracy": output.get("conflict_balanced_accuracy"),
        "conflict_macro_f1": output.get("conflict_macro_f1"),
    }


def _split_raw(bundle, split_mode: str, seed: int, test_ratio: float):
    raw = bundle.frame.copy().reset_index(drop=True)
    raw["__row_id__"] = np.arange(len(raw), dtype=int)
    if split_mode == "FULL_DATA":
        return raw.copy(), raw.copy()
    if split_mode == "HOLDOUT_80_20":
        return stratified_train_test_split(raw, bundle.target, test_ratio, seed)
    raise ValueError(f"Unsupported split_mode: {split_mode}")


def _run_block(
    bundle,
    base_config: Mapping[str, Any],
    *,
    split_mode: str,
    system: str,
    client_count: int,
) -> list[dict[str, Any]]:
    cfg = deepcopy(base_config)
    cfg["evaluation"]["mode"] = split_mode
    cfg["federated"]["run_client_sweep"] = False
    # Order permutation auditing is not a factor in this matrix. Reducing the
    # audit count does not change the selected prediction for the canonical
    # client order; it only avoids re-running diagnostic permutations.
    cfg["federated"]["order_sensitivity_max_permutations"] = 1

    if system == "CENTRALIZED":
        cfg["experiment"]["run_centralized"] = True
        cfg["experiment"]["run_federated"] = False
        cfg["federated"]["n_clients"] = 0
    elif system == "FEDERATED":
        cfg["experiment"]["run_centralized"] = False
        cfg["experiment"]["run_federated"] = True
        cfg["federated"]["n_clients"] = int(client_count)
    else:
        raise ValueError(system)

    seed = int(base_config["evaluation"]["seed"])
    test_ratio = float(base_config["evaluation"]["test_ratio"])
    raw_train, raw_test = _split_raw(bundle, split_mode, seed, test_ratio)

    result = _run_split(
        bundle,
        raw_train,
        raw_test,
        cfg,
        quiet=True,
        prediction_policies=POLICIES,
        fold=1,
    )
    artifact = result["structural_artifact"]
    base = _base_row(
        bundle=bundle,
        split_mode=split_mode,
        system=system,
        client_count=client_count,
        artifact=artifact,
    )

    rows = [_none_row(base)]
    key = "centralized" if system == "CENTRALIZED" else "federated"
    for policy in POLICIES:
        output = result["policy_results"][policy][key]
        if output is None:
            raise RuntimeError(f"Missing {system} output for {bundle.name} {split_mode} {policy}")
        rows.append(_policy_row(base, policy, output))
    return rows


def run_full_factorial(
    base_config: Mapping[str, Any],
    bundles: Iterable[Any],
    *,
    client_counts: Sequence[int] = DEFAULT_CLIENT_COUNTS,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    bundles = list(bundles)
    expected = build_factorial_design([bundle.name for bundle in bundles], client_counts=client_counts)

    for bundle in bundles:
        for split_mode in SPLIT_MODES:
            rows.extend(
                _run_block(
                    bundle,
                    base_config,
                    split_mode=split_mode,
                    system="CENTRALIZED",
                    client_count=0,
                )
            )
            for client_count in client_counts:
                rows.extend(
                    _run_block(
                        bundle,
                        base_config,
                        split_mode=split_mode,
                        system="FEDERATED",
                        client_count=int(client_count),
                    )
                )

    frame = pd.DataFrame(rows)
    if len(frame) != len(expected):
        raise AssertionError(f"factorial row count mismatch: got {len(frame)}, expected {len(expected)}")
    return frame


def _write_outputs(frame: pd.DataFrame, output: Path, base_config: Mapping[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output / "FULL_FACTORIAL_RESULTS.csv", index=False, encoding="utf-8-sig")

    baselines = frame[frame["selection_policy"] == "NONE"].copy()
    policies = frame[frame["selection_policy"] != "NONE"].copy()
    baselines.to_csv(output / "FULL_FACTORIAL_BASELINES.csv", index=False, encoding="utf-8-sig")
    policies.to_csv(output / "FULL_FACTORIAL_POLICY_RESULTS.csv", index=False, encoding="utf-8-sig")

    metric_cols = ["accuracy", "balanced_accuracy", "macro_f1", "resolver_coverage"]
    means = (
        policies.groupby(["system", "split_mode", "selection_policy"], dropna=False)[metric_cols]
        .mean()
        .reset_index()
    )
    means.to_csv(output / "FULL_FACTORIAL_POLICY_MEANS.csv", index=False, encoding="utf-8-sig")

    by_client = (
        policies.groupby(
            ["system", "split_mode", "client_count", "selection_policy"],
            dropna=False,
        )[metric_cols]
        .mean()
        .reset_index()
    )
    by_client.to_csv(
        output / "FULL_FACTORIAL_POLICY_MEANS_BY_CLIENT_COUNT.csv",
        index=False,
        encoding="utf-8-sig",
    )

    structural_cols = [
        "coverage",
        "conflict_case_rate",
        "true_in_candidate_rate",
        "rule_count",
        "mean_local_rule_count",
    ]
    structural_means = (
        baselines.groupby(["system", "split_mode", "client_count"], dropna=False)[structural_cols]
        .mean()
        .reset_index()
    )
    structural_means.to_csv(
        output / "FULL_FACTORIAL_BASELINE_MEANS.csv",
        index=False,
        encoding="utf-8-sig",
    )

    manifest = {
        "schema_version": 1,
        "datasets": sorted(frame["dataset"].unique().tolist()),
        "row_count": int(len(frame)),
        "baseline_rows": int(len(baselines)),
        "policy_rows": int(len(policies)),
        "split_modes": list(SPLIT_MODES),
        "policies": list(POLICIES),
        "client_counts": sorted(int(x) for x in frame.loc[frame["system"] == "FEDERATED", "client_count"].unique()),
        "seed": int(base_config["evaluation"]["seed"]),
        "test_ratio": float(base_config["evaluation"]["test_ratio"]),
        "interpretation": {
            "NONE": "Pure rule-induction / candidate-structure baseline; no unique prediction is selected, therefore Accuracy/BA/Macro-F1 are NA.",
            "FULL_DATA": "100% of rows induce the rules; policy metrics are resubstitution/in-sample and are not generalization estimates.",
            "HOLDOUT_80_20": "Stratified seed=42 80/20 split; policy metrics are out-of-sample holdout results.",
            "conflict": "One evaluated object matches induced rules pointing to more than one decision class before a selection policy chooses a winner.",
        },
    }
    (output / "FULL_FACTORIAL_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _validate_runtime_output(frame: pd.DataFrame) -> None:
    if len(frame) != 210:
        raise AssertionError(f"Expected 210 rows, got {len(frame)}")
    none = frame[frame["selection_policy"] == "NONE"]
    selected = frame[frame["selection_policy"] != "NONE"]
    if len(none) != 30 or len(selected) != 180:
        raise AssertionError(f"Expected 30 baseline + 180 policy rows, got {len(none)} + {len(selected)}")
    if not none[["accuracy", "balanced_accuracy", "macro_f1"]].isna().all().all():
        raise AssertionError("NONE rows must not claim prediction metrics")
    if not selected[["accuracy", "balanced_accuracy", "macro_f1"]].notna().all().all():
        raise AssertionError("Policy rows must contain prediction metrics")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--output", default="outputs/teacher_full_factorial_20261029")
    args = parser.parse_args()

    config_path = Path(args.config)
    base_config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    # Dataset discovery deliberately uses the untouched HOLDOUT config because
    # discover_datasets validates supported application modes. FULL_DATA is a
    # teacher-demo experimental wrapper around the same frozen rule pipeline.
    bundles = discover_datasets(base_config)
    names = [bundle.name for bundle in bundles]
    expected_names = {"Hayes-Roth", "Car Evaluation", "Balance Scale"}
    if set(names) != expected_names:
        raise AssertionError(f"Unexpected UCI dataset set: {names}")

    frame = run_full_factorial(base_config, bundles)
    _validate_runtime_output(frame)
    output = Path(args.output)
    _write_outputs(frame, output, base_config)

    print("FULL_FACTORIAL_VERDICT=PASS")
    print(f"DATASETS={len(names)}")
    print(f"ROWS={len(frame)}")
    print(f"BASELINE_ROWS={(frame['selection_policy'] == 'NONE').sum()}")
    print(f"POLICY_ROWS={(frame['selection_policy'] != 'NONE').sum()}")
    print(f"OUTPUT={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
