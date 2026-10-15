# 04 — Test evidence

All commands ran in the project `.venv` (Python 3.11.9, numpy 2.3.5, pandas 2.2.3, pytest 9.0.2).
Exit codes are the real process exit codes. No Windows temp-cleanup `PermissionError` was printed
in any run. Raw logs are under `outputs/final_math_audit_20261015/`.

## 1. Baseline (unmodified source, `main` @ `5e649ef`)

| Command / group | Tests | Result | Exit | Runtime |
|---|---|---|---|---|
| `python -m compileall -q roughset main.py` | — | no output | 0 | — |
| `python -m pytest -q` (full suite) | 74 | **74 passed, 0 failed** | 0 | 30.11 s (cold) / 13.41 s |
| core math + LEM2 (`test_math_core.py`, `test_reference_ast_parity.py`) | 8 | 8 passed | 0 | 1.27 s |
| reduct (`test_reduct.py`) | 1 | 1 passed | 0 | 0.68 s |
| pipeline / reduct integration (`test_reduct_pipeline.py`) | 14 | 14 passed | 0 | 3.78 s |
| paper historical (`test_paper.py`) | 1 | 1 passed | 0 | 1.15 s |
| resolver semantics (`test_evaluation.py`) | 4 | 4 passed | 0 | 0.97 s |
| federated (`test_federated.py`) | 5 | 5 passed | 0 | 1.22 s |

Logs: `baseline/compileall.txt`, `baseline/pytest_full.txt`, `baseline/test_groups.json`.

## 2. RED: new contract tests against the unmodified source

`tests/test_final_math_audit.py` was written before any production change and run against
`5e649ef` (log: `red_green/RED_before_fix.txt`): **18 failed, 5 passed**, exit 1.

| Test | RED result | Failure (from the log) | Meaning |
|---|---|---|---|
| E1 single decision class → `()` | FAIL | `('a',) == ()` | search skipped `|R| = 0` |
| E2 `γ_C = 0` → `()` | FAIL | `('a',) == ()` | search skipped `|R| = 0` |
| E3 `TRUE → Y` (helper) | FAIL | `ImportError induce_lem2_on_reduct` | no empty-reduct LEM2 path existed |
| E3 pipeline central `TRUE → Y` | FAIL | `('a',) == ()` | empty reduct unreachable |
| E4 no invented rule (helper) | FAIL | `ImportError` | as E3 |
| E4 pipeline zero rules | FAIL | `('a',) == ()` | empty reduct unreachable |
| E5 single-class client local `()` | FAIL | `('A',) == ()` | same, per client |
| non-empty reduct delegates to frozen core | FAIL | `ImportError` | helper did not exist (guard test, not a defect) |
| P1 exact POS at `n = 300 000` | FAIL | candidates `(('a',), ('b',))`, expected `(('b',),)` | `np.isclose` accepted `|POS_{a}| = n − 2` as preserving |
| P2 selection independent of floats | FAIL | `(('A',), ('B',))`, expected `(('A',),)` | acceptance followed the floats |
| S1 STANDARD weight over all clients | FAIL | `1.0 == 1 + 1` | Client_2's supporting object ignored |
| S2 provenance ≠ support scope | FAIL | `('Client_2', 0) not in frozenset({('Client_1', 0)})` | support limited to producers |
| G1 distributed GS = pooled | FAIL | `{'N': (1, 2)} != {'N': (2, 2)}` | numerator missed non-producers |
| G2 overlapping rules (toy) | FAIL | `len(...) == 2`, expected 3 | fails on **scope**, not on double counting (see below) |
| G3 non-producers contribute | FAIL | missing `('Client_2', 1)` | scope |
| G5 GS prediction = pooled | FAIL | `'Y' == 'N'` | scope flips the toy prediction |
| G5 STANDARD prediction = pooled | FAIL | `'Y' == 'N'` | scope flips the toy prediction |
| G5 hand-verified toy predictions | FAIL | `['Y','N','N','Y'] != ['N','N','N','Y']` | scope |
| P3 normalisation + lexicographic selection | PASS | — | already correct |
| P4 dependency reporting formula | PASS | — | already correct |
| toy rule set / provenance as documented | PASS | — | UNION already correct |
| G4 denominator = pooled class size | PASS | — | already correct |
| A1 artifact unchanged by all 4 resolvers | PASS | — | already correct |

Added before the fix and run against `5e649ef` (log: `red_green/RED_before_fix_g2_resolver.txt`):

| Test | Result | Meaning |
|---|---|---|
| `test_g2_resolver_numerator_is_a_set_union_independent_of_scope` | **PASS** on unmodified code | GLOBAL_STRENGTH already unions object ids; the double-count hypothesis is disproven |

## 3. Production changes (minimal)

| File | Change |
|---|---|
| `roughset/reduct.py` | add `find_exact_minimum_cardinality_reducts` (integer POS equality, sizes from 0); `select_minimum_reduct` calls it. V6.1 `find_minimum_cardinality_reducts` kept verbatim (comment added) for `paper.py`. `_positive_region_size`, `dependency_degree` unchanged. |
| `roughset/pipeline.py` | add `induce_lem2_on_reduct` (empty-reduct branch; non-empty delegates to frozen `core.induce_lem2`) and `global_rule_support_context` (all-client support); central path calls the same steps as `run_centralized(run_evaluation=False)` through the helper; local LEM2 through the helper; global weights/support from `global_rule_support_context`. |

Not modified: `core.py`, `evaluation.py`, `federated.py`, `paper.py`, `artifacts.py`, `app.py`,
`batch.py`, `config.json`, `main.py`.

## 4. GREEN

After the fix: `tests/test_final_math_audit.py` **24 passed** (`red_green/GREEN_after_fix.txt`).
Two guard tests were then added and pass:

- `test_paper_lane_reduct_search_is_v61_verbatim` — the paper lane's search body is AST-identical
  to the V6.1 reference `find_minimal_reducts`, and `paper.py` uses it.
- `test_exact_search_equals_v61_search_when_gamma_positive_and_n_small` — on 120 seeded random
  tables with `γ_C > 0`, ≥ 2 classes, `n < 40`, the exact search returns exactly the V6.1 result.

## 5. Existing tests touched

Five existing tests in `tests/test_reduct_pipeline.py` failed after the fix **only because their
monkeypatch spies were attached to the old call sites**. Their assertions were not changed; only
the attachment point moved to the production call site:

| Test | Old spy target | New spy target |
|---|---|---|
| `test_centralized_selected_reduct_controls_lem2_features` | `evaluation.induce_lem2` (inside `run_centralized`) | `pipeline.induce_lem2` (inside `induce_lem2_on_reduct`) |
| `test_reduct_disabled_keeps_all_feature_lem2_baseline` | `evaluation.induce_lem2` | `pipeline.induce_lem2` |
| `test_reduct_is_train_only_for_holdout_and_each_fold[HOLDOUT]` / `[K_FOLD_CV]` | `reduct.find_minimum_cardinality_reducts` | `reduct.find_exact_minimum_cardinality_reducts` |
| `test_policy_does_not_change_structural_artifact` | `reduct.find_minimum_cardinality_reducts` | `reduct.find_exact_minimum_cardinality_reducts` |

The diff is 10 lines changed (10 removed, 10 added): the module import, `original = …` and `monkeypatch.setattr(…)` in each test.
`tests/test_reference_ast_parity.py` was not touched and passes, so the frozen V6.1 functions are
still byte-for-byte AST-identical to the reference.

## 6. Final regression (post-fix)

| Command / group | Tests | Result | Exit | Runtime |
|---|---|---|---|---|
| `python -m compileall -q roughset main.py` | — | no output | 0 | — |
| `python -m pytest -q` (full suite) | **100** | **100 passed, 0 failed** | 0 | 11.15 s |
| core math + LEM2 | 8 | 8 passed | 0 | 0.78 s |
| reduct | 1 | 1 passed | 0 | 0.63 s |
| pipeline / reduct integration | 14 | 14 passed | 0 | 1.94 s |
| paper historical | 1 | 1 passed | 0 | 0.83 s |
| resolver semantics (`test_evaluation.py`) | 4 | 4 passed | 0 | 0.42 s |
| resolver semantics incl. no-double-count and artifact identity | 6 | 6 passed | 0 | 0.55 s |
| federated | 5 | 5 passed | 0 | 0.47 s |
| final audit contract (`test_final_math_audit.py`) | 26 | 26 passed | 0 | 14.55 s |
| empty reduct (E1–E5) | 7 | 7 passed | 0 | 0.57 s |
| distributed / pooled equivalence (S1, G1, G5 ×3) | 5 | 5 passed | 0 | 0.90 s |

100 = 74 baseline + 26 new. Logs: `final_regression/{compileall.txt,pytest_full.txt,test_groups.json,final_state.json}`.

## 7. Hand-calculable toy evidence — `toy_math_crosscheck.csv`

Generated by `scripts/toy_crosscheck.py`, which recomputes everything with plain set arithmetic
and **asserts** agreement with the production artifact, and asserts that the "pre-fix" columns are
exactly what the V6.1 aggregation (`aggregate_rule_weights`, `aggregate_rule_support_context`
over producing clients) returns.

Training data (object id: A, B, D):

| Client_1 | Client_2 | Client_3 |
|---|---|---|
| c1_0: 0, 1, Y | c2_0: 1, 1, Y | c3_0: 0, 0, Y |
| c1_1: 1, 1, Y | c2_1: 0, 1, N | c3_1: 0, 1, N |

Class sizes: `|X_Y| = 4` (c1_0, c1_1, c2_0, c3_0), `|X_N| = 2` (c2_1, c3_1). Reduct disabled so the
fixed global rule set is the LEM2 output on {A, B}.

Global rules (UNION order) and supports `Supp_c(r) = {z ∈ U_c : z ⊨ Ante(r), D(z) = d_r}`:

| Rule | Provenance | Client_1 | Client_2 | Client_3 | `Supp_G` all clients | pre-fix (producers only) |
|---|---|---|---|---|---|---|
| r1 `B=1 → Y` | Client_1 | c1_0, c1_1 (2) | c2_0 (1) | — (0) | **3** | 2 |
| r2 `A=1 → Y` | Client_2 | c1_1 (1) | c2_0 (1) | — (0) | **2** | 1 |
| r3 `A=0 → N` | Client_2 | — (0) | c2_1 (1) | c3_1 (1) | **2** | 1 |
| r4 `B=0 → Y` | Client_3 | — (0) | — (0) | c3_0 (1) | **1** | 1 |
| r5 `B=1 → N` | Client_3 | — (0) | c2_1 (1) | c3_1 (1) | **2** | 1 |

r1 and r5 are both locally certain and directly contradict each other on `B = 1`: local certainty
is not pooled certainty.

Test object `x0 = (A=1, B=1)`, true Y. `M_Y(x0) = {r1, r2}`, `M_N(x0) = {r5}`.

| d | covered by client | distributed union `N_d` | pooled union | sum of supports (if double counted) | `ClassSize_d` | `GS(d|x0)` | pre-fix GS |
|---|---|---|---|---|---|---|---|
| Y | C1: c1_0, c1_1; C2: c2_0; C3: — | **3** | 3 | 5 | 4 | **0.75** | 0.75 |
| N | C1: —; C2: c2_1; C3: c3_1 | **2** | 2 | 2 | 2 | **1.00** | 0.50 |

GLOBAL_STRENGTH predicts **N** (1.00 > 0.75); pre-fix predicted Y (0.75 > 0.50).
c1_1 and c2_0 are covered by both r1 and r2 and count once (3, not 5).
STANDARD_VOTING at x0: Y = 3 + 2 = 5, N = 2 → Y (pre-fix 3 vs 1 → Y).

All four test objects (from the CSV):

| x | true | GLOBAL_STRENGTH new / pre-fix | STANDARD new / pre-fix | SIMPLE | FIRST_MATCH |
|---|---|---|---|---|---|
| x0 (1,1) | Y | N / Y | Y / Y | Y | Y |
| x1 (0,0) | Y | N / N | **N / Y** (A=0→N 2 vs B=0→Y 1; pre-fix 1 vs 1 tie → default Y) | Y | N |
| x2 (0,1) | N | N / N | **N / Y** (Y 3 vs N 2+2 = 4; pre-fix 2 vs 2 tie → default Y) | N | Y |
| x3 (1,0) | Y | Y / Y | Y / Y | Y | Y |

FIRST_MATCH and SIMPLE_VOTING do not read supports and are identical before and after.

## 8. Real-data distributed = pooled — `uci_distributed_vs_pooled.csv`

`scripts/uci_distributed_vs_pooled.py` rebuilds all 12 UCI3 structural artifacts exactly as the
batch does and checks, per configuration: client union = training set; for **every** global rule
`Σ_c |Supp_c(r)|` = pooled support on `U_train`; STANDARD weights equal pooled; class sizes equal
pooled; STANDARD and GLOBAL_STRENGTH predictions on every test object equal the pooled
calculation; the artifact fingerprint is unchanged after evaluating all four resolvers; conflict
case ids identical across resolvers; train/test row overlap = 0. **All checks true in all 12
configurations.** Global rule counts match the batch run.

Rules with supporting objects on clients that did not induce them (i.e. affected by the scope bug):

| Dataset | C=2 | C=3 | C=4 | C=5 |
|---|---|---|---|---|
| Hayes-Roth | 20 / 30 | 21 / 28 | 21 / 29 | 24 / 33 |
| Car Evaluation | 94 / 184 | 155 / 207 | 184 / 223 | 197 / 226 |
| Balance Scale | 120 / 209 | 139 / 200 | 127 / 181 | 128 / 183 |

## 9. Reproduction of the reference by the unmodified source

The pre-fix rerun (`PRE_FIX_BASELINE/batch_runs/PRE_FIX_5e649ef`) equals
`evidence/20261014_162216/structural_summary.csv` and `research_chain_summary.csv` in all
12 rows and every non-timing column (absolute tolerance 1e-12; 4 runtime columns excluded).
