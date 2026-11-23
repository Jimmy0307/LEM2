# 2026-11-23｜老師新指示：80/20 與 Validation-first 比較（獨立於 188 × 42）

**狀態：新試驗流程（LEAKAGE CONTROL & DOCKER SMOKE），不是188資料集重跑結果，也不覆蓋 frozen baseline。**

## 最重要的口徑更正

使用者向教授口頭說了「80/20」**外層正確**：既有主程式先依類別把 source.frame 分為外層80%／20%。真正拿來學規則的既有協定則是將外層80%再切80/20，換算為全資料**64% Development / 16% Validation / 20% Test**。原主批雖保留16% Validation，**並未拿它選六種投票策略**。不能把「80/20」誤寫成80%全部都用於訓練的已完成研究。

**老師新提的「80裡面的60訓練20驗證」必須明示以總資料100%為分母：60%訓練＋20%驗證＋20%最終測試。** 驗證20%是從原來80%訓練池抽取四分之一，Test20%在所有對照間保持完全一樣。

## 每個 dataset × seed × scenario × rule variant 的對照 Arms

| Arm（輸出欄位） | 規則訓練 | 挑策略用 | Test | 研究目的 |
|---|---|---|---|---|
| \`STAGED60_VAL_SELECTED\` | 60% | 獨立20% Val只看六Policy的平均Accuracy或BA，固定高者 | 外層相同20% | 是否有實際驗證選法效益 |
| \`REFIT80_VAL_SELECTED\` | 選法後重新用外層80%學規則 | 只沿用上一列在20% Val所選Policy，**不能重新用Test挑** | 相同20% | 正式部署流程；用足80%訓練而無Test選擇洩漏 |
| \`FIXED80_STV\` | 與REFIT80**完全同一個80%規則模型** | 不選，事先固定STV | 相同20% | 隔離策略選擇效益，公平成對比較 |
| \`LEGACY64_VAL_SELECTED\`（可選） | 64% | 16% Val選Policy | 相同20% | 舊分割利用Val的新增對照，**不是原本舊Test選優結果** |
| \`LEGACY64_FIXED_STV\`（可選） | 與上一列同一64%規則模型 | 事先固定STV | 相同20% | 隔離內層Val大小與選法的效果 |

**核心比較**：\`REFIT80_VAL_SELECTED − FIXED80_STV\` 的 Test Accuracy/BA，兩者擬合規則完全相同且Test相同，只差使用何種Policy。再比較 \`STAGED60_VAL_SELECTED\` 與 \`REFIT80_VAL_SELECTED\`，看選法後80%重訓帶來的影響；因規則訓練樣本變了，這一差不能解讀成純粹選法效果。另看 \`LEGACY64_VAL_SELECTED\` 與 \`LEGACY64_FIXED_STV\` 的內層16%驗證效果。

每個臂另保存 \`MAJORITY_ONLY\`（只猜Development訓練多數類別）的 Test Accuracy/BA，避免把規則學習與多數類別Fallback的效益混為一談。

## 驗證選法規範

- 預先指定目標 \`--metric accuracy\` 或 \`--metric ba\`，**不得看Test結果後才改**。每個資料集/Seed的「平均」是 Validation Rows 上的分類正確比例（或類別平均召回）；跨42Seeds的聚合留到完成報告做，不在單個Test資料上選。
- 六策略：FM／SV／STV／GS／PS／PG；同一規則模型上產生六種預測，**不是訓練六個不同LEM2模型**。
- 若Val分數相等，採預先固定的 \`STV → SV → GS → PS → PG → FM\` tie-order；tie不能由Test決定。
- 同一資料集、Seed、情境下四種臂共用相同**外層20%Test IDs**。64/16保留原有Seed和split function，以便方法核對。
- A／B2作獨立分析，不可混用A的Val挑Policy去比較B2 Test，除非另外預先註冊。

## 操作方式（先小型驗證，未授權全188×42重跑）

在Repo根目錄：

\`\`\`bash
python -m pip install numpy==2.3.5 pandas==2.2.3 scipy==1.16.3
python -m experiments.validation_first_20261123.run \
  --csv /data/your.csv --target class \
  --seeds 1 2 3 --scenarios CENTRALIZED FED_IID \
  --metric ba --include-legacy --out /tmp/lem2-validation-output
\`\`\`

Linux Docker：

\`\`\`bash
docker build -f Dockerfile.validation-first -t lem2-validation-first:pilot .
docker run --rm --cpus=4 --memory=8g \
  -v "$PWD/datasets:/data:ro" -v "$PWD/validation_output:/out" \
  lem2-validation-first:pilot \
  --csv /data/your.csv --target class --seeds 1 2 3 \
  --scenarios CENTRALIZED FED_IID --out /out
\`\`\`

Docker image只有數值核心和新Pilot CLI，無需上傳公司資料給外部API。**不是安全聯邦通信實現**，核心\`fedrs.experiment.fit_model\`目前使用Pooled Development建立支持矩陣；不同機構環境必須再補隱私協定。VM Linux部署只需相同Python3.12和requirements-core＋scipy版本；Docker只是便利包裝，並沒有消除硬體記憶體與演算法複雜度限制。使用Linux可由外部\`timeout\`＋cgroups限制CPU時間／RAM，不能誤以為本CLI已實施每模型2700秒watchdog。

**Missing data：此Pilot拒絕缺失值（fail closed）**，因為老師所說的「鄭遠」方法尚未提供確切論文、數學定義或原程式。不得把簡單均值填補、類別Missing-token和粗糙集容忍關係冒充為該方法；確認後新增具名Adapter，以**訓練集內**擬合並對Val/Test只做transform，另做缺失比例消融。

## 四種規則方法的分層比較（擴充規劃，尚未實作／執行）

| 名稱（口頭辨識） | 預定正式算法 | 目前狀態 | 不可直接交換的差異 |
|---|---|---|---|
| LEM2 | 現行 exact reduct＋LEM2 | **本分支有可執行Pilot入口** | classical 下近似／空約簡需明確記錄 |
| RIPPER（口頭「rapier」） | Repeated Incremental Pruning to Produce Error Reduction | **待導入並核對可重現版本** | 有序規則列表、預設類別與剪枝，與LEM2的UNION規則不完全等價 |
| PRISM（口頭「prison」） | PRISM sequential covering | **待導入並核對方法** | 規則與無命中決策處理需定義 |
| DRSA | Dominance-based Rough Set Approach | **待決策Criterion方向與DOMLEM變體** | 必須有序屬性、單調偏好方向、決策類別序；不適合任意名目標籤 |

四算法共同的輸出應包含DataSplitID、FeatureBudget、TargetOntology、缺失值策略、rule_count、Coverage、Conflict、Accuracy、BalancedAccuracy、MacroF1、Latency、PeakRSS、TIMEOUT，以及版本與來源Hash。**只對語意可比的類別與決策問題做paired比較。**

## Gate
1. [x] 程式實作外層同一Test、60/20與64/16兩種內層切分
2. [x] Validation選Policy、固定STV對照、80% refit並獨立輸出Test
3. [x] Majority-only負控制、輸出manifest與CSV
4. [ ] GitHub Actions pytest實際執行PASS
5. [ ] Docker Linux build＋CLI smoke PASS
6. [ ] 真實來源小樣本與與原主批逐Seed結果Parity
7. [ ] 四算法 adapter與鄭遠 missing data 文獻確認後實作
8. [ ] 實際大樣本獨立運算；**嚴禁將本分支結果覆寫主線188×42實驗資料**
