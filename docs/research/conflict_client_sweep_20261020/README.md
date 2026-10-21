# Federated LEM2 Research — Literature × Mathematics × Code Mapping

> Scope: research documentation and research-branch evaluation/reporting integration on top of the frozen mathematical baseline.
>
> Frozen production baseline: `main @ 31b078bb78c6754d04c56a2e1cc849c8feb221d7`
>
> Final teacher-facing entry point: `FINAL_TEACHER_HANDOFF.md`

## Canonical reading order

1. `FINAL_TEACHER_HANDOFF.md` — final scope and software handoff.
2. `TEAM_DISCUSSION_PREDICTION_POLICIES_AND_CONFLICT.md` — four Prediction Policies and conflict.
3. `TEAM_EVALUATION_METRICS_ESTABLISHED.md` — formula × meaning × code × citation for established evaluation.
4. `CONFLICT_RESOLUTION_NOTES.md` — cited mathematical conflict/policy explanation.
5. `LITERATURE_REFERENCE_INDEX.md` — citation provenance and adaptation boundaries.
6. `modules/00`–`08` — layer-by-layer research architecture.
7. `reference/policies/` — separated teaching/reference code for the four Prediction Policies.

## Terminology

The four compared methods are formally called **Prediction Policies**:

```text
FIRST_MATCH
SIMPLE_VOTING
STANDARD_VOTING
GLOBAL_STRENGTH
```

`Conflict Resolution` describes their role when competing rule evidence exists; it is not used as the formal shared algorithm family name.

## Main architecture

\[
Data
\rightarrow Local\ LEM2
\rightarrow Federated\ Aggregation
\rightarrow Global\ Rules
\rightarrow Rule\ Conflict
\rightarrow Prediction\ Policy
\rightarrow Evaluation
\]

Client count is an outer experimental factor:

\[
C\in\{2,3,4,5\}
\]

## Prediction Policies

### FIRST_MATCH

\[
k^*(x)=\min\{k:x\models Ante(r_k)\}
\]

\[
\hat y_{FM}(x)=d_{r_{k^*(x)}}
\]

Evidence: rule order.

Source: Woźniak et al. (2026), DOI `10.1007/978-3-032-29921-5_38`.

### SIMPLE_VOTING

\[
S_{SV}(d|x)=|M_d(x)|
\]

Evidence: matching-rule count.

Source: Lazo-Cortés et al. (2020), DOI `10.1007/978-3-030-49076-8_7`.

### STANDARD_VOTING

\[
Supp_c(r)=\{z\in U_c:z\models Ante(r)\land D(z)=d_r\}
\]

\[
w_F(r)=\sum_c|Supp_c(r)|
\]

\[
S_{STD}(d|x)=\sum_{r\in M_d(x)}w_F(r)
\]

Evidence: pooled decision-consistent positive rule-support sum.

Literature boundary: Lazo-Cortés et al. (2020) supports the support-weighted voting principle; the all-client decision-consistent support scope is this project’s federated adaptation.

### GLOBAL_STRENGTH

\[
S_d(x)=\bigcup_{r\in M_d(x)}S_G(r)
\]

\[
GS(d|x)=\frac{|S_d(x)|}{N_d}
\]

Evidence: unique class-consistent support coverage ratio.

Source: Bazan et al. (2000), GlobalStrength Eq. (23), DOI `10.1007/978-3-7908-1840-6_3`.

Mnemonic:

\[
\boxed{
Order
\rightarrow Rule\ Count
\rightarrow Rule\ Support\ Sum
\rightarrow Unique\ Class\ Coverage\ Ratio
}
\]

## Rule conflict

For test case \(x\):

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

The main prediction-time conflict set is:

\[
\boxed{
\mathcal C=\{x\in U_{test}:|\{d_r:r\in M(x)\}|>1\}
}
\]

This follows the established overlapping/intersecting rule-conflict framing in Lindgren (2004) and Lindgren & Boström (2002).

Exact same-antecedent / different-decision groups are supplementary structural diagnostics, not the complete conflict definition.

## Established evaluation only

Primary manuscript-facing measures:

```text
Balanced Accuracy
Macro-F1
Coverage
Ruleset size
Mean conditions per rule
Pairwise antecedent Jaccard
Conflict-set count / proportion
Balanced Accuracy on conflict set
Macro-F1 on conflict set
Variation Ratio across client-order predictions
```

Repeated splits/seeds are required before Friedman + post-hoc / paired Wilcoxon significance claims.

Legacy project names `CRA / CCR / OSR / H_rule` are not primary theoretical metrics; they may remain only for backward compatibility or supplementary diagnostics.

## Code mapping

| Layer | Canonical code |
|---|---|
| LEM2 | `roughset/core.py` |
| Reduct | `roughset/reduct.py` |
| Prediction Policies | `roughset/evaluation.py::predict_with_policy` |
| Federated UNION / client order | `roughset/federated.py` |
| Structural artifact / conflict workload | `roughset/pipeline.py` |
| Established Variation Ratio | `roughset/established_metrics.py` |
| All-policy output | `roughset/batch.py::run_policy_matrix` |
| Windows all-policy launcher | `run.bat` |
| Separated teacher/reference policy code | `reference/policies/` |

## Software synchronization

`run.bat` calls:

```text
main.py --config config.json --all-policies
```

The batch pipeline evaluates all configured Prediction Policies and client counts, and now emits the established Variation Ratio fields:

```text
mean_variation_ratio
mean_variation_ratio_conflict
```

No extra `.bat` command is required because the synchronization occurs in the Python batch/reporting layer invoked by the launcher.

## Verification

The research branch contains a GitHub Actions verification workflow that runs:

```text
python -m compileall -q roughset main.py
python -m pytest -q
```

It also includes parity tests for the four separated reference policy files and an integration test that requires Variation Ratio fields in the all-policy batch summary.

Native Windows double-click execution of `.bat` is environment-specific and is distinct from this Python-level CI verification.

## Safe empirical conclusion

The frozen UCI3 mechanism baseline does not identify a universal best policy. A safe summary is:

\[
\boxed{
Policy^*=f(Dataset,Rule\ Structure,Conflict\ Workload,Client\ Configuration)
}
\]

The current results are descriptive/mechanistic until repeated paired runs support formal statistical inference.

## References

- Bazan, J. G., Nguyen, H. S., Nguyen, S. H., Synak, P., & Wróblewski, J. (2000). *Rough Set Algorithms in Classification Problem*. https://doi.org/10.1007/978-3-7908-1840-6_3
- Brodersen, K. H., Ong, C. S., Stephan, K. E., & Buhmann, J. M. (2010). *The Balanced Accuracy and Its Posterior Distribution*. https://doi.org/10.1109/ICPR.2010.764
- Demšar, J. (2006). *Statistical Comparisons of Classifiers over Multiple Data Sets*. *Journal of Machine Learning Research, 7*, 1–30.
- Gal, Y. (2016). *Uncertainty in Deep Learning*. PhD thesis, University of Cambridge, §3.3.1, Eq. (3.19).
- Lazo-Cortés, M. S., Martínez-Trinidad, J. F., Carrasco-Ochoa, J. A., & Almanza-Ortega, N. N. (2020). *Towards Selecting Reducts for Building Decision Rules for Rule-Based Classifiers*. https://doi.org/10.1007/978-3-030-49076-8_7
- Lindgren, T. (2004). *Methods for Rule Conflict Resolution*. https://doi.org/10.1007/978-3-540-30115-8_26
- Lindgren, T., & Boström, H. (2002). *Classification with Intersecting Rules*. https://doi.org/10.1007/3-540-36169-3_31
- Sokolova, M., & Lapalme, G. (2009). *A systematic analysis of performance measures for classification tasks*. https://doi.org/10.1016/j.ipm.2009.03.002
- Woźniak, K., Sousa, J., & Śnieżyński, B. (2026). *Rule-Based Federated Learning for Healthcare*. https://doi.org/10.1007/978-3-032-29921-5_38
