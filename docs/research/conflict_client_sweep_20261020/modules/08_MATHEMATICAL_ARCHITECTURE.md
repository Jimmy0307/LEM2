# Module 08 — Federated LEM2 整套數學架構與四種 Resolver 比較

## 0. 目的

本文件把目前 frozen baseline 的數學物件、資料流、aggregation、conflict、四種 resolver 與 evaluation 放進同一套符號系統。

核心研究鏈：

\[
Client\ Data
\rightarrow
Local\ LEM2
\rightarrow
Federated\ Aggregation
\rightarrow
Global\ Rule\ Set
\rightarrow
Conflict\ Audit
\rightarrow
Resolver
\rightarrow
Prediction
\rightarrow
Evaluation
\]

Client Count Sweep \(C\in\{2,3,4,5\}\) 位於整條流程外層。

---

## 1. 統一符號

- \(C\)：client 數量。
- \(U_c\)：client \(c\) 的 training objects。
- \(U_{train}=\bigsqcup_{c=1}^{C}U_c\)：所有 client training objects 的不交聯集。
- \(D(z)\)：object \(z\) 的真實 decision。
- \(R_c\)：client \(c\) 的 local LEM2 rule set。
- \(R_G\)：aggregation 後的 global rule set。
- \(r:Ante(r)\rightarrow d_r\)：一條 rule。
- \(x\models Ante(r)\)：test case \(x\) 符合 rule antecedent。
- \(M(x)=\{r\in R_G:x\models Ante(r)\}\)：所有 matching global rules。
- \(M_d(x)=\{r\in M(x):d_r=d\}\)：支持 decision \(d\) 的 matching rules。
- \(d_0\)：default class；federated 路徑為所有 client class counts 合併後的 majority class。

完整 rule identity：

\[
key(r)=(sorted(Ante(r)),d_r)
\]

因此同 antecedent、不同 decision 的 rules 是不同完整規則：

\[
X\rightarrow A \neq X\rightarrow B
\]

---

## 2. Local LEM2

對 client \(c\)：

\[
R_c=LEM2(U_c)
\]

對 decision concept \(B\)，selector \(t=(a,v)\) 的 block 為：

\[
[t]=\{z:a(z)=v\}
\]

complex \(T=\{t_1,\ldots,t_k\}\) 的 block：

\[
[T]=\bigcap_{t\in T}[t]
\]

frozen implementation 持續增加 selector，直到：

\[
[T]\neq\emptyset,
\qquad
[T]\subseteq B
\]

形成 certain rule：

\[
T\rightarrow d
\]

selector minimization 只允許在移除 selector 後仍保持 non-empty 且 \([T]\subseteq B\) 時刪除；rule-set reduction 再移除可被其他 rules 完整覆蓋的 complex。

### 本層不變條件

後面的 aggregation 或 resolver 比較都不得修改 local LEM2 core；否則就無法判斷 performance 差異究竟來自 local induction 還是 global decision mechanism。

---

## 3. Federated Aggregation

一般化寫法：

\[
R_G=\mathcal A(R_1,\ldots,R_C)
\]

### 3.1 Frozen baseline：UNION

\[
R_G=\bigcup_{c=1}^{C}R_c
\]

若：

\[
freq(r)=|\{c:r\in R_c\}|
\]

則：

\[
R_G^{UNION}=\{r:freq(r)\ge1\}
\]

同一 full rule 重複出現時，global list 只保留第一個 occurrence，但 provenance 保留所有產生該 rule 的 clients：

\[
Prov(r)=\{c:r\in R_c\}
\]

global list order 因此保留 client order，再保留各 client 內部 LEM2 order。這個順序只會直接影響 FIRST_MATCH。

### 3.2 比較用候選，不是目前 production baseline

INTERSECTION：

\[
R_G^{INT}=\bigcap_{c=1}^{C}R_c
=\{r:freq(r)=C\}
\]

QUORUM：

\[
R_G^{Q}=\{r:freq(r)\ge q\}
\]

若採過半：

\[
q=\left\lceil\frac C2\right\rceil
\]

目前 frozen production aggregation 是 UNION；INTERSECTION / QUORUM 只作為後續 aggregation research candidate，不能寫成已實作 baseline。

---

## 4. Rule Structure

### 4.1 Pairwise rule Jaccard

對 client \(i,j\)：

\[
J(R_i,R_j)=\frac{|R_i\cap R_j|}{|R_i\cup R_j|}
\]

目前同時可看：

- antecedent-only signature；
- full-rule signature \((Antecedent,Decision)\)。

平均 pairwise Jaccard：

\[
\bar J=\frac{2}{C(C-1)}\sum_{i<j}J(R_i,R_j)
\]

rule heterogeneity 可視為：

\[
H_{rule}=1-\bar J_{full}
\]

注意：

\[
Low\ Jaccard\not\Rightarrow High\ Conflict
\]

因為不同 antecedents 仍可能 cover 同一 test case。

---

## 5. Conflict Audit

Conflict 必須在 resolver 之前定義。

### 5.1 Exact antecedent conflict

對 antecedent \(a\)：

\[
D(a)=\{d_r:Ante(r)=a\}
\]

若：

\[
|D(a)|>1
\]

則 \(a\) 是 exact conflict group。

### 5.2 Inference-level conflict

對 test case \(x\)：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

若：

\[
|\{d_r:r\in M(x)\}|>1
\]

則 \(x\) 是 inference conflict case。

Conflict Case Rate：

\[
CCR=\frac{|X_{conflict}|}{N_{test}}
\]

其中：

\[
X_{conflict}=\{x:|\{d_r:r\in M(x)\}|>1\}
\]

這個 conflict set 對同一 frozen global rule artifact 而言應該與 resolver 無關。

---

## 6. Resolver 的共同輸入與輸出

四種 resolver 都使用同一個：

\[
M(x)
\]

最後都必須輸出單一 decision：

\[
\hat y(x)\in\mathcal D
\]

若：

\[
M(x)=\emptyset
\]

則所有 policy 都輸出 default class：

\[
\hat y(x)=d_0
\]

對 SIMPLE / STANDARD / GLOBAL_STRENGTH，若最高 score 有多個 winners，程式的共同 tie rule 為：

1. 若 default class \(d_0\) 在 winners 中，選 \(d_0\)；
2. 否則選字串排序最小的 winner。

實作使用 `np.isclose` 判定浮點 score tie。

---

## 7. Resolver 1 — FIRST_MATCH

令 global rules 有固定順序：

\[
R_G=(r_1,r_2,\ldots,r_m)
\]

定義最早 matching rule：

\[
k^*(x)=\min\{k:x\models Ante(r_k)\}
\]

則：

\[
\hat y_{FM}(x)=d_{r_{k^*(x)}}
\]

### 使用的 evidence

只有「位置最前面的 matching rule」。

### 數學特性

- 不計 rule 數量；
- 不計 support；
- 不做 class-size normalization；
- 對 global rule order 敏感。

因 global list order 保留 client order：

\[
Client\ Order
\rightarrow
Rule\ Order
\rightarrow
Prediction
\]

因此需要另外計算 Order Sensitivity Rate。

---

## 8. Resolver 2 — SIMPLE_VOTING

每條 matching rule 一票：

\[
S_{SV}(d|x)=|M_d(x)|
\]

等價於：

\[
S_{SV}(d|x)=\sum_{r\in M(x)}I[d_r=d]
\]

最後：

\[
\hat y_{SV}(x)=TieResolve\left(\arg\max_d S_{SV}(d|x),d_0\right)
\]

### 使用的 evidence

只看 supporting rule count。

### 數學特性

- 每條 rule 權重完全相同；
- 不看一條 rule 有多少 training support；
- 不做 class-size normalization；
- 對 client arrival order 不敏感。

---

## 9. Resolver 3 — STANDARD_VOTING

### 9.1 Federated frozen baseline 的 rule support

對任一 global rule \(r\)，在每個 client 上重新評估：

\[
Supp_c(r)=
\{z\in U_c:z\models Ante(r)\land D(z)=d_r\}
\]

因 client partitions 不交：

\[
S_G(r)=\bigsqcup_{c=1}^{C}Supp_c(r)
\]

rule weight：

\[
w(r)=Supp_G(r)=|S_G(r)|
=\sum_{c=1}^{C}|Supp_c(r)|
\]

注意：這不是只看產生該 rule 的 provenance clients；final audit 後是把**每一條 global rule 在所有 clients 上重新評估**。

而且 federated final baseline 的 support 是 decision-consistent：

\[
z\models Ante(r)
\quad\text{且}\quad
D(z)=d_r
\]

才計入。

### 9.2 Voting

\[
S_{STD}(d|x)
=
\sum_{r\in M_d(x)}w(r)
\]

最後：

\[
\hat y_{STD}(x)
=
TieResolve\left(\arg\max_dS_{STD}(d|x),d_0\right)
\]

### 使用的 evidence

每條 matching rule 在 pooled training data 上的正向 support 數量。

### 數學特性

- rule support 越大，票越重；
- 同一 training object 若同時支持兩條相同 decision 的 rules，可能在兩條 rule weight 中各被計一次；
- 不除以 class size；
- 對 arrival order 不敏感。

這個「可能跨 rules 重複計算同一 object」正是它與 GLOBAL_STRENGTH 的重要差異。

---

## 10. Resolver 4 — GLOBAL_STRENGTH

對 decision \(d\) 的 matching rules，先把所有 positive support objects 做集合聯集：

\[
S_d(x)
=
\bigcup_{r\in M_d(x)}S_G(r)
\]

再以該 decision class size 正規化：

\[
N_d=|\{z\in U_{train}:D(z)=d\}|
\]

\[
GS(d|x)
=
\frac{|S_d(x)|}{N_d}
\]

最後：

\[
\hat y_{GS}(x)
=
TieResolve\left(\arg\max_dGS(d|x),d_0\right)
\]

### 使用的 evidence

「這一群 matching rules 合起來，可以覆蓋該 decision class 中多少不重複的 training objects」。

### 數學特性

- 同一 object 被多條同 decision rules cover 時只算一次；
- 有 class-size normalization；
- score 可解讀為 matching-rule coalition 對該 class 的覆蓋比例；
- 對 arrival order 不敏感。

---

## 11. 四種 resolver 的核心差別

| Resolver | 核心問題 | Score / 選擇方式 | 是否使用 support | 同 object 可否跨 rule 重複計數 | 是否 class-normalized | Arrival-order sensitive |
|---|---|---|---|---|---|---|
| FIRST_MATCH | 誰先出現？ | 最早 matching rule | 否 | 不適用 | 否 | 是 |
| SIMPLE_VOTING | 哪個 decision 的 matching rules 比較多？ | \(|M_d(x)|\) | 否 | 不適用 | 否 | 否 |
| STANDARD_VOTING | 哪個 decision 累積的 rule support 比較大？ | \(\sum_{r\in M_d}w(r)\) | 是 | **可以** | 否 | 否 |
| GLOBAL_STRENGTH | 哪個 decision 的 matching-rule coalition 覆蓋其 class 比例更高？ | \(|\cup S_G(r)|/N_d\) | 是 | **不可以** | **是** | 否 |

最重要的數學差異不是名稱，而是 evidence aggregation 的層次：

\[
\boxed{
Order
\rightarrow
Rule\ Count
\rightarrow
Rule\ Support\ Sum
\rightarrow
Unique\ Object\ Coverage\ Ratio
}
\]

---

## 12. 同一個 A/B 例子

假設 test case \(x\) match：

\[
r_1\rightarrow A,
\quad
r_2\rightarrow A,
\quad
r_3\rightarrow B
\]

且：

\[
w(r_1)=100,
\quad
w(r_2)=50,
\quad
w(r_3)=120
\]

### FIRST_MATCH

若 order 是 \(r_3,r_1,r_2\)，輸出 \(B\)；若 order 是 \(r_1,r_2,r_3\)，輸出 \(A\)。

### SIMPLE_VOTING

\[
S_{SV}(A)=2,
\qquad
S_{SV}(B)=1
\]

所以選 \(A\)。

### STANDARD_VOTING

\[
S_{STD}(A)=100+50=150
\]

\[
S_{STD}(B)=120
\]

所以選 \(A\)。

### GLOBAL_STRENGTH

假設兩條 A rules 的 support 高度重疊：

\[
|S_G(r_1)\cup S_G(r_2)|=110
\]

且：

\[
N_A=500
\]

則：

\[
GS(A|x)=110/500=0.22
\]

若：

\[
|S_G(r_3)|=120,
\qquad
N_B=200
\]

則：

\[
GS(B|x)=120/200=0.60
\]

因此 GLOBAL_STRENGTH 反而選 \(B\)。

同一個 structural conflict 可以因 evidence aggregation 定義不同而得到不同 prediction。

---

## 13. Evaluation

### Balanced Accuracy

\[
BA=\frac1K\sum_{k=1}^{K}Recall_k
\]

### Macro F1

\[
MacroF1=\frac1K\sum_{k=1}^{K}F1_k
\]

### Coverage

\[
Coverage=
\frac{|\{x:M(x)\neq\emptyset\}|}{N_{test}}
\]

### Conflict Resolution Accuracy

\[
CRA=
\frac{|\{x\in X_{conflict}:\hat y(x)=y(x)\}|}{|X_{conflict}|}
\]

另報 conflict-only Balanced Accuracy，避免 overall metrics 掩蓋 resolver 真正處理 conflict 時的表現。

### Order Sensitivity

令 \(\Pi_C\) 為 client order permutations。若：

\[
|\{\hat y_{\pi}(x):\pi\in\Pi_C\}|>1
\]

則 \(x\) 為 order-sensitive。

\[
OSR=
\frac{\#order-sensitive\ test\ cases}{N_{test}}
\]

當 \(C\le5\) 時最多 \(5!=120\) 個 order，目前 frozen 設定可完整枚舉。

---

## 14. 公平比較的控制條件

四個 resolver 的比較必須固定：

\[
Local\ Rules,
R_G,
Conflict\ Cases,
Train/Test\ Split
\]

只替換：

\[
Resolver
\]

因此正確實驗邏輯為：

```text
同一 RuleSystemArtifact
        ↓
同一 M(x) / conflict workload
        ↓
FIRST / SIMPLE / STANDARD / GLOBAL
        ↓
比較 prediction 與 metrics
```

如果每個 resolver 重新跑 local LEM2 或重建 global rule set，就無法把差異歸因於 conflict resolution。

---

## 15. Client Count Sweep 的角色

對：

\[
C\in\{2,3,4,5\}
\]

每一個 C 都重跑同一條 pipeline：

\[
C
\rightarrow
R_c
\rightarrow
R_G
\rightarrow
Rule\ Structure
\rightarrow
Conflict
\rightarrow
Resolver
\rightarrow
Performance
\]

因此 Client Count Sweep 不是第五種 resolver，也不是 aggregation operator；它是外層 experimental factor。

---

## 16. 目前研究可以安全下的結論

1. exact conflict 與 inference conflict 必須分開。
2. FIRST_MATCH 的主要結構風險是 client-order dependence。
3. SIMPLE_VOTING 消除 order dependence，但把所有 rules 視為等權。
4. STANDARD_VOTING 使用 pooled decision-consistent rule support，但可能跨 matching rules 重複計算同一 training object。
5. GLOBAL_STRENGTH 以 unique support-object union 消除重複計數，並用 class size 正規化。
6. 四種 resolver 使用的 evidence 定義不同，因此不能只用「投票方式不同」概括。
7. frozen UCI3 evidence 沒有 universal winner；best resolver 具有 dataset/workload dependency。

---

## 17. 程式對照

- Local LEM2：`roughset/core.py::induce_lem2`
- Rule identity：`roughset/core.py::Rule.key`
- Federated UNION：`roughset/federated.py::union_rules_with_provenance`
- Rule Jaccard：`roughset/evaluation.py::pairwise_rule_jaccard`
- Exact conflict：`roughset/evaluation.py::audit_rule_conflicts`
- Pre-resolution inference conflict：`roughset/pipeline.py::_pre_resolution_conflicts`
- Pooled federated support：`roughset/pipeline.py::global_rule_support_context`
- Resolver：`roughset/evaluation.py::predict_with_policy`
- Order sensitivity：`roughset/federated.py::audit_order_sensitivity`, `audit_order_distribution`

---

## 18. 老師問法對應

### 「聯集在哪？」

在 local LEM2 之後、global rule set 建立時：

\[
R_G=\bigcup_cR_c
\]

不是 Jaccard 的分母，也不是 GLOBAL_STRENGTH 的 support-set union。

### 「Conflict 在哪？」

在 \(R_G\) 建立之後、resolver 之前。先定義 conflict，才能公平比較 resolver。

### 「四種算法到底差在哪？」

它們都不改 LEM2，也不改 global rules；差別只在同一組 matching rules \(M(x)\) 上如何把 evidence 壓縮成一個 decision：

\[
FIRST=順序,
\quad
SIMPLE=規則數,
\quad
STANDARD=rule\ support\ sum,
\quad
GLOBAL=unique\ class\ coverage\ ratio.
\]

### 「你們現在有最佳解嗎？」

沒有。現有 evidence 支持的是 resolver effectiveness 依 dataset、rule structure、conflict workload 與 client configuration 而變，不支持 universal winner。
