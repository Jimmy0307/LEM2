# Module 07 — Client Count Sweep

## 目的

Client Count Sweep 不是新的演算法層，而是包在整條 federated LEM2 pipeline 外面的 experimental factor。

固定：

\[
C\in\{2,3,4,5\}
\]

對每一個 client count，都重跑同一條研究鏈：

\[
Local\ LEM2
\rightarrow
Aggregation
\rightarrow
Rule\ Structure
\rightarrow
Conflict\ Audit
\rightarrow
Conflict\ Resolution
\rightarrow
Evaluation
\]

---

## 實驗矩陣

對每個 dataset：

\[
Dataset
\times
C
\times
Resolver
\]

其中：

\[
Resolver\in
\{FIRST\_MATCH,SIMPLE\_VOTING,STANDARD\_VOTING,GLOBAL\_STRENGTH\}
\]

目前 frozen UCI3 evidence 使用 holdout seed = 42。

因此現階段的 sweep 主要用來建立 structural / mechanism evidence；若未來要做 publication-level generalization，還應增加多 seed / repeated split robustness，而不是直接把單一 split 當普遍定律。

---

## 每個 C 的 structural outputs

這些在同一 \(C\) 下應與 resolver 無關：

### Local / Global rule structure

- Avg Local Rules
- Total Local Rules
- Global Rule Count
- Pairwise Jaccard (Antecedent)
- Pairwise Jaccard (Full Rule)
- Rule provenance

### Conflict workload

- Exact Conflict Group Count
- Conflict Antecedent Rate
- Conflict Rule Share
- Inference Conflict Case Count
- Conflict Case Rate

因此 structural layer 可以先寫成：

\[
S_C=
\{RuleStructure_C,ConflictWorkload_C\}
\]

---

## 每個 C 的 resolver-dependent outputs

對每個固定 structural artifact \(S_C\)，再比較四種 resolvers：

\[
S_C
\rightarrow
Resolver_p
\rightarrow
Outcome_{C,p}
\]

收集：

- Accuracy
- Balanced Accuracy
- Macro F1
- Coverage
- Conflict Resolution Accuracy
- Conflict-only Balanced Accuracy
- disagreement vs FIRST_MATCH
- Order Sensitivity / order distribution

---

## 研究鏈

Client Count Sweep 真正回答：

\[
Client\ Count
\rightarrow
Rule\ Structure
\rightarrow
Conflict\ Workload
\rightarrow
Resolver\ Outcome
\rightarrow
Performance
\]

換句話說，不是單純問：

> C 變多，accuracy 有沒有變？

而是問：

> C 變多後，local rules 怎麼分化、global overlap 怎麼變、conflict workload 怎麼變、固定 resolver 如何受到影響？

---

## Frozen UCI3 的主要 structural evidence

### Inference Conflict Case Rate：C=2 → C=5

Hayes-Roth：

\[
0.1154\rightarrow0.6538
\]

Car Evaluation：

\[
0.2457\rightarrow0.6069
\]

Balance Scale：

\[
0.3730\rightarrow0.6587
\]

三個 dataset 的 endpoint 都上升。

但 Hayes-Roth 中間 C=4 相較 C=3 有回落，因此不能寫：

\[
C\uparrow\Rightarrow CCR\ strictly\ monotonic\uparrow
\]

安全說法是：

> 在 frozen UCI3 的 C=2 與 C=5 endpoint 比較中，更高 client fragmentation 均伴隨 substantially higher inference conflict workload。

---

## FIRST_MATCH order risk

C=5 的 Order Sensitivity Rate：

- Hayes-Roth：0.5769
- Car Evaluation：0.2370
- Balance Scale：0.5794

這說明 client count 不只可能改 conflict workload，也可能放大 FIRST_MATCH 的 arrival-order risk。

但 order sensitivity 是 policy-specific outcome，不是 structural conflict definition。

---

## Rule count 不是充分解釋

Balance Scale：

Global rules：

\[
209\rightarrow200\rightarrow181\rightarrow183
\]

Inference conflict rate：

\[
0.373\rightarrow0.492\rightarrow0.587\rightarrow0.659
\]

rule count 大致下降，但 conflict 持續增加。

因此更合理的 mechanism 是：

\[
Coverage\ Overlap
+
Decision\ Disagreement
\]

而不是單純：

\[
More\ Rules\Rightarrow More\ Conflict
\]

---

## Sweep 中不能改的東西

Client Count Sweep 不應重新定義：

- LEM2 core semantics；
- reduct mathematics；
- full rule identity；
- exact conflict definition；
- inference conflict definition；
- resolver formulas。

每個 C 只是改變資料如何被切成 clients，然後觀察整條 frozen pipeline 的結果。

---

## 下一階段 robustness

目前 frozen evidence 已足夠支持 mechanism / diagnostic discussion，但若要強化論文主張，下一階段優先項應是：

1. repeated seeds / repeated splits；
2. 每個 C 的 mean / std / confidence interval；
3. conflict workload 與 resolver outcome 的統計關聯；
4. 再考慮 adaptive resolver。

也就是先確認：

\[
Observed\ Pattern
\]

是不是能跨 split 重現，再進一步提出：

\[
New\ Resolver
\]

---

## 老師問法

### 「Client Sweep 是不是另一個演算法？」

不是。它是外層 experimental factor，改變 \(C\)，而不是改 LEM2 / aggregation / resolver 定義。

### 「C 越多 conflict 就一定越多嗎？」

目前三個 datasets 的 C=2 → C=5 endpoint 都上升，但不是逐 C 嚴格單調，所以只能做 empirical association claim，不能寫成數學必然。
