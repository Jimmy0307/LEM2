"""Run a single frozen model and evaluate the six policies on its test split."""
import resource
from time import perf_counter

from fedrs.experiment import fit_model, nested_split
from fedrs.metrics import scores
from fedrs.partition import constrained_partition, original_partition
from fedrs.predict import POLICIES, candidate_profile, match_matrix, resolve_scalable, variant_matrix
from roughset.preprocessing import detect_feature_types

SCENARIOS = ("CENTRALIZED", "FED_IID", "FED_A05", "FED_A01")
REGIMES = {"FED_IID": ("IID", None), "FED_A05": ("NONIID_05", 0.5), "FED_A01": ("NONIID_01", 0.1)}


class ConflictBoundViolation(RuntimeError):
    pass


class FeatureMissingTypeMismatch(ValueError):
    pass


def run_model(source, dataset, seed, scenario):
    started = perf_counter()
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario}")
    dev, val, test = nested_split(source.frame, source.target, seed)
    if scenario == "CENTRALIZED":
        clients, attempts, status = {"central": dev}, 0, "CENTRALIZED"
        distribution, alpha, system, n_clients = "IID", None, "CENTRALIZED", 0
    else:
        regime, alpha = REGIMES[scenario]
        try:
            clients = original_partition(dev, source.target, 3, seed, regime)
            attempts, status = 1, "ORIGINAL_OK"
        except ValueError as exc:
            clients, attempts, status = constrained_partition(dev, source.target, 3, seed, regime)
            attempts += 1  # Include the failed original partition call.
            if clients is None:
                raise RuntimeError(f"PARTITION_FAILED: {status}, attempts={attempts}; original={exc}") from exc
            status = f"CONSTRAINED_{status}"
        distribution = "IID" if scenario == "FED_IID" else "DIRICHLET_NONIID"
        system, n_clients = "FEDERATED", 3
    continuous, categorical = (detect_feature_types(dev, source.features, unique_numeric_threshold=10)
                               if source.dynamic_types else (source.continuous, source.categorical))
    inconsistent = {feature: treatment for feature, treatment in source.missing_treatments.items()
                    if (treatment == "DROP_NUMERIC" and feature in categorical)
                    or (treatment == "KEEP_CATEGORY" and feature in continuous)}
    if inconsistent:
        raise FeatureMissingTypeMismatch(f"FEATURE_MISSING_TYPE_MISMATCH seed={seed}: {inconsistent}")
    fm = fit_model(source.features, continuous, categorical, source.target, clients, dev, val, test,
                   "EQUAL_WIDTH_3", "CLASSICAL", 1.0)
    t0 = perf_counter()
    matrix = match_matrix(fm.frames["test"], fm.rules)
    match_seconds = perf_counter() - t0
    truth = fm.frames["test"][source.target].astype(str).to_numpy()
    results, predict_seconds = [], 0.0
    for variant in ("A_ALL_RULES", "B2_TRUE_AS_FALLBACK"):
        mv = variant_matrix(matrix, fm.ctx, variant)
        profile = candidate_profile(mv, fm.ctx, truth)
        no_match = int(profile["no_hit"].sum())
        n = len(truth)
        fixed = dict(dataset=dataset, seed=seed, distribution=distribution, dirichlet_alpha=alpha,
                     split_mode="NESTED_64_16_20", system=system, client_count=n_clients,
                     train_rows=len(dev), test_rows=n, rule_count=len(fm.rules), no_match_count=no_match,
                     covered_count=n-no_match, test_coverage_pct=100.0*(n-no_match)/n,
                     true_in_candidate_count=int(profile["truth_in_candidates"].sum()),
                     candidate_coverage_pct=100.0*float(profile["truth_in_candidates"].mean()),
                     conflict_rate_pct=100.0*float(profile["multi"].mean()), rule_variant=variant)
        variant_rows = []
        for policy in POLICIES:
            t0 = perf_counter()
            pred = resolve_scalable(mv, fm.ctx, policy)
            predict_seconds += perf_counter() - t0
            score = scores(truth, pred)
            variant_rows.append({**fixed, "selection_policy": policy,
                                 "accuracy_pct": 100.0*score["accuracy"],
                                 "balanced_accuracy_pct": 100.0*score["ba"]})
        spread = max(x["accuracy_pct"] for x in variant_rows) - min(x["accuracy_pct"] for x in variant_rows)
        if spread > fixed["conflict_rate_pct"] + 1e-6:
            raise ConflictBoundViolation(f"{dataset} seed={seed} scenario={scenario} variant={variant} spread={spread} conflict={fixed['conflict_rate_pct']}")
        results.extend(variant_rows)
    timing = {"dataset": dataset, "seed": seed, "scenario": scenario, "partition_status": status,
              "partition_attempts": attempts, **fm.timings, "match_seconds": match_seconds,
              "predict_seconds": predict_seconds, "wall_seconds": perf_counter()-started,
              "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
              "continuous_features": list(continuous), "categorical_features": list(categorical)}
    return {"rows": results, "timing": timing}
