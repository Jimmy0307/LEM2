# Module 05 — Conflict Resolution

## 目的

這一層只回答：當同一個 test case 同時得到多個 decision evidence 時，最後如何輸出單一 prediction。

本層不修改：

- local LEM2；
- federated aggregation；
- global rule identity；
- pre-resolution conflict definition。

輸入：

\[
M(x)=\{r\in R_G\mid x\models Ante(r)\}
\]

以及：

\[
M_d(x)=\{r\in M(x):d_r=d\}
\]

輸出：

\[
\hat y(x)\in\mathcal D
\]

若 \(M(x)=\emptyset\)，四種 policy 都回傳 default class \(d_0\)。Federated default 為 pooled client class counts 的 majority class。

---

## 共同 tie rule

SIMPLE_VOTING、STANDARD_VOTING、GLOBAL_STRENGTH 都先產生 decision score。

令：

\[
S^*=\max_d S(d|x)
\]

以及 winners：

\[
W=\{d:S(d|x)\approx S^*\}
\]

程式使用 `np.isclose` 判定浮點 tie。

最後：

1. 若 default class \(d_0\in W\)，選 \(d_0\)；
2. 否則選字串排序最小的 winner。

---

## 1. FIRST_MATCH

令 ordered global rule list 為：

\[
R_G=(r_1,\ldots,r_m)
\]

最早符合的 rule：

\[
k^*(x)=\min\{k:x\models Ante(r_k)\}
\]

prediction：

\[
\hat y_{FM}(x)=d_{r_{k^*(x)}}
\]

它使用的 evidence 只有「誰先出現」。

因此：

\[
Client\ Order
\rightarrow
Global\ Rule\ Order
\rightarrow
Prediction
\]

FIRST_MATCH 對 arrival order 敏感。

---

## 2. SIMPLE_VOTING

每條 matching global rule 一票：

\[
S_{SV}(d|x)=|M_d(x)|
\]

等價於：

\[
S_{SV}(d|x)=\sum_{r\in M(x)}I[d_r=d]
\]

選 score 最大的 decision，再套共同 tie rule。

它只回答：

> 哪個 decision 的 matching rules 比較多？

所有 rules 等權，不看 training support。

---

## 3. STANDARD_VOTING

### Federated frozen baseline 的 support 定義

Final mathematical audit 後，對**每一條 global rule** \(r\)，會在**所有 clients** 上重新評估 support，不只看產生該 rule 的 provenance clients。

對 client \(c\)：

\[
Supp_c(r)
=
\{z\in U_c:z\models Ante(r)\land D(z)=d_r\}
\]

因 client partitions 不交：

\[
S_G(r)=\bigsqcup_{c=1}^{C}Supp_c(r)
\]

rule weight：

\[
w(r)=|S_G(r)|
=\sum_{c=1}^{C}|Supp_c(r)|
\]

因此 federated STANDARD_VOTING 使用的是 **pooled, decision-consistent positive support**。

Voting score：

\[
S_{STD}(d|x)
=
\sum_{r\in M_d(x)}w(r)
\]

它回答：

> 支持某 decision 的 matching rules，累積起來有多少正向 training support？

### 重要特性

若同一個 training object 同時支持兩條相同 decision 的 matching rules，它可能分別存在兩條 rule 的 \(w(r)\) 中，因此在 score sum 中重複貢獻。

這不是 bug，而是 STANDARD_VOTING 與 GLOBAL_STRENGTH 的主要數學差異之一。

---

## 4. GLOBAL_STRENGTH

對 decision \(d\)，先把所有 matching rules 的 positive support objects 做集合聯集：

\[
S_d(x)
=
\bigcup_{r\in M_d(x)}S_G(r)
\]

class size：

\[
N_d=|\{z\in U_{train}:D(z)=d\}|
\]

Global Strength：

\[
GS(d|x)
=
\frac{|S_d(x)|}{N_d}
\]

prediction：

\[
\hat y_{GS}(x)
=
TieResolve\left(\arg\max_dGS(d|x),d_0\right)
\]

因 numerator 是 set union，同一 training object 即使被多條同 decision matching rules cover，也只算一次。

所以它回答：

> 目前這群 matching rules 合起來，真正覆蓋了該 decision class 多少比例？

---

## 四種方法真正的數學差別

| Resolver | 使用的 evidence | 同 object 跨 rules 是否可能重複計數 | class-size normalization | Arrival-order sensitive |
|---|---|---|---|---|
| FIRST_MATCH | 最早 matching rule | 不適用 | 否 | 是 |
| SIMPLE_VOTING | matching rule 數量 | 不適用 | 否 | 否 |
| STANDARD_VOTING | pooled positive rule support 加總 | 是 | 否 | 否 |
| GLOBAL_STRENGTH | unique positive support-object coverage | 否 | 是 | 否 |

可以壓成：

\[
\boxed{
Order
\rightarrow
Rule\ Count
\rightarrow
Rule\ Support\ Sum
\rightarrow
Unique\ Class\ Coverage\ Ratio
}
\]

---

## Production implementation

- `roughset/evaluation.py::predict_with_policy`
- `roughset/pipeline.py::global_rule_support_context`
- `roughset/evaluation.py::fit_rule_support_sets`
- `roughset/evaluation.py::aggregate_rule_support_context`
- `roughset/federated.py::audit_order_sensitivity`
- `roughset/federated.py::audit_order_distribution`

注意：`evaluation.fit_rule_weights` 仍存在，且 centralized 路徑可使用 antecedent coverage；但 **frozen federated final pipeline 的 STANDARD_VOTING weight 應以 `pipeline.global_rule_support_context` 為準**。

完整統一數學請見：`08_MATHEMATICAL_ARCHITECTURE.md`。

---

## 目前研究結論

Frozen UCI3 evidence 不支持任何單一 resolver 全面勝出。

因此目前應把 resolver 視為 dataset/workload-dependent 的第二層 decision mechanism，而不是把某個 fixed resolver 當成最終答案。
