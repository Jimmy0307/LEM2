# Team Discussion Index

Use these documents as the current canonical discussion set:

1. `FINAL_TEACHER_HANDOFF.md` — final teacher-facing entry point: scope, research flow, software path, verification boundary, and remaining publication work.
2. `TEAM_DISCUSSION_PREDICTION_POLICIES_AND_CONFLICT.md` — four Prediction Policies and conflict definitions.
3. `TEAM_EVALUATION_METRICS_ESTABLISHED.md` — established evaluation metrics only, with formulas, meanings, code mappings, and citations.
4. `CONFLICT_RESOLUTION_NOTES.md` — cited mathematical explanation of conflict → Prediction Policy → single decision.
5. `LITERATURE_REFERENCE_INDEX.md` — literature provenance and citation/adaptation boundaries.
6. `README.md` — compact Literature × Mathematics × Code mapping.
7. `reference/policies/` — four separated teaching/reference Python implementations for instructor review.

Terminology note: the four compared methods are `Prediction Policies`; `Conflict Resolution` describes what they do on conflict cases.

Evaluation note: `CRA / CCR / OSR / H_rule` are no longer primary research metrics. Formal evaluation uses established measures; legacy fields remain only for compatibility or supplementary diagnostics.

Software note: `run.bat` remains the Windows all-policy entry point. It calls `main.py --all-policies`; `roughset.batch.run_policy_matrix()` now emits established Variation Ratio outputs in the combined batch summary. `run_single.bat` remains available for the single policy configured in `config.json`.

Verification note: GitHub Actions verifies the Python call chain with Python 3.12, `compileall`, and the full pytest suite, including batch-output integration and separated-policy parity tests. A Linux CI run does not substitute for a native Windows double-click `.bat` smoke test.
