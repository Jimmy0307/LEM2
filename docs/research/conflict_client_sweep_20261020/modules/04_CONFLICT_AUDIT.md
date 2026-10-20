# Module 04 — Conflict Audit

## 目的

這一層只回答：global rule set 建立後，哪些 antecedents 或哪些 test cases 存在 competing decision evidence。

Conflict 必須在 resolver 之前定義。

輸入：

\[
R_G
\]

以及 test objects。

輸出：pre-resolution conflict structure。

---

## 1. Exact antecedent conflict

對 antecedent \(a\)：

\[
D(a)=\{d_r:Ante(r)=a\}
\]

若：

\[
|D(a)|>1
\]

則 \(a\) 是 exact conflict group。

最直觀形式：

\[
X\rightarrow A
\]

與：

\[
X\rightarrow B
\]

完整 rules 不同，但 antecedent 相同、decision 不同。

### 指標

Unique antecedents：

\[
N_A=|\{Ante(r):r\in R_G\}|
\]

Conflict Antecedent Rate：

\[
CAR=
\frac{\#conflicting\ antecedents}{N_A}
\]

Conflict Rule Share：

\[
CRS=
\frac{\#rules\ belonging\ to\ exact\ conflict\ groups}{|R_G|}
\]

---

## 2. Inference-level conflict

Exact conflict 不是 prediction-time conflict 的完整描述。

對 test case \(x\)：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

matching decisions：

\[
D_x=\{d_r:r\in M(x)\}
\]

若：

\[
|D_x|>1
\]

則 \(x\) 是 inference conflict case。

Conflict set：

\[
X_{conflict}=\{x:|D_x|>1\}
\]

Conflict Case Rate：

\[
CCR=
\frac{|X_{conflict}|}{N_{test}}
\]

---

## 為什麼兩種 conflict 必須分開

例如：

```text
IF A=1       THEN Yes
IF A=1,B=2   THEN No
```

antecedents 不相同，所以不是 exact conflict。

但對：

```text
A=1,B=2
```

兩條 rules 都 match，因此：

\[
|D_x|=2
\]

形成 inference conflict。

所以：

\[
Exact\ Conflict=0
\]

完全可能同時：

\[
Inference\ Conflict>0
\]

Frozen Car Evaluation C=2 就是最乾淨的實證例子：exact conflict groups = 0，但 inference conflict cases = 85/346。

---

## Conflict 是 resolver-independent workload

對同一個 frozen `RuleSystemArtifact`：

- \(R_G\) 固定；
- \(M(x)\) 固定；
- \(X_{conflict}\) 固定。

因此：

\[
Conflict\ Workload
\]

應在 FIRST / SIMPLE / STANDARD / GLOBAL 之前先算好。

resolver 只改：

\[
\hat y(x)
\]

不能反過來改「這一筆原本有沒有 conflict」。

這是四種 resolver 能公平比較的必要條件。

---

## Conflict detection 與 resolution

Detection：

\[
R_G,x
\rightarrow
Conflict?\in\{0,1\}
\]

Resolution：

\[
M(x)
\rightarrow
\hat y(x)
\]

所以：

\[
Conflict\ Detection\neq Conflict\ Resolution
\]

---

## Production implementation

- Exact conflict：`roughset/evaluation.py::audit_rule_conflicts`
- Matching rules：`roughset/evaluation.py::matching_rules`
- Frozen pre-resolution conflict：`roughset/pipeline.py::_pre_resolution_conflicts`
- Resolver-specific correctness on those cases：evaluation pipeline / `audit_conflict_cases`

---

## 老師問法

### 「同 antecedent 不同 decision 才叫 conflict 嗎？」

那只是 exact conflict。真正 prediction 時還有更大的 inference conflict：不同 antecedents 也可能同時 cover 同一 case 並支持不同 decisions。

### 「Resolver 不是已經選 A/B 了嗎？為什麼還要另外定義 conflict？」

因為要比較 resolver，就必須先固定共同 workload。若每個 resolver 自己定義 conflict，performance comparison 就失去共同基準。
