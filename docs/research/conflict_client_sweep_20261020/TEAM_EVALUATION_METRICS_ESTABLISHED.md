# 組員討論版：既有 Evaluation Metrics × Formula × Meaning × Code

> 原則：正式研究只使用既有分類評量、既有 rule-conflict 定義、既有 disagreement measure 與既有統計檢定。專案內曾自訂的 `CRA / CCR / OSR / H_rule` 不再作主要指標。

---

# 1. 正式主指標

| 問題 | 正式使用 | 來源 |
|---|---|---|
| 整體分類品質 | Balanced Accuracy | Healthcare source paper；Brodersen et al. (2010) |
| Precision / Recall 平衡 | Macro-F1 | Sokolova & Lapalme (2009) |
| Explicit rules 能覆蓋多少資料 | Coverage | Healthcare source paper |
| Rule base 大小 | Ruleset size | Healthcare source paper |
| Rule 複雜度 | Mean conditions per rule | Healthcare source paper |
| Client rulesets 相似度 | Pairwise Jaccard | Healthcare source paper |
| 哪些 test cases 發生 rule conflict | Conflict set | Lindgren (2004); Lindgren & Boström (2002) |
| Conflict cases 上分類品質 | BA / Macro-F1 restricted to conflict set | 標準 metric 套用在既有 conflict set |
| FIRST_MATCH 對 client order 的 disagreement | Variation Ratio | Freeman (1965); Gal (2016) |
| Policy 是否顯著不同 | Friedman + post-hoc；paired Wilcoxon | Demšar (2006)；Healthcare source paper 使用 paired Wilcoxon |

---

# 2. Balanced Accuracy

\[
Recall_k=\frac{TP_k}{TP_k+FN_k}
\]

\[
\boxed{BA=\frac1K\sum_{k=1}^{K}Recall_k}
\]

## 代表意思

每個 class 都有一樣的權重。資料不平衡時，比 raw accuracy 更不容易被 majority class 誤導。

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

## 代表意思

BA 主要看 recall；Macro-F1 同時看 precision 和 recall。

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

---

# 4. Coverage

令：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

\[
\boxed{Coverage=\frac{|\{x:M(x)\neq\emptyset\}|}{N_{test}}}
\]

## 代表意思

多少 test cases 至少被一條 explicit rule match，而不是直接掉到 default class。

## Code

`roughset/evaluation.py::evaluate_rule_model`

```python
"coverage": (
    float(np.mean([len(x) > 0 for x in matched]))
    if len(test)
    else 0.0
)
```

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

## 代表意思

- Ruleset size：global rule base 有多大。
- Conditions per rule：每條 rule 平均有多 specific / complex。

較短的 rules 通常較 general、會 cover 更大的 feature space；但是否因此造成更多 conflict 仍需 empirical verification。

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

---

# 6. Pairwise Jaccard similarity

\[
\boxed{J(R_i,R_j)=\frac{|R_i\cap R_j|}{|R_i\cup R_j|}}
\]

## 代表意思

- \(J=1\)：兩 clients 的 rulesets 完全相同。
- \(J=0\)：完全沒有共同 rules。
- 越低表示 local rulesets 越不相似。

正式主分析優先使用 Healthcare paper-compatible 的 antecedent-only Jaccard。

不要再用：

\[
H_{rule}=1-J
\]

作主要新指標。

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

---

# 7. Conflict set

Lindgren 對 rule conflict 的核心定義：

> two or more rules cover the same example but predict different classes.

因此：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

\[
\boxed{
\mathcal C=\{x:|\{d_r:r\in M(x)\}|>1\}
}
\]

## 正式報告

只報：

\[
\boxed{|\mathcal C|}
\]

與：

\[
\boxed{\frac{|\mathcal C|}{N_{test}}}
\]

這是 conflict set 的 size / proportion，不要再取新的 `CCR` 名稱。

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

---

# 8. BA / Macro-F1 on the conflict set

不再使用自訂名稱 `Conflict Resolution Accuracy (CRA)` 當主要指標。

直接報：

\[
\boxed{BA_{\mathcal C}}
\]

\[
\boxed{MacroF1_{\mathcal C}}
\]

## 代表意思

只在真正發生 competing-rule conflict 的 cases 上比較四種 Prediction Policies。

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

---

# 9. FIRST_MATCH client-order disagreement — Variation Ratio

所有 client-order permutations 對同一 case \(x\) 產生 \(T\) 個 predictions。

令 modal prediction 出現次數為：

\[
f_x=\max_d\sum_{t=1}^{T}I[\hat y_{\pi_t}(x)=d]
\]

Variation Ratio：

\[
\boxed{VR(x)=1-\frac{f_x}{T}}
\]

整體：

\[
\boxed{\overline{VR}=\frac1N\sum_xVR(x)}
\]

## 代表意思

- 0：所有 client orders 都給一樣答案。
- 越大：client order 對 prediction 的影響越強。

## 目前 code 狀態

目前 production **還沒有直接算 VR**。

但 `roughset/federated.py::audit_order_sensitivity` 已經建立完整 prediction matrix：

```python
matrix = np.asarray(predictions_by_order, dtype=object)
```

目前只是做 binary 判斷：

```python
sensitive = np.array([
    len(set(matrix[:, j].tolist())) > 1
    for j in range(matrix.shape[1])
])
```

正式下一版若改 code，應直接從 `matrix[:, j]` 算 modal frequency，再套 Variation Ratio；不要再把 `OSR` 當 primary metric。

---

# 10. BA distribution across client permutations

對每個 client order \(\pi\)：

\[
BA_{\pi}
\]

報：

\[
\boxed{Mean, SD, Min, Max}
\]

## 代表意思

Variation Ratio 看 individual predictions 的 disagreement；BA distribution 看整個模型 performance 對 client order 有多敏感。

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

後面用 `_finite_summary` 產出 mean / std / min / max。

---

# 11. 四個 Prediction Policies 的統計比較

目前只有 seed 42 的單一 holdout，因此**現在只能 descriptive comparison，不能宣稱 statistical significance**。

正式 publication phase 要先有 repeated splits / seeds，再使用：

## Friedman test

四個 policies、跨多個 dataset × split blocks：

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

其中：

- \(k=4\)：四個 Prediction Policies。
- \(N\)：獨立比較 blocks 數。
- \(R_j\)：第 \(j\) 個 policy 的平均 rank。

若整體顯著，再做 post-hoc pairwise comparisons + Holm correction。

## Wilcoxon signed-rank

兩個 policies 的 paired comparison：

\[
d_i=s_i^{(A)}-s_i^{(B)}
\]

對非零 \(|d_i|\) 排 rank，再比較 signed ranks。

## Code 狀態

目前 repo 尚未實作 Friedman / Wilcoxon。

這不是 bug；因 frozen UCI3 目前本來就只有一個 holdout split，資料條件還不足以做正式 repeated statistical comparison。

---

# 12. Legacy 欄位如何處理

| 舊名稱 | 新的正式定位 |
|---|---|
| `conflict_case_rate` | conflict-set proportion（描述統計） |
| `conflict_resolution_accuracy` | 不作主結果；用 conflict-set BA / Macro-F1 |
| `order_sensitivity_rate` | legacy；正式改 Variation Ratio |
| `order_sensitivity_conflict_rate` | legacy supplementary |
| `rule_heterogeneity = 1-J` | 不作主結果；直接報 Jaccard |
| `disagreement_vs_first_match` | supplementary behavior analysis |
| `exact_conflict_antecedent_rate` | supplementary structural audit |

---

# 13. 最後真正要比較的表

每個 dataset × C × Prediction Policy：

```text
Balanced Accuracy
Macro-F1
Coverage
Ruleset Size
Mean Conditions per Rule
Mean Pairwise Jaccard
Conflict Set Count
Conflict Set Proportion
Balanced Accuracy on Conflict Set
Macro-F1 on Conflict Set
```

FIRST_MATCH 額外：

```text
Mean Variation Ratio
BA across client permutations: Mean / SD / Min / Max
```

Repeated experiments 完成後才加：

```text
Friedman + post-hoc
Paired Wilcoxon
```

---

# 14. References

1. Woźniak, K., Sousa, J., & Śnieżyński, B. (2026). *Rule-Based Federated Learning for Healthcare*. DOI `10.1007/978-3-032-29921-5_38`.
2. Brodersen, K. H., Ong, C. S., Stephan, K. E., & Buhmann, J. M. (2010). *The Balanced Accuracy and Its Posterior Distribution*. DOI `10.1109/ICPR.2010.764`.
3. Sokolova, M., & Lapalme, G. (2009). *A systematic analysis of performance measures for classification tasks*. DOI `10.1016/j.ipm.2009.03.002`.
4. Lindgren, T. (2004). *Methods for Rule Conflict Resolution*. DOI `10.1007/978-3-540-30115-8_26`.
5. Lindgren, T., & Boström, H. (2002). *Classification with Intersecting Rules*. DOI `10.1007/3-540-36169-3_31`.
6. Freeman, L. C. (1965). *Elementary Applied Statistics*. Wiley.
7. Gal, Y. (2016). *Uncertainty in Deep Learning*. PhD thesis, University of Cambridge.
8. Demšar, J. (2006). *Statistical Comparisons of Classifiers over Multiple Data Sets*. *Journal of Machine Learning Research, 7*, 1–30.
