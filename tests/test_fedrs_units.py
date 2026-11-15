"""Unit tests for fedrs components (no network, small data)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from roughset.core import Rule  # noqa: E402
from roughset.pipeline import induce_lem2_on_reduct  # noqa: E402
from roughset.preprocessing import apply_preprocessor, fit_shared_preprocessor  # noqa: E402
from roughset.reduct import select_minimum_reduct  # noqa: E402

from fedrs import discretize as dz  # noqa: E402
from fedrs.conflict_cuts import _purity_conflict, fit_ef_hist, fit_fcp_hist, fit_loco_select  # noqa: E402
from fedrs.induce import beta_positive_mask, beta_reduct, induce_client, induce_lem2_beta  # noqa: E402
from fedrs.noise import flip_labels, synthetic_table  # noqa: E402
from fedrs.partition import ClientConstraint, constrained_partition, satisfies  # noqa: E402
from fedrs.predict import build_context, candidate_profile, match_matrix, resolve, variant_matrix  # noqa: E402


def _clients(seed=0, n=240):
    df = synthetic_table(n, "balanced", seed)
    return {"C1": df.iloc[: n // 3].reset_index(drop=True), "C2": df.iloc[n // 3: 2 * n // 3].reset_index(drop=True),
            "C3": df.iloc[2 * n // 3:].reset_index(drop=True)}


# ------------------------------------------------------------ discretizers --

def test_equal_width_matches_original_preprocessor_exactly():
    cl = _clients()
    prep = fit_shared_preprocessor(cl, ["x1", "x2", "x3", "c1", "c2"], "class", ["x1", "x2", "x3"], ["c1", "c2"], 3)
    model = dz.fit_equal_width(cl, ["x1", "x2", "x3"], "class", 3)
    for df in cl.values():
        a = apply_preprocessor(df, prep, "class")
        b = dz.apply_cuts(df, model, "class", ["c1", "c2"])
        for f in ("x1", "x2", "x3"):
            assert (a[f + "_bin"].astype(str) == b[f + "_bin"]).all()


def test_mdlp_finds_true_threshold_and_ignores_noise_feature():
    cl = _clients(n=900)
    m = dz.fit_mdlp_central(cl, ["x1", "x2", "x3"], "class")
    assert any(abs(c - 0.35) < 0.02 for c in m.cuts["x1"])
    assert len(m.cuts["x3"]) == 0          # irrelevant feature -> MDLP stops
    h = dz.fit_mdlp_histogram(cl, ["x1"], "class")
    assert any(abs(c - 0.35) < 1 / 32 + 1e-9 for c in h.cuts["x1"])
    assert not h.uses_pooled_raw_values and h.uses_labels


def test_chimerge_and_rs_md_respect_interval_cap_and_find_signal():
    cl = _clients(n=600)
    c = dz.fit_chimerge_central(cl, ["x1", "x2"], "class")
    assert all(len(v) <= dz.MAX_INTERVALS - 1 for v in c.cuts.values())
    assert any(abs(x - 0.35) < 0.05 for x in c.cuts["x1"])
    r = dz.fit_rs_discernibility(cl, ["x1", "x2", "x3"], "class", ["c1", "c2"])
    assert all(len(v) <= dz.MAX_INTERVALS - 1 for v in r.cuts.values())
    assert any(abs(x - 0.35) < 0.05 for x in r.cuts["x1"])


def test_count_matched_controls_copy_interval_count():
    cl = _clients(n=600)
    ref = dz.fit_mdlp_histogram(cl, ["x1", "x2", "x3"], "class")
    ew = dz.fit_count_matched(cl, ["x1", "x2", "x3"], "class", ref, "EW")
    assert ew.effective_intervals() == ref.effective_intervals()


def test_ef_hist_is_federated_and_close_to_pooled_quantiles():
    cl = _clients(n=900)
    a = fit_ef_hist(cl, ["x3"], "class", 3)
    b = dz.fit_equal_frequency(cl, ["x3"], "class", 3)
    assert not a.uses_pooled_raw_values
    assert np.allclose(a.cuts["x3"], b.cuts["x3"], atol=0.02)


# ------------------------------------------------------------- induction --

def test_vprs_beta_one_equals_classical():
    cl = _clients(n=300)
    m = dz.fit_equal_width(cl, ["x1", "x2", "x3"], "class", 3)
    for name, raw in cl.items():
        df = dz.apply_cuts(raw, m, "class", ["c1", "c2"])
        cols = dz.condition_columns(["x1", "x2", "x3", "c1", "c2"], ["x1", "x2", "x3"])
        classical = select_minimum_reduct(df, cols, "class").selected_reduct
        assert beta_reduct(df, cols, "class", 1.0)[0] == tuple(classical)
        a = induce_lem2_on_reduct(df, list(classical), "class", name)
        b = induce_lem2_beta(df, list(classical), "class", 1.0, name)
        assert [r.key for r in a] == [r.key for r in b]


def test_single_class_client_yields_empty_reduct_and_true_rule():
    df = pd.DataFrame({"a": ["x", "y", "z"], "b": ["p", "q", "p"], "class": ["k", "k", "k"]})
    m = induce_client("C", df, ["a", "b"], "class")
    assert m.reduct == () and len(m.rules) == 1 and m.rules[0].conditions == () and m.empty_rules == 1


def test_vprs_tolerates_single_flipped_label_classical_does_not():
    df = pd.DataFrame({"a": ["x"] * 10 + ["y"] * 10, "class": ["P"] * 9 + ["N"] + ["N"] * 10})
    assert beta_positive_mask(df, ["a"], "class", 1.0).sum() == 10
    assert beta_positive_mask(df, ["a"], "class", 0.8).sum() == 20


# ---------------------------------------------------------- rule variants --

def _ctx():
    rules = (Rule((("a", "x"),), "P", "C1"), Rule((), "N", "C2"), Rule((("a", "y"),), "N", "C1"))
    train = pd.DataFrame({"a": ["x", "x", "y", "y"], "class": ["P", "P", "N", "N"]})
    return rules, build_context(rules, train, "class", "P")


def test_rule_variants_drop_and_fallback_true_rule():
    rules, ctx = _ctx()
    test = pd.DataFrame({"a": ["x", "z"], "class": ["P", "N"]})
    M = match_matrix(test, rules)
    assert M.tolist() == [[True, True, False], [False, True, False]]
    A = candidate_profile(M, ctx, test["class"])
    assert A["multi"].tolist() == [True, False]
    B = candidate_profile(variant_matrix(M, ctx, "B_DROP_TRUE"), ctx, test["class"])
    assert B["no_hit"].tolist() == [False, True]
    B2 = variant_matrix(M, ctx, "B2_TRUE_AS_FALLBACK")
    assert B2.tolist() == [[True, False, False], [False, True, False]]
    assert resolve(B2, ctx, "SIMPLE_VOTING").tolist() == ["P", "N"]


def test_tie_prefers_default_then_string_order():
    rules = (Rule((("a", "x"),), "Z", "C1"), Rule((("a", "x"),), "B", "C2"))
    train = pd.DataFrame({"a": ["x", "x"], "class": ["Z", "B"]})
    test = pd.DataFrame({"a": ["x"], "class": ["Z"]})
    M = match_matrix(test, rules)
    assert resolve(M, build_context(rules, train, "class", "Z"), "SIMPLE_VOTING")[0] == "Z"
    assert resolve(M, build_context(rules, train, "class", "Q"), "SIMPLE_VOTING")[0] == "B"


# ------------------------------------------------------------- Control C --

def test_control_c_enforces_constraints_deterministically():
    df = synthetic_table(600, "skewed", 3)
    df["__row_id__"] = np.arange(len(df))
    a, k1, s1 = constrained_partition(df, "class", 3, 5, "NONIID_01")
    b, k2, s2 = constrained_partition(df, "class", 3, 5, "NONIID_01")
    assert s1 == "OK" and k1 == k2 and satisfies(a, "class", ClientConstraint())
    assert all((a[k]["__row_id__"].to_numpy() == b[k]["__row_id__"].to_numpy()).all() for k in a)


def test_flip_labels_rate_and_seed():
    df = synthetic_table(300, "balanced", 1)
    out = flip_labels(df, "class", 0.1, 9)
    assert int((out["class"] != df["class"]).sum()) == 30
    assert out.equals(flip_labels(df, "class", 0.1, 9))


# ------------------------------------------------------------------- P4 --

def test_purity_conflict_counts_only_disagreeing_pure_clients():
    c1 = np.array([[5, 0]])
    c2 = np.array([[0, 3]])
    c3 = np.array([[2, 2]])
    assert _purity_conflict([c1, c2, c3]) == 8
    assert _purity_conflict([c1, c1 * 2, c3]) == 0


def test_fcp_and_loco_run_without_validation_data():
    cl = _clients(n=450)
    f = fit_fcp_hist(cl, ["x1", "x2", "x3"], "class")
    assert any(abs(x - 0.35) < 1 / 32 + 1e-9 for x in f.cuts["x1"])
    loco = fit_loco_select(cl, ["x1", "x2", "x3"], "class", ["c1", "c2"], ["x1", "x2", "x3", "c1", "c2"])
    assert loco.extra["chosen"] in {r["candidate"] for r in loco.extra["table"]}
    assert all(0 <= r["loco_ba"] <= 1 for r in loco.extra["table"])


def test_fed_md_mu_one_matches_pooled_md_objective_and_finds_signal():
    from fedrs.conflict_cuts import fit_fed_md
    cl = _clients(n=450)
    m = fit_fed_md(cl, ["x1", "x2", "x3"], "class", ["c1", "c2"], mu_within=1.0)
    assert any(abs(x - 0.35) < 1 / 32 + 1e-9 for x in m.cuts["x1"])
    assert m.extra["remaining_cross_pairs"] >= 0 and m.extra["remaining_within_pairs"] >= 0
    xc = fit_fed_md(cl, ["x1", "x2", "x3"], "class", ["c1", "c2"], mu_within=0.25)
    assert xc.method == "FED_MD_MU0.25" and xc.extra["rounds"] >= 1
    assert not m.uses_pooled_raw_values
