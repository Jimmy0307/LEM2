# 08 — Final mathematical freeze report

RoughSet / Federated LEM2 **non-collaborative baseline**.
Repository `Jimmy0307/LEM2`; base `main` @ `5e649ef9d6065e98d472b024e2b50e025c271990`;
branch `audit/final-math-freeze-20261015`; audit date 2026-10-15.
Companion documents: `01_BASELINE_STATE.md` … `07_LIMITATIONS.md` in this folder; evidence in
`outputs/final_math_audit_20261015/` (hashed in `AUDIT_MANIFEST.sha256`).

---

## 1. Executive verdict

**FINAL_MATHEMATICAL_FREEZE = PASS.**

Three implementation defects were proven by tests written before any change, and corrected with
minimal changes in `roughset/reduct.py` and `roughset/pipeline.py`:

1. the production reduct search excluded the empty reduct `R = ∅`;
2. reduct preservation was decided by a floating-point tolerance (`np.isclose`) instead of exact
   positive-region cardinality;
3. federated STANDARD_VOTING weights and GLOBAL_STRENGTH support sets were computed only on the
   clients that induced each rule (provenance scope) instead of on all clients.

Defects 1–2 have no effect on the UCI3 numbers (proved, and confirmed by identical reducts and
structure). Defect 3 changed STANDARD_VOTING and GLOBAL_STRENGTH results in 11 of 12
configurations each; **all prior federated STANDARD_VOTING and GLOBAL_STRENGTH results are
superseded**. FIRST_MATCH and SIMPLE_VOTING are unchanged in all 12 configurations. The Rough Set
primitives, LEM2 (`core.py`) and the `paper.py` lane are unchanged. No stop condition was met.

## 2. Exact mathematical definitions

Full contract with code paths: `02_MATHEMATICAL_DEFINITIONS.md`. Summary:

- `IND(B)`: equal values on every `a ∈ B`; `U/IND(∅) = {U}`.
- `B_lower(X) = ∪{[x]_B ⊆ X}`; `POS_B(D) = ∪_X B_lower(X)`; `γ_B(D) = |POS_B(D)|/|U|` (reporting only).
- Reduct: minimum `|R|`, `R ⊆ C`, with `|POS_R(D)| = |POS_C(D)|` (integers), searched from `|R| = 0`;
  lexicographically first candidate selected; all candidates recorded.
- LEM2 local certainty: `∅ ≠ [Ante(r)]_{U_c} ⊆ X_{d,c}`; `R = ∅` gives `TRUE → d` iff `U_c` is single-class, else no rule.
- `R_G = ∪_c R_c` (rule key = sorted antecedent + decision) is an aggregated set of locally certain
  rules — not pooled-certain, not `LEM2(U_train)`. `Provenance(r) = {c : r ∈ R_c}`.
- Conflict: `|{d_r : r ∈ M(x)}| > 1`, `M(x)` = matching global rules.
- `J_R`, `RI = 1 − mean J_R`; `H_rule = 1 − mean pairwise full-rule Jaccard`.
- FIRST_MATCH: first matching rule in UNION order. SIMPLE_VOTING: one vote per matching rule.
  STANDARD_VOTING: `Σ_{r∈M_d(x)} Supp_G(r)`, `Supp_G(r) = Σ_{all c} |{z ∈ U_c : z ⊨ Ante(r), D(z) = d_r}|`.
  GLOBAL_STRENGTH: `|∪_{r∈M_d(x)} S_G(r)| / |X_d ∩ U_train|`. Ties: `np.isclose` winners, default
  class preferred, else string-smallest.

## 3. Audit findings

Item-by-item table with EXPECTED / ACTUAL CODE PATH / ACTUAL FORMULA / VERDICT:
`03_IMPLEMENTATION_AUDIT.md`. All Rough Set, LEM2, pipeline-structure and resolver-formula items
pass; the three defects above were the only failures. One cosmetic dead branch in
`pipeline.evaluate_resolvers` (`system == "FEDERATED"` vs lower-case loop variable) has no numeric
effect and was left unchanged.

## 4. Bugs found

| ID | Bug | Proof (RED on `5e649ef`) |
|---|---|---|
| BUG-1 | `find_minimum_cardinality_reducts` searched `|R| = 1..|C|`, so `R = ∅` was never a candidate (single-class or `γ_C = 0` tables selected `('a',)`). | E1, E2, E3/E4 pipeline, E5 |
| BUG-2 | Preservation by `np.isclose(γ_R, γ_C)`; with `n = 300 000`, `{a}` with `|POS| = n − 2` was accepted and selected instead of the true reduct `{b}`. | P1, P2 |
| BUG-3 | Federated STANDARD weight `= Σ_{c∈Prov(r)} Supp_c(r)` and GLOBAL_STRENGTH sets `= ⊔_{c∈Prov(r)} Supp_c(r)` — non-producing clients' supporting objects ignored; distributed ≠ pooled. | S1, S2, G1, G3, G5 (×3) |
| GAP-1 | With `R = ∅` reachable, LEM2 had no path for it: the frozen `induce_lem2` raises on an empty attribute list (pandas `groupby([])`). | E3, E4 helper tests |

## 5. Bugs fixed

| ID | Fix | File |
|---|---|---|
| BUG-1, BUG-2 | New `find_exact_minimum_cardinality_reducts`: sizes from 0, accept iff `_positive_region_size(R) == _positive_region_size(C)`. `select_minimum_reduct` uses it. `dependency_degree` unchanged. | `roughset/reduct.py` |
| GAP-1 | New `induce_lem2_on_reduct`: `R = ∅` → `[TRUE → d]` for a single-class table, `[]` otherwise; non-empty `R` → frozen `core.induce_lem2` unchanged. Central and local induction call it. | `roughset/pipeline.py` |
| BUG-3 | New `global_rule_support_context`: evaluates every global rule on every client; `Supp_G(r) = Σ_c |Supp_c(r)|`, `S_G(r) = ⊔_c Supp_c(r)`, class sizes summed. Replaces the provenance-scoped aggregation in `build_rule_system`. | `roughset/pipeline.py` |

## 6. Suspected bugs that were disproven

- **GLOBAL_STRENGTH double counting** objects covered by several matching rules — disproven: the
  resolver already unions object ids (`test_g2_resolver_numerator_is_a_set_union_independent_of_scope`
  passed on the unmodified code; toy: 3 covered objects, not 5).
- **GLOBAL_STRENGTH denominator** not pooled — disproven (G4 passed on unmodified code).
- **Policy altering the structural artifact** — disproven (A1 passed on unmodified code; batch builds
  each artifact once).
- **Train/test leakage in reduct selection** — none (`test_reduct_is_train_only_*`; train/test row
  overlap 0 in all 12 UCI3 artifacts).

## 7. Files changed

| File | Kind |
|---|---|
| `roughset/reduct.py` | production (+28 / −1 lines) |
| `roughset/pipeline.py` | production (+67 / −24 lines) |
| `tests/test_final_math_audit.py` | new tests |
| `tests/test_reduct_pipeline.py` | spy attachment points only (10 lines changed; assertions unchanged) |
| `docs/final_math_audit_20261015/*.md` | audit documents |
| `outputs/final_math_audit_20261015/**` | evidence (force-added; `outputs/` is git-ignored) |

Unchanged: `core.py`, `evaluation.py`, `federated.py`, `paper.py`, `artifacts.py`, `app.py`,
`batch.py`, `config.json`, `main.py`, `reference/`, `evidence/`.

## 8. Tests added

`tests/test_final_math_audit.py`, 26 tests: E1, E2, E3 (helper + pipeline), E4 (helper + pipeline),
E5, non-empty-reduct delegation; P1–P4; S1, S2; toy rule set; G1, G2 (toy), G2 (resolver-level),
G3, G4, G5 (GLOBAL_STRENGTH, STANDARD, hand-verified predictions); A1 artifact identity; paper-lane
AST identity; exact = V6.1 search on 120 random tables in the equivalence region.

## 9. Final pytest result

`python -m pytest -q` → **100 passed, 0 failed**, exit 0, 11.15 s (74 baseline + 26 new).
Group runs (core math/LEM2, reduct, pipeline, paper historical, resolver semantics, federated,
empty reduct, distributed/pooled) all exit 0 — `04_TEST_EVIDENCE.md` §6.

## 10. compileall result

`python -m compileall -q roughset main.py` → exit 0, no output (baseline and final).

## 11. Empty reduct evidence

E1 (single class): `γ_C = γ_∅ = 1`, selected `()`, minimum size 0, 1 candidate. E2 (`γ_C = γ_∅ = 0`):
selected `()`. E3: `R = ∅` all-Y → exactly `[TRUE → Y]`; through `build_rule_system` all four
resolvers predict Y with coverage 1, no crash. E4: `R = ∅`, inconsistent → `[]`, central rules `()`.
E5: a single-class client gets local reduct `()` and rule `TRUE → Y` while the other client keeps
`('A',)`.

## 12. Exact POS equality evidence

P1: `n = 300 000`, `|POS_C| = n`, `|POS_{a}| = n − 2`, `|POS_{b}| = n`; `np.isclose` judges `{a}`
preserving; the fixed selector returns candidates `(('b',),)`. P2: with every dependency float
patched to 0.5 the selector still returns `('A',)`. A10: for `n < 99 900` and `γ_C > 0` with ≥ 2
classes the old and new searches coincide (proved; 120-table test); UCI3 reducts identical pre/post.

## 13. STANDARD support-scope evidence

S1 (two clients): `A=1 → Y` induced by Client_1 only; Client_2 has `(A=1, B=1, Y)`;
`Supp_1 = Supp_2 = 1`, `Supp_G = 2` (pre-fix 1); Client_2's `(A=1, B=0, N)` matches the antecedent
but is correctly not counted. Toy (`toy_math_crosscheck.csv`): `B=1 → Y` support 2 + 1 + 0 = 3
(pre-fix 2). UCI3: 51–87% of global rules per configuration have support on non-producing clients.

## 14. Global Strength no-double-count evidence

Toy `x0 = (A=1, B=1)`: `M_Y = {B=1 → Y, A=1 → Y}` cover {c1_0, c1_1, c2_0} and {c1_1, c2_0};
union 3, sum 5; `GS(Y|x0) = 3/4`. Resolver-level test: supports {1,2,3} and {2,3,4} give 4/8 = 0.5,
not 6/8.

## 15. Distributed == pooled evidence

Toy: per-rule supports, per-decision unions, denominators and predictions equal the pooled
calculation (G1, G5, asserted in `toy_crosscheck.py`). Real data
(`uci_distributed_vs_pooled.csv`): for all 12 UCI3 configurations, every global rule's support,
every STANDARD weight, the class sizes and every STANDARD / GLOBAL_STRENGTH test prediction equal
the pooled calculation on `U_train`.

## 16. UCI3 rerun summary

`outputs/final_math_audit_20261015/UCI3_HOLDOUT42_FINAL/` — Hayes-Roth, Car Evaluation, Balance
Scale; HOLDOUT, seed 42, STRATIFIED, C = 2..5, reduct enabled, four resolvers; exit 0. Full tables:
`05_UCI3_RESULTS.md`. The unmodified source first reproduced the 2026-10-14 reference exactly
(`PRE_FIX_BASELINE/`, 0 differences at 1e-12).

## 17. Old-vs-new comparison

`old_vs_new.csv` (48 rows: dataset × C × policy; old = unmodified rerun = reference on every value
the reference stores):
- Structure (reducts, rules, provenance, coverage, conflict cases): **0 differences** in all 12
  configurations.
- FIRST_MATCH: 0 / 12 changed. SIMPLE_VOTING: 0 / 12 changed.
- STANDARD_VOTING: 11 / 12 changed; GLOBAL_STRENGTH: 11 / 12 changed (Hayes-Roth C = 2 unchanged
  for both). Example BA changes: Hayes-Roth C = 5 STD 0.744 → 0.578, GS 0.800 → 0.733; Car C = 4 GS
  0.725 → 0.683; Balance C = 2 GS 0.511 → 0.535.
- Winner changes: Car C = 4 macro-F1 GS → STD; Balance C = 5 BA and conflict BA STD → GS.

## 18. Structural findings

- Central reducts are the full attribute set in all three datasets; local reducts shrink only in
  Hayes-Roth (C = 4, 5).
- RI = 0 in Car and Balance at every C, and in Hayes-Roth at C = 2, 3, while rule heterogeneity
  (0.75–0.97) and inference conflict (0.12–0.66) are high.
- Inference conflict (0.115–0.659) far exceeds exact-antecedent conflict (0–0.058).
- Conflict rises with C in Car and Balance; Hayes-Roth is non-monotonic.
- Local rules shorten and matches per test object rise with C in all three datasets.

## 19. Resolver findings

- No resolver is best in every configuration on BA, conflict BA or macro-F1.
- FIRST_MATCH best on Hayes-Roth (C ≥ 3), GLOBAL_STRENGTH best on Car (BA, conflict BA), STANDARD_VOTING
  best on Balance (C ≤ 4); SIMPLE_VOTING never best.
- FIRST_MATCH OSR is 0.038–0.579; its high nominal Hayes-Roth BA depends on client order
  (C = 5 order-mean BA 0.735 vs nominal 0.833).

## 20. Dataset-specific conclusions

- **Hayes-Roth**: only dataset with reduct variation; non-monotonic conflict; FIRST_MATCH wins nominally
  but with the largest order risk; 26 test objects make differences coarse.
- **Car Evaluation**: fully stable reducts with rising `H_rule` and conflict; GLOBAL_STRENGTH leads on
  BA; accuracy overstates performance relative to BA (class imbalance).
- **Balance Scale**: stable reducts, highest `H_rule`, conflict rising while `H_rule` falls;
  STANDARD_VOTING leads for C ≤ 4, GLOBAL_STRENGTH at C = 5; FIRST_MATCH lowest BA at every C.

## 21. Cross-dataset conclusions

Common: full-attribute central reducts, high rule heterogeneity, inference ≫ exact-antecedent conflict,
shorter local rules and more matches per object as C grows, non-zero FIRST_MATCH order sensitivity.
Within these runs reduct heterogeneity is not necessary for rule heterogeneity or conflict; `H_rule` is
present wherever conflict is but tracks its C-trajectory only in Car; resolver quality is
dataset-dependent. Details and labels: `06_EMPIRICAL_ANALYSIS.md`.

## 22. Limitations

`07_LIMITATIONS.md`: 3 datasets; one holdout split; seed 42; 4/6/4 attributes; exhaustive reduct
search not evidence of scalability; RI / `H_rule` / conflict diagnostics are derived research metrics;
partitioned-data simulation, not a distributed-systems benchmark; local certainty ≠ pooled certainty;
no collaborative resolver; legacy `federated.run_federated` (not on the production path) keeps the
provenance-scoped aggregation; `paper.py` keeps the V6.1 reduct search; no universal causal claim.

## 23. What can be claimed (SUPPORTED CLAIMS)

Directly supported by source, tests and results:

- The main pipeline selects the central reduct on training data only, and each federated client
  selects its own local reduct on its own training partition, independently.
- LEM2 receives only the selected reduct features (central and local).
- Reduct selection uses exact integer positive-region equality and includes the empty reduct.
- Local LEM2 rules are locally certain; the UNION is not treated as pooled-certain.
- The four resolvers evaluate one identical structural artifact; resolver choice does not alter
  reducts, rules, provenance, supports or the conflict workload (conflict case identities).
- For a fixed global rule set, distributed support equals pooled support, and distributed
  STANDARD_VOTING and GLOBAL_STRENGTH scores and predictions equal the pooled calculation.
- GLOBAL_STRENGTH counts each covered training object once.
- In these benchmark runs, rule heterogeneity and inference conflict occur with zero reduct instability.
- No single baseline resolver dominates all tested configurations.
- FIRST_MATCH and SIMPLE_VOTING results are unchanged by the audit; prior STANDARD_VOTING and
  GLOBAL_STRENGTH federated results are superseded.

## 24. What cannot be claimed (NOT SUPPORTED / NOT YET PROVEN)

- Client count universally increases conflict (Hayes-Roth is non-monotonic; one split, one seed).
- Reduct instability causes conflict.
- Rule heterogeneity causes conflict (and `H_rule` runs opposite to conflict in Balance).
- Any resolver is universally optimal, or the corrected STANDARD/GLOBAL resolvers are "better".
- The results generalise to other datasets, larger enterprise data, label-skewed partitions or other seeds.
- Exhaustive minimum-cardinality reduct search scales to high-dimensional data.
- `R_G` is a globally certain rule set or equals `LEM2(U_train)`.

## 25. Final freeze decision

Freeze the mathematical baseline at the commit on `audit/final-math-freeze-20261015` that contains
this report, once reviewed and merged. Report STANDARD_VOTING and GLOBAL_STRENGTH federated results
only from `UCI3_HOLDOUT42_FINAL` (or later runs of this code); FIRST_MATCH and SIMPLE_VOTING results
from either run are identical. No collaborative resolver is part of the frozen baseline.

Notes on the flags below. `MATH_CORE_CHANGED = YES` because the reduct **selection** criterion in
`reduct.py` changed (search from `|R| = 0`, integer `POS` equality), as required by audit sections 6–7;
the Rough Set primitives (IND, lower approximation, `|POS|`, `γ`) are unchanged and AST-identical to
V6.1, and UCI3 reducts are unchanged. `LEM2_CORE_CHANGED = NO`: `core.py` is byte-identical; the
empty-reduct case is dispatched before LEM2 in `pipeline.py`, and for every non-empty attribute set
the frozen LEM2 runs unchanged.

```text
EMPTY_REDUCT_SEMANTICS=PASS
EXACT_REDUCT_PRESERVATION=PASS
STANDARD_SUPPORT_SCOPE=PASS
GLOBAL_STRENGTH_SUPPORT_SCOPE=PASS
GLOBAL_STRENGTH_NO_DOUBLE_COUNT=PASS
DISTRIBUTED_POOLED_EQUIVALENCE=PASS
FIRST_MATCH_UNCHANGED=PASS
SIMPLE_VOTING_UNCHANGED=PASS
STRUCTURAL_ARTIFACT_IDENTITY=PASS
CONFLICT_WORKLOAD_IDENTITY=PASS
ROUGH_SET_CORE_MATH=PASS
LEM2_CORE_MATH=PASS
TRAIN_ONLY_REDUCT=PASS
LOCAL_REDUCT_PER_CLIENT=PASS
POLICY_STRUCTURE_IDENTITY=PASS
UCI3_RERUN=PASS
MATH_CORE_CHANGED=YES
LEM2_CORE_CHANGED=NO
PAPER_REPLICATION_CHANGED=NO
OLD_STANDARD_RESULTS_SUPERSEDED=YES
OLD_GLOBAL_STRENGTH_RESULTS_SUPERSEDED=YES
FINAL_MATHEMATICAL_FREEZE=PASS
```
