# Reduct Pipeline Audit

Audit date: 2026-10-14  
Scope: current `RoughSet_Software_V1_ENV_READY_UCI3_ALL_POLICIES` package before implementation changes.

## Findings

### Reduct is implemented, but is outside the ordinary experiment pipeline

`roughset/reduct.py` contains `dependency_degree()` and exhaustive `find_minimum_cardinality_reducts()`; `find_minimal_reducts` is only a backward-compatible alias. The normal application module does not import either function. The production call site is `roughset/paper.py:42`, in `run_paper_protocol()`. The package exports both names from `roughset/__init__.py`, and `tests/test_reduct.py` tests the mathematical result.

The paper protocol deliberately computes a reduct from its complete input table before iterating over folds (`roughset/paper.py:27-51`). Its docstring calls this a historical replication lane. That behavior is distinct from the normal leakage-free experiment path and must not be used as the template for the revised main pipeline.

### Centralized currently induces LEM2 over every preprocessed condition column

In `roughset/app.py:154-160`, `_run_split()` assigns all preprocessor `condition_columns` and passes that full list to `run_centralized()`. In `roughset/evaluation.py:425-445`, `run_centralized()` passes the supplied list directly to `induce_lem2()`. Thus the current path is:

`split train -> fit preprocessing -> all condition columns -> induce_lem2(train)`

There is no train-only reduct calculation in this path.

### Federated currently induces every client's LEM2 rules over the same full feature list

In `roughset/app.py:133-151`, clients are partitioned from `raw_train`; preprocessing is fitted using the training-side source and then applied to each client. At `roughset/app.py:167-174`, the same complete `condition_columns` list is passed to `run_federated()`.

In `roughset/federated.py:406-446`, `run_federated()` iterates over clients and calls `induce_lem2(client_df, condition_cols=condition_columns, ...)` for each one. Each client has its own local table and rules, but does not calculate or use a local reduct. `roughset/federated.py:485` then unions the local rules with provenance.

### Prediction policies are resolver behavior after rule induction; batch currently rebuilds structure per policy

`roughset/evaluation.py:42-103` implements the four policy resolvers in `predict_with_policy()`. Centralized rules are induced first in `run_centralized()` and then evaluated with the requested policy (`evaluation.py:425-480`). Federated local rules and the global UNION are constructed before the requested policy is used for global inference (`federated.py:406-485`, then `542-565`).

However, `roughset/batch.py:64-68` loops over policies and calls `run_application()` once per policy. `main.py:23,33` selects that runner for `--all-policies`, and `run.bat:43` invokes it. Therefore policy is downstream of induction inside each individual run, while an all-policy batch repeats preprocessing, partitioning, induction, UNION, and structural diagnostics for each policy. `run_single.bat:43` runs the one configured policy.

## Requested facts: expected versus actual

| Check | Expected for revised main pipeline | Actual before changes |
|---|---|---|
| Reduct use | Central and each local client calculate reducts from their own training table | Reduct search is only wired into the historical paper protocol lane |
| Central LEM2 inputs | Selected central reduct | All preprocessed condition columns |
| Federated LEM2 inputs | A separately selected local reduct per client | The same all-feature column list is passed to every client |
| Policy timing | Same built rule system evaluated by each resolver | Within one run policy affects inference after rules exist; batch repeats the entire run for each policy |
| Leakage control | Reduct recalculated from each split's train rows | No main-pipeline reduct exists yet; paper replication intentionally selects from its full table before folds |

## Relevant module responsibilities

- `roughset/core.py`: `Rule`, rule identity (`Rule.key`), and LEM2/Rough Set operations. Existing AST parity coverage in `tests/test_reference_ast_parity.py` freezes the canonical math implementation.
- `roughset/reduct.py`: positive-region size, dependency degree, and exhaustive minimum-cardinality reduct search.
- `roughset/federated.py`: client partitioning, client-local induction, UNION/provenance, and federated diagnostics. It currently receives feature columns from the caller.
- `roughset/evaluation.py`: prediction resolvers, metrics, rule similarity/conflict audits, and centralized induction wrapper.
- `roughset/app.py`: dataset discovery, splitting, preprocessing, centralized/federated orchestration, CV and client sweep, and existing CSV/JSON outputs.
- `roughset/paper.py`: separate Wang-style historical replication lane, including its full-data reduct selection.
- `roughset/batch.py`: all-policy loop; currently invokes the full application separately for each policy.
- `main.py`: dispatches single-policy or all-policy execution.
- `config.json`: currently has experiment/evaluation/preprocessing/federated/paper/report/batch sections; no `reduct` section.
- `run.bat`: invokes `main.py --all-policies`; `run_single.bat` invokes `main.py` without that flag.
- `tests/`: current coverage includes reduct hand calculation, paper lane, core AST parity and reference behavior, evaluation policies/conflicts, federated partition/UNION/order behavior, app outputs, and per-policy batch execution. It does not currently assert main-pipeline reduct use, local reduct heterogeneity, leakage spies, policy structural reuse, or the requested expanded report metrics.

## Minimal correction boundary

Keep `roughset/core.py` and the existing reduct mathematics unchanged. Add a train-scoped structural-build seam in the application/federated orchestration that records all minimum candidates and selects a canonical candidate, pass only the selected reduct to each corresponding LEM2 call, and return a reusable structural artifact. Move policy comparison to an evaluation phase over that artifact. Extend output/reporting and add tests at those seams. Preserve the historical paper protocol as a separately labeled replication lane; do not silently change its protocol.

## Repository/worktree note

The package directory has no local `.git` root. `git rev-parse --show-toplevel` resolves to `C:/Users/user`, whose status includes unrelated home-directory content. Do not use that status as a package change list; keep edits confined to the requested package paths.
