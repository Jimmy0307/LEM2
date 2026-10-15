from __future__ import annotations

from collections import defaultdict
import itertools
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

from .core import Rule, induce_lem2
from .evaluation import (
    majority_class, majority_class_from_clients, fit_rule_weights, fit_rule_support_sets,
    aggregate_rule_support_context, aggregate_rule_weights, pairwise_rule_jaccard,
    audit_rule_conflicts, audit_conflict_cases, evaluate_rule_model, predict_table,
)

def stratified_client_partition(train_df, target_col, n_clients=5, seed=42):
    if n_clients < 1:
        raise ValueError("n_clients must be >= 1")

    rng = np.random.default_rng(seed)
    buckets: List[List[int]] = [[] for _ in range(n_clients)]

    for _, group in train_df.groupby(target_col, sort=False):
        ids = group.index.to_numpy(copy=True)
        rng.shuffle(ids)
        for i, row_id in enumerate(ids):
            buckets[i % n_clients].append(int(row_id))

    clients: Dict[str, pd.DataFrame] = {}
    for i, ids in enumerate(buckets, 1):
        if not ids:
            raise ValueError(
                f"Client_{i} received no rows. Reduce n_clients for this dataset/split."
            )
        clients[f"Client_{i}"] = train_df.loc[ids].copy().reset_index(drop=True)

    return clients


def dirichlet_label_skew_partition(
    train_df: pd.DataFrame,
    target_col: str,
    n_clients: int = 5,
    alpha: float = 0.5,
    seed: int = 42,
    max_retries: int = 100,
) -> Dict[str, pd.DataFrame]:
    """Partition training rows with class-conditional Dirichlet label skew.

    For each decision class k:
        p_k ~ Dirichlet(alpha * 1_C)
        n_k1,...,n_kC ~ Multinomial(n_k, p_k)

    Mathematical invariants enforced by construction:
    1) every training row is assigned to exactly one client;
    2) client partitions are pairwise disjoint;
    3) the union of client partitions equals the full training set.

    Empty clients are rejected and the deterministic RNG stream continues to the
    next retry.  Therefore identical (data, seed, alpha, C) gives identical output.
    """
    if n_clients < 1:
        raise ValueError("n_clients must be >= 1")
    if float(alpha) <= 0:
        raise ValueError("alpha must be > 0")
    if int(max_retries) < 1:
        raise ValueError("max_retries must be >= 1")
    if len(train_df) < n_clients:
        raise ValueError(
            f"Cannot create {n_clients} non-empty clients from only {len(train_df)} rows."
        )

    rng = np.random.default_rng(seed)
    client_names = [f"Client_{i}" for i in range(1, n_clients + 1)]

    for _attempt in range(int(max_retries)):
        buckets: Dict[str, List[Any]] = {name: [] for name in client_names}

        for _, group in train_df.groupby(target_col, sort=False, dropna=False):
            row_ids = group.index.to_numpy(copy=True)
            rng.shuffle(row_ids)

            proportions = rng.dirichlet(np.full(n_clients, float(alpha), dtype=float))
            counts = rng.multinomial(len(row_ids), proportions)

            start = 0
            for client_name, count in zip(client_names, counts):
                stop = start + int(count)
                if stop > start:
                    buckets[client_name].extend(row_ids[start:stop].tolist())
                start = stop

            # Multinomial counts must consume the class exactly.
            if start != len(row_ids):
                raise AssertionError("Dirichlet partition failed to consume a class exactly.")

        if all(buckets[name] for name in client_names):
            assigned = [idx for name in client_names for idx in buckets[name]]
            if len(assigned) != len(train_df):
                raise AssertionError("Dirichlet partition lost or duplicated rows by count.")
            if len(set(assigned)) != len(assigned):
                raise AssertionError("Dirichlet partition assigned a row to multiple clients.")
            if set(assigned) != set(train_df.index.tolist()):
                raise AssertionError("Dirichlet partition union does not equal the training set.")

            return {
                name: train_df.loc[buckets[name]].copy().reset_index(drop=True)
                for name in client_names
            }

    raise ValueError(
        "DIRICHLET_LABEL_SKEW could not produce all non-empty clients within "
        f"{max_retries} deterministic retries. Increase alpha, reduce n_clients, "
        "or increase dirichlet_max_retries."
    )


def partition_clients(
    train_df: pd.DataFrame,
    target_col: str,
    n_clients: int = 5,
    seed: int = 42,
    strategy: str = "STRATIFIED",
    dirichlet_alpha: float = 0.5,
    dirichlet_max_retries: int = 100,
) -> Dict[str, pd.DataFrame]:
    """Dispatch a mathematically explicit federated partition strategy."""
    strategy = str(strategy).strip().upper()
    if strategy == "STRATIFIED":
        return stratified_client_partition(
            train_df, target_col=target_col, n_clients=n_clients, seed=seed
        )
    if strategy == "DIRICHLET_LABEL_SKEW":
        return dirichlet_label_skew_partition(
            train_df,
            target_col=target_col,
            n_clients=n_clients,
            alpha=dirichlet_alpha,
            seed=seed,
            max_retries=dirichlet_max_retries,
        )
    raise ValueError(
        "strategy must be STRATIFIED or DIRICHLET_LABEL_SKEW."
    )

def _client_orderings(
    client_names: Sequence[str],
    max_permutations: int = 120,
    seed: int = 42,
) -> List[Tuple[str, ...]]:
    names = tuple(client_names)
    if len(names) <= 1:
        return [names]

    factorial = math.factorial(len(names))
    if factorial <= max_permutations:
        return list(itertools.permutations(names))

    # Uniform random permutations with rejection of duplicates.  Do not force the
    # original client order into the sample, because that would overweight one
    # specific ordering when factorial(C) > max_permutations.
    rng = np.random.default_rng(seed)
    seen: Set[Tuple[str, ...]] = set()
    orders: List[Tuple[str, ...]] = []
    attempts = 0
    max_attempts = max_permutations * 100
    while len(orders) < max_permutations and attempts < max_attempts:
        candidate = tuple(rng.permutation(names).tolist())
        if candidate not in seen:
            seen.add(candidate)
            orders.append(candidate)
        attempts += 1
    return orders


def audit_order_sensitivity(
    test: pd.DataFrame,
    local_rules: Mapping[str, Sequence["Rule"]],
    default_class: Any,
    prediction_policy: str,
    rule_weights: Optional[Mapping[Any, float]] = None,
    rule_support_sets: Optional[Mapping[Any, Set[Any]]] = None,
    class_sizes: Optional[Mapping[Any, int]] = None,
    conflict_case_flags: Optional[Sequence[bool]] = None,
    max_permutations: int = 120,
    seed: int = 42,
) -> Dict[str, Any]:
    """How often predictions change when client arrival order changes."""
    orders = _client_orderings(list(local_rules), max_permutations=max_permutations, seed=seed)
    if not orders or len(test) == 0:
        return {
            "orderings_checked": len(orders),
            "order_sensitivity_rate": 0.0,
            "order_sensitivity_conflict_rate": float("nan"),
        }

    predictions_by_order: List[List[Any]] = []
    for order in orders:
        ordered = {name: local_rules[name] for name in order}
        ordered_global_rules = union_rules(ordered)
        preds, _ = predict_table(
            test,
            ordered_global_rules,
            default_class,
            prediction_policy=prediction_policy,
            rule_weights=rule_weights,
            rule_support_sets=rule_support_sets,
            class_sizes=class_sizes,
        )
        predictions_by_order.append([str(x) for x in preds])

    matrix = np.asarray(predictions_by_order, dtype=object)
    sensitive = np.array([len(set(matrix[:, j].tolist())) > 1 for j in range(matrix.shape[1])])
    overall = float(sensitive.mean()) if len(sensitive) else 0.0

    conflict_only = float("nan")
    if conflict_case_flags is not None:
        conflict_mask = np.asarray(conflict_case_flags, dtype=bool)
        if conflict_mask.any():
            conflict_only = float(sensitive[conflict_mask].mean())

    return {
        "orderings_checked": len(orders),
        "order_sensitivity_rate": overall,
        "order_sensitivity_conflict_rate": conflict_only,
    }


def _finite_summary(values: Sequence[float], prefix: str) -> Dict[str, float]:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {
            f"{prefix}_mean": float("nan"),
            f"{prefix}_std": float("nan"),
            f"{prefix}_min": float("nan"),
            f"{prefix}_max": float("nan"),
        }
    return {
        f"{prefix}_mean": float(arr.mean()),
        f"{prefix}_std": float(arr.std(ddof=0)),
        f"{prefix}_min": float(arr.min()),
        f"{prefix}_max": float(arr.max()),
    }


def audit_order_distribution(
    test: pd.DataFrame,
    local_rules: Mapping[str, Sequence["Rule"]],
    default_class: Any,
    target: str,
    prediction_policy: str,
    rule_weights: Optional[Mapping[Any, float]] = None,
    rule_support_sets: Optional[Mapping[Any, Set[Any]]] = None,
    class_sizes: Optional[Mapping[Any, int]] = None,
    max_permutations: int = 120,
    seed: int = 42,
) -> Dict[str, Any]:
    """Evaluate prediction metrics over client-arrival permutations.

    For a fixed client count C and fixed learned local rules, this isolates the
    order effect induced by UNION + FIRST_MATCH from the client-count effect.
    Metrics are recomputed for every checked client order and summarized by
    population mean/std/min/max.  Conflict cases are defined by the order-invariant
    set of all matching global rules; CRA is then evaluated per order.
    """
    orders = _client_orderings(
        list(local_rules), max_permutations=max_permutations, seed=seed
    )
    if not orders or len(test) == 0:
        empty = pd.DataFrame()
        total_possible = math.factorial(len(local_rules)) if len(local_rules) > 1 else 1
        out: Dict[str, Any] = {
            "order_distribution_table": empty,
            "orderings_checked": len(orders),
            "total_possible_orderings": total_possible,
            "order_sampling_complete": len(orders) == total_possible,
            "order_sensitivity_rate": 0.0,
            "order_sensitivity_conflict_rate": float("nan"),
        }
        for name in (
            "order_accuracy",
            "order_balanced_accuracy",
            "order_macro_f1",
            "order_coverage",
            "order_conflict_resolution_accuracy",
        ):
            out.update(_finite_summary([], name))
        return out

    # The set of global full rules is invariant to client order; only ordering changes.
    reference_rules = union_rules(local_rules)
    dummy_predictions = [default_class] * len(test)
    reference_conflicts = audit_conflict_cases(
        test=test,
        rules=reference_rules,
        predictions=dummy_predictions,
        target=target,
    )
    conflict_flags = np.asarray(reference_conflicts["conflict_case_flags"], dtype=bool)

    rows: List[Dict[str, Any]] = []
    predictions_by_order: List[List[str]] = []

    for order in orders:
        ordered_local = {name: local_rules[name] for name in order}
        ordered_rules = union_rules(ordered_local)
        metrics = evaluate_rule_model(
            test=test,
            rules=ordered_rules,
            default_class=default_class,
            target=target,
            prediction_policy=prediction_policy,
            rule_weights=rule_weights,
            rule_support_sets=rule_support_sets,
            class_sizes=class_sizes,
        )
        case_audit = audit_conflict_cases(
            test=test,
            rules=ordered_rules,
            predictions=metrics["predictions"],
            target=target,
        )
        predictions_by_order.append([str(x) for x in metrics["predictions"]])
        rows.append({
            "client_order": " -> ".join(order),
            "accuracy": metrics["accuracy"],
            "balanced_accuracy": metrics["balanced_accuracy"],
            "macro_f1": metrics["macro_f1"],
            "coverage": metrics["coverage"],
            "conflict_resolution_accuracy": case_audit["conflict_resolution_accuracy"],
        })

    table = pd.DataFrame(rows)
    matrix = np.asarray(predictions_by_order, dtype=object)
    sensitive = np.array([
        len(set(matrix[:, j].tolist())) > 1
        for j in range(matrix.shape[1])
    ], dtype=bool)
    order_sensitivity_rate = float(sensitive.mean()) if sensitive.size else 0.0
    order_sensitivity_conflict_rate = (
        float(sensitive[conflict_flags].mean())
        if conflict_flags.any()
        else float("nan")
    )

    total_possible = math.factorial(len(local_rules)) if len(local_rules) > 1 else 1
    out = {
        "order_distribution_table": table,
        "orderings_checked": len(orders),
        "total_possible_orderings": total_possible,
        "order_sampling_complete": len(orders) == total_possible,
        "order_sensitivity_rate": order_sensitivity_rate,
        "order_sensitivity_conflict_rate": order_sensitivity_conflict_rate,
    }
    out.update(_finite_summary(table["accuracy"].tolist(), "order_accuracy"))
    out.update(_finite_summary(table["balanced_accuracy"].tolist(), "order_balanced_accuracy"))
    out.update(_finite_summary(table["macro_f1"].tolist(), "order_macro_f1"))
    out.update(_finite_summary(table["coverage"].tolist(), "order_coverage"))
    out.update(_finite_summary(
        table["conflict_resolution_accuracy"].tolist(),
        "order_conflict_resolution_accuracy",
    ))
    return out

def union_rules_with_provenance(
    local_rules: Mapping[str, Sequence[Rule]],
) -> Tuple[List[Rule], Dict[Any, Tuple[str, ...]]]:
    """UNION aggregation plus complete source provenance.

    Rule identity remains exactly the existing mathematical/code definition:
        key = (sorted antecedent conditions, decision)

    UNION keeps the first occurrence only to preserve first-match ordering, but
    provenance records *every* client that independently produced the same rule.
    This separates two concepts that must not be conflated:
      - global rule order (needed for FIRST_MATCH), and
      - source multiplicity (needed for later collaborative weighting/auditing).
    """
    merged: List[Rule] = []
    seen: Set[Any] = set()
    source_sets: Dict[Any, Set[str]] = defaultdict(set)

    for client_name, rules in local_rules.items():
        for rule in rules:
            source_sets[rule.key].add(str(client_name))
            if rule.key not in seen:
                seen.add(rule.key)
                merged.append(rule)

    provenance = {
        key: tuple(sorted(values, key=str))
        for key, values in source_sets.items()
    }
    return merged, provenance


def union_rules(local_rules: Mapping[str, Sequence[Rule]]) -> List[Rule]:
    """Backward-compatible UNION rule list without exposing provenance."""
    merged, _ = union_rules_with_provenance(local_rules)
    return merged


def run_federated(
    clients: Mapping[str, pd.DataFrame],
    test: pd.DataFrame,
    condition_columns: Sequence[str],
    target: str,
    prediction_policy: str = "FIRST_MATCH",
    aggregation: str = "UNION",
    run_evaluation: bool = True,
    show_rules: bool = True,
    show_rule_limit: int = 5,
    verbose_lem2: bool = False,
    order_sensitivity_max_permutations: int = 120,
    order_sensitivity_seed: int = 42,
    quiet: bool = False,
):
    if not quiet:
        print("\nFEDERATED | Local LEM2 -> Aggregation")

    local_rules: Dict[str, List[Rule]] = {}
    local_rule_weights: Dict[str, Dict[Any, float]] = {}
    local_rule_support_sets: Dict[str, Dict[Any, Set[Any]]] = {}
    local_class_sizes: Dict[str, Dict[Any, int]] = {}
    local_metrics: List[Dict[str, Any]] = []

    for client_name, client_df in clients.items():
        rules = induce_lem2(
            client_df,
            condition_cols=condition_columns,
            decision_col=target,
            source=client_name,
            verbose=verbose_lem2,
        )
        weights = fit_rule_weights(client_df, rules)
        support_sets, class_sizes = fit_rule_support_sets(
            client_df,
            rules,
            target=target,
            row_prefix=client_name,
        )

        local_rules[client_name] = rules
        local_rule_weights[client_name] = weights
        local_rule_support_sets[client_name] = support_sets
        local_class_sizes[client_name] = class_sizes

        row = {
            "client": client_name,
            "n": len(client_df),
            "rules": len(rules),
            "classes": client_df[target].value_counts().to_dict(),
        }

        if run_evaluation:
            local_default = majority_class(client_df, target)
            row.update(
                evaluate_rule_model(
                    test,
                    rules,
                    local_default,
                    target,
                    prediction_policy=prediction_policy,
                    rule_weights=weights,
                    rule_support_sets=support_sets,
                    class_sizes=class_sizes,
                )
            )

        local_metrics.append(row)

        if show_rules:
            msg = f"  {client_name}: n={len(client_df)}, rules={len(rules)}"
            if run_evaluation:
                msg += f", BA={row['balanced_accuracy']:.4f}, coverage={row['coverage']:.4f}"
            print(msg)

    aggregation = aggregation.strip().upper()
    if aggregation != "UNION":
        raise ValueError("Only federated_aggregation='UNION' is implemented.")

    global_rules, global_rule_sources = union_rules_with_provenance(local_rules)
    global_rule_weights = aggregate_rule_weights(local_rule_weights)
    global_rule_support_sets, global_class_sizes = aggregate_rule_support_context(
        local_rule_support_sets, local_class_sizes
    )
    global_default = majority_class_from_clients(clients, target)

    local_counts = [len(rs) for rs in local_rules.values()]
    jaccard = pairwise_rule_jaccard(local_rules)
    rule_conflicts = audit_rule_conflicts(global_rules, rule_sources=global_rule_sources)

    result: Dict[str, Any] = {
        "clients": dict(clients),
        "client_count": len(clients),
        "local_rules": local_rules,
        "local_rule_weights": local_rule_weights,
        "local_rule_support_sets": local_rule_support_sets,
        "local_class_sizes": local_class_sizes,
        "local_metrics": pd.DataFrame(local_metrics),
        "avg_local_rule_count": float(np.mean(local_counts)) if local_counts else 0.0,
        "total_local_rule_count": int(sum(local_counts)),
        "global_rules": global_rules,
        "global_rule_count": int(len(global_rules)),
        "global_rule_sources": global_rule_sources,
        "global_rule_source_counts": {
            key: len(sources) for key, sources in global_rule_sources.items()
        },
        "global_rule_weights": global_rule_weights,
        "global_rule_support_sets": global_rule_support_sets,
        "global_class_sizes": global_class_sizes,
        "default_class": global_default,
        "prediction_policy": str(prediction_policy).strip().upper(),
        "test_row_ids": test["__row_id__"].astype(int).tolist() if "__row_id__" in test else [],
        **jaccard,
        **rule_conflicts,
    }

    if show_rules:
        print("\n  Aggregation = UNION")
        print(f"  Total local rules = {result['total_local_rule_count']}")
        print(f"  Unique global rules = {len(global_rules)}")
        print(f"  Avg local rules = {result['avg_local_rule_count']:.2f}")
        print(f"  Pairwise Jaccard (antecedent) = {result['pairwise_jaccard_antecedent']:.4f}")
        print(f"  Pairwise Jaccard (full rule) = {result['pairwise_jaccard_full_rule']:.4f}")
        print(
            f"  Conflict groups = {result['conflict_group_count']} | "
            f"Antecedent rate = {result['conflict_antecedent_rate']:.4f} | "
            f"Rule share = {result['conflict_rule_share']:.4f}"
        )
        for i, rule in enumerate(global_rules[:show_rule_limit], 1):
            print(f"  G{i:02d}. {rule}")
        if len(global_rules) > show_rule_limit:
            print(f"  ... {len(global_rules)-show_rule_limit} more")

    if run_evaluation:
        metrics = evaluate_rule_model(
            test,
            global_rules,
            global_default,
            target,
            prediction_policy=prediction_policy,
            rule_weights=global_rule_weights,
            rule_support_sets=global_rule_support_sets,
            class_sizes=global_class_sizes,
        )
        result.update(metrics)

        case_conflicts = audit_conflict_cases(
            test=test,
            rules=global_rules,
            predictions=metrics["predictions"],
            target=target,
        )
        result.update(case_conflicts)

        order_audit = audit_order_distribution(
            test=test,
            local_rules=local_rules,
            default_class=global_default,
            target=target,
            prediction_policy=prediction_policy,
            rule_weights=global_rule_weights,
            rule_support_sets=global_rule_support_sets,
            class_sizes=global_class_sizes,
            max_permutations=order_sensitivity_max_permutations,
            seed=order_sensitivity_seed,
        )
        result.update(order_audit)

        if not quiet:
            cra = result["conflict_resolution_accuracy"]
            cra_text = "NA" if pd.isna(cra) else f"{cra:.4f}"
            print(
                f"  Prediction = {metrics['prediction_policy']} | "
                f"Federated Accuracy = {metrics['accuracy']:.4f} | "
                f"Balanced Accuracy = {metrics['balanced_accuracy']:.4f} | "
                f"Macro F1 = {metrics['macro_f1']:.4f} | "
                f"Coverage = {metrics['coverage']:.4f}"
            )
            print(
                f"  Conflict Case Rate = {result['conflict_case_rate']:.4f} | "
                f"Conflict Resolution Accuracy = {cra_text} | "
                f"Order Sensitivity = {result['order_sensitivity_rate']:.4f} "
                f"({result['orderings_checked']} client orders checked)"
            )
            print(
                f"  Order-averaged BA = {result['order_balanced_accuracy_mean']:.4f} "
                f"± {result['order_balanced_accuracy_std']:.4f} | "
                f"range=[{result['order_balanced_accuracy_min']:.4f}, "
                f"{result['order_balanced_accuracy_max']:.4f}]"
            )

    return result
