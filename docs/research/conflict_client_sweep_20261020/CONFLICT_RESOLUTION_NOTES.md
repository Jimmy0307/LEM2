# Federated LEM2 的 Conflict 與 Resolution：從 A/B 衝突到最終決策

## 1. 最核心的問題：最後只能是 A 或 B

假設兩個 client 各自學到：

\[
r_1:X\rightarrow A
\]

\[
r_2:X\rightarrow B
\]

條件相同：

\[
Ante(r_1)=Ante(r_2)=X
\]

但 decision 不同：

\[
Decision(r_1)\neq Decision(r_2)
\]

這就是最直觀的 conflict。

系統最後不可能輸出 \(A+B\)，最終仍必須輸出：

\[
A\quad\text{or}\quad B
\]

真正的問題因此是：

> 當 A、B 都有規則證據時，要根據什麼 evidence 決定最後相信哪一邊？

---

## 2. 為什麼不能在 UNION 時直接刪 A 或 B？

如果 aggregation 只把 antecedent 當 rule identity：

```text
Client 1: X → A
Client 2: X → B
```

看到 X 重複後直接只留其中一條，就會把 conflict 藏掉。

所以 frozen baseline 的完整 rule identity 是：

\[
key(r)=(Ante(r),Decision(r))
\]

因此：

\[
X\rightarrow A
\]

和：

\[
X\rightarrow B
\]

是兩條不同完整規則，兩條都保留。

Aggregation 只回答「哪些 rules 進 global rule set」，不負責決定 A/B winner。

---

## 3. Conflict Detection 與 Resolution 分開

### Conflict Detection

先問：

> 現在是不是同一筆 test case 同時有不同 decision evidence？

對 test case \(x\)：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

若：

\[
|\{d_r:r\in M(x)\}|>1
\]

就是 inference-level conflict。

### Conflict Resolution

再問：

> 已知 A/B 都有人支持，最後要選誰？

\[
\{A,B\}
\rightarrow
Resolver
\rightarrow
A\text{ or }B
\]

因此正確順序是：

```text
Local Rules
    ↓
Federated Aggregation
    ↓
Global Rules
    ↓
Conflict Detection
    ↓
Conflict Resolution
    ↓
Single Prediction
```

---

## 4. FIRST_MATCH：誰先出現就選誰

假設：

```text
r1: X → A
r2: X → B
```

如果 `r1` 在前：

\[
\hat y=A
\]

如果順序反過來：

\[
\hat y=B
\]

數學上令：

\[
k^*(x)=\min\{k:x\models Ante(r_k)\}
\]

則：

\[
\hat y=d_{r_{k^*(x)}}
\]

它沒有比較 A/B evidence 強弱，只使用 rule order。

因此：

\[
Client\ Order
\rightarrow
Rule\ Order
\rightarrow
Prediction
\]

這就是 order sensitivity。

---

## 5. SIMPLE_VOTING：哪一邊 matching rules 比較多

假設：

```text
r1 → A
r2 → A
r3 → A
r4 → B
r5 → B
```

則：

\[
Score(A)=3,
\qquad
Score(B)=2
\]

所以選 A。

公式：

\[
Score_{SV}(d|x)=|M_d(x)|
\]

每條 rule 都只有一票，因此：

> 很強的 rule = 1 票；很弱的 rule = 1 票。

---

## 6. STANDARD_VOTING：看 pooled positive rule support

這裡要以 **final mathematical audit 後的 federated pipeline** 為準。

對每一條 global rule \(r\)，不是只看產生它的 client，而是把它重新放到所有 clients 的 training data 上評估。

對 client \(c\)：

\[
Supp_c(r)
=
\{z\in U_c:z\models Ante(r)\land D(z)=d_r\}
\]

只有：

1. antecedent 命中；且
2. object 真實 decision 等於 rule decision

才算 positive support。

所有 clients 合起來：

\[
w(r)=Supp_G(r)
=\sum_{c=1}^{C}|Supp_c(r)|
\]

然後：

\[
Score_{STD}(d|x)
=
\sum_{r\in M_d(x)}w(r)
\]

例如：

```text
r1: X → A   positive support = 100
r2: Y → A   positive support = 50
r3: Z → B   positive support = 120
```

則：

\[
Score(A)=100+50=150
\]

\[
Score(B)=120
\]

所以 STANDARD_VOTING 選 A。

它回答的是：

> 支持 A/B 的 matching rules，累積起來各自有多少正向 training evidence？

### 重要限制

如果同一個 training object 同時支持 r1 與 r2，它會存在兩個 rule weights 中。

因此在：

\[
w(r_1)+w(r_2)
\]

裡可能被計兩次。

---

## 7. GLOBAL_STRENGTH：先去除重複 object，再看 class coverage

GLOBAL_STRENGTH 不直接把各 rule support 相加。

假設 A 有：

\[
r_1,r_2,r_3
\]

先做：

\[
S_A(x)
=
Supp(r_1)\cup Supp(r_2)\cup Supp(r_3)
\]

所以同一 training object 即使同時被三條 A rules 支持，也只算一次。

接著除以整個 A class 大小：

\[
GS(A|x)=\frac{|S_A(x)|}{|Class_A|}
\]

B 同樣：

\[
GS(B|x)=\frac{|S_B(x)|}{|Class_B|}
\]

最後：

\[
\hat y=\arg\max_dGS(d|x)
\]

所以它真正問的是：

> 目前這群 matching rules 合起來，可以覆蓋這個 decision class 多少比例？

---

## 8. STANDARD 與 GLOBAL 最容易混淆的地方

假設兩條 A rules：

\[
w(r_1)=100,
\qquad
w(r_2)=50
\]

STANDARD 直接加：

\[
Score_{STD}(A)=100+50=150
\]

但如果兩條 rules 大量 cover 同一批 objects，實際 unique support 只有：

\[
|Supp(r_1)\cup Supp(r_2)|=110
\]

GLOBAL_STRENGTH 使用的是 110，不是 150。

如果：

\[
|Class_A|=500
\]

則：

\[
GS(A)=110/500=0.22
\]

假設 B：

\[
|Supp(r_3)|=120,
\qquad
|Class_B|=200
\]

則：

\[
GS(B)=120/200=0.60
\]

因此可能出現：

```text
SIMPLE → A
STANDARD → A
GLOBAL_STRENGTH → B
```

這不是矛盾，而是三個方法回答的問題不同。

---

## 9. 四種 resolver 一次看懂

| Resolver | 真正問的問題 | Evidence |
|---|---|---|
| FIRST_MATCH | 誰先出現？ | Rule order |
| SIMPLE_VOTING | 哪邊 matching rules 比較多？ | Rule count |
| STANDARD_VOTING | 哪邊累積 positive rule support 比較大？ | Sum of pooled positive rule support |
| GLOBAL_STRENGTH | 哪邊的 matching-rule coalition 覆蓋自己 class 的比例比較高？ | Unique support-object union / class size |

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

## 10. Tie 與沒有 rule match 時怎麼辦

如果：

\[
M(x)=\emptyset
\]

四種 policy 都使用 default class。

對 SIMPLE / STANDARD / GLOBAL，如果最高 score tie：

1. default class 在 winners 裡就選 default；
2. 否則選字串排序最小的 winner。

所以 resolver 的完整數學不能只寫 `argmax`，tie rule 也是 implementation semantics 的一部分。

---

## 11. 我們目前到底解決了什麼？

不是宣稱已經找到永遠正確的 resolver。

我們已經把問題拆成：

\[
Conflict\ Detection
\rightarrow
Conflict\ Resolution
\rightarrow
Evaluation
\]

並且可以在同一 frozen global rule artifact 上比較四種 resolver。

目前 frozen UCI3 結果：

- Hayes-Roth：FIRST_MATCH 最好或並列最好；
- Car Evaluation：GLOBAL_STRENGTH 最好；
- Balance Scale：C=2–4 STANDARD_VOTING 最好，C=5 GLOBAL_STRENGTH 最好。

因此不能宣稱某個 fixed resolver 是 universal best。

目前較合理的研究式為：

\[
Best\ Resolver
=
f(Dataset,Rule\ Structure,Conflict\ Workload,Client\ Configuration)
\]

---

## 12. 下一個真正值得研究的問題

現在我們已經知道怎麼：

```text
找到 conflict
↓
整理 A/B evidence
↓
用四種固定 resolver 做決策
↓
量化 outcome
```

所以下一步才是：

> 能不能根據當下的 conflict structure、rule support、provenance、class distribution，自動決定這一次應該相信哪一種 evidence？

也就是從：

\[
Fixed\ Resolver
\]

走向：

\[
Adaptive\ Resolver
\]

但在提出新 resolver 前，四種 frozen baseline 必須先作為共同 comparator。

---

## 13. 老師問「你們 conflict 到底怎麼處理？」

一句話回答：

> 我們不在 aggregation 階段把衝突規則刪掉，而是先保留完整 rules；當同一個 test case 同時命中不同 decision 的規則後，才進入 resolver。目前比較 FIRST_MATCH、規則數投票、pooled positive support 加權，以及 unique class coverage strength。四者最後都只輸出一個 decision，但使用的 evidence 定義不同。

完整數學架構見：`modules/08_MATHEMATICAL_ARCHITECTURE.md`。
