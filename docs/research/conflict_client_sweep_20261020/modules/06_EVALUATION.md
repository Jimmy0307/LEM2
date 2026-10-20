# Module 06 — Evaluation

## 目的

這一層只回答：aggregation、conflict structure 與 resolver 最後帶來什麼可量化結果。

## Overall prediction metrics

### Balanced Accuracy

對各 class recall 取平均：

\[
BA=\frac{1}{K}\sum_{k=1}^{K}Recall_k
\]

用來降低 class imbalance 對單純 accuracy 的影響。

### Macro F1

對各 class 的 F1 分數取平均：

\[
MacroF1=\frac{1}{K}\sum_{k=1}^{K}F1_k
\]

### Coverage

有至少一條 rule match 的 test cases 比率：

\[
Coverage=
\frac{\#\{x:|M(x)|>0\}}{N_{test}}
\]

## Conflict-only performance

只在 inference-level conflict cases 上評估 resolver。

令：

\[
X_{conflict}=\{x:|\{d_r:r\in M(x)\}|>1\}
\]

則可以計算：

\[
Conflict\ Resolution\ Accuracy=
\frac{\#correct\ predictions\ on\ X_{conflict}}{|X_{conflict}|}
\]

以及 conflict-only Balanced Accuracy。

這一層非常重要，因為 overall performance 可能掩蓋 resolver 真正面對 conflict 時的表現。

## Order Sensitivity

令 \(\Pi_C\) 為 client arrival order 的 permutations。

若同一 case 在不同 order 下得到不同 prediction：

\[
|\{\hat y_{\pi}(x):\pi\in\Pi_C\}|>1
\]

則該 case 為 order-sensitive。

Order Sensitivity Rate：

\[
OSR=
\frac{\#order\ sensitive\ test\ cases}{N_{test}}
\]

當 \(C\le5\) 時：

\[
5!=120
\]

目前設定可以完整枚舉 client order。

## 評估原則

不同 resolver 必須基於同一 frozen rule artifact 與同一 structural conflict workload 比較。

因此正確順序是：

```text
固定 local rules / global rules / conflict structure
                 ↓
          替換 resolver
                 ↓
       比較 performance
```

不能讓不同 resolver 各自重建 rules，否則比較的就不只是 resolution method。

## Production implementation

- `roughset/evaluation.py::balanced_accuracy`
- `macro_f1_score`
- `classification_accuracy`
- conflict-only metrics in final pipeline
- `roughset/federated.py::audit_order_sensitivity`
- `audit_order_distribution`
