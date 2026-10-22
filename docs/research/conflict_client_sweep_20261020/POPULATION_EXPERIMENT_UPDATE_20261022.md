# 2026-10-22 Meeting Update — Six-Policy Population Experiment

> 狀態：已進入 research branch implementation。
>
> 核心原則：保留四個既有 baseline，不覆蓋原 Standard / Global；另外新增兩個 **project-defined experimental population variants**。後兩個方法不能引用成既有文獻方法。

---

## 1. 固定實驗資料與 80/20 holdout

三個 UCI 資料集使用相同 holdout protocol。20% test data 不參與 reduct、LEM2、client aggregation、support-set construction 或 weight construction；所有 model / rule artifacts 完成後，才對最後 20% 做 prediction 與 evaluation。

| Dataset | Total rows | Condition attributes | Total data columns | Classes | Frozen train rows | Frozen test rows |
|---|---:|---:|---:|---:|---:|---:|
| Hayes-Roth | 132 | 4 | 5 | 3 | 106 | 26 |
| Car Evaluation | 1,728 | 6 | 7 | 4 | 1,382 | 346 |
| Balance Scale | 625 | 4 | 5 | 3 | 499 | 126 |

`Total data columns = condition attributes + decision column`，不把內部 `__row_id__` 算進資料標頭量。

正式 batch output 另外逐列輸出：

```text
dataset_rows
dataset_columns
condition_attribute_count
target_column
class_count
train_rows
test_rows
```

---

## 2. 六種 Prediction Policies

同一個 train/test split、client partition、local reduct、local LEM2、global UNION rule set、support context 與 conflict set 下，只替換 prediction policy：

```text
1. FIRST_MATCH
2. SIMPLE_VOTING
3. STANDARD_VOTING
4. GLOBAL_STRENGTH
5. POPULATION_STANDARD
6. POPULATION_GLOBAL
```

前四種是既有 baseline；5、6 是 2026-10-22 meeting-derived experimental variants。

---

## 3. Population correction 的共同定義

對固定 test case \(x\) 與 candidate decision \(d\)，令：

\[
M_d(x)=\{r\in R_G:x\models Ante(r),\ d_r=d\}
\]

每條 matching rule 的 decision-consistent training support set 為 \(S_G(r)\)。

Raw support occurrences：

\[
\boxed{T_d=\sum_{r\in M_d(x)}|S_G(r)|}
\]

Unique supporting population：

\[
\boxed{U_d=\left|\bigcup_{r\in M_d(x)}S_G(r)\right|}
\]

重複膨脹量：

\[
D_d=T_d-U_d
\]

Population nonredundancy ratio：

\[
\boxed{
P_d
=1-\frac{D_d}{T_d}
=\frac{U_d}{T_d}
}
\]

這個 \(P_d\) 是本研究新定義的實驗 quantity，不是既有 rough-set metric。

### Meeting example

```text
r1 -> A : {u1,u2,u3}
r2 -> A : {u2,u3,u4}
```

原 Standard support sum：

\[
T_A=3+3=6
\]

但 unique population：

\[
U_A=|\{u1,u2,u3,u4\}|=4
\]

重複 support occurrences：

\[
D_A=6-4=2
\]

因此：

\[
\boxed{P_A=1-\frac26=\frac46=\frac23}
\]

這就是會議中「3+3 不直接當 6；把重複 population 去掉後變成 2/3」的正式化。

---

## 4. POPULATION_STANDARD

原 Standard Voting：

\[
S_{STD}(d|x)=T_d
\]

Population correction：

\[
\boxed{
S_{PS}(d|x)
=T_dP_d
=T_d\frac{U_d}{T_d}
=U_d
}
\]

所以它的 operational meaning 是：

> 不再用重複的 rule-support occurrences 投票，而以該 decision 的 unique supporting training population 作為 score。

Meeting example 中 A 的 score 從 6 修正成 4。

Code：

```text
roughset/evaluation.py::population_support_summary
roughset/evaluation.py::predict_with_policy(policy="POPULATION_STANDARD")
reference/policies/population_standard.py
```

---

## 5. POPULATION_GLOBAL

原 GlobalStrength：

\[
GS(d|x)=\frac{U_d}{N_d}
\]

其中 \(N_d\) 為 training data 中 decision class \(d\) 的總 population。

目前依會議「Global 也做同樣 population correction」的 operational definition：

\[
\boxed{
S_{PG}(d|x)
=
GS(d|x)P_d
=
\frac{U_d}{N_d}\frac{U_d}{T_d}
=
\frac{U_d^2}{N_dT_d}
}
\]

它同時保留：

1. GlobalStrength 的 class-size normalization；
2. 新增的 duplicate-support penalty。

這個公式是本研究 experimental variant，**不是 Bazan et al. (2000) 的 GlobalStrength 原公式**。

Code：

```text
roughset/evaluation.py::predict_with_policy(policy="POPULATION_GLOBAL")
reference/policies/population_global.py
```

---

## 6. 20% prediction-set evaluation

老師會議要求的 final 20% reporting 現在輸出：

```text
Accuracy
Recall (macro)
Macro-F1
Balanced Accuracy
Overall Coverage
Target Coverage by class
Target Coverage macro
```

### Overall Coverage

\[
\boxed{
Coverage_{overall}
=
\frac{|\{x\in U_{test}:M(x)\neq\emptyset\}|}{|U_{test}|}
}
\]

### Target Coverage

對真實 target class \(d\)：

\[
\boxed{
Coverage_d
=
\frac{|\{x\in U_{test}:D(x)=d,\ M(x)\neq\emptyset\}|}
{|\{x\in U_{test}:D(x)=d\}|}
}
\]

也就是：最後 20% prediction set 中，真正屬於該 target 的 cases，有多少至少能被一條 explicit rule cover。

Target Coverage 與 Recall 不同：

- Target Coverage：rule system 有沒有 cover 到；
- Recall：最後 prediction 有沒有判對。

---

## 7. Output contract

`batch_summary.csv` / `resolver_summary.csv` 現在應包含：

```text
Dataset metadata
+ policy
+ Accuracy
+ Recall macro
+ Macro-F1
+ Balanced Accuracy
+ Overall Coverage
+ Target Coverage macro
+ Target Coverage by class
+ conflict metrics
+ order robustness metrics
```

`config.json` 的 default all-policy batch 已更新為六種 methods，因此 Windows：

```text
run.bat
→ main.py --config config.json --all-policies
→ same artifacts
→ six prediction policies
→ same 20% holdout evaluation
```

---

## 8. Citation boundary

四個 baseline 的文獻來源不變：

- FIRST_MATCH — Woźniak et al. (2026), DOI `10.1007/978-3-032-29921-5_38`.
- SIMPLE / STANDARD Voting principle — Lazo-Cortés et al. (2020), DOI `10.1007/978-3-030-49076-8_7`.
- GLOBAL_STRENGTH — Bazan et al. (2000), DOI `10.1007/978-3-7908-1840-6_3`.

但：

```text
POPULATION_STANDARD
POPULATION_GLOBAL
Population nonredundancy ratio P_d = U_d / T_d
```

全部屬於 **project-defined experimental design**。除非後續文獻檢索找到完全相同方法，不能把它們寫成既有文獻已提出。
