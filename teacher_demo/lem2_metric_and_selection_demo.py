from __future__ import annotations

from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
METRIC_CSV = BASE / "CENTRALIZED_VS_FEDERATED.csv"
CONFLICT_CSV = BASE / "CENTRALIZED_CONFLICT_STRUCTURE.csv"

POLICY_ORDER = ["FIRST", "SIMPLE", "STD", "GS", "PS", "PG"]
METRIC_COLS = [
    "central_accuracy",
    "central_balanced_accuracy",
    "central_macro_f1",
]


def compute_three_dataset_means(df: pd.DataFrame) -> pd.DataFrame:
    """Average centralized Acc / BA / Macro-F1 across the 3 datasets per policy."""
    out = (
        df.groupby(["policy", "prediction_policy"], as_index=False)[METRIC_COLS]
        .mean()
    )
    out[METRIC_COLS] = out[METRIC_COLS] * 100.0
    out["policy"] = pd.Categorical(out["policy"], categories=POLICY_ORDER, ordered=True)
    return out.sort_values("policy").reset_index(drop=True)


def overall_descriptive_mean(df: pd.DataFrame) -> pd.Series:
    """Descriptive mean across all 18 rows (6 policies x 3 datasets)."""
    return df[METRIC_COLS].mean() * 100.0


def selection_layer_demo() -> None:
    """
    Demonstrate where the study-defined conflict comes from.

    LEM2 itself outputs rules. The study then adds a matching/selection layer.
    A conflict is declared only when the same object matches rules pointing to
    more than one decision class. The six policies resolve that ambiguity;
    they do not belong to classical Rough Set / LEM2 itself.
    """
    rules = [
        {"name": "R1", "conditions": {"x1": "low"}, "decision": "A", "support": 7},
        {"name": "R2", "conditions": {"x2": "high"}, "decision": "B", "support": 5},
        {"name": "R3", "conditions": {"x1": "low", "x2": "high"}, "decision": "A", "support": 2},
    ]
    obj = {"x1": "low", "x2": "high"}

    def matches(rule: dict, row: dict) -> bool:
        return all(row.get(k) == v for k, v in rule["conditions"].items())

    matched = [rule for rule in rules if matches(rule, obj)]
    candidates = sorted({rule["decision"] for rule in matched})

    print("\n=== STUDY-ADDED SELECTION-LAYER DEMO ===")
    print("Classical LEM2 output: a rule set. No winner is required at this point.")
    print("Object passed into our extra matching/selection layer:", obj)
    for rule in matched:
        cond = " AND ".join(f"{k}={v}" for k, v in rule["conditions"].items())
        print(f"  {rule['name']}: IF {cond} THEN {rule['decision']} (support={rule['support']})")
    print("Candidate decisions:", candidates)
    print("Study-defined conflict:", "YES" if len(candidates) > 1 else "NO")
    print("The six policies are applied AFTER this point to choose one winner.")


def main() -> None:
    metrics = pd.read_csv(METRIC_CSV)
    conflict = pd.read_csv(CONFLICT_CSV)

    means = compute_three_dataset_means(metrics)
    print("=== ACC / BA / MACRO-F1: MEAN ACROSS 3 DATASETS ===")
    print(
        means[
            ["policy", "prediction_policy"] + METRIC_COLS
        ].round(2).to_string(index=False)
    )

    overall = overall_descriptive_mean(metrics)
    print("\n=== OVERALL DESCRIPTIVE MEAN ACROSS ALL 18 CENTRALIZED ROWS ===")
    print(overall.round(2).to_string())

    print("\n=== EMPIRICAL CENTRALIZED SELECTION-LAYER CONFLICT COUNTS ===")
    print("These counts appear only because the study applies the induced rules back to objects")
    print("and explicitly asks the rule set to produce one final decision.")
    for _, row in conflict.iterrows():
        print(
            f"{row['dataset']}: {int(row['conflicts'])}/{int(row['test'])} "
            f"= {row['conflict_rate'] * 100:.1f}%"
        )

    selection_layer_demo()


if __name__ == "__main__":
    main()
