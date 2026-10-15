# RoughSet Software Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the validated V6.1 monolithic script into a Windows-runnable software bundle with isolated Rough Set/LEM2 core, reduct search, adapters, federated logic, evaluation, and app orchestration while preserving validated behavior.

**Architecture:** Migration-first refactor. The original V6.1 file remains the behavioral reference and is never edited. Mathematical primitives/LEM2 move into `core.py`; reduct search is deliberately isolated in `reduct.py`; I/O/preprocessing, federated experiments, evaluation, and orchestration live in separate modules. `run.bat` + `config.json` form the normal user interface.

**Tech Stack:** Python 3, pandas, numpy, scikit-learn where already required by V6.1, ucimlrepo where already required, pytest, Windows BAT.

**Spec:** `docs/superpowers/specs/2026-10-09-roughset-software-architecture-design.md`

## Global Constraints

- Preserve `/mnt/data/lem2_control_panel_v6_1_數學一致性修正版.py` unchanged as canonical behavioral reference.
- Do not change the mathematics of equivalence classes, lower approximation, positive region/dependency, or LEM2.
- Approved refinement after code-vs-math review: reduct search is separated into `roughset/reduct.py` instead of being permanently coupled to `core.py`.
- `Rule.key` remains `(sorted conditions, decision)` so conflicting consequents are not de-duplicated away.
- Adapters may transform data but may not induce rules, search reducts, resolve conflicts, or implement LEM2.
- `federated.py` may orchestrate clients, aggregation, provenance, conflict audits, order effects, and non-IID partitions but may not duplicate LEM2 mathematics.
- No Collaborative Filtering resolver, PRISM, RIPPER, DRSA rule induction, GUI, or web app in this refactor.
- Use TDD: each behavior-changing extraction starts with a failing parity/regression test.

## Review Focus

1. **LEM2 tie behavior:** extraction must preserve the current deterministic final lexical tie-break so rule signatures do not drift accidentally.
2. **Index identity:** split/partition/provenance code must preserve row identity; no silent reindexing that changes support sets.
3. **Missing data:** adapter behavior must match V6.1 fail-fast/drop-target behavior exactly for equivalent modes.
4. **Dirichlet edge cases:** empty clients must follow the existing retry/failure semantics; never silently move rows.
5. **Windows launch paths:** `run.bat` must work from a directory containing spaces/non-ASCII names and preserve non-zero exit codes.

---

### Task 1: Freeze the Reference and Extract Mathematical Core + Reduct

**Files:**
- Create: `roughset/__init__.py`
- Create: `roughset/core.py`
- Create: `roughset/reduct.py`
- Test: `tests/test_math_core.py`
- Test: `tests/test_reduct.py`

**Interfaces:**
- `core.py`: `Rule`, `equivalence_classes`, `lower_approximation`, `build_blocks`, `complex_block`, `choose_best_pair`, `minimize_complex`, `build_one_complex`, `remove_redundant_complexes`, `induce_lem2`.
- `reduct.py`: `_positive_region_size`, `dependency_degree`, `find_minimum_cardinality_reducts`.
- Backward-compatible alias: `find_minimal_reducts = find_minimum_cardinality_reducts`.

- [ ] Write failing parity tests against original V6.1.
- [ ] Verify RED.
- [ ] Extract frozen LEM2 definitions without redesign.
- [ ] Extract positive-region/dependency/reduct search.
- [ ] Verify GREEN.

### Task 2: Extract Evaluation and Conflict Metrics

**Files:**
- Create: `roughset/evaluation.py`
- Test: `tests/test_evaluation.py`

**Interfaces:** FIRST_MATCH, SIMPLE_VOTING, STANDARD_VOTING, GLOBAL_STRENGTH, classification metrics, Jaccard, conflict metrics.

- [ ] Write failing parity tests for all policies/metrics.
- [ ] Verify RED.
- [ ] Extract without algorithmic changes.
- [ ] Verify GREEN.

### Task 3: Extract Data Adapters and Preprocessing

**Files:**
- Create: `roughset/adapters.py`
- Test: `tests/test_adapters.py`

**Interfaces:** `DatasetBundle`, CSV/DataFrame/UCI loading, feature detection, discretization, split helpers.

- [ ] Write failing parity tests for loading, missing-data policy, train-only discretization, and non-ASCII paths.
- [ ] Verify RED.
- [ ] Extract adapter/preprocessing behavior.
- [ ] Verify GREEN.

### Task 4: Extract Federated Layer

**Files:**
- Create: `roughset/federated.py`
- Test: `tests/test_federated.py`

**Interfaces:** client partitioning, Dirichlet non-IID, UNION/provenance, order sensitivity/distribution, federated run.

- [ ] Write failing parity/property tests for membership, conservation, provenance, ordering, order metrics, and empty-client behavior.
- [ ] Verify RED.
- [ ] Extract federated behavior.
- [ ] Verify GREEN.

### Task 5: Thin App + Config + BAT + End-to-End Parity

**Files:**
- Create: `roughset/app.py`
- Create: `main.py`
- Create: `config.json`
- Create: `run.bat`
- Create: `requirements.txt`
- Create: `README.md`
- Test: `tests/test_architecture.py`
- Test: `tests/test_end_to_end.py`

- [ ] Write failing architecture and end-to-end parity tests.
- [ ] Verify RED.
- [ ] Implement app/config/main/BAT.
- [ ] Run full `pytest -q`.
- [ ] Run `python -m compileall -q roughset main.py`.
- [ ] Run local deterministic smoke test.
- [ ] Verify original V6.1 SHA-256 unchanged.
- [ ] Build final ZIP excluding `.venv`, caches, and generated outputs.

## Final Acceptance

- Full pytest suite: 0 failures.
- `compileall`: exit 0.
- Frozen core parity: PASS.
- Reduct hand-calculation fixture: PASS.
- Evaluation parity: PASS.
- Federated partition/provenance/order parity: PASS.
- End-to-end reference-vs-package parity: PASS.
- Original V6.1 SHA-256 unchanged.
- ZIP contents audited.

## Approved Extension Added During Execution

User-approved requirements added before implementation completion:

- batch `real_data/local/` ingestion
- optional `real_data/schemas/<stem>.schema.json`
- `real_data/uci_sources.txt` supporting UCI ID and DOI
- DOI resolver with local cache and explicit offline failure
- explicit separation of `sources.py`, `schema.py`, `splitting.py`, and `preprocessing.py`
- safe target resolution; never assume last column
- Windows `run.bat` as the normal entry point
