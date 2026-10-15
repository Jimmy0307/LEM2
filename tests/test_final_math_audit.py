"""Final mathematical audit (2026-10-15) contract tests.

See docs/final_math_audit_20261015/02_MATHEMATICAL_DEFINITIONS.md for the
definitions these tests pin down:

* E1-E5  empty reduct R = {} (IND({}) = {U}; search includes |R| = 0)
* P1-P3  reduct preservation by exact integer |POS_R(D)| = |POS_C(D)|
* S1-S2  STANDARD_VOTING support scope: Supp_G(r) = sum over ALL clients
* G1-G5  GLOBAL_STRENGTH class coverage: union of covered objects,
         distributed == pooled for a fixed global rule set
* A1     one structural artifact is shared, unmodified, by all four resolvers
"""
from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import pytest

from roughset.core import Rule
from roughset.evaluation import fit_rule_support_sets, predict_with_policy
from roughset.reduct import (
    _positive_region_size,
    dependency_degree,
    select_minimum_reduct,
)

POLICIES = ["FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING", "GLOBAL_STRENGTH"]


def _table(rows, columns=("A", "B", "D")):
    return pd.DataFrame(list(rows), columns=list(columns)).astype(str)


def _keys(rules):
    return [rule.key for rule in rules]


# ---------------------------------------------------------------------------
# Empty reduct
# ---------------------------------------------------------------------------

E1_SINGLE_CLASS = _table(
    [("0", "0", "Y"), ("0", "1", "Y"), ("1", "0", "Y"), ("1", "1", "Y")],
    columns=("a", "b", "D"),
)
# Every condition class {a=0,b=0} and {a=1,b=1} holds both decisions.
E2_DEPENDENCY_ZERO = _table(
    [("0", "0", "Y"), ("0", "0", "N"), ("1", "1", "Y"), ("1", "1", "N")],
    columns=("a", "b", "D"),
)


def test_e1_single_decision_class_selects_empty_reduct():
    df = E1_SINGLE_CLASS
    assert dependency_degree(df, ["a", "b"], "D") == 1.0
    assert dependency_degree(df, [], "D") == 1.0

    result = select_minimum_reduct(df, ["a", "b"], "D")

    assert result.selected_reduct == ()
    assert result.minimum_reduct_size == 0
    assert result.candidate_reducts == ((),)
    assert result.candidate_count == 1
    assert result.selected_dependency == 1.0


def test_e2_full_dependency_zero_selects_empty_reduct():
    df = E2_DEPENDENCY_ZERO
    assert _positive_region_size(df, ["a", "b"], "D") == 0
    assert _positive_region_size(df, [], "D") == 0
    assert dependency_degree(df, ["a", "b"], "D") == 0.0
    assert dependency_degree(df, [], "D") == 0.0

    result = select_minimum_reduct(df, ["a", "b"], "D")

    assert result.selected_reduct == ()
    assert result.minimum_reduct_size == 0
    assert result.candidate_count == 1


def test_e3_empty_reduct_single_class_induces_unconditional_certain_rule():
    from roughset.pipeline import induce_lem2_on_reduct

    rules = induce_lem2_on_reduct(E1_SINGLE_CLASS, (), "D", source="Centralized")

    assert len(rules) == 1
    assert rules[0].conditions == ()
    assert rules[0].decision == "Y"
    assert rules[0].key == ((), "Y")


def test_e3_pipeline_central_empty_reduct_gives_true_implies_y_without_crash():
    from roughset.pipeline import build_rule_system, evaluate_resolvers

    test = _table([("1", "1", "Y"), ("0", "0", "Y")], columns=("a", "b", "D"))
    artifact = build_rule_system(
        E1_SINGLE_CLASS, test, ["a", "b"], "D", run_federated=False
    )

    assert artifact.central_reduct_result.selected_reduct == ()
    assert _keys(artifact.central_rules) == [((), "Y")]
    results = evaluate_resolvers(artifact, POLICIES)
    for policy in POLICIES:
        central = results[policy]["centralized"]
        assert central["predictions"] == ["Y", "Y"]
        assert central["coverage"] == 1.0


def test_e4_empty_reduct_inconsistent_table_invents_no_rule():
    from roughset.pipeline import induce_lem2_on_reduct

    assert induce_lem2_on_reduct(E2_DEPENDENCY_ZERO, (), "D") == []


def test_e4_pipeline_central_empty_reduct_inconsistent_gives_zero_rules():
    from roughset.pipeline import build_rule_system

    test = _table([("0", "0", "Y")], columns=("a", "b", "D"))
    artifact = build_rule_system(
        E2_DEPENDENCY_ZERO, test, ["a", "b"], "D", run_federated=False
    )

    assert artifact.central_reduct_result.selected_reduct == ()
    assert artifact.central_rules == ()


def test_e5_single_class_client_gets_local_empty_reduct_and_true_rule():
    from roughset.pipeline import build_rule_system

    clients = {
        "Client_1": _table([("0", "0", "Y"), ("1", "1", "Y")]),
        "Client_2": _table([("0", "0", "N"), ("1", "1", "Y")]),
    }
    train = pd.concat(clients.values(), ignore_index=True)
    test = _table([("1", "0", "Y")])
    artifact = build_rule_system(train, test, ["A", "B"], "D", clients=clients)

    assert artifact.local_reduct_results["Client_1"].selected_reduct == ()
    assert _keys(artifact.local_rules["Client_1"]) == [((), "Y")]
    assert artifact.local_reduct_results["Client_2"].selected_reduct == ("A",)


def test_nonempty_reduct_lem2_path_is_the_frozen_core():
    from roughset.core import induce_lem2
    from roughset.pipeline import induce_lem2_on_reduct

    df = _table([("0", "0", "N"), ("0", "1", "N"), ("1", "0", "Y"), ("1", "1", "Y")])
    for reduct in (("A",), ("A", "B"), ("B",)):
        assert _keys(induce_lem2_on_reduct(df, reduct, "D")) == _keys(
            induce_lem2(df, list(reduct), "D")
        )


# ---------------------------------------------------------------------------
# Exact positive-region preservation
# ---------------------------------------------------------------------------

def _large_near_tie_table(n: int) -> pd.DataFrame:
    """|POS_C| = n, |POS_{a}| = n - 2, |POS_{b}| = n.

    gamma_{a} = (n-2)/n differs from gamma_C = 1 by 2/n, which np.isclose's
    default rtol=1e-5 accepts once n > 2e5.  The only true size-1 reduct is {b}.
    """
    a = np.zeros(n, dtype=int)
    b = np.zeros(n, dtype=int)
    d = np.array(["Y"] * n, dtype=object)
    a[n - 2] = 1                      # (a=1, b=0, Y)
    a[n - 1], b[n - 1], d[n - 1] = 1, 1, "N"  # (a=1, b=1, N)
    return pd.DataFrame({"a": a.astype(str), "b": b.astype(str), "D": d})


def test_p1_reduct_selection_uses_exact_positive_region_cardinality():
    n = 300_000
    df = _large_near_tie_table(n)
    full_pos = _positive_region_size(df, ["a", "b"], "D")
    assert full_pos == n
    assert _positive_region_size(df, ["a"], "D") == n - 2
    assert _positive_region_size(df, ["b"], "D") == n
    # The float criterion cannot tell these apart at this n.
    assert np.isclose(dependency_degree(df, ["a"], "D"), dependency_degree(df, ["a", "b"], "D"))

    result = select_minimum_reduct(df, ["a", "b"], "D")

    assert result.candidate_reducts == (("b",),)
    assert result.selected_reduct == ("b",)
    assert _positive_region_size(df, result.selected_reduct, "D") == full_pos


def test_p2_reduct_acceptance_does_not_depend_on_dependency_floats(monkeypatch):
    import roughset.reduct as reduct

    df = pd.DataFrame({"A": [0, 0, 1, 1], "B": [0, 1, 0, 1], "D": ["N", "N", "Y", "Y"]})
    # Make every reported float identical; selection must still follow POS sizes.
    monkeypatch.setattr(reduct, "dependency_degree", lambda *_args, **_kw: 0.5)

    result = reduct.select_minimum_reduct(df, ["A", "B"], "D")

    assert result.selected_reduct == ("A",)
    assert result.candidate_reducts == (("A",),)


def test_p3_candidates_are_normalized_and_lexicographically_selected():
    df = pd.DataFrame({"A": [0, 0, 1, 1], "B": [0, 0, 1, 1], "D": ["N", "N", "Y", "Y"]})

    result = select_minimum_reduct(df, ["B", "A"], "D")

    assert result.candidate_reducts == (("A",), ("B",))
    assert result.selected_reduct == ("A",)
    assert result.candidate_count == 2


def test_p4_dependency_reporting_formula_unchanged():
    df = pd.DataFrame({"A": [0, 0, 1], "B": [0, 0, 0], "D": ["N", "Y", "Y"]})
    assert _positive_region_size(df, ["A", "B"], "D") == 1
    assert dependency_degree(df, ["A", "B"], "D") == pytest.approx(1 / 3)


# ---------------------------------------------------------------------------
# STANDARD_VOTING support scope
# ---------------------------------------------------------------------------

def _support_scope_artifact():
    from roughset.pipeline import build_rule_system

    clients = {
        # LEM2 on Client_1 induces A=1 -> Y.
        "Client_1": _table([("1", "0", "Y"), ("0", "0", "N")]),
        # Client_2 induces B=1 -> Y and B=0 -> N, NOT A=1 -> Y, but its row 0
        # (A=1, B=1, Y) satisfies A=1 -> Y.  Row 1 (A=1, B=0, N) matches the
        # antecedent only and must not count as support.
        "Client_2": _table([("1", "1", "Y"), ("1", "0", "N"), ("0", "0", "N")]),
    }
    train = pd.concat(clients.values(), ignore_index=True)
    test = _table([("1", "1", "Y")])
    return clients, build_rule_system(train, test, ["A", "B"], "D", clients=clients)


def test_s1_standard_support_counts_non_producing_clients():
    clients, artifact = _support_scope_artifact()
    rule = ((("A", "1"),), "Y")

    assert rule in _keys(artifact.local_rules["Client_1"])
    assert rule not in _keys(artifact.local_rules["Client_2"])
    assert artifact.rule_provenance[rule] == ("Client_1",)

    supp = {
        name: len(fit_rule_support_sets(df, [Rule(rule[0], rule[1])], "D")[0][rule])
        for name, df in clients.items()
    }
    assert supp == {"Client_1": 1, "Client_2": 1}

    assert artifact.global_rule_weights[rule] == supp["Client_1"] + supp["Client_2"] == 2
    assert artifact.global_rule_support_sets[rule] == frozenset(
        {("Client_1", 0), ("Client_2", 0)}
    )


def test_s2_provenance_is_kept_separate_from_support_scope():
    _clients, artifact = _support_scope_artifact()
    for rule in artifact.global_rules:
        producers = set(artifact.rule_provenance[rule.key])
        supporters = {client for client, _row in artifact.global_rule_support_sets[rule.key]}
        assert producers <= supporters
    # Client_2's object supports a rule it did not produce.
    assert ("Client_2", 0) in artifact.global_rule_support_sets[((("A", "1"),), "Y")]


# ---------------------------------------------------------------------------
# GLOBAL_STRENGTH (and STANDARD) on the hand-checkable toy
# ---------------------------------------------------------------------------

# Hand-checkable toy (also exported to toy_math_crosscheck.csv):
#   Client_1: c1_0 (A=0,B=1,Y)  c1_1 (A=1,B=1,Y)       -> induces B=1 -> Y
#   Client_2: c2_0 (A=1,B=1,Y)  c2_1 (A=0,B=1,N)       -> induces A=1 -> Y, A=0 -> N
#   Client_3: c3_0 (A=0,B=0,Y)  c3_1 (A=0,B=1,N)       -> induces B=0 -> Y, B=1 -> N
TOY_CLIENTS = {
    "Client_1": _table([("0", "1", "Y"), ("1", "1", "Y")]),
    "Client_2": _table([("1", "1", "Y"), ("0", "1", "N")]),
    "Client_3": _table([("0", "0", "Y"), ("0", "1", "N")]),
}
TOY_TEST = _table([("1", "1", "Y"), ("0", "0", "Y"), ("0", "1", "N"), ("1", "0", "Y")])


def _toy_artifact():
    from roughset.pipeline import build_rule_system

    train = pd.concat(TOY_CLIENTS.values(), ignore_index=True)
    # Reduct disabled so the fixed global rule set is the one documented above.
    return train, build_rule_system(
        train, TOY_TEST, ["A", "B"], "D", clients=TOY_CLIENTS, reduct_enabled=False
    )


def _pooled_context(train, rules):
    """Direct pooled calculation over U_train = disjoint union of the clients."""
    support_sets, class_sizes = fit_rule_support_sets(train, rules, "D")
    weights = {key: float(len(objects)) for key, objects in support_sets.items()}
    return weights, support_sets, class_sizes


def _gs_scores(row, rules, support_sets, class_sizes):
    matched = [r for r in rules if all(str(row[a]) == str(v) for a, v in r.conditions)]
    scores = {}
    for decision in sorted({str(r.decision) for r in matched}):
        covered = set()
        for r in matched:
            if str(r.decision) == decision:
                covered |= set(support_sets[r.key])
        scores[decision] = (len(covered), int(class_sizes[decision]))
    return scores


def test_toy_global_rule_set_and_provenance_are_as_documented():
    _train, artifact = _toy_artifact()
    assert [str(r) for r in artifact.global_rules] == [
        "IF B=1 THEN decision=Y [source=Client_1]",
        "IF A=1 THEN decision=Y [source=Client_2]",
        "IF A=0 THEN decision=N [source=Client_2]",
        "IF B=0 THEN decision=Y [source=Client_3]",
        "IF B=1 THEN decision=N [source=Client_3]",
    ]
    assert artifact.rule_provenance[((("B", "1"),), "Y")] == ("Client_1",)


def test_g1_distributed_global_strength_equals_pooled():
    train, artifact = _toy_artifact()
    _w, pooled_sets, pooled_sizes = _pooled_context(train, artifact.global_rules)
    for _, row in TOY_TEST.iterrows():
        assert _gs_scores(
            row, artifact.global_rules, artifact.global_rule_support_sets, artifact.global_class_sizes
        ) == _gs_scores(row, artifact.global_rules, pooled_sets, pooled_sizes)
    for rule in artifact.global_rules:
        assert len(artifact.global_rule_support_sets[rule.key]) == len(pooled_sets[rule.key])


def test_g2_overlapping_matching_rules_do_not_double_count():
    _train, artifact = _toy_artifact()
    x = TOY_TEST.iloc[0]  # A=1, B=1 matches B=1->Y, A=1->Y and B=1->N
    supp = artifact.global_rule_support_sets
    by_b = supp[((("B", "1"),), "Y")]
    by_a = supp[((("A", "1"),), "Y")]
    assert len(by_b) == 3 and len(by_a) == 2 and len(by_a & by_b) == 2

    scores = _gs_scores(x, artifact.global_rules, supp, artifact.global_class_sizes)
    assert scores["Y"] == (3, 4)          # |union| = 3, not 3 + 2 = 5
    assert scores["N"] == (2, 2)


def test_g3_non_producing_clients_contribute_covered_objects():
    _train, artifact = _toy_artifact()
    rule = ((("B", "1"),), "N")  # produced by Client_3 only
    assert artifact.rule_provenance[rule] == ("Client_3",)
    assert artifact.global_rule_support_sets[rule] == frozenset({("Client_2", 1), ("Client_3", 1)})


def test_g4_denominator_equals_pooled_class_size():
    train, artifact = _toy_artifact()
    pooled = train["D"].value_counts().to_dict()
    assert artifact.global_class_sizes == {str(k): int(v) for k, v in pooled.items()}
    assert artifact.global_class_sizes == {"Y": 4, "N": 2}


@pytest.mark.parametrize("policy", ["GLOBAL_STRENGTH", "STANDARD_VOTING"])
def test_g5_fixed_rule_distributed_prediction_equals_pooled(policy):
    train, artifact = _toy_artifact()
    weights, pooled_sets, pooled_sizes = _pooled_context(train, artifact.global_rules)
    for _, row in TOY_TEST.iterrows():
        distributed, _ = predict_with_policy(
            row, artifact.global_rules, artifact.default_class, policy,
            rule_weights=artifact.global_rule_weights,
            rule_support_sets=artifact.global_rule_support_sets,
            class_sizes=artifact.global_class_sizes,
        )
        pooled, _ = predict_with_policy(
            row, artifact.global_rules, artifact.default_class, policy,
            rule_weights=weights, rule_support_sets=pooled_sets, class_sizes=pooled_sizes,
        )
        assert distributed == pooled
    assert artifact.global_rule_weights == weights


def test_g5_toy_predictions_are_hand_verified():
    from roughset.pipeline import evaluate_resolvers

    _train, artifact = _toy_artifact()
    results = evaluate_resolvers(artifact, POLICIES)
    # x0=(1,1): GS  Y=3/4, N=2/2 -> N.  STANDARD Y=3+2, N=2 -> Y.
    # x1=(0,0): STANDARD A=0->N 2 vs B=0->Y 1 -> N.  GS N=2/2 vs Y=1/4 -> N.
    # x2=(0,1): STANDARD Y=3 vs N=2+2 -> N.          GS Y=3/4 vs N=2/2 -> N.
    # x3=(1,0): only Y rules match -> Y everywhere.
    assert results["GLOBAL_STRENGTH"]["federated"]["predictions"] == ["N", "N", "N", "Y"]
    assert results["STANDARD_VOTING"]["federated"]["predictions"] == ["Y", "N", "N", "Y"]


# ---------------------------------------------------------------------------
# Structural artifact identity across resolvers
# ---------------------------------------------------------------------------

def _artifact_fingerprint(artifact):
    return copy.deepcopy(
        {
            "train_row_ids": artifact.train_row_ids,
            "test_row_ids": artifact.test_row_ids,
            "central_reduct": artifact.central_reduct_result,
            "local_reducts": dict(artifact.local_reduct_results),
            "central_rules": _keys(artifact.central_rules),
            "local_rules": {k: _keys(v) for k, v in artifact.local_rules.items()},
            "global_rules": _keys(artifact.global_rules),
            "provenance": dict(artifact.rule_provenance),
            "global_weights": dict(artifact.global_rule_weights),
            "global_support": dict(artifact.global_rule_support_sets),
            "global_class_sizes": dict(artifact.global_class_sizes),
            "conflict_flags": artifact.pre_resolution_conflict_flags,
            "conflict_ids": artifact.pre_resolution_conflict_case_ids,
            "train": artifact.train.to_csv(),
            "test": artifact.test.to_csv(),
        }
    )


def test_a1_all_resolvers_share_one_unmodified_structural_artifact():
    from roughset.pipeline import evaluate_resolver

    _train, artifact = _toy_artifact()
    before = _artifact_fingerprint(artifact)
    conflict_ids = set()
    for policy in POLICIES:
        out = evaluate_resolver(artifact, policy)
        conflict_ids.add(tuple(out["federated"]["pre_resolution_conflict_case_ids"]))
        assert _artifact_fingerprint(artifact) == before
    assert len(conflict_ids) == 1


def test_g2_resolver_numerator_is_a_set_union_independent_of_scope():
    """The GLOBAL_STRENGTH resolver itself unions covered objects (pre-existing behaviour)."""
    r1 = Rule((("A", "1"),), "Y")
    r2 = Rule((("B", "1"),), "Y")
    r3 = Rule((("A", "1"),), "N")
    supports = {r1.key: {1, 2, 3}, r2.key: {2, 3, 4}, r3.key: {9, 10, 11}}
    sizes = {"Y": 8, "N": 4}
    row = pd.Series({"A": "1", "B": "1"})

    pred, matched = predict_with_policy(
        row, [r1, r2, r3], "N", "GLOBAL_STRENGTH", rule_support_sets=supports, class_sizes=sizes
    )

    # Y: |{1,2,3,4}| / 8 = 0.5 (a sum would give 6/8 = 0.75 and win); N: 3/4 = 0.75.
    assert len(matched) == 3
    assert pred == "N"


# ---------------------------------------------------------------------------
# Historical lane and equivalence region of the reduct fix
# ---------------------------------------------------------------------------

def test_paper_lane_reduct_search_is_v61_verbatim(ref):
    import ast
    import inspect
    import textwrap

    import roughset.paper as paper
    import roughset.reduct as reduct

    def body(fn):
        node = ast.parse(textwrap.dedent(inspect.getsource(fn))).body[0]
        stmts = node.body
        if ast.get_docstring(node) is not None:
            stmts = stmts[1:]
        return ast.dump(ast.Module(body=stmts, type_ignores=[])), ast.dump(node.args)

    assert body(reduct.find_minimum_cardinality_reducts) == body(ref.find_minimal_reducts)
    assert paper.find_minimum_cardinality_reducts is reduct.find_minimum_cardinality_reducts


def test_exact_search_equals_v61_search_when_gamma_positive_and_n_small():
    """For n < 1e5, 1/n exceeds isclose's tolerance, and gamma_C > 0 with >= 2
    classes rules out R = ().  There the corrected search must agree with V6.1,
    which is why UCI3 reducts cannot move."""
    from roughset.reduct import (
        find_exact_minimum_cardinality_reducts,
        find_minimum_cardinality_reducts,
    )

    rng = np.random.default_rng(20261015)
    checked = 0
    for _ in range(120):
        n = int(rng.integers(4, 40))
        df = pd.DataFrame(
            {f"f{i}": rng.integers(0, 3, n).astype(str) for i in range(4)}
            | {"D": rng.choice(["x", "y", "z"], n)}
        )
        features = ["f0", "f1", "f2", "f3"]
        if df["D"].nunique() < 2 or _positive_region_size(df, features, "D") == 0:
            continue
        checked += 1
        assert find_exact_minimum_cardinality_reducts(df, features, "D") == (
            find_minimum_cardinality_reducts(df, features, "D")
        )
    assert checked > 40
