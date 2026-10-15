from __future__ import annotations
import ast
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'reference'/'lem2_control_panel_v6_1_reference.py'


def _defs(path):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    return {n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}


def _shape(node):
    # Location metadata is omitted by ast.dump; comments are intentionally irrelevant.
    return ast.dump(node, include_attributes=False)


def test_frozen_lem2_core_ast_matches_v61_reference_exactly():
    ref=_defs(REF); new=_defs(ROOT/'roughset'/'core.py')
    names=['Rule','equivalence_classes','lower_approximation','build_blocks','complex_block','choose_best_pair','minimize_complex','build_one_complex','remove_redundant_complexes','induce_lem2']
    for name in names:
        assert _shape(new[name]) == _shape(ref[name]), name


def test_dependency_math_ast_matches_v61_reference_exactly():
    ref=_defs(REF); new=_defs(ROOT/'roughset'/'reduct.py')
    for name in ['_positive_region_size','dependency_degree']:
        assert _shape(new[name]) == _shape(ref[name]), name


def test_extracted_evaluation_math_ast_matches_v61_reference():
    ref=_defs(REF); new=_defs(ROOT/'roughset'/'evaluation.py')
    names=['balanced_accuracy','classification_accuracy','macro_f1_score','fit_rule_weights','fit_rule_support_sets','aggregate_rule_support_context','aggregate_rule_weights','pairwise_rule_jaccard','audit_rule_conflicts','audit_conflict_cases','evaluate_rule_model','run_centralized']
    for name in names:
        assert _shape(new[name]) == _shape(ref[name]), name


def test_extracted_federated_math_ast_matches_v61_reference():
    ref=_defs(REF); new=_defs(ROOT/'roughset'/'federated.py')
    names=['stratified_client_partition','dirichlet_label_skew_partition','partition_clients','_client_orderings','audit_order_sensitivity','_finite_summary','audit_order_distribution','union_rules_with_provenance','union_rules','run_federated']
    for name in names:
        assert _shape(new[name]) == _shape(ref[name]), name
