# Module 01 — Local LEM2

## 目的

這一層只回答：每個 client 如何從自己的 local decision table 產生 local certain rules。

對 client \(c\)：

\[
U_c
\rightarrow
LEM2
\rightarrow
R_c
\]

其中：

\[
R_c=LEM2(U_c)
\]

---

## 基本物件

對 decision concept \(B\)，selector：

\[
t=(a,v)
\]

selector block：

\[
[t]=\{x:a(x)=v\}
\]

complex：

\[
T=\{t_1,\ldots,t_k\}
\]

其 block：

\[
[T]=\bigcap_{t\in T}[t]
\]

---

## Frozen implementation 的 selector 選擇

對目前尚未覆蓋的 target objects \(G\)，candidate selector 先最大化：

\[
|[t]\cap G|
\]

若 tie，再最小化：

\[
|[t]|
\]

若仍 tie，程式以 selector 的字串順序作 deterministic tie-break。

建立 complex 的停止條件：

\[
T\neq\emptyset
\]

且：

\[
[T]\neq\emptyset
\]

且：

\[
[T]\subseteq B
\]

此時形成 certain rule：

\[
T\rightarrow d
\]

---

## Selector minimization

若移除 selector \(t_i\) 後仍：

\[
[T\setminus\{t_i\}]\neq\emptyset
\]

且：

\[
[T\setminus\{t_i\}]\subseteq B
\]

則該 selector 可刪除。

所以 local rule 在自己的 client 上保持 certainty。

---

## Rule-set reduction

LEM2 持續建立 complexes，直到 target lower approximation 被覆蓋。

若某 complex 對 target 的 coverage 已完全可由其他 complexes 提供，則它可以被移除。

因此 local LEM2 有兩層最小化：

1. complex 內的 selector minimization；
2. rule-set 層的 redundant complex removal。

---

## 重要數學邊界

Local certainty 只保證 rule 在自己的 client table 上成立。

對 \(r\in R_c\)：

\[
[Ante(r)]_{U_c}\subseteq X_{d_r,c}
\]

但不保證 pooled data 上：

\[
[Ante(r)]_{U_{train}}\subseteq X_{d_r}
\]

因此兩個 clients 可以各自在 local data 上產生 certain rules，但 aggregation 後互相衝突。

這正是 federated conflict 可以產生而不代表 local LEM2 算錯的原因。

---

## 輸入／輸出／固定項

輸入：

\[
U_c
\]

輸出：

\[
R_c
\]

本輪 conflict / client-count 研究固定：

- LEM2 core semantics；
- selector selection；
- certainty condition；
- selector minimization；
- rule-set reduction。

後續比較 aggregation 或 resolver 時，不應改本層。

---

## Production implementation

- `roughset/core.py::lower_approximation`
- `roughset/core.py::choose_best_pair`
- `roughset/core.py::build_one_complex`
- `roughset/core.py::minimize_complex`
- `roughset/core.py::remove_redundant_complexes`
- `roughset/core.py::induce_lem2`

若啟用 reduct，pipeline 由 `roughset/pipeline.py::induce_lem2_on_reduct` 將 selected reduct 送入 frozen LEM2；empty reduct 有額外明確語意，但不屬於本輪 conflict 方法變更。

---

## 老師問法

### 「聯集在 LEM2 裡嗎？」

不是。Local LEM2 的輸出只是 \(R_c\)。Federated rule UNION 發生在下一層 Aggregation。

### 「為什麼 local rule 都 certain，global 還會 conflict？」

因 certainty 的 domain 是各自的 \(U_c\)，不是 pooled \(U_{train}\)。不同 clients 的 local distributions 可以讓相同／重疊 antecedent 對應不同 decision。
