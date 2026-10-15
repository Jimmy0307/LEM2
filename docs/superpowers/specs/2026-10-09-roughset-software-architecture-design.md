# RoughSet Software Architecture Design

Date: 2026-10-09  
Baseline: `lem2_control_panel_v6_1_數學一致性修正版.py`

## 1. Goal

Convert the validated V6.1 single-file research script into a maintainable software package without changing the mathematics of the validated Rough Set / LEM2 core.

Primary usability target:

- normal use through `run.bat`
- user edits `config.json`, not a 3,000+ line Python file
- mathematical core isolated from dataset adapters and experiment orchestration
- existing V6.1 remains untouched as the reference implementation
- behavior must be regression-equivalent before the software package is considered valid

## 2. Chosen Architecture

```text
roughset_software/
├─ run.bat
├─ config.json
├─ main.py
├─ requirements.txt
├─ roughset/
│  ├─ __init__.py
│  ├─ core.py
│  ├─ adapters.py
│  ├─ federated.py
│  ├─ evaluation.py
│  └─ app.py
├─ tests/
│  ├─ test_math_core.py
│  ├─ test_adapters.py
│  ├─ test_federated.py
│  ├─ test_evaluation.py
│  ├─ test_architecture.py
│  └─ test_end_to_end.py
└─ docs/
   └─ superpowers/specs/
      └─ 2026-10-09-roughset-software-architecture-design.md
```

This is intentionally not a plugin framework. The package is split only by mathematical and engineering responsibility.

## 3. Frozen Mathematical Core

`roughset/core.py` is the protected mathematical layer. The following V6.1 definitions are moved with behavior preserved:

- `Rule`
- `equivalence_classes`
- `lower_approximation`
- `build_blocks`
- `complex_block`
- `choose_best_pair`
- `minimize_complex`
- `build_one_complex`
- `remove_redundant_complexes`
- `induce_lem2`
- `_positive_region_size`
- `dependency_degree`
- `find_minimal_reducts`

The software refactor must not change these mathematical contracts.

### 3.1 Lower approximation

\[
\underline{C}(X)=\bigcup\{[x]_C:[x]_C\subseteq X\}
\]

### 3.2 Positive region and dependency

\[
POS_C(D)=\bigcup_{X\in U/D}\underline{C}(X)
\]

\[
\gamma_C(D)=\frac{|POS_C(D)|}{|U|}
\]

### 3.3 Reduct criterion

For the current implementation, a returned minimum-cardinality reduct satisfies:

\[
R\subseteq C,\qquad \gamma_R(D)=\gamma_C(D)
\]

and the implementation searches increasing subset cardinality until the first valid cardinality is found.

### 3.4 LEM2 pair-selection contract

For target uncovered set `G`, select a condition pair `t` by:

\[
\max |[t]\cap G|
\]

with tie preference:

\[
\min |[t]|
\]

A completed certain complex must satisfy:

\[
\emptyset\neq[T]\subseteq B
\]

where `B` is the target lower approximation.

## 4. Module Responsibilities

### 4.1 `core.py`

Only mathematical Rough Set / LEM2 operations.

It must not:

- load UCI/CSV/Excel files
- split train/test data
- create federated clients
- calculate classification reports
- print reports
- read configuration files

### 4.2 `adapters.py`

Responsible for converting external data into a common decision-table representation.

Contains or owns the V6.1 responsibilities corresponding to:

- `prepare_uci_frame`
- `load_uci_dataset`
- `_prepare_custom_frame`
- `load_input`
- `_clean_column_name`
- `_clean_name_list`
- numeric/categorical feature detection
- shared discretization fitting/application

Common output interface:

```python
@dataclass
class DatasetBundle:
    name: str
    frame: pd.DataFrame
    features: list[str]
    target: str
```

Adapter rules:

1. It may clean and transform data according to explicit configuration.
2. It may not induce rules.
3. It may not select reducts.
4. It may not resolve rule conflicts.
5. Missing-data handling must remain explicit and fail-fast where V6.1 is fail-fast.

### 4.3 `federated.py`

Owns the federated experiment layer:

- `stratified_client_partition`
- `dirichlet_label_skew_partition`
- `partition_clients`
- `union_rules_with_provenance`
- `union_rules`
- client-count sweep
- rule-source provenance
- pairwise client rule similarity
- conflict audits
- order sensitivity
- order-distribution metrics
- federated training orchestration

Mathematical provenance contract:

\[
Sources(r)=\{c:r\in R_c\}
\]

A global rule must preserve all source clients that produced the same full rule key.

For Dirichlet label skew, for each decision class `k`:

\[
\mathbf p_k\sim Dirichlet(\alpha\mathbf 1_C)
\]

and class objects are allocated according to those proportions while preserving partition conservation:

\[
\bigcup_c U_c=U_{train}
\]

\[
U_i\cap U_j=\varnothing\quad (i\neq j)
\]

### 4.4 `evaluation.py`

Owns inference policies and evaluation metrics:

- `majority_class`
- `_rule_matches`
- `matching_rules`
- `_resolve_vote`
- `predict_with_policy`
- `fit_rule_weights`
- `fit_rule_support_sets`
- `aggregate_rule_support_context`
- `aggregate_rule_weights`
- `predict_table`
- `classification_accuracy`
- `balanced_accuracy`
- `macro_f1_score`
- `evaluate_rule_model`

Supported policies remain:

- `FIRST_MATCH`
- `SIMPLE_VOTING`
- `STANDARD_VOTING`
- `GLOBAL_STRENGTH`

No collaborative-filtering resolver is introduced during this refactor.

### 4.5 `app.py`

Thin orchestration and reporting layer.

Owns:

- `ControlPanel`
- configuration validation
- dataset loop
- holdout / K-fold orchestration
- centralized/federated module calls
- client sweep orchestration
- paper-protocol orchestration
- summary/report construction and printing

`app.py` may coordinate modules but must not reimplement mathematics from `core.py`.

### 4.6 `main.py`

Entry point only.

Expected flow:

```text
read config.json
→ construct ControlPanel
→ validate config
→ call app.run_and_report(...)
→ return process exit code
```

No mathematical or dataset logic belongs in `main.py`.

## 5. Configuration

`config.json` becomes the primary user-facing control surface.

Default structure:

```json
{
  "input_mode": "UCI_ALL",
  "run_centralized": true,
  "run_federated": true,
  "prediction_policy": "FIRST_MATCH",
  "evaluation_mode": "HOLDOUT",
  "test_ratio": 0.2,
  "seed": 42,
  "n_clients": 5,
  "run_client_sweep": true,
  "client_counts": [2, 3, 4, 5],
  "federated_partition": "STRATIFIED",
  "dirichlet_alpha": 0.5,
  "dirichlet_max_retries": 100,
  "n_bins": 3,
  "report_style": "BOTH",
  "show_rules": true,
  "show_rule_limit": 10
}
```

The refactor must map configuration keys to V6.1 semantics rather than invent new defaults silently.

## 6. Windows BAT Launcher

`run.bat` is designed for non-developer use.

Behavior:

1. resolve project directory from `%~dp0`
2. choose `.venv\Scripts\python.exe` if present
3. otherwise choose `py -3` or `python`
4. if `.venv` does not exist, create it
5. install/update requirements only when required by initial setup
6. execute `main.py --config config.json`
7. preserve non-zero exit codes
8. pause on error so Windows users can read the failure message

The BAT file must not contain algorithmic logic.

## 7. Migration Strategy

The refactor is migration-first, not rewrite-first.

1. Keep original V6.1 file untouched.
2. Create tests that import the original V6.1 implementation as reference behavior.
3. Move one responsibility at a time into package modules.
4. After each move, compare package behavior against V6.1 on deterministic fixtures.
5. Only remove duplicated package-local transitional code after equivalence is proven.

## 8. Required Regression Tests

### 8.1 Mathematical regression

The existing mathematical suite must remain green, including:

- lower approximation
- positive region/dependency
- exhaustive minimum-cardinality reduct comparison
- LEM2 certainty/minimality/coverage invariants
- Balanced Accuracy
- Macro F1
- Standard Voting
- Global Strength
- conflict metrics
- order sensitivity

### 8.2 Core parity

For deterministic fixtures, compare V6.1 and package outputs for:

- reduct candidates
- induced rule signatures
- rule decisions
- dependency degree
- lower approximation membership

Equivalent legal LEM2 tie outcomes are acceptable only where the same deterministic ordering is not preserved. The migration target is exact behavior where possible.

### 8.3 Federated parity

Compare V6.1 and package outputs for fixed seeds:

- client membership
- local rule sets
- global union rules
- rule-source provenance
- Jaccard metrics
- exact conflict groups
- conflict case rate
- order sensitivity
- order BA/CRA distribution

### 8.4 Partition conservation

For all supported partition modes:

\[
\sum_c|U_c|=|U_{train}|
\]

with no duplicated or missing training rows.

### 8.5 End-to-end parity

At least one deterministic small dataset must run through both:

```text
original V6.1
vs
software package
```

and compare final summary metrics.

## 9. Non-goals for This Refactor

This architecture refactor does not add:

- Collaborative Filtering conflict resolution
- PRISM
- RIPPER
- DRSA rule induction
- new reduct algorithms
- new mathematical definitions
- GUI
- web application

Those are follow-up features after architectural parity is proven.

## 10. Acceptance Criteria

The software package is acceptable only if all conditions hold:

1. original V6.1 remains unchanged
2. frozen mathematical functions retain validated behavior
3. package modules compile
4. existing math regression suite passes
5. new architecture/parity tests pass
6. `.py` and package execution produce equivalent deterministic outputs on reference fixtures
7. `run.bat` launches successfully from a Windows-style project directory
8. invalid configuration fails clearly rather than silently falling back
9. no adapter or orchestration layer duplicates LEM2 mathematics
10. normal users can operate the program through `config.json` + `run.bat`

## 11. Approved Real-Data / UCI Source Extension (2026-10-10)

The approved architecture is refined so the original Adapter responsibility is split into explicit source, schema, splitting, and preprocessing modules:

- `sources.py`: local-folder discovery, UCI source parsing, DOI→UCI ID resolution/cache
- `adapters.py`: raw file/UCI object → `DatasetBundle`
- `schema.py`: target + continuous/categorical/ordinal/ignore roles
- `splitting.py`: Holdout/K-Fold only
- `preprocessing.py`: training-only discretization and symbolic transformation

`real_data/local/` is batch-scanned by `run.bat`. Multiple files are independent datasets and get separate output folders.

`real_data/uci_sources.txt` accepts `uci_id:44`, `44`, `doi:10.24432/...`, or a plain `10.24432/...` DOI. DOI-only operation may require Internet on first resolution and is cached afterward.

Target safety rule: never infer target from column position. A target may be auto-selected only when exactly one normalized column is named `target`, `class`, `label`, or `decision`; otherwise a sidecar schema is required.

Continuous/categorical/ordinal/ignore roles are separated before splitting/preprocessing. Continuous bin boundaries are fitted on training data only and then applied to test data.
