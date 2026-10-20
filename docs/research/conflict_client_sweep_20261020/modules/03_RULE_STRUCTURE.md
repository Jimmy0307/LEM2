# Module 03 — Rule Structure Diagnostics

## 目的

這一層只回答：不同 clients 學到的 rules 有多相似、多分散，以及 aggregation 後的 global rule structure 長什麼樣。

它不做 prediction，也不決定 conflict winner。

---

## Rule signatures

### Antecedent-only signature

\[
sig_A(r)=sorted(Ante(r))
\]

用途：只比較條件結構，不看 decision。

### Full-rule signature

\[
sig_F(r)=(sorted(Ante(r)),d_r)
\]

用途：條件與 decision 都必須相同才算同一 rule。

Frozen production heterogeneity 的主要 contract 以 full-rule signature 為準；antecedent Jaccard 同時保留作 conflict research 輔助診斷。

---

## Pairwise Jaccard

對 client \(i,j\)：

\[
J(i,j)=\frac{|F_i\cap F_j|}{|F_i\cup F_j|}
\]

其中 \(F_i,F_j\) 可以分別用 antecedent-only 或 full-rule signatures 建立。

若 \(C>1\)，平均 pairwise similarity：

\[
\bar J=
\frac{2}{C(C-1)}
\sum_{i<j}J(i,j)
\]

full-rule heterogeneity：

\[
H_{rule}=1-\bar J_{full}
\]

---

## 為什麼 Jaccard 不等於 Conflict

低 Jaccard 表示 clients 產生的 rules 重疊少。

但：

\[
Low\ Jaccard\not\Rightarrow High\ Conflict
\]

也不能寫：

\[
Low\ Jaccard\Rightarrow Low\ Conflict
\]

原因是兩條不同 antecedents 仍可能同時 cover 同一 test case。

例如：

```text
A=1       → Yes
A=1,B=2   → No
```

antecedents 不同，但 case `A=1,B=2` 會同時 match。

因此 rule diversity 是 conflict 的結構背景，不是 conflict definition。

---

## Global Rule Count

\[
|R_G|
\]

表示 aggregation 後 full global rules 的數量。

但：

\[
|R_G|\uparrow
\]

不代表：

\[
Conflict\uparrow
\]

現有 Balance Scale evidence 甚至呈現 global rule count 大致下降，但 inference conflict rate 上升。

所以 conflict 更直接取決於：

\[
Rule\ Coverage\ Overlap
+
Decision\ Disagreement
\]

而不是 raw rule count。

---

## Provenance

對 global rule \(r\)：

\[
Prov(r)=\{c:r\in R_c\}
\]

它回答的是：

> 哪些 clients 獨立產生了同一條完整 rule？

Provenance 與 support 不同。

Final audit 後 STANDARD / GLOBAL 的 federated support 會把每條 global rule 放到所有 client training tables 上重新評估；不只在 \(Prov(r)\) 上計算。

因此：

\[
Provenance(r)\neq SupportScope(r)
\]

這個區分必須保留。

---

## 本層輸出

- Local rule count；
- Global rule count；
- Pairwise Jaccard（antecedent）；
- Pairwise Jaccard（full rule）；
- Rule heterogeneity；
- Rule provenance。

這些輸出可以解釋 conflict 的背景，但本層本身不標記 conflict winner。

---

## Production implementation

- `roughset/evaluation.py::rule_antecedent_signature`
- `roughset/evaluation.py::rule_full_signature`
- `roughset/evaluation.py::pairwise_rule_jaccard`
- provenance：`roughset/federated.py::union_rules_with_provenance`

---

## 老師問法

### 「Jaccard 的聯集跟 federated UNION 一樣嗎？」

不一樣。Jaccard 的 \(R_i\cup R_j\) 只是相似度分母；federated UNION 的 \(\bigcup_cR_c\) 是真正建立 global rules 的 aggregation operator。

### 「Jaccard 低是不是就代表 conflict 高？」

不能這樣下定律。Jaccard 是 set identity similarity，inference conflict 是 case-level coverage overlap + decision disagreement。
