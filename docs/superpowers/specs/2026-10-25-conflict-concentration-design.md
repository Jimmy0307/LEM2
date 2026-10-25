# Conflict Concentration / Anatomy Design

## Intent
Turn the existing 908 prediction-time conflict occurrences into a reproducible concentration analysis that answers **where conflicts concentrate, which objects persist across client counts, which candidate-decision combinations dominate, and how the six prediction policies perform on the same conflict subset**.

## Why
The current evidence layer already stores row-level conflict cases and decision-level scores, but the presentation mostly aggregates them to a single workload count. The missing layer is therefore analysis, not a new LEM2 algorithm.

## Goals
- Reuse existing `ALL_CONFLICT_CASES.csv`, `ALL_CONFLICT_DECISION_SCORES.csv`, and teacher dataset metadata.
- Quantify concentration by dataset × client count, true class, candidate signature, persistent row, factor/value, and prediction policy.
- Preserve the distinction between conflict occurrence and unique object.
- Report factor/value results only as **within-conflict concentration**, not causal risk.
- Keep all six policies on the same pre-resolution conflict set.
- Generate machine-readable CSV evidence plus a teacher-facing Markdown report and PPT summary JSON.

## Non-goals
- No change to LEM2 induction, reduct, UNION, support construction, or any prediction-policy formula.
- No merge to `main`.
- No claim that client count causes conflict monotonically.
- No class-normalized true-class conflict rate unless a verified class denominator is available.

## Approaches considered
1. **Re-run the full LEM2 experiment and instrument every layer.** Rejected: unnecessary for the requested question because the 908 cases are already persisted.
2. **Analyze the existing row-level and decision-level evidence. Chosen.** Lowest risk, reproducible, and preserves frozen experiment semantics.
3. **Ad-hoc notebook/manual pivoting.** Rejected: fast but not durable enough for teacher review or later repeated-seed work.

## Analysis outputs
- `CONFLICT_CONFIGURATION.csv`: dataset × C counts, rates, shares, matching-rule and candidate-set size, true-candidate-missing, PS/PG change counts.
- `CONFLICT_TRUE_CLASS.csv`: conflict counts/shares by true class within each configuration.
- `CONFLICT_CANDIDATE_SIGNATURE.csv`: candidate decision combinations and their concentration.
- `CONFLICT_PERSISTENCE.csv`: unique test rows across C=2..5 with persistence 1–4 and labels SINGLE / REPEATED / PERSISTENT.
- `CONFLICT_FACTOR_VALUE.csv`: factor/value frequencies within conflict cases only.
- `CONFLICT_POLICY_ACCURACY.csv`: conflict-only accuracy for all six policies.
- `CONFLICT_TRANSITION_STATUS.csv`: PS and PG corrected / harmed / unchanged counts.
- `CONFLICT_DECISION_SCORE_SUMMARY.csv`: aggregate decision-level redundancy/support diagnostics split by true vs competing decision.
- `CONFLICT_PPT_SUMMARY.json`: compact values for deck generation.
- `CONFLICT_CONCENTRATION_REPORT.md`: narrative findings with explicit limitations.

## Core definitions
- Conflict occurrence key: `(dataset, client_count, fold, row_id)`.
- Unique object key: `(dataset, fold, row_id)`.
- Candidate signature: sorted distinct candidate decisions joined by `|`.
- Persistence: number of distinct client counts in `{2,3,4,5}` for which the same unique object is a conflict.
- Policy accuracy is evaluated only on rows already flagged as conflict; policies do not create the conflict set.

## Success criteria
- Input conflict rows = 908 and configuration totals reconcile to existing 266 + 598 + 44.
- Configuration denominator uses verified `test_rows` metadata.
- Persistence counts reconcile back to 908 occurrences when weighted by each object's number of conflict client counts.
- All six policies receive the same conflict-row denominator per configuration.
- Generated evidence is deterministic and CI-tested.
