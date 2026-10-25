# LEM2 40-slide conflict-factor presentation audit — 2026-10-26

## Scope

This update closes the professor-facing gap: the prior deck defined inference conflict and quantified concentration/persistence, but did not consolidate the already-computed **conflict factors** into presentation-ready evidence.

## Added slides

### Structural factor screening

The deck now explicitly separates structural/configuration factors from causal claims.

- **Client count C**: pooled 12-configuration descriptive association with pre-resolution conflict rate: Pearson `r=0.8398`, Spearman `rho=0.8637`.
- **Matching-rule load** (mean matching rules per conflict case):
  - Car Evaluation: `2.45 -> 2.63 -> 3.09 -> 3.72`
  - Balance Scale: `2.89 -> 3.23 -> 3.61 -> 3.94`
  - Hayes-Roth: `2.33 -> 2.50 -> 3.00 -> 3.00`
  This is the structural signal closest to the operational definition of inference conflict: the same test object being matched by rules proposing different decisions.
- **Coverage/exposure** approaches 1.0 as C grows, but conflict continues to vary, so coverage alone is insufficient.
- **Reduct instability** is not a common driver: it is `0` for all Car and Balance C=2..5 configurations while their conflict rates rise strongly; pooled Pearson `r=0.0664`.
- **Rule heterogeneity** is not a universal driver: pooled Pearson `r=0.0179`, and dataset-level directions disagree.
- **Exact antecedent conflict** is not the main source: Car C=2 has exact conflict rate `0` but inference conflict rate `85/346 = 24.6%`.
- **Global rule count** is not a universal driver: Car rises, Balance falls, Hayes is mixed while conflict workload changes.

Interpretation boundary: these are descriptive factor screens on the frozen seed=42 sweep, not causal inference.

### Factor-value anatomy

The deck now exposes the existing `CONFLICT_FACTOR_VALUE.csv` evidence as conflict-composition statistics.

**Balance Scale** top value within each factor among conflict occurrences:
- `left_distance=5`: 65/266 = 24.4%
- `left_weight=1`: 65/266 = 24.4%
- `right_distance=4`: 72/266 = 27.1%
- `right_weight=1`: 73/266 = 27.4%

**Car Evaluation**:
- `buying=low`: 195/598 = 32.6%
- `maint=low`: 186/598 = 31.1%
- `doors=2`: 166/598 = 27.8%
- `persons=more`: 240/598 = 40.1%
- `lug_boot=big`: 223/598 = 37.3%
- `safety=high`: 239/598 = 40.0% (`safety=med`: 39.3%)

**Hayes-Roth**:
- `age=1` and `age=2`: 15/44 each = 34.1%
- `educational_level=2`: 21/44 = 47.7%
- `hobby=3`: 23/44 = 52.3%
- `marital_status=1`: 23/44 = 52.3%

Interpretation boundary: these percentages describe **composition among conflict occurrences**. They are not factor-value risk because the existing table has no non-conflict denominator. A future risk claim requires `ConflictRate(value)=n_conflict(value)/n_all_evaluations(value)` and preferably lift/effect-size estimates over repeated matched splits.

## Existing slide corrections

The former mechanism-closure slide no longer says the factors are simply "not measured". It now distinguishes:
1. direct operational mechanism (`|Candidate(x)| > 1`),
2. completed descriptive structural-factor screening,
3. completed factor-value conflict composition,
4. still-pending repeated-split robustness/causal validation.

The final conclusion slide was updated accordingly.

## Visual / artifact QA

- Slide count: **40**
- LibreOffice PDF render: **PASS, 40/40 pages**
- New/modified conflict-factor slides visually inspected after render: no visible clipping/overflow observed.
- PPTX SHA-256: `750f59d29e44fefc4294ca8d06955419d693bcaef8b37176860c27a6c8513895`
- Drive file ID: `1ZaYE8IzTa7b391B3AppJQhjnIyPYYh3e`
- Drive raw readback size: `1,610,014 bytes`
- Drive readback SHA-256 matches local artifact.

## Repository boundary

All presentation metadata/audit changes remain on `research/conflict-client-sweep-20261020`. Frozen `main` is not modified.
