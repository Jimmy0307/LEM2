# Module 06 — Evaluation（既有理論指標版）

## 目的

在固定 local rules、global rules 與同一 conflict set 下，只替換 **Prediction Policy**，並使用既有分類、rule-conflict、uncertainty/disagreement 與統計比較方法評估結果。

本版不再把專案內自訂名稱 `CRA / CCR / OSR / H_rule` 當主要指標。舊欄位只保留 backward compatibility。

```text
同一 RuleSystemArtifact
        ↓
同一 global rules / 同一 conflict set
        ↓
只替換 Prediction Policy
        ↓
既有 metrics / statistics
```

完整公式、code 與 citation 對照見：

`../TEAM_EVALUATION_METRICS_ESTABLISHED.md`

---

# 1. Balanced Accuracy

\[
Recall_k=\frac{TP_k}{TP_k+FN_k}
\]

\[
\boxed{BA=\frac1K\sum_{k=1}^{K}Recall_k}
\]

**涵義**：各 class recall 等權；適合 class imbalance。Healthcare source paper 直接將 Balanced Accuracy 設為 primary metric（Woźniak et al., 2026, §4.3）；更一般的 balanced-accuracy 理論可參考 Brodersen et al. (2010)。

**Code**：`roughset/evaluation.py::balanced_accuracy`

```python
for cls in pd.unique(y_true):
    mask = y_true == cls
    if mask.sum():
        recalls.append(float((y_pred[mask] == cls).mean()))
return float(np.mean(recalls)) if recalls else 0.0
```

**Citations**：

- Woźniak et al. (2026): https://doi.org/10.1007/978-3-032-29921-5_38
- Brodersen et al. (2010): https://doi.org/10.1109/ICPR.2010.764

---

# 2. Macro-F1

\[
Precision_k=\frac{TP_k}{TP_k+FP_k}
\]

\[
Recall_k=\frac{TP_k}{TP_k+FN_k}
\]

\[
F1_k=\frac{2Precision_kRecall_k}{Precision_k+Recall_k}
\]

\[
\boxed{MacroF1=\frac1K\sum_kF1_k}
\]

**涵義**：每個 class 等權，且同時考慮 precision 與 recall；作為 BA 的 secondary metric（Sokolova & Lapalme, 2009）。

**Code**：`roughset/evaluation.py::macro_f1_score`

**Citation**：https://doi.org/10.1016/j.ipm.2009.03.002

---

# 3. Coverage

令：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

\[
\boxed{Coverage=\frac{|\{x:M(x)\neq\emptyset\}|}{N_{test}}}
\]

**涵義**：多少 test cases 至少被一條 explicit rule 處理，而不是使用 default class。Healthcare source paper 在 §4.3 直接使用此定義（Woźniak et al., 2026）。

**Code**：`roughset/evaluation.py::evaluate_rule_model`

```python
"coverage": float(np.mean([len(x) > 0 for x in matched])) if len(test) else 0.0
```

**Citation**：https://doi.org/10.1007/978-3-032-29921-5_38

---

# 4. Ruleset size / Conditions per rule

\[
\boxed{|R_G|}
\]

\[
\boxed{\overline L=\frac1{|R_G|}\sum_{j=1}^{|R_G|}L_j}
\]

**涵義**：前者衡量 ruleset 規模；後者衡量 rule complexity / specificity。兩者都是 Healthcare source paper 的 interpretability measures（Woźniak et al., 2026, §4.3）。

**Code**：`roughset/pipeline.py::_rule_condition_summary`

```python
counts = [len(rule.conditions) for rule in rules]
"rule_count": len(counts)
"average_condition_count": float(np.mean(counts))
```

**Citation**：https://doi.org/10.1007/978-3-032-29921-5_38

---

# 5. Pairwise Jaccard similarity

\[
\boxed{J(R_i,R_j)=\frac{|R_i\cap R_j|}{|R_i\cup R_j|}}
\]

Healthcare source paper 以 sorted rule conditions 作 set elements，計算 pairwise Jaccard 並對 client pairs 平均（Woźniak et al., 2026, Eq. 5）。

**正式主分析**：`pairwise_jaccard_antecedent`。

**不再以** \(H_{rule}=1-J\) **作新主要 metric**。

**Code**：`roughset/evaluation.py::_jaccard` 與 `pairwise_rule_jaccard`。

**Citation**：https://doi.org/10.1007/978-3-032-29921-5_38

---

# 6. Conflict set

Lindgren (2004) 對 rule conflict 的核心定義：兩條或更多 rules cover 同一 example，但 predict different classes。

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

\[
\boxed{\mathcal C=\{x:|\{d_r:r\in M(x)\}|>1\}}
\]

正式只報：

\[
\boxed{|\mathcal C|}
\]

與普通比例：

\[
\boxed{\frac{|\mathcal C|}{N_{test}}}
\]

不要再把比例包裝成新的 `CCR`。

**Code**：`roughset/pipeline.py::_pre_resolution_conflicts`

```python
matched = matching_rules(row, rules)
decisions = sorted({str(rule.decision) for rule in matched})
is_conflict = len(decisions) > 1
```

**Citations**：

- Lindgren (2004): https://doi.org/10.1007/978-3-540-30115-8_26
- Lindgren & Boström (2002): https://doi.org/10.1007/3-540-36169-3_31

---

# 7. Performance restricted to the conflict set

不再把 `Conflict Resolution Accuracy (CRA)` 當主要新 metric。

直接計算：

\[
\boxed{BA_{\mathcal C}}
\]

與：

\[
\boxed{MacroF1_{\mathcal C}}
\]

**涵義**：standard classification metrics conditioned on the established conflict set。

**Code**：`roughset/pipeline.py::evaluate_resolvers`

```python
flags = np.asarray(artifact.pre_resolution_conflict_flags, dtype=bool)
y_true = artifact.test[artifact.target].astype(str).to_numpy()[flags]
y_pred = np.asarray(metrics["predictions"], dtype=object)[flags]

conflict_ba = balanced_accuracy(y_true, y_pred)
conflict_f1 = macro_f1_score(y_true, y_pred)
```

現有欄位：

```text
conflict_balanced_accuracy
conflict_macro_f1
```

**Citations**：Lindgren (2004) + Brodersen et al. (2010) + Sokolova & Lapalme (2009)。

---

# 8. FIRST_MATCH client-order disagreement — Variation Ratio

對固定 case \(x\) 的 \(T\) 個 client-order predictions，令 modal class 出現次數為：

\[
f_x=\max_d\sum_{t=1}^{T}I[\hat y_{\pi_t}(x)=d]
\]

則：

\[
\boxed{VR(x)=1-\frac{f_x}{T}}
\]

Gal (2016, Eq. 3.19) 明確以此 variation ratio 衡量 categorical prediction dispersion，並引用 Freeman (1965)。

**涵義**：

- \(VR=0\)：所有 client orders 完全一致。
- 越高：client arrival order 對 prediction 的影響越大。

**Code — 已補上**：`roughset/established_metrics.py`

```python
counts = Counter(matrix[:, case_idx].tolist())
modal_frequency = max(counts.values()) if counts else 0
ratios.append(1.0 - (modal_frequency / n_orders))
```

主要 functions：

```text
variation_ratio_by_case
mean_variation_ratio
audit_order_variation_ratio
```

舊 `order_sensitivity_rate` 保留 legacy compatibility，但不再作正式主分析。

**Citation**：Gal, Y. (2016), §3.3.1, Eq. (3.19): https://www.cs.ox.ac.uk/people/yarin.gal/website/thesis/thesis.pdf

---

# 9. Performance distribution across client permutations

每個 client order \(\pi\) 都得到：

\[
BA_\pi
\]

報普通描述統計：

\[
\boxed{Mean,\ SD,\ Min,\ Max}
\]

**Code**：`roughset/federated.py::audit_order_distribution`。

這不是新 metric，而是標準 BA 在 controlled client-order permutations 下的 distribution。

---

# 10. 四種 Prediction Policies 的正式統計比較

目前 UCI3 frozen evidence 只有單一 holdout seed 42，因此現在只能作 descriptive comparison，不能宣稱 statistical significance。

Repeated splits / seeds 完成後，依 Demšar (2006)：

- 兩個 policies：paired Wilcoxon signed-rank test。
- 四個 policies：Friedman omnibus test + post-hoc multiple comparisons。

Healthcare source paper 本身也使用 paired Wilcoxon signed-rank test，\(\alpha=0.05\)，並以 5 random splits 作 paired comparisons（Woźniak et al., 2026, §4.3）。

**Citations**：

- Demšar (2006): https://www.jmlr.org/papers/v7/demsar06a.html
- Woźniak et al. (2026): https://doi.org/10.1007/978-3-032-29921-5_38

---

# 11. Fair comparison matrix

對每個 dataset、每個 \(C\)：

| 固定項 | 是否固定 |
|---|---|
| Train/test split | 是 |
| Client partition | 是 |
| Local LEM2 rules | 是 |
| Global UNION rules | 是 |
| Conflict set \(\mathcal C\) | 是 |
| Default class | 是 |
| Prediction Policy | **唯一主要替換項** |

所以 performance difference 才能合理歸因於 Prediction Policy，而不是重新學習出不同 rule systems。

---

# 12. Legacy → formal mapping

| Legacy 欄位 | 正式寫作定位 |
|---|---|
| `conflict_case_rate` | conflict-set proportion |
| `conflict_resolution_accuracy` | supplementary；主要改報 \(BA_{\mathcal C}\) / \(MacroF1_{\mathcal C}\) |
| `order_sensitivity_rate` | legacy binary diagnostic；正式改 VR |
| `rule_heterogeneity` | supplementary；主分析直接報 Jaccard |
| `disagreement_vs_first_match` | supplementary behavior analysis |
| `exact_conflict_antecedent_rate` | supplementary structural audit |

---

# References

1. Woźniak, K., Sousa, J., & Śnieżyński, B. (2026). *Rule-Based Federated Learning for Healthcare*. https://doi.org/10.1007/978-3-032-29921-5_38
2. Brodersen, K. H., Ong, C. S., Stephan, K. E., & Buhmann, J. M. (2010). *The Balanced Accuracy and Its Posterior Distribution*. https://doi.org/10.1109/ICPR.2010.764
3. Sokolova, M., & Lapalme, G. (2009). *A systematic analysis of performance measures for classification tasks*. https://doi.org/10.1016/j.ipm.2009.03.002
4. Lindgren, T. (2004). *Methods for Rule Conflict Resolution*. https://doi.org/10.1007/978-3-540-30115-8_26
5. Lindgren, T., & Boström, H. (2002). *Classification with Intersecting Rules*. https://doi.org/10.1007/3-540-36169-3_31
6. Gal, Y. (2016). *Uncertainty in Deep Learning*. https://www.cs.ox.ac.uk/people/yarin.gal/website/thesis/thesis.pdf
7. Demšar, J. (2006). *Statistical Comparisons of Classifiers over Multiple Data Sets*. *JMLR, 7*, 1–30. https://www.jmlr.org/papers/v7/demsar06a.html
