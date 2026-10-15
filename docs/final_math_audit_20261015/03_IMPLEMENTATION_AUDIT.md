# 03 — Implementation audit

Each item: **EXPECTED** (contract in `02_MATHEMATICAL_DEFINITIONS.md`), **ACTUAL CODE PATH**,
**ACTUAL FORMULA / LOGIC**, **VERDICT**. "Pre-audit" means `main` @ `5e649ef`; "post-audit" means
this branch. Evidence for every verdict is a test in `tests/` (named) or an output under
`outputs/final_math_audit_20261015/`.

Frozen-code note. `tests/test_reference_ast_parity.py` pins the AST of `core.py` LEM2 functions,
`reduct._positive_region_size`, `reduct.dependency_degree`, the evaluation support/weight
functions and `federated.run_federated` to the V6.1 reference. None of those functions was
modified; the parity tests still pass (`04_TEST_EVIDENCE.md`).

---

## A. Rough Set core and reduct

| # | Item | EXPECTED | ACTUAL CODE PATH | ACTUAL FORMULA / LOGIC | VERDICT |
|---|------|----------|------------------|------------------------|---------|
| A1 | IND | `x IND(B) y ⇔ ∀a∈B a(x)=a(y)` | `core.equivalence_classes`; `reduct._positive_region_size` | `groupby(B, dropna=False)`; `B=∅` handled explicitly in `_positive_region_size` | PASS |
| A2 | Lower approximation | `∪{[x]_B ⊆ X}` | `core.lower_approximation` | union of equivalence classes that are subsets of the concept | PASS (`test_lower_approximation_matches_reference`, `test_inconsistent_table_only_induces_certain_region`) |
| A3 | Positive region | `∪_X B_lower(X)` | `reduct._positive_region_size` | sum of sizes of condition classes with exactly one decision value — same set | PASS (`test_dependency_and_reduct_match_hand_calculation`, P1, P4) |
| A4 | Dependency | `|POS_B|/|U|` | `reduct.dependency_degree` | `_positive_region_size / len(df)` | PASS — unchanged, reporting only (P4) |
| A5 | Minimum-cardinality search | exhaustive by increasing size; first size with a preserving subset | pre: `find_minimum_cardinality_reducts`; post: `find_exact_minimum_cardinality_reducts` | `itertools.combinations` by size; returns all preserving subsets of the first successful size | PASS |
| A6 | Empty reduct | search includes `|R| = 0`; `IND(∅) = {U}` | pre: `range(1, …)`; post: `range(0, …)` | pre-audit **excluded `R = ∅`**: single-class table selected `('a',)`, `γ_C = 0` table selected `('a',)` | **BUG (confirmed, RED E1/E2) → FIXED** |
| A7 | Exact preservation | accept iff `|POS_R| = |POS_C|` (integers) | pre: `np.isclose(γ_R, γ_C)`; post: `_positive_region_size(R) == _positive_region_size(C)` | `np.isclose` (rtol 1e-5, atol 1e-8) accepts `γ_R = (n−2)/n` vs `γ_C = 1` once `n > 2·10^5`; RED P1 selected the non-reduct `('a',)` at `n = 300 000` | **BUG (confirmed, RED P1/P2) → FIXED** |
| A8 | Candidate normalisation | sorted, de-duplicated candidate tuple | `reduct.select_minimum_reduct` | `tuple(sorted({tuple(sorted(c))}))` | PASS (P3, `test_deterministic_multiple_minimum_reduct_selection_records_all_candidates`) |
| A9 | Deterministic lexicographic selection | `min_lex` of candidates | `select_minimum_reduct` | `candidates[0]` after sort; policy fixed to `LEXICOGRAPHIC_FIRST` | PASS (P3) |
| A10 | Equivalence region of fix | the fix must not move reducts when `γ_C > 0`, `≥ 2` classes, `n < 99 900` | both searches | `isclose` tolerance is `1e-8 + 1e-5·|γ_C| ≤ 1.001·10^-5`; for `p ≠ q`, `|p/n − q/n| ≥ 1/n`, which exceeds that tolerance when `n < 99 900`, so `isclose ⇔ equality`; `∅` cannot preserve `POS` when `γ_C > 0` with ≥ 2 classes. UCI3 `n ≤ 1 383` training rows | PASS (`test_exact_search_equals_v61_search_when_gamma_positive_and_n_small`, 120 seeded random tables; UCI3 reducts identical — `old_vs_new.csv`) |
| A11 | Paper lane isolation | `paper.py` semantics unchanged | `paper.run_paper_protocol` → `find_minimum_cardinality_reducts` | V6.1 search body is AST-identical to the reference `find_minimal_reducts`; `paper.py` not edited | PASS (`test_paper_lane_reduct_search_is_v61_verbatim`, `test_paper_protocol_runs_on_small_deterministic_table`) |

## B. LEM2

| # | Item | EXPECTED | ACTUAL CODE PATH | ACTUAL FORMULA / LOGIC | VERDICT |
|---|------|----------|------------------|------------------------|---------|
| L1 | Pair selection | maximise `|[t] ∩ G|`, tie → minimise `|[t]|` | `core.choose_best_pair` | sort key `(-|[t]∩G|, |[t]|, str(t))`; the last key is a deterministic tie-break | PASS (`test_lem2_matches_reference_on_deterministic_fixture`, AST parity) |
| L2 | Certainty | every complex `T` has `∅ ≠ [T] ⊆ B ⊆ X_d` | `core.build_one_complex` | loop exits only on `T ≠ ∅ ∧ [T] ≠ ∅ ∧ [T] ⊆ B`; `B` = lower approximation | PASS |
| L3 | Complex minimisation | drop a condition iff the block stays in `B` | `core.minimize_complex` | tries each condition; keeps the drop if `trial_block ≠ ∅ ∧ trial_block ⊆ B` | PASS |
| L4 | Redundant complex removal | drop a complex whose `B`-coverage is covered by the others | `core.remove_redundant_complexes` | as stated | PASS |
| L5 | Inconsistent data | no rule for objects outside the lower approximation | `core.induce_lem2` | `if not B: continue` | PASS (`test_inconsistent_table_only_induces_certain_region`) |
| L6 | LEM2 with `R = ∅` | `TRUE → d` for one class; no rule otherwise | pre: `induce_lem2(df, [])` → pandas `groupby([])` raises; post: `pipeline.induce_lem2_on_reduct` | post: explicit `IND(∅) = {U}` branch; non-empty `R` delegates to frozen `induce_lem2` | **GAP (crash on a reachable input once A6 is fixed) → FIXED outside the frozen core** (E3, E4, E5, `test_nonempty_reduct_lem2_path_is_the_frozen_core`) |
| L7 | LEM2 receives only reduct features | `cols = selected_reduct` | `pipeline.build_rule_system` | central: `central_cols = central_reduct.selected_reduct`; local: `client_cols = local_reduct.selected_reduct` | PASS (`test_centralized_selected_reduct_controls_lem2_features`, `test_federated_clients_use_own_local_reducts`) |

`core.py` was not modified. `LEM2_CORE_CHANGED = NO`.

## C. Pipeline structure

| # | Item | EXPECTED | ACTUAL CODE PATH | ACTUAL FORMULA / LOGIC | VERDICT |
|---|------|----------|------------------|------------------------|---------|
| P1 | Train/test split | split before any learning | `app._run_dataset` → `splitting.stratified_train_test_split` | split on raw data, seed 42; test ids disjoint from train ids | PASS |
| P2 | Train-only preprocessing | discretiser fit on training clients only | `app._run_split` → `fit_shared_preprocessor(raw_clients or train)` | min/max from training (clients) only; applied to test | PASS (UCI3 attributes are categorical; no bins used) |
| P3 | Central train-only reduct | `select_minimum_reduct(U_train)` | `build_rule_system` | `select_minimum_reduct(train, …)` | PASS (`test_reduct_is_train_only_for_holdout_and_each_fold[HOLDOUT/K_FOLD_CV]`) |
| P4 | Local train-only reduct per client | `select_minimum_reduct(U_c)` for each `c` | `build_rule_system` loop over `client_tables` | one independent selection per client | PASS (`test_federated_clients_use_own_local_reducts`, `test_policy_does_not_change_structural_artifact` — exactly 1 + C selections) |
| P5 | Policy-independent artifact | built once, read-only for all resolvers | `batch.run_policy_matrix` → `app._run_split` → `build_rule_system` then `evaluate_resolvers` | artifact is a frozen dataclass; resolvers only read it | PASS (A1 fingerprint test; `test_policy_does_not_change_structural_artifact`) |
| P6 | UNION semantics | `R_G = ∪_c R_c` by key, first-occurrence order, full provenance | `federated.union_rules_with_provenance` | as stated | PASS (`test_union_preserves_all_sources_and_first_occurrence_order`); rule identity unchanged |
| P7 | Conflict detection | `|{d_r : r ∈ M(x)}| > 1` on `R_G`, before resolution | `pipeline._pre_resolution_conflicts` | as stated, stored in artifact | PASS (`test_conflict_only_metrics_and_case_identity_are_policy_invariant`) |
| P8 | Conflict ids reported per policy | identical ids for every policy | `pipeline.evaluate_resolvers` | the branch `system == "FEDERATED"` never fires (loop uses lower-case `"federated"`), so ids are recomputed from the same artifact mask — numerically identical to the artifact ids | PASS (cosmetic dead branch noted, no numeric effect; not changed) |

## D. Resolvers and federated support

| # | Item | EXPECTED | ACTUAL CODE PATH | ACTUAL FORMULA / LOGIC | VERDICT |
|---|------|----------|------------------|------------------------|---------|
| R1 | FIRST_MATCH | first matching rule in `R_G` order | `evaluation.predict_with_policy` | as stated; default when no match | PASS — unchanged; UCI3 identical (`old_vs_new.csv`) |
| R2 | SIMPLE_VOTING | one vote per matching global rule | `predict_with_policy` | `votes[d] += 1` per matched rule | PASS — unchanged; UCI3 identical |
| R3 | STANDARD_VOTING formula | `Σ_{r∈M_d(x)} w(r)` | `predict_with_policy` | as stated | PASS (resolver unchanged) |
| B3 | STANDARD weight scope (federated) | `w(r) = Σ_{all c} Supp_c(r)` | pre: `aggregate_rule_weights(local fit_rule_weights)`; post: `pipeline.global_rule_support_context` | pre: `w(r) = Σ_{c∈Prov(r)} |[Ante r]_{U_c}| = Σ_{c∈Prov(r)} Supp_c(r)` — non-producing clients ignored | **BUG (confirmed, RED S1/G5) → FIXED** |
| R4 | GLOBAL_STRENGTH formula | union numerator / pooled class size | `predict_with_policy` | `|∪ S(r)| / class_sizes[d]` | PASS — no double count (G2 resolver-level test passed **before** the fix) |
| B4 | GLOBAL_STRENGTH support scope (federated) | `S_G(r) = ⊔_{all c} Supp_c(r)` | pre: `aggregate_rule_support_context(local support sets of own rules)`; post: `global_rule_support_context` | pre: `S_old(r) = ⊔_{c∈Prov(r)} Supp_c(r)` | **BUG (confirmed, RED G1/G3/G5) → FIXED** |
| B5 | GS denominator | `|X_d ∩ U_train|` | `aggregate_rule_support_context` class sizes | `Σ_c |X_d ∩ U_c|` | PASS before and after (G4) |
| B6 | Centralized STANDARD / GS | `w(r) = Supp_{U_train}(r)`, `S(r)` on `U_train` | `fit_rule_weights`, `fit_rule_support_sets` on `train` | antecedent count = support by certainty (4.7) | PASS — unchanged |
| B7 | Provenance vs support | provenance reported, never limits support | `rule_provenance` vs `global_rule_support_sets` | post: producers ⊆ supporters, non-producers included | PASS (S2, G3) |
| B8 | Legacy `federated.run_federated` | — | not called by the production pipeline (`app` imports it but never calls it) | still uses provenance-scoped aggregation; AST-frozen to V6.1 | NOT ON PRODUCTION PATH — documented in `07_LIMITATIONS.md`, not changed |

## E. Hypotheses given before the audit

| Hypothesis | Result |
|---|---|
| A. Reduct search begins at cardinality 1 and excludes `R = ∅` | **Confirmed** (E1/E2 RED) and fixed |
| B. Selection uses floating `np.isclose` | **Confirmed** (P1/P2 RED) and fixed; no numeric effect on UCI3 (A10) |
| C. Federated support computed only for rules a client induced | **Confirmed** (S1/G1/G3/G5 RED) and fixed |
| D. GLOBAL_STRENGTH might double count objects covered by several rules | **Disproven**: the resolver already unions object ids (`test_g2_resolver_numerator_is_a_set_union_independent_of_scope` passed on unmodified code). The only GS defect was scope (C). |
| D. GS denominator might not be the pooled class size | **Disproven** (G4 passed on unmodified code) |
