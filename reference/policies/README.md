# Separated Prediction Policy Reference Code

這個資料夾只用於老師／組員閱讀與方法對照。Production runtime 的 canonical implementation 仍在：

```text
roughset/evaluation.py::predict_with_policy
```

四個檔案：

```text
first_match.py
simple_voting.py
standard_voting.py
global_strength.py
```

分別對應：

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

## 1. FIRST_MATCH

\[
k^*(x)=\min\{k:x\models Ante(r_k)\}
\]

\[
\hat y(x)=d_{r_{k^*(x)}}
\]

來源：Woźniak, Sousa, & Śnieżyński (2026), *Rule-Based Federated Learning for Healthcare*. DOI `10.1007/978-3-032-29921-5_38`.

## 2. SIMPLE_VOTING

\[
S_{SV}(d|x)=|M_d(x)|
\]

來源：Lazo-Cortés et al. (2020), *Towards Selecting Reducts for Building Decision Rules for Rule-Based Classifiers*. DOI `10.1007/978-3-030-49076-8_7`.

## 3. STANDARD_VOTING

\[
S_{STD}(d|x)=\sum_{r\in M_d(x)}w_F(r)
\]

其中 frozen federated implementation 使用：

\[
w_F(r)=\sum_c|\{z\in U_c:z\models Ante(r)\land D(z)=d_r\}|
\]

來源：Lazo-Cortés et al. (2020) 的 support-weighted voting principle；上述 all-client decision-consistent support scope 是本研究的 federated adaptation。

## 4. GLOBAL_STRENGTH

\[
GS(d|x)=\frac{|\cup_{r\in M_d(x)}S_G(r)|}{N_d}
\]

來源：Bazan et al. (2000), *Rough Set Algorithms in Classification Problem*, GlobalStrength Eq. (23). DOI `10.1007/978-3-7908-1840-6_3`.

## Tie / no match

Reference code 與 frozen runtime 使用相同 semantics：

- no matching rule → default class；
- voting / strength score tie → default class 若在 tied winners 中就選 default；否則選字串排序最小的 winner。

## Parity test

`tests/test_reference_policy_examples.py` 使用同一個 hand-checkable rule set，將四支 reference function 的輸出逐一與 `roughset.evaluation.predict_with_policy()` 比對。Reference code 若與 frozen runtime 漂移，測試會失敗。
