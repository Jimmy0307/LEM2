# Module 05 — Conflict Resolution

## 目的

這一層只回答：當同一個 test case 同時得到 A/B 等不同 decision evidence 時，最後如何輸出單一 prediction。

輸入：

\[
M(x)=\{r\in R_G\mid x\models Ante(r)\}
\]

以及其中各 decision 的 evidence。

輸出：

\[
\hat y(x)\in\{d_1,d_2,\ldots\}
\]

## FIRST_MATCH

依 global rule order 找第一條 matching rule：

\[
\hat y=d(r_{first})
\]

優點：簡單。

主要問題：如果 global rule order 受 client arrival order 影響，prediction 也可能改變。

## SIMPLE_VOTING

每條 matching rule 一票：

\[
Score(d|x)=\sum_{r\in M(x)}I[d(r)=d]
\]

選得票最高的 decision。

## STANDARD_VOTING

每條 matching rule 依 training antecedent support 加權：

\[
w(r)=|\{x_i:x_i\models Ante(r)\}|
\]

\[
Score(d|x)=\sum_{r\in M_d(x)}w(r)
\]

選 weighted score 最大的 decision。

## GLOBAL_STRENGTH

對同一 decision 的 matching rules，先做 support-object set union：

\[
S_d(x)=\bigcup_{r\in M_d(x)}Supp(r)
\]

再除以該 decision class 的大小：

\[
Strength(d|x)=\frac{|S_d(x)|}{|Class_d|}
\]

最後：

\[
\hat y=\arg\max_d Strength(d|x)
\]

因為 numerator 使用 set union，同一 training object 即使被多條 matching rules cover，也只計一次。

## 核心原則

這一層不改 local LEM2，也不改 aggregation 後的 structural conflict。

它只回答：

> 已知 A、B 都有 evidence，最後該相信誰？

## Production implementation

- `roughset/evaluation.py::predict_with_policy`
- `fit_rule_weights`
- `fit_rule_support_sets`
- `aggregate_rule_weights`
- `aggregate_rule_support_context`

## 現有研究結論

Frozen UCI3 evidence 不支持任何單一 resolver 全面勝出。

因此目前應把 resolver 視為 dataset/workload-dependent 的第二層 decision mechanism，而不是把某個 fixed resolver 當成最終答案。
