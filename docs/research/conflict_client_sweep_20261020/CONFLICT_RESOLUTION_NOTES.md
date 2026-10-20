# Federated LEM2 的 Conflict 與 Resolution：從 A/B 衝突到最終決策

## 1. 問題其實很簡單：最後只能是 A 或 B

假設兩個 client 各自從自己的資料學到：

\[
r_1:X\rightarrow A
\]

\[
r_2:X\rightarrow B
\]

其中兩條規則的條件完全相同：

\[
Ante(r_1)=Ante(r_2)=X
\]

但 decision 不同：

\[
Decision(r_1)=A
\]

\[
Decision(r_2)=B
\]

這就是最直觀的 conflict。

因為對同一個條件 \(X\)，最後分類結果不可能同時是 \(A+B\)。系統最後仍然必須輸出 \(A\) 或 \(B\)。

因此真正的問題不是「A 和 B 能不能同時存在」，而是：

> 當 A 和 B 都有規則證據支持時，最後應該根據什麼選其中一個？

---

## 2. 為什麼不在 UNION 時直接刪掉其中一條？

最簡單但也最危險的做法是：

```text
Client 1:
X → A

Client 2:
X → B

合併時發現 X 重複
↓
只留其中一條
```

如果程式直接以 antecedent 當作唯一 identity，可能只留下先到的那條。這樣最後看起來好像完全沒有 conflict，但實際情況仍然是 Client 1 認為 \(X\rightarrow A\)，Client 2 認為 \(X\rightarrow B\)。

所以 conflict 並沒有被解決，只是被 aggregation 階段藏掉。

因此目前 baseline 不這樣做。

---

## 3. 我們現在先保存完整規則

我們把一條規則的完整 identity 定義為：

\[
RuleIdentity=(Antecedent,Decision)
\]

所以 \((X,A)\) 與 \((X,B)\) 被視為兩條不同規則。

Global rules 裡會保留：

```text
X → A
X → B
```

然後另外只看 antecedent：

\[
AntecedentSignature=X
\]

如果同一個 antecedent 底下出現超過一個 decision：

\[
|\{Decision\}|>1
\]

才正式標記為 conflict。

因此流程不是「衝突 → 先刪掉一條」，而是：

```text
衝突
↓
先保留 evidence
↓
辨識 conflict
↓
真正預測時再 resolve
```

---

## 4. Conflict Detection 與 Conflict Resolution 是兩件事

### Conflict Detection

回答：現在有沒有 A、B 同時競爭？

例如：

```text
X → A
X → B
```

代表：

\[
Conflict=True
\]

### Conflict Resolution

回答：既然 A、B 都有人支持，那最後選哪個？

\[
\{A,B\}
\rightarrow
Resolver
\rightarrow
A\text{ or }B
\]

所以 conflict 本身不是答案。它只是表示這一筆資料不能直接靠單一規則決定，需要進入第二層 decision mechanism。

---

## 5. FIRST_MATCH

假設 global rules 順序：

```text
r1: X → A
r2: X → B
```

新資料 \(x\) 同時符合兩條規則，第一條先 match，因此：

\[
\hat y=A
\]

如果規則順序反過來：

```text
r2: X → B
r1: X → A
```

則：

\[
\hat y=B
\]

FIRST_MATCH 的邏輯本質上是：

\[
\hat y=Decision(\text{first matching rule})
\]

它沒有真正比較 A 與 B 哪一個證據比較強，只是誰排前面就相信誰。

因此如果 global rule order 受到 client arrival order 影響，就會形成：

\[
Client\ Order
\rightarrow
Rule\ Order
\rightarrow
Prediction
\]

這就是 order sensitivity。

---

## 6. SIMPLE_VOTING：哪邊規則比較多就選哪邊

假設一筆資料同時命中：

```text
r1 → A
r2 → A
r3 → A
r4 → B
r5 → B
```

則：

\[
Vote(A)=3
\]

\[
Vote(B)=2
\]

最後：

\[
\hat y=A
\]

數學上：

\[
Score(d|x)=\sum_{r\in M(x)} I[d(r)=d]
\]

其中 \(M(x)\) 代表所有符合 test case \(x\) 的 rules。

因此 SIMPLE_VOTING 的概念就是：每一條 matching rule 都只有一票，哪個 decision 的票比較多就贏。

它的限制是：很弱的 rule 與很強的 rule 都只算一票。

---

## 7. STANDARD_VOTING：不是每條 rule 都一樣重要

目前 baseline 的 rule weight 是：

\[
w(r)=|\{x_i:x_i\models Ante(r)\}|
\]

意思是：這條 rule 的 antecedent 在 training data 中有多少資料支持。

例如：

```text
r1: X → A   weight = 100
r2: Y → A   weight = 50
r3: Z → B   weight = 120
```

如果新的 test case 同時符合三條：

\[
Score(A)=100+50=150
\]

\[
Score(B)=120
\]

所以：

\[
\hat y=A
\]

一般公式：

\[
Score(d|x)=\sum_{r\in M_d(x)}w(r)
\]

其中 \(M_d(x)\) 代表符合 \(x\) 而且 decision 為 \(d\) 的規則。

所以 STANDARD_VOTING 不只看有幾條 rule 支持 A，而是看支持 A 的規則背後有多少 training evidence。

---

## 8. GLOBAL_STRENGTH：看這群規則真正支撐了多少 decision class

假設 test case \(x\) 同時符合：

```text
A:
r1
r2
r3

B:
r4
r5
```

對 A，先看每條規則實際支持哪些 training objects，然後做集合聯集：

\[
S_A(x)=Supp(r_1)\cup Supp(r_2)\cup Supp(r_3)
\]

如果同一個 training object 同時被三條 A rule cover，只算一次。

B 也一樣：

\[
S_B(x)=Supp(r_4)\cup Supp(r_5)
\]

接著除以各自 decision class 的總大小：

\[
Strength(A|x)=\frac{|S_A(x)|}{|Class_A|}
\]

\[
Strength(B|x)=\frac{|S_B(x)|}{|Class_B|}
\]

最後：

\[
\hat y=\arg\max_d Strength(d|x)
\]

GLOBAL_STRENGTH 問的不是「有幾條 rule 支持 A」，而是「目前這群符合的 A rules，實際可以支撐整個 A class 多大的比例」。

---

## 9. 四種方法放在一起

```text
                  Test Case x
                       │
                找 matching rules
                       │
              ┌────────┴────────┐
              ↓                 ↓
         A 的 evidence       B 的 evidence
              │                 │
              └────────┬────────┘
                       ↓
                    Resolver
                       ↓
                    A 或 B
```

四種 Resolver 的差異就是如何衡量 evidence：

- FIRST_MATCH：誰先出現。
- SIMPLE_VOTING：誰的 rule 數量多。
- STANDARD_VOTING：誰的 rule support 加總比較大。
- GLOBAL_STRENGTH：誰的 matching rules 實際覆蓋其 class 的比例比較大。

---

## 10. 一個完整例子

假設現在 test case 同時 match：

```text
r1: X → A   support = 100
r2: Y → A   support = 50
r3: Z → B   support = 120
```

### FIRST_MATCH

如果順序是 `r3, r1, r2`，答案是 \(B\)。如果順序是 `r1, r2, r3`，答案是 \(A\)。

### SIMPLE_VOTING

A 有兩條：

\[
Vote(A)=2
\]

B 一條：

\[
Vote(B)=1
\]

所以答案是 \(A\)。

### STANDARD_VOTING

\[
Score(A)=100+50=150
\]

\[
Score(B)=120
\]

所以答案是 \(A\)。

### GLOBAL_STRENGTH

假設 r1、r2 背後大量支持資料其實是同一批：

\[
|Supp(r_1)\cup Supp(r_2)|=110
\]

而：

\[
|Class_A|=500
\]

所以：

\[
Strength(A)=110/500=0.22
\]

B：

\[
|Supp(r_3)|=120
\]

\[
|Class_B|=200
\]

所以：

\[
Strength(B)=120/200=0.60
\]

最後反而選 \(B\)。

這就是為什麼四個 resolver 不一定會給相同答案。

---

## 11. 所以我們目前到底「解決」了什麼？

目前並不是宣稱已經找到一個永遠正確的 conflict resolution method，而是把問題拆成三層。

第一層：

\[
Conflict\ Detection
\]

找出哪些 case 同時有 A/B evidence。

第二層：

\[
Conflict\ Resolution
\]

比較不同方法怎麼選 A 或 B。

第三層：

\[
Evaluation
\]

再看哪一種 resolver 在不同資料環境下表現比較好。

---

## 12. 實驗結果目前告訴我們什麼？

目前沒有任何一種 resolver 在所有資料上都最好。

- Hayes-Roth：FIRST_MATCH 最好或並列最好。
- Car Evaluation：GLOBAL_STRENGTH 最好。
- Balance Scale：C=2～4 是 STANDARD_VOTING 較好；C=5 則 GLOBAL_STRENGTH 較好。

因此目前證據真正支持的是：

\[
\boxed{
Best\ Resolver
=
f(
Dataset,
Conflict\ Structure,
Rule\ Structure,
Client\ Configuration
)
}
\]

也就是：最適合的 conflict resolution strategy 取決於資料與 conflict workload。

---

## 13. 下一個真正值得研究的問題

我們現在已經知道：

```text
Conflict 怎麼找
        ↓
A / B evidence 怎麼整理
        ↓
不同 resolver 怎麼選
        ↓
怎麼評估結果
```

所以下一步不應該再去改 LEM2，而是研究：

> 當 A、B 發生衝突時，能不能根據當下的 rule structure、support、client provenance、class distribution、conflict pattern，自動決定這一次應該相信哪一種 evidence？

也就是從固定 resolver：

\[
Fixed\ Resolver
\]

進一步變成：

\[
Adaptive\ Resolver
\]

核心問題：

\[
\boxed{
\text{Given conflicting evidence for }A\text{ and }B,
\text{ which evidence should dominate?}
}
\]

---

## 14. 老師問「你們 conflict 到底怎麼處理？」時的一句話版本

我們不在聯邦規則合併時把衝突規則刪掉，而是先保留所有完整規則。當一筆資料同時符合不同 decision 的規則時，再進入 conflict resolution。現在比較四種方式：第一條規則、規則數量投票、依規則支持量加權，以及依實際 class coverage 計算 global strength。最後仍然只輸出 A 或 B。現在的結果顯示沒有一種 resolver 在所有資料上都最好，所以真正的下一步是研究如何根據 conflict workload 自適應選擇 A 或 B。
