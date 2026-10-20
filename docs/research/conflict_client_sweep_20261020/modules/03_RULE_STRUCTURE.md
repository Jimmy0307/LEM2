# Module 03 — Rule Structure Diagnostics

## 目的

這一層只回答：不同 clients 學到的 rules 有多相似、多分散，以及 global rules 的結構長什麼樣。

它不處理 prediction，也不決定 conflict winner。

## Pairwise Jaccard

對 client \(i,j\) 的 rule sets：

\[
J(R_i,R_j)=\frac{|R_i\cap R_j|}{|R_i\cup R_j|}
\]

目前系統分兩種 identity 計算：

### Antecedent-only

\[
sig_A(r)=Ante(r)
\]

用途：看條件結構的重疊程度。

### Full-rule

\[
sig_F(r)=(Ante(r),d_r)
\]

用途：把 decision 也納入，較適合 conflict research。

## Rule heterogeneity

低 Jaccard 代表不同 client rulesets 彼此重疊少、heterogeneity 高。

但必須注意：

\[
Low\ Jaccard\not\Rightarrow High\ Conflict
\]

因為兩條 antecedent 不完全相同，仍可能在 feature space 中同時 cover 同一個 test case。

所以 rule diversity 只是 conflict 的結構背景之一，不等於 conflict 本身。

## Global Rule Count

\[
|R_G|
\]

代表 aggregation 後 global rule set 的大小。

但現有 frozen evidence 已顯示 rule count 也不能單獨解釋 conflict growth；Balance Scale 在 client 增加時 global rule count 大致下降，但 inference conflict rate 反而上升。

## Provenance

每條 global rule 應保留其來源 client：

\[
Prov(r)=\{c_1,c_2,\ldots\}
\]

這讓後續可以知道：

- 同一 full rule 由哪些 clients 產生；
- conflict group 的 opposing rules 各自來自哪些 clients；
- future adaptive resolver 是否要利用 client-level evidence。

## Production implementation

- `roughset/evaluation.py::pairwise_rule_jaccard`
- `rule_antecedent_signature`
- `rule_full_signature`
- provenance 由 federated aggregation artifact 保存。

## 本層輸出

- Pairwise Jaccard (antecedent)
- Pairwise Jaccard (full rule)
- Global rule count
- Rule heterogeneity
- Rule provenance

這些輸出送給下一層 Conflict Audit 使用，但本層本身不定義 conflict。
