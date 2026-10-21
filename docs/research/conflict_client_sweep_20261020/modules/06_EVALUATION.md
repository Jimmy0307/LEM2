# Module 06 — Evaluation（既有理論指標版）

## 目的

這一層只回答：在固定 local rules、global rules 與同一 conflict set 下，不同 **Prediction Policies** 帶來什麼可量化結果。

本版原則：**主要評量只使用既有文獻／標準統計方法。**

不再把下列專案內自訂名稱當成正式主要指標：

- `Conflict Resolution Accuracy (CRA)`
- `Conflict Case Rate (CCR)`
- `Order Sensitivity Rate (OSR)`
- `H_rule = 1 - mean Jaccard`

舊欄位可以保留作 backward compatibility，但 manuscript / 組內主要比較不再以這些名稱立論。

正確比較仍必須是：

```text
同一 RuleSystemArtifact
        ↓
同一 global rules / 同一 conflict set
        ↓
只替換 Prediction Policy
        ↓
比較既有評量指標
```

---

# 1. Overall prediction performance

## 1.1 Balanced Accuracy — 主要指標

對第 \(k\) 類：

\[
Recall_k=\frac{TP_k}{TP_k+FN_k}
\]

若共有 \(K\) 個 classes：

\[
\boxed{
BA=\frac{1}{K}\sum_{k=1}^{K}Recall_k
}
\]

### 涵義

每個 class 擁有相同權重，因此不會讓多數類別的樣本數支配整體分數。

- \(BA\) 高：各 class 的 recall 整體較平均、較好。
- \(BA\) 低：至少有部分 class 的 recall 明顯較差。

### 為什麼是主指標

Healthcare source paper 明確把 Balanced Accuracy 設為 primary metric，理由是多數資料集存在 class imbalance。

理論來源可再對應 Brodersen et al. (2010), *The Balanced Accuracy and Its Posterior Distribution*，DOI `10.1109/ICPR.2010.764`。

### 現有 code

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

這段就是逐 class 計算 recall 後做 arithmetic mean。

---

## 1.2 Macro-F1 — 次要分類指標

對 class \(k\)：

\[
Precision_k=\frac{TP_k}{TP_k+FP_k}
\]

\[
Recall_k=\frac{TP_k}{TP_k+FN_k}
\]

\[
F1_k=\frac{2Precision_kRecall_k}{Precision_k+Recall_k}
\]

最後：

\[
\boxed{
MacroF1=\frac1K\sum_{k=1}^{K}F1_k
}
\]

### 涵義

Balanced Accuracy 主要看各 class recall；Macro-F1 同時考慮 precision 與 recall。

因此：

- BA 高但 Macro-F1 較低：可能 recall 不錯，但 false positives 較多。
- BA 與 Macro-F1 都高：各 class 的 precision / recall 整體較平衡。

理論與分類評量來源可對應 Sokolova & Lapalme (2009), *A systematic analysis of performance measures for classification tasks*, DOI `10.1016/j.ipm.2009.03.002`。

### 現有 code

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

---

## 1.3 Accuracy — 僅作直觀補充

\[
\boxed{
Accuracy=\frac{1}{N}\sum_{i=1}^{N}I(\hat y_i=y_i)
}
\]

### 涵義

整體答對比例，容易理解；但 class imbalance 時可能被 majority class 誤導，因此不作主要 winner criterion。

### 現有 code

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

# 2. Rule-system interpretability / structure

這一組直接延續 Healthcare source paper 的評量方式。

## 2.1 Ruleset size

\[
\boxed{|R_G|}
\]

### 涵義

Global ruleset 中規則總數。

- 數量少：模型較 compact。
- 數量多：可表達 pattern 較多，但人工檢視成本也較高。

### 現有 code

`roughset/pipeline.py::_rule_condition_summary`

```python
counts = [len(rule.conditions) for rule in rules]
return {
    "rule_count": len(counts),
    "average_condition_count": float(np.mean(counts)),
    ...
}
```

---

## 2.2 Conditions per rule

若第 \(j\) 條 rule 有 \(L_j\) 個 antecedent conditions：

\[
\boxed{
\overline L=\frac1{|R_G|}\sum_{j=1}^{|R_G|}L_j
}
\]

### 涵義

衡量 rule complexity。

- 平均條件數較少：rule 較 general、較容易 match 更多 cases。
- 平均條件數較多：rule 較 specific。

Healthcare paper 本身就是用平均 conditions per rule 描述 ruleset complexity。

### 現有 code

同樣在 `roughset/pipeline.py::_rule_condition_summary`：

```python
counts = [len(rule.conditions) for rule in rules]
"average_condition_count": float(np.mean(counts))
```

---

## 2.3 Coverage

令：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

則：

\[
\boxed{
Coverage=
\frac{|\{x\in U_{test}:M(x)\neq\emptyset\}|}
{|U_{test}|}
}
\]

### 涵義

多少 test cases 能被至少一條 explicit rule 處理，而不是落到 default class。

Healthcare source paper 明確把 coverage 定義為「matched a rule other than the default rule 的 test cases 比例」。

### 現有 code

`roughset/evaluation.py::evaluate_rule_model`

```python
"coverage": (
    float(np.mean([len(x) > 0 for x in matched]))
    if len(test)
    else 0.0
)
```

---

# 3. Client ruleset similarity — Pairwise Jaccard

對 Client \(i,j\) 的 rulesets：

\[
\boxed{
J(R_i,R_j)=
\frac{|R_i\cap R_j|}{|R_i\cup R_j|}
}
\]

### 涵義

- \(J=1\)：兩個 clients 的 rulesets 完全相同。
- \(J=0\)：沒有共同 rules。
- 數值越低：clients 學到的 rules 越不同。

Healthcare source paper 使用 Jaccard 並對所有 client pairs 平均。

### 正式主分析的版本

Healthcare paper stated set view 是以 sorted rule conditions 比較，因此主分析應優先報：

```text
pairwise_jaccard_antecedent
```

`pairwise_jaccard_full_rule` 可保留作 supplementary conflict audit，但不再另外建立：

\[
H_{rule}=1-\bar J
\]

作正式主要指標。

### 現有 code

`roughset/evaluation.py::_jaccard`

```python
def _jaccard(set_a, set_b) -> float:
    union = set_a | set_b
    if not union:
        return float("nan")
    return float(len(set_a & set_b) / len(union))
```

以及 `roughset/evaluation.py::pairwise_rule_jaccard`：

```python
ant_a = {rule_antecedent_signature(r) for r in local_rules[a]}
ant_b = {rule_antecedent_signature(r) for r in local_rules[b]}

rows.append({
    "jaccard_antecedent": _jaccard(ant_a, ant_b),
    ...
})
```

---

# 4. Rule Conflict — 使用既有 conflict 定義，不創新的 correctness metric

Lindgren (2004) 對 unordered rule sets 的 conflict 定義是：

> two or more rules cover the same example but predict different classes.

Lindgren & Boström (2002) 同樣研究 overlapping rules predicting different classes。

因此對 test case \(x\)：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

定義 conflict set：

\[
\boxed{
\mathcal C=
\left\{
x\in U_{test}:
|\{d_r:r\in M(x)\}|>1
\right\}
}
\]

### 正式報告方式

只報 descriptive quantities：

\[
\boxed{|\mathcal C|}
\]

與：

\[
\boxed{
\frac{|\mathcal C|}{|U_{test}|}
}
\]

不再把這個比例包裝成新的 `CCR` 指標名稱。

### 涵義

- \(|\mathcal C|=0\)：沒有 test object 同時被不同 decision rules cover。
- 比例越高：Prediction Policy 真正需要在 competing rule evidence 中做決策的 cases 越多。

### 現有 code

`roughset/pipeline.py::_pre_resolution_conflicts`

```python
matched = matching_rules(row, rules)
decisions = sorted({str(rule.decision) for rule in matched})
is_conflict = len(decisions) > 1
```

目前 code 已輸出：

```python
"conflict_cases_count": conflict_count,
"pre_resolution_conflict_case_rate": (
    conflict_count / total if total else float("nan")
)
```

正式寫作只把它解釋為 **conflict-set size / proportion**，不宣稱這是新 metric。

Exact-antecedent conflict 仍可作 supplementary structural audit，但不是主要 classifier evaluation metric。

### 文獻

- Lindgren, T. (2004). *Methods for Rule Conflict Resolution*. DOI `10.1007/978-3-540-30115-8_26`.
- Lindgren, T., & Boström, H. (2002). *Classification with Intersecting Rules*. DOI `10.1007/3-540-36169-3_31`.

---

# 5. Performance on the conflict set

不再使用自訂名稱 `Conflict Resolution Accuracy (CRA)` 作主要結果。

直接把既有標準 metrics 限制在 \(\mathcal C\) 上：

\[
\boxed{BA_{\mathcal C}}
\]

以及：

\[
\boxed{MacroF1_{\mathcal C}}
\]

### 涵義

這回答的是：

> 當既有 rule-conflict definition 真正成立時，哪一個 Prediction Policy 的分類品質較好？

因為 conflict subset 也可能 class-imbalanced，所以主要看 \(BA_{\mathcal C}\)，Macro-F1 作補充。

### 現有 code

`roughset/pipeline.py::evaluate_resolvers` 已經從固定的 structural artifact 讀取同一組 conflict flags：

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

這兩個可以直接沿用，因為它們不是新 metric，而是標準 BA / Macro-F1 在理論定義 conflict set 上的條件式評估。

---

# 6. FIRST_MATCH order robustness — Variation Ratio

舊文件使用 `OSR`，本版不再把 OSR 當正式主要 metric。

對固定 test case \(x\)，令所有檢查過的 client-order permutations 為：

\[
\Pi_C=\{\pi_1,\ldots,\pi_T\}
\]

取得 FIRST_MATCH predictions：

\[
\hat y_{\pi_1}(x),\ldots,\hat y_{\pi_T}(x)
\]

令 modal class 出現次數為：

\[
f_x=
\max_d
\sum_{t=1}^{T}
I[\hat y_{\pi_t}(x)=d]
\]

Variation Ratio：

\[
\boxed{
VR(x)=1-\frac{f_x}{T}
}
\]

整體可報：

\[
\boxed{
\overline{VR}=\frac1N\sum_{x\in U_{test}}VR(x)
}
\]

### 涵義

- \(VR(x)=0\)：所有 client orders 對該 case 都預測同一 class。
- \(VR(x)\) 越大：不同 client orders 的 prediction disagreement 越高。

Variation Ratio 是既有 categorical dispersion / predictive disagreement measure，可對應 Freeman (1965)；在 predictive uncertainty context 中亦見 Gal (2016)。

### 目前 code 狀態

**尚未直接實作 Variation Ratio。**

目前 `roughset/federated.py::audit_order_sensitivity` 已經建立所需的 prediction matrix：

```python
matrix = np.asarray(predictions_by_order, dtype=object)
```

但目前只轉成 binary sensitive / not-sensitive：

```python
sensitive = np.array([
    len(set(matrix[:, j].tolist())) > 1
    for j in range(matrix.shape[1])
])
```

這一段資料結構已足以計算 VR；正式下一版 code 應以既有 Variation Ratio 取代 OSR 作 primary order-disagreement metric。

---

# 7. Performance robustness across client permutations

除了 Variation Ratio，仍保留標準 descriptive statistics。

對每個 client order \(\pi\) 計算：

\[
BA_{\pi}
\]

報：

\[
Mean(BA_{\pi}),\quad SD(BA_{\pi}),\quad Min(BA_{\pi}),\quad Max(BA_{\pi})
\]

### 涵義

Variation Ratio 看「prediction 是否一致」；BA distribution 看「order 改變後 performance 波動多大」。

### 現有 code

`roughset/federated.py::audit_order_distribution`

現有 code 已逐 permutation 重算：

```python
rows.append({
    "client_order": " -> ".join(order),
    "balanced_accuracy": metrics["balanced_accuracy"],
    "macro_f1": metrics["macro_f1"],
    "coverage": metrics["coverage"],
})
```

並以 `_finite_summary` 計算 mean / std / min / max。

這部分可以直接沿用。

---

# 8. 四個 Prediction Policies 的統計比較

單看哪一個 configuration 的 BA 最大只能算 descriptive comparison。

若要形成 publication-level claim，需要 repeated datasets / repeated splits 後使用既有 non-parametric classifier-comparison framework。

Demšar (2006) 建議：

- 兩個 classifiers / policies：Wilcoxon signed-rank test。
- 多個 classifiers / policies、跨多個 datasets：Friedman test + post-hoc multiple comparison。

### Friedman test

若有 \(k\) 個 policies、\(N\) 個 independent blocks（例如 dataset × split），先在每個 block 對 policies 排名，令第 \(j\) 個 policy 的平均 rank 為 \(R_j\)：

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

### 涵義

檢定四個 Prediction Policies 的 performance rank 是否可視為相同。

若拒絕：

\[
H_0:R_1=R_2=R_3=R_4
\]

再做 post-hoc pairwise comparison，並使用 Holm correction 控制 multiple testing。

### Wilcoxon signed-rank

對兩個 policies，在相同 blocks 上取得配對差：

\[
d_i=s_i^{(A)}-s_i^{(B)}
\]

對非零 \(|d_i|\) 排 rank，再比較正負 signed ranks。

### 目前 code 狀態

**Production code 尚未實作 Friedman / Wilcoxon。**

而且 frozen UCI3 evidence 目前只有單一 holdout / seed 42，因此目前結果只能做 descriptive mechanism baseline，不能用這一個 split 宣稱 statistical significance。

下一階段應先重跑 repeated splits / seeds，再加統計檢定。

文獻：Demšar, J. (2006). *Statistical Comparisons of Classifiers over Multiple Data Sets*. JMLR, 7, 1–30.

---

# 9. 正式主表建議

每個 dataset × client count × Prediction Policy，主表只報：

| 類別 | 指標 |
|---|---|
| Prediction | Balanced Accuracy |
| Prediction secondary | Macro-F1 |
| Interpretability | Coverage |
| Rule structure | Ruleset size |
| Rule complexity | Mean conditions per rule |
| Client similarity | Mean pairwise Jaccard |
| Rule conflict | \(|\mathcal C|\), \(|\mathcal C|/N_{test}\) |
| Conflict subset performance | \(BA_{\mathcal C}\), \(MacroF1_{\mathcal C}\) |
| FIRST_MATCH order disagreement | Mean Variation Ratio |
| FIRST_MATCH order performance | BA mean / SD / min / max across permutations |
| Statistical comparison（repeated runs 後） | Friedman + post-hoc；paired Wilcoxon |

Accuracy 可以保留在 supplementary table，但不作主要 winner criterion。

---

# 10. Legacy → 正式名稱對照

| 舊欄位 / 名稱 | 正式處理 |
|---|---|
| `conflict_case_rate` / `pre_resolution_conflict_case_rate` | 解讀為 `conflict-set proportion`，不要創 CCR 名稱 |
| `conflict_resolution_accuracy` | 不作主要 metric；改用 \(BA_{\mathcal C}\)、\(MacroF1_{\mathcal C}\) |
| `order_sensitivity_rate` | legacy diagnostic；正式改用 Variation Ratio |
| `order_sensitivity_conflict_rate` | legacy diagnostic；不作主結果 |
| `rule_heterogeneity = 1 - J` | 不作主指標；直接報 mean pairwise Jaccard |
| `disagreement_vs_first_match` | supplementary behavioral comparison，不作 performance metric |
| `exact_conflict_antecedent_rate` | supplementary structural audit |

---

# 11. Code 對映總表

| 理論量 | 現有 code | 狀態 |
|---|---|---|
| Balanced Accuracy | `roughset/evaluation.py::balanced_accuracy` | 已實作，可直接用 |
| Macro-F1 | `roughset/evaluation.py::macro_f1_score` | 已實作，可直接用 |
| Accuracy | `roughset/evaluation.py::classification_accuracy` | 已實作，補充 |
| Coverage | `roughset/evaluation.py::evaluate_rule_model` | 已實作，可直接用 |
| Ruleset size / conditions per rule | `roughset/pipeline.py::_rule_condition_summary` | 已實作，可直接用 |
| Pairwise Jaccard | `roughset/evaluation.py::pairwise_rule_jaccard` | 已實作；antecedent 版本作 primary |
| Conflict set | `roughset/pipeline.py::_pre_resolution_conflicts` | 已實作 |
| BA / Macro-F1 on conflict set | `roughset/pipeline.py::evaluate_resolvers` | 已實作 |
| BA distribution across permutations | `roughset/federated.py::audit_order_distribution` | 已實作 |
| Variation Ratio | 可由 `audit_order_sensitivity` 的 prediction matrix 計算 | **尚未實作** |
| Friedman / Wilcoxon | 無 | **尚未實作；需 repeated runs 後再加** |

---

# 12. 文獻基礎

1. Woźniak, K., Sousa, J., & Śnieżyński, B. (2026). *Rule-Based Federated Learning for Healthcare*. DOI `10.1007/978-3-032-29921-5_38`.
   - Balanced Accuracy
   - ruleset size
   - conditions per rule
   - coverage
   - pairwise Jaccard
   - 5 random data splits
   - paired Wilcoxon comparison

2. Brodersen, K. H., Ong, C. S., Stephan, K. E., & Buhmann, J. M. (2010). *The Balanced Accuracy and Its Posterior Distribution*. DOI `10.1109/ICPR.2010.764`.

3. Sokolova, M., & Lapalme, G. (2009). *A systematic analysis of performance measures for classification tasks*. DOI `10.1016/j.ipm.2009.03.002`.

4. Lindgren, T. (2004). *Methods for Rule Conflict Resolution*. DOI `10.1007/978-3-540-30115-8_26`.

5. Lindgren, T., & Boström, H. (2002). *Classification with Intersecting Rules*. DOI `10.1007/3-540-36169-3_31`.

6. Freeman, L. C. (1965). *Elementary Applied Statistics*. Wiley.（Variation Ratio）

7. Gal, Y. (2016). *Uncertainty in Deep Learning*. PhD thesis, University of Cambridge.（classification variation ratio）

8. Demšar, J. (2006). *Statistical Comparisons of Classifiers over Multiple Data Sets*. Journal of Machine Learning Research, 7, 1–30.

---

## 最後原則

正式研究主線不再依賴新創 metrics，而改成：

\[
\boxed{
Existing\ Classification\ Metrics
+
Existing\ Rule\ Conflict\ Definition
+
Existing\ Disagreement\ Measure
+
Existing\ Statistical\ Tests
}
\]

用來回答：

\[
Client\ Count
\rightarrow
Rule\ Structure
\rightarrow
Rule\ Conflict
\rightarrow
Prediction\ Policy\ Performance
\]
