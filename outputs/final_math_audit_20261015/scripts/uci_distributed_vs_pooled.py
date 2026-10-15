"""Check distributed == pooled support / GLOBAL_STRENGTH / STANDARD on the real UCI3 artifacts,
and that resolver evaluation leaves the structural artifact untouched.

Rebuilds each structural artifact exactly as app._run_split does (same split, partition,
preprocessor, build_rule_system) and writes uci_distributed_vs_pooled.csv.
Usage: python uci_distributed_vs_pooled.py <snapshot_dir> <out_csv>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).parent))
from roughset.adapters import load_uci_dataset_by_id  # noqa: E402
from roughset.app import _feature_types  # noqa: E402
from roughset.evaluation import fit_rule_support_sets, predict_table  # noqa: E402
from roughset.federated import partition_clients  # noqa: E402
from roughset.pipeline import build_rule_system, evaluate_resolver  # noqa: E402
from roughset.preprocessing import apply_preprocessor, fit_shared_preprocessor  # noqa: E402
from roughset.splitting import stratified_train_test_split  # noqa: E402
from uci_snapshot import replay_fetcher  # noqa: E402

POLICIES = ["FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING", "GLOBAL_STRENGTH"]


def fingerprint(a):
    return repr((
        a.train_row_ids, a.test_row_ids, a.central_reduct_result, sorted(a.local_reduct_results.items()),
        [r.key for r in a.central_rules], sorted((k, [r.key for r in v]) for k, v in a.local_rules.items()),
        [r.key for r in a.global_rules], sorted(a.rule_provenance.items()),
        sorted(a.global_rule_weights.items()), sorted((k, sorted(v)) for k, v in a.global_rule_support_sets.items()),
        sorted(a.global_class_sizes.items()), a.pre_resolution_conflict_flags, a.pre_resolution_conflict_case_ids,
    ))


def main(snapshot: Path, out_csv: Path):
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8-sig"))
    fetch = replay_fetcher(snapshot)
    rows = []
    for uci_id in (44, 19, 12):
        bundle = load_uci_dataset_by_id(uci_id, fetcher=fetch)
        raw = bundle.frame.copy().reset_index(drop=True)
        raw["__row_id__"] = np.arange(len(raw), dtype=int)
        raw_train, raw_test = stratified_train_test_split(raw, bundle.target, cfg["evaluation"]["test_ratio"], cfg["evaluation"]["seed"])
        cont, cat = _feature_types(bundle, raw_train, cfg["preprocessing"])
        for c in cfg["federated"]["client_counts"]:
            raw_clients = partition_clients(raw_train, target_col=bundle.target, n_clients=c, seed=cfg["evaluation"]["seed"],
                                            strategy=cfg["federated"]["partition"])
            prep = fit_shared_preprocessor(raw_clients, bundle.features, bundle.target, cont, cat, cfg["preprocessing"]["n_bins"])
            train = apply_preprocessor(raw_train, prep, bundle.target)
            test = apply_preprocessor(raw_test, prep, bundle.target)
            clients = {k: apply_preprocessor(v, prep, bundle.target) for k, v in raw_clients.items()}
            art = build_rule_system(train, test, list(prep["condition_columns"]), bundle.target, clients=clients,
                                    reduct_enabled=True, metadata={"dataset": bundle.name, "seed": 42})
            target = bundle.target
            # pooled calculation on U_train = disjoint union of the clients
            pooled = pd.concat(clients.values(), ignore_index=True)
            p_sets, p_sizes = fit_rule_support_sets(pooled, art.global_rules, target)
            p_weights = {k: float(len(v)) for k, v in p_sets.items()}
            support_equal = all(len(art.global_rule_support_sets[r.key]) == len(p_sets[r.key]) for r in art.global_rules)
            weights_equal = art.global_rule_weights == p_weights
            sizes_equal = art.global_class_sizes == p_sizes
            # the clients' union is exactly the training set
            union_is_train = sorted(pooled["__row_id__"].astype(int)) == sorted(train["__row_id__"].astype(int))
            non_producer_rules = sum(
                1 for r in art.global_rules
                if {cl for cl, _ in art.global_rule_support_sets[r.key]} - set(art.rule_provenance[r.key])
            )
            preds_equal = {}
            for policy in ("STANDARD_VOTING", "GLOBAL_STRENGTH"):
                dist, _ = predict_table(test, art.global_rules, art.default_class, policy, art.global_rule_weights,
                                        art.global_rule_support_sets, art.global_class_sizes)
                pool, _ = predict_table(test, art.global_rules, art.default_class, policy, p_weights, p_sets, p_sizes)
                preds_equal[policy] = list(map(str, dist)) == list(map(str, pool))
            before = fingerprint(art)
            conflict_ids = {tuple(evaluate_resolver(art, p)["federated"]["pre_resolution_conflict_case_ids"]) for p in POLICIES}
            rows.append({
                "dataset": bundle.name, "client_count": c, "global_rule_count": len(art.global_rules),
                "rules_with_support_from_non_producing_clients": non_producer_rules,
                "client_union_equals_train": union_is_train,
                "support_sizes_distributed_eq_pooled": support_equal,
                "standard_weights_distributed_eq_pooled": weights_equal,
                "class_sizes_distributed_eq_pooled": sizes_equal,
                "standard_predictions_distributed_eq_pooled": preds_equal["STANDARD_VOTING"],
                "global_strength_predictions_distributed_eq_pooled": preds_equal["GLOBAL_STRENGTH"],
                "artifact_unchanged_after_4_resolvers": fingerprint(art) == before,
                "conflict_case_ids_identical_across_4_resolvers": len(conflict_ids) == 1,
                "train_test_row_overlap": len(set(art.train_row_ids) & set(art.test_row_ids)),
            })
            print(rows[-1])
    frame = pd.DataFrame(rows)
    frame.to_csv(out_csv, index=False)
    checks = [c for c in frame.columns if frame[c].dtype == bool]
    print("ALL_TRUE:", bool(frame[checks].all().all()), "| train_test_overlap_total:", int(frame["train_test_row_overlap"].sum()))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
