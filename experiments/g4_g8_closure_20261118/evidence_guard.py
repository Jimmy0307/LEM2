"""Audit published G4-G8 source tables without re-running or modifying research.

Run:
    python -m experiments.g4_g8_closure_20261118.evidence_guard
    python -m experiments.g4_g8_closure_20261118.evidence_guard --json
Outputs derived values on stdout only; no original research CSV is changed.
Not a confirmatory re-execution and not an endorsement of causal superiority.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
G = ROOT / "docs/research/redesign_20261116/data"
T = ROOT / "docs/research/teacher_dashboard/data"

def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))

def one(items, **filters):
    hits = [x for x in items if all(x.get(k) == v for k, v in filters.items())]
    if len(hits) != 1:
        raise AssertionError(f"Expected exactly 1 source row {filters}; got {len(hits)}")
    return hits[0]

def close(value, target, tol=0.012):
    if not math.isclose(value, target, abs_tol=tol):
        raise AssertionError(f"Value {value} differs from source-established {target}; tolerance {tol}")
    return True

def audit():
    # The UCI20 gate is exploratory and directly diagnoses TRUE-rule confounding.
    g1 = rows(G / "G1_POLICY_SPREAD_FRIEDMAN.csv")
    uci_a = one(g1, regime="NONIID_01", rule_variant="A_ALL_RULES")
    uci_b2 = one(g1, regime="NONIID_01", rule_variant="B2_TRUE_AS_FALLBACK")
    uci_a_spread = float(uci_a["spread_pp"])
    uci_b2_spread = float(uci_b2["spread_pp"])
    close(uci_a_spread, 9.0186635283, 0.00001)
    close(uci_b2_spread, 1.0982289630, 0.00001)
    if not (uci_b2_spread < uci_a_spread and float(uci_b2["friedman_p"]) > 0.05):
        raise AssertionError("UCI20 B2 spread/p direction changed")

    g5 = rows(G / "G5_POLICY_FRIEDMAN.csv")
    om_a = one(g5, regime="NONIID_01", rule_variant="A_ALL_RULES")
    om_b2 = one(g5, regime="NONIID_01", rule_variant="B2_TRUE_AS_FALLBACK")
    om_a_spread = float(om_a["spread_pp"])
    om_b2_spread = float(om_b2["spread_pp"])
    close(om_a_spread, 1.2181969921, 0.00001)
    close(om_b2_spread, 0.3826384160, 0.00001)
    # Critical: p=.0437 (uncorrected), not p>.05; must not claim equivalent policies.
    if not (0.04 < float(om_b2["friedman_p"]) < 0.05):
        raise AssertionError("Confirmatory-source Friedman p has changed")

    structure = rows(G / "G5_STRUCTURE.csv")
    a = one(structure, regime="NONIID_01", discretizer="EQUAL_WIDTH_3", rule_variant="A_ALL_RULES")
    b2 = one(structure, regime="NONIID_01", discretizer="EQUAL_WIDTH_3", rule_variant="B2_TRUE_AS_FALLBACK")
    drop = one(structure, regime="NONIID_01", discretizer="EQUAL_WIDTH_3", rule_variant="B_DROP_TRUE")
    exact_a = float(a["coverage"])
    exact_b2 = float(b2["coverage"])
    exact_drop = float(drop["coverage"])
    true_only = float(a["coverage_only_from_true_rules"])
    conflict_drop = float(a["conflict_created_by_true"])
    close(exact_a, exact_b2, 1e-10)
    close(exact_a - exact_drop, true_only, 1e-10)
    close(true_only, 0.4242988361, 0.00001)
    close(conflict_drop, 0.3517447157, 0.00001)
    if not (float(b2["conflict_rate"]) < float(a["conflict_rate"])):
        raise AssertionError("B2 active conflict is not lower")

    supplements = rows(T / "G2_JOINT_COVERAGE_CONFLICT_3SEED_SUMMARY.csv")
    f0 = one(supplements, system="FEDERATED", variant="BASE_LEM2")
    f1 = one(supplements, system="FEDERATED", variant="VALIDATION_GATED_CONFLICT_AWARE")
    c0 = one(supplements, system="CENTRALIZED", variant="BASE_LEM2")
    c1 = one(supplements, system="CENTRALIZED", variant="VALIDATION_GATED_CONFLICT_AWARE")
    fed_cov_delta = float(f1["coverage_pct"]) - float(f0["coverage_pct"])
    fed_ba_delta = float(f1["balanced_accuracy_pct"]) - float(f0["balanced_accuracy_pct"])
    ctr_cov_delta = float(c1["coverage_pct"]) - float(c0["coverage_pct"])
    ctr_ba_delta = float(c1["balanced_accuracy_pct"]) - float(c0["balanced_accuracy_pct"])
    close(fed_cov_delta, 2.3907129214, 0.00001)
    close(fed_ba_delta, -0.0147704088, 0.00001)
    close(ctr_cov_delta, 13.1730305735, 0.00001)
    close(ctr_ba_delta, 1.5819693359, 0.00001)
    if not (fed_cov_delta > 0 and fed_ba_delta < 0 and ctr_cov_delta > 0 and ctr_ba_delta > 0):
        raise AssertionError("Supplement semantics or baseline direction changed")
    for d in (f0, f1, c0, c1):
        if not math.isclose(float(d["coverage_pct"]) + float(d["no_match_pct"]), 100.0, abs_tol=1e-6):
            raise AssertionError("Coverage and No Match not complementary in published summary")

    manifest = json.loads((T / "G8_OPTIMIZED_REDUCT_MANIFEST.json").read_text(encoding="utf-8"))
    paired = rows(T / "G8_GREEDY_FULL_LEM2_TEST_PAIRED.csv")
    if not (manifest["actual_configs"] == 82 and manifest["paired_exact_configs"] == 36 and len(paired) == 16):
        raise AssertionError("Published G8 counts changed")
    actual = [float(x["delta_test_balanced_accuracy_pct_greedy_minus_full"]) for x in paired]
    # Having identical Train POS is not equivalent to proving equal Test BA.
    if not (any(x < -3.0 for x in actual) and any(x > 1.0 for x in actual)):
        raise AssertionError("G8 expected positive and negative test-quality cases missing")
    confirm = rows(G / "G5_PRIMARY_HYPOTHESES.csv")
    if not (len(confirm) == 4 and all(x["passed"].lower() == "true" for x in confirm)):
        raise AssertionError("Frozen G5 primary hypotheses no longer verified")
    return {
        "status": "PASS_EXISTING_EVIDENCE_ONLY",
        "source_claim": "Exploratory summaries and frozen confirmatory results cross-checked; NO new full-model experiments run",
        "track_A_policy": {
            "uci20_spread_union_pp": uci_a_spread,
            "uci20_spread_B2_pp": uci_b2_spread,
            "uci20_B2_friedman_p": float(uci_b2["friedman_p"]),
            "openml51_spread_union_pp": om_a_spread,
            "openml51_spread_B2_pp": om_b2_spread,
            "openml51_B2_friedman_p_uncorrected": float(om_b2["friedman_p"]),
            "claim_limit": "Small spread is not an equivalence test; G4 selector improvement over ValidationBest remains unproven"
        },
        "track_B_coverage": {
            "openml51_alpha_01_EW3_union_coverage_pct": exact_a * 100,
            "openml51_alpha_01_EW3_B2_coverage_pct": exact_b2 * 100,
            "openml51_alpha_01_EW3_dropTRUE_coverage_pct": exact_drop * 100,
            "openml51_TRUE_only_coverage_pp": true_only * 100,
            "openml51_TRUE_created_conflict_pp": conflict_drop * 100,
            "federated_supplement_effective_coverage_delta_pp": fed_cov_delta,
            "federated_supplement_test_BA_delta_pp": fed_ba_delta,
            "central_supplement_effective_coverage_delta_pp": ctr_cov_delta,
            "central_supplement_test_BA_delta_pp": ctr_ba_delta,
            "claim_limit": "Coverage != accuracy; default class fallback != abstention"
        },
        "track_C_scalability": {
            "reduct_cpu_configs": manifest["actual_configs"],
            "exact_reference_pairs": manifest["paired_exact_configs"],
            "full_LEM2_pairs": len(paired),
            "worst_greedy_vs_full_test_BA_delta_pp": min(actual),
            "best_greedy_vs_full_test_BA_delta_pp": max(actual),
            "claim_limit": "Greedy preserving Train POS is not minimum reduct nor full-pipeline Test BA parity"
        },
        "confirmatory_unchanged": {"g5_hypotheses": len(confirm), "all_previously_reported_PASS": True},
        "next_phase_status": "PARTIAL_REQUIRES_NEW_EXPERIMENTS"
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true", help="Print audit JSON")
    args = p.parse_args()
    result = audit()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("G4_G8_CLOSURE_EVIDENCE_GUARD_PASS", result["status"])
        for key in ("track_A_policy", "track_B_coverage", "track_C_scalability"):
            print(key, json.dumps(result[key], ensure_ascii=False, sort_keys=True))
        print("G4_G8_RESEARCH_COMPLETION_STATUS_PARTIAL_NEW_EXPERIMENTS_REQUIRED")

if __name__ == "__main__":
    main()
