# 02 — Mathematical definitions (contract)

Scope: RoughSet / Federated LEM2 **non-collaborative baseline**, as implemented on branch
`audit/final-math-freeze-20261015` (base `main` = `5e649ef`). Every formula below was read from
production code; the code path is given so each line can be checked. Where the pre-audit code
differed from the contract, the difference is stated and cross-referenced to
`03_IMPLEMENTATION_AUDIT.md`.

Notation. `U` is a decision table with condition attributes `C` and decision `D`.
`U_train` is the holdout training part. Under federation `U_train = ⊔_c U_c` (disjoint client
partitions, `stratified_client_partition`). `X_d = {z ∈ U : D(z) = d}`.
A rule is `r = Ante(r) → d_r` where `Ante(r)` is a conjunction of attribute–value pairs
(possibly empty, written `TRUE`). `z ⊨ Ante(r)` means `a(z) = v` for every `(a, v)` in `Ante(r)`
(compared as strings, `evaluation._rule_matches`). `[Ante(r)]_V = {z ∈ V : z ⊨ Ante(r)}`.

---

## 4.1 Indiscernibility

For `B ⊆ C`: `x IND(B) y ⇔ ∀a ∈ B: a(x) = a(y)`.

Code: `core.equivalence_classes` (pandas `groupby(B, dropna=False)`), and inside
`reduct._positive_region_size`. For `B = ∅` the relation is total: `U/IND(∅) = {U}`
(`_positive_region_size` branch `if not attrs`; `pipeline.induce_lem2_on_reduct` branch `if not reduct`).

## 4.2 Lower approximation

`B_lower(X) = ∪{[x]_B : [x]_B ⊆ X}` — `core.lower_approximation`.

## 4.3 Positive region

`POS_B(D) = ∪_{X ∈ U/D} B_lower(X)`.

Code: `reduct._positive_region_size` returns the integer `|POS_B(D)|` as the total size of
condition classes whose decision set has exactly one value (`nunique(dropna=False) == 1`).
That is exactly the union of the lower approximations of all decision classes.
For `B = ∅`: `|POS_∅(D)| = |U|` if `U` has one decision value, else `0`.

## 4.4 Dependency

`γ_B(D) = |POS_B(D)| / |U|` — `reduct.dependency_degree`. Used for **reporting only**.

## 4.5 Minimum-cardinality reduct (production selector)

`R ⊆ C` is accepted iff `|POS_R(D)| = |POS_C(D)|` (exact integer equality).
`MinRed(C) = {R ⊆ C : |POS_R(D)| = |POS_C(D)| and |R| = min{|R'| : |POS_{R'}(D)| = |POS_C(D)|}}`,
searched exhaustively by increasing `|R| = 0, 1, …, |C|`.

Code: `reduct.find_exact_minimum_cardinality_reducts` (added by this audit), called by
`reduct.select_minimum_reduct`.

Candidate normalisation: each candidate is sorted, duplicates removed, and the tuple of candidates
is sorted lexicographically. Selection: `selected = min_lex(MinRed(C))` (`LEXICOGRAPHIC_FIRST`).
All candidates are recorded.

Pre-audit difference: the selector used `np.isclose(γ_R, γ_C)` and started at `|R| = 1`
(see 03, items A6/A7). The V6.1 search is kept unchanged as
`find_minimum_cardinality_reducts` for the separate `paper.py` historical lane only.

## 4.6 Empty reduct

`R = ∅` is a legal candidate. Under `IND(∅)`, `U/IND(∅) = {U}`, so
`|POS_∅(D)| = |U|` when every object has the same decision and `0` otherwise.
Therefore `∅ ∈ MinRed(C)` iff `|POS_C(D)| = |U|·[|U/D| = 1]`, i.e. iff the table has one
decision value, or `γ_C(D) = 0`.

LEM2 with `R = ∅` (`pipeline.induce_lem2_on_reduct`): the only complex is the empty conjunction
with block `U`. For each decision `d`, the lower approximation is `U` if `U = X_d` and `∅` otherwise.
Hence LEM2 returns `[TRUE → d]` for a single-class table and `[]` (no certain rule) otherwise.
For non-empty `R` the frozen V6.1 `core.induce_lem2` is called unchanged.

## 4.7 LEM2 certainty (local)

For client `c` with reduct `R_c`, each induced rule satisfies
`∅ ≠ [Ante(r)]_{U_c} ⊆ (R_c)_lower(X_{d_r,c}) ⊆ X_{d_r,c}`
(`core.build_one_complex` stops only when `T ≠ ∅` and `[T] ⊆ B`, `B` = lower approximation;
`minimize_complex` only drops conditions while the block stays non-empty and inside `B`).
Consequence used below: for a rule's **own** client, `|[Ante(r)]_{U_c}| = Supp_c(r)`.

Local certainty does **not** imply pooled certainty: `r` certain on `U_c` can have
`[Ante(r)]_{U_train} ⊄ X_{d_r}`. Example: toy rules `B=1 → Y` (Client_1) and `B=1 → N` (Client_3)
are both locally certain (`toy_math_crosscheck.csv`).

## 4.8 Federated UNION

`R_G = ∪_c R_c`, with rule identity `key(r) = (sorted Ante(r), d_r)`
(`federated.union_rules_with_provenance`). The list order is first occurrence in client order
`Client_1, …, Client_C`, then each client's LEM2 order; later duplicates are dropped from the
list but recorded in provenance.

`R_G` is an **aggregated set of locally certain rules**. It is not a globally certain pooled
rule set and is not `LEM2(⊔_c U_c)`.

`Provenance(r) = {c : r ∈ R_c}`. Provenance is reported; it does not limit support evaluation.

## 4.9 Pre-resolution conflict

`M(x) = {r ∈ R_G : x ⊨ Ante(r)}`, `M_d(x) = {r ∈ M(x) : d_r = d}`.
`x` is a conflict case iff `|{d_r : r ∈ M(x)}| > 1` (`pipeline._pre_resolution_conflicts`).
Conflict flags and case identities are computed once, on the structural artifact, before any
resolver runs. Exact-antecedent conflict (separately reported) groups `R_G` by identical
`Ante(r)` and flags groups with more than one decision (`evaluation.audit_rule_conflicts`):
`exact_conflict_antecedent_rate = #conflicting antecedent groups / #distinct antecedents`.

## 4.10 Reduct Jaccard

`J_R(i, j) = |R_i ∩ R_j| / |R_i ∪ R_j|`, with the explicit convention `J_R(∅, ∅) = 1`
(`reduct.pairwise_reduct_jaccard`). Local–central: `J_R(R_c, R_central)` (`pipeline._jaccard`,
same convention).

## 4.11 Reduct instability

`RI = 1 − mean_{i<j} J_R(i, j)` over client pairs; `NaN` for a single client.

## 4.12 Rule heterogeneity (production definition)

`F_c = {(sorted Ante(r) as strings, str(d_r)) : r ∈ R_c}` (full-rule signature).
`J_rule(i, j) = |F_i ∩ F_j| / |F_i ∪ F_j|` (`NaN` when the union is empty; skipped in the mean).
`H_rule = 1 − mean_{i<j} J_rule(i, j)` (`evaluation.pairwise_rule_jaccard`, `pipeline.build_rule_system`).
So `H_rule = 1 − mean pairwise full-rule Jaccard` — antecedent **and** decision must match.

## 4.13 Resolver formulas (as implemented in `evaluation.predict_with_policy`)

Common tie rule `_resolve_vote(votes, default)`: let `best = max votes`; winners are decisions
with `np.isclose(score, best)`; if `default ∈ winners` predict `default`, else the
string-smallest winner. If `M(x) = ∅` every policy predicts `default`.
Federated default = majority label over pooled client counts (`majority_class_from_clients`);
centralized default = `majority_class(U_train)`.

**FIRST_MATCH.** `pred(x) = d_{r*}`, `r*` the first rule of the ordered list `R_G` with
`x ⊨ Ante(r*)`. Order-sensitive by design; its order sensitivity is measured over client
permutations (all `C!` orders when `C! ≤ 120`; here `C ≤ 5` so all orders).

**SIMPLE_VOTING.** `votes(d) = |M_d(x)|` — one matching global rule, one vote.

**STANDARD_VOTING.** `votes(d) = Σ_{r ∈ M_d(x)} w(r)` with
- centralized: `w(r) = |[Ante(r)]_{U_train}|` (`fit_rule_weights`), which equals
  `Supp_{U_train}(r)` because centralized LEM2 rules are certain on `U_train` (4.7);
- federated (this audit, 4.14): `w(r) = Supp_G(r) = Σ_{all c} Supp_c(r)`.

**GLOBAL_STRENGTH.** For each `d` with `M_d(x) ≠ ∅`:
`GS(d|x) = |{z ∈ U_train : D(z) = d ∧ ∃ r ∈ M_d(x): z ⊨ Ante(r)}| / |X_d ∩ U_train|`,
implemented as `|∪_{r ∈ M_d(x)} S(r)| / class_size(d)` where `S(r)` is the support set of `r`.
The numerator is a **set union** of covered objects (no double counting).

## 4.14 Federated support (STANDARD weight and GLOBAL_STRENGTH sets)

`Supp_c(r) = {z ∈ U_c : z ⊨ Ante(r) ∧ D(z) = d_r}` with object ids `(c, local row)`.
`S_G(r) = ⊔_{all c} Supp_c(r)`, `Supp_G(r) = |S_G(r)| = Σ_c |Supp_c(r)|`,
`ClassSize_d = Σ_c |X_d ∩ U_c|`.
Code: `pipeline.global_rule_support_context` (added by this audit), which evaluates **every**
global rule on **every** client.

Pre-audit difference: weights and support sets were built per client for that client's own rules
only, then summed / unioned, i.e. `w_old(r) = Σ_{c ∈ Provenance(r)} Supp_c(r)` (see 03, items B3/B4).

## 4.15 Distributed = pooled (fixed global rule set)

Because the client partitions are disjoint and ids are `(c, row)`:
- `|S_G(r)| = Σ_c |Supp_c(r)| = |{z ∈ U_train : z ⊨ Ante(r), D(z) = d_r}|`;
- `N_d(x) = |∪_{r ∈ M_d(x)} S_G(r)| = Σ_c N_{c,d}(x)` with
  `N_{c,d}(x) = |{z ∈ U_c : D(z) = d ∧ ∃ r ∈ M_d(x): z ⊨ Ante(r)}|`;
- `ClassSize_d = |X_d ∩ U_train|`;
- so `GS(d|x)` and `votes_STANDARD(d)` are identical whether computed per client and summed or
  directly on the pooled table; predictions are identical. Verified by tests G1/G5 and
  `toy_math_crosscheck.csv`.

## 4.16 Performance metrics (reporting)

`accuracy`, `balanced_accuracy` = mean per-class recall over classes present in `y_true`,
`macro_F1` over the union of true and predicted labels, `coverage = |{x : M(x) ≠ ∅}| / |test|`.
Conflict-restricted variants use only the pre-resolution conflict cases.
`disagreement vs FIRST_MATCH` = fraction of test objects whose prediction differs from FIRST_MATCH.
