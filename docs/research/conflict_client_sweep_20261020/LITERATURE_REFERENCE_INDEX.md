# Literature Reference Index

This index separates four literature lanes used by the Federated LEM2 research package: source architecture, Prediction Policies, rule conflict, and established evaluation/statistical methods.

## 1. Federated LEM2 source architecture

**Woźniak, K., Sousa, J., & Śnieżyński, B. (2026). _Rule-Based Federated Learning for Healthcare_.**

- DOI: https://doi.org/10.1007/978-3-032-29921-5_38
- Used for: federated discretization, local rule induction, UNION aggregation, first-match inference, `C ∈ {2,3,4,5}`, Balanced Accuracy, Coverage, ruleset size, conditions per rule, and pairwise Jaccard.

## 2. Prediction Policies

### FIRST_MATCH

Woźniak et al. (2026), above.

### SIMPLE_VOTING / STANDARD_VOTING

**Lazo-Cortés, M. S., Martínez-Trinidad, J. F., Carrasco-Ochoa, J. A., & Almanza-Ortega, N. N. (2020). _Towards Selecting Reducts for Building Decision Rules for Rule-Based Classifiers_.**

- DOI: https://doi.org/10.1007/978-3-030-49076-8_7
- Used for: RSES-style Simple Voting and Standard Voting principles.

### GLOBAL_STRENGTH

**Bazan, J. G., Nguyen, H. S., Nguyen, S. H., Synak, P., & Wróblewski, J. (2000). _Rough Set Algorithms in Classification Problem_.**

- DOI: https://doi.org/10.1007/978-3-7908-1840-6_3
- Used for: GlobalStrength / unique class-consistent support coverage normalized by class size.

## 3. Rule conflict

**Lindgren, T. (2004). _Methods for Rule Conflict Resolution_.**

- DOI: https://doi.org/10.1007/978-3-540-30115-8_26
- Used for: the established definition that conflict occurs when two or more rules cover the same example but predict different classes.

**Lindgren, T., & Boström, H. (2002). _Classification with Intersecting Rules_.**

- DOI: https://doi.org/10.1007/3-540-36169-3_31
- Used for: overlapping/intersecting rules and class prediction under competing rule coverage.

## 4. Established evaluation metrics

### Balanced Accuracy

**Brodersen, K. H., Ong, C. S., Stephan, K. E., & Buhmann, J. M. (2010). _The Balanced Accuracy and Its Posterior Distribution_.**

- DOI: https://doi.org/10.1109/ICPR.2010.764
- Used for: theoretical support for Balanced Accuracy under class imbalance.

Healthcare source paper also explicitly selects Balanced Accuracy as its primary metric.

### Macro-F1 / classification performance measures

**Sokolova, M., & Lapalme, G. (2009). _A systematic analysis of performance measures for classification tasks_. _Information Processing & Management, 45_(4), 427–437.**

- DOI: https://doi.org/10.1016/j.ipm.2009.03.002
- Used for: established precision / recall / F-score evaluation framework across classification tasks.

### Variation Ratio

**Gal, Y. (2016). _Uncertainty in Deep Learning_. PhD thesis, University of Cambridge.**

- Source: https://www.cs.ox.ac.uk/people/yarin.gal/website/thesis/thesis.pdf
- Relevant location: §3.3.1, Eq. (3.19).
- Formula: `VR(x) = 1 - f_x / T`.
- Used for: categorical prediction dispersion across client-order predictions.
- Gal explicitly attributes variation ratios to Freeman (1965).

### Statistical comparison of multiple classifiers / policies

**Demšar, J. (2006). _Statistical Comparisons of Classifiers over Multiple Data Sets_. _Journal of Machine Learning Research, 7_, 1–30.**

- Source: https://www.jmlr.org/papers/v7/demsar06a.html
- Used for: Wilcoxon signed-rank comparison of two classifiers and Friedman + post-hoc comparison of multiple classifiers over multiple data sets / blocks.

Healthcare source paper also uses paired Wilcoxon signed-rank tests across repeated data splits.

## 5. Evaluation-document entry point

See:

`TEAM_EVALUATION_METRICS_ESTABLISHED.md`

for each metric's formula, interpretation, exact code mapping, and citation.
