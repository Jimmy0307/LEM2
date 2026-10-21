# 組員討論版：既有 Evaluation Metrics × Formula × Meaning × Code × Citation

> 原則：正式研究只使用已有理論與已有分類／統計評量。專案先前自訂的 `CRA / CCR / OSR / H_rule` 不再作主要指標；舊欄位只保留相容性與補充分析。
>
> Citation 原則：每一個正式 metric 都要能指出既有來源；若只是把既有 metric 套到 conflict subset，必須明寫「conditional evaluation」，不要假裝是新指標。

---

# 1. 正式評量架構

| 研究問題 | 正式方法 | 主要來源 |
|---|---|---|
| 整體分類品質 | Balanced Accuracy | Woźniak et al. (2026); Brodersen et al. (2010) |
| Precision / Recall 是否兼顧 | Macro-F1 | Sokolova & Lapalme (2009) |
| Explicit rules 能覆蓋多少 test cases | Coverage | Woźniak et al. (2026), §4.3 |
| Rule base 大小 | Ruleset size | Woźniak et al. (2026), §4.3 |
| Rule 複雜度 | Mean conditions per rule | Woźniak et al. (2026), §4.3 |
| Client rulesets 相似度 | Pairwise Jaccard | Woźniak et al. (2026), Eq. (5) |
| 哪些 test cases 發生 rule conflict | Conflict set | Lindgren (2004) |
| Conflict cases 上分類品質 | BA / Macro-F1 restricted to conflict set | 既有 BA / F1 + Lindgren conflict set |
| FIRST_MATCH 對 client order 的 prediction disagreement | Variation Ratio | Gal (2016), Eq. (3.19), citing Freeman (1965) |
| 四個 Prediction Policies 是否有顯著差異 | Friedman + post-hoc；paired Wilcoxon | Demšar (2006); Woźniak et al. (2026) |

---

# 2. Balanced Accuracy

對第 \(k\) 類：

\[
Recall_k=\frac{TP_k}{TP_k+FN_k}
\]

若共有 \(K\) 個 classes：

\[
\boxed{BA=\frac1K\sum_{k=1}^{K}Recall_k}
\]

## 涵義

每個 class 的 recall 具有相同權重，因此比 raw accuracy 更不容易被 majority class 支配。Healthcare source paper 明確以 Balanced Accuracy 作為 primary metric，原因是多數資料集存在 class imbalance（Woźniak et al., 2026, §4.3）。Brodersen et al. (2010) 也專門討論 balanced accuracy 在不平衡資料下的評估意義。

## Code

`roughset/evaluation.py::balanced_accuracy`

```python
def balanced_accuracy(y_true, y_pred) -> float:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    recalls = []

    for cls in pd.unique(y_true):
        mask = y_true == cls
        if mask.sum():
            recalls.append(float((y_pred[mask] == cls).mean()))

    return float(np.mean(recalls)) if recalls else 0.0
```

## Citation

- Woźniak, K., Sousa, J., & Śnieżyński, B. (2026). *Rule-Based Federated Learning for Healthcare*. https://doi.org/10.1007/978-3-032-29921-5_38
- Brodersen, K. H., Ong, C. S., Stephan, K. E., & Buhmann, J. M. (2010). *The Balanced Accuracy and Its Posterior Distribution*. https://doi.org/10.1109/ICPR.2010.764

---

# 3. Macro-F1

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
\boxed{MacroF1=\frac1K\sum_{k=1}^{K}F1_k}
\]

## 涵義

Balanced Accuracy 主要反映各 class 的 recall；Macro-F1 同時納入 precision 與 recall，並讓各 class 等權平均。這使它適合作為 BA 的 secondary classification metric，而不是取代 BA（Sokolova & Lapalme, 2009）。

## Code

`roughset/evaluation.py::macro_f1_score`

```python
for cls in classes:
    tp = int(np.sum((y_true == cls) & (y_pred == cls)))
    fp = int(np.sum((y_true != cls) & (y_pred == cls)))
    fn = int(np.sum((y_true == cls) & (y_pred != cls)))

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )
    scores.append(f1)

return float(np.mean(scores))
```

## Citation

- Sokolova, M., & Lapalme, G. (2009). *A systematic analysis of performance measures for classification tasks*. *Information Processing & Management, 45*(4), 427–437. https://doi.org/10.1016/j.ipm.2009.03.002

---

# 4. Coverage

令：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

則：

\[
\boxed{Coverage=\frac{|\{x\in U_{test}:M(x)\neq\emptyset\}|}{|U_{test}|}}
\]

## 涵義

代表多少 test cases 至少被一條 explicit rule match，而不是直接落到 default class。Healthcare paper 在 §4.3 明確把 coverage 定義為「matched a rule other than the default rule 的 test cases 比例」（Woźniak et al., 2026）。

## Code

`roughset/evaluation.py::evaluate_rule_model`

```python
"coverage": (
    float(np.mean([len(x) > 0 for x in matched]))
    if len(test)
    else 0.0
)
```

## Citation

- Woźniak et al. (2026), §4.3. https://doi.org/10.1007/978-3-032-29921-5_38

---

# 5. Ruleset size / Mean conditions per rule

Ruleset size：

\[
\boxed{|R_G|}
\]

Mean conditions per rule：

\[
\boxed{\overline L=\frac1{|R_G|}\sum_{j=1}^{|R_G|}L_j}
\]

其中 \(L_j\) 為第 \(j\) 條 rule 的 antecedent condition 數量。

## 涵義

- Ruleset size：global rule base 的規模。
- Mean conditions per rule：平均 rule complexity / specificity。

Healthcare paper 把 ruleset size 與 average number of conditions per rule 作為 global ruleset interpretability 的正式評量（Woźniak et al., 2026, §4.3）。

## Code

`roughset/pipeline.py::_rule_condition_summary`

```python
counts = [len(rule.conditions) for rule in rules]

return {
    "rule_count": len(counts),
    "average_condition_count": float(np.mean(counts)),
    "median_condition_count": float(np.median(counts)),
    "min_condition_count": int(min(counts)),
    "max_condition_count": int(max(counts)),
}
```

## Citation

- Woźniak et al. (2026), §4.3. https://doi.org/10.1007/978-3-032-29921-5_38

---

# 6. Pairwise Jaccard similarity

對 clients \(i,j\) 的 local rulesets：

\[
\boxed{J(R_i,R_j)=\frac{|R_i\cap R_j|}{|R_i\cup R_j|}}
\]

## 涵義

- \(J=1\)：兩 clients 的 rulesets 完全相同。
- \(J=0\)：沒有共同 rules。
- 越低表示 local rulesets 越不相似。

Healthcare paper 將 rules 視為 sorted conditions 的 set elements，計算 pairwise Jaccard 後再對 client pairs 平均（Woźniak et al., 2026, Eq. 5）。因此正式主分析優先使用 antecedent-only Jaccard。

不要再把：

\[
H_{rule}=1-J
\]

包裝成新的主要 metric。

## Code

`roughset/evaluation.py::_jaccard`

```python
def _jaccard(set_a, set_b) -> float:
    union = set_a | set_b
    if not union:
        return float("nan")
    return float(len(set_a & set_b) / len(union))
```

`roughset/evaluation.py::pairwise_rule_jaccard`

```python
ant_a = {rule_antecedent_signature(r) for r in local_rules[a]}
ant_b = {rule_antecedent_signature(r) for r in local_rules[b]}

"jaccard_antecedent": _jaccard(ant_a, ant_b)
```

## Citation

- Woźniak et al. (2026), Eq. (5). https://doi.org/10.1007/978-3-032-29921-5_38

---

# 7. Conflict set

Lindgren (2004) 對 unordered rule sets 的 conflict 核心定義是：兩條或更多 rules cover 同一個 example，但 predict different classes。

令：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

則 conflict set：

\[
\boxed{\mathcal C=\{x\in U_{test}:|\{d_r:r\in M(x)\}|>1\}}
\]

## 正式報告

只報：

\[
\boxed{|\mathcal C|}
\]

與普通描述比例：

\[
\boxed{\frac{|\mathcal C|}{|U_{test}|}}
\]

不要再創新的 `CCR` 名稱。

## 涵義

這代表 Prediction Policy 真正遇到 competing decision rules 的 workload。

## Code

`roughset/pipeline.py::_pre_resolution_conflicts`

```python
matched = matching_rules(row, rules)
decisions = sorted({str(rule.decision) for rule in matched})
is_conflict = len(decisions) > 1
```

現有輸出：

```python
"conflict_cases_count": conflict_count,
"pre_resolution_conflict_case_rate": (
    conflict_count / total if total else float("nan")
)
```

欄位名稱可保留相容性；manuscript 只稱為 **conflict-set count / proportion**。

## Citation

- Lindgren, T. (2004). *Methods for Rule Conflict Resolution*. In *ECML 2004*, LNCS 3201, 262–273. https://doi.org/10.1007/978-3-540-30115-8_26
- Lindgren, T., & Boström, H. (2002). *Classification with Intersecting Rules*. https://doi.org/10.1007/3-540-36169-3_31

---

# 8. BA / Macro-F1 on the conflict set

不再使用自訂名稱 `Conflict Resolution Accuracy (CRA)` 作主要結果。

直接將既有標準 metrics 限制在 Lindgren-defined conflict set \(\mathcal C\)：

\[
\boxed{BA_{\mathcal C}}
\]

\[
\boxed{MacroF1_{\mathcal C}}
\]

## 涵義

回答：**真正發生 competing-rule conflict 時，哪個 Prediction Policy 的分類品質較好？**

這不是新的 metric；它只是 standard BA / Macro-F1 的 conditional evaluation。

## Code

`roughset/pipeline.py::evaluate_resolvers`

```python
flags = np.asarray(
    artifact.pre_resolution_conflict_flags,
    dtype=bool,
)

y_true = artifact.test[artifact.target].astype(str).to_numpy()[flags]
y_pred = np.asarray(metrics["predictions"], dtype=object)[flags]

conflict_ba = balanced_accuracy(y_true, y_pred)
conflict_f1 = macro_f1_score(y_true, y_pred)
```

現有輸出鍵：

```text
conflict_balanced_accuracy
conflict_macro_f1
```

## Citation

- Conflict subset 定義：Lindgren (2004), https://doi.org/10.1007/978-3-540-30115-8_26
- BA：Brodersen et al. (2010), https://doi.org/10.1109/ICPR.2010.764
- Macro-F1 / classification-measure framework：Sokolova & Lapalme (2009), https://doi.org/10.1016/j.ipm.2009.03.002

---

# 9. FIRST_MATCH client-order disagreement — Variation Ratio

對固定 test case \(x\)，假設檢查 \(T\) 種 client-order predictions：

\[
\hat y_{\pi_1}(x),\ldots,\hat y_{\pi_T}(x)
\]

modal predicted class 的出現次數：

\[
f_x=\max_d\sum_{t=1}^{T}I[\hat y_{\pi_t}(x)=d]
\]

Variation Ratio：

\[
\boxed{VR(x)=1-\frac{f_x}{T}}
\]

整體只做普通摘要平均：

\[
\boxed{\overline{VR}=\frac1N\sum_xVR(x)}
\]

## 涵義

- \(VR=0\)：所有 client orders 都產生同一個 prediction。
- 值越大：categorical predictions 對 client arrival order 越缺乏 consensus。

Gal (2016, Eq. 3.19) 明確使用 \(1-f_x/T\) 的 variation ratio，並將來源追溯至 Freeman (1965)。我們不是提出新 disagreement metric，而是把既有 categorical dispersion measure 套用到 client-order predictions。

## Code — 已補上

`roughset/established_metrics.py::variation_ratio_by_case`

```python
def variation_ratio_by_case(predictions_by_order):
    matrix = np.asarray(predictions_by_order, dtype=object)
    ...
    n_orders = matrix.shape[0]
    ratios = []

    for case_idx in range(matrix.shape[1]):
        counts = Counter(matrix[:, case_idx].tolist())
        modal_frequency = max(counts.values()) if counts else 0
        ratios.append(1.0 - (modal_frequency / n_orders))

    return np.asarray(ratios, dtype=float)
```

`roughset/established_metrics.py::audit_order_variation_ratio` 會使用與既有 client-order audit 相同的 permutations，對同一 learned local rule sets 重排後取得 prediction matrix，再計算 VR。

主要輸出：

```text
variation_ratio_by_case
mean_variation_ratio
mean_variation_ratio_conflict
orderings_checked
```

其中 `mean_variation_ratio_conflict` 只是把同一個 VR 限制在已固定的 conflict set 上取平均，不是新的 metric。

## Citation

- Gal, Y. (2016). *Uncertainty in Deep Learning*. PhD thesis, University of Cambridge, §3.3.1, Eq. (3.19). https://www.cs.ox.ac.uk/people/yarin.gal/website/thesis/thesis.pdf
- Gal (2016) 將 variation ratios 的原始來源標為 Freeman (1965)。

---

# 10. BA distribution across client permutations

每個 client order \(\pi\) 各自得到：

\[
BA_{\pi}
\]

正式報普通描述統計：

\[
\boxed{Mean,\ SD,\ Min,\ Max}
\]

## 涵義

Variation Ratio 看 individual predictions 的 categorical disagreement；BA distribution 看整體 predictive performance 對 client order 的敏感程度。

## Code

`roughset/federated.py::audit_order_distribution`

```python
rows.append({
    "client_order": " -> ".join(order),
    "balanced_accuracy": metrics["balanced_accuracy"],
    "macro_f1": metrics["macro_f1"],
    "coverage": metrics["coverage"],
})
```

後續 `_finite_summary` 產生 mean / std / min / max。

這裡沒有創新 metric，只是 standard performance metric 在 controlled permutations 下的 descriptive distribution。

---

# 11. 四個 Prediction Policies 的統計比較

目前 frozen UCI3 evidence 只有單一 holdout seed 42，因此目前只能做 **descriptive comparison**，不能宣稱 statistical significance。

正式 publication phase 必須先建立 repeated splits / seeds，再使用 Demšar (2006) 建議的 non-parametric classifier-comparison framework。

## Friedman test

對 \(k\) 個 classifiers / policies 與 \(N\) 個比較 blocks：

\[
\boxed{
\chi_F^2=
\frac{12N}{k(k+1)}
\left[
\sum_{j=1}^{k}R_j^2-
\frac{k(k+1)^2}{4}
\right]
}
\]

本研究：

\[
k=4
\]

對應四個 Prediction Policies。

若 omnibus test 顯著，再做 post-hoc pairwise comparisons 並進行 multiple-comparison correction。

## Wilcoxon signed-rank

兩個 policies 的 paired comparison：

\[
d_i=s_i^{(A)}-s_i^{(B)}
\]

對非零 \(|d_i|\) 排 rank，再比較正負 signed ranks。

Healthcare source paper 本身也使用 paired Wilcoxon signed-rank test，\(\alpha=0.05\)，並在 5 random splits 上比較模型版本（Woźniak et al., 2026, §4.3）。

## Code 狀態

目前 repo **尚未執行** Friedman / Wilcoxon publication test，因為 repeated experimental blocks 尚未建立完整。這不是缺失性 bug；若現在用單一 seed 直接做 significance test，反而是方法錯誤。

## Citation

- Demšar, J. (2006). *Statistical Comparisons of Classifiers over Multiple Data Sets*. *Journal of Machine Learning Research, 7*, 1–30. https://www.jmlr.org/papers/v7/demsar06a.html
- Woźniak et al. (2026), §4.3. https://doi.org/10.1007/978-3-032-29921-5_38

---

# 12. Legacy 欄位如何處理

| 舊名稱 | 正式定位 |
|---|---|
| `conflict_case_rate` | conflict-set proportion（普通描述比例） |
| `conflict_resolution_accuracy` | legacy；主結果改用 \(BA_{\mathcal C}\) / \(MacroF1_{\mathcal C}\) |
| `order_sensitivity_rate` | legacy binary diagnostic；正式主分析改 Variation Ratio |
| `order_sensitivity_conflict_rate` | legacy supplementary |
| `rule_heterogeneity = 1-J` | 不作主結果；直接報 Jaccard |
| `disagreement_vs_first_match` | supplementary behavior analysis |
| `exact_conflict_antecedent_rate` | supplementary structural audit |

---

# 13. 正式結果表應保留的欄位

每個 dataset × client count × Prediction Policy：

```text
Balanced Accuracy
Macro-F1
Coverage
Ruleset Size
Mean Conditions per Rule
Mean Pairwise Antecedent Jaccard
Conflict Set Count
Conflict Set Proportion
Balanced Accuracy on Conflict Set
Macro-F1 on Conflict Set
```

FIRST_MATCH 額外：

```text
Mean Variation Ratio
Variation Ratio by Case（supplementary / audit）
BA across client permutations: Mean / SD / Min / Max
```

Repeated experiments 完成後才增加：

```text
Friedman + post-hoc
Paired Wilcoxon
```

---

# 14. References

1. Woźniak, K., Sousa, J., & Śnieżyński, B. (2026). *Rule-Based Federated Learning for Healthcare*. In *Computational Science – ICCS 2026*, LNCS 16783, 563–578. https://doi.org/10.1007/978-3-032-29921-5_38
2. Brodersen, K. H., Ong, C. S., Stephan, K. E., & Buhmann, J. M. (2010). *The Balanced Accuracy and Its Posterior Distribution*. In *2010 20th International Conference on Pattern Recognition*, 3121–3124. https://doi.org/10.1109/ICPR.2010.764
3. Sokolova, M., & Lapalme, G. (2009). *A systematic analysis of performance measures for classification tasks*. *Information Processing & Management, 45*(4), 427–437. https://doi.org/10.1016/j.ipm.2009.03.002
4. Lindgren, T. (2004). *Methods for Rule Conflict Resolution*. In *Machine Learning: ECML 2004*, LNCS 3201, 262–273. https://doi.org/10.1007/978-3-540-30115-8_26
5. Lindgren, T., & Boström, H. (2002). *Classification with Intersecting Rules*. https://doi.org/10.1007/3-540-36169-3_31
6. Gal, Y. (2016). *Uncertainty in Deep Learning*. PhD thesis, University of Cambridge. https://www.cs.ox.ac.uk/people/yarin.gal/website/thesis/thesis.pdf
7. Demšar, J. (2006). *Statistical Comparisons of Classifiers over Multiple Data Sets*. *Journal of Machine Learning Research, 7*, 1–30. https://www.jmlr.org/papers/v7/demsar06a.html
