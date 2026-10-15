# Final mathematical audit + rerun + empirical analysis prompt

Use this prompt only after the canonical source tree from `RoughSet_Software_V1_ENV_READY_UCI3_ALL_POLICIES` has been imported into this repository.

---

You are to perform a complete **MATHEMATICAL AUDIT + REGRESSION VERIFICATION + UCI3 RE-RUN + EMPIRICAL ANALYSIS + FINAL FREEZE REPORT** for the current RoughSet / Federated LEM2 **non-collaborative baseline**.

This is not a request to add a Collaborative Resolver, redesign the method, or optimize results. Preserve the current research question and stop rather than forcing a PASS if the existing mathematics do not support it.

## 0. Scope

Pipeline under audit:

`Data → Train/Test split → preprocessing → central/local reduct → LEM2 → local rules → UNION → structural diagnostics → pre-resolution conflict → four existing resolvers → performance`

Resolvers:

- `FIRST_MATCH`
- `SIMPLE_VOTING`
- `STANDARD_VOTING`
- `GLOBAL_STRENGTH`

## 1. Create durable audit directories first

Before analysis, create:

`docs/final_math_audit_20261015/`

with:

1. `01_BASELINE_STATE.md`
2. `02_MATHEMATICAL_DEFINITIONS.md`
3. `03_IMPLEMENTATION_AUDIT.md`
4. `04_TEST_EVIDENCE.md`
5. `05_UCI3_RESULTS.md`
6. `06_EMPIRICAL_ANALYSIS.md`
7. `07_LIMITATIONS.md`
8. `08_FINAL_FREEZE_REPORT.md`

Also create:

`outputs/final_math_audit_20261015/`

Every phase must write its evidence to disk before the final chat response.

## 2. Baseline snapshot

Record:

- Python version
- package versions
- config
- timestamp
- SHA-256 of relevant source files
- SHA-256 of relevant tests

At minimum hash:

- `roughset/core.py`
- `roughset/reduct.py`
- `roughset/pipeline.py`
- `roughset/artifacts.py`
- `roughset/evaluation.py`
- `roughset/federated.py`
- `roughset/app.py`
- `roughset/batch.py`
- `roughset/paper.py`
- `config.json`

Treat `outputs/batch_runs/20261014_162216` as `PRE_AUDIT_REFERENCE_RUN` when present. Do not modify or overwrite it.

## 3. Baseline tests

Before modifying code run:

```bash
pytest -q
python -m compileall -q roughset main.py
```

Also run existing core-math, reduct, LEM2, paper-historical, and pipeline tests. Record test count, pass/fail, runtime and exit code in `04_TEST_EVIDENCE.md`.

If baseline already fails, stop and report the pre-existing failure.

## 4. Write the mathematical contract first

In `02_MATHEMATICAL_DEFINITIONS.md`, formally write the exact mathematics used by the project.

### 4.1 Indiscernibility

For `B ⊆ C`:

`x IND(B) y iff ∀a∈B, a(x)=a(y)`.

### 4.2 Lower approximation

`B_lower(X) = ∪{[x]_B : [x]_B ⊆ X}`.

### 4.3 Positive region

`POS_B(D) = ∪_{X∈U/D} B_lower(X)`.

### 4.4 Dependency

`γ_B(D) = |POS_B(D)| / |U|`.

### 4.5 Minimum-cardinality reduct

For `R ⊆ C`, require:

`|POS_R(D)| = |POS_C(D)|`

and choose minimum `|R|`.

The preservation decision must be based on exact integer positive-region cardinality equality. Dependency floats may remain for reporting only.

### 4.6 Empty reduct

`R = ∅` must have explicit semantics. Under `IND(∅)`, the entire universe forms one equivalence class:

`U / IND(∅) = {U}`.

Reduct search must therefore include cardinality `0`.

### 4.7 LEM2 certainty

For client `c`, local certainty means:

`[T]_{U_c} ⊆ X_{d,c}`.

Local certainty does not imply pooled/global certainty.

### 4.8 Federated UNION

`R_G = ∪_c R_c` is an **aggregated set of locally certain rules**.

Do not describe it as a globally certain pooled LEM2 rule set, and do not equate it with `LEM2(∪_c U_c)`.

### 4.9 Pre-resolution conflict

For test object `x`:

`M(x) = {r∈R_G : r matches x}`.

A conflict occurs iff:

`|{Decision(r): r∈M(x)}| > 1`.

### 4.10 Reduct Jaccard

`J_R(i,j) = |R_i∩R_j| / |R_i∪R_j|`.

### 4.11 Reduct instability

`RI = 1 - mean pairwise J_R`.

### 4.12 Rule heterogeneity

Write the exact production definition. If currently used as:

`H_rule = 1 - mean pairwise full-rule Jaccard`,

state it explicitly.

### 4.13 Resolver formulas

Do not infer formulas from names. Read production code and write the exact implemented formulas for:

- FIRST_MATCH
- SIMPLE_VOTING
- STANDARD_VOTING
- GLOBAL_STRENGTH

## 5. Implementation audit

In `03_IMPLEMENTATION_AUDIT.md`, audit every mathematical component against the contract.

For each item record:

- EXPECTED
- ACTUAL CODE PATH
- ACTUAL FORMULA / LOGIC
- VERDICT

At minimum audit:

- IND
- lower approximation
- positive region
- dependency
- minimum-cardinality search
- empty reduct
- candidate normalization
- deterministic lexicographic selection
- LEM2 pair selection
- LEM2 certainty
- LEM2 complex minimization
- central train-only reduct
- local train-only reduct
- policy-independent structural artifact
- UNION semantics
- conflict detection
- four resolver formulas

## 6. Empty reduct tests

Add deterministic tests.

### E1 — single decision class

Example:

```text
a b D
0 0 Y
0 1 Y
1 0 Y
1 1 Y
```

Require:

- `γ_C(D)=1`
- `γ_∅(D)=1`
- selected reduct `()`
- minimum size `0`
- candidate count `1`

### E2 — full dependency zero

Construct a deterministic inconsistent table with:

- `γ_C(D)=0`
- `γ_∅(D)=0`

Under the current dependency-preserving minimum-cardinality definition, selected reduct must be `()`.

### E3 — unconditional certain rule

If `R=∅` and all decisions are `Y`, LEM2 must represent an empty-condition certain rule equivalent to:

`TRUE → Y`.

It must not crash.

### E4 — empty reduct + inconsistent decisions

If `R=∅`, `γ=0`, and all class lower approximations are empty, LEM2 must produce `0` certain rules and must not invent a rule.

## 7. Exact reduct preservation

Verify the production selector accepts a candidate iff:

`positive_region_size(candidate) == positive_region_size(full_conditions)`.

It must not depend on `np.isclose(gamma_candidate, gamma_full)`.

If the implementation still uses float tolerance, write a failing test first and make the smallest possible correction. Do not change the reporting formula for `dependency_degree()`.

## 8. STANDARD_VOTING support scope

First read the actual production formula.

If `STANDARD_VOTING` is support-weighted, define for global rule `r = Ante(r) → d`:

`Supp_c(r) = |{z∈U_c : z satisfies Ante(r) and D(z)=d}|`.

Then global support must be:

`Supp_G(r) = Σ_c Supp_c(r)` over **all clients**.

It must not be restricted to clients that induced the rule, because `r∉R_c` does not imply `Supp_c(r)=0`.

### Required toy test

Construct at least two clients such that:

- Client 1 induces `A=1 → Y`.
- Client 2 does not induce that rule.
- Client 2 still contains at least one training row `A=1, D=Y`.

Require:

- `r∉R_2`
- `Supp_2(r)>0`
- `Supp_G(r)=Supp_1(r)+Supp_2(r)`

Keep provenance separate:

`Provenance(r) = {c : client c induced r}`.

Provenance must not constrain support evaluation scope.

## 9. GLOBAL_STRENGTH mathematics

Read the actual production formula first.

If Global Strength is matching-rule class coverage, for test object `x` and decision `d` define:

`M_d(x) = {r∈R_G : r matches x and decision(r)=d}`.

Then verify:

`GS(d|x) = |{z∈U_train : D(z)=d and ∃r∈M_d(x), z satisfies Ante(r)}| / |{z∈U_train : D(z)=d}|`.

The numerator is a **union of covered training objects**, not the sum of supports of matching rules. A training object covered by multiple matching rules must count once.

## 10. Distributed Global Strength

Because client partitions are disjoint:

`U_train = ⊔_c U_c`.

Define:

`N_d(x) = Σ_c N_{c,d}(x)`

where:

`N_{c,d}(x) = |{z∈U_c : D(z)=d and ∃r∈M_d(x), z satisfies Ante(r)}|`.

And:

`ClassSize_d = Σ_c |{z∈U_c : D(z)=d}|`.

Then:

`GS(d|x) = N_d(x) / ClassSize_d`.

For a fixed global rule set, this distributed calculation must exactly equal direct pooled calculation.

## 11. Global Strength required tests

Add tests for:

- G1: distributed GS equals pooled GS
- G2: overlapping matching rules do not double count covered objects
- G3: non-producing clients still contribute covered objects
- G4: denominator equals pooled class size
- G5: fixed-rule distributed prediction equals pooled prediction

## 12. Hand-calculable toy evidence

Do not rely only on pytest PASS.

Create:

`outputs/final_math_audit_20261015/toy_math_crosscheck.csv`

and document it in `04_TEST_EVIDENCE.md`.

At minimum show:

- rule antecedent and decision
- Client 1/2/3 support
- global support
- one test object
- matching rules by decision
- covered object IDs/counts by client and decision
- distributed union count
- pooled union count
- class denominator
- final GS score
- final prediction

The example must be manually checkable.

## 13. Structural artifact invariance

All four resolvers must reuse the same:

- train/test split
- client partition
- central reduct
- local reducts
- central rules
- local rules
- global rules
- conflict case identities

Policy must not alter the structural artifact. STANDARD/GLOBAL support metadata belongs to that artifact.

## 14. Preserve these semantics

- `FIRST_MATCH` remains the order-sensitive baseline.
- If `SIMPLE_VOTING` currently means one matching rule = one vote, keep it unchanged.
- Do not modify `paper.py` Wang historical replication semantics.
- Do not add Collaborative Resolver behavior.

## 15. Full regression

After any necessary correction run:

```bash
pytest -q
python -m compileall -q roughset main.py
```

Also run explicit test groups for:

- core math
- LEM2
- reduct
- pipeline
- paper historical
- resolver semantics
- distributed/pooled equivalence

Write all results to `04_TEST_EVIDENCE.md`.

## 16. UCI3 complete rerun

Rerun:

- Hayes-Roth UCI 44
- Car Evaluation UCI 19
- Balance Scale UCI 12

Fixed settings:

- HOLDOUT
- seed `42`
- STRATIFIED
- client counts `2,3,4,5`
- `reduct.enabled=true`
- four existing resolvers

Write to:

`outputs/final_math_audit_20261015/UCI3_HOLDOUT42_FINAL/`

Do not overwrite the 2026-10-14 reference run.

## 17. Old-vs-new regression table

If `outputs/batch_runs/20261014_162216` exists, create:

`outputs/final_math_audit_20261015/old_vs_new.csv`

Compare for every `dataset × C × policy`:

- old/new accuracy and delta
- old/new balanced accuracy and delta
- old/new macro-F1 and delta
- old/new conflict balanced accuracy and delta
- old/new coverage and delta
- central reduct
- local reducts
- rule counts
- conflict rate

## 18. Expected regression behavior

- FIRST_MATCH must remain unchanged.
- SIMPLE_VOTING must remain unchanged.
- STANDARD_VOTING may change only if an actual support-scope bug is proven and fixed.
- GLOBAL_STRENGTH may change only if an actual mathematical coverage/scope bug is proven and fixed.

If FIRST_MATCH or SIMPLE_VOTING changes, STOP and investigate.

## 19. Full UCI result tables

In `05_UCI3_RESULTS.md`, report all `3 datasets × C=2,3,4,5`, not only C=5.

Structural fields must include at least:

- dataset
- C
- central reduct size
- mean local reduct size
- reduct instability
- mean local-central reduct Jaccard
- rule heterogeneity
- global rule count
- coverage
- pre-resolution conflict rate
- covered-conflict rate if implemented

Resolver fields must include at least:

- dataset
- C
- policy
- accuracy
- balanced accuracy
- macro-F1
- coverage
- conflict resolution accuracy
- conflict balanced accuracy
- conflict macro-F1
- disagreement vs FIRST_MATCH
- conflict disagreement vs FIRST_MATCH
- order sensitivity
- order BA mean/std/min/max

## 20. Empirical analysis rules

In `06_EMPIRICAL_ANALYSIS.md`, distinguish explicitly between:

- **OBSERVED**
- **INTERPRETATION**
- **NOT PROVEN**

Do not turn a single-seed holdout observation into a universal causal claim.

Analyze the research chain:

`Client partition → reduct/rule structural heterogeneity → inference conflict → resolver quality → prediction performance`.

## 21. Analysis A — reduct

Analyze:

- whether central reduct shrinks
- whether local reducts shrink
- how RI changes with C
- how local-central Jaccard changes with C

Explicitly examine Car Evaluation and Balance Scale for cases where `RI=0` while rule heterogeneity and conflict remain high.

If observed, it is acceptable to state only:

> Within these benchmark runs, reduct heterogeneity is not a necessary condition for rule heterogeneity or inference conflict.

Do not present that sentence as a universal theorem.

## 22. Analysis B — rule heterogeneity

Analyze C=2→5 trajectories of rule heterogeneity and compare them with RI and conflict.

Explicitly explain that identical selected feature subsets do not imply identical induced rule systems because local object distributions, decision distributions, lower approximations, and LEM2 induction can still differ.

## 23. Analysis C — client count

For each dataset, examine C=2,3,4,5 for:

- coverage
- rule heterogeneity
- conflict rate
- resolver performance

Do not assume `C↑ → conflict↑`. Test monotonicity from the observed numbers. If Hayes-Roth is non-monotonic, say so explicitly.

## 24. Analysis D — conflict

Compare exact antecedent conflict with inference conflict.

If inference conflict is much higher, explain that non-identical overlapping antecedents can still match the same test object and support different decisions.

Do not claim that only identical antecedents can produce conflict.

## 25. Analysis E — resolver comparison

For every dataset × C configuration identify the best resolver for:

- balanced accuracy
- conflict balanced accuracy
- macro-F1

Do not report only winners. Analyze whether one resolver dominates all tested configurations.

If not, state only the empirical observation:

> No single baseline resolver dominates across all tested dataset/client-count configurations.

## 26. Analysis F — FIRST_MATCH

Analyze nominal performance together with order sensitivity.

Where FIRST_MATCH has high accuracy but high OSR or a wide order BA range, explicitly distinguish prediction performance from order robustness.

## 27. Analysis G — STANDARD / GLOBAL

If the audit proves the old implementation was already mathematically correct, say so explicitly and explain why old/new UCI numbers do not change.

If a real bug is corrected, list every affected configuration and mark previous STANDARD/GLOBAL results as superseded.

## 28. Descriptive structural associations

Create:

`outputs/final_math_audit_20261015/structural_associations.csv`

Across the 12 structural observations (`dataset × C`), compute descriptive:

- client_count vs RI
- client_count vs rule heterogeneity
- client_count vs conflict
- RI vs rule heterogeneity
- rule heterogeneity vs conflict

Report Pearson and Spearman if appropriate, but label the analysis **exploratory descriptive association only** because n=12 is small. Also report per-dataset trajectories rather than relying only on pooled correlation.

## 29. Dataset-specific analysis

Write separate sections for:

- Hayes-Roth
- Car Evaluation
- Balance Scale

For each answer:

1. Is the reduct stable?
2. How large is rule heterogeneity?
3. How does conflict change with C?
4. Which resolver performs best under which C?
5. What is the FIRST_MATCH order risk?
6. Is there unusual/non-monotonic behavior?
7. What evidence does the dataset contribute to the proposed structural mechanism?

## 30. Cross-dataset synthesis

Summarize:

- observations common to all three datasets
- observations only present in some datasets
- whether reduct heterogeneity is necessary
- whether rule heterogeneity appears more directly aligned with conflict than reduct heterogeneity
- whether resolver quality depends on dataset/client count
- whether FIRST_MATCH shows an order-robustness tradeoff

Do not convert descriptive evidence into an unsupported causal theorem.

## 31. Limitations

In `07_LIMITATIONS.md`, include at least:

- 3 datasets only
- single HOLDOUT split
- seed=42
- small feature counts 4/6/4
- exhaustive minimum-cardinality reduct is feasible here but not evidence of scalability to high-dimensional data
- RI, rule heterogeneity, and conflict diagnostics are derived research metrics, not original Pawlak/LEM2 measures
- federated setup is a partitioned-data simulation, not a real distributed systems/network benchmark
- local certainty is not pooled/global certainty
- no collaborative resolver is part of this baseline
- no universal causal claim is supported from the current evidence

## 32. Final freeze report

Create:

`docs/final_math_audit_20261015/08_FINAL_FREEZE_REPORT.md`

It must contain:

1. Executive verdict
2. Exact mathematical definitions
3. Audit findings
4. Bugs found
5. Bugs fixed
6. Suspected bugs that were disproven
7. Files changed
8. Tests added
9. Final pytest result
10. compileall result
11. Empty reduct evidence
12. Exact POS equality evidence
13. Standard support-scope evidence
14. Global Strength no-double-count evidence
15. Distributed==pooled evidence
16. UCI3 rerun summary
17. Old-vs-new comparison
18. Structural findings
19. Resolver findings
20. Dataset-specific conclusions
21. Cross-dataset conclusions
22. Limitations
23. What can be claimed
24. What cannot be claimed
25. Final freeze decision

## 33. Claims section

The final report must separate:

### SUPPORTED CLAIMS

Only include claims directly supported by source/tests/results, such as when verified:

- main pipeline uses train-only reduct
- each federated client selects a local reduct independently
- LEM2 uses only selected reduct features
- four resolvers share the same structural artifact
- local certainty is not treated as pooled certainty
- policy does not alter the conflict workload
- distributed support equals pooled support for a fixed global rule set
- distributed Global Strength equals pooled calculation
- rule heterogeneity can occur with zero reduct instability in these benchmark runs
- no single baseline resolver dominates all tested configurations

### NOT SUPPORTED / NOT YET PROVEN

Examples:

- client count universally increases conflict
- reduct instability causes conflict
- rule heterogeneity causally causes conflict
- one resolver is universally optimal
- the results generalize to large enterprise datasets
- exhaustive reduct is scalable to high-dimensional datasets

## 34. Required final verdict block

End `08_FINAL_FREEZE_REPORT.md` with exactly these keys:

```text
EMPTY_REDUCT_SEMANTICS=PASS/FAIL
EXACT_REDUCT_PRESERVATION=PASS/FAIL
STANDARD_SUPPORT_SCOPE=PASS/FAIL
GLOBAL_STRENGTH_SUPPORT_SCOPE=PASS/FAIL
GLOBAL_STRENGTH_NO_DOUBLE_COUNT=PASS/FAIL
DISTRIBUTED_POOLED_EQUIVALENCE=PASS/FAIL
FIRST_MATCH_UNCHANGED=PASS/FAIL
SIMPLE_VOTING_UNCHANGED=PASS/FAIL
STRUCTURAL_ARTIFACT_IDENTITY=PASS/FAIL
CONFLICT_WORKLOAD_IDENTITY=PASS/FAIL
ROUGH_SET_CORE_MATH=PASS/FAIL
LEM2_CORE_MATH=PASS/FAIL
TRAIN_ONLY_REDUCT=PASS/FAIL
LOCAL_REDUCT_PER_CLIENT=PASS/FAIL
POLICY_STRUCTURE_IDENTITY=PASS/FAIL
UCI3_RERUN=PASS/FAIL
MATH_CORE_CHANGED=YES/NO
LEM2_CORE_CHANGED=YES/NO
PAPER_REPLICATION_CHANGED=YES/NO
OLD_STANDARD_RESULTS_SUPERSEDED=YES/NO
OLD_GLOBAL_STRENGTH_RESULTS_SUPERSEDED=YES/NO
FINAL_MATHEMATICAL_FREEZE=PASS/BLOCKED
```

## 35. Recovery copy and manifest

Copy the final report to:

`outputs/final_math_audit_20261015/FINAL_MATHEMATICAL_FREEZE_REPORT.md`

Create:

`outputs/final_math_audit_20261015/AUDIT_MANIFEST.sha256`

The manifest must hash at least:

- all eight audit markdown files
- `toy_math_crosscheck.csv`
- `old_vs_new.csv`
- `structural_associations.csv`
- final UCI3 summaries
- final freeze report

This evidence must remain recoverable even if the chat response is lost.

## 36. Final chat response

Only respond after all required disk files and the manifest exist.

The chat response must summarize:

- overall verdict
- actual mathematical issues found
- actual fixes made
- suspected issues disproven
- final pytest and compileall
- whether UCI3 results changed
- most important empirical findings
- exact output paths
- complete verdict block

## 37. Stop conditions

Stop rather than forcing PASS if any of the following occurs:

- a core Rough Set formula must change
- LEM2 induction semantics must change
- FIRST_MATCH results change
- SIMPLE_VOTING results change
- Wang historical replication changes
- train/test leakage appears
- policy changes the structural artifact
- fixed-rule distributed calculation cannot equal pooled calculation
- empty reduct support cannot be added without breaking existing semantics
- UCI dataset semantics change

On stop, write and report:

- EXPECTED
- ACTUAL
- ROOT_CAUSE
- MATHEMATICAL_IMPLICATION
- MINIMAL_NEXT_FIX

Do not change the research method merely to obtain a PASS.
