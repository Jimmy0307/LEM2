# 聯邦 LEM2 六策略、TRUE-only Coverage 與 B2：形式性質與反例

**日期**：2026-11-18。**理論範圍**：同一決策表切分、同一組全域規則、同一個 default class，且解析器在無命中或只有一個候選決策時採同一預測。這些是本研究實作的工程契約；本文件不宣稱數學新穎性，也不是有隱私保證的聯邦協定。

## 記號

- 测試樣本全集 `T`，每個樣本 `x`；規則 `r` 的前件集合可為空（TRUE）。
- `M_A(x)`：原 UNION 中，前件命中 `x` 的所有規則；`M_S(x)` 是其中 **非空前件** 的規則；`M_E(x)` 是其中 TRUE 規則。它們規則身分不相交，且 `M_A=M_S∪M_E`。
- `M_D(x)=M_S(x)`：直接刪除 TRUE 規則；`M_B2(x)=M_S(x)` 若非空，否則 `M_E(x)`。
- `C_V(x)={decision(r):r∈M_V(x)}`；`Conflict_V(x)=1[|C_V(x)|≥2]`；`Coverage_V(x)=1[|M_V(x)|>0]`。
- `K`：在 Test 中觀測到的決策類別數。 `T_c`：True label 為 c 的測試樣本子集。

## 性質 1｜只改 Resolver 的原始結構不變性

對固定 `M_V`、同一 default class 的任何兩個 resolver `f,g`，若它們在 `|C_V(x)|≤1` 時都按候選唯一類別或 default 類別輸出，則：

`Coverage_f(x)=Coverage_g(x)`、`Conflict_f(x)=Conflict_g(x)`、`C_f(x)=C_g(x)`。而 `f(x)≠g(x)` 的所有樣本必落在 `|C_V(x)|≥2`。

**證明**：原始規則 `M_V` 不依 Resolver 改變；候選決策集合及其基數因此不變。零候選只能採共同 default，一候選只能採該唯一值。反證：若 `f(x)≠g(x)`，不可能是零／一候選，所以至少二候選。□

## 性質 2｜Accuracy 與 Balanced Accuracy 的可改善上界

上式條件下，`N=|T|`，令 `Z={x∈T:|C_V(x)|≥2}`：

`|Accuracy(f)-Accuracy(g)|≤|Z|/N`。

更精確的 BA 上界為：

`|BA(f)-BA(g)|≤(1/K)∑_{c:|T_c|>0}(|Z∩T_c|/|T_c|)`。

**證明**：若兩方法對樣本做出相同預測，該樣本的正確性貢獻完全相同；兩方法的正確性變化最多在 `Z`。Accuracy 對所有樣本權重相同，取絕對值及三角不等式得到第一式。BA 是各真實類別 Recall 的算術平均，對每個 `T_c` 同樣計算界限再平均得到第二式。□

**關鍵提醒**：不能把 BA 增益界直接寫成總 Conflict Rate。若Conflict全集中於小樣本少數類，BA 的改變仍可能很大；必須使用按真實類別加權的第二式。因此任何「路由器多救回幾% BA」都要用類別條件Conflict作正確的潛力界限。

## 性質 3｜TRUE-only、Coverage 差及 B2 的衝突單調性

對每個樣本：

1. `Coverage_A(x)-Coverage_D(x)=1[|M_S(x)|=0 ∧ |M_E(x)|>0]`。
2. `Coverage_A(x)=Coverage_B2(x)`。
3. `C_B2(x)⊆C_A(x)`，所以 `Conflict_B2(x)≤Conflict_A(x)`。

**證明**：若有非空規則，A、D、B2 均被非空規則命中，Coverage差為0；若沒有非空規則，A只有TRUE可以命中，D必為無命中，B2則保留TRUE。這給出前兩式。B2所選規則必為A的子集，故其候選決策集合也是A的子集，不能增加候選決策數（亦不能由無Conflict變成有Conflict）。□

**限制**：此處 `Conflict_B2≤Conflict_A` 只是原始規則集合下的定義與優先權的結構結果，**不構成任何Test BA更高的證明**，亦不代表 `TRUE→d` 應由數學上刪除。

## 反例 1｜B2 減少Conflict仍可能使預測變錯

讓 Test 真實 `y=A`，非空規則 `r_1: (a=x)→B`，TRUE 規則 `r_2: TRUE→A`。原 UNION 有兩候選 `{A,B}`；若原解析器的權重使A勝，原本正確。B2因存在非空規則而排除TRUE，候選只剩B，最後必錯。因此 `Conflict_B2<Conflict_A` 不蘊涵 `Accuracy_B2≥Accuracy_A`，更不蘊涵 `BA_B2≥BA_A`。同一構造把真實標籤換成B則得到B2可能改好的情況。

## 反例 2｜Coverage提高但 BA 不變或降低

在測試物件x原本沒有任何非空匹配規則時，增補 `r_3` 可以使有效Coverage由0變1。但如果補充規則預測的類別與真實答案不同、而原 default class原本正確，Test accuracy反而會降低。即使增補規則與default預測相同，Coverage會上升而Accuracy不變。故有效Coverage提升不是成功的充分條件；還需同一分割下的True Candidate、BA、Macro-F1及Minority Recall對照。

## 反例 3｜Greedy 保持Train POS≠外部泛化不減

設候選特徵a與b在Train中完美相關，且相對決策有相同POS；選擇a或b都使Train POS不減。若Test中a維持決策關係而b受分布轉移變成常數或反向關係，兩個Reduct對Test的判斷可不同。因此訓練POS等價不足以保證Test BA相同，更不能保證Greedy取得最小基數Reduct。現有16組完整LEM2配對也包含 Test BA −3.719pp與 +1.099pp案例，構成工程上的直接警示。

## 適用於本研究的實作驗收

- `experiments/g4_g8_closure_20261118/rule_trace.py` 逐筆算非空規則、TRUE-only、B2有效候選及原始／active Conflict，Test標籤只提供離線統計，不參與預測。
- `tests/test_g4_g8_rule_trace.py` 檢查Coverage相同但Conflict可能變動、刪TRUE導致NoMatch、多數類Fallback不等於Abstention。
- `experiments/g4_g8_closure_20261118/evidence_guard.py` 逐表重算現存UCI20/OpenML51/G8關鍵數值，避免引用錯誤方向。
- 此文件不等於宣稱找到 `conf_G(r)` 的非平凡下界，也未證明B2普遍優越。R5「局部規則可信度下界」仍是獨立未完成研究問題。
