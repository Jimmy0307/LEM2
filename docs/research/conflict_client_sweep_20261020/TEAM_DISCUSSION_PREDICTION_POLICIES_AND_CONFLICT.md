# 組員討論版：四種 Prediction Policies + 兩種 Conflict

> 用途：組內分工與討論。
>
> 這份只抽出大家需要共同理解、共同重現、共同討論的核心。不要把四種方法寫成我們新發明的演算法；它們有既有文獻來源，我們的研究重點是把它們放進同一個 Federated LEM2 artifact 下公平比較。

---

# 1. 先統一名詞

四個方法正式稱：

\[
\boxed{Prediction\ Policies}
\]

也就是：

```text
FIRST_MATCH
SIMPLE_VOTING
STANDARD_VOTING
GLOBAL_STRENGTH
```

在研究問題裡，它們的功能是處理 conflict，所以可以說：

> 「我們比較四種 prediction policies 在 conflict cases 上的 conflict-resolution behavior。」

但不要把四個共同正式命名成「四個 resolver 演算法」。

Production code 名稱也是：

```python
predict_with_policy(..., policy=...)
```

---

# 2. 大流程

```text
Client 1 data ─→ Local LEM2 ─→ R1
Client 2 data ─→ Local LEM2 ─→ R2
...
Client C data ─→ Local LEM2 ─→ RC
                         │
                         ▼
                  UNION Aggregation
                         │
                         ▼
                  Global Rule Set RG
                         │
                         ▼
                    Conflict Audit
                  ┌──────┴──────┐
                  ▼             ▼
             Exact Conflict  Inference Conflict
                  │             │
                  └──────┬──────┘
                         ▼
                  Prediction Policy
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
 FIRST_MATCH       SIMPLE_VOTING    STANDARD_VOTING
                                         │
                                         ▼
                                  GLOBAL_STRENGTH
                         │
                         ▼
                    Single Decision
                         │
                         ▼
                      Evaluation
```

真正研究鏈：

\[
Client\ Count
\rightarrow
Rule\ Structure
\rightarrow
Conflict
\rightarrow
Prediction\ Policy
\rightarrow
Performance
\]

---

# 3. 兩種 Conflict

## 3.1 Exact Antecedent Conflict

同一個 antecedent，卻有不同 decision。

例如：

\[
X\rightarrow A
\]

\[
X\rightarrow B
\]

定義：

\[
D(a)=\{d_r:Ante(r)=a\}
\]

若：

\[
|D(a)|>1
\]

就是 Exact Conflict。

Code：

```text
roughset/evaluation.py
└─ audit_rule_conflicts(...)
```

它回答：

> Global Rule Set 本身有沒有「同條件、不同結論」？

---

## 3.2 Inference-Level Conflict

不要求 antecedent 完全相同。

只要某一筆 test case 同時命中不同 decision 的 rules，就形成 conflict。

對 test case \(x\)：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

如果：

\[
|\{d_r:r\in M(x)\}|>1
\]

就是 Inference Conflict。

例如：

```text
A=1       → Yes
A=1,B=2   → No
```

測試資料：

```text
A=1,B=2
```

兩條都 match，所以 prediction 階段出現 Yes / No 競爭。

Code：

```text
roughset/pipeline.py
└─ _pre_resolution_conflicts(...)
```

核心指標：

\[
CCR=
\frac{|X_{conflict}|}{N_{test}}
\]

### 為什麼兩種要分開？

因為：

\[
ExactConflict=0
\]

不代表：

\[
InferenceConflict=0
\]

我們 frozen Car Evaluation C=2 就是：

```text
Exact conflict groups = 0
Inference conflict cases = 85 / 346
Inference conflict rate = 0.245664740
```

所以只查「同 antecedent 不同 decision」不夠。

---

# 4. 四種 Prediction Policies

所有方法使用同一個：

\[
M_d(x)=
\{r\in R_G:x\models Ante(r),d_r=d\}
\]

最後都只輸出：

\[
\hat y(x)=A\quad\text{or}\quad B\quad\text{or another single class}
\]

不會輸出 A+B。

---

## Policy 1 — FIRST_MATCH

### 問題

> 誰先出現？

Ordered global rules：

\[
R_G=(r_1,r_2,\ldots,r_m)
\]

第一條符合 test case 的 rule：

\[
k^*(x)=\min\{k:x\models Ante(r_k)\}
\]

prediction：

\[
\hat y_{FM}(x)=d_{r_{k^*(x)}}
\]

### Example

```text
r1: X → A
r2: X → B
```

順序 `[r1,r2]`：

```text
A
```

順序 `[r2,r1]`：

```text
B
```

### 最大問題

\[
Client\ Arrival\ Order
\rightarrow
Global\ Rule\ Order
\rightarrow
Prediction
\]

所以會有 order sensitivity。

### Literature

Woźniak et al. (2026), *Rule-Based Federated Learning for Healthcare*.

這是原 Healthcare paper 的 inference baseline。

### 組員要會做

- 重現 first-match；
- 改 client order；
- 比較 prediction 是否改變；
- 算 Order Sensitivity Rate。

---

## Policy 2 — SIMPLE_VOTING

### 問題

> 哪個 decision 的 matching rules 比較多？

公式：

\[
S_{SV}(d|x)=|M_d(x)|
\]

Example：

```text
A rules = 3
B rules = 2
```

則：

\[
A
\]

### 特性

```text
強 rule = 1 票
弱 rule = 1 票
```

完全不看 support。

### Literature

RSES Simple Voting；Lazo-Cortés et al. (2020).

DOI:

`10.1007/978-3-030-49076-8_7`

### 組員要會做

- 收集所有 matching rules；
- 按 decision groupby；
- 每條 rule +1；
- 比較最高票 decision。

Pseudo-code：

```python
votes = {}
for rule in matching_rules:
    votes[rule.decision] += 1
prediction = argmax(votes)
```

---

## Policy 3 — STANDARD_VOTING

### 問題

> 哪個 decision 的 matching rules 累積正向 support 比較大？

對 global rule \(r\)，client \(c\) 的 positive support：

\[
Supp_c(r)=
\{z\in U_c:
 z\models Ante(r)
 \land
 D(z)=d_r
\}
\]

所有 clients：

\[
S_G(r)=\bigsqcup_{c=1}^{C}Supp_c(r)
\]

rule weight：

\[
w(r)=|S_G(r)|
\]

policy score：

\[
S_{STD}(d|x)
=
\sum_{r\in M_d(x)}w(r)
\]

### Example

```text
r1 → A, support = 100
r2 → A, support = 50
r3 → B, support = 120
```

A：

\[
100+50=150
\]

B：

\[
120
\]

所以：

\[
A
\]

### 最大差異

同一 training object 如果同時支持兩條 A rules：

```text
object z supports r1
object z supports r2
```

STANDARD 的：

\[
w(r_1)+w(r_2)
\]

裡面它可能被貢獻兩次。

### Literature

RSES Standard Voting；Lazo-Cortés et al. (2020).

RSES 定義是「每條 rule 擁有與 supporting objects 數量相同的 votes」。

### 我們的 Federated adaptation

原本 rule-support voting 被放進 federated context：

> 每一條 global rule 都在所有 clients 上重新計算 decision-consistent positive support。

不是只看產生該 rule 的 client。

Code：

```text
roughset/pipeline.py
└─ global_rule_support_context(...)

roughset/evaluation.py
└─ predict_with_policy(...)
   └─ STANDARD_VOTING
```

### 組員要會做

- 對每條 global rule 重新跑所有 clients；
- antecedent match + true decision 相同才算 support；
- rule weights 按 decision 加總；
- 理解它可能 double-count object across rules。

---

## Policy 4 — GLOBAL_STRENGTH

### 問題

> 這群 matching rules 合起來，真正覆蓋這個 class 多少比例？

對 decision \(d\)：

\[
S_d(x)=
\bigcup_{r\in M_d(x)}S_G(r)
\]

然後：

\[
N_d=|\{z\in U_{train}:D(z)=d\}|
\]

\[
GS(d|x)=
\frac{|S_d(x)|}{N_d}
\]

### Example

A 有兩條 rules：

```text
r1 support count = 100
r2 support count = 50
```

STANDARD：

\[
100+50=150
\]

但如果很多 support objects 重複，聯集實際只有：

\[
|S_G(r_1)\cup S_G(r_2)|=110
\]

假設：

\[
|Class_A|=500
\]

則：

\[
GS(A)=110/500=0.22
\]

B：

\[
120/200=0.60
\]

GLOBAL_STRENGTH 最後選：

\[
B
\]

### 最大差異

STANDARD：

\[
Rule\ Support\ Sum
\]

GLOBAL：

\[
Unique\ Support\ Object\ Union
\]

所以同一 object 被多條同 decision rules cover：

```text
STANDARD：可能算多次
GLOBAL：只算一次
```

而且 GLOBAL 還會除以 class size。

### Literature

Bazan et al. (2000), *Rough Set Algorithms in Classification Problem*.

DOI:

`10.1007/978-3-7908-1840-6_3`

原文 GlobalStrength 的數學核心就是：

> matching rules cover 的 class-consistent objects 做聯集，再除以該 decision class size。

### 組員要會做

- 收集每條 matching rule 的 support-object IDs；
- 依 decision 分組；
- 做 set union；
- 除以 pooled class size；
- 比較最大值。

Pseudo-code：

```python
for decision in decisions:
    supported_objects = set()
    for rule in matching_rules_for_decision:
        supported_objects |= support_sets[rule]
    score[decision] = len(supported_objects) / class_size[decision]
```

---

# 5. 四種方法放在同一張表

| Policy | 最核心問題 | Score | 看不看 Support | 同一 object 跨 rules 可否重複 | Class normalization | Order sensitive |
|---|---|---|---|---|---|---|
| `FIRST_MATCH` | 誰先出現？ | first matching rule | 否 | N/A | 否 | **是** |
| `SIMPLE_VOTING` | 哪邊 rules 多？ | \(|M_d(x)|\) | 否 | N/A | 否 | 否 |
| `STANDARD_VOTING` | 哪邊 rule supports 加總大？ | \(\sum w(r)\) | **是** | **可以** | 否 | 否 |
| `GLOBAL_STRENGTH` | 哪邊 unique class coverage 高？ | \(|\cup S_G(r)|/N_d\) | **是** | **不可以** | **是** | 否 |

最簡單的記法：

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

# 6. 組員實作時要固定的東西

比較四種 policies 時，下面全部不能變：

```text
Train / Test Split
Client Partition
Local Reduct
Local LEM2 Rules
Global UNION Rule Set
Rule Identity
Pre-resolution Conflict Cases
Default Class
```

唯一要換的是：

```text
prediction_policy
```

也就是：

\[
Same\ Artifact
\rightarrow
Different\ Policy
\rightarrow
Different\ Outcome
\]

否則無法說 performance 差異是 policy 造成的。

---

# 7. 組員各自至少要產出的結果

每一個 dataset、每一個 client count \(C\)：

## Structural / Conflict（Policy-independent）

```text
Local rule count
Global rule count
Pairwise Jaccard antecedent
Pairwise Jaccard full-rule
Exact conflict groups
Conflict antecedent rate
Conflict rule share
Inference conflict cases
Inference conflict case rate
```

## Policy-dependent

四種 policy 都要跑：

```text
Accuracy
Balanced Accuracy
Macro F1
Coverage
Conflict Resolution Accuracy
Conflict-only Balanced Accuracy
Disagreement vs FIRST_MATCH
Order Sensitivity（至少 FIRST_MATCH）
```

---

# 8. Client Count 要一起做

固定：

\[
C\in\{2,3,4,5\}
\]

每個 C 都重新走：

```text
Local LEM2
→ UNION
→ Rule Structure
→ Conflict Audit
→ 4 Prediction Policies
→ Evaluation
```

研究問題不是只有：

```text
C ↑ → accuracy 怎樣？
```

而是：

\[
\boxed{
C
\rightarrow
Rule\ Structure
\rightarrow
Conflict
\rightarrow
Policy\ Behavior
\rightarrow
Performance
}
\]

### Literature anchor

Healthcare paper 本來就測 C=2,3,4,5，因此這個 sweep 是直接延續 source paper 的實驗設計。

更廣義 FL 文獻也把 client count 視為重要變數，例如：

- Cowlishaw et al. (2025), DOI `10.1038/s41598-025-94244-2`.
- Babar et al. (2024), DOI `10.1371/journal.pone.0302539`.

但這些只能支撐 client fragmentation / heterogeneity 的背景，不能拿來直接宣稱「client 越多 conflict 一定越多」。

---

# 9. 組內不能寫錯的幾句話

## 可以寫

> 四種方法是不同 Prediction Policies，用來比較當 competing rule evidence 存在時，最後 class prediction 如何形成。

> Exact Conflict 與 Inference Conflict 是不同層級；後者可以在前者為零時仍然存在。

> FIRST_MATCH 具有 client-arrival-order sensitivity，而三種 score-based policies 在固定 evidence context 下是 order invariant。

> Standard Voting 使用 rule-support sum；Global Strength 使用 unique support-object union / class size。

> Client Count Sweep 是外層實驗變數，不是第五種演算法。

## 不可以寫

> 我們發明了 Simple Voting / Standard Voting / Global Strength。

> Voting 一定比 FIRST_MATCH 準。

> GLOBAL_STRENGTH 一定最好。

> Client 越多，conflict 數學上一定單調增加。

> Exact conflict groups 就等於全部 conflict。

> UNION 本身就是 conflict resolution。

---

# 10. 組員分工建議

可以直接拆成以下工作包：

### A. Conflict Audit

負責：

```text
Exact Conflict
Inference Conflict
CCR
Conflict cases export
```

### B. FIRST_MATCH + Order Audit

負責：

```text
FIRST_MATCH
Client permutations
Order Sensitivity Rate
Order performance distribution
```

### C. SIMPLE + STANDARD

負責：

```text
Simple rule-count voting
Federated pooled positive support
Standard weighted voting
```

### D. GLOBAL_STRENGTH

負責：

```text
Support-object set union
Class-size normalization
Global Strength prediction
```

### E. Client Sweep + Evaluation

負責：

```text
C = 2,3,4,5
Same artifacts
4 policies
Overall + conflict-only comparison
```

最後全部必須共用同一個 mathematical contract，不可各自修改 LEM2 或 conflict definition。

---

# 11. 必讀文獻

## Source Federated LEM2

Woźniak, K., Sousa, J., & Sniezynski, B. (2026). *Rule-Based Federated Learning for Healthcare*.

DOI: `10.1007/978-3-032-29921-5_38`

用途：

```text
Federated LEM2
UNION aggregation
FIRST_MATCH
C = 2..5
```

## Simple / Standard Voting

Lazo-Cortés, M. S., Martínez-Trinidad, J. F., Carrasco-Ochoa, J. A., & Almanza-Ortega, N. N. (2020). *Towards Selecting Reducts for Building Decision Rules for Rule-Based Classifiers*.

DOI: `10.1007/978-3-030-49076-8_7`

用途：

```text
Rule conflict
Simple Voting
Standard Voting
Rule support
```

## GLOBAL_STRENGTH

Bazan, J. G., Nguyen, H. S., Nguyen, S. H., Synak, P., & Wróblewski, J. (2000). *Rough Set Algorithms in Classification Problem*.

DOI: `10.1007/978-3-7908-1840-6_3`

用途：

```text
GlobalStrength
Matching-rule coalition
Unique support-object union
Class normalization
```

## Rule Conflict

Lindgren, T. (2004). *Methods for Rule Conflict Resolution*.

DOI: `10.1007/978-3-540-30115-8_26`

Lindgren, T., & Boström, H. (2002). *Classification with Intersecting Rules*.

DOI: `10.1007/3-540-36169-3_31`

Lindgren, T., & Boström, H. (2004). *Resolving Rule Conflicts with Double Induction*.

DOI: `10.3233/IDA-2004-8503`

用途：

```text
Overlapping rules
Different class predictions
Conflict-resolution problem
```

---

# 12. 一句話版本

整個組員工作其實就是：

> 固定同一套 Federated LEM2 global rules，先把「哪裡真的有 conflict」找出來，再用 FIRST_MATCH、Simple Voting、Standard Voting、Global Strength 四種 Prediction Policies 分別決定 A/B，最後比較 client 數量 C=2..5 改變時，rule structure、conflict workload、order sensitivity 與 performance 怎麼一起變。
