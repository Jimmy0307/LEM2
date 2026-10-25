# Professor-Question Closure Status — 2026-10-23

## Scope closed in this update

The research branch now answers the professor's previous questions through code-generated evidence rather than manual slide transcription.

### Added diagnostics

- Target Candidate Coverage by class and macro average.
- Candidate-generation / coverage failure vs candidate-ranking / conflict error separation.
- Standard → Population Standard transition decomposition.
- GlobalStrength → Population Global transition decomposition.
- Per-transition `T_d`, `U_d`, `P_d`, redundancy, winner change, and truth status.
- Project-defined Redundancy Asymmetry diagnostic:
  `A(x) = R_competitor - R_true`, with `R_d = 1 - P_d`.

### Teacher-facing canonical exports

Stored under `evidence/20261023/teacher/`:

1. `TEACHER_DATASET_METADATA.csv`
2. `TEACHER_SIX_POLICY_METRICS.csv`
3. `TEACHER_COVERAGE_BY_CLASS.csv`
4. `TEACHER_TARGET_1_TO_5.csv`
5. `TEACHER_STANDARD_TRANSITIONS.csv`
6. `TEACHER_GLOBAL_TRANSITIONS.csv`
7. `TEACHER_ERROR_DECOMPOSITION.csv`
8. `TEACHER_REDUNDANCY_ASYMMETRY.csv`
9. `TARGET_BACKTRACE_MANIFEST.json`
10. `PROVENANCE.txt`

### Refreshed evidence

- 3 UCI datasets.
- 80/20 holdout; final 20% is prediction/evaluation only.
- `C ∈ {2,3,4,5}`.
- six prediction methods.
- 72 policy-result rows.
- 15 selected target backtraces.
- 908 prediction-time conflict occurrences.
- 45 conflict occurrences have no true-class candidate rule.
- Population Standard changes 16 winners: 6 corrected, 9 harmed, 1 changed with the same correctness.
- Population Global changes 27 winners: 10 corrected, 13 harmed, 4 changed with the same correctness.
- all 43 changed winners move to a lower-redundancy decision.

### Important coverage result

Ordinary Target Coverage and Target Candidate Coverage are not interchangeable.

Example: Balance Scale C=2

- target-any-rule macro coverage: 93.2%
- true-target candidate macro coverage: 57.5%

Balance class B has 0% candidate coverage at C=2 and C=3 despite ordinary target coverage of 90% and 100%. This is a candidate-generation / induction issue, not something a voting policy can fix.

## Verification

The implementation was developed with a real RED → GREEN test sequence.

Final implementation verification before generated presentation commits:

```text
python -m compileall -q roughset main.py tools/target_case_backtrace.py
python -m pytest -q
118 passed in 10.32s
```

Refreshed `Target Case Population Backtrace` workflow: SUCCESS.

Professor-question presentation build workflow: SUCCESS.

The presentation build validates a 23-slide PPTX and exports a PDF for mobile viewing.

## Presentation

Canonical professor-question deck:

- `presentation/Federated_LEM2_Teacher_Questions_Complete_20261023.pptx`
- `presentation/Federated_LEM2_Teacher_Questions_Complete_20261023.pdf`

Generator:

- `tools/build_teacher_question_deck.py`

The older `Federated_LEM2_Final_Research_Update_20261023.*` remains as the research-mechanism version; the new teacher-question deck should be used when answering the professor's previous checklist.

## Repository boundary

- Production `main` remains frozen at `31b078bb78c6754d04c56a2e1cc849c8feb221d7`.
- Research work remains on `research/conflict-client-sweep-20261020`.
- PR #5 remains Draft / Open / Not merged.
- No seventh prediction policy was added.
