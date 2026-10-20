# Module 01 — Local LEM2

## 目的

這一層只回答：每個 client 如何從自己的 local decision table 產生 local rules。

給定 client \(c\) 的資料：

\[
D_c
\]

local rule set 定義為：

\[
R_c=LEM2(D_c)
\]

因此：

```text
Client 1 data -> LEM2 -> R1
Client 2 data -> LEM2 -> R2
...
Client C data -> LEM2 -> Rc
```

## 這一層沒有做什麼

- 不做 federated UNION。
- 不做 client 間規則比較。
- 不做 conflict resolution。
- 不做 global prediction。

## LEM2 本身的核心

對 decision concept \(B\)，從 selector \(t=(a,v)\) 建立 complex \(T\)，其覆蓋：

\[
[T]=\bigcap_{t\in T}[t]
\]

直到：

\[
[T]\subseteq B
\]

形成規則：

\[
T\Rightarrow B
\]

接著執行 selector minimization 與 rule-set reduction。

## 研究邊界

本輪 conflict/client-count 研究不修改這一層的 LEM2 數學。

也就是後面即使要比較不同 aggregation 或 resolver，也應該讓 local induction 保持 frozen，避免把『rule 怎麼產生』和『rule 怎麼合併／衝突怎麼處理』混在一起。
