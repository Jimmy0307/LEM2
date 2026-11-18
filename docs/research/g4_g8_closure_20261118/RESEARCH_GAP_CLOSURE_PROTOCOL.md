# G4–G8 未結項閉環：六策略、Coverage/No Match 與高維約簡（2026-11-18）

**研究目標**：不是再增加漂亮的模型數量，而是回答三個事前決策：① 哪一類錯誤真正可由最後的六策略修復？② 哪一類 No Match 可以透過 Train-only 規則增補在不惡化 Conflict/BA 下修復？③ 可擴展約簡是否在真正 End-to-End LEM2 上有速度、品質與資源優勢？

**基線**：GitHub PR #6 的 `research/federated-rule-degeneracy-redesign-20261116`；歷史 42 Seeds/G4–G8 探索資料不可覆寫。此文件是**後續研究方案與既有證據稽核**，不是追認先前探索為新預註冊，也不是宣稱新高維實驗已經完成。

## 一、由既有原始表核對的關鍵診斷

| 現象 | 既有原始證據 | 目前只可支持 |
|---|---|---|
| α=.1、UCI20 六策略最大平均 Test BA 差 | `G1_POLICY_SPREAD_FRIEDMAN.csv`：原 UNION 9.019pp；B2=1.098pp；Friedman p=0.849（UCI20探索性） | 大部分原始方法差距受空前件規則影響；不能將不顯著直接解讀為方法等效 |
| α=.1、OpenML 51 六策略差距 | `G5_POLICY_FRIEDMAN.csv`：原 UNION 1.218pp；B2=0.383pp；B2 Friedman **p=0.0437**（未校正） | 差距很小，但並非「完全沒有可偵測差異」；需要效益門檻與多重比較 |
| α=.1、51資料 EW3 原始Coverage | `G5_STRUCTURE.csv`：原 UNION 82.50%、B2 82.50%、完全刪TRUE 40.07%；42.43pp只靠TRUE命中 | B2可保留表面Coverage並重排衝突；不能將這42.43pp當非空規則的可靠Evidence |
| α=.1、51資料 EW3 Conflict | 同表：原 UNION 46.24%、B2 30.76%、刪TRUE 11.07% | 後備規則優先權改變「Active Conflict」；Conflict下降本身不等於分類改善 |
| 有效Coverage增補／聯邦 | `G2_JOINT_COVERAGE_CONFLICT_3SEED_SUMMARY.csv`：65.439%→67.830%（+2.391pp），BA 63.976%→63.961%（−0.015pp） | 訓練補充規則可擴大有效命中，但這一組並未改善BA；No Match不是Abstention |
| 有效Coverage增補／集中式 | 同表：43.167%→56.340%（+13.173pp），BA 59.808%→61.390%（+1.582pp），Active Conflict 2.136%→2.204% | 中心端有正向探索訊號，不能轉稱聯邦端同樣有效或「衝突未增加」 |
| G8約簡可行性 | `G8_OPTIMIZED_REDUCT_MANIFEST.json`：82個CPU配置、36組原始精確對照、16組完整LEM2配對 | 精確POS快取對已測低維配置有相同精確結果；Greedy保持Train POS但非最小約簡，品質可能下降 |

資料來源：相對於 Repository 根目錄，`G1*`、`G5*` 位於 `docs/research/redesign_20261116/data/`；其他 G2/G8 CSV 位於 `docs/research/teacher_dashboard/data/`。請用 `python -m experiments.g4_g8_closure_20261118.evidence_guard` 從原始 CSV 核對，不能僅以本文的四捨五入結果當成計算證據。

## 二、共同評估協定：不可跨 Gate 偷換比較條件

- 對照的觀測單位是 **dataset/family**（Seed為同源重複），預先固定資料名單、來源SHA、Seed、Client數、Label Skew、Development/Validation/Test；每個方法**共享相同Test**。
- 來源與Seed切分沿用64% Development／16% Inner Validation／20% Outer Test；外層 Test 只在所有方法、門檻選定後使用。完全分開 Exploratory（歷史UCI20/PMLB/OpenML51）與新來源Confirmatory。
- 固定無修改版：`A_ALL_RULES`；有適當對照的變體 `B2_TRUE_AS_FALLBACK`；移除TRUE `B_DROP_TRUE` 只作診斷，不可無成本替代。
- 改「最後解析器」時必須凍結 discretizer、partition、reduct、LEM2 和 global rules；改「規則增補」則必須固定 resolver 并比較新加入的 rules。因子矩陣中每一行只動一項；聯合方法另列 interaction。
- 記錄完整的運算時間（包含資料轉換、Reduct、Induction、Prediction）、Peak RSS、通訊 byte（如有）、規則數、全域支持度、No Match/Abstention（分開計數），禁止只報 Reduct階段耗時當全管線耗時。
- 所有報表同時保留 Accuracy、Balanced Accuracy、Macro-F1，主要指標為 dataset等權 **Test BA**；Coverage不是正確率，Active Conflict不是原始Conflict。
- 若新試驗使用歷史51份或歷史20份，必須標為post-hoc/exploratory；新確認性驗證**重新定義全新來源排除規則**，將 `ada`、`gina` 及同源變體作family級排除（保留來源鏈與別名查核）。

## 三、Track A｜六策略適用性與自適應選法（G4）

**核心競爭假說 A0**：在 B2 及相同規則集合下，六策略的有效差異小到不足以支付 Validation／Routing 成本；若如此，**應停止**自適應選法，保留簡單穩健的固定策略。

1. 固定 EW3＋B2、FED_MD＋B2 兩種 rule generation；每種由同一資料/Seed/Client實驗提供六個解析器的資料集級BA（不能與改離散化的改善相加）。
2. 先測 **structural invariance**：當規則與 fallback 都固定，解析器不能改變 Original Exact Coverage、Truth-in-Candidate或Original Conflict；僅 Conflict物件可能改變所選標籤。
3. 依五種錯誤型態分解：NoNonemptyRuleMatch、TRUE-only fallback、NonemptySingleWrong、NonemptyMultipleTruthAbsent、NonemptyMultipleTruthPresentButWrong（剩餘正確類別逐步列明；各類定義應互斥、窮盡）。
4. 先比較事前凍結的固定 GS、SV、六策略 ValidationBest、Conflict-Bucket Router；對固定B2分別報告 Conditional Treatment Effect，按 No-Match、Single、Multi 等子集分群。Test不能做選法輸入。
5. **決策 Gate A**：若在全新來源上，路由相對 ValidationBest **未達預先指定且有實際價值的BA改善 +1pp**，或95%區間跨越0／延遲成本明顯增加，標記 **NO INCREMENTAL VALUE，停止路由研究**。這是**新的決策門檻**，不是既有確認性結果；Friedman p不顯著不能當作等效證明。

## 四、Track B｜真正的 Coverage 與 No Match 修復（G2／G4）

**核心假說 B0**：有效Coverage增加不保證 Test BA 增加，因大量 No Match 是規則生成或正確候選問題；自適應救援必須分離 TRUE-only、真正無規則與正確候選缺失。

`RuleTrace(x)` 必須保存：
- `nonempty_match_count`，`true_match_count`；`raw_candidate_set`、`effective_candidate_set`；
- `true_only`、`raw_no_match`、`effective_no_match`、`abstained`（如果沒有設拒絕機制就全部False）；
- `truth_in_raw_candidate`、`truth_in_effective_candidate`（這兩個只在報告階段有Test真實標籤，線上無法當選法特徵）；
- `active_conflict`、`shadow_conflict`、`final_correct`、`source_policy`。

**必要對照**：原始EW3＋UNION；EW3＋B2；FED_MD＋B2；每一種再正交比較沒有增補、Train-only supplements、Validation-gated supplements；只在原始非空規則未命中時呼叫 supplement。報告 Effective Coverage、**Nonempty Exact Coverage**、TRUE-only Coverage、No Match with Fallback、Correct Candidate Coverage及BA。

**Gate B**：若聯邦端有效Coverage增加但BA的跨來源95% CI沒有支持 **>0** 的提升，定義為 **COVERAGE_ONLY**，不視為分類品質驗收；若 Conflict/Minority Recall 變差，不可依Coverage改善宣稱成功。無法因增加相同原始Label的單前件規則而提升BA，也應記錄為負結果。

**可證明的限制**：固定Global Rules與相同No-Match fallback時，兩個只在Multi-decision Conflict內做不同決策的Resolver，Test Accuracy 差異的絕對值不超過該Conflict子集占所有Test的比例。這是Accuracy（行級）上界，不是BA的相同數值上界；BA需按類別Recall權重獨立導出。對任一TRUE-only個案，沒有非空規則的證據，不得將其算成非空規則命中。

## 五、Track C｜G8高維與約簡加速（工程→模型→研究）

**核心假說 C0**：Exact Cached Reduct在可搜尋維度上維持相同最小基數及所選屬性；Greedy雖快，但只有Train POS相同，不能保證 Test BA，也不能把計算成本只歸給 Reduct。

**三階段階梯**：
1. 校正：4／6／8特徵、600／1600／3200筆，以Reference exact為Oracle，比較Exact cache（相同最小基數與規則ID）、Greedy（同Train POS但不聲稱exact），含空約簡／重複欄／矛盾決策／全常數屬性的變形測試。
2. 全管線：8／12／16／24特徵 × 600／1600／3200／6400筆 × IID／α=.5／α=.1 × 3／5／10 Clients；只有資料來源實際擁有該特徵／列數才進行。跑Reduct→LEM2→Merge B2→Test，所有方法同分割，同離散化，記錄因超時／記憶體不足的右設限事件。**先小批量逐級驗證再放大**。
3. 外部驗證：用原始特徵語義或Train-only特徵選擇；禁止取影像前24個常數像素後宣稱高維成功。較強基準至少集中CART／聯邦CART，真正FedTree等若無忠實實作列Blocked。

**Gate C**：
- Exact Cache：在所有 Reference 可執行配置上 100% 的選出最小基數、POS、規則集一致；若多組同樣基數的約簡可行，先明定 deterministic tie-break，避免誤判。
- Greedy：Full pipeline Test BA 的**來源級**95% CI不能比參考低超過事前指定非劣界限 **−1pp** 才能考慮宣稱品質可接受；需實際做非劣性檢定，不可用p>0.05視為成功。
- 端到端實測壁鐘／CPU／Peak RSS報告，不只Reduct時計。不可用高維Greedy的Train POS=1推論Test性能不減。
- 若原始精確約簡在24特徵不可行，明確標示 Exact/Approximation不同產品線，不宣稱破解NP-hard。

## 六、學術驗收與治理

| 閘門 | 可以在既有資料上驗證 | 真正缺少的證據 | 判定 |
|---|---|---|---|
| G4 六策略適用情境 | UCI20/Friedman、OpenML51/B2、Conflict分解 | 用已凍結候選規則在全新來源驗證Router相對ValBest的實際增益 | **PARTIAL** |
| Coverage／NoMatch | UCI20 Supplement、OpenML51 TRUE-only拆解 | 採B2後新增規則是否能提升聯邦Test BA，且不降低少數類Recall | **PARTIAL** |
| G8 算力與品質 | 82CPU/36exact/16 Full LEM2 | 高維實際完整外測、來源級BA與全流程資源、更多Client | **PARTIAL** |

**停止條件**：三線只要證據不支持正向效果就記錄為負結果並停止優化，**不得用調Seed、挑資料、縮Confidence Interval或改標準硬做出優勢**。新的Confirmatory驗證只能在新來源／新Seeds、上游同源鏈查核與完整預註冊凍結後執行。

## 七、優先可執行入口

1. `python -m experiments.g4_g8_closure_20261118.evidence_guard`：獨立以已發布CSV核對6策略Spread、Coverage、B2效果與G8 16組配對（無下載、無模型重算）。
2. 既有 `python -m experiments.redesign_20261116.verify_g5_independent --check`；`pytest tests/test_fedrs_publication_integrity.py`：維持原確認性結果不變。
3. 原實作入口：`teacher_demo/g4_rule_conflict_router.py`、`teacher_demo/joint_coverage_conflict_3seed.py`、`teacher_demo/g8_greedy_lem2_quality.py`；`experiments/redesign_20261116/gate5_confirmatory.py`。修改前先釐清其CLI與cache依賴，不得臆測現成CLI可以直接跑新大矩陣。
4. 新資料測試輸出放在 `experiments/g4_g8_closure_20261118/` 的新Namespace；沒有正式凍結前**不寫入**舊的 `docs/research/redesign_20261116/data/`。

**下一輪最重要的研究交付**：不是「三條線全部PASS」，而是每條線都有 source-locked 的可執行控制實驗、三項可明確否決的假設、完整Effect Size／資源及不利結果；完成這些才能向老師說「已正式回答在什麼條件下有效」。
