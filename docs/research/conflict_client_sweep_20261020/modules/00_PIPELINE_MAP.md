# Federated LEM2 研究流程總圖

## 目的

本文件只負責定義各研究層的邊界、輸入輸出與固定／可變項，不討論哪一種 resolver 最好。

完整流程：

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

Client Count Sweep：

\[
C\in\{2,3,4,5\}
\]

位於整條流程外層，用來觀察 client fragmentation 改變時，各層輸出如何變化。

---

## 模組切分

1. `01_LOCAL_LEM2.md`：每個 client 如何由 local data 產生 certain rules。
2. `02_AGGREGATION.md`：local rule sets 如何形成 global rule set；Federated UNION 在這一層。
3. `03_RULE_STRUCTURE.md`：規則數量、Jaccard、heterogeneity、provenance。
4. `04_CONFLICT_AUDIT.md`：exact conflict 與 inference conflict。
5. `05_CONFLICT_RESOLUTION.md`：同一 conflict workload 下四種 resolver 如何輸出單一 decision。
6. `06_EVALUATION.md`：overall、conflict-only、order sensitivity。
7. `07_CLIENT_COUNT_SWEEP.md`：C=2,3,4,5 的外層實驗設計。
8. `08_MATHEMATICAL_ARCHITECTURE.md`：統一符號、完整數學與四種 resolver 對照。

---

## 每一層的輸入與輸出

| 層 | 輸入 | 輸出 | 這一層回答的問題 |
|---|---|---|---|
| Local LEM2 | \(U_c\) | \(R_c\) | 每個 client 學到哪些 certain rules？ |
| Aggregation | \(R_1,\ldots,R_C\) | \(R_G\) | 哪些完整 rules 進 global set？ |
| Rule Structure | local/global rules | Jaccard、rule count、provenance | 規則結構有多分散？ |
| Conflict Audit | \(R_G\)、test cases | conflict groups / cases | 哪裡出現 competing decisions？ |
| Resolver | \(M(x)\) | \(\hat y(x)\) | A/B conflict 最後選誰？ |
| Evaluation | truth + predictions | BA、F1、coverage、CRA、OSR | 這個 resolver 結果如何？ |
| Client Sweep | \(C\) | 各層隨 C 的變化 | client fragmentation 帶來什麼？ |

---

## 固定項與實驗變項

### Resolver 比較時固定

- train/test split；
- client partitions；
- local reduct / local LEM2 rules；
- aggregation 後 \(R_G\)；
- pre-resolution conflict cases。

只替換：

\[
Resolver\in\{FIRST,SIMPLE,STANDARD,GLOBAL\}
\]

### Client Count Sweep 時改變

\[
C\in\{2,3,4,5\}
\]

但 LEM2 semantics、rule identity、conflict definition 不改。

---

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

用途：計算 client rule sets 相似度；不是 aggregation method。

### 3. GLOBAL_STRENGTH 的 support-set UNION

\[
S_d(x)=\bigcup_{r\in M_d(x)}Supp(r)
\]

用途：合併同 decision 的 positive support objects 並避免重複計數；不是 client rule aggregation。

---

## 研究邊界

所有討論必須先指出目前位於哪一層。

特別禁止把以下三件事混成一件：

\[
Aggregation
\neq
Conflict\ Detection
\neq
Conflict\ Resolution
\]

這是後續所有公式、程式與實驗解讀的共同邊界。
