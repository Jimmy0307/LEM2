# Conflict Concentration / Anatomy

This report analyzes the already-frozen prediction-time conflict evidence. It does **not** change LEM2, UNION, reducts, or any prediction-policy formula.

## Headline reconciliation

- Conflict occurrences: **908**
- Configuration-level test evaluations: **1992**
- Overall conflict workload: **45.6%**
- Unique test objects with at least one conflict: **392**
- True class absent from Candidate(x): **45** occurrences

## Where the 908 occurrences concentrate

- **Balance Scale: 266** (29.3% of all conflict occurrences)
- **Car Evaluation: 598** (65.9% of all conflict occurrences)
- **Hayes-Roth: 44** (4.8% of all conflict occurrences)

By client count:
- **C=2: 135** (14.9%)
- **C=3: 210** (23.1%)
- **C=4: 253** (27.9%)
- **C=5: 310** (34.1%)

## Persistence across client counts

The same `(dataset, fold, row_id)` can be a conflict at multiple C values. Persistence therefore separates isolated partition-sensitive conflicts from repeatedly recurring objects.
- Conflict at **1 client count**: 106 unique objects
- Conflict at **2 client counts**: 123 unique objects
- Conflict at **3 client counts**: 96 unique objects
- Conflict at **4 client counts**: 67 unique objects

## Candidate decision concentration

### Balance Scale
- `L|R`: 149 occurrences
- `B|L|R`: 51 occurrences
- `B|L`: 38 occurrences
- `B|R`: 28 occurrences

### Car Evaluation
- `acc|unacc`: 335 occurrences
- `acc|good`: 61 occurrences
- `acc|vgood`: 45 occurrences
- `acc|good|unacc`: 29 occurrences
- `acc|good|vgood`: 29 occurrences

### Hayes-Roth
- `1.0|2.0`: 30 occurrences
- `1.0|2.0|3.0`: 5 occurrences
- `2.0|3.0`: 5 occurrences
- `1.0|3.0`: 4 occurrences

## Conflict-only resolver accuracy

- **FIRST_MATCH**: 655/908 = 72.1%
- **GLOBAL_STRENGTH**: 661/908 = 72.8%
- **POPULATION_GLOBAL**: 658/908 = 72.5%
- **POPULATION_STANDARD**: 696/908 = 76.7%
- **SIMPLE_VOTING**: 622/908 = 68.5%
- **STANDARD_VOTING**: 699/908 = 77.0%

## Population transition outcomes

- **GS_TO_PG**: CHANGED_SAME_CORRECTNESS=4, CORRECTED=10, HARMED=13, UNCHANGED=881
- **STD_TO_PS**: CHANGED_SAME_CORRECTNESS=1, CORRECTED=6, HARMED=9, UNCHANGED=892

## Factor/value interpretation boundary

`CONFLICT_FACTOR_VALUE.csv` reports **within-conflict concentration only**. It tells us what values are common among conflict occurrences, but it does not estimate relative risk or causal effect because non-conflict rows are not used as denominators in this layer.

## Interpretation

The 908 conflicts should not be treated as one homogeneous block. They can now be decomposed into configuration concentration, recurring objects, candidate-decision combinations, evidence structure, and resolver outcomes. This supports the next research question: which data/rule structures repeatedly create cross-decision overlap, and which resolver biases matter for those structures?
