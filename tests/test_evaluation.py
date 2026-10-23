from __future__ import annotations
import math
import pandas as pd
from roughset.core import Rule
from roughset.evaluation import (
    predict_with_policy, fit_rule_weights, fit_rule_support_sets,
    balanced_accuracy, macro_f1_score, pairwise_rule_jaccard,
    audit_rule_conflicts, audit_conflict_cases, evaluate_rule_model,
    target_coverage_by_class, target_candidate_coverage_by_class,
)


def test_prediction_policies_match_reference(ref):
    train = pd.DataFrame({'A':['x','x','y','y'], 'B':['m','n','m','n'], 'D':['Y','Y','N','N']})
    rules = [Rule((('A','x'),), 'Y'), Rule((('B','m'),), 'N')]
    row = pd.Series({'A':'x','B':'m'})
    weights = fit_rule_weights(train, rules)
    supports, sizes = fit_rule_support_sets(train, rules, 'D')
    ref_rules = [ref.Rule(r.conditions, r.decision, r.source) for r in rules]
    ref_weights = ref.fit_rule_weights(train, ref_rules)
    ref_supports, ref_sizes = ref.fit_rule_support_sets(train, ref_rules, 'D')
    for policy in ['FIRST_MATCH','SIMPLE_VOTING','STANDARD_VOTING','GLOBAL_STRENGTH']:
        kwargs = {}
        ref_kwargs = {}
        if policy == 'STANDARD_VOTING':
            kwargs['rule_weights'] = weights; ref_kwargs['rule_weights'] = ref_weights
        if policy == 'GLOBAL_STRENGTH':
            kwargs.update(rule_support_sets=supports, class_sizes=sizes)
            ref_kwargs.update(rule_support_sets=ref_supports, class_sizes=ref_sizes)
        got = predict_with_policy(row, rules, 'Y', policy, **kwargs)[0]
        exp = ref.predict_with_policy(row, ref_rules, 'Y', policy, **ref_kwargs)[0]
        assert str(got) == str(exp)


def test_metrics_match_reference(ref):
    yt = ['A','A','B','B','B']
    yp = ['A','B','B','B','A']
    assert balanced_accuracy(yt, yp) == ref.balanced_accuracy(yt, yp)
    assert macro_f1_score(yt, yp) == ref.macro_f1_score(yt, yp)


def test_jaccard_and_exact_conflict_metrics():
    local = {
        'c1':[Rule((('A','1'),),'Y'), Rule((('B','2'),),'N')],
        'c2':[Rule((('A','1'),),'Y'), Rule((('B','2'),),'Y')],
    }
    jac = pairwise_rule_jaccard(local)
    assert math.isclose(jac['pairwise_jaccard_antecedent'], 1.0)
    assert math.isclose(jac['pairwise_jaccard_full_rule'], 1/3)
    all_rules = local['c1'] + local['c2']
    audit = audit_rule_conflicts(all_rules)
    assert audit['conflict_group_count'] == 1
    assert math.isclose(audit['conflict_antecedent_rate'], 0.5)


def test_conflict_case_and_resolution_accuracy():
    test = pd.DataFrame({'A':['1','0'], 'B':['2','2'], 'D':['Y','N']})
    rules = [Rule((('A','1'),),'Y'), Rule((('B','2'),),'N')]
    metrics = evaluate_rule_model(test, rules, 'N', 'D', 'FIRST_MATCH')
    audit = audit_conflict_cases(test, rules, metrics['predictions'], 'D')
    assert audit['conflict_case_count'] == 1
    assert audit['conflict_case_rate'] == 0.5
    assert audit['conflict_resolution_accuracy'] == 1.0


def test_target_candidate_coverage_requires_a_matching_rule_for_the_true_class():
    y_true = ['A', 'A', 'B']
    matched = [
        [Rule((('x','1'),), 'B')],
        [Rule((('x','2'),), 'A')],
        [],
    ]

    ordinary = target_coverage_by_class(y_true, matched)
    candidate = target_candidate_coverage_by_class(y_true, matched)

    # Ordinary target coverage asks only whether any rule matched.
    assert ordinary == {'A': 1.0, 'B': 0.0}
    # Candidate coverage asks whether the true decision itself is represented.
    assert candidate == {'A': 0.5, 'B': 0.0}
