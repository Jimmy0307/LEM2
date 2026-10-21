# 組員討論版：四種 Prediction Policies + Conflict

> 用途：組內分工與討論。
>
> 四種方法統稱 **Prediction Policies**。`Conflict Resolution` 描述它們在 conflict cases 上的功能，但不是四種方法共同的正式原名。
>
> 評量方式請統一使用 `TEAM_EVALUATION_METRICS_ESTABLISHED.md`；不再以自訂 `CRA / CCR / OSR / H_rule` 作主要研究指標。

---

# 1. 四種 Prediction Policies

```text
FIRST_MATCH
SIMPLE_VOTING
STANDARD_VOTING
GLOBAL_STRENGTH
```

共同 matching set：

\[
M_d(x)=\{r\in R_G:x\models Ante(r),\ d_r=d\}
\]

## 1.1 FIRST_MATCH

\[
k^*(x)=\min\{k:x\models Ante(r_k)\}
\]

\[
\hat y_{FM}(x)=d_{r_{k^*(x)}}
\]

核心：**Order**。

Source paper 明確使用 first-match inference，且 global rule order 反映 client results 的 arrival order（Woźniak et al., 2026）。

Citation: https://doi.org/10.1007/978-3-032-29921-5_38

## 1.2 SIMPLE_VOTING

\[
S_{SV}(d|x)=|M_d(x)|
\]

核心：**Rule Count**。每條 matching rule 一票。

對應 RSES-style Simple Voting；Lazo-Cortés et al. (2020) 討論 matching rules 對 consequent decision 投票的 rule-based classification conflict handling。

Citation: https://doi.org/10.1007/978-3-030-49076-8_7

## 1.3 STANDARD_VOTING

本研究 federated 版本對 global rule \(r\) 在所有 clients 上計算 decision-consistent positive support：

\[
Supp_c(r)=\{z\in U_c:z\models Ante(r)\land D(z)=d_r\}
\]

\[
S_G(r)=\bigsqcup_{c=1}^{C}Supp_c(r)
\]

\[
w(r)=|S_G(r)|
\]

\[
S_{STD}(d|x)=\sum_{r\in M_d(x)}w(r)
\]

核心：**Rule Support Sum**。

RSES Standard Voting 的既有原理是 support-weighted rule voting；我們的 federated pooled positive-support construction 是 adaptation，不能寫成原文已經提出這個 federated formula（Lazo-Cortés et al., 2020）。

Citation: https://doi.org/10.1007/978-3-030-49076-8_7

## 1.4 GLOBAL_STRENGTH

\[
S_d(x)=\bigcup_{r\in M_d(x)}S_G(r)
\]

\[
N_d=|\{z\in U_{train}:D(z)=d\}|
\]

\[
GS(d|x)=\frac{|S_d(x)|}{N_d}
\]

核心：**Unique Class Coverage Ratio**。

Bazan et al. (2000) 的 GlobalStrength 公式使用 matching rules 的 class-consistent covered-object union，再除以 decision-class size。本研究把 support context federated 化。

Citation: https://doi.org/10.1007/978-3-7908-1840-6_3

---

# 2. 四種方法最簡單的差異

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

| Policy | Evidence | Order sensitive | Duplicate support object across rules | Class normalization |
|---|---|---|---|---|
| FIRST_MATCH | rule order | 是 | N/A | 否 |
| SIMPLE_VOTING | matching-rule count | 否 | N/A | 否 |
| STANDARD_VOTING | rule-support sum | 否 | 可重複貢獻 | 否 |
| GLOBAL_STRENGTH | unique support-object union | 否 | 去重 | 是 |

---

# 3. Conflict：正式主體使用 established rule-conflict definition

Lindgren (2004) 的核心定義是：兩條或更多 rules cover 同一 example，但 predict different classes。

對 test case \(x\)：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

\[
\boxed{
\mathcal C=\{x:|\{d_r:r\in M(x)\}|>1\}
}
\]

這個 \(\mathcal C\) 就是正式 **Conflict Set**。

Citation: https://doi.org/10.1007/978-3-540-30115-8_26

Code：

```text
roughset/pipeline.py::_pre_resolution_conflicts
```

```python
matched = matching_rules(row, rules)
decisions = sorted({str(rule.decision) for rule in matched})
is_conflict = len(decisions) > 1
```

正式只報 conflict-set count 與 ordinary proportion，不再創 `CCR` 名稱。

---

# 4. Exact Antecedent Conflict 只作 supplementary structural audit

若：

\[
Ante(r_i)=Ante(r_j),\qquad d_i\neq d_j
\]

則 global ruleset 存在 identical-antecedent contradiction。

Code：

```text
roughset/evaluation.py::audit_rule_conflicts
```

這一層可以保留來解釋 rule structure，但不是主要 classifier evaluation metric。真正 prediction-time conflict 仍以 Lindgren-style Conflict Set \(\mathcal C\) 為主。

---

# 5. 正式 Evaluation

請直接看：

`TEAM_EVALUATION_METRICS_ESTABLISHED.md`

主要保留：

```text
Balanced Accuracy
Macro-F1
Coverage
Ruleset Size
Mean Conditions per Rule
Pairwise Antecedent Jaccard
Conflict Set Count / Proportion
Balanced Accuracy on Conflict Set
Macro-F1 on Conflict Set
Variation Ratio for client-order disagreement
BA distribution across client permutations
Friedman + post-hoc / paired Wilcoxon after repeated experiments
```

Variation Ratio 已在 research branch 補成獨立 helper：

```text
roughset/established_metrics.py
```

Gal (2016, Eq. 3.19)：

\[
VR(x)=1-\frac{f_x}{T}
\]

Citation: https://www.cs.ox.ac.uk/people/yarin.gal/website/thesis/thesis.pdf

---

# 6. 組員實作比較時必須固定

```text
Train / Test Split
Client Partition
Local Reduct
Local LEM2 Rules
Global UNION Rule Set
Rule Identity
Conflict Set
Default Class
```

唯一主要替換項：

```text
prediction_policy
```

因此：

\[
Same\ Artifact
\rightarrow
Different\ Policy
\rightarrow
Different\ Outcome
\]

---

# 7. Client count sweep

固定：

\[
C\in\{2,3,4,5\}
\]

每個 \(C\) 重新走：

```text
Local LEM2
→ UNION
→ Rule Structure
→ Conflict Set
→ 4 Prediction Policies
→ Established Evaluation Metrics
```

Healthcare source paper 本身即使用 `C = 2..5` 並在 5 random data splits 上評估，因此 client-count sweep 有直接 source-paper experimental precedent。

Citation: https://doi.org/10.1007/978-3-032-29921-5_38

---

# 8. 組內不能寫錯

可以寫：

- 四個方法是 Prediction Policies。
- FIRST_MATCH 是 source-paper baseline。
- Simple / Standard Voting 有既有 RSES-style literature foundation。
- GlobalStrength 有 Bazan et al. 的既有數學來源。
- Conflict Set 採 Lindgren-style overlapping-rule conflict definition。
- Standard Voting 與 GlobalStrength 的 federated support context 是本研究 adaptation。

不要寫：

- 四種都是我們提出的新演算法。
- 四種都是 voting。
- `CCR / CRA / OSR / H_rule` 是既有經典 metric。
- Client 越多 conflict 在數學上必然單調增加。
- Voting 一定比 FIRST_MATCH 準。

---

# References

1. Woźniak, K., Sousa, J., & Śnieżyński, B. (2026). *Rule-Based Federated Learning for Healthcare*. https://doi.org/10.1007/978-3-032-29921-5_38
2. Lazo-Cortés, M. S., Martínez-Trinidad, J. F., Carrasco-Ochoa, J. A., & Almanza-Ortega, N. N. (2020). *Towards Selecting Reducts for Building Decision Rules for Rule-Based Classifiers*. https://doi.org/10.1007/978-3-030-49076-8_7
3. Bazan, J. G., Nguyen, H. S., Nguyen, S. H., Synak, P., & Wróblewski, J. (2000). *Rough Set Algorithms in Classification Problem*. https://doi.org/10.1007/978-3-7908-1840-6_3
4. Lindgren, T. (2004). *Methods for Rule Conflict Resolution*. https://doi.org/10.1007/978-3-540-30115-8_26
5. Gal, Y. (2016). *Uncertainty in Deep Learning*. https://www.cs.ox.ac.uk/people/yarin.gal/website/thesis/thesis.pdf
