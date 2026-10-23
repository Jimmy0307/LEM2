from __future__ import annotations

import math

from roughset.research_evidence import transition_redundancy_evidence


def test_redundancy_asymmetry_is_positive_when_population_correction_fixes_high_redundancy_competitor():
    scores = {
        'A': {'population_nonredundancy_ratio': 0.5},
        'B': {'population_nonredundancy_ratio': 1.0},
    }
    evidence = transition_redundancy_evidence(
        true_decision='B',
        old_winner='A',
        new_winner='B',
        decision_scores=scores,
    )
    assert evidence['status'] == 'CORRECTED'
    assert evidence['true_candidate_present'] is True
    assert math.isclose(evidence['old_redundancy'], 0.5)
    assert math.isclose(evidence['new_redundancy'], 0.0)
    assert math.isclose(evidence['winner_redundancy_drop'], 0.5)
    assert math.isclose(evidence['redundancy_asymmetry'], 0.5)


def test_redundancy_asymmetry_is_negative_when_correction_over_penalizes_true_decision():
    scores = {
        'A': {'population_nonredundancy_ratio': 0.5},
        'B': {'population_nonredundancy_ratio': 1.0},
    }
    evidence = transition_redundancy_evidence(
        true_decision='A',
        old_winner='A',
        new_winner='B',
        decision_scores=scores,
    )
    assert evidence['status'] == 'HARMED'
    assert math.isclose(evidence['redundancy_asymmetry'], -0.5)


def test_missing_true_candidate_is_classified_as_coverage_failure():
    scores = {
        'A': {'population_nonredundancy_ratio': 0.8},
        'B': {'population_nonredundancy_ratio': 0.9},
    }
    evidence = transition_redundancy_evidence(
        true_decision='C',
        old_winner='A',
        new_winner='B',
        decision_scores=scores,
    )
    assert evidence['true_candidate_present'] is False
    assert evidence['error_type'] == 'COVERAGE_INDUCTION_FAILURE'
    assert math.isnan(evidence['redundancy_asymmetry'])
