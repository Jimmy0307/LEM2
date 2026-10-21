# Federated LEM2 — Final Teacher Handoff

> 目的：把老師目前要求的「整體介紹、分開 code、conflict、四種 Prediction Policies、client-count sweep、評量方式、引用來源、可執行軟體」集中到同一個入口。
>
> Frozen mathematical baseline：`main @ 31b078bb78c6754d04c56a2e1cc849c8feb221d7`
>
> Research branch：`research/conflict-client-sweep-20261020`

---

## 1. 研究流程

```text
Decision Table
   ↓
Local Rough Set / Reduct / LEM2
   ↓
Local Rule Sets R1 ... RC
   ↓
Federated UNION Aggregation
   ↓
Global Rule Set RG
   ↓
Rule Conflict Set
   ↓
Prediction Policy
   ├─ FIRST_MATCH
   ├─ SIMPLE_VOTING
   ├─ STANDARD_VOTING
   └─ GLOBAL_STRENGTH
   ↓
Prediction
   ↓
Established Evaluation Metrics
```

Client count \(C\in\{2,3,4,5\}\) 是外層實驗變數，不是第五種演算法。

完整架構：`modules/00_PIPELINE_MAP.md` 到 `modules/08_MATHEMATICAL_ARCHITECTURE.md`。

---

## 2. 四種方法的正式名稱

共同名稱使用：

\[
\boxed{Prediction\ Policies}
\]

不是「四種 resolver 演算法」。Conflict resolution 是它們在 competing-rule cases 上的功能。

| Policy | Evidence | 主要來源 |
|---|---|---|
| `FIRST_MATCH` | rule order | Woźniak et al. (2026) |
| `SIMPLE_VOTING` | matching-rule count | Lazo-Cortés et al. (2020) / RSES |
| `STANDARD_VOTING` | pooled positive rule-support sum | Lazo-Cortés et al. (2020) principle + federated adaptation |
| `GLOBAL_STRENGTH` | unique class-coverage ratio | Bazan et al. (2000) |

公式與說明：`TEAM_DISCUSSION_PREDICTION_POLICIES_AND_CONFLICT.md`。

老師若要「四個方法分開 code」，請看：

```text
reference/policies/
├─ first_match.py
├─ simple_voting.py
├─ standard_voting.py
└─ global_strength.py
```

這四支是 teaching/reference code；runtime 的 canonical implementation 仍保留在：

```text
roughset/evaluation.py::predict_with_policy
```

以避免 production semantics 分叉。

---

## 3. Conflict 定義

主要 conflict object 採既有 rule-conflict literature 的 prediction-time 定義：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

\[
\boxed{
\mathcal C=\{x\in U_{test}:|\{d_r:r\in M(x)\}|>1\}
}
\]

也就是：同一 example 被多條 rules cover，而且 rules 預測不同 classes（Lindgren, 2004；Lindgren & Boström, 2002）。

Exact same-antecedent / different-decision conflict 只保留作 supplementary structural audit。

完整說明：`CONFLICT_RESOLUTION_NOTES.md`。

---

## 4. 正式評量方式

正式主分析只使用既有理論／標準評量：

| 面向 | 指標 |
|---|---|
| Classification | Balanced Accuracy、Macro-F1 |
| Rule coverage | Coverage |
| Rule complexity | Ruleset size、mean conditions per rule |
| Client ruleset similarity | Pairwise Jaccard |
| Conflict workload | conflict-set count / proportion |
| Conflict cases performance | \(BA_{\mathcal C}\)、\(MacroF1_{\mathcal C}\) |
| Client-order categorical disagreement | Variation Ratio |
| Repeated policy comparison | Friedman + post-hoc / paired Wilcoxon |

不再以專案自創名稱 `CRA / CCR / OSR / H_rule` 作主要理論指標；舊欄位若仍出現在輸出，只作 backward compatibility / supplementary diagnostics。

完整公式 × 涵義 × code × citation：`TEAM_EVALUATION_METRICS_ESTABLISHED.md`。

---

## 5. 軟體入口

Windows 預設入口：

```text
run.bat
```

執行鏈：

```text
run.bat
→ environment check/setup
→ main.py --config config.json --all-policies
→ roughset.batch.run_policy_matrix(...)
→ 4 Prediction Policies
→ configured client-count sweep
→ outputs/batch_runs/<run_id>/
```

單一 config policy 入口：

```text
run_single.bat
```

目前 `config.json` 已設定：

```text
client_counts = [2, 3, 4, 5]
prediction_policies =
  FIRST_MATCH
  SIMPLE_VOTING
  STANDARD_VOTING
  GLOBAL_STRENGTH
```

Variation Ratio 已由 `roughset/established_metrics.py` 實作，正式 batch output 應輸出：

```text
mean_variation_ratio
mean_variation_ratio_conflict
```

因此 `.bat` 本身不需要增加新 command；同步點在 `batch.py` 的輸出 schema。

---

## 6. Frozen empirical baseline 的安全說法

目前 frozen UCI3 / holdout / seed 42 baseline 顯示：

- Hayes-Roth：nominal FIRST_MATCH 最好或並列最好，但存在明顯 client-order sensitivity；
- Car Evaluation：GLOBAL_STRENGTH 在 C=2–5 的 Balanced Accuracy 都最高；
- Balance Scale：C=2–4 STANDARD_VOTING 較高，C=5 GLOBAL_STRENGTH 較高。

因此目前只能說：

\[
\boxed{
Policy^*=f(Dataset,Rule\ Structure,Conflict\ Workload,Client\ Configuration)
}
\]

不能宣稱某一種 Prediction Policy universal best。

---

## 7. 研究與 publication scope 的界線

目前老師要求的 engineering / method handoff 已涵蓋：

- local LEM2 與 federated flow；
- aggregation；
- conflict；
- 四種 Prediction Policies；
- C=2–5 client sweep；
- 數學與 code mapping；
- established evaluation metrics；
- citation mapping；
- Windows launcher / all-policy software path；
- group discussion handoff。

若後續進入正式 publication-level inference，還需要另外增加：

```text
multiple random splits / seeds
→ paired repeated observations
→ Friedman omnibus test
→ post-hoc correction
→ paired Wilcoxon where appropriate
```

這是下一階段統計驗證，不是目前四種方法與 conflict implementation 的缺口。

---

# Canonical files for discussion

1. `FINAL_TEACHER_HANDOFF.md` — 本文件，總入口。
2. `TEAM_DISCUSSION_PREDICTION_POLICIES_AND_CONFLICT.md` — 四種方法 + conflict。
3. `TEAM_EVALUATION_METRICS_ESTABLISHED.md` — 評量公式、涵義、code、citation。
4. `CONFLICT_RESOLUTION_NOTES.md` — conflict → prediction policy 的數學說明。
5. `LITERATURE_REFERENCE_INDEX.md` — 文獻索引。
6. `modules/00`–`08` — 每個 pipeline layer 的拆解。
7. `reference/policies/` — 四支分開 teaching/reference code。

---

# References

- Bazan, J. G., Nguyen, H. S., Nguyen, S. H., Synak, P., & Wróblewski, J. (2000). *Rough Set Algorithms in Classification Problem*. https://doi.org/10.1007/978-3-7908-1840-6_3
- Brodersen, K. H., Ong, C. S., Stephan, K. E., & Buhmann, J. M. (2010). *The Balanced Accuracy and Its Posterior Distribution*. https://doi.org/10.1109/ICPR.2010.764
- Demšar, J. (2006). *Statistical Comparisons of Classifiers over Multiple Data Sets*. Journal of Machine Learning Research, 7, 1–30.
- Gal, Y. (2016). *Uncertainty in Deep Learning*. PhD thesis, University of Cambridge, §3.3.1, Eq. (3.19).
- Lazo-Cortés, M. S., Martínez-Trinidad, J. F., Carrasco-Ochoa, J. A., & Almanza-Ortega, N. N. (2020). *Towards Selecting Reducts for Building Decision Rules for Rule-Based Classifiers*. https://doi.org/10.1007/978-3-030-49076-8_7
- Lindgren, T. (2004). *Methods for Rule Conflict Resolution*. https://doi.org/10.1007/978-3-540-30115-8_26
- Lindgren, T., & Boström, H. (2002). *Classification with Intersecting Rules*. https://doi.org/10.1007/3-540-36169-3_31
- Sokolova, M., & Lapalme, G. (2009). *A systematic analysis of performance measures for classification tasks*. https://doi.org/10.1016/j.ipm.2009.03.002
- Woźniak, K., Sousa, J., & Śnieżyński, B. (2026). *Rule-Based Federated Learning for Healthcare*. https://doi.org/10.1007/978-3-032-29921-5_38
