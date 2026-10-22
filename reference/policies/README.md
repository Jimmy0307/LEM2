# Separated Prediction Policy Reference Code

這個資料夾只用於老師／組員閱讀與方法對照。Production runtime 的 canonical implementation 仍在：

```text
roughset/evaluation.py::predict_with_policy
```

目前共六支：

```text
first_match.py
simple_voting.py
standard_voting.py
global_strength.py
population_standard.py
population_global.py
```

其中前四種是既有方法／既有原理的 baseline；後兩種是 2026-10-22 會議後新增的 **project-defined experimental variants**，不能引用成既有文獻已提出的方法。

## 1. FIRST_MATCH

\[
k^*(x)=\min\{k:x\models Ante(r_k)\},\qquad
\hat y(x)=d_{r_{k^*(x)}}
\]

來源：Woźniak, Sousa, & Śnieżyński (2026), *Rule-Based Federated Learning for Healthcare*. DOI `10.1007/978-3-032-29921-5_38`.

## 2. SIMPLE_VOTING

\[
S_{SV}(d|x)=|M_d(x)|
\]

來源：Lazo-Cortés et al. (2020), DOI `10.1007/978-3-030-49076-8_7`.

## 3. STANDARD_VOTING

\[
S_{STD}(d|x)=\sum_{r\in M_d(x)}w_F(r)
\]

其中 frozen federated implementation 使用所有 clients 上的 decision-consistent positive support。來源是 Lazo-Cortés et al. (2020) 的 support-weighted voting principle；federated support scope 是本研究 adaptation。

## 4. GLOBAL_STRENGTH

\[
GS(d|x)=\frac{|\cup_{r\in M_d(x)}S_G(r)|}{N_d}
\]

來源：Bazan et al. (2000), GlobalStrength Eq. (23), DOI `10.1007/978-3-7908-1840-6_3`.

## 5. POPULATION_STANDARD — project-defined

對同一 candidate decision \(d\)：

\[
T_d=\sum_{r\in M_d(x)}|S_G(r)|
\]

\[
U_d=\left|\bigcup_{r\in M_d(x)}S_G(r)\right|
\]

\[
P_d=\frac{U_d}{T_d}
\]

新的 Standard correction：

\[
\boxed{S_{PS}(d|x)=T_dP_d=U_d}
\]

也就是把同一 training population 因多條 matching rules 而重複出現的 support occurrence 去重。

會議例子：兩條 A-rule support 分別是 `{u1,u2,u3}` 與 `{u2,u3,u4}`，則 \(T_A=6\)、\(U_A=4\)、\(P_A=4/6=2/3\)，修正後 score = 4。

## 6. POPULATION_GLOBAL — project-defined

保留 GlobalStrength 的 class-size normalization，再套用同一 population nonredundancy ratio：

\[
\boxed{
S_{PG}(d|x)
=
\frac{U_d}{N_d}\cdot\frac{U_d}{T_d}
=
\frac{U_d^2}{N_dT_d}
}
\]

這是目前依 2026-10-22 會議需求凍結的實驗定義，不是 Bazan et al. (2000) 的原公式。

## Tie / no match

六支 reference code 與 runtime 使用相同 semantics：

- no matching rule → default class；
- score tie → default class 若在 tied winners 中就選 default；否則選字串排序最小的 winner。

## Parity test

`tests/test_reference_policy_examples.py` 將六支 reference functions 的輸出與 `roughset.evaluation.predict_with_policy()` 逐一比對。Reference code 若與 runtime 漂移，測試會失敗。
