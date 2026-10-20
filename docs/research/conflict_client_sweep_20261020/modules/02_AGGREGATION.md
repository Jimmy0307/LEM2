# Module 02 — Federated Rule Aggregation

## 目的

這一層只回答：各 client 已經產生 local rules 後，哪些完整 rules 應該進入 global rule set。

輸入：

\[
R_1,R_2,\ldots,R_C
\]

輸出：

\[
R_G
\]

一般化：

\[
R_G=\mathcal A(R_1,R_2,\ldots,R_C)
\]

其中 \(\mathcal A\) 是 aggregation operator。

---

## Rule identity 先定義清楚

Frozen baseline 的完整 rule key：

\[
key(r)=(sorted(Ante(r)),d_r)
\]

因此：

\[
X\rightarrow A
\]

和：

\[
X\rightarrow B
\]

是不同完整 rules。

這個定義很重要，因為若只把 antecedent 當 identity，就可能在 aggregation 階段把不同 decision 的 evidence 隱性消掉。

---

## 目前 production baseline：UNION

\[
R_G^{UNION}=\bigcup_{c=1}^{C}R_c
\]

令：

\[
freq(r)=|\{c:r\in R_c\}|
\]

則：

\[
R_G^{UNION}=\{r:freq(r)\ge1\}
\]

意思是：只要至少一個 client 產生某條完整 rule，就可進 global set。

### Duplicate full rule

如果多個 clients 產生完全相同的：

\[
(Antecedent,Decision)
\]

則 global list 只保留第一個 occurrence，避免 duplicate full rule；但 provenance 保存所有來源：

\[
Prov(r)=\{c:r\in R_c\}
\]

因此：

- global rule identity；
- global rule order；
- source multiplicity

是三個不同概念。

---

## Global rule order

UNION implementation 依 client mapping order 掃描：

```text
Client_1 rules
→ Client_2 rules
→ ...
→ Client_C rules
```

同一 client 內則保持 LEM2 rule order。

所以 global list order 是「第一個 occurrence 的順序」。

這對 set membership 沒有影響，但對 FIRST_MATCH prediction 有直接影響。

---

## INTERSECTION：比較候選，不是 frozen production baseline

\[
R_G^{INT}=\bigcap_{c=1}^{C}R_c
\]

等價於：

\[
R_G^{INT}=\{r:freq(r)=C\}
\]

它回答的是：

> 哪些完整 rules 被所有 clients 共同產生？

優點是共識強；風險是 local heterogeneity 高時可能留下極少 rules，造成 coverage 大幅下降。

目前不能寫成 production 已實作 resolver pipeline。

---

## QUORUM / MAJORITY：比較候選，不是 frozen production baseline

給 threshold \(q\)：

\[
R_G^Q=\{r:freq(r)\ge q\}
\]

若採簡單過半：

\[
q=\left\lceil\frac C2\right\rceil
\]

它位於 UNION 與 INTERSECTION 之間：

\[
UNION:q=1
\]

\[
INTERSECTION:q=C
\]

因此可以把三者看成同一 frequency-threshold family。

---

## Aggregation 與 Conflict Resolution 的界線

Aggregation：

\[
R_1,\ldots,R_C
\rightarrow
R_G
\]

回答：

> 哪些 rules 進 global set？

Conflict Resolution：

\[
M(x)
\rightarrow
\hat y(x)
\]

回答：

> 這些 global rules 在某 test case 上打架時，最後選哪個 decision？

因此：

\[
Aggregation\neq Resolver
\]

---

## 這一層與其他 UNION 的區別

### Federated rule UNION

\[
R_G=\bigcup_cR_c
\]

是 aggregation operator。

### Jaccard UNION

\[
R_i\cup R_j
\]

只出現在 similarity denominator。

### GLOBAL_STRENGTH support UNION

\[
\bigcup_{r\in M_d(x)}Supp(r)
\]

是在 resolver 裡去除重複 training objects。

三者不可混用。

---

## Production implementation

- `roughset/federated.py::union_rules_with_provenance`
- `roughset/federated.py::union_rules`
- `roughset/core.py::Rule.key`

目前 frozen baseline 只把 UNION 當 production aggregation；INTERSECTION / QUORUM 保留為下一階段 aggregation-method comparison。

---

## 老師問法

### 「你的聯集在哪？」

在 local LEM2 完成之後、global rule set 建立之前：

\[
R_G=\bigcup_cR_c
\]

### 「UNION 是不是在解 conflict？」

不是。UNION 只決定 membership。Conflict 要等 \(R_G\) 建好後另外 audit。

### 「相同 condition、不同 decision 怎麼辦？」

因 full-rule identity 包含 decision，所以兩條都保留；之後由 conflict audit 顯性標記，而不是 aggregation 階段隨便刪一條。
