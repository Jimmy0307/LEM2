"""One federated model = split -> partition -> discretize -> local induction -> UNION.

All fitting uses DEVELOPMENT client data only.  Validation is used only for
policy/router selection; Test is read only to report final metrics.
"""
from __future__ import annotations

import json
import tracemalloc
from dataclasses import dataclass
from time import perf_counter
from typing import Callable, Dict, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from roughset.evaluation import majority_class_from_clients
from roughset.splitting import stratified_train_test_split

from . import discretize as dz
from .induce import LocalModel, TINY_CLIENT_ROWS, beta_positive_mask, client_overlap, induce_federation, union_rules
from .metrics import scores
from .predict import POLICIES, RULE_VARIANTS, RuleContext, build_context, candidate_profile, match_matrix, resolve, variant_matrix

POLICY_ORDER = ("SIMPLE_VOTING", "GLOBAL_STRENGTH", "STANDARD_VOTING",
                "FIRST_MATCH", "POPULATION_STANDARD", "POPULATION_GLOBAL")
DEFAULT_BASE = {"IID": "GLOBAL_STRENGTH", "NONIID_05": "SIMPLE_VOTING", "NONIID_01": "SIMPLE_VOTING"}


def nested_split(frame: pd.DataFrame, target: str, seed: int):
    """Original G4 protocol: 80/20 outer holdout (seed), then 80/20 inner (seed+1000)."""
    raw = frame.copy().reset_index(drop=True)
    raw["__row_id__"] = np.arange(len(raw), dtype=int)
    train, test = stratified_train_test_split(raw, target, 0.2, seed)
    dev, val = stratified_train_test_split(train, target, test_ratio=0.2, seed=1000 + seed)
    ids = [set(x["__row_id__"]) for x in (dev, val, test)]
    assert not (ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])
    return dev, val, test


@dataclass
class FittedModel:
    target: str
    cut_model: dz.CutModel
    cond_cols: List[str]
    clients: Dict[str, pd.DataFrame]       # discretized client development tables
    frames: Dict[str, pd.DataFrame]        # discretized dev/val/test
    local: Dict[str, LocalModel]
    rules: tuple
    provenance: Dict[object, tuple]
    ctx: RuleContext
    timings: Dict[str, float]
    peak_memory_mb: Optional[float]


def fit_model(features: Sequence[str], continuous: Sequence[str], categorical: Sequence[str], target: str,
              raw_clients: Mapping[str, pd.DataFrame], dev: pd.DataFrame, val: pd.DataFrame, test: pd.DataFrame,
              discretizer: str | Callable = "EQUAL_WIDTH_3", induction: str = "CLASSICAL", beta: float = 1.0,
              measure_memory: bool = False) -> FittedModel:
    if measure_memory:
        tracemalloc.start()
    t0 = perf_counter()
    if callable(discretizer):
        cut_model = discretizer(raw_clients, list(continuous), target, list(categorical))
    else:
        cut_model = dz.fit_method(discretizer, raw_clients, continuous, target, categorical)
    t_bin = perf_counter() - t0
    cond = dz.condition_columns(features, continuous)
    t0 = perf_counter()
    clients = {k: dz.apply_cuts(v, cut_model, target, categorical) for k, v in raw_clients.items()}
    frames = {k: dz.apply_cuts(v, cut_model, target, categorical) for k, v in (("dev", dev), ("val", val), ("test", test))}
    t_apply = perf_counter() - t0
    local = induce_federation(clients, cond, target, induction, beta)
    rules, provenance = union_rules(local)
    pooled = pd.concat(list(clients.values()), ignore_index=True)
    default = majority_class_from_clients(clients, target)
    t0 = perf_counter()
    ctx = build_context(rules, pooled, target, default)
    t_ctx = perf_counter() - t0
    peak = None
    if measure_memory:
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak = peak_bytes / 2 ** 20
    timings = {
        "binning_fit_seconds": t_bin,
        "binning_apply_seconds": t_apply,
        "reduct_seconds": float(sum(m.reduct_seconds for m in local.values())),
        "lem2_seconds": float(sum(m.lem2_seconds for m in local.values())),
        "support_context_seconds": t_ctx,
    }
    return FittedModel(target, cut_model, cond, clients, frames, local, rules, provenance, ctx, timings, peak)


# --------------------------------------------------------- diagnostics ---

def client_rows(fm: FittedModel) -> List[dict]:
    out = []
    for name, m in fm.local.items():
        total = max(m.rows, 1)
        out.append({
            "client": name, "client_rows": m.rows, "client_classes": m.n_classes,
            "class_proportions_json": json.dumps({k: round(v / total, 6) for k, v in sorted(m.class_counts.items())}),
            "single_class_client": m.n_classes == 1, "tiny_client": m.rows < TINY_CLIENT_ROWS,
            "reduct_size": len(m.reduct), "empty_reduct": len(m.reduct) == 0,
            "reduct_json": json.dumps(list(m.reduct)), "reduct_candidates": m.reduct_candidates,
            "local_rules": len(m.rules), "local_empty_antecedent_rules": m.empty_rules,
            "local_nonempty_rules": len(m.rules) - m.empty_rules,
            "local_rule_decisions_json": json.dumps(pd.Series([str(r.decision) for r in m.rules]).value_counts().to_dict() if m.rules else {}),
            "local_pos_fraction_full": m.pos_fraction_full, "local_pos_fraction_reduct": m.pos_fraction_reduct,
            "reduct_seconds": m.reduct_seconds, "lem2_seconds": m.lem2_seconds,
        })
    return out


def config_row(fm: FittedModel) -> dict:
    rules = fm.rules
    lengths = [len(r.conditions) for r in rules]
    nonempty = [l for l in lengths if l > 0]
    empty_decisions = sorted(str(r.decision) for r in rules if not r.conditions)
    groups: Dict[tuple, set] = {}
    for r in rules:
        groups.setdefault(tuple(sorted(r.conditions)), set()).add(str(r.decision))
    exact_conflicts = sum(1 for v in groups.values() if len(v) > 1)
    dev = fm.frames["dev"]
    pos = beta_positive_mask(dev, fm.cond_cols, fm.target, 1.0)
    singles = [m for m in fm.local.values() if m.n_classes == 1]
    by_dec = {}
    for r in rules:
        by_dec.setdefault(str(r.decision), []).append(len(fm.provenance[r.key]))
    return {
        "global_rules": len(rules), "true_rules": len(empty_decisions),
        "true_rule_decisions_json": json.dumps(empty_decisions),
        "nonempty_rules": len(rules) - len(empty_decisions),
        "mean_rule_length": float(np.mean(lengths)) if lengths else float("nan"),
        "mean_nonempty_rule_length": float(np.mean(nonempty)) if nonempty else float("nan"),
        "max_rule_length": int(max(lengths)) if lengths else 0,
        "rules_per_decision_json": json.dumps({k: len(v) for k, v in sorted(by_dec.items())}),
        "rules_shared_by_2plus_clients": int(sum(len(v) > 1 for v in fm.provenance.values())),
        "exact_antecedent_conflict_groups": exact_conflicts,
        "n_clients": len(fm.local),
        "single_class_clients": len(singles),
        "tiny_clients": sum(m.rows < TINY_CLIENT_ROWS for m in fm.local.values()),
        "empty_reduct_clients": sum(len(m.reduct) == 0 for m in fm.local.values()),
        "min_client_rows": min(m.rows for m in fm.local.values()),
        "dev_pos_fraction": float(pos.mean()), "dev_boundary_fraction": float(1 - pos.mean()),
        "mean_local_pos_fraction": float(np.mean([m.pos_fraction_full for m in fm.local.values()])),
        "effective_intervals_json": json.dumps(fm.cut_model.effective_intervals()),
        "mean_effective_intervals": float(np.mean(list(fm.cut_model.effective_intervals().values()))) if fm.cut_model.labels else 0.0,
        "binning_uses_labels": fm.cut_model.uses_labels,
        "binning_uses_pooled_raw_values": fm.cut_model.uses_pooled_raw_values,
        "binning_communication_numbers_per_client": fm.cut_model.communication_numbers_per_client,
        "peak_memory_mb": fm.peak_memory_mb,
        **client_overlap(fm.local),
        **fm.timings,
    }


def structure_rows(fm: FittedModel, matrices: Mapping[str, np.ndarray]) -> List[dict]:
    rows = []
    for split, M in matrices.items():
        y = fm.frames[split][fm.target].astype(str).to_numpy()
        E = fm.ctx.is_empty
        base = candidate_profile(M, fm.ctx, y)
        has_true = E.any()
        if has_true:
            M_ne = M.copy(); M_ne[:, E] = False
            ne = candidate_profile(M_ne, fm.ctx, y)
            hit_true = M[:, E].any(axis=1)
        for variant in RULE_VARIANTS:
            Mv = variant_matrix(M, fm.ctx, variant)
            p = candidate_profile(Mv, fm.ctx, y)
            single = p["single"]
            single_dec = np.full(len(y), None, dtype=object)
            if single.any():
                from .predict import _decision_masks
                masks = _decision_masks(Mv, fm.ctx)
                single_dec[single] = np.asarray(fm.ctx.classes, dtype=object)[masks[single].argmax(axis=1)]
            row = {
                "split": split, "rule_variant": variant, "rows": len(y),
                "coverage": float((~p["no_hit"]).mean()), "no_hit_rate": float(p["no_hit"].mean()),
                "single_rate": float(single.mean()), "conflict_rate": float(p["multi"].mean()),
                "truth_in_candidates_rate": float(p["truth_in_candidates"].mean()),
                "single_precision": float((single_dec[single] == y[single]).mean()) if single.any() else float("nan"),
                "multi_truth_in_candidates": float(p["truth_in_candidates"][p["multi"]].mean()) if p["multi"].any() else float("nan"),
                "mean_matched_rules": float(p["n_matched_rules"].mean()),
            }
            if variant == "A_ALL_RULES":
                row.update({
                    "rows_matched_by_true_rule": float(hit_true.mean()) if has_true else 0.0,
                    "coverage_only_from_true_rules": float((~base["no_hit"] & ne["no_hit"]).mean()) if has_true else 0.0,
                    "conflict_rate_without_true": float(ne["multi"].mean()) if has_true else row["conflict_rate"],
                    "conflict_created_by_true": float((base["multi"] & ~ne["multi"]).mean()) if has_true else 0.0,
                    "conflict_involving_true": float((base["multi"] & hit_true).mean()) if has_true else 0.0,
                    "truth_in_candidates_only_via_true": float((base["truth_in_candidates"] & ~ne["truth_in_candidates"]).mean()) if has_true else 0.0,
                })
            rows.append(row)
    return rows


def router_buckets(M: np.ndarray, ctx: RuleContext) -> np.ndarray:
    prof = candidate_profile(M, ctx, [ctx.default_class] * M.shape[0])
    n_dec, n_rules = prof["n_candidate_decisions"], prof["n_matched_rules"]
    out = np.where(n_dec <= 1, "NO_CONFLICT",
          np.where(n_dec >= 3, "THREE_PLUS_CLASSES",
          np.where(n_rules >= 4, "TWO_CLASS_MANY_RULES", "TWO_CLASS_FEW_RULES")))
    return out.astype(object)


def policy_rows(fm: FittedModel, matrices: Mapping[str, np.ndarray], regime: str,
                variants: Sequence[str] = RULE_VARIANTS) -> List[dict]:
    """Six policies + VALIDATION_BEST + original G4 CONFLICT_BUCKET_ROUTER_V1."""
    from teacher_demo.g4_rule_conflict_router import apply_router, select_router
    out = []
    yv = fm.frames["val"][fm.target].astype(str).to_numpy()
    yt = fm.frames["test"][fm.target].astype(str).to_numpy()
    for variant in variants:
        Mv = variant_matrix(matrices["val"], fm.ctx, variant)
        Mt = variant_matrix(matrices["test"], fm.ctx, variant)
        t0 = perf_counter()
        pv = {p: resolve(Mv, fm.ctx, p) for p in POLICIES}
        pt = {p: resolve(Mt, fm.ctx, p) for p in POLICIES}
        t_pred = perf_counter() - t0
        val_ba = {p: scores(yv, pv[p])["ba"] for p in POLICIES}
        vbest = max(POLICY_ORDER, key=lambda p: (val_ba[p], -POLICY_ORDER.index(p)))
        base = DEFAULT_BASE[regime]
        bv, bt = router_buckets(Mv, fm.ctx), router_buckets(Mt, fm.ctx)
        selection, _, router_val = select_router(yv, pv, bv, base)
        router_test = apply_router(pt, bt, base, selection)
        prof_t = candidate_profile(Mt, fm.ctx, yt)
        methods = {**{p: (pv[p], pt[p]) for p in POLICIES},
                   "VALIDATION_BEST": (pv[vbest], pt[vbest]),
                   "CONFLICT_BUCKET_ROUTER_V1": (router_val, router_test)}
        for method, (v_pred, t_pred_arr) in methods.items():
            sv, st = scores(yv, v_pred), scores(yt, t_pred_arr)
            multi = prof_t["multi"]
            out.append({
                "rule_variant": variant, "method": method,
                "selected_policy": vbest if method == "VALIDATION_BEST" else (json.dumps(selection, sort_keys=True) if method.startswith("CONFLICT") else method),
                "val_ba": sv["ba"], "test_ba": st["ba"], "test_accuracy": st["accuracy"], "test_macro_f1": st["macro_f1"],
                "test_multi_resolution_accuracy": float((t_pred_arr[multi] == yt[multi]).mean()) if multi.any() else float("nan"),
                "test_multi_resolution_given_truth_in": float((t_pred_arr[multi & prof_t["truth_in_candidates"]] == yt[multi & prof_t["truth_in_candidates"]]).mean()) if (multi & prof_t["truth_in_candidates"]).any() else float("nan"),
                "prediction_seconds_six_policies_val_test": t_pred,
            })
    return out


def evaluate(fm: FittedModel, regime: str, variants: Sequence[str] = RULE_VARIANTS) -> Dict[str, object]:
    t0 = perf_counter()
    matrices = {s: match_matrix(fm.frames[s], fm.rules) for s in ("dev", "val", "test")}
    t_match = perf_counter() - t0
    cfg = config_row(fm)
    cfg["match_seconds_dev_val_test"] = t_match
    return {
        "config": cfg,
        "clients": client_rows(fm),
        "structure": structure_rows(fm, matrices),
        "policies": policy_rows(fm, matrices, regime, variants),
        "matrices": matrices,
    }
