# Module 02 — Federated Rule Aggregation

## 目的

這一層只回答：各 client 已經產生 local rules 後，哪些 rules 應該進入 global rule set。

輸入：

\[
R_1,R_2,\ldots,R_C
\]

輸出：

\[
R_G
\]

一般寫法：

\[
R_G=\mathcal{A}(R_1,R_2,\ldots,R_C)
\]

其中 \(\mathcal{A}\) 是 aggregation operator。

## UNION baseline

目前 healthcare-paper baseline 與 frozen implementation 的主要 aggregation 是：

\[
R_G^{union}=\bigcup_{c=1}^{C}R_c
\]

意思是：只要至少一個 client 產生某條完整規則，該規則就可以進入 global rule set。

如果令：

\[
freq(r)=\#\{c:r\in R_c\}
\]

則 UNION 等價於：

\[
R_G^{union}=\{r:freq(r)\ge1\}
\]

## INTERSECTION

只有所有 clients 都有的 rule 才進 global set：

\[
R_G^{intersection}=\bigcap_{c=1}^{C}R_c
\]

等價於：

\[
R_G^{intersection}=\{r:freq(r)=C\}
\]

## QUORUM / MAJORITY

設定 threshold \(q\)，只有至少 \(q\) 個 clients 具有的 rule 才保留：

\[
R_G^{quorum}=\{r:freq(r)\ge q\}
\]

若採過半：

\[
q=\left\lceil\frac{C}{2}\right\rceil
\]

## Rule identity

為了不在 aggregation 階段把衝突藏掉，完整 rule identity 必須包含 antecedent 與 decision：

\[
key(r)=(Ante(r),d_r)
\]

因此：

\[
X\rightarrow A
\]

與：

\[
X\rightarrow B
\]

是兩條不同完整規則，兩條都可以被保留進 \(R_G\)。

## Production implementation

目前 frozen baseline 的 UNION 實作位於：

- `roughset/federated.py::union_rules_with_provenance`

它同時保存 provenance，讓 global rule 可以追溯回原始 client。

## 這一層不負責什麼

- 不決定 A/B 衝突最後選誰。
- 不做 FIRST_MATCH / voting。
- 不計算 Jaccard。
- 不計算 prediction performance。

這一層只負責回答：『哪些完整 rules 進入 global rule set？』
