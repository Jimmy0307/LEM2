# Federated LEM2 的 Conflict 與 Prediction Policies

> 本文件是組內與老師討論用的概念版。正式共同名稱採 **Prediction Policies（預測策略）**；「conflict resolution」描述它們在衝突情境中的功能，不把四種方法統稱為四個 resolver 演算法。
>
> Frozen production baseline：`main @ 31b078bb78c6754d04c56a2e1cc849c8feb221d7`

---

## 1. 問題：最後仍必須輸出單一 decision

假設不同 clients 學到：

\[
r_1:X\rightarrow A
\]

\[
r_2:X\rightarrow B
\]

若同一筆測試資料同時符合兩條規則，最後 prediction 仍必須是單一 class：

\[
\hat y(x)\in\{A,B\}
\]

因此研究問題不是「把 A 與 B 合在一起」，而是：

> 當 competing rule evidence 同時存在時，Prediction Policy 要根據什麼 evidence 產生唯一決策？

Rule-conflict literature 一般把「兩條以上 rules cover 同一 example，但 predict different classes」視為衝突情境；本研究以這個 prediction-time 定義作主要 conflict object（Lindgren, 2004；Lindgren & Boström, 2002）。

---

## 2. Aggregation 與 Conflict Handling 必須分開

Frozen implementation 的完整 rule identity 是：

\[
key(r)=(Ante(r),Decision(r))
\]

因此：

\[
X\rightarrow A
\]

與：

\[
X\rightarrow B
\]

是兩條不同完整規則，不會因 antecedent 相同而互相覆蓋。

Federated aggregation 採 UNION：

\[
R_G=\bigcup_{c=1}^{C}R_c
\]

此步驟只回答「哪些 local rules 進入 global ruleset」，不負責決定衝突時 A/B 誰勝出。Woźniak et al. (2026) 的 Federated LEM2 source paper 同樣以 local rules 的 union 建立 global rule set，再進行 inference。

因此流程應拆成：

```text
Local LEM2
    ↓
Federated UNION Aggregation
    ↓
Global Rule Set
    ↓
Conflict Detection
    ↓
Prediction Policy
    ↓
Single Prediction
```

---

## 3. 主要 Conflict 定義：prediction-time conflict set

對測試資料 \(x\)：

\[
M(x)=\{r\in R_G:x\models Ante(r)\}
\]

若 matching rules 的 decisions 不只一種：

\[
|\{d_r:r\in M(x)\}|>1
\]

則 \(x\) 屬於 conflict set：

\[
\boxed{
\mathcal C=\{x\in U_{test}:|\{d_r:r\in M(x)\}|>1\}
}
\]

這個定義直接對應 overlapping/intersecting rules predicting different classes 的既有 rule-conflict 問題（Lindgren, 2004；Lindgren & Boström, 2002）。

### Exact antecedent conflict

如果：

\[
Ante(r_i)=Ante(r_j),\qquad d_i\neq d_j
\]

我們另外記錄為 exact-antecedent structural contradiction。

它是 supplementary structural audit，不取代上面的 prediction-time conflict set；因為不同 antecedents 仍可能同時 cover 同一個 object。

---

# 4. Policy 1 — FIRST_MATCH

Woźniak et al. (2026) 的 Federated LEM2 inference 採 first-match approach；global rule order 保留 client results / local rule order 的順序語意。

令：

\[
R_G=(r_1,r_2,\ldots,r_m)
\]

第一條符合 \(x\) 的 rule：

\[
k^*(x)=\min\{k:x\models Ante(r_k)\}
\]

則：

\[
\boxed{
\hat y_{FM}(x)=d_{r_{k^*(x)}}
}
\]

它使用的 evidence 是：

\[
\boxed{Rule\ Order}
\]

因此：

\[
Client\ Order\rightarrow Global\ Rule\ Order\rightarrow Prediction
\]

FIRST_MATCH 不是 voting method。

**來源**：Woźniak, Sousa, & Śnieżyński (2026), *Rule-Based Federated Learning for Healthcare*. DOI `10.1007/978-3-032-29921-5_38`.

---

# 5. Policy 2 — SIMPLE_VOTING

對 decision \(d\)：

\[
M_d(x)=\{r\in M(x):d_r=d\}
\]

Simple Voting：

\[
\boxed{
S_{SV}(d|x)=|M_d(x)|
}
\]

每一條 matching rule 一票，不考慮 rule support 大小。

它使用的 evidence 是：

\[
\boxed{Matching\ Rule\ Count}
\]

RSES rule-classification literature 將 Simple Voting 描述為 matching rules 對 consequent decision 投等權票（Lazo-Cortés et al., 2020）。

**來源**：Lazo-Cortés et al. (2020), *Towards Selecting Reducts for Building Decision Rules for Rule-Based Classifiers*. DOI `10.1007/978-3-030-49076-8_7`.

---

# 6. Policy 3 — STANDARD_VOTING

Standard Voting 使用 rule support 作為權重。

在 frozen federated implementation 中，對每條 global rule \(r\)，會在 **所有 clients** 上重新估計 decision-consistent positive support：

\[
Supp_c(r)
=
\{z\in U_c:z\models Ante(r)\land D(z)=d_r\}
\]

合併所有 clients：

\[
S_G(r)=\bigsqcup_{c=1}^{C}Supp_c(r)
\]

rule weight：

\[
\boxed{w_F(r)=|S_G(r)|}
\]

最後：

\[
\boxed{
S_{STD}(d|x)=\sum_{r\in M_d(x)}w_F(r)
}
\]

它使用的 evidence 是：

\[
\boxed{Rule\ Support\ Sum}
\]

### 與原文的關係

RSES Standard Voting 的既有原理是 support-weighted rule voting；本研究將 weight 的 evidence scope 擴展為 federated pooled、decision-consistent positive support。因此不能寫成「Lazo-Cortés et al. 已提出本研究的 federated support 定義」。

同一 training object 若同時支持多條 matching rules，可能在多個 rule weights 中重複貢獻。

**來源**：Lazo-Cortés et al. (2020). DOI `10.1007/978-3-030-49076-8_7`.

---

# 7. Policy 4 — GLOBAL_STRENGTH

Bazan et al. (2000) 的 GlobalStrength 核心不是把 rule supports 直接相加，而是先對 matching rules 所 cover 的 class-consistent objects 做 set union，再除以 decision class size。

本研究的 federated 版本：

\[
S_d(x)=\bigcup_{r\in M_d(x)}S_G(r)
\]

令：

\[
N_d=|\{z\in U_{train}:D(z)=d\}|
\]

則：

\[
\boxed{
GS(d|x)=\frac{|S_d(x)|}{N_d}
}
\]

它使用的 evidence 是：

\[
\boxed{Unique\ Class\ Coverage\ Ratio}
\]

相同 object 同時被多條同 decision rules cover 時，在 union 中只計一次。

**來源**：Bazan, Nguyen, Nguyen, Synak, & Wróblewski (2000), *Rough Set Algorithms in Classification Problem*, GlobalStrength Eq. (23). DOI `10.1007/978-3-7908-1840-6_3`.

---

# 8. STANDARD 與 GLOBAL 的差異

假設兩條 A rules：

\[
w(r_1)=100,\qquad w(r_2)=50
\]

STANDARD：

\[
S_{STD}(A)=100+50=150
\]

若兩條 rules 的支持 objects 大量重疊：

\[
|S_G(r_1)\cup S_G(r_2)|=110
\]

且：

\[
N_A=500
\]

則 GLOBAL：

\[
GS(A)=110/500=0.22
\]

所以：

\[
\boxed{STANDARD=Rule\ Support\ Sum}
\]

\[
\boxed{GLOBAL=Unique\ Class\ Coverage\ Ratio}
\]

兩者得到不同 prediction 是方法定義造成的正常結果。

---

# 9. 四種 Prediction Policies 一次看懂

| Prediction Policy | 核心問題 | Evidence | 主要來源 |
|---|---|---|---|
| `FIRST_MATCH` | 誰先 match？ | Rule order | Woźniak et al. (2026) |
| `SIMPLE_VOTING` | 哪個 decision 的 matching rules 多？ | Rule count | Lazo-Cortés et al. (2020) / RSES |
| `STANDARD_VOTING` | 哪個 decision 的 weighted rule evidence 大？ | Federated pooled positive support sum | Lazo-Cortés et al. (2020) 原理 + 本研究 adaptation |
| `GLOBAL_STRENGTH` | 哪個 decision 的 unique class coverage 高？ | Unique support-object union / class size | Bazan et al. (2000) |

最簡單記法：

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

# 10. Tie 與 no-match semantics

如果：

\[
M(x)=\emptyset
\]

使用 pooled-majority default class。

對 SIMPLE / STANDARD / GLOBAL，如果最高 score tie：

1. default class 位於 winners 中 → 選 default class；
2. 否則 → 選字串排序最小的 winner。

因此 implementation semantics 不只是 `argmax`，tie rule 也必須固定。

Production implementation：

```text
roughset/evaluation.py::predict_with_policy
roughset/evaluation.py::_resolve_vote
```

---

# 11. 評量方式

正式主要評量不再使用專案自創名稱 `CRA / CCR / OSR / H_rule` 作理論核心。

使用：

- Balanced Accuracy — Woźniak et al. (2026); Brodersen et al. (2010).
- Macro-F1 — Sokolova & Lapalme (2009).
- Coverage / Ruleset Size / Conditions per Rule / Pairwise Jaccard — Woźniak et al. (2026).
- Conflict-set count / proportion — Lindgren-style conflict set 的描述統計。
- \(BA_{\mathcal C}\) / \(MacroF1_{\mathcal C}\) — 標準分類指標 restricted to conflict set。
- Variation Ratio — client-order categorical disagreement；Gal (2016), Eq. (3.19), citing Freeman (1965).
- repeated experiments 完成後：Friedman + post-hoc / paired Wilcoxon；Demšar (2006)，並與 Healthcare source paper 的 paired Wilcoxon 設計對齊。

完整公式、涵義與 code mapping：

`TEAM_EVALUATION_METRICS_ESTABLISHED.md`

---

# 12. Frozen empirical result 的正確說法

目前 frozen UCI3 單一 holdout/seed 結果顯示：

- Hayes-Roth：nominal FIRST_MATCH 最好或並列最好，但對 client order 高度敏感；
- Car Evaluation：GLOBAL_STRENGTH 的 Balanced Accuracy 在 C=2–5 都最高；
- Balance Scale：C=2–4 STANDARD_VOTING 較高，C=5 GLOBAL_STRENGTH 較高。

因此目前安全結論是：

\[
\boxed{
Policy^*=f(Dataset,Rule\ Structure,Conflict\ Workload,Client\ Configuration)
}
\]

不能宣稱存在 universal best policy。

這一批仍是 mechanism baseline；publication-level superiority 需要 repeated splits/seeds 與正式 statistical comparison。

---

# 13. 老師問「你們 conflict 到底怎麼處理？」

可以直接回答：

> 我們不在 federated aggregation 階段刪除 competing rules，而是以 antecedent + decision 保留完整 rule identity。當同一 test case 同時被不同 decision rules cover 時，依既有 rule-conflict 定義形成 conflict set，再比較四種 Prediction Policies：FIRST_MATCH、Simple Voting、Standard Voting 與 Global Strength。四者使用的 evidence 分別是 rule order、matching-rule count、pooled positive rule-support sum，以及 unique class-coverage ratio。

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
