# Federated LEM2 Research — Literature × Mathematics × Code Mapping

> Scope: research documentation only. This document does not modify the frozen production semantics.
>
> Frozen production baseline: `main @ 31b078bb78c6754d04c56a2e1cc849c8feb221d7`
>
> Research branch: `research/conflict-client-sweep-20261020`

## 0. Terminology

The four compared methods are called **Prediction Policies** in this project, matching the production API (`prediction_policy`, `predict_with_policy`).

`Conflict Resolution` describes the research function of those policies on conflict cases; it is not the collective original name of all four methods.

The source Healthcare paper itself separates:

1. `Aggregation Strategy` — local rule sets are combined by UNION;
2. `Inference` — the first matching rule determines the prediction.

Source paper:

- Woźniak, K., Sousa, J., & Sniezynski, B. (2026). *Rule-Based Federated Learning for Healthcare*. DOI: `10.1007/978-3-032-29921-5_38`.

---

# 1. End-to-end research pipeline

\[
Client\ Data
\rightarrow
Local\ LEM2
\rightarrow
Federated\ Aggregation
\rightarrow
Global\ Rule\ Set
\rightarrow
Rule\ Structure
\rightarrow
Conflict\ Audit
\rightarrow
Prediction\ Policy
\rightarrow
Prediction
\rightarrow
Evaluation
\]

The Client Count Sweep is an outer experimental factor:

\[
C\in\{2,3,4,5\}
\]

It does not redefine LEM2, aggregation, conflict, or prediction-policy mathematics.

---

# 2. Full Literature × Math × Code mapping

| Layer | Mathematical object | Production code | Literature mapping | Mapping strength | What this project adds |
|---|---|---|---|---|---|
| Local LEM2 | \(R_c=LEM2(U_c)\) | `roughset/core.py::induce_lem2`, `lower_approximation`, `build_one_complex` | Classical LEM2; Woźniak et al. (2026) use local LEM2 with shared global discretization | Direct | Frozen local induction used as common baseline |
| Reduct | minimum \(|R|\) with \(|POS_R(D)|=|POS_C(D)|\) | `roughset/reduct.py::find_exact_minimum_cardinality_reducts`, `select_minimum_reduct` | Rough-set reduct theory | Direct | Exact integer preservation and empty-reduct semantics fixed by final audit |
| Federated aggregation | \(R_G=\bigcup_{c=1}^{C}R_c\) | `roughset/federated.py::union_rules_with_provenance` | Woźniak et al. (2026) UNION aggregation | Direct | Full-rule identity plus complete provenance |
| Full rule identity | \(key(r)=(sorted(Ante(r)),d_r)\) | `roughset/core.py::Rule.key` | Source paper states uniqueness in terms of condition sets; exact code semantics are not specified in the paper | Project contract | Decision is included so contradictory conclusions are not silently collapsed |
| Rule similarity | \(J(A,B)=|A\cap B|/|A\cup B|\) | `roughset/evaluation.py::pairwise_rule_jaccard` | Source paper uses Jaccard to quantify local-rule diversity | Direct | Both antecedent-only and full-rule signatures are reported |
| Exact antecedent conflict | same antecedent, >1 decision | `roughset/evaluation.py::audit_rule_conflicts` | Rule-conflict / inconsistent-rule literature; RSES treats contradictory rule conclusions as a classification conflict | Strong | Explicit structural conflict rate on the federated global rule set |
| Inference conflict | \(|\{d_r:r\in M(x)\}|>1\) | `roughset/pipeline.py::_pre_resolution_conflicts`, `evaluation.audit_conflict_cases` | Lindgren conflict literature: multiple rules cover the same example but predict different classes | Direct | Conflict workload is frozen before any policy runs |
| FIRST_MATCH | first matching ordered rule | `roughset/evaluation.py::predict_with_policy` | Woźniak et al. (2026) first-match inference | Direct | Exhaustive client-order sensitivity audit for C≤5 |
| SIMPLE_VOTING | \(S_{SV}(d|x)=|M_d(x)|\) | `predict_with_policy` | RSES Simple Voting; Lazo-Cortés et al. (2020) | Direct | Federated comparator on the same frozen global rule artifact |
| STANDARD_VOTING | \(S_{STD}(d|x)=\sum_{r\in M_d(x)}w(r)\) | `predict_with_policy`, `pipeline.global_rule_support_context` | RSES Standard Voting; Lazo-Cortés et al. (2020) | Strong adaptation | Weight becomes pooled, decision-consistent support evaluated over all clients |
| GLOBAL_STRENGTH | \(GS(d|x)=|\bigcup_{r\in M_d(x)}S_G(r)|/N_d\) | `predict_with_policy`, `global_rule_support_context` | Bazan et al. (2000), GlobalStrength | Formula-level direct; federated context adapted | Distributed pooled support sets and pooled class denominator |
| Evaluation | BA, Macro-F1, Coverage, CRA, OSR | `roughset/evaluation.py`, `roughset/federated.py` | Source paper evaluates prediction quality and coverage; conflict literature evaluates conflict-handling methods | Mixed | Conflict-only metrics and order-sensitivity distribution |
| Client Count Sweep | \(C=2,3,4,5\) | partition + artifact build + policy evaluation | Woźniak et al. (2026) use C=2..5; broader FL literature studies client-count effects | Direct experimental precedent | Tracks structure → conflict → policy outcome, not only overall accuracy |

---

# 3. Federated aggregation and rule identity

For client \(c\):

\[
R_c=LEM2(U_c)
\]

The frozen federated baseline uses:

\[
R_G=\bigcup_{c=1}^{C}R_c
\]

Production code:

```text
roughset/federated.py
└─ union_rules_with_provenance(...)
```

Full rule identity:

\[
key(r)=(sorted(Ante(r)),d_r)
\]

Therefore:

\[
X\rightarrow A
\neq
X\rightarrow B
\]

Both full rules remain observable. Conflict is then audited explicitly rather than hidden by antecedent-only deduplication.

Important distinction:

\[
Aggregation\neq Conflict\ Detection\neq Prediction\ Policy
\]

Aggregation answers which rules enter \(R_G\). Conflict Audit asks whether competing decisions are present. Prediction Policy decides the final class.

---

# 4. The two conflict definitions

## 4.1 Exact Antecedent Conflict

For an antecedent signature \(a\):

\[
D(a)=\{d_r:Ante(r)=a\}
\]

Conflict exists if:

\[
|D(a)|>1
\]

Example:

```text
X → A
X → B
```

Code:

```text
roughset/evaluation.py
└─ audit_rule_conflicts(...)
```

This is a structural property of the global rule set.

## 4.2 Inference-Level Conflict

For test case \(x\):

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

A prediction-time conflict exists if:

\[
|\{d_r:r\in M(x)\}|>1
\]

Example:

```text
A=1       → Yes
A=1,B=2   → No
```

The antecedents are different, so this is not an exact antecedent conflict. But a case with `A=1,B=2` matches both and therefore has competing decisions.

Code:

```text
roughset/pipeline.py
└─ _pre_resolution_conflicts(...)

roughset/evaluation.py
└─ audit_conflict_cases(...)
```

Conflict Case Rate:

\[
CCR=
\frac{|X_{conflict}|}{N_{test}}
\]

The distinction is empirically necessary: in frozen Car Evaluation at C=2, exact conflict groups are zero while inference conflict cases are 85/346.

### Literature correspondence

The unordered-rule classification literature explicitly treats the situation where multiple rules cover the same example and predict different classes as a conflict problem. Relevant papers include:

- Lindgren, T. (2004). *Methods for Rule Conflict Resolution*. DOI: `10.1007/978-3-540-30115-8_26`.
- Lindgren, T., & Boström, H. (2002). *Classification with Intersecting Rules*. DOI: `10.1007/3-540-36169-3_31`.
- Lindgren, T., & Boström, H. (2004). *Resolving Rule Conflicts with Double Induction*. DOI: `10.3233/IDA-2004-8503`.
- Yao, Y., & Zhou, B. (2008). *Micro and Macro Evaluation of Classification Rules*. DOI: `10.1109/COGINF.2008.4639199`.

---

# 5. Four Prediction Policies

All four policies receive the same frozen global rules and the same test case.

Define:

\[
M_d(x)=\{r\in R_G:x\models Ante(r),d_r=d\}
\]

The production entry point is:

```text
roughset/evaluation.py
└─ predict_with_policy(...)
```

Supported values:

```text
FIRST_MATCH
SIMPLE_VOTING
STANDARD_VOTING
GLOBAL_STRENGTH
```

## 5.1 FIRST_MATCH

Let the ordered global list be:

\[
R_G=(r_1,\ldots,r_m)
\]

Then:

\[
k^*(x)=\min\{k:x\models Ante(r_k)\}
\]

\[
\hat y_{FM}(x)=d_{r_{k^*(x)}}
\]

**Evidence used:** order only.

Properties:

- no rule-count voting;
- no rule support;
- no class-size normalization;
- client-arrival order can change predictions.

Literature correspondence:

- Woźniak et al. (2026) explicitly use first-match inference after UNION aggregation.

Our extension:

\[
Client\ Order\rightarrow Rule\ Order\rightarrow Prediction
\]

is audited by client-order permutations. For C≤5 and max permutations 120, every client order can be enumerated.

## 5.2 SIMPLE_VOTING

Each matching rule casts one vote:

\[
S_{SV}(d|x)=|M_d(x)|
\]

Prediction is the decision with the largest vote count, followed by the common deterministic tie rule.

**Evidence used:** matching-rule count.

Literature correspondence:

- RSES Simple Voting: one matching rule = one vote.
- Lazo-Cortés et al. (2020) describe this rule-conflict voting procedure.

Reference:

- Lazo-Cortés, M. S., Martínez-Trinidad, J. F., Carrasco-Ochoa, J. A., & Almanza-Ortega, N. N. (2020). *Towards Selecting Reducts for Building Decision Rules for Rule-Based Classifiers*. DOI: `10.1007/978-3-030-49076-8_7`.

## 5.3 STANDARD_VOTING

RSES Standard Voting assigns more votes to rules with greater support.

The frozen federated project defines decision-consistent support on each client:

\[
Supp_c(r)=
\{z\in U_c:z\models Ante(r)\land D(z)=d_r\}
\]

Global support set:

\[
S_G(r)=\bigsqcup_{c=1}^{C}Supp_c(r)
\]

Rule weight:

\[
w(r)=|S_G(r)|
=\sum_{c=1}^{C}|Supp_c(r)|
\]

Policy score:

\[
S_{STD}(d|x)=
\sum_{r\in M_d(x)}w(r)
\]

Code:

```text
roughset/pipeline.py
└─ global_rule_support_context(...)

roughset/evaluation.py
└─ predict_with_policy(...)
   └─ STANDARD_VOTING
```

Important project adaptation:

- each global rule is evaluated on **all clients**, not only provenance clients;
- only antecedent matches whose true decision equals the rule decision count as positive support.

The final mathematical audit corrected this support scope.

Main mathematical difference from GLOBAL_STRENGTH: if the same training object positively supports multiple matching rules of the same decision, it may contribute once to each rule weight and therefore more than once to the score sum.

## 5.4 GLOBAL_STRENGTH

For a decision \(d\), first union the positive support objects of all matching rules:

\[
S_d(x)=
\bigcup_{r\in M_d(x)}S_G(r)
\]

Define pooled class size:

\[
N_d=|\{z\in U_{train}:D(z)=d\}|
\]

Then:

\[
GS(d|x)=
\frac{|S_d(x)|}{N_d}
\]

Prediction selects the decision with maximal Global Strength, followed by the common deterministic tie rule.

Code:

```text
roughset/evaluation.py
└─ predict_with_policy(...)
   └─ GLOBAL_STRENGTH

roughset/pipeline.py
└─ global_rule_support_context(...)
```

Key property:

- the numerator is a set union;
- the same training object covered by several matching rules of the same class is counted once;
- the score is normalized by total class size.

Literature correspondence:

Bazan et al. define GlobalStrength using the union of class-consistent objects covered by matching rules divided by the class cardinality. The mathematical structure directly corresponds to this project's policy; this project adapts the support construction to a federated pooled context.

Reference:

- Bazan, J. G., Nguyen, H. S., Nguyen, S. H., Synak, P., & Wróblewski, J. (2000). *Rough Set Algorithms in Classification Problem*. In *Rough Set Methods and Applications*. DOI: `10.1007/978-3-7908-1840-6_3`.

---

# 6. Four-policy comparison table

| Prediction Policy | Main question | Formula / selection | Evidence | Can the same object contribute through multiple matching rules? | Class normalized? | Arrival-order sensitive? | Literature origin |
|---|---|---|---|---|---|---|---|
| `FIRST_MATCH` | Which rule appears first? | first matching ordered rule | rule order | N/A | No | **Yes** | Woźniak et al. (2026) |
| `SIMPLE_VOTING` | Which decision has more matching rules? | \(|M_d(x)|\) | rule count | N/A | No | No | RSES / Lazo-Cortés et al. (2020) |
| `STANDARD_VOTING` | Which decision accumulates more positive rule support? | \(\sum_{r\in M_d}w(r)\) | pooled rule support | **Yes** | No | No | RSES Standard Voting; federated adaptation here |
| `GLOBAL_STRENGTH` | Which matching-rule coalition covers more of its own class? | \(|\cup S_G(r)|/N_d\) | unique support-object coverage | **No** | **Yes** | No | Bazan et al. (2000); federated adaptation here |

The four policies form a useful evidence hierarchy:

\[
\boxed{
Order
\rightarrow
Rule\ Count
\rightarrow
Rule\ Support\ Sum
\rightarrow
Unique\ Class\ Coverage\ Ratio
}
\]

This hierarchy is descriptive, not a claim that each later policy is universally more accurate.

---

# 7. Common tie/default semantics

If no global rule matches:

\[
M(x)=\emptyset
\Rightarrow
\hat y(x)=d_0
\]

For `SIMPLE_VOTING`, `STANDARD_VOTING`, and `GLOBAL_STRENGTH`, production code uses `_resolve_vote`:

1. find the maximum score;
2. treat scores as tied using `np.isclose`;
3. if default class is among the winners, select it;
4. otherwise select the string-smallest winning class.

This tie rule is part of implementation semantics and must be reported with policy formulas.

---

# 8. Client Count Sweep and corresponding literature

The source Healthcare paper already varies:

\[
C\in\{2,3,4,5\}
\]

Therefore the project's C=2..5 sweep directly continues the source experimental factor.

The difference is the research question.

The source paper primarily asks whether federated rule learning retains predictive performance under different client/bin configurations.

This project asks:

\[
\boxed{
Client\ Count
\rightarrow
Rule\ Structure
\rightarrow
Conflict\ Workload
\rightarrow
Prediction\ Policy\ Outcome
\rightarrow
Performance
}
\]

Broader FL evidence also supports client count as an important independent variable:

- Cowlishaw, R., Longépé, N., & Riccardi, A. (2025). *Balancing centralisation and decentralisation in federated learning for Earth Observation-based agricultural predictions*. Scientific Reports, 15, 10454. DOI: `10.1038/s41598-025-94244-2`.
  - Treats number of clients as a primary independent variable.
  - Reports slower learning / lower final F1 in its specific setup as client count increases.
  - This supports fragmentation motivation, not a universal theorem that more clients always reduce performance.

- Babar, M., Qureshi, B., & Koubaa, A. (2024). *Investigating the impact of data heterogeneity on the performance of federated learning algorithm using medical imaging*. PLOS ONE, 19(5), e0302539. DOI: `10.1371/journal.pone.0302539`.
  - Supports the broader role of heterogeneous decentralized data in federated performance.
  - It does **not** directly establish rule-conflict growth and must only be used as FL background.

Current frozen UCI3 evidence shows higher C=5 than C=2 inference-conflict rate in all three datasets, but not a strict monotonic law at every intermediate C.

---

# 9. Closely related federated rule-fusion work

A recent neighboring study is:

- Pękala, B., Wilbik, A., & Gil, D. (2026). *A privacy-preserving rule fusion approach for uncertainty-aware decision-making in posture detection*. Scientific Reports. DOI: `10.1038/s41598-026-60758-6`.

It provides current evidence that federated collaborative generation and integration of rule sets is an active research direction, particularly under privacy and uncertainty constraints.

Use this paper as **neighboring federated rule-fusion literature**. Do not attribute a specific conflict-delete procedure to it unless that claim is verified directly from the full method text.

---

# 10. What is existing literature vs. what is our contribution?

## Existing concepts

The following are not new algorithms proposed by this project:

- LEM2;
- UNION aggregation in the source Healthcare baseline;
- FIRST_MATCH inference;
- Simple Voting;
- Standard Voting;
- Global Strength;
- rule-conflict resolution as a general problem;
- varying client count as an FL experiment.

## Project contribution direction

The defensible contribution is the integrated federated mechanism analysis:

\[
\boxed{
Client\ Fragmentation
\rightarrow
Rule\ Structural\ Change
\rightarrow
Conflict\ Workload
\rightarrow
Prediction\ Policy
\rightarrow
Performance
}
\]

Specifically:

1. distinguish full-rule identity from antecedent identity;
2. preserve contradictory full rules rather than hiding them through antecedent-only deduplication;
3. separate exact antecedent conflict from inference-level conflict;
4. freeze pre-resolution conflict workload before policy comparison;
5. compare four Prediction Policies on the same `RuleSystemArtifact`;
6. quantify FIRST_MATCH client-order sensitivity;
7. evaluate both overall and conflict-only performance;
8. study all of the above under C=2..5 client fragmentation.

No current evidence justifies claiming a universal best policy.

---

# 11. Core references

1. Woźniak, K., Sousa, J., & Sniezynski, B. (2026). *Rule-Based Federated Learning for Healthcare*. DOI: `10.1007/978-3-032-29921-5_38`.
2. Lazo-Cortés, M. S., Martínez-Trinidad, J. F., Carrasco-Ochoa, J. A., & Almanza-Ortega, N. N. (2020). *Towards Selecting Reducts for Building Decision Rules for Rule-Based Classifiers*. DOI: `10.1007/978-3-030-49076-8_7`.
3. Bazan, J. G., Nguyen, H. S., Nguyen, S. H., Synak, P., & Wróblewski, J. (2000). *Rough Set Algorithms in Classification Problem*. DOI: `10.1007/978-3-7908-1840-6_3`.
4. Lindgren, T. (2004). *Methods for Rule Conflict Resolution*. DOI: `10.1007/978-3-540-30115-8_26`.
5. Lindgren, T., & Boström, H. (2002). *Classification with Intersecting Rules*. DOI: `10.1007/3-540-36169-3_31`.
6. Lindgren, T., & Boström, H. (2004). *Resolving Rule Conflicts with Double Induction*. DOI: `10.3233/IDA-2004-8503`.
7. Yao, Y., & Zhou, B. (2008). *Micro and Macro Evaluation of Classification Rules*. DOI: `10.1109/COGINF.2008.4639199`.
8. Cowlishaw, R., Longépé, N., & Riccardi, A. (2025). *Balancing centralisation and decentralisation in federated learning for Earth Observation-based agricultural predictions*. DOI: `10.1038/s41598-025-94244-2`.
9. Babar, M., Qureshi, B., & Koubaa, A. (2024). *Investigating the impact of data heterogeneity on the performance of federated learning algorithm using medical imaging*. DOI: `10.1371/journal.pone.0302539`.
10. Pękala, B., Wilbik, A., & Gil, D. (2026). *A privacy-preserving rule fusion approach for uncertainty-aware decision-making in posture detection*. DOI: `10.1038/s41598-026-60758-6`.

---

# 12. Detailed project documents

- `modules/00_PIPELINE_MAP.md`
- `modules/01_LOCAL_LEM2.md`
- `modules/02_AGGREGATION.md`
- `modules/03_RULE_STRUCTURE.md`
- `modules/04_CONFLICT_AUDIT.md`
- `modules/05_CONFLICT_RESOLUTION.md`
- `modules/06_EVALUATION.md`
- `modules/07_CLIENT_COUNT_SWEEP.md`
- `modules/08_MATHEMATICAL_ARCHITECTURE.md`
- `TEAM_DISCUSSION_PREDICTION_POLICIES_AND_CONFLICT.md`
- `figures/federated_lem2_conflict_resolver_flow.webp`
