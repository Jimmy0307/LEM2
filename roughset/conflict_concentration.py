from __future__ import annotations

import json
import math
from collections import defaultdict
from statistics import fmean
from typing import Any, Iterable, Mapping, Sequence


DEFAULT_POLICY_COLUMNS: dict[str, str] = {
    "FIRST_MATCH": "pred_first_match",
    "SIMPLE_VOTING": "pred_simple_voting",
    "STANDARD_VOTING": "pred_standard_voting",
    "GLOBAL_STRENGTH": "pred_global_strength",
    "POPULATION_STANDARD": "pred_population_standard",
    "POPULATION_GLOBAL": "pred_population_global",
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_int(value: Any, *, field: str) -> int:
    try:
        return int(float(_text(value)))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid integer for {field}: {value!r}") from exc


def _as_float(value: Any, *, field: str) -> float:
    try:
        return float(_text(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid float for {field}: {value!r}") from exc


def _truthy(value: Any) -> bool:
    return _text(value).lower() in {"1", "true", "yes", "y"}


def _sort_key(values: Sequence[Any]) -> tuple[str, ...]:
    return tuple(_text(value) for value in values)


def _candidate_values(raw: Any) -> tuple[str, ...]:
    if isinstance(raw, (list, tuple, set)):
        values = list(raw)
    elif raw is None or _text(raw) == "":
        values = []
    else:
        text = _text(raw)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = [part.strip() for part in text.replace("|", ",").split(",") if part.strip()]
        values = parsed if isinstance(parsed, list) else [parsed]
    return tuple(sorted({_text(value) for value in values if _text(value)}, key=str))


def candidate_signature(raw: Any) -> str:
    """Return deterministic distinct candidate labels joined by ``|``."""
    return "|".join(_candidate_values(raw))


def _unique_conflict_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str, str]] = set()
    for raw in rows:
        row = dict(raw)
        dataset = _text(row.get("dataset"))
        if not dataset:
            raise ValueError("Conflict row is missing dataset")
        client_count = _as_int(row.get("client_count"), field="client_count")
        fold = _text(row.get("fold")) or "1"
        row_id = _text(row.get("row_id"))
        if not row_id:
            raise ValueError("Conflict row is missing row_id")
        key = (dataset, client_count, fold, row_id)
        if key in seen:
            raise ValueError(f"Duplicate conflict occurrence: {key}")
        seen.add(key)
        row["dataset"] = dataset
        row["client_count"] = client_count
        row["fold"] = fold
        row["row_id"] = row_id
        row["true"] = _text(row.get("true"))
        row["matching_rules"] = _as_int(row.get("matching_rules", 0), field="matching_rules")
        row["_candidates"] = _candidate_values(row.get("candidate_decisions"))
        result.append(row)
    return result


def summarize_configurations(
    conflict_rows: Iterable[Mapping[str, Any]],
    metadata_rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = _unique_conflict_rows(conflict_rows)
    metadata: dict[tuple[str, int, str], int] = {}
    for raw in metadata_rows:
        dataset = _text(raw.get("dataset"))
        client_count = _as_int(raw.get("client_count"), field="metadata.client_count")
        fold = _text(raw.get("fold")) or "1"
        key = (dataset, client_count, fold)
        test_rows = _as_int(raw.get("test_rows"), field="metadata.test_rows")
        if key in metadata and metadata[key] != test_rows:
            raise ValueError(f"Conflicting metadata for {key}")
        metadata[key] = test_rows

    groups: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["dataset"], row["client_count"], row["fold"])].append(row)

    total_conflicts = len(rows)
    result: list[dict[str, Any]] = []
    for key in sorted(groups, key=_sort_key):
        grouped = groups[key]
        if key not in metadata:
            raise ValueError(f"Missing test_rows metadata for {key}")
        test_rows = metadata[key]
        conflict_count = len(grouped)
        missing_true = sum(int(row["true"] not in row["_candidates"]) for row in grouped)
        ps_changed = sum(int(_text(row.get("ps_status")) not in {"", "UNCHANGED"}) for row in grouped)
        pg_changed = sum(int(_text(row.get("pg_status")) not in {"", "UNCHANGED"}) for row in grouped)
        result.append(
            {
                "dataset": key[0],
                "client_count": key[1],
                "fold": key[2],
                "test_rows": test_rows,
                "conflict_count": conflict_count,
                "conflict_rate": conflict_count / test_rows if test_rows else math.nan,
                "share_of_all_conflicts": conflict_count / total_conflicts if total_conflicts else math.nan,
                "avg_matching_rules": fmean(row["matching_rules"] for row in grouped),
                "avg_candidate_decisions": fmean(len(row["_candidates"]) for row in grouped),
                "true_candidate_missing_count": missing_true,
                "true_candidate_missing_rate": missing_true / conflict_count if conflict_count else math.nan,
                "ps_changed_count": ps_changed,
                "pg_changed_count": pg_changed,
            }
        )
    return result


def summarize_true_classes(conflict_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = _unique_conflict_rows(conflict_rows)
    config_totals: dict[tuple[str, int, str], int] = defaultdict(int)
    groups: dict[tuple[str, int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        config_key = (row["dataset"], row["client_count"], row["fold"])
        config_totals[config_key] += 1
        groups[config_key + (row["true"],)].append(row)

    result: list[dict[str, Any]] = []
    for key in sorted(groups, key=_sort_key):
        grouped = groups[key]
        total = config_totals[key[:3]]
        missing = sum(int(row["true"] not in row["_candidates"]) for row in grouped)
        result.append(
            {
                "dataset": key[0],
                "client_count": key[1],
                "fold": key[2],
                "true_class": key[3],
                "conflict_count": len(grouped),
                "share_within_configuration": len(grouped) / total if total else math.nan,
                "avg_matching_rules": fmean(row["matching_rules"] for row in grouped),
                "true_candidate_missing_count": missing,
                "true_candidate_missing_rate_within_conflicts": missing / len(grouped),
            }
        )
    return result


def summarize_candidate_signatures(conflict_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = _unique_conflict_rows(conflict_rows)
    config_totals: dict[tuple[str, int, str], int] = defaultdict(int)
    groups: dict[tuple[str, int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        config_key = (row["dataset"], row["client_count"], row["fold"])
        config_totals[config_key] += 1
        signature = "|".join(row["_candidates"])
        groups[config_key + (signature,)].append(row)

    result: list[dict[str, Any]] = []
    for key in sorted(groups, key=_sort_key):
        grouped = groups[key]
        total = config_totals[key[:3]]
        result.append(
            {
                "dataset": key[0],
                "client_count": key[1],
                "fold": key[2],
                "candidate_signature": key[3],
                "candidate_decision_count": len(key[3].split("|")) if key[3] else 0,
                "conflict_count": len(grouped),
                "share_within_configuration": len(grouped) / total if total else math.nan,
                "avg_matching_rules": fmean(row["matching_rules"] for row in grouped),
            }
        )
    return result


def summarize_persistence(
    conflict_rows: Iterable[Mapping[str, Any]],
    *,
    expected_client_counts: Sequence[int] = (2, 3, 4, 5),
) -> list[dict[str, Any]]:
    rows = _unique_conflict_rows(conflict_rows)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["dataset"], row["fold"], row["row_id"])].append(row)

    result: list[dict[str, Any]] = []
    expected_n = len(set(int(value) for value in expected_client_counts))
    for key in sorted(groups, key=_sort_key):
        grouped = groups[key]
        true_values = {row["true"] for row in grouped}
        if len(true_values) != 1:
            raise ValueError(f"True decision changed across client counts for {key}: {sorted(true_values)}")
        factor_snapshots = {
            tuple(sorted((name, _text(value)) for name, value in row.items() if name.startswith("factor__") and _text(value)))
            for row in grouped
        }
        if len(factor_snapshots) > 1:
            raise ValueError(f"Factor values changed across client counts for {key}")
        client_counts = sorted({int(row["client_count"]) for row in grouped})
        count = len(client_counts)
        if count == 1:
            label = "SINGLE"
        elif expected_n and count == expected_n:
            label = "PERSISTENT"
        else:
            label = "REPEATED"
        factors = dict(next(iter(factor_snapshots), ()))
        result.append(
            {
                "dataset": key[0],
                "fold": key[1],
                "row_id": key[2],
                "true_class": next(iter(true_values)),
                "conflict_client_count": count,
                "conflict_client_counts": "|".join(str(value) for value in client_counts),
                "persistence_rate": count / expected_n if expected_n else math.nan,
                "persistence_label": label,
                "avg_matching_rules": fmean(row["matching_rules"] for row in grouped),
                "max_matching_rules": max(row["matching_rules"] for row in grouped),
                "candidate_signatures": ";".join(sorted({"|".join(row["_candidates"]) for row in grouped})),
                "factors": json.dumps({name.removeprefix("factor__"): value for name, value in factors.items()}, ensure_ascii=False, sort_keys=True),
            }
        )
    return result


def summarize_factor_values(conflict_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = _unique_conflict_rows(conflict_rows)
    dataset_totals: dict[str, int] = defaultdict(int)
    groups: dict[tuple[str, str, str], int] = defaultdict(int)
    for row in rows:
        dataset_totals[row["dataset"]] += 1
        for name, value in row.items():
            if not name.startswith("factor__"):
                continue
            text = _text(value)
            if not text:
                continue
            groups[(row["dataset"], name.removeprefix("factor__"), text)] += 1

    result: list[dict[str, Any]] = []
    for key in sorted(groups, key=_sort_key):
        count = groups[key]
        total = dataset_totals[key[0]]
        result.append(
            {
                "dataset": key[0],
                "factor": key[1],
                "value": key[2],
                "conflict_count": count,
                "share_within_dataset_conflicts": count / total if total else math.nan,
            }
        )
    return result


def summarize_policy_accuracy(
    conflict_rows: Iterable[Mapping[str, Any]],
    *,
    policy_columns: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    rows = _unique_conflict_rows(conflict_rows)
    columns = dict(policy_columns or DEFAULT_POLICY_COLUMNS)
    if rows:
        missing = [column for column in columns.values() if column not in rows[0]]
        if missing:
            raise KeyError(f"Missing policy prediction columns: {missing}")

    groups: dict[tuple[str, int, str, str], tuple[int, int]] = {}
    counters: dict[tuple[str, int, str, str], list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        for policy, column in columns.items():
            key = (row["dataset"], row["client_count"], row["fold"], policy)
            counters[key][1] += 1
            counters[key][0] += int(_text(row.get(column)) == row["true"])
    groups = {key: (value[0], value[1]) for key, value in counters.items()}

    return [
        {
            "dataset": key[0],
            "client_count": key[1],
            "fold": key[2],
            "policy": key[3],
            "correct": correct,
            "conflict_count": total,
            "conflict_accuracy": correct / total if total else math.nan,
        }
        for key, (correct, total) in sorted(groups.items(), key=lambda item: _sort_key(item[0]))
    ]


def summarize_transition_status(conflict_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = _unique_conflict_rows(conflict_rows)
    groups: dict[tuple[str, int, str, str, str], int] = defaultdict(int)
    for row in rows:
        for transition, column in (("STD_TO_PS", "ps_status"), ("GS_TO_PG", "pg_status")):
            status = _text(row.get(column)) or "UNKNOWN"
            groups[(row["dataset"], row["client_count"], row["fold"], transition, status)] += 1
    return [
        {
            "dataset": key[0],
            "client_count": key[1],
            "fold": key[2],
            "transition": key[3],
            "status": key[4],
            "count": count,
        }
        for key, count in sorted(groups.items(), key=lambda item: _sort_key(item[0]))
    ]


def summarize_decision_scores(decision_score_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, int, str, str], list[dict[str, float]]] = defaultdict(list)
    for raw in decision_score_rows:
        dataset = _text(raw.get("dataset"))
        client_count = _as_int(raw.get("client_count"), field="decision_score.client_count")
        fold = _text(raw.get("fold")) or "1"
        role = "TRUE" if _truthy(raw.get("is_true_decision")) else "COMPETITOR"
        groups[(dataset, client_count, fold, role)].append(
            {
                "total_support_occurrences": _as_float(raw.get("total_support_occurrences", 0), field="total_support_occurrences"),
                "unique_population": _as_float(raw.get("unique_population", 0), field="unique_population"),
                "redundancy_ratio": _as_float(raw.get("redundancy_ratio", 0), field="redundancy_ratio"),
            }
        )

    result: list[dict[str, Any]] = []
    for key in sorted(groups, key=_sort_key):
        grouped = groups[key]
        result.append(
            {
                "dataset": key[0],
                "client_count": key[1],
                "fold": key[2],
                "decision_role": key[3],
                "decision_rows": len(grouped),
                "mean_total_support_occurrences": fmean(row["total_support_occurrences"] for row in grouped),
                "mean_unique_population": fmean(row["unique_population"] for row in grouped),
                "mean_redundancy_ratio": fmean(row["redundancy_ratio"] for row in grouped),
            }
        )
    return result
