# Conflict Concentration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible concentration/anatomy analysis over the existing 908 conflict occurrences, publish evidence on the research branch, and update the teacher-facing PPT without changing frozen LEM2 semantics.

**Architecture:** Add a focused `roughset.conflict_concentration` analysis module plus a thin CLI tool. The module consumes existing row-level conflict evidence, decision-level score evidence, and verified test-row metadata; CI runs tests, generates outputs under the research evidence tree, and commits those generated outputs back to the research branch. PPT updates consume only generated summaries.

**Tech Stack:** Python 3.12 standard library + existing project dependencies; pytest; GitHub Actions; PowerPoint post-processing outside the LEM2 core.

**Spec:** `docs/superpowers/specs/2026-10-25-conflict-concentration-design.md`

## Global Constraints
- Research branch only: `research/conflict-client-sweep-20261020`.
- Do not modify frozen `main` or LEM2 / reduct / UNION / six-policy mathematics.
- 908 means configuration-level conflict occurrences, not unique rows.
- Factor/value tables are within-conflict concentration only; do not infer causal risk.
- All six policy metrics must use the same pre-resolution conflict rows.

## Review Focus
- JSON-like `candidate_decisions` parsing must be stable for numeric-looking labels and strings.
- Duplicate `(dataset,C,fold,row_id)` records must not silently inflate configuration counts.
- Persistence must count distinct client counts, not raw duplicated rows.
- Missing/blank factor columns must not produce fake factor-value categories.
- Policy columns missing from malformed input must fail clearly rather than silently dropping a method.

---

### Task 1: Conflict concentration analysis primitives

**Files:**
- Create: `roughset/conflict_concentration.py`
- Create: `tests/test_conflict_concentration.py`

**Interfaces:**
- Consumes: iterable mappings representing conflict rows and metadata rows.
- Produces: `candidate_signature`, `summarize_configurations`, `summarize_true_classes`, `summarize_candidate_signatures`, `summarize_persistence`, `summarize_factor_values`, `summarize_policy_accuracy`, `summarize_transition_status`, `summarize_decision_scores`.

- [ ] **Step 1: Write failing tests** for signature normalization, configuration reconciliation, persistence 1–4, factor omission, and six-policy conflict accuracy.
- [ ] **Step 2: Run tests and verify RED** because `roughset.conflict_concentration` does not yet exist.
- [ ] **Step 3: Implement minimal analysis functions** with deterministic sorting and explicit input validation.
- [ ] **Step 4: Run focused tests and full pytest suite; verify GREEN.**
- [ ] **Step 5: Commit.**

### Task 2: Evidence generator and CI publication

**Files:**
- Create: `tools/analyze_conflict_concentration.py`
- Create: `.github/workflows/conflict-concentration.yml`
- Generate: `docs/research/conflict_client_sweep_20261020/evidence/20261025/conflict_concentration/*`

**Interfaces:**
- Consumes: `ALL_CONFLICT_CASES.csv`, `ALL_CONFLICT_DECISION_SCORES.csv`, `teacher/TEACHER_DATASET_METADATA.csv`.
- Produces: eight CSV evidence files, `CONFLICT_PPT_SUMMARY.json`, and `CONFLICT_CONCENTRATION_REPORT.md`.

- [ ] **Step 1: Add CLI integration test** using temporary CSVs; verify it fails before the tool exists.
- [ ] **Step 2: Implement the CLI** and report renderer.
- [ ] **Step 3: Add workflow** that runs compile + pytest + generator, validates 908/config totals, and commits generated evidence only when changed.
- [ ] **Step 4: Push trigger and verify GitHub Actions run is green.**
- [ ] **Step 5: Read back generated evidence and reconcile headline totals.**

### Task 3: Teacher-facing presentation update

**Files:**
- Modify locally from: `LEM2_Teacher_TargetConflict_Intuitive_20261025_ConflictCause_MethodIssues.pptx`
- Publish branch artifact under: `docs/research/conflict_client_sweep_20261020/presentation/`

**Interfaces:**
- Consumes: generated `CONFLICT_PPT_SUMMARY.json` plus small concentration CSVs.
- Produces: updated deck with concentration/anatomy slides and conflict-only policy comparison.

- [ ] **Step 1: Add slide(s)** after the conflict-definition/cause section: configuration heat table, persistence/candidate concentration, and conflict-only policy comparison.
- [ ] **Step 2: Keep language bounded to evidence** and mark factor findings as within-conflict concentration.
- [ ] **Step 3: Render and inspect changed slides; run PowerPoint overflow/structure checks.**
- [ ] **Step 4: Publish updated PPTX to the research branch and verify readback identity.**

### Task 4: Final verification

- [ ] **Step 1:** Verify PR branch head, generated evidence paths, and PPT artifact are all present.
- [ ] **Step 2:** Verify test/CI status with fresh GitHub check output.
- [ ] **Step 3:** Self-review diff against the design because no independent subagent tool is available in this harness.
