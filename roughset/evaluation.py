from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

from .core import Rule, induce_lem2


def majority_class(df: pd.DataFrame, target_col: str):
    return str(df[target_col].value_counts().idxmax())


def majority_class_from_clients(clients: Mapping[str, pd.DataFrame], target_col: str):
    counts: Counter = Counter()
    for df in clients.values():
        counts.update(df[target_col].astype(str).value_counts().to_dict())
    if not counts:
        raise ValueError("No client labels available for default class.")
    return counts.most_common(1)[0][0]


def _rule_matches(row: pd.Series, rule: Rule) -> bool:
    return all(str(row[attr]) == str(value) for attr, value in rule.conditions)


def matching_rules(row: pd.Series, rules: Sequence[Rule]) -> List[Rule]:
    return [rule for rule in rules if _rule_matches(row, rule)]


def _resolve_vote(votes: Mapping[Any, float], default_class: Any):
    if not votes:
        return default_class
    best = max(votes.values())
    winners = [decision for decision, score in votes.items() if np.isclose(score, best)]
    if default_class in winners:
        return default_class
    return sorted(winners, key=str)[0]


def population_support_summary(
    matched_rules: Sequence[Rule],
    rule_support_sets: Mapping[Any, Set[Any]],
    class_sizes: Optional[Mapping[Any, int]] = None,
) -> Dict[Any, Dict[str, float]]:
    """Summarize support duplication for each decision among matching rules.

    This is a project-defined experimental quantity from the 2026-10-22
    meeting, not a literature-derived rough-set metric.

    For decision d:

        T_d = sum_r |S(r)|                         total support occurrences
        U_d = |union_r S(r)|                       unique supporting population
        P_d = U_d / T_d                            nonredundancy ratio

    ``POPULATION_STANDARD`` uses ``U_d = T_d * P_d`` as its score.
    ``POPULATION_GLOBAL`` applies the same factor to GlobalStrength:

        (U_d / N_d) * P_d = U_d^2 / (N_d * T_d)

    where N_d is the training class size.
    """
    grouped: Dict[Any, List[Rule]] = defaultdict(list)
    for rule in matched_rules:
        grouped[rule.decision].append(rule)

    result: Dict[Any, Dict[str, float]] = {}
    for decision, decision_rules in grouped.items():
        support_sets = [set(rule_support_sets.get(rule.key, set())) for rule in decision_rules]
        total_occurrences = float(sum(len(values) for values in support_sets))
        unique_objects: Set[Any] = set()
        for values in support_sets:
            unique_objects |= values
        unique_population = float(len(unique_objects))
        redundancy = total_occurrences - unique_population
        nonredundancy_ratio = (
            unique_population / total_occurrences if total_occurrences > 0 else 0.0
        )
        class_size = 0
        if class_sizes is not None:
            class_size = int(class_sizes.get(decision, class_sizes.get(str(decision), 0)))
        global_strength = unique_population / class_size if class_size > 0 else 0.0
        result[decision] = {
            "total_support_occurrences": total_occurrences,
            "unique_population": unique_population,
            "redundant_occurrences": redundancy,
            "population_nonredundancy_ratio": nonredundancy_ratio,
            "class_size": float(class_size),
            "global_strength": global_strength,
        }
    return result


def predict_with_policy(
    row: pd.Series,
    rules: Sequence[Rule],
    default_class: Any,
    policy: str = "FIRST_MATCH",
    rule_weights: Optional[Mapping[Any, float]] = None,
    rule_support_sets: Optional[Mapping[Any, Set[Any]]] = None,
    class_sizes: Optional[Mapping[Any, int]] = None,
):
    policy = str(policy).strip().upper()

    if policy == "FIRST_MATCH":
        for rule in rules:
            if _rule_matches(row, rule):
                return rule.decision, [rule]
        return default_class, []

    matched = matching_rules(row, rules)
    if not matched:
        return default_class, []

    votes: Dict[Any, float] = defaultdict(float)

    if policy == "SIMPLE_VOTING":
        for rule in matched:
            votes[rule.decision] += 1.0

    elif policy == "STANDARD_VOTING":
        if rule_weights is None:
            raise ValueError("STANDARD_VOTING requires rule_weights.")
        for rule in matched:
            votes[rule.decision] += float(rule_weights.get(rule.key, 0.0))

    elif policy == "GLOBAL_STRENGTH":
        if rule_support_sets is None or class_sizes is None:
            raise ValueError(
                "GLOBAL_STRENGTH requires rule_support_sets and class_sizes."
            )

        matched_by_decision: Dict[Any, List[Rule]] = defaultdict(list)
        for rule in matched:
            matched_by_decision[rule.decision].append(rule)

        for decision, decision_rules in matched_by_decision.items():
            supported_objects: Set[Any] = set()
            for rule in decision_rules:
                supported_objects |= set(rule_support_sets.get(rule.key, set()))

            denominator = int(class_sizes.get(decision, class_sizes.get(str(decision), 0)))
            votes[decision] = (
                len(supported_objects) / denominator
                if denominator > 0
                else 0.0
            )

    elif policy in {"POPULATION_STANDARD", "POPULATION_GLOBAL"}:
        if rule_support_sets is None:
            raise ValueError(f"{policy} requires rule_support_sets.")
        if policy == "POPULATION_GLOBAL" and class_sizes is None:
            raise ValueError("POPULATION_GLOBAL requires class_sizes.")

        summaries = population_support_summary(
            matched,
            rule_support_sets,
            class_sizes=class_sizes,
        )
        for decision, summary in summaries.items():
            if policy == "POPULATION_STANDARD":
                # Standard support sum T_d corrected by P_d = U_d/T_d.
                # Algebraically this is the unique supporting population U_d.
                votes[decision] = summary["unique_population"]
            else:
                # GlobalStrength U_d/N_d with the same nonredundancy penalty P_d.
                votes[decision] = (
                    summary["global_strength"]
                    * summary["population_nonredundancy_ratio"]
                )

    else:
        raise ValueError(
            "policy must be FIRST_MATCH, SIMPLE_VOTING, STANDARD_VOTING, "
            "GLOBAL_STRENGTH, POPULATION_STANDARD, or POPULATION_GLOBAL."
        )

    return _resolve_vote(votes, default_class), matched


def fit_rule_weights(train: pd.DataFrame, rules: Sequence[Rule]) -> Dict[Any, float]:
    """
    Standard-voting weight = number of training objects matching the antecedent.
    """
    weights: Dict[Any, float] = {}

    for rule in rules:
        count = 0
        for _, row in train.iterrows():
            if _rule_matches(row, rule):
                count += 1
        weights[rule.key] = float(count)

    return weights


def fit_rule_support_sets(
    train: pd.DataFrame,
    rules: Sequence[Rule],
    target: str,
    row_prefix: Optional[str] = None,
) -> Tuple[Dict[Any, Set[Any]], Dict[Any, int]]:
    """
    Build the support context required by GLOBAL_STRENGTH.

    For each rule, store training objects that satisfy both its antecedent
    and its decision.  A prefix can be used so federated client row IDs stay
    globally unique without sharing raw rows.
    """
    support_sets: Dict[Any, Set[Any]] = {}
    class_sizes = train[target].astype(str).value_counts().to_dict()

    for rule in rules:
        supported: Set[Any] = set()
        for idx, row in train.iterrows():
            if _rule_matches(row, rule) and str(row[target]) == str(rule.decision):
                object_id = (row_prefix, int(idx)) if row_prefix is not None else int(idx)
                supported.add(object_id)
        support_sets[rule.key] = supported

    return support_sets, {str(k): int(v) for k, v in class_sizes.items()}


def aggregate_rule_support_context(
    local_support_sets: Mapping[str, Mapping[Any, Set[Any]]],
    local_class_sizes: Mapping[str, Mapping[Any, int]],
) -> Tuple[Dict[Any, Set[Any]], Dict[Any, int]]:
    merged_sets: Dict[Any, Set[Any]] = defaultdict(set)
    merged_class_sizes: Counter = Counter()

    for support_sets in local_support_sets.values():
        for key, values in support_sets.items():
            merged_sets[key] |= set(values)

    for class_sizes in local_class_sizes.values():
        merged_class_sizes.update({str(k): int(v) for k, v in class_sizes.items()})

    return dict(merged_sets), dict(merged_class_sizes)


def aggregate_rule_weights(
    local_rule_weights: Mapping[str, Mapping[Any, float]],
) -> Dict[Any, float]:
    """Sum local antecedent-support weights for identical global rules."""
    merged: Dict[Any, float] = defaultdict(float)
    for weights in local_rule_weights.values():
        for key, value in weights.items():
            merged[key] += float(value)
    return dict(merged)


def predict_table(
    df: pd.DataFrame,
    rules: Sequence[Rule],
    default_class: Any,
    prediction_policy: str = "FIRST_MATCH",
    rule_weights: Optional[Mapping[Any, float]] = None,
    rule_support_sets: Optional[Mapping[Any, Set[Any]]] = None,
    class_sizes: Optional[Mapping[Any, int]] = None,
):
    preds = []
    matched_rule_lists = []

    for _, row in df.iterrows():
        pred, matched = predict_with_policy(
            row,
            rules,
            default_class=default_class,
            policy=prediction_policy,
            rule_weights=rule_weights,
            rule_support_sets=rule_support_sets,
            class_sizes=class_sizes,
        )
        preds.append(pred)
        matched_rule_lists.append(matched)

    return preds, matched_rule_lists


def balanced_accuracy(y_true, y_pred) -> float:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    recalls = []

    for cls in pd.unique(y_true):
        mask = y_true == cls
        if mask.sum():
            recalls.append(float((y_pred[mask] == cls).mean()))

    return float(np.mean(recalls)) if recalls else 0.0


def classification_accuracy(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=object)
    y_pred = np.asarray(y_pred, dtype=object)
    if len(y_true) == 0:
        return 0.0
    return float(np.mean(y_true == y_pred))


def macro_recall_score(y_true, y_pred) -> float:
    """Macro recall; numerically equal to multiclass Balanced Accuracy here."""
    return balanced_accuracy(y_true, y_pred)


def macro_f1_score(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=object)
    y_pred = np.asarray(y_pred, dtype=object)
    classes = sorted(set(y_true.tolist()) | set(y_pred.tolist()), key=str)
    if not classes:
        return 0.0

    scores = []
    for cls in classes:
        tp = int(np.sum((y_true == cls) & (y_pred == cls)))
        fp = int(np.sum((y_true != cls) & (y_pred == cls)))
        fn = int(np.sum((y_true == cls) & (y_pred != cls)))
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        scores.append(f1)
    return float(np.mean(scores))


def target_coverage_by_class(
    y_true: Sequence[Any],
    matched_rule_lists: Sequence[Sequence[Rule]],
) -> Dict[str, float]:
    """Coverage inside each true target class on the evaluation set."""
    true = np.asarray([str(value) for value in y_true], dtype=object)
    covered = np.asarray([len(rules) > 0 for rules in matched_rule_lists], dtype=bool)
    result: Dict[str, float] = {}
    for label in sorted(set(true.tolist()), key=str):
        mask = true == label
        result[str(label)] = float(np.mean(covered[mask])) if mask.any() else float("nan")
    return result


def rule_antecedent_signature(rule: "Rule") -> Tuple[Tuple[str, str], ...]:
    """Canonical antecedent only; used for paper-style Jaccard and conflict grouping."""
    return tuple(sorted((str(a), str(v)) for a, v in rule.conditions))


def rule_full_signature(rule: "Rule") -> Tuple[Tuple[Tuple[str, str], ...], str]:
    """Antecedent + decision; used when full rule identity matters."""
    return (rule_antecedent_signature(rule), str(rule.decision))


def _jaccard(set_a: Set[Any], set_b: Set[Any]) -> float:
    union = set_a | set_b
    if not union:
        return float("nan")
    return float(len(set_a & set_b) / len(union))


def pairwise_rule_jaccard(
    local_rules: Mapping[str, Sequence["Rule"]],
) -> Dict[str, Any]:
    """Compute pairwise client similarity in two ways.

    antecedent: conditions only, matching the healthcare paper's stated set view.
    full_rule:  conditions + decision, stricter and useful for conflict research.
    """
    names = list(local_rules)
    rows: List[Dict[str, Any]] = []

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            ant_a = {rule_antecedent_signature(r) for r in local_rules[a]}
            ant_b = {rule_antecedent_signature(r) for r in local_rules[b]}
            full_a = {rule_full_signature(r) for r in local_rules[a]}
            full_b = {rule_full_signature(r) for r in local_rules[b]}
            rows.append({
                "client_i": a,
                "client_j": b,
                "jaccard_antecedent": _jaccard(ant_a, ant_b),
                "jaccard_full_rule": _jaccard(full_a, full_b),
            })

    table = pd.DataFrame(rows)
    if table.empty:
        return {
            "pairwise_table": table,
            "pairwise_jaccard_antecedent": float("nan"),
            "pairwise_jaccard_full_rule": float("nan"),
        }

    return {
        "pairwise_table": table,
        "pairwise_jaccard_antecedent": float(table["jaccard_antecedent"].mean(skipna=True)),
        "pairwise_jaccard_full_rule": float(table["jaccard_full_rule"].mean(skipna=True)),
    }


def audit_rule_conflicts(
    rules: Sequence["Rule"],
    rule_sources: Optional[Mapping[Any, Sequence[str]]] = None,
) -> Dict[str, Any]:
    """Audit exact-antecedent conflicts in a global ruleset.

    A conflict group exists when the same antecedent maps to >1 decision.
    This is stricter than case-level conflict; overlapping non-identical rules are
    captured later by conflict_case_rate.  When provenance is supplied, the audit
    reports all clients that produced each conflicting full rule rather than only
    the first client retained by UNION ordering.
    """
    groups: Dict[Any, List["Rule"]] = defaultdict(list)
    for rule in rules:
        groups[rule_antecedent_signature(rule)].append(rule)

    conflicting = {
        ant: rs
        for ant, rs in groups.items()
        if len({str(r.decision) for r in rs}) > 1
    }
    conflict_rule_count = sum(len(rs) for rs in conflicting.values())
    unique_antecedents = len(groups)
    total_rules = len(rules)

    rows = []
    for ant, rs in conflicting.items():
        sources: Set[str] = set()
        for r in rs:
            if rule_sources is not None:
                sources.update(str(x) for x in rule_sources.get(r.key, ()))
            elif r.source:
                sources.add(str(r.source))
        rows.append({
            "antecedent": " AND ".join(f"{a}={v}" for a, v in ant),
            "decisions": sorted({str(r.decision) for r in rs}),
            "rule_count": len(rs),
            "sources": sorted(sources),
        })

    return {
        "conflict_groups_table": pd.DataFrame(rows),
        "unique_antecedent_count": unique_antecedents,
        "conflict_group_count": len(conflicting),
        "conflict_antecedent_rate": (len(conflicting) / unique_antecedents) if unique_antecedents else 0.0,
        "conflict_rule_count": conflict_rule_count,
        "conflict_rule_share": (conflict_rule_count / total_rules) if total_rules else 0.0,
    }


def audit_conflict_cases(
    test: pd.DataFrame,
    rules: Sequence["Rule"],
    predictions: Sequence[Any],
    target: str,
) -> Dict[str, Any]:
    """Measure conflicts that actually occur during inference.

    A test case is conflicting if all matching rules contain >1 distinct decision.
    Conflict resolution accuracy is accuracy restricted to those cases only.
    """
    conflict_flags: List[bool] = []
    rows: List[Dict[str, Any]] = []

    for pos, (_, row) in enumerate(test.iterrows()):
        matched = matching_rules(row, rules)
        decisions = sorted({str(r.decision) for r in matched})
        is_conflict = len(decisions) > 1
        conflict_flags.append(is_conflict)
        if is_conflict:
            rows.append({
                "row_id": int(row["__row_id__"]) if "__row_id__" in row.index else pos,
                "true": str(row[target]),
                "predicted": str(predictions[pos]),
                "matching_rules": len(matched),
                "decisions": decisions,
                "correct": str(predictions[pos]) == str(row[target]),
            })

    n = len(test)
    count = int(sum(conflict_flags))
    resolution_accuracy = (
        float(np.mean([r["correct"] for r in rows])) if rows else float("nan")
    )
    return {
        "conflict_cases_table": pd.DataFrame(rows),
        "conflict_case_flags": conflict_flags,
        "conflict_case_count": count,
        "conflict_case_rate": (count / n) if n else 0.0,
        "conflict_resolution_accuracy": resolution_accuracy,
    }


def evaluate_rule_model(
    test: pd.DataFrame,
    rules: Sequence[Rule],
    default_class: Any,
    target: str,
    prediction_policy: str = "FIRST_MATCH",
    rule_weights: Optional[Mapping[Any, float]] = None,
    rule_support_sets: Optional[Mapping[Any, Set[Any]]] = None,
    class_sizes: Optional[Mapping[Any, int]] = None,
):
    preds, matched = predict_table(
        test,
        rules,
        default_class,
        prediction_policy=prediction_policy,
        rule_weights=rule_weights,
        rule_support_sets=rule_support_sets,
        class_sizes=class_sizes,
    )

    overall_coverage = float(np.mean([len(x) > 0 for x in matched])) if len(test) else 0.0
    target_coverage = target_coverage_by_class(test[target], matched)
    target_coverage_values = [value for value in target_coverage.values() if np.isfinite(value)]
    target_coverage_macro = (
        float(np.mean(target_coverage_values)) if target_coverage_values else float("nan")
    )

    return {
        "accuracy": classification_accuracy(test[target], preds),
        "balanced_accuracy": balanced_accuracy(test[target], preds),
        "recall_macro": macro_recall_score(test[target], preds),
        "macro_f1": macro_f1_score(test[target], preds),
        "coverage": overall_coverage,
        "overall_coverage": overall_coverage,
        "target_coverage_by_class": target_coverage,
        "target_coverage_macro": target_coverage_macro,
        "predictions": preds,
        "matched_rules": matched,
        "prediction_policy": str(prediction_policy).strip().upper(),
    }


def run_centralized(
    train: pd.DataFrame,
    test: pd.DataFrame,
    condition_columns: Sequence[str],
    target: str,
    prediction_policy: str = "FIRST_MATCH",
    run_evaluation: bool = True,
    show_rules: bool = True,
    show_rule_limit: int = 5,
    verbose_lem2: bool = False,
    quiet: bool = False,
):
    if not quiet:
        print("\nCENTRALIZED | LEM2")

    rules = induce_lem2(
        train,
        condition_cols=condition_columns,
        decision_col=target,
        source="Centralized",
        verbose=verbose_lem2,
    )

    default_class = majority_class(train, target)
    rule_weights = fit_rule_weights(train, rules)
    rule_support_sets, class_sizes = fit_rule_support_sets(
        train, rules, target=target
    )

    result: Dict[str, Any] = {
        "rules": rules,
        "rule_weights": rule_weights,
        "rule_support_sets": rule_support_sets,
        "class_sizes": class_sizes,
        "default_class": default_class,
        "prediction_policy": str(prediction_policy).strip().upper(),
        "test_row_ids": test["__row_id__"].astype(int).tolist() if "__row_id__" in test else [],
    }

    if show_rules:
        print(f"  Rules = {len(rules)}")
        for i, rule in enumerate(rules[:show_rule_limit], 1):
            print(f"  C{i:02d}. {rule}")
        if len(rules) > show_rule_limit:
            print(f"  ... {len(rules)-show_rule_limit} more")

    if run_evaluation:
        metrics = evaluate_rule_model(
            test,
            rules,
            default_class,
            target,
            prediction_policy=prediction_policy,
            rule_weights=rule_weights,
            rule_support_sets=rule_support_sets,
            class_sizes=class_sizes,
        )
        result.update(metrics)
        if not quiet:
            print(
                f"  Prediction = {metrics['prediction_policy']} | "
                f"Accuracy = {metrics['accuracy']:.4f} | "
                f"Balanced Accuracy = {metrics['balanced_accuracy']:.4f} | "
                f"Macro F1 = {metrics['macro_f1']:.4f} | "
                f"Coverage = {metrics['coverage']:.4f}"
            )

    return result
