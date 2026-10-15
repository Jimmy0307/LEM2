"""Hand-checkable toy cross-check for STANDARD support scope and GLOBAL_STRENGTH.

Recomputes supports / Global Strength with plain set arithmetic (no production
support code) and asserts agreement with the production RuleSystemArtifact.
Writes toy_math_crosscheck.csv next to this folder's parent.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from roughset.evaluation import (  # noqa: E402
    aggregate_rule_support_context,
    aggregate_rule_weights,
    predict_with_policy,
)
from roughset.pipeline import build_rule_system, evaluate_resolvers  # noqa: E402

COLS = ["A", "B", "D"]
CLIENTS = {
    "Client_1": [("0", "1", "Y"), ("1", "1", "Y")],
    "Client_2": [("1", "1", "Y"), ("0", "1", "N")],
    "Client_3": [("0", "0", "Y"), ("0", "1", "N")],
}
TEST = [("1", "1", "Y"), ("0", "0", "Y"), ("0", "1", "N"), ("1", "0", "Y")]
OBJ = {f"c{c[-1]}_{i}": (c, i, row) for c, rows in CLIENTS.items() for i, row in enumerate(rows)}


def sat(row, conditions):
    values = dict(zip(COLS, row))
    return all(values[a] == str(v) for a, v in conditions)


def ante(rule):
    return " AND ".join(f"{a}={v}" for a, v in rule.conditions) or "TRUE"


def main(out_csv: Path):
    clients = {c: pd.DataFrame(rows, columns=COLS) for c, rows in CLIENTS.items()}
    train = pd.concat(clients.values(), ignore_index=True)
    test = pd.DataFrame(TEST, columns=COLS)
    art = build_rule_system(train, test, ["A", "B"], "D", clients=clients, reduct_enabled=False)
    results = evaluate_resolvers(art, ["FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING", "GLOBAL_STRENGTH"])

    class_size = {d: sum(1 for _, _, r in OBJ.values() if r[2] == d) for d in ("Y", "N")}
    rows = []

    # Hand-computed support sets (object names c<k>_<i>), all clients vs producers only.
    supp, old = {}, {}
    for no, rule in enumerate(art.global_rules, 1):
        prov = art.rule_provenance[rule.key]
        covered = {n for n, (_c, _i, r) in OBJ.items() if sat(r, rule.conditions) and r[2] == rule.decision}
        supp[rule.key] = covered
        old[rule.key] = {n for n in covered if OBJ[n][0] in prov}
        per_client = {c: sorted(n for n in covered if OBJ[n][0] == c) for c in CLIENTS}
        prod = {(OBJ[n][0], OBJ[n][1]) for n in covered}
        assert prod == set(art.global_rule_support_sets[rule.key]), rule
        assert len(covered) == art.global_rule_weights[rule.key], rule
        rows.append({
            "section": "RULE", "item": f"r{no}", "antecedent": ante(rule), "decision": rule.decision,
            "provenance": "|".join(prov),
            "client_1_support_ids": " ".join(per_client["Client_1"]),
            "client_2_support_ids": " ".join(per_client["Client_2"]),
            "client_3_support_ids": " ".join(per_client["Client_3"]),
            "client_1_support": len(per_client["Client_1"]),
            "client_2_support": len(per_client["Client_2"]),
            "client_3_support": len(per_client["Client_3"]),
            "global_support_all_clients": len(covered),
            "pre_fix_provenance_scoped_support": len(old[rule.key]),
            "production_global_weight": art.global_rule_weights[rule.key],
        })

    # The pre-fix columns are what the V6.1 aggregation over producing clients yields.
    old_weights = aggregate_rule_weights(art.local_rule_weights)
    old_sets, old_sizes = aggregate_rule_support_context(art.local_rule_support_sets, art.local_class_sizes)
    for key, names in old.items():
        assert old_weights[key] == len(names)
        assert old_sets[key] == {(OBJ[n][0], OBJ[n][1]) for n in names}
    assert old_sizes == art.global_class_sizes

    for t_no, x in enumerate(TEST):
        matched = [r for r in art.global_rules if sat(x, r.conditions)]
        for d in sorted({r.decision for r in matched}):
            md = [r for r in matched if r.decision == d]
            union = set().union(*(supp[r.key] for r in md))
            old_union = set().union(*(old[r.key] for r in md))
            pooled_union = sum(
                1 for r in train.astype(str).itertuples(index=False)
                if r.D == d and any(sat(tuple(r), m.conditions) for m in md)
            )
            assert pooled_union == len(union)
            rows.append({
                "section": "TEST_OBJECT_DECISION", "item": f"x{t_no} A={x[0]},B={x[1]} true={x[2]}",
                "decision": d,
                "matching_rules": " ; ".join(f"{ante(r)}->{r.decision}" for r in md),
                "client_1_support_ids": " ".join(sorted(n for n in union if n.startswith("c1"))),
                "client_2_support_ids": " ".join(sorted(n for n in union if n.startswith("c2"))),
                "client_3_support_ids": " ".join(sorted(n for n in union if n.startswith("c3"))),
                "client_1_support": sum(n.startswith("c1") for n in union),
                "client_2_support": sum(n.startswith("c2") for n in union),
                "client_3_support": sum(n.startswith("c3") for n in union),
                "distributed_union_count": len(union),
                "pooled_union_count": pooled_union,
                "sum_of_rule_supports_if_double_counted": sum(len(supp[r.key]) for r in md),
                "class_denominator": class_size[d],
                "gs_score": len(union) / class_size[d],
                "pre_fix_gs_score": len(old_union) / class_size[d],
                "standard_vote": sum(len(supp[r.key]) for r in md),
                "pre_fix_standard_vote": sum(len(old[r.key]) for r in md),
            })
        for policy in ("GLOBAL_STRENGTH", "STANDARD_VOTING", "SIMPLE_VOTING", "FIRST_MATCH"):
            pred = results[policy]["federated"]["predictions"][t_no]
            row = pd.Series(dict(zip(COLS, x)))
            old_pred, _ = predict_with_policy(
                row, art.global_rules, art.default_class, policy,
                rule_weights={k: float(len(v)) for k, v in old.items()},
                rule_support_sets={k: {(OBJ[n][0], OBJ[n][1]) for n in v} for k, v in old.items()},
                class_sizes=art.global_class_sizes,
            )
            rows.append({
                "section": "PREDICTION", "item": f"x{t_no} A={x[0]},B={x[1]} true={x[2]}",
                "decision": pred, "matching_rules": policy,
                "pre_fix_prediction": old_pred, "default_class": art.default_class,
            })

    frame = pd.DataFrame(rows)
    frame.to_csv(out_csv, index=False, encoding="utf-8")
    print(frame.to_string(index=False, max_colwidth=40))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
