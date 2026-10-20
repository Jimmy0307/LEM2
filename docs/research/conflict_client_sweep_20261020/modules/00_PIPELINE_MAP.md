# Federated LEM2 研究流程總圖

本文件只負責定義研究流程各層邊界，不討論哪一種方法最好。

\[
Data
\rightarrow
Local\ LEM2
\rightarrow
Aggregation
\rightarrow
Global\ Rule\ Set
\rightarrow
Rule\ Structure\ Audit
\rightarrow
Conflict\ Audit
\rightarrow
Conflict\ Resolution
\rightarrow
Prediction
\rightarrow
Evaluation
\]

Client Count Sweep \(C\in\{2,3,4,5\}\) 位於整條流程外層，用來觀察 client 數改變時，各層輸出如何改變。

## 模組切分

1. `01_LOCAL_LEM2.md`：每個 client 如何由 local data 產生 local rules。
2. `02_AGGREGATION.md`：local rules 如何形成 global rule set；UNION 發生在這一層。
3. `03_RULE_STRUCTURE.md`：規則數量、Jaccard、heterogeneity 與 provenance。
4. `04_CONFLICT_AUDIT.md`：exact conflict 與 inference-level conflict 如何定義與量化。
5. `05_CONFLICT_RESOLUTION.md`：A/B 衝突後如何由 resolver 產生單一 prediction。
6. `06_EVALUATION.md`：Balanced Accuracy、Macro F1、Coverage、conflict-only performance、order sensitivity。
7. `07_CLIENT_COUNT_SWEEP.md`：固定 C=2,3,4,5，串起整條研究鏈。

## 三個常被混淆的 UNION

### 1. Federated rule aggregation UNION

\[
R_G=\bigcup_{c=1}^{C}R_c
\]

用途：把各 client 的 local rule sets 聚合成 global rule set。

### 2. Jaccard 中的 set UNION

\[
J(R_i,R_j)=\frac{|R_i\cap R_j|}{|R_i\cup R_j|}
\]

用途：計算兩個 client rule sets 的相似度；不是 aggregation method。

### 3. GLOBAL_STRENGTH 的 support-set UNION

\[
S_d(x)=\bigcup_{r\in M_d(x)}Supp(r)
\]

用途：合併支持同一 decision 的 training-object support sets，避免重複計數；不是 client rule aggregation。

## 研究邏輯

之後所有討論都必須先指出目前在第幾層，避免把 aggregation、conflict、resolver 混成同一件事。
