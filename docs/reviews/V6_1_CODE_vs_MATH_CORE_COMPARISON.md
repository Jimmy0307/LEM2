# V6.1：Code vs. 原始數學核心逐項比較

基準檔案：`lem2_control_panel_v6_1_數學一致性修正版.py`

目的：在把 V6.1 拆成 `Adapter + Core + Federated + Evaluation + App` 以前，先把「不能被重構改壞」的數學與目前 code 一一對上。

---

## 0. 結論摘要

| 層 | 數學/定義 | V6.1 code | 判定 |
|---|---|---|---|
| Indiscernibility / equivalence class | 相同 condition values 形成等價類 | `groupby(condition_cols)` | ✅ 等價 |
| Lower approximation | \([x]_C \subseteq X\) 才納入 | `if eq_class <= concept` | ✅ 直接對應 |
| Positive region | 所有 decision class lower approximations 的聯集 | 以「condition equivalence class 內 decision 唯一」計數 | ✅ 等價計算 |
| Dependency degree | \(\gamma_C(D)=|POS_C(D)|/|U|\) | `_positive_region_size / len(df)` | ✅ 直接對應 |
| Reduct | 保持 \(\gamma\) 且最小 | 逐 cardinality exhaustive search | ✅ 找的是 minimum-cardinality reduct |
| LEM2 block | \([t]\) | attribute-value pair 對應 row set | ✅ |
| LEM2 complex | \([T]=\cap_{t\in T}[t]\) | repeated set intersection | ✅ |
| Pair selection | max \(|[t]\cap G|\)，tie min \(|[t]|\) | sort `(-overlap, block_size, lexical)` | ✅；最後 lexical tie 是 deterministic implementation choice |
| Certain complex | \(\emptyset\neq[T]\subseteq B\) | loop termination condition | ✅ |
| Minimal complex | 刪除任一可刪 condition | iterative removal | ✅ inclusion-minimal；結果可能受刪除順序影響 |
| Local covering | complexes cover \(B\)，再刪冗餘 complex | `covered == B` + `remove_redundant_complexes` | ✅ |
| Rule identity | antecedent + decision | `Rule.key=(sorted conditions, decision)` | ⚠️ V6.1 明確定義；不是所有 paper 都這樣定義 |
| Federated UNION | unique full rules，first occurrence 保序 | `union_rules_with_provenance` | ✅ 內部定義一致 |
| Standard Voting | fired rule weight = # training objects matching antecedent | `fit_rule_weights` | ✅ 對 RSES Standard Voting |
| Global Strength | matching rules 對該 class support-object union / class size | support-set union / class size | ✅ 對 Bazan 定義 |
| Jaccard | \(|R_i\cap R_j|/|R_i\cup R_j|\) | `_jaccard` | ✅ |
| Exact conflict | same antecedent → >1 decisions | `audit_rule_conflicts` | ✅ 我們的研究定義 |
| Case conflict | one test case matches rules with >1 decisions | `audit_conflict_cases` | ✅ 我們的研究定義 |
| Order sensitivity | prediction changes across client orders | `audit_order_sensitivity` | ✅ 我們的研究定義 |
| Dirichlet Non-IID | \(p_k\sim Dir(\alpha 1_C)\) | `rng.dirichlet` + `rng.multinomial` | ✅ |

**目前沒有看到必須重寫 LEM2 Core 的數學錯位。**

真正要在軟體化時保護的是：**搬模組，不改下面這些函式的演算法語義。**

---

# 1. 等價類 / Indiscernibility

數學上，對 condition attributes \(C\)：

\[
IND(C)=\{(x,y)\in U^2:\forall a\in C,\ a(x)=a(y)\}
\]

物件 \(x\) 的等價類：

\[
[x]_C=\{y\in U:(x,y)\in IND(C)\}
\]

V6.1：

```python
def equivalence_classes(df, condition_cols):
    groups = df.groupby(list(condition_cols), sort=False, dropna=False).groups
    return [set(ids) for ids in groups.values()]
```

### 比較

`groupby(condition_cols)` 正好把「所有 condition values 完全相同」的 rows 放在一起，因此每個 group 就是一個 \([x]_C\)。

**判定：✅ Exact computational equivalent**

---

# 2. Lower Approximation

數學：

\[
\underline{C}(X)
=
\bigcup\{[x]_C:[x]_C\subseteq X\}
\]

V6.1 核心：

```python
def lower_approximation(df, condition_cols, decision_col, decision_value):
    concept = set(df.index[df[decision_col] == decision_value])
    lower = set()

    for eq_class in equivalence_classes(df, condition_cols):
        if eq_class <= concept:
            lower |= eq_class

    return lower
```

直接對照：

| 數學 | Code |
|---|---|
| \(X\) | `concept` |
| \([x]_C\) | `eq_class` |
| \([x]_C\subseteq X\) | `eq_class <= concept` |
| union | `lower |= eq_class` |

**判定：✅ 一對一實作**

---

# 3. Positive Region 與 Dependency Degree

數學：

\[
POS_C(D)
=
\bigcup_{X\in U/D}
\underline{C}(X)
\]

\[
\gamma_C(D)
=
\frac{|POS_C(D)|}{|U|}
\]

V6.1：

```python
def _positive_region_size(df, attrs, target):
    if not attrs:
        return len(df) if df[target].nunique(dropna=False) == 1 else 0

    grouped = df.groupby(list(attrs), dropna=False)[target].nunique(dropna=False)
    pure_keys = grouped[grouped == 1].index

    if len(pure_keys) == 0:
        return 0

    sizes = df.groupby(list(attrs), dropna=False).size()
    return int(sizes.loc[pure_keys].sum())


def dependency_degree(df, attrs, target):
    return _positive_region_size(df, attrs, target) / len(df) if len(df) else 0.0
```

### 為什麼 `decision_nunique == 1` 與 Positive Region 等價？

一個 condition equivalence class \(E=[x]_C\) 若只含一種 decision：

\[
|\{d(y):y\in E\}|=1
\]

則必存在某 decision concept \(X\)，使：

\[
E\subseteq X
\]

因此 \(E\) 完整屬於某個 lower approximation，故屬於 positive region。

反之，如果 equivalence class 內含兩種 decision，它不可能完整包含於任一單一 decision concept，因此不屬於 positive region。

**判定：✅ 不是近似，而是等價的 optimized computation**

---

# 4. Reduct

Pawlak-style relative reduct核心條件：

\[
R\subseteq C
\]

\[
\gamma_R(D)=\gamma_C(D)
\]

一般 reduct 還要求 inclusion-minimal。Wang 2007 的 feature-selection benchmark 又進一步把焦點放在 **minimal cardinality / shortest reduct**。

V6.1：

```python
def find_minimal_reducts(df, features, target):
    features = list(features)
    full_gamma = dependency_degree(df, features, target)

    for size in range(1, len(features) + 1):
        found = []

        for combo in itertools.combinations(features, size):
            if np.isclose(dependency_degree(df, combo, target), full_gamma):
                found.append(tuple(combo))

        if found:
            return found

    return [tuple(features)]
```

### 它真正找到什麼？

它從：

\[
|R|=1,2,3,\ldots
\]

逐層 exhaustive search。

第一個出現：

\[
\gamma_R(D)=\gamma_C(D)
\]

的 cardinality \(k^\*\) 時，回傳該層所有符合的 subsets。

因此：

\[
k^\*
=
\min\{|R|:R\subseteq C,\gamma_R(D)=\gamma_C(D)\}
\]

**判定：✅ minimum-cardinality reduct search**

### 命名提醒

`find_minimal_reducts()` 在數學語言上略寬鬆。

更精確名稱應是：

```python
find_minimum_cardinality_reducts()
```

因為「minimal by inclusion」與「minimum cardinality」概念不同；這支 code 實際做的是後者。

---

# 5. LEM2 Attribute–Value Blocks

LEM2 中 pair：

\[
t=(a,v)
\]

其 block：

\[
[t]=\{x\in U:a(x)=v\}
\]

V6.1：

```python
def build_blocks(df, condition_cols):
    blocks = {}
    for attr in condition_cols:
        for value in pd.unique(df[attr]):
            blocks[(attr, value)] = set(df.index[df[attr] == value])
    return blocks
```

**判定：✅ 直接對應 \([t]\)**

---

# 6. Complex Block

若：

\[
T=\{t_1,\ldots,t_m\}
\]

則：

\[
[T]
=
\bigcap_{t\in T}[t]
\]

V6.1：

```python
def complex_block(conditions, blocks, universe):
    if not conditions:
        return set(universe)

    result = set(universe)
    for pair in conditions:
        result &= blocks[pair]
    return result
```

**判定：✅ Exact set intersection**

---

# 7. LEM2 Pair Selection

經典 LEM2：

1. 從與目前 goal \(G\) 有交集的 pairs 中選；
2. 最大化：

\[
|[t]\cap G|
\]

3. 平手時最小化：

\[
|[t]|
\]

4. 再平手，原 pseudocode 說「select first pair」。

V6.1：

```python
def choose_best_pair(blocks, G, used_pairs):
    candidates = []

    for pair, block in blocks.items():
        if pair in used_pairs:
            continue

        overlap = len(block & G)
        if overlap:
            candidates.append((pair, overlap, len(block)))

    candidates.sort(key=lambda x: (-x[1], x[2], str(x[0])))
    return candidates[0][0]
```

對照：

\[
-x[1]
\Rightarrow
\max |[t]\cap G|
\]

\[
x[2]
\Rightarrow
\min |[t]|
\]

\[
str(x[0])
\Rightarrow
deterministic\ final\ tie-break
\]

### 注意

最後的 lexical ordering：

```python
str(x[0])
```

**不是 Rough Set 數學本體**，只是把經典 pseudocode 中模糊的「first pair」固定化，確保 reproducibility。

**判定：✅ 核心準則吻合；final tie-break 是合理 implementation choice**

---

# 8. 建立 Certain Complex

LEM2 要持續加 pair，直到：

\[
\emptyset\neq[T]\subseteq B
\]

其中 \(B\) 是要覆蓋的 lower approximation。

V6.1：

```python
while True:
    current = complex_block(T, blocks, universe)

    if T and current and current <= B:
        break

    best_pair = choose_best_pair(blocks, G, T)
    T.append(best_pair)
    G &= blocks[best_pair]
```

條件：

```python
T and current and current <= B
```

對應：

\[
T\neq\emptyset
\]

\[
[T]\neq\emptyset
\]

\[
[T]\subseteq B
\]

**判定：✅ Exact certain-complex stopping condition**

---

# 9. Minimal Complex

數學上：

\[
T
\]

為 \(B\) 的 minimal complex，如果：

\[
[T]\neq\emptyset,\quad [T]\subseteq B
\]

且不存在 proper subset \(T'\subset T\) 仍滿足此條件。

V6.1：

```python
def minimize_complex(conditions, B, blocks, universe):
    conditions = list(conditions)
    changed = True

    while changed and len(conditions) > 1:
        changed = False

        for condition in list(conditions):
            trial = [x for x in conditions if x != condition]
            trial_block = complex_block(trial, blocks, universe)

            if trial_block and trial_block <= B:
                conditions = trial
                changed = True
                break

    return conditions
```

它逐個測試是否可刪：

\[
[T-\{t\}]\neq\emptyset
\]

且：

\[
[T-\{t\}]\subseteq B
\]

可則刪掉，直到沒有單一 condition 能再刪。

**判定：✅ 得到 inclusion-minimal complex**

### 注意

若存在多個合法 minimal complexes，最後得到哪一個可能受 pair / deletion order 影響。

這不是「code 錯」，而是 LEM2 本來可能有多個合法 local coverings。

---

# 10. Local Covering

LEM2：

\[
G=B
\]

產生一個 minimal complex \(T\) 後：

\[
G
=
B-\bigcup_{T\in\mathcal T}[T]
\]

直到：

\[
G=\emptyset
\]

即：

\[
\bigcup_{T\in\mathcal T}[T]
\supseteq B
\]

V6.1：

```python
complexes = []
covered = set()

while covered != B:
    uncovered = B - covered

    T, T_block = build_one_complex(
        B, uncovered, blocks, universe
    )

    complexes.append((T, T_block))
    covered |= (T_block & B)
```

最後：

```python
complexes = remove_redundant_complexes(complexes, B)
```

`remove_redundant_complexes()` 會測試移除某 complex 後，其餘 complexes 是否仍 cover 全部 \(B\)。

**判定：✅ LEM2 local-covering structure 對得上**

---

# 11. LEM2 最終主函式

目前整個 mathematical flow：

```text
Decision Concept
      ↓
Lower Approximation B
      ↓
Attribute-value Blocks [t]
      ↓
G = uncovered part of B
      ↓
max |[t] ∩ G|
tie → min |[t]|
      ↓
grow T
      ↓
∅ ≠ [T] ⊆ B
      ↓
minimize T
      ↓
cover B
      ↓
remove redundant complexes
      ↓
Certain Rules
```

V6.1 `induce_lem2()` 正好按這條跑。

**判定：✅ 核心流程吻合經典 certain-rule LEM2**

---

# 12. 一個人工可手算例子

決策表：

| row | A | B | D |
|---:|---:|---:|---|
| 0 | 0 | 0 | N |
| 1 | 0 | 1 | N |
| 2 | 1 | 0 | Y |
| 3 | 1 | 1 | Y |

## 用 \(\{A,B\}\)

每個 profile 都唯一：

\[
U/\{A,B\}
=
\{\{0\},\{1\},\{2\},\{3\}\}
\]

因此：

\[
\underline{AB}(N)=\{0,1\}
\]

\[
\underline{AB}(Y)=\{2,3\}
\]

\[
POS_{AB}(D)=U
\]

\[
\gamma_{AB}(D)=1
\]

## 只用 A

\[
A=0\Rightarrow N
\]

\[
A=1\Rightarrow Y
\]

所以：

\[
\gamma_A(D)=1
\]

## 只用 B

兩個 B-values 都混合 N/Y：

\[
\gamma_B(D)=0
\]

因此 shortest reduct：

\[
R=\{A\}
\]

V6.1 實際輸出：

```text
gamma(A,B) = 1.0
gamma(A)   = 1.0
gamma(B)   = 0.0
reducts    = [('A',)]

LEM2:
IF A=0 THEN N
IF A=1 THEN Y
```

**Code 與手算完全一致。**

---

# 13. Inconsistent Table 驗證

| row | A | B | D |
|---:|---:|---:|---|
| 0 | 0 | 0 | N |
| 1 | 0 | 0 | Y |
| 2 | 1 | 0 | Y |

Condition equivalence classes：

\[
\{0,1\},\{2\}
\]

第一群同時含 N/Y，因此不能放入任何單一 decision lower approximation。

所以：

\[
\underline{AB}(N)=\emptyset
\]

\[
\underline{AB}(Y)=\{2\}
\]

\[
POS_{AB}(D)=\{2\}
\]

\[
\gamma_{AB}(D)=1/3
\]

V6.1 實際輸出：

```text
lower N = set()
lower Y = {2}
gamma   = 0.3333333333333333

LEM2:
IF A=1 THEN Y
```

這證明目前 LEM2 是 **certain-rule lane**：

衝突 equivalence class \(\{0,1\}\) 不會硬產生 certain rule。

**判定：✅ 與 Lower Approximation 邏輯一致**

---

# 14. Rule Identity：這是我們必須明確標註的 implementation choice

V6.1：

```python
@property
def key(self):
    return (tuple(sorted(self.conditions)), self.decision)
```

因此：

```text
IF A=High → Yes
IF A=High → No
```

是 **兩條不同 full rules**。

形式上：

\[
Key(r)
=
(A(r),D(r))
\]

### 這不是 Pawlak / LEM2 theorem

這是我們在軟體與 Federated aggregation 中對「rule identity」的明確定義。

它很適合 conflict research，因為不同 consequent 不會在 de-dup 時被消掉。

**判定：⚠️ 合理且必要，但必須標為 implementation definition，不可說是 LEM2 原始數學要求。**

---

# 15. Federated UNION + Provenance

V6.1：

```python
source_sets[rule.key].add(str(client_name))

if rule.key not in seen:
    seen.add(rule.key)
    merged.append(rule)
```

因此：

\[
R_G
=
\bigcup_c R_c
\]

但 global list 中只留一個 full-rule instance，同時另存：

\[
Sources(r)
=
\{c:r\in R_c\}
\]

### 兩件事被分開

1. **Rule ordering**
   - first occurrence 決定 FIRST_MATCH global order。

2. **Rule provenance**
   - 所有產生該 full rule 的 clients 都保留。

**判定：✅ 對目前 Federated experiment definition 自洽。**

---

# 16. Standard Voting

V6.1：

```python
for rule in rules:
    count = 0
    for _, row in train.iterrows():
        if _rule_matches(row, rule):
            count += 1

    weights[rule.key] = float(count)
```

因此：

\[
w(r)
=
|\{x\in U_{train}:x\models Antecedent(r)\}|
\]

prediction：

\[
Score(d|x)
=
\sum_{r\in M(x),D(r)=d}w(r)
\]

這符合 RSES Standard Voting 所使用的 rule weight：training objects matching antecedent。

**判定：✅**

---

# 17. Global Strength

對新物件 \(u_t\)、decision class \(X_j\)，設：

\[
MRul(X_j,u_t)
\]

為所有「match \(u_t\) 且 predict \(X_j\)」的 rules。

Global strength：

\[
GS(X_j,u_t)
=
\frac{
\left|
\bigcup_{r\in MRul(X_j,u_t)}
\left(
Pred(r)\cap X_j
\right)
\right|
}{
|X_j|
}
\]

V6.1 先建立每條 rule 的 support object set：

```python
if _rule_matches(row, rule) and row[target] == rule.decision:
    supported.add(object_id)
```

prediction 時：

```python
supported_objects = set()

for rule in decision_rules:
    supported_objects |= rule_support_sets[rule.key]

votes[decision] = len(supported_objects) / class_sizes[decision]
```

因此 numerator 是 **set union**，不是 support 直接相加，所以同一 training object 被多條 matching rules cover 時不會 double count。

**判定：✅ 對 Bazan Global Strength 公式**

---

# 18. Jaccard Similarity

原 healthcare paper使用：

\[
J(R_i,R_j)
=
\frac{|R_i\cap R_j|}{|R_i\cup R_j|}
\]

V6.1：

```python
def _jaccard(set_a, set_b):
    union = set_a | set_b
    return len(set_a & set_b) / len(union)
```

並提供兩版：

### A. Antecedent Jaccard

\[
J_A
\]

只比較 conditions。

這比較接近 healthcare paper 的 stated rule-set representation。

### B. Full-rule Jaccard

\[
J_F
\]

比較：

\[
Antecedent+Decision
\]

這是為 conflict research 額外加的嚴格版本。

**判定：✅；兩者必須分欄，不可混叫同一個 Jaccard。**

---

# 19. Conflict Metrics：這些不是經典 Rough Set 定理

## Exact Antecedent Conflict

若：

\[
A(r_i)=A(r_j)
\]

但：

\[
D(r_i)\neq D(r_j)
\]

則該 antecedent 是 conflicting。

V6.1：

```python
if len({str(r.decision) for r in rs}) > 1
```

### Conflict Antecedent Rate

\[
CAR
=
\frac{
N_{conflicting\ antecedents}
}{
N_{unique\ antecedents}
}
\]

### Conflict Rule Share

\[
CRS
=
\frac{
N_{rules\ belonging\ to\ conflicting\ antecedents}
}{
N_{global\ rules}
}
\]

**判定：✅ 定義與 code 一致；屬於我們的新研究 metrics。**

---

# 20. Conflict Case Rate / Resolution Accuracy

對 test object \(x\)：

\[
M(x)=\{r:x\models Antecedent(r)\}
\]

若：

\[
|\{D(r):r\in M(x)\}|>1
\]

則是 inference conflict。

### Conflict Case Rate

\[
CCR
=
\frac{
|\{x:|Decisions(M(x))|>1\}|
}{
N_{test}
}
\]

### Conflict Resolution Accuracy

\[
CRA
=
\frac{
N_{correct\ predictions\ among\ conflict\ cases}
}{
N_{conflict\ cases}
}
\]

V6.1 code 正是逐 test row 計算 matched rules、distinct decisions，並只在 conflict rows 上算 accuracy。

**判定：✅**

---

# 21. Order Sensitivity

對不同 client permutation：

\[
\pi_1,\pi_2,\ldots,\pi_M
\]

若同一 test case：

\[
|\{
\hat y^{(\pi_1)}(x),
...,
\hat y^{(\pi_M)}(x)
\}|>1
\]

則該 case 是 order-sensitive。

\[
OSR
=
\frac{
N_{order-sensitive\ cases}
}{
N_{test}
}
\]

V6.1：

```python
sensitive = [
    len(set(matrix[:, j])) > 1
    for j in range(matrix.shape[1])
]
```

**判定：✅ 完全對上我們定義。**

---

# 22. Dirichlet Label Skew

對每個 decision class \(k\)：

\[
\mathbf p_k
\sim
Dirichlet(\alpha\mathbf 1_C)
\]

接著：

\[
(n_{k1},...,n_{kC})
\sim
Multinomial(n_k,\mathbf p_k)
\]

V6.1：

```python
proportions = rng.dirichlet(
    np.full(n_clients, alpha)
)

counts = rng.multinomial(
    len(row_ids),
    proportions
)
```

並驗證：

\[
\bigcup_cU_c=U_{train}
\]

\[
U_i\cap U_j=\emptyset
\]

以及：

\[
\sum_c|U_c|=|U_{train}|
\]

**判定：✅ 數學與 code 一致。**

---

# 23. 真正需要 Freeze 的 Core

軟體化時，我建議把下面視為 **Mathematical Frozen Surface**：

```text
Rule              （資料結構；key 定義需鎖住）
equivalence_classes
lower_approximation
build_blocks
complex_block
choose_best_pair
minimize_complex
build_one_complex
remove_redundant_complexes
induce_lem2
_positive_region_size
dependency_degree
find_minimal_reducts
```

其中分兩層：

### 原始 Rough Set / LEM2 數學

```text
equivalence_classes
lower_approximation
build_blocks
complex_block
choose_best_pair
minimize_complex
build_one_complex
remove_redundant_complexes
induce_lem2
_positive_region_size
dependency_degree
```

### 我們的 benchmark 搜尋策略

```text
find_minimal_reducts
```

其目標是 minimum-cardinality reduct。

---

# 24. 不應放進 Core 的東西

下列都應留在 Core 外：

```text
train/test split
K-fold
discretization
UCI/CSV/Excel loading

client partition
Dirichlet
UNION
provenance

FIRST_MATCH
SIMPLE_VOTING
STANDARD_VOTING
GLOBAL_STRENGTH

Jaccard
conflict metrics
order sensitivity
client sweep

Balanced Accuracy
Macro F1
Coverage
```

因為：

\[
\boxed{
LEM2\neq Evaluation\neq Federated\neq ConflictResolution
}
\]

這個邊界是之後軟體化最重要的防錯機制。

---

# 25. 最終判定

目前 V6.1 可以拆成三種 provenance：

## A. 原始 Rough Set / LEM2 數學

\[
Equivalence
\rightarrow
Lower
\rightarrow
POS/\gamma
\rightarrow
LEM2
\]

**目前 code 對得上。**

## B. 文獻-derived classifier / benchmark

```text
minimum-cardinality reduct
Standard Voting
Global Strength
10-fold benchmark lane
```

**公式與 code 可對上，但要標清是哪篇 benchmark / classifier 定義。**

## C. 我們自己的 Federated Conflict Research Layer

```text
full-rule identity
provenance
full-rule Jaccard
conflict antecedent rate
conflict case rate
CRA
order sensitivity
order-distribution summary
Dirichlet non-IID experiment
```

**數學上自洽，但不能寫成「LEM2 原始定義」。**

---

# 建議軟體化時的唯一原則

先建立一組 regression contract：

\[
Output_{new\ core}
=
Output_{V6.1\ core}
\]

再搬 code。

**不要在拆模組的同時重寫數學。**

這樣我們之後如果看到結果變了，可以立刻知道是：

- Adapter 改了資料，
- Experiment 改了切法，
- Resolver 改了 prediction，

而不是 LEM2 本身被改壞。


---
# Appendix A：目前 V6.1 對應行號

- `Rule`: L3046–L3058
- `equivalence_classes`: L3061–L3063
- `lower_approximation`: L3066–L3074
- `build_blocks`: L3077–L3082
- `complex_block`: L3085–L3092
- `choose_best_pair`: L3095–L3112
- `minimize_complex`: L3115–L3129
- `build_one_complex`: L3132–L3155
- `remove_redundant_complexes`: L3158–L3174
- `induce_lem2`: L3177–L3220
- `_positive_region_size`: L1188–L1196
- `dependency_degree`: L1199–L1200
- `find_minimal_reducts`: L1203–L1218
- `union_rules_with_provenance`: L2774–L2803
- `predict_with_policy`: L2062–L2123
- `fit_rule_weights`: L2126–L2139
- `fit_rule_support_sets`: L2142–L2166
- `pairwise_rule_jaccard`: L2282–L2319
- `audit_rule_conflicts`: L2322–L2369
- `audit_conflict_cases`: L2372–L2412
- `audit_order_sensitivity`: L2445–L2495
- `audit_order_distribution`: L2516–L2633
- `dirichlet_label_skew_partition`: L1727–L1802
