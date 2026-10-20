# Module 04 — Conflict Audit

## 目的

這一層只回答：global rule set 已建立後，哪些規則或哪些 test cases 存在互相競爭的 decision evidence。

輸入：

\[
R_G
\]

輸出：conflict structure。

## Exact antecedent conflict

若兩條規則：

\[
Ante(r_1)=Ante(r_2)
\]

但：

\[
d(r_1)\neq d(r_2)
\]

則形成 exact conflict。

對 antecedent \(a\)，定義：

\[
D(a)=\{d_r\mid Ante(r)=a\}
\]

若：

\[
|D(a)|>1
\]

則 \(a\) 為 exact conflict group。

主要指標：

\[
Conflict\ Antecedent\ Rate=
\frac{\#conflicting\ antecedents}{\#unique\ antecedents}
\]

\[
Conflict\ Rule\ Share=
\frac{\#rules\ in\ conflict\ groups}{|R_G|}
\]

## Inference-level conflict

Exact conflict 不足以描述真正 prediction-time 的衝突。

對 test case \(x\)，所有 matching rules：

\[
M(x)=\{r\in R_G\mid x\models Ante(r)\}
\]

如果：

\[
|\{d_r:r\in M(x)\}|>1
\]

則 \(x\) 是 inference-level conflict case。

Conflict Case Rate：

\[
CCR=
\frac{\#inference\ conflict\ cases}{N_{test}}
\]

## 為什麼兩種 conflict 必須分開

例如：

```text
IF A=1       THEN Yes
IF A=1,B=2   THEN No
```

兩條 antecedent 不相同，所以不是 exact conflict。

但對 case `A=1,B=2`，兩條都會 match，因此產生 inference-level conflict。

所以：

\[
Exact\ Conflict=0
\]

不代表：

\[
Inference\ Conflict=0
\]

## Production implementation

- `roughset/evaluation.py::audit_rule_conflicts`
- `roughset/evaluation.py::audit_conflict_cases`

## 本層不做什麼

- 不決定最後輸出 A 還是 B。
- 不做 voting。
- 不以 resolver 結果重新定義 conflict。

Conflict 必須在 resolver 之前被定義，這樣不同 resolver 才是在同一個 structural workload 上公平比較。
