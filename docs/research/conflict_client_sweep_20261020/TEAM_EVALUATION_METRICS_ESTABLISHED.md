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

每個 class 的 recall 具有相同權重，因此比 raw accuracy 更不容易被 majority class 支配。Healthcare source paper 明確以 Balanced Accuracy 作為 primary metric，原因是多數資料集存在 class imbalance（Woźniak et al., 2026, §4.3）。Brodersen et al. (2010) 也專門討論 balanced accuracy 的理論與 posterior distribution。

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

Balanced Accuracy 主要反映各 class recall；Macro-F1 同時受到 precision 與 recall 影響，而且每個 class 等權平均。

所以 BA winner 與 Macro-F1 winner 不同並不矛盾，代表兩個方法在 false positives / false negatives 與各 class recall 上的 trade-off 不同。

## Code

`roughset/evaluation.py::macro_f1_score`

```python
def macro_f1_score(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=object)
    y_pred = np.asarray(y_pred, dtype=object)
    classes = sorted(set(y_true.tolist()) | set(y_pred.tolist()), key=str)

    scores = []
    for cls in classes:
        tp = int(np.sum((y_true == cls) & (y_pred == cls)))
        fp = int(np.sum((y_true != cls) & (y_pred == cls)))
        fn = int(np.sum((y_true == cls) & (y_pred != cls)))
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        scores.append(f1)

    return float(np.mean(scores))
```

## Citation

- Sokolova, M., & Lapalme, G. (2009). *A systematic analysis of performance measures for classification tasks*. *Information Processing & Management, 45*(4), 427–437. https://doi.org/10.1016/j.ipm.2009.03.002

---

# 4. Accuracy — 只作直觀補充

\[
\boxed{Accuracy=\frac1N\sum_{i=1}^{N}I(\hat y_i=y_i)}
\]

## 涵義

整體答對比例容易閱讀，但 class imbalance 時可能被 majority class 支配，所以本研究不把 Accuracy 當主要 winner criterion。

## Code

`roughset/evaluation.py::classification_accuracy`

```python
def classification_accuracy(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=object)
    y_pred = np.asarray(y_pred, dtype=object)
    if len(y_true) == 0:
        return 0.0
    return float(np.mean(y_true == y_pred))
```

---

# 5. Rule-system structure / interpretability

## 5.1 Ruleset size

\[
\boxed{|R_G|}
\]

### 涵義

Global ruleset 的規則總數。較少代表模型較 compact；較多代表可以表達更多局部 patterns，但人工檢視成本也較高。

### Code

`roughset/pipeline.py::_rule_condition_summary`

```python
counts = [len(rule.conditions) for rule in rules]
return {
    "rule_count": len(counts),
    "average_condition_count": float(np.mean(counts)),
    ...
}
```

### Citation

- Woźniak et al. (2026), evaluation framework, DOI `10.1007/978-3-032-29921-5_38`.

## 5.2 Mean conditions per rule

若第 \(j\) 條 rule 有 \(L_j\) 個 antecedent conditions：

\[
\boxed{\bar L=\frac1{|R_G|}\sum_{j=1}^{|R_G|}L_j}
\]

### 涵義

衡量 rule complexity / specificity。平均條件越少，規則通常越 general；條件越多則越 specific。

### Code

```python
counts = [len(rule.conditions) for rule in rules]
"average_condition_count": float(np.mean(counts))
```

### Citation

- Woźniak et al. (2026), §4.3.

---

# 6. Coverage

令：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

則：

\[
\boxed{Coverage=\frac{|\{x\in U_{test}:M(x)\neq\emptyset\}|}{|U_{test}|}}
\]

## 涵義

表示多少 test cases 能被至少一條 explicit rule 處理，而不是落到 default class。它不是 correctness metric。

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

- Woźniak et al. (2026), §4.3, DOI `10.1007/978-3-032-29921-5_38`.

---

# 7. Pairwise Jaccard

對 Client \(i,j\) 的 rule sets：

\[
\boxed{J(R_i,R_j)=\frac{|R_i\cap R_j|}{|R_i\cup R_j|}}
\]

## 涵義

- \(J=1\)：完全相同。
- \(J=0\)：完全無共同 rule signatures。
- 數值越低：client rulesets 越不同。

正式主分析使用 source-paper-compatible antecedent signature；full-rule Jaccard 可留作 supplementary conflict analysis。不要再另立 \(H_{rule}=1-\bar J\) 作主指標。

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

- Woźniak et al. (2026), Eq. (5), DOI `10.1007/978-3-032-29921-5_38`.

---

# 8. Conflict set

Lindgren (2004) 的 rule-conflict 核心是：兩條或更多 rules cover 同一個 example，但 predict different classes。

令：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

則：

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

不再創新的 `CCR` 名稱。

## 涵義

它描述 Prediction Policy 真正遇到 competing class evidence 的 workload。

## Code

`roughset/pipeline.py::_pre_resolution_conflicts`

```python
matched = matching_rules(row, rules)
decisions = sorted({str(rule.decision) for rule in matched})
is_conflict = len(decisions) > 1
```

現有舊欄位名稱如 `pre_resolution_conflict_case_rate` 可以保留相容性；manuscript 只稱 conflict-set count / proportion。

Exact-antecedent conflict 只作 supplementary structural audit。

## Citation

- Lindgren, T. (2004). *Methods for Rule Conflict Resolution*. https://doi.org/10.1007/978-3-540-30115-8_26
- Lindgren, T., & Boström, H. (2002). *Classification with Intersecting Rules*. https://doi.org/10.1007/3-540-36169-3_31

---

# 9. BA / Macro-F1 on the conflict set

不再使用自訂名稱 `Conflict Resolution Accuracy (CRA)` 作主要結果。

直接把既有標準 metrics 限制在 \(\mathcal C\)：

\[
\boxed{BA_{\mathcal C}}
\]

\[
\boxed{MacroF1_{\mathcal C}}
\]

## 涵義

回答：真正發生 competing-rule conflict 時，哪一個 Prediction Policy 的分類品質較好？

這不是新 metric，而是 established metric 的 conditional evaluation。

## Code

`roughset/pipeline.py::_evaluate_system`

```python
flags = np.asarray(artifact.pre_resolution_conflict_flags, dtype=bool)
y_true = artifact.test[artifact.target].astype(str).to_numpy()[flags]
y_pred = np.asarray(metrics["predictions"], dtype=object)[flags]

conflict_ba = balanced_accuracy(y_true, y_pred)
conflict_f1 = macro_f1_score(y_true, y_pred)
```

現有輸出：

```text
conflict_balanced_accuracy
conflict_macro_f1
```

## Citation

- Conflict subset：Lindgren (2004), DOI `10.1007/978-3-540-30115-8_26`.
- BA：Brodersen et al. (2010), DOI `10.1109/ICPR.2010.764`.
- Macro-F1 / performance-measure framework：Sokolova & Lapalme (2009), DOI `10.1016/j.ipm.2009.03.002`.

---

# 10. Client-order disagreement — Variation Ratio

對固定 test case \(x\)，假設檢查 \(T\) 種 client-order predictions：

\[
\hat y_{\pi_1}(x),\ldots,\hat y_{\pi_T}(x)
\]

modal predicted class 出現次數：

\[
f_x=\max_d\sum_{t=1}^{T}I[\hat y_{\pi_t}(x)=d]
\]

Variation Ratio：

\[
\boxed{VR(x)=1-\frac{f_x}{T}}
\]

整體可報普通摘要平均：

\[
\boxed{\overline{VR}=\frac1N\sum_xVR(x)}
\]

## 涵義

- \(VR=0\)：所有 client orders 都給同一 prediction。
- 值越大：categorical predictions 對 client order 越缺乏 consensus。

Gal (2016, Eq. 3.19) 使用 \(1-f_x/T\) 的 variation ratio，並把來源追溯至 Freeman (1965)。本研究只是把既有 measure 套到 client-order prediction ensemble。

## Code

`roughset/established_metrics.py::variation_ratio_by_case`

```python
for case_idx in range(matrix.shape[1]):
    counts = Counter(matrix[:, case_idx].tolist())
    modal_frequency = max(counts.values()) if counts else 0
    ratios.append(1.0 - (modal_frequency / n_orders))
```

`roughset/established_metrics.py::audit_order_variation_ratio` 使用與既有 order audit 相同的 client permutations，重排同一 learned local rule sets，取得 prediction matrix 後計算 VR。

正式 all-policy batch output 已接入：

```text
mean_variation_ratio
mean_variation_ratio_conflict
```

`mean_variation_ratio_conflict` 只是把同一 VR 限制在固定 conflict set 上做描述平均，不是另一個新 metric。

## Citation

- Gal, Y. (2016). *Uncertainty in Deep Learning*. PhD thesis, University of Cambridge, §3.3.1, Eq. (3.19). https://www.cs.ox.ac.uk/people/yarin.gal/website/thesis/thesis.pdf
- Gal (2016) attributes variation ratios to Freeman (1965).

---

# 11. Performance distribution across client permutations

每個 client order \(\pi\) 都可計算：

\[
BA_\pi
\]

報普通描述統計：

\[
\boxed{Mean,\ SD,\ Min,\ Max}
\]

## 涵義

Variation Ratio 看 individual predictions 的 categorical disagreement；BA distribution 看整體 predictive performance 對 order 的敏感程度。

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

這裡的 mean/std/min/max 是普通描述統計，不宣稱為新 metric。

---

# 12. Repeated policy comparison — Friedman / Wilcoxon

目前 frozen UCI3 單一 holdout/seed 只能作 descriptive mechanism baseline。

正式 publication-level comparison 必須先產生 repeated paired observations，例如多個 random splits / seeds。

四個 policies 同時比較：

\[
H_0:\quad R_{FM}=R_{SV}=R_{STD}=R_{GS}
\]

使用 Friedman omnibus test；顯著後再做 post-hoc multiple comparisons。

兩個方法 paired comparison 可使用 Wilcoxon signed-rank test。

## Citation

- Demšar, J. (2006). *Statistical Comparisons of Classifiers over Multiple Data Sets*. *Journal of Machine Learning Research, 7*, 1–30.
- Woźniak et al. (2026) 的 source experiment 本身也使用 paired Wilcoxon across repeated splits。

## Code status

目前 **沒有** 在單一 seed-42 baseline 上硬算 Friedman/Wilcoxon，這是刻意的：沒有 repeated paired observations 時不應製造假的 statistical significance。

---

# 13. Primary vs supplementary outputs

正式主分析：

```text
Balanced Accuracy
Macro-F1
Coverage
Ruleset size
Mean conditions per rule
Pairwise antecedent Jaccard
Conflict-set count / proportion
BA on conflict set
Macro-F1 on conflict set
Variation Ratio
BA distribution across client orders
```

舊欄位可保留 compatibility，但降級：

```text
conflict_resolution_accuracy
pre_resolution_conflict_case_rate / CCR wording
order_sensitivity_rate / OSR wording
rule_heterogeneity / H_rule wording
disagreement_vs_first_match
```

最後一個 `disagreement_vs_first_match` 仍可作 supplementary behavioral comparison，但不作主要 performance metric。

---

# References

- Brodersen, K. H., Ong, C. S., Stephan, K. E., & Buhmann, J. M. (2010). *The Balanced Accuracy and Its Posterior Distribution*. https://doi.org/10.1109/ICPR.2010.764
- Demšar, J. (2006). *Statistical Comparisons of Classifiers over Multiple Data Sets*. *Journal of Machine Learning Research, 7*, 1–30.
- Gal, Y. (2016). *Uncertainty in Deep Learning*. PhD thesis, University of Cambridge, §3.3.1, Eq. (3.19).
- Lindgren, T. (2004). *Methods for Rule Conflict Resolution*. https://doi.org/10.1007/978-3-540-30115-8_26
- Lindgren, T., & Boström, H. (2002). *Classification with Intersecting Rules*. https://doi.org/10.1007/3-540-36169-3_31
- Sokolova, M., & Lapalme, G. (2009). *A systematic analysis of performance measures for classification tasks*. https://doi.org/10.1016/j.ipm.2009.03.002
- Woźniak, K., Sousa, J., & Śnieżyński, B. (2026). *Rule-Based Federated Learning for Healthcare*. https://doi.org/10.1007/978-3-032-29921-5_38
