# Federated LEM2 — Final Teacher Handoff

> 目的：把老師目前要求的「整體介紹、分開 code、conflict、client-count sweep、六種 prediction methods、80/20 評量、引用來源、可執行軟體」集中到同一個入口。
>
> Frozen mathematical baseline：`main @ 31b078bb78c6754d04c56a2e1cc849c8feb221d7`
>
> Research branch：`research/conflict-client-sweep-20261020`

---

## 1. 研究流程

```text
Decision Table
   ↓
80% Training / 20% Holdout
   ↓
Local Rough Set / Reduct / LEM2          ← only 80%
   ↓
Local Rule Sets R1 ... RC
   ↓
Federated UNION Aggregation
   ↓
Global Rule Set RG + training support context
   ↓
Rule Conflict Set
   ↓
Prediction Policy / Experimental Variant
   ├─ FIRST_MATCH
   ├─ SIMPLE_VOTING
   ├─ STANDARD_VOTING
   ├─ GLOBAL_STRENGTH
   ├─ POPULATION_STANDARD      [project-defined]
   └─ POPULATION_GLOBAL        [project-defined]
   ↓
Prediction on untouched 20% holdout
   ↓
Accuracy / Recall / F1 / BA / Coverage
```

Client count \(C\in\{2,3,4,5\}\) 是外層實驗變數，不是 prediction method。

20% holdout 不參與 reduct、LEM2、aggregation、support-set construction 或 weight construction。

---

## 2. 三個 UCI dataset 的資料量

| Dataset | Total rows | Condition attributes | Total data columns | Classes | Frozen train | Frozen test |
|---|---:|---:|---:|---:|---:|---:|
| Hayes-Roth | 132 | 4 | 5 | 3 | 106 | 26 |
| Car Evaluation | 1,728 | 6 | 7 | 4 | 1,382 | 346 |
| Balance Scale | 625 | 4 | 5 | 3 | 499 | 126 |

`Total data columns = condition attributes + decision column`；內部 `__row_id__` 不算資料標頭。

Batch output 會逐列寫出：

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

## 3. 四個既有 baseline

共同正式名稱仍是 **Prediction Policies**。

| Policy | Evidence | 主要來源 |
|---|---|---|
| `FIRST_MATCH` | rule order | Woźniak et al. (2026) |
| `SIMPLE_VOTING` | matching-rule count | Lazo-Cortés et al. (2020) / RSES |
| `STANDARD_VOTING` | pooled positive rule-support sum | Lazo-Cortés et al. (2020) principle + federated adaptation |
| `GLOBAL_STRENGTH` | unique class-coverage ratio | Bazan et al. (2000) |

四個 baseline 不被這次改動覆蓋，仍保留作 comparison control。

---

## 4. 2026-10-22 新增兩個 population experimental variants

這兩個是本研究依會議需求新增的 experimental design，**不是既有文獻已提出的方法**。

對 candidate decision \(d\)：

\[
T_d=\sum_{r\in M_d(x)}|S_G(r)|
\]

\[
U_d=\left|\bigcup_{r\in M_d(x)}S_G(r)\right|
\]

\[
\boxed{P_d=\frac{U_d}{T_d}}
\]

其中 \(P_d\) 表示 raw rule-support occurrences 中，扣除跨 rules 重複 population 後留下的 nonredundant proportion。

Meeting example：

```text
r1 -> A : {u1,u2,u3}
r2 -> A : {u2,u3,u4}
```

所以：

\[
T_A=3+3=6,\qquad U_A=4,\qquad P_A=4/6=2/3
\]

### POPULATION_STANDARD

\[
\boxed{S_{PS}(d|x)=T_dP_d=U_d}
\]

也就是 Standard 的 raw support sum 去除 duplicate support inflation。

### POPULATION_GLOBAL

原 GlobalStrength：

\[
GS(d|x)=\frac{U_d}{N_d}
\]

目前 experimental correction：

\[
\boxed{
S_{PG}(d|x)
=
\frac{U_d}{N_d}\frac{U_d}{T_d}
=
\frac{U_d^2}{N_dT_d}
}
\]

完整規格：`POPULATION_EXPERIMENT_UPDATE_20261022.md`。

---

## 5. 六支分開 reference code

老師若要逐支看 code：

```text
reference/policies/
├─ first_match.py
├─ simple_voting.py
├─ standard_voting.py
├─ global_strength.py
├─ population_standard.py
└─ population_global.py
```

Production canonical implementation：

```text
roughset/evaluation.py::predict_with_policy
```

`tests/test_reference_policy_examples.py` 對 reference implementation 與 runtime 做 parity check。

---

## 6. Conflict 定義

主要 conflict 使用既有 rule-conflict literature 的 prediction-time 定義：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

\[
\boxed{
\mathcal C=\{x\in U_{test}:|\{d_r:r\in M(x)\}|>1\}
}
\]

也就是同一 example 被多條 rules cover，而且 rules 預測不同 classes（Lindgren, 2004；Lindgren & Boström, 2002）。

Exact same-antecedent / different-decision conflict 只作 supplementary structural audit。

---

## 7. 最後 20% prediction-set evaluation

老師會議要求的 final reporting 現在包含：

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

Target Coverage 看「rule system 有沒有 cover 到該 target」；Recall 看「最後 prediction 有沒有判對」，兩者不要混用。

既有研究 metrics（Jaccard、rule complexity、conflict-set BA/F1、Variation Ratio）仍保留作結構與 robustness analysis。

---

## 8. Windows software path

Windows 預設入口：

```text
run.bat
```

執行鏈：

```text
run.bat
→ main.py --config config.json --all-policies
→ roughset.batch.run_policy_matrix(...)
→ C = 2,3,4,5 client sweep
→ six policies on the same artifact
→ untouched 20% holdout evaluation
→ outputs/batch_runs/<run_id>/
```

`config.json` 現在 default all-policy list：

```text
FIRST_MATCH
SIMPLE_VOTING
STANDARD_VOTING
GLOBAL_STRENGTH
POPULATION_STANDARD
POPULATION_GLOBAL
```

`.bat` command 本身不需另外改；變更在它呼叫的 Python batch pipeline。

---

## 9. Citation boundary

### 可直接引用既有 literature

- Woźniak et al. (2026)：Federated LEM2 source architecture、FIRST_MATCH、C=2..5、BA/Coverage/Jaccard。
- Lazo-Cortés et al. (2020)：Simple / Standard voting principle。
- Bazan et al. (2000)：GlobalStrength。
- Lindgren (2004)；Lindgren & Boström (2002)：rule conflict。
- Brodersen et al. (2010)：Balanced Accuracy。
- Sokolova & Lapalme (2009)：classification metrics。
- Gal (2016)：Variation Ratio。
- Demšar (2006)：classifier comparison statistics。

### 不可假裝是既有文獻方法

```text
POPULATION_STANDARD
POPULATION_GLOBAL
P_d = U_d / T_d
```

這三者目前都屬於 **project-defined experimental design**。

---

## 10. Canonical files for discussion

1. `FINAL_TEACHER_HANDOFF.md` — 本文件，會議總入口。
2. `POPULATION_EXPERIMENT_UPDATE_20261022.md` — 2026-10-22 六方法新規格。
3. `TEAM_DISCUSSION_PREDICTION_POLICIES_AND_CONFLICT.md` — 四個 established baseline + conflict。
4. `TEAM_EVALUATION_METRICS_ESTABLISHED.md` — 既有 evaluation formulas / citations。
5. `LITERATURE_REFERENCE_INDEX.md` — citation boundary。
6. `reference/policies/` — 六支 separated teaching/reference code。
7. `roughset/evaluation.py` — canonical runtime prediction implementation。
8. `roughset/batch.py` — six-policy batch output / metadata contract。

---

# References

- Bazan, J. G., Nguyen, H. S., Nguyen, S. H., Synak, P., & Wróblewski, J. (2000). *Rough Set Algorithms in Classification Problem*. https://doi.org/10.1007/978-3-7908-1840-6_3
- Brodersen, K. H., Ong, C. S., Stephan, K. E., & Buhmann, J. M. (2010). *The Balanced Accuracy and Its Posterior Distribution*. https://doi.org/10.1109/ICPR.2010.764
- Demšar, J. (2006). *Statistical Comparisons of Classifiers over Multiple Data Sets*. *JMLR, 7*, 1–30.
- Gal, Y. (2016). *Uncertainty in Deep Learning*. PhD thesis, University of Cambridge.
- Lazo-Cortés, M. S., Martínez-Trinidad, J. F., Carrasco-Ochoa, J. A., & Almanza-Ortega, N. N. (2020). *Towards Selecting Reducts for Building Decision Rules for Rule-Based Classifiers*. https://doi.org/10.1007/978-3-030-49076-8_7
- Lindgren, T. (2004). *Methods for Rule Conflict Resolution*. https://doi.org/10.1007/978-3-540-30115-8_26
- Lindgren, T., & Boström, H. (2002). *Classification with Intersecting Rules*. https://doi.org/10.1007/3-540-36169-3_31
- Sokolova, M., & Lapalme, G. (2009). *A systematic analysis of performance measures for classification tasks*. https://doi.org/10.1016/j.ipm.2009.03.002
- Woźniak, K., Sousa, J., & Śnieżyński, B. (2026). *Rule-Based Federated Learning for Healthcare*. https://doi.org/10.1007/978-3-032-29921-5_38
