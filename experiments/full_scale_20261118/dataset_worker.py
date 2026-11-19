"""Process one source, checkpointing each completed model or failure."""
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError

import numpy as np
from fedrs.experiment import nested_split
from roughset.preprocessing import detect_feature_types
from experiments.full_scale_20261118.model import SCENARIOS, run_model
from experiments.full_scale_20261118.registry import source_registry
from experiments.full_scale_20261118.runner import invoke_with_deadline
from experiments.full_scale_20261118.sources import TooFewClasses, drop_rare_classes, exclusion_details, load_openml, load_pmlb, load_uci


def emit(path, event):
    with open(path, "a", encoding="utf-8") as out:
        out.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        out.flush()
        os.fsync(out.fileno())


def size_class(n):
    return "小" if n < 500 else "中" if n < 5000 else "大" if n < 50000 else "超大"


def metadata(source, item, seeds):
    if source.dynamic_types:
        per_seed = {}
        for seed in seeds:
            dev, _, _ = nested_split(source.frame, source.target, seed)
            per_seed[str(seed)] = list(detect_feature_types(dev, source.features, unique_numeric_threshold=10)[0])
    else:
        per_seed = {str(seed): list(source.continuous) for seed in seeds}
    fractions = {seed: len(features) / len(source.features) for seed, features in per_seed.items()}
    types = {seed: "連續" if value == 1 else "類別/離散" if value == 0 else "混合"
             for seed, value in fractions.items()}
    fraction = next(iter(fractions.values())) if len(set(fractions.values())) == 1 else None
    feature_type = next(iter(types.values())) if len(set(types.values())) == 1 else None
    counts = source.frame[source.target].astype(str).value_counts()
    return dict(cohort=item.cohort, dataset=item.dataset, source_url=source.source_url,
                upstream_commit=item.upstream_commit, raw_sha256=source.raw_sha256,
                prepared_sha256=source.prepared_sha256, original_rows=source.original_rows,
                used_rows=len(source.frame), original_features=source.original_features,
                used_features=len(source.features), used_feature_names=json.dumps(source.original_feature_names, ensure_ascii=False),
                n_classes=len(counts), dropped_classes=json.dumps(source.dropped_classes, ensure_ascii=False),
                minority_share=float(counts.min()/counts.sum()), continuous_fraction=fraction,
                feature_type=feature_type, continuous_by_seed=json.dumps(per_seed, ensure_ascii=False),
                continuous_fraction_by_seed=json.dumps(fractions, ensure_ascii=False),
                feature_type_by_seed=json.dumps(types, ensure_ascii=False),
                feature_type_varies=len(set(types.values())) > 1,
                continuous_features_vary=len({tuple(v) for v in per_seed.values()}) > 1,
                missing_treatments=json.dumps(source.missing_treatments, ensure_ascii=False),
                excluded_features=json.dumps(source.excluded_features, ensure_ascii=False),
                size_class=size_class(source.original_rows),
                same_source_as=item.same_source_as, related_source=item.related_source, status="PREPARED")


def ladder_sample(source, n):
    counts = source.frame[source.target].astype(str).value_counts().sort_index()
    if len(source.frame) < n:
        raise ValueError(f"LADDER_INSUFFICIENT_ROWS requested={n} available={len(source.frame)}")
    exact = counts * n / len(source.frame)
    quotas = np.floor(exact).astype(int)
    for label in (exact - quotas).sort_values(ascending=False, kind="stable").index[:n-int(quotas.sum())]:
        quotas[label] += 1
    rng = np.random.default_rng(20261118)
    selected = []
    labels = source.frame[source.target].astype(str)
    for label, quota in quotas.items():
        candidates = np.flatnonzero(labels.to_numpy() == label)
        if quota:
            selected.extend(rng.choice(candidates, size=int(quota), replace=False).tolist())
    subset = source.frame.iloc[sorted(selected)].copy().reset_index(drop=True)
    subset, dropped = drop_rare_classes(subset, source.target)
    return replace(source, frame=subset, dropped_classes=dropped)


def run(args):
    registry = source_registry().set_index("dataset", drop=False)
    item = registry.loc[args.dataset]
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    scenarios = [x for x in getattr(args, "scenarios", ",".join(SCENARIOS)).split(",") if x]
    if not scenarios or not set(scenarios).issubset(SCENARIOS):
        raise ValueError("Invalid scenarios")
    deadline = args.deadline
    try:
        for attempt in range(1, 4):
            try:
                if item.cohort == "PMLB":
                    source = load_pmlb(item["name"])
                elif item.cohort == "OML51":
                    source = load_openml(int(item.did), args.cache)
                else:
                    source = load_uci(item["name"])
                break
            except (HTTPError, URLError, ConnectionError, TimeoutError) as exc:
                retryable = not isinstance(exc, HTTPError) or exc.code == 429 or exc.code >= 500
                if not retryable or attempt == 3:
                    raise
                emit(args.events, {"kind": "source_retry_failure", "dataset": args.dataset,
                                   "status": type(exc).__name__, "error": f"attempt {attempt}: {exc}"})
                time.sleep(min(2 ** (attempt - 1), max(0.0, deadline - time.time())))
        if source.original_rows > 500_000 and not args.isolated:
            raise RuntimeError("SOURCE_REQUIRES_ISOLATED_SHARD")
        metadata_error = None
        try:
            record = metadata(source, item, seeds)
        except Exception as exc:
            metadata_error = f"{type(exc).__name__}: {exc}"
            record = exclusion_details(source.frame, source.features, source.target, source.original_feature_names,
                                       source.raw_sha256, source.original_rows, source.original_features,
                                       source.dropped_classes, source.source_url)
            record.update(cohort=item.cohort, dataset=item.dataset, upstream_commit=item.upstream_commit,
                          same_source_as=item.same_source_as, related_source=item.related_source,
                          size_class=size_class(source.original_rows), status="PREPARED",
                          prepared_sha256=source.prepared_sha256)
        emit(args.events, {"kind": "registry", "record": record})
        if metadata_error:
            emit(args.events, {"kind": "metadata_failure", "dataset": args.dataset,
                               "status": "FEATURE_TYPE_METADATA_ERROR", "error": metadata_error})
        elif record["continuous_fraction"] is None:
            emit(args.events, {"kind": "metadata_failure", "dataset": args.dataset,
                               "status": "FEATURE_FRACTION_VARIES_BY_SEED",
                               "error": "Source-level continuous_fraction is undefined; see per-seed registry columns"})
    except TooFewClasses as exc:
        if exc.details:
            record = {**exc.details, "cohort": item.cohort, "dataset": item.dataset,
                      "upstream_commit": item.upstream_commit, "same_source_as": item.same_source_as,
                      "related_source": item.related_source, "size_class": size_class(exc.details["original_rows"])}
            emit(args.events, {"kind": "registry", "record": record})
        emit(args.events, {"kind": "source_failure", "dataset": args.dataset,
                           "status": "EXCLUDED_TOO_FEW_CLASSES", "error": str(exc)})
        return 1
    except BaseException as exc:
        emit(args.events, {"kind": "source_failure", "dataset": args.dataset,
                           "status": type(exc).__name__, "error": str(exc)})
        return 1
    full = {}
    for seed in seeds:
        for scenario in scenarios:
            remaining = deadline - time.time()
            if remaining <= 0:
                return 2
            limit = min(2700.0, remaining)
            result = invoke_with_deadline(run_model, (source, args.dataset, seed, scenario), limit)
            if result["status"] == "TIMEOUT" and limit < 2700:
                result["status"] = "SHARD_DEADLINE"
            if result["status"] == "OK":
                data = result["value"]
                emit(args.events, {"kind": "model", "dataset": args.dataset, "seed": seed,
                                   "scenario": scenario, "record": data})
                if seed == 1001 and scenario in ("FED_IID", "FED_A01"):
                    full[scenario] = data
            else:
                emit(args.events, {"kind": "model_failure", "dataset": args.dataset, "seed": seed,
                                   "scenario": scenario, "status": result["status"], "error": result["error"]})
                if result["status"] == "ConflictBoundViolation":
                    return 3
    if source.original_rows >= 20_000:
        for scale, n in (("1800", 1800), ("10000", 10_000), ("FULL", len(source.frame))):
            for scenario in (s for s in ("FED_IID", "FED_A01") if s in scenarios):
                dropped = {}
                reused = scale == "FULL" and scenario in full
                sample_rows = len(source.frame)
                if scale == "FULL" and scenario not in full and 1001 in seeds:
                    emit(args.events, {"kind": "ladder_failure", "dataset": args.dataset, "seed": 1001,
                                       "scenario": scenario, "scale": scale, "scale_rows": n,
                                       "status": "FULL_MODEL_FAILED", "error": "Full-size primary model did not complete"})
                    continue
                if scale == "FULL" and scenario in full:
                    result = {"status": "OK", "value": full[scenario]}
                else:
                    try:
                        sample = source if scale == "FULL" else ladder_sample(source, n)
                        dropped = sample.dropped_classes
                        sample_rows = len(sample.frame)
                    except Exception as exc:
                        emit(args.events, {"kind": "ladder_failure", "dataset": args.dataset, "seed": 1001,
                                           "scenario": scenario, "scale": scale, "scale_rows": n,
                                           "status": type(exc).__name__, "error": str(exc)})
                        continue
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        return 2
                    result = invoke_with_deadline(run_model, (sample, args.dataset, 1001, scenario), min(2700, remaining))
                if result["status"] == "OK":
                    rows = [r for r in result["value"]["rows"] if r["rule_variant"] == "A_ALL_RULES"]
                    emit(args.events, {"kind": "ladder", "dataset": args.dataset, "seed": 1001,
                                       "scenario": scenario, "scale": scale, "scale_rows": n,
                                       "scale_used_rows": sample_rows, "dropped_classes": dropped, "rows": rows,
                                       "timing": None if reused else result["value"]["timing"]})
                else:
                    emit(args.events, {"kind": "ladder_failure", "dataset": args.dataset, "seed": 1001,
                                       "scenario": scenario, "scale": scale, "scale_rows": n,
                                       "status": result["status"], "error": result["error"]})
                    if result["status"] == "ConflictBoundViolation":
                        return 3
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True)
    p.add_argument("--events", required=True)
    p.add_argument("--cache", required=True)
    p.add_argument("--seeds", required=True)
    p.add_argument("--scenarios", default=",".join(SCENARIOS))
    p.add_argument("--deadline", required=True, type=float)
    p.add_argument("--isolated", action="store_true")
    return run(p.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
