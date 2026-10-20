# Module 07 — Client Count Sweep

## 目的

Client Count Sweep 不是新的演算法層，而是包在整條 federated LEM2 pipeline 外面的實驗框架。

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

## 每個 C 要收集的輸出

### Local / Global rule structure

- Avg Local Rules
- Total Local Rules
- Global Rule Count
- Pairwise Jaccard (Antecedent)
- Pairwise Jaccard (Full Rule)
- provenance

### Conflict

- Exact Conflict Group Count
- Conflict Antecedent Rate
- Conflict Rule Share
- Inference Conflict Case Count
- Conflict Case Rate

### Resolution

- FIRST_MATCH
- SIMPLE_VOTING
- STANDARD_VOTING
- GLOBAL_STRENGTH

### Evaluation

- Balanced Accuracy
- Macro F1
- Coverage
- Conflict Resolution Accuracy / conflict-only Balanced Accuracy
- Order Sensitivity Rate

## 研究問題

Client Count Sweep 真正回答的是：

\[
Client\ Count
\rightarrow
Rule\ Structure
\rightarrow
Conflict
\rightarrow
Resolution
\rightarrow
Performance
\]

也就是：client fragmentation 增加後，local rule diversity、global conflict workload、arrival-order risk 與 resolver effectiveness 如何改變。

## 目前 frozen UCI3 evidence 的安全結論

從 C=2 到 C=5：

- Hayes-Roth inference conflict rate：0.1154 → 0.6538
- Car Evaluation：0.2457 → 0.6069
- Balance Scale：0.3730 → 0.6587

但不能宣稱每增加一個 client 都必然單調增加，因為 Hayes-Roth 中間有回落。

FIRST_MATCH 的 order sensitivity 在 C=5：

- Hayes-Roth：0.5769
- Car Evaluation：0.2370
- Balance Scale：0.5794

因此現有 evidence 支持：client fragmentation 增加與更高 inference conflict workload、較高 FIRST_MATCH order risk 有明顯關聯，但不是單一 rule-count 或 exact-conflict 指標可以完整解釋。

## 重要邊界

Client Count Sweep 不應修改：

- LEM2 core semantics
- reduct mathematics
- conflict definition

它只是改變 \(C\)，觀察整條 pipeline 的輸出如何變化。
