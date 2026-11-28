"""Protocol comparison model: 80/20 holdout vs nested 80(64/16)/20, same outer test split.

For one (source, seed, scenario):
  * NESTED_64_16_20 : rules induced on dev (64 %), all six policies x two rule variants scored on the
                      validation split (16 %) AND the outer test split (20 %). The test rows are the same
                      computation as experiments/full_scale_20261118/model.run_model (parity-checked).
  * HOLDOUT_80_20   : rules induced on dev + val (the full outer 80 %), same partition/discretisation
                      protocol, all policies x variants scored on the SAME outer test split.
Policy selection on validation is done in analysis (tie order = fedrs.experiment.POLICY_ORDER).
Induction, discretisation, partitioning and scoring code are reused unchanged.
"""
import resource
from time import perf_counter

import pandas as pd

from experiments.full_scale_20261118.model import REGIMES, SCENARIOS, ConflictBoundViolation, FeatureMissingTypeMismatch
from fedrs.experiment import fit_model, nested_split
from fedrs.metrics import scores
from fedrs.partition import constrained_partition, original_partition
from fedrs.predict import POLICIES, candidate_profile, match_matrix, resolve_scalable, variant_matrix
from roughset.preprocessing import detect_feature_types

PROTOCOLS = ("NESTED_64_16_20", "HOLDOUT_80_20")
VARIANTS = ("A_ALL_RULES", "B2_TRUE_AS_FALLBACK")


def _clients(train, source, seed, scenario):
    if scenario == "CENTRALIZED":
        return {"central": train}, 0, "CENTRALIZED", "IID", None, "CENTRALIZED", 0
    regime, alpha = REGIMES[scenario]
    try:
        clients = original_partition(train, source.target, 3, seed, regime)
        attempts, status = 1, "ORIGINAL_OK"
    except ValueError as exc:
        clients, attempts, status = constrained_partition(train, source.target, 3, seed, regime)
        attempts += 1
        if clients is None:
            raise RuntimeError(f"PARTITION_FAILED: {status}, attempts={attempts}; original={exc}") from exc
        status = f"CONSTRAINED_{status}"
    distribution = "IID" if scenario == "FED_IID" else "DIRICHLET_NONIID"
    return clients, attempts, status, distribution, alpha, "FEDERATED", 3


def _feature_types(train, source, seed):
    continuous, categorical = (detect_feature_types(train, source.features, unique_numeric_threshold=10)
                               if source.dynamic_types else (source.continuous, source.categorical))
    inconsistent = {f: t for f, t in source.missing_treatments.items()
                    if (t == "DROP_NUMERIC" and f in categorical) or (t == "KEEP_CATEGORY" and f in continuous)}
    if inconsistent:
        raise FeatureMissingTypeMismatch(f"FEATURE_MISSING_TYPE_MISMATCH seed={seed}: {inconsistent}")
    return continuous, categorical


def _score_split(fm, frame, target, fixed, protocol, split):
    matrix = match_matrix(frame, fm.rules)
    truth = frame[target].astype(str).to_numpy()
    rows = []
    for variant in VARIANTS:
        mv = variant_matrix(matrix, fm.ctx, variant)
        prof = candidate_profile(mv, fm.ctx, truth)
        n, no_match = len(truth), int(prof["no_hit"].sum())
        base = {**fixed, "protocol": protocol, "split": split, "eval_rows": n, "rule_variant": variant,
                "no_match_count": no_match, "coverage_pct": 100.0 * (n - no_match) / n,
                "candidate_coverage_pct": 100.0 * float(prof["truth_in_candidates"].mean()),
                "conflict_rate_pct": 100.0 * float(prof["multi"].mean())}
        block = []
        for policy in POLICIES:
            s = scores(truth, resolve_scalable(mv, fm.ctx, policy))
            block.append({**base, "selection_policy": policy, "accuracy_pct": 100.0 * s["accuracy"],
                          "balanced_accuracy_pct": 100.0 * s["ba"]})
        spread = max(x["accuracy_pct"] for x in block) - min(x["accuracy_pct"] for x in block)
        if spread > base["conflict_rate_pct"] + 1e-6:
            raise ConflictBoundViolation(f"{fixed['dataset']} seed={fixed['seed']} {protocol}/{split}/{variant}")
        rows.extend(block)
    return rows


def run_model(source, dataset, seed, scenario):
    started = perf_counter()
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario}")
    dev, val, test = nested_split(source.frame, source.target, seed)
    rows, timing = [], {"dataset": dataset, "seed": seed, "scenario": scenario}
    for protocol in PROTOCOLS:
        train = dev if protocol == "NESTED_64_16_20" else pd.concat([dev, val])
        clients, attempts, status, distribution, alpha, system, n_clients = _clients(train, source, seed, scenario)
        continuous, categorical = _feature_types(train, source, seed)
        t0 = perf_counter()
        fm = fit_model(source.features, continuous, categorical, source.target, clients, train, val, test,
                       "EQUAL_WIDTH_3", "CLASSICAL", 1.0)
        fixed = dict(dataset=dataset, seed=seed, distribution=distribution, dirichlet_alpha=alpha, system=system,
                     client_count=n_clients, train_rows=len(train), rule_count=len(fm.rules))
        splits = (("val", "val"), ("test", "test")) if protocol == "NESTED_64_16_20" else (("test", "test"),)
        for frame_key, split in splits:
            rows.extend(_score_split(fm, fm.frames[frame_key], source.target, fixed, protocol, split))
        timing[protocol] = {"partition_status": status, "partition_attempts": attempts, **fm.timings,
                            "rules": len(fm.rules), "seconds": perf_counter() - t0,
                            "continuous_features": list(continuous), "categorical_features": list(categorical)}
    timing["wall_seconds"] = perf_counter() - started
    timing["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    return {"rows": rows, "timing": timing}
