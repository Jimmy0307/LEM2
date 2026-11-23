# Federated LEM2：42-Seed Coverage／Conflict 完整研究解讀
**對象：指導教授／研究組報告** · **凍結時間：2026-11-23 11:42:29（Asia/Taipei）** · 研究狀態：INTERIM，不是 188 全部完成。

## 研究口徑與分母

188 個已註冊資料集；42 Seeds × 4 配置（Centralized、Fed IID、Fed α=0.5、Fed α=0.1）= 168 個模型／來源；六種投票策略與 A/B2 為同一規則模型的後處理結果。已取得 30,078／31,584 個模型（95.2%），179／188 來源完整、9 筆仍有缺漏。每份完整資料集 A/B2 各有四個情境；本報告所有跨來源均值先在單一資料集的 42 Seeds 上彙總，然後給每個資料集等權重。這不是依 Test 列數作加權的母體總比例。

在特徵方面，26 筆原始 Features ≤6（25 筆完整）、162 筆原始 Features >6（154 筆完整）。所有高維資料集均僅使用最多六個候選特徵；不能把 full rows 寫成 full features。188 個來源的真實 Target 值沒有完整統一字典，僅類別數與部分來源的原始欄位註冊資料可查。

## 指標定義——為何 Coverage≠Accuracy，Conflict≠錯誤率

假設每一個 Seed 的測試集合有 `T` 筆：
- Test Coverage (%) = `covered_count/T ×100`，至少一條前件符合。
- No-Match (%) = `no_match_count/T ×100`；與 Test Coverage 相加為100%。若有 fallback 猜測，即使 Accuracy 高仍可能沒有規則覆蓋。
- Candidate Coverage (%) = `true_in_candidate_count/T ×100`。在有規則命中且候選集中含真實決策時才記 1。這需知道 Test Truth，所以是**事後診斷指標**，不是部署時可直接知道的訊號。
- Covered but True Absent (pp) = `Test Coverage − Candidate Coverage`。有命中、但候選類別裡沒有正確答案；即使使用完美投票，也不能從現有候選決策選到正確類別。
- Conflict Rate (%) = `test rows with matching rules predicting ≥2 distinct decision labels / T ×100`。同一類別的多條規則不等於 Conflict；Conflict 與 Candidate Coverage 在統計上會重疊，不可直接將這兩個率相減當成「有害衝突」。
- Rule Count = 該情境 union/dedup 後的規則數（跨 Seed 平均）。
- 各類 **mean Test／Covered／No-Match／True-in-Candidates 筆數** 使用逐 Seed 的算術平均；有小數是正常的，不代表原始資料出現半筆記錄。
- Balanced Accuracy 是類別召回的平均。高 Accuracy + 低 BA 可能意味著高度類別不平衡或預測偏向多數類。
- 某一資料集的「best Accuracy / best BA」是從六種政策的 **Test 結果事後取最大平均值**；是描述性 oracle 上界，不可當成預先部署的真實方法表現。兩個 winner 可能不是同一政策。

## 179 個完整來源：A_ALL_RULES（每來源等權）

| 情境 | Test Coverage | Candidate Coverage | Covered but True Absent | No Match | Conflict | Best Accuracy (test-selected) | Best BA (test-selected) |
|---|---:|---:|---:|---:|---:|---:|---:|
| CENTRALIZED | 27.56% | 23.01% | 4.55 pp | 72.44% | 1.26% | 60.18% | 46.50% |
| FED_IID | 46.75% | 39.06% | 7.69 pp | 53.25% | 13.08% | 62.60% | 50.10% |
| FED_A05 | 64.63% | 51.78% | 12.85 pp | 35.37% | 27.20% | 60.15% | 48.80% |
| FED_A01 | 86.54% | 68.50% | 18.04 pp | 13.46% | 55.48% | 55.24% | 45.43% |

**主訊號：**越嚴重的 label-skew，Test Coverage 平均反而越高；但 Conflict 與「規則有命中卻缺正確候選」也升高。因此不能報告「提高 Coverage = 修復 LEM2」。在 A01 179 來源中，113 筆同時達到 Coverage≥80% 且 Conflict≥50%；73 筆 Covered-but-true-absent ≥20 pp。這是描述性篩選門檻，非任何理論臨界值。

## 同一規則模型 A vs B2：真正的 trade-off

| A01 | A_ALL_RULES | B2_TRUE_AS_FALLBACK | B2−A |
|---|---:|---:|---:|
| Test Coverage | 86.54% | 86.54% | 0.00 pp |
| Candidate Coverage | 68.50% | 61.42% | −7.08 pp |
| Covered but True Absent | 18.04 pp | 25.12 pp | +7.08 pp |
| No Match | 13.46% | 13.46% | 0.00 pp |
| Conflict | 55.48% | 33.93% | **−21.55 pp** |
| Best Accuracy | 55.24% | 55.20% | −0.04 pp |
| Best Balanced Accuracy | 45.43% | 47.05% | +1.62 pp |

B2 控制 TRUE 規則的使用，能降低某部分跨決策類別衝突，但也會刪除一部分含真實類別的候選。**Conflict Rate 的改善不等於同等幅度的 Accuracy 或 Balanced Accuracy 改善。** A01 B2 仍有 27／179 筆來源同時符合 Coverage≥80% 且 Conflict≥50%，其餘問題可能來自非 TRUE 規則彼此衝突。

## 分原始特徵數：兩組不是隨機對照，不能直接推論截六特徵影響

A_ALL_RULES、FED_A01、42 Seeds 完整來源：

| 原始 Feature group | n | Test Coverage | Candidate Coverage | No Match | Conflict | Coverage≥80% 且 Conflict≥50% |
|---|---:|---:|---:|---:|---:|---:|
| ≤6（保留所有原有候選欄位） | 25 | 98.36% | 84.31% | 1.64% | 71.36% | 23／25 |
| >6（實際上只用6） | 154 | 84.62% | 65.93% | 15.38% | 52.90% | 90／154 |

這個數字說明：**「截成六維必然增加 Conflict」無法由目前數據成立**。相反，完整低維組的 Conflict 平均更高，但這可能由 Rows、Label 數、領域、離散特徵與 source family 差異造成，完全不能宣稱「高維截斷能降低 Conflict」。需要相同來源不同 k 的配對消融來區分。

### 最有證據力的案例

1. **MNIST（784→6 Features，70,000 Rows）**：四情境 Test Coverage=0%、No Match=100%，Best Accuracy=11.25%、Best BA=10%；此結果代表現有 six-feature baseline 失敗，不是 784-feature MNIST 的最終 performance。
2. **Iris（4→4）**：FED_A01 A 版 Coverage=100%、Candidate=97.78%、Conflict=74.76%；B2 衝突下降約52.62 pp。這種衝突並非因截高維造成。
3. **AI4I Maintenance（6→6）**：FED_A01 A 版 Coverage=99.86%、Candidate=95.15%、Conflict=55.87%；B2 Conflict −38.20 pp、Candidate −9.12 pp。此例強調高候選覆蓋與高衝突可同時存在。
4. **Bioresponse（1,776→6）**：Centralized Coverage=2.09%；FED_A01 Coverage=95.92%、Candidate=67.55%、Conflict=36.96%。沒有多特徵配對實驗前，不得將這種變化全部歸因六特徵。
5. **Bank Marketing（16→6）**：FED_A01 A 版 Coverage=94.97%、Candidate=78.84%、Conflict=55.80%，Best Accuracy=70.02%、Best BA=50.32%；偏高的 Accuracy 與低 BA 並存。
6. **Banana（2→2）**：Centralized Coverage=0.38%；FED_A01 Coverage=95.11%、Candidate=76.31%、Conflict=56.29%；也是對「只有截六維才出現覆蓋反曲線」的反例。

### 更深入的研究問題（本輪不可冒稱已解決）

RQ1：哪部分 Conflict 直接源自空前件 TRUE→class 規則，而哪部分源自非空前件規則的多類重疊？A／B2 只能量測規則處理後差異，不足以單獨確定規則類型的全部因果。

RQ2：是否有「少數類別支持不足」導致 local reduct 退化，令 Coverage 虛高但 candidate precision 下降？需逐 Client 的 class support、TRUE-rule count、rules 的 antecedent length、decision conflict decomposition。

RQ3：特徵維度 2/4/6/8/12/ALL 的改變，能否消除 No Match，或使 rule explosion 和過度擬合惡化？必須固定相同 dataset、seed、Test 與 clients，不能用原本 Features 不同的兩群橫向均值代替。

RQ4：Rule Conflict 與推理成本不是同一件事。即使 Conflict rate 下降，也未必降低規則比對時間、CPU、記憶體與 timeout；需要完整運行時指標才能判斷真正「降載」。

RQ5：目前只做 HFL：三 client 共享 Features 和 Target、僅 Rows/label distribution 不同。真正 feature/target heterogeneous FL 尚未做，不可宣稱跨機構部署有效。

## Web 版使用與證據鏈

- [研究網站（可篩選188個資料集）](./)：切換原始 Features ≤6 / >6、4 個實驗情境、A/B2，逐筆顯示候選缺口與 no-match，點資料集查看全部 8 組結果。
- [188×4×2 完整 1,504 列指標 CSV](./coverage_conflict_188.csv)：所有來源，包括未完成／無結果的行也保留、缺值不填零；包含平均真實筆數與百分比。
- [24 列研究分組統計 CSV](./coverage_conflict_group_summary.csv)：All／原始≤6／原始>6 × 4 情境 × A/B2。
- [原始 188 筆特徵來源稽核](https://github.com/Jimmy0307/LEM2/blob/research/expanded-42seeds-20261120/docs/research/expanded_188_42seeds/review/FEATURE_SELECTION_AUDIT_188.csv)。
- [完整 42 Seeds 建模輸出（原有研究分支）](https://github.com/Jimmy0307/LEM2/tree/research/expanded-42seeds-20261120/docs/research/expanded_188_42seeds/report_catalog/20261123T114229/full42_generated)。
- [規模／反曲線探索報告](https://github.com/Jimmy0307/LEM2/blob/research/expanded-42seeds-20261120/docs/research/expanded_188_42seeds/report_catalog/20261123T114229/regime_exploration/REGIME_EVIDENCE_SYNTHESIS_20261123.md)。

**研究結論（目前只能如此主張）**：跨多來源觀察到 non-IID 條件下 Test Coverage、Candidate Coverage 和 Conflict 的同步變動，以及不同規則版本之間的候選能力／衝突取捨；但由於六特徵上限、client 同構、部分來源 timeout、資料族群依賴與 Test-selected 上界，尚不能宣稱擴張 Features 後的效果，也不能推論共同的臨界點或錯誤量的因果機制。
