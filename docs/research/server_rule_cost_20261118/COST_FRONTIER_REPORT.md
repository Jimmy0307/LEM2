# Federated LEM2: cross-source empirical cost tiers (2026-11-18)

**EXPLORATORY DESCRIPTIVE REVIEW, NOT A NEW SERVER RULE ALGORITHM.**
Frozen G5 CSVs are unchanged. Only published aggregates and metadata are read.

## Evidence coverage
- Confirmatory cohort: 51 OpenML sources, 37 manually identified families, 10 seeds,
  3 regimes, 5 non-CART arms; 765 source-regime-arm records, 7,650 model tasks.
- All 161 historical source-catalogue rows are included in the inventory.
- All 117 historical PMLB audit candidates, of which 109 passed; CPU records joined.
- Actual CPU staircase: 36 trials from 4 distinct sources.

These groups are NOT 51+161 independent datasets; related source families overlap.
Historical PMLB experiments use at most 900 rows and the first 6 features.
G5 uses first 6 features, at most 1,800 rows, and 3 Clients.

## Budget frontier (one FIXED arm selected by retrospective aggregate TEST BA)
Caps are HARD per-task maximum numbers per Client across all 51 sources
and 10 seeds in the given regime, not averages. Displayed numbers are means.
The selected fixed arm is a retrospective TEST-based ranking and is
NOT a deployable selection policy. The 512 tier does NOT permit MDLP
on every source; the 10M tier does NOT permit FED_MD on every source.
Intermediate accuracy and communication between roughly 413 and
7.7M mean numbers per Client remain unobserved.

| Regime | Hard tier | Arm | Test BA | Non-TRUE coverage | Conflict | Rules | Mean numbers/Client | Max numbers/Client |
|---|---|---|---:|---:|---:|---:|---:|---:|
| IID | L0_16 | R3 | 45.55% | 49.17% | 18.34% | 206.2 | 8.1 | 12.0 |
| IID | L1_512 | R3 | 45.55% | 49.17% | 18.34% | 206.2 | 8.1 | 12.0 |
| IID | L2_2048 | R3 | 45.55% | 49.17% | 18.34% | 206.2 | 8.1 | 12.0 |
| IID | L3_10000000 | R3 | 45.55% | 49.17% | 18.34% | 206.2 | 8.1 | 12.0 |
| IID | L4_40000000 | M2 | 50.21% | 68.69% | 27.44% | 291.5 | 7,673,759.9 | 39,431,584.0 |
| NONIID_05 | L0_16 | R3 | 45.85% | 58.19% | 26.44% | 169.8 | 8.1 | 12.0 |
| NONIID_05 | L1_512 | R3 | 45.85% | 58.19% | 26.44% | 169.8 | 8.1 | 12.0 |
| NONIID_05 | L2_2048 | R2 | 46.74% | 45.65% | 13.63% | 112.0 | 412.8 | 1,610.0 |
| NONIID_05 | L3_10000000 | R2 | 46.74% | 45.65% | 13.63% | 112.0 | 412.8 | 1,610.0 |
| NONIID_05 | L4_40000000 | M2 | 49.85% | 74.78% | 36.26% | 238.5 | 7,673,759.9 | 39,431,584.0 |
| NONIID_01 | L0_16 | R3 | 45.04% | 49.12% | 33.95% | 99.0 | 8.1 | 12.0 |
| NONIID_01 | L1_512 | R3 | 45.04% | 49.12% | 33.95% | 99.0 | 8.1 | 12.0 |
| NONIID_01 | L2_2048 | R2 | 45.76% | 38.60% | 30.86% | 64.8 | 412.8 | 1,610.0 |
| NONIID_01 | L3_10000000 | R2 | 45.76% | 38.60% | 30.86% | 64.8 | 412.8 | 1,610.0 |
| NONIID_01 | L4_40000000 | M2 | 47.55% | 63.03% | 39.22% | 145.9 | 7,673,759.9 | 39,431,584.0 |

## Actual CPU time (whole Classical LEM2 fit; NOT Server rule integration)
| Rows | Features | Sources | Median fit seconds | Median 6-policy test seconds | Median rules |
|---:|---:|---:|---:|---:|---:|
| 600 | 4 | 4 | 0.422 | 0.044 | 13.0 |
| 600 | 6 | 4 | 0.773 | 0.050 | 17.0 |
| 600 | 8 | 4 | 2.282 | 0.085 | 46.5 |
| 1600 | 4 | 4 | 0.781 | 0.092 | 13.0 |
| 1600 | 6 | 4 | 1.515 | 0.127 | 26.5 |
| 1600 | 8 | 4 | 3.825 | 0.233 | 54.5 |
| 3200 | 4 | 4 | 1.481 | 0.173 | 8.5 |
| 3200 | 6 | 4 | 2.425 | 0.235 | 22.0 |
| 3200 | 8 | 4 | 7.003 | 0.531 | 68.0 |

## Interpretation / guardrails
1. Hard budget levels constrain the maximum recorded per-task communication
   over all 51 sources and 10 seeds; observed maxima are not population bounds.
2. Communication numbers are simulated accounting, not network latency
   or actual secure-protocol byte payload. Multiplying by 8 only models float64.
3. Fit time is preprocessing + reduct + induction, NOT Server merge CPU.
4. Non-TRUE coverage subtracts A-only TRUE matches from B2 coverage;
   it is not predictive precision nor a global rule certificate.
5. Per-dataset Pareto uses TEST outcomes: diagnostic only; choosing by it
   for a deployed selector would leak Test labels.
6. Ada/Gina potentially overlap historical upstream sources; 51 and 161
   must never be added into an independence claim.
7. No result here identifies the optimal budget for a new server-side
   coverage/conflict rule subset optimizer: rule antecedents and
   independent validation evidence are absent from stored G5 CSVs.

## Next gate: Server-only cost-knee experiment
Freeze each Client rule set once, without any further Client calls.
On identical frozen rules compare UNION, TRUE fallback, exact logical
deduplication, safe subsumption pruning and budgeted rule subsets.
Sweep 25/50/75/100 percent non-TRUE rules and measure server CPU,
peak RAM, serialized rule bytes, validation coverage/conflict/BA,
and held-out Test BA with source-level paired statistics.
Without authorized Server-side validation, restrict objectives to
syntactic rule overlap and potential logical conflict, not observed
global empirical Coverage. Require new preregistration for confirmation.

Reproduce: python -m experiments.server_rule_cost_20261118.analyze_cost_frontier
