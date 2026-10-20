# Module 06 — Evaluation

## 目的

這一層只回答：在固定 local rules、global rules 與 pre-resolution conflict workload 下，不同 resolver 帶來什麼可量化結果。

正確比較必須是：

```text
同一 RuleSystemArtifact
        ↓
同一 global rules / same conflict cases
        ↓
替換 resolver
        ↓
比較 outcomes
```

不能讓不同 resolver 各自重跑 LEM2 或重新建立 global rules。

---

## 1. Classification Accuracy

\[
Accuracy=
\frac{1}{N}
\sum_{i=1}^{N}I[\hat y_i=y_i]
\]

作為直觀整體正確率，但 class imbalance 時不能單獨使用。

---

## 2. Balanced Accuracy

對真實資料中出現的 \(K\) 個 classes：

\[
Recall_k=
\frac{TP_k}{TP_k+FN_k}
\]

\[
BA=
\frac1K\sum_{k=1}^{K}Recall_k
\]

這是目前主要 overall performance 指標之一。

---

## 3. Macro F1

對每個 class：

\[
F1_k=
\frac{2Precision_kRecall_k}{Precision_k+Recall_k}
\]

再平均：

\[
MacroF1=
\frac1K\sum_{k=1}^{K}F1_k
\]

production implementation 對 true/predicted labels 的 union 計算 classes。

---

## 4. Coverage

對 test case \(x\)：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

若：

\[
M(x)\neq\emptyset
\]

代表至少一條 rule 可以覆蓋該 case。

Coverage：

\[
Coverage=
\frac{|\{x:M(x)\neq\emptyset\}|}{N_{test}}
\]

若沒有 matching rule，所有 policies 都回傳 default class，所以 coverage 與 accuracy 必須分開看。

---

## 5. Conflict-only performance

先固定：

\[
X_{conflict}
=
\{x:|\{d_r:r\in M(x)\}|>1\}
\]

Conflict Resolution Accuracy：

\[
CRA=
\frac{|\{x\in X_{conflict}:\hat y(x)=y(x)\}|}{|X_{conflict}|}
\]

另外報 conflict-only Balanced Accuracy。

原因是 overall performance 中包含大量 non-conflict cases，可能掩蓋 resolver 真正面對 competing evidence 時的能力。

因此 resolver 至少要同時看：

\[
Overall\ Performance
\]

以及：

\[
ConflictOnly\ Performance
\]

---

## 6. Order Sensitivity

令：

\[
\Pi_C
\]

為 client arrival order permutations。

對 case \(x\)，若：

\[
|\{\hat y_\pi(x):\pi\in\Pi_C\}|>1
\]

則該 case 是 order-sensitive。

Order Sensitivity Rate：

\[
OSR=
\frac{\#order-sensitive\ test\ cases}{N_{test}}
\]

也可限制在 conflict cases：

\[
OSR_{conflict}
=
\frac{\#order-sensitive\ conflict\ cases}{|X_{conflict}|}
\]

對目前：

\[
C\le5
\]

最多：

\[
5!=120
\]

種 client orders，設定 `max_permutations=120` 可以完整枚舉。

---

## 7. Resolver 與 order sensitivity 的理論關係

### FIRST_MATCH

會直接讀 global list order，因此：

\[
OSR\ge0
\]

且實際可能很高。

### SIMPLE / STANDARD / GLOBAL

只要 rule set 與 evidence context 相同，score aggregation 不依賴 rule traversal order，因此 frozen definitions 為 order-invariant。

所以 voting 的一個明確優點是消除 arrival-order semantics；但：

\[
OrderInvariant
\not\Rightarrow
HigherAccuracy
\]

這點已被 Hayes-Roth 結果證明。

---

## 8. Fair comparison matrix

對每個 dataset、每個 \(C\)：

| 固定項 | 是否固定 |
|---|---|
| Train/test split | 是 |
| Client partition | 是 |
| Local LEM2 rules | 是 |
| Global UNION rules | 是 |
| Pre-resolution conflict cases | 是 |
| Default class | 是 |
| Resolver | **唯一主要替換項** |

這樣 performance difference 才能歸因於 resolution policy。

---

## 9. Production implementation

- `roughset/evaluation.py::classification_accuracy`
- `roughset/evaluation.py::balanced_accuracy`
- `roughset/evaluation.py::macro_f1_score`
- `roughset/evaluation.py::evaluate_rule_model`
- pre-resolution conflict：`roughset/pipeline.py::_pre_resolution_conflicts`
- order sensitivity：`roughset/federated.py::audit_order_sensitivity`
- order distribution：`roughset/federated.py::audit_order_distribution`

---

## 老師問法

### 「為什麼有 overall accuracy 還要 conflict-only？」

因 resolver 真正介入的是 competing evidence cases。若大部分資料根本沒 conflict，overall score 可能把 resolution quality 稀釋掉。

### 「Voting 比 FIRST_MATCH 穩定，所以一定比較好？」

只能說 order stability 較好，不能推論 accuracy 一定較高。Stability 與 predictive performance 是兩個 evaluation dimensions。
