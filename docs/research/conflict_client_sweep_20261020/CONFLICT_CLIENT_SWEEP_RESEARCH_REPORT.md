# Federated LEM2 Conflict Audit + Client Count Sweep 研究報告

**日期：2026-10-20**  
**Repository：`Jimmy0307/LEM2`**  
**Frozen baseline：`main @ 31b078bb78c6754d04c56a2e1cc849c8feb221d7`**  
**本報告分支：`research/conflict-client-sweep-20261020`**

---

## 1. 結論先行

這一輪的核心結論不是「聯邦 LEM2 有沒有 conflict」，而是：

> **當多個 client 各自誘導規則，再以 UNION 聚合時，衝突主要不是由「完全相同 antecedent 對應不同 decision」造成，而是由大量不同但重疊的規則在推論時同時命中同一個 case 所造成。**

因此必須把兩種衝突分開：

1. **Exact antecedent conflict**：相同 antecedent 對應多個 decision。
2. **Inference-level conflict**：某一 test case 同時命中多條規則，而命中規則包含多個 decision。

UCI3 的 frozen evidence 清楚顯示：client 數增加時，三個資料集的 inference-level conflict workload 整體都明顯上升；但 exact conflict groups 不一定同步或單調增加。

最強的反例是 **Car Evaluation, C=2**：

- Exact conflict groups = **0**
- 但 inference conflict case rate = **0.2457**（85/346 test cases）

所以：

> **「沒有相同 antecedent 的直接矛盾」不等於「推論沒有衝突」。**

第二個核心結論是：

> **FIRST_MATCH 的問題不是只有準確率，而是 client arrival order 直接成為模型語意的一部分。**

在 C=5 時，FIRST_MATCH prediction 會因 client order 改變的 test-case 比率：

- Hayes-Roth：**57.69%**
- Car Evaluation：**23.70%**
- Balance Scale：**57.94%**

而 SIMPLE_VOTING、STANDARD_VOTING、GLOBAL_STRENGTH 在目前定義下皆為 order-invariant。

第三個核心結論是：

> **沒有一種 resolver 可以跨資料集全面勝出。**

在本次 frozen sweep 中：

- Hayes-Roth：FIRST_MATCH 在 C=2–5 都是最佳或並列最佳。
- Car Evaluation：GLOBAL_STRENGTH 在 C=2–5 都是最佳。
- Balance Scale：STANDARD_VOTING 在 C=2–4 最佳；C=5 改由 GLOBAL_STRENGTH 最佳。

因此不能宣稱「Voting 解決 conflict」或「Global Strength 一定最好」。較合理的研究結論是：

> **Conflict resolution policy 是 dataset/workload-dependent 的第二層決策問題。**

---

## 2. 這一輪沒有改什麼

本研究報告建立在已完成 final mathematical audit 的 frozen baseline 上。

本輪：

- 不修改 `roughset/core.py`；
- 不修改 LEM2 induction；
- 不修改 lower approximation；
- 不修改 reduct 數學；
- 不重新定義 UNION；
- 不把新的 collaborative-filtering resolver 塞進 production baseline。

原因是目前 conflict diagnostics、client sweep、order sensitivity 與四種 resolver 已經存在，且 final mathematical audit 已驗證核心 baseline。

本輪工作的性質是：

> **把既有 evidence 收斂成一個可被數學追蹤、可被老師逐項質問、也可直接進入論文 Results / Discussion 的研究鏈。**

---

## 3. 原 Healthcare paper 到底留下什麼問題

來源：*Rule-Based Federated Learning for Healthcare*，DOI `10.1007/978-3-032-29921-5_38`。

原 paper 的主要流程是：

```text
各 client
  ↓
使用共享 discretization boundaries
  ↓
本地誘導 LEM2 rules
  ↓
server 以 UNION 聚合
  ↓
依 client results arrival order 保序
  ↓
FIRST_MATCH inference
```

其 UNION 可寫為：

\[
R_G = \bigcup_{c=1}^{C}R_c
\]

paper 亦明確指出，global ruleset 沒有重新排序；推論時第一條符合條件的規則決定 prediction，而 global order 反映 client result arrival order。

### 3.1 第一個缺口：rule identity 與 conflict 沒有被完整定義

paper 描述兩條規則在「conditions 相同」時視為 identical。

問題是，如果：

\[
Ante(r_1)=Ante(r_2)
\]

但：

\[
d(r_1)\neq d(r_2)
\]

那麼僅用 antecedent 做 UNION identity，就會出現一個沒有被 paper 明確回答的問題：

> 到底要保留哪一個 decision？

如果只是保留先到的規則，conflict 會被 client arrival order 隱性消掉，而不是被真正處理。

### 3.2 本研究 baseline 的做法

目前 V6.1 baseline 把兩個概念分開：

完整規則 identity：

\[
key(r)=(sorted(Ante(r)), d_r)
\]

因此相同 antecedent、不同 decision 的兩條規則都會被保留。

另外建立 antecedent-only signature：

\[
sig_A(r)=sorted(Ante(r))
\]

用來：

- 計算 antecedent Jaccard；
- 聚合 exact conflict groups；
- 分析 rule heterogeneity。

這樣的好處是：

> **不會在 UNION 階段先把 conflict 消掉，而是先保存 evidence，再交給 conflict audit / resolver 處理。**

---

## 4. 數學定義與程式追蹤

### 4.1 Global rule set

client \(c\) 的 local ruleset：

\[
R_c
\]

global ruleset：

\[
R_G=\bigcup_{c=1}^{C}R_c
\]

production implementation：

- `roughset/federated.py::union_rules_with_provenance`

同時保存 rule source provenance，讓每條 global rule 可以追溯到哪些 client。

---

### 4.2 Pairwise rule diversity

對 client \(i,j\)：

\[
J(R_i,R_j)=\frac{|R_i\cap R_j|}{|R_i\cup R_j|}
\]

本系統分兩種 identity：

1. antecedent only；
2. antecedent + decision。

production implementation：

- `roughset/evaluation.py::pairwise_rule_jaccard`
- `rule_antecedent_signature`
- `rule_full_signature`

低 Jaccard 表示 local rulesets 重疊程度低、heterogeneity 高。

但本次結果顯示：

> **rule diversity 與 conflict 並不是一對一關係。**

因為不同 antecedent 仍可覆蓋同一 test case。

---

### 4.3 Exact antecedent conflict

對某 antecedent \(a\)，定義：

\[
D(a)=\{d_r\mid sig_A(r)=a\}
\]

若：

\[
|D(a)|>1
\]

則 antecedent \(a\) 為 exact conflict group。

production implementation：

- `roughset/evaluation.py::audit_rule_conflicts`

指標：

\[
Conflict\ Antecedent\ Rate=
\frac{\# conflicting\ antecedents}{\# unique\ antecedents}
\]

\[
Conflict\ Rule\ Share=
\frac{\# rules\ belonging\ to\ conflict\ groups}{|R_G|}
\]

---

### 4.4 Inference-level conflict

對 test object \(x\)，所有符合規則：

\[
M(x)=\{r\in R_G\mid x\models Ante(r)\}
\]

如果：

\[
|\{d_r\mid r\in M(x)\}|>1
\]

則 \(x\) 是 inference-level conflict case。

Conflict Case Rate：

\[
CCR=
\frac{|\{x:\ |\{d_r:r\in M(x)\}|>1\}|}{N_{test}}
\]

production implementation：

- `roughset/evaluation.py::audit_conflict_cases`
- final pipeline 亦保存 policy-independent pre-resolution conflict flags。

這個定義很重要，因為它在 resolver 之前建立，所以：

> **同一個 structural ruleset 的 conflict workload 不應隨 resolver 改變。**

resolver 只能改「怎麼回答 conflict」，不能改「原本有沒有 conflict」。

---

### 4.5 Conflict Resolution Accuracy / Conflict Balanced Accuracy

若 \(X_{conflict}\) 為所有 inference-level conflict cases，則：

\[
Conflict\ Resolution\ Accuracy=
\frac{\#correct\ predictions\ on\ X_{conflict}}
{|X_{conflict}|}
\]

final research chain 同時保存 conflict-only Balanced Accuracy，避免 class imbalance 使單純 accuracy 過度樂觀。

---

### 4.6 Order sensitivity

令 \(\Pi_C\) 為 client arrival order 的 permutation 集合。

對 case \(x\)，若不同 client order 產生不同 prediction：

\[
|\{\hat{y}_{\pi}(x):\pi\in\Pi_C\}|>1
\]

則該 case 為 order-sensitive。

Order Sensitivity Rate：

\[
OSR=
\frac{\# order-sensitive\ test\ cases}{N_{test}}
\]

production implementation：

- `roughset/federated.py::audit_order_sensitivity`
- `audit_order_distribution`

當 \(C\le5\) 時，最多只有：

\[
5!=120
\]

種 client order，因此目前設定可完整枚舉。

---

## 5. 實驗範圍

Frozen UCI3 evidence：

- Hayes-Roth
- Car Evaluation
- Balance Scale
- Holdout
- seed = 42
- client count：\(C\in\{2,3,4,5\}\)
- resolvers：
  - FIRST_MATCH
  - SIMPLE_VOTING
  - STANDARD_VOTING
  - GLOBAL_STRENGTH

主要 evidence root：

`outputs/final_math_audit_20261015/UCI3_HOLDOUT42_FINAL/batch_runs/FINAL/`

關鍵檔案：

- `research_chain_summary.csv`
- `structural/<dataset>/client_sweep.csv`
- `structural/<dataset>/conflict_groups.csv`
- `structural/<dataset>/conflict_cases.csv`
- `structural/<dataset>/order_distribution.csv`
- `resolver_summary.csv`
- `policy_disagreement.csv`

---

## 6. Structural findings

本節只回答：

> client 數增加後，規則結構、exact conflict、inference conflict、order sensitivity 發生什麼變化？

### 6.1 Hayes-Roth

| C | Global rules | Jaccard antecedent | Exact groups | Conflict antecedent rate | Conflict rule share | Inference conflict cases | Conflict case rate | FIRST_MATCH order sensitivity |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 30 | 0.1724 | 1 | 0.0345 | 0.0667 | 3/26 | 0.1154 | 1/26 = 0.0385 |
| 3 | 28 | 0.2725 | 1 | 0.0370 | 0.0714 | 14/26 | 0.5385 | 9/26 = 0.3462 |
| 4 | 29 | 0.2594 | 1 | 0.0357 | 0.0690 | 10/26 | 0.3846 | 9/26 = 0.3462 |
| 5 | 33 | 0.2337 | 1 | 0.0313 | 0.0606 | 17/26 | 0.6538 | 15/26 = 0.5769 |

**解讀：**

Exact conflict 幾乎固定：每個 C 都只有 1 個 conflict group。

但 inference conflict 從 11.5% 上升到 65.4%。

因此 Hayes-Roth 的主要 conflict mechanism 不是 exact same-antecedent contradiction，而是不同規則的 overlapping coverage。

---

### 6.2 Car Evaluation

| C | Global rules | Jaccard antecedent | Exact groups | Conflict antecedent rate | Conflict rule share | Inference conflict cases | Conflict case rate | FIRST_MATCH order sensitivity |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 184 | 0.1413 | 0 | 0.0000 | 0.0000 | 85/346 | 0.2457 | 16/346 = 0.0462 |
| 3 | 207 | 0.1123 | 4 | 0.0197 | 0.0386 | 134/346 | 0.3873 | 40/346 = 0.1156 |
| 4 | 223 | 0.0958 | 2 | 0.0090 | 0.0179 | 169/346 | 0.4884 | 61/346 = 0.1763 |
| 5 | 226 | 0.0719 | 3 | 0.0135 | 0.0265 | 210/346 | 0.6069 | 82/346 = 0.2370 |

**解讀：**

這是最乾淨的 evidence：

- client 越多，antecedent Jaccard 由 0.1413 降至 0.0719，local rule diversity 增加；
- global rules 由 184 增至 226；
- inference conflict rate 由 24.6% 增至 60.7%；
- FIRST_MATCH order sensitivity 由 4.6% 增至 23.7%。

但 exact conflict groups 是：

\[
0\rightarrow4\rightarrow2\rightarrow3
\]

完全不是單調增加。

所以不能用「exact conflict groups 數量」代替整體 conflict workload。

---

### 6.3 Balance Scale

| C | Global rules | Jaccard antecedent | Exact groups | Conflict antecedent rate | Conflict rule share | Inference conflict cases | Conflict case rate | FIRST_MATCH order sensitivity |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 209 | 0.0485 | 3 | 0.0146 | 0.0287 | 47/126 | 0.3730 | 28/126 = 0.2222 |
| 3 | 200 | 0.0746 | 8 | 0.0417 | 0.0800 | 62/126 | 0.4921 | 47/126 = 0.3730 |
| 4 | 181 | 0.1093 | 9 | 0.0526 | 0.1050 | 74/126 | 0.5873 | 58/126 = 0.4603 |
| 5 | 183 | 0.0875 | 10 | 0.0578 | 0.1093 | 83/126 | 0.6587 | 73/126 = 0.5794 |

**解讀：**

這組結果更進一步說明：conflict 增加不等於 global rule count 增加。

Global rules：

\[
209\rightarrow200\rightarrow181\rightarrow183
\]

大致下降；但 inference conflict rate：

\[
0.373\rightarrow0.492\rightarrow0.587\rightarrow0.659
\]

持續上升。

因此 conflict 不是單純「規則太多」。更合理的解釋是：

> **規則覆蓋區域之間的交疊方式，才是 inference conflict 的直接機制。**

---

## 7. 三個 dataset 放在一起後的主要結論

### 7.1 Client count 增加，inference conflict workload 整體明顯增加

C=2 → C=5：

- Hayes-Roth：0.1154 → 0.6538
- Car Evaluation：0.2457 → 0.6069
- Balance Scale：0.3730 → 0.6587

Hayes-Roth 中間有 C=4 的回落，因此不能聲稱「每一步都單調」。

可以安全聲稱的是：

> **在三個 UCI dataset 的 C=2 與 C=5 endpoint 比較中，client fragmentation 增加均伴隨 substantially higher inference-level conflict workload。**

---

### 7.2 Exact conflict 不是主要 conflict 指標

最重要 evidence：

Car Evaluation C=2：

\[
Exact\ Conflict\ Groups=0
\]

但：

\[
CCR=0.2457
\]

這直接證明 exact conflict 與 inference conflict 是不同現象。

因此未來 paper 必須同時報：

1. conflict group metrics；
2. inference conflict metrics。

不能只報其中之一。

---

### 7.3 Rule similarity 也不能單獨代表 conflict

低 Jaccard 代表 client rulesets 更 heterogeneous，但 conflict 是 case-level rule overlap 的函數。

因此：

\[
Low\ Jaccard\not\Rightarrow Low\ Conflict
\]

也不能直接寫成：

\[
Low\ Jaccard\Rightarrow High\ Conflict
\]

正確說法應該是：

> Rule heterogeneity 提供 conflict 形成的結構條件之一，但是否形成 inference conflict，仍取決於不同規則在 feature space 的 overlap 與 decision disagreement。

---

## 8. Resolver findings

### 8.1 Hayes-Roth

| C | FIRST_MATCH BA | SIMPLE BA | STANDARD BA | GLOBAL BA | 最佳 |
|---:|---:|---:|---:|---:|---|
| 2 | 0.7667 | 0.6556 | 0.7667 | 0.7667 | FIRST / STANDARD / GLOBAL 並列 |
| 3 | 0.8333 | 0.6111 | 0.7444 | 0.7333 | FIRST_MATCH |
| 4 | 0.7778 | 0.5667 | 0.6222 | 0.7333 | FIRST_MATCH |
| 5 | 0.8333 | 0.5222 | 0.5778 | 0.7333 | FIRST_MATCH |

Hayes-Roth 顯示：

> **不能因 FIRST_MATCH 有 order sensitivity 就推論 voting 一定提高 predictive performance。**

它可以在 stability 意義上較差，但在這個 dataset 的固定 observed order 下，predictive performance 仍然最好。

---

### 8.2 Car Evaluation

| C | FIRST_MATCH BA | SIMPLE BA | STANDARD BA | GLOBAL BA | 最佳 |
|---:|---:|---:|---:|---:|---|
| 2 | 0.6639 | 0.6215 | 0.6694 | 0.7174 | GLOBAL_STRENGTH |
| 3 | 0.6740 | 0.7103 | 0.7089 | 0.7985 | GLOBAL_STRENGTH |
| 4 | 0.6314 | 0.5815 | 0.5927 | 0.6832 | GLOBAL_STRENGTH |
| 5 | 0.5964 | 0.5399 | 0.5435 | 0.6236 | GLOBAL_STRENGTH |

Car Evaluation 則呈現完全不同的 pattern：GLOBAL_STRENGTH 在 C=2–5 全部最佳。

這代表當 conflict workload 上升時，利用 global support context 的 weighting 在此資料上比 arrival-order FIRST_MATCH 更有效。

---

### 8.3 Balance Scale

| C | FIRST_MATCH BA | SIMPLE BA | STANDARD BA | GLOBAL BA | 最佳 |
|---:|---:|---:|---:|---:|---|
| 2 | 0.4885 | 0.5230 | 0.5575 | 0.5345 | STANDARD_VOTING |
| 3 | 0.4713 | 0.5345 | 0.5862 | 0.5690 | STANDARD_VOTING |
| 4 | 0.5115 | 0.5747 | 0.5977 | 0.5862 | STANDARD_VOTING |
| 5 | 0.4885 | 0.5402 | 0.5632 | 0.5908 | GLOBAL_STRENGTH |

Balance Scale 顯示 weighted voting 明顯比 FIRST_MATCH 穩定，且 policy winner 會隨 C 改變。

---

## 9. Resolver 的正確研究結論

目前 evidence 不支持：

> 「某個 resolver 解決了 federated LEM2 conflict。」

支持的是：

> **不同 resolver 對相同 structural conflict workload 產生不同決策；最佳 resolver 與 dataset、client count、class structure、rule overlap 有關。**

因此未來方法設計可以寫成兩層：

```text
Layer 1: conflict diagnosis
  - rule diversity
  - exact conflict
  - inference conflict
  - order sensitivity

Layer 2: conflict resolution
  - FIRST_MATCH
  - SIMPLE_VOTING
  - STANDARD_VOTING
  - GLOBAL_STRENGTH
  - future adaptive / collaborative resolver
```

這比把 resolver 混進 LEM2 core 更乾淨。

---

## 10. 對老師可能追問的直接回答

### Q1. Conflict 到底是什麼？

有兩種。

Exact conflict：同 antecedent、不同 decision。

Inference conflict：同一個 case 同時命中多個不同 decision 的 rules。

第二種是實際 prediction 時更重要的 conflict。

---

### Q2. 為什麼 exact conflict = 0 還會有 conflict？

因為兩條 antecedent 不必相同，也可能同時 cover 同一個 case。

例如：

```text
IF A=1       THEN Yes
IF A=1,B=2   THEN No
```

case `A=1,B=2` 會同時命中兩條規則。

---

### Q3. Client 越多，conflict 就一定越多嗎？

不能寫成數學必然。

本次三個 dataset 的 C=2 → C=5 endpoint 都增加，但 Hayes-Roth 在 C=4 有下降。

所以 empirical conclusion 是：

> client fragmentation 增加與更高 inference conflict workload 有明顯關聯，但不是逐 C 嚴格單調定律。

---

### Q4. 是不是規則越多所以 conflict 越多？

不是。

Balance Scale 的 global rule count 從 209 降到 183，但 conflict case rate 從 0.373 升到 0.659。

所以 rule count 不是充分解釋。

---

### Q5. FIRST_MATCH 最大問題是什麼？

不是公式錯，而是：

> client arrival order 會改變 global rule order，因此會改變 prediction。

在 C=5，Hayes-Roth 與 Balance Scale 約 58% test cases 都可能隨 client order 改 prediction。

這是 reproducibility / stability 問題。

---

### Q6. 那為什麼不直接用 voting？

因為 voting 不一定更準。

Hayes-Roth 的 FIRST_MATCH 在 C=2–5 都最好或並列最好；SIMPLE_VOTING 多數情況反而下降。

因此 resolver 本身要被當成 empirical design choice，而不是預設答案。

---

### Q7. 那現在研究貢獻在哪？

相對原 Healthcare paper，本研究目前新增：

1. 把完整 rule identity 與 antecedent identity 分開；
2. 保留相同 antecedent、不同 decision 的完整 provenance，而不是在 UNION 時隱性消掉；
3. 明確定義 exact conflict；
4. 明確定義 inference conflict；
5. 建立 conflict-only performance；
6. 建立 client-order sensitivity audit；
7. 系統化 sweep C=2–5；
8. 同一 frozen rule artifact 比較四種 conflict resolver；
9. 把研究鏈從「client → performance」擴成：

\[
Client\ Count
\rightarrow
Rule\ Structure
\rightarrow
Conflict
\rightarrow
Resolution
\rightarrow
Performance
\]

---

## 11. Reporting gap 與本報告的處理

目前 production `client_sweep.csv` 已包含：

- rule Jaccard；
- global rules；
- pre-resolution conflict case rate；
- resolver performance；
- order sensitivity。

但 final sweep CSV 沒有直接帶出：

- exact conflict group count；
- conflict antecedent rate；
- conflict rule share。

然而各 dataset 的 `conflict_groups.csv` 已完整保存 C=2–5 exact conflict rows。

因此本報告沒有修改 frozen production code，而是由現有 evidence 衍生：

令：

- \(G\) = exact conflict group count；
- \(m_g\) = group \(g\) 中的 full-rule count；
- \(|R_G|\) = global full-rule count。

因 UNION 已對 full-rule identity 去重，所以 unique antecedent 數可由：

\[
|A_G|=|R_G|-\sum_g(m_g-1)
\]

得到。

接著：

\[
Conflict\ Antecedent\ Rate=\frac{G}{|A_G|}
\]

\[
Conflict\ Rule\ Share=\frac{\sum_g m_g}{|R_G|}
\]

衍生結果保存於：

`docs/research/conflict_client_sweep_20261020/structural_conflict_summary.csv`

這是 reporting derivation，不是新的 algorithm semantics。

---

## 12. 目前可以安全寫進論文的主張

### 可以寫

1. 隨 client fragmentation 增加，三個 UCI dataset 在 C=2 到 C=5 的 inference conflict workload 均顯著提高。
2. Exact antecedent conflict 與 inference-level conflict 是不同現象，且 exact conflict 不足以代表 prediction-time conflict。
3. FIRST_MATCH 對 client arrival order 敏感，且 sensitivity 可隨 client count 顯著放大。
4. Order-invariant voting 消除了 arrival-order dependency，但不保證提高 predictive performance。
5. Resolver effectiveness 具有 dataset-specific / workload-specific 性質。
6. Rule count 本身不足以解釋 conflict growth。

### 現在不能寫

1. 「client 越多，conflict 必然單調增加」。
2. 「rule diversity 越高，conflict 必然越高」。
3. 「GLOBAL_STRENGTH 一定最好」。
4. 「Voting 已解決 federated LEM2 conflict」。
5. 「Exact conflict group count 可以代表整體 conflict」。
6. 「本研究已提出最終 optimal conflict resolver」。

---

## 13. 下一階段研究方向

現有 baseline 已經把問題拆乾淨：

```text
Rule generation
  ↓
Federated UNION + provenance
  ↓
Structural conflict audit
  ↓
Resolver comparison
```

下一階段才適合研究 adaptive resolver，例如 collaborative-filtering-inspired resolver。

但新的 resolver 必須滿足：

1. 不改 LEM2 core；
2. 不改 structural conflict definition；
3. 只讀 frozen `RuleSystemArtifact`；
4. 與 FIRST_MATCH / SIMPLE / STANDARD / GLOBAL 同一 artifact 比較；
5. 必須分開報 overall performance 與 conflict-only performance；
6. 必須報 order invariance；
7. 不能只因某一 dataset 改善就宣稱 general superiority。

因此目前最合理的下一個 research question 是：

> **Can an adaptive conflict resolver infer which rule/client evidence should dominate a conflicting case, without modifying the local LEM2 induction process or sharing raw client data?**

---

## 14. Evidence provenance

Frozen source baseline：

`31b078bb78c6754d04c56a2e1cc849c8feb221d7`

Final math audit：

`docs/final_math_audit_20261015/`

Final UCI3 evidence：

`outputs/final_math_audit_20261015/UCI3_HOLDOUT42_FINAL/batch_runs/FINAL/`

Structural sweep：

- `structural/Hayes-Roth/client_sweep.csv`
- `structural/Car_Evaluation/client_sweep.csv`
- `structural/Balance_Scale/client_sweep.csv`

Exact conflict evidence：

- `structural/Hayes-Roth/conflict_groups.csv`
- `structural/Car_Evaluation/conflict_groups.csv`
- `structural/Balance_Scale/conflict_groups.csv`

Cross-resolver chain：

- `research_chain_summary.csv`
- `resolver_summary.csv`
- `policy_disagreement.csv`

本報告新增的 derived evidence：

- `docs/research/conflict_client_sweep_20261020/structural_conflict_summary.csv`

---

## 15. Final research verdict

### Baseline correctness

**KEEP FROZEN.**

目前沒有證據要求再次修改 LEM2 core 或 reduct mathematics。

### Conflict audit

**SUFFICIENT FOR RESEARCH ANALYSIS.**

Exact conflict、inference conflict、resolver outcome、order sensitivity 已能分開量化。

### Client count sweep

**SUPPORTS A CLEAR EMPIRICAL RESULT.**

增加 client fragmentation 會擴大 inference conflict workload 與 FIRST_MATCH order-risk，但 pattern 不是簡單的 rule-count 或 exact-conflict 單因子關係。

### Resolver conclusion

**NO UNIVERSAL WINNER.**

目前最重要的研究發現不是某個 resolver 勝出，而是 resolver effectiveness 本身具有 dataset/workload dependency。

### Next research move

先以這份 conflict framework 作為 baseline；若要提出新的 conflict-resolution 方法，應新增 resolver layer，而不是重寫 LEM2。
