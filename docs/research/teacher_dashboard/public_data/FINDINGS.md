# 公開電商與工業設備：Classical／Federated LEM2 實測發現

**狀態：EXPLORATORY_4_SEEDS_COMPLETED。** 已完成 8 個研究任務，280 列結果（40 組規則集合 × NONE＋六策略）。這是 Seed 1、7、21、42 的探索性對照，**不是 42 Seeds，也不是統計顯著性的充分證據**。完整執行證據、公開資料與授權詳見 [研究頁](./) 及 [Manifest](../data/PUBLIC_COMMERCE_TECH_PILOT_MANIFEST.json)。

## 資料來源與範圍

- **電商**：UCI Online Shoppers Purchasing Intention，原始 12,330 筆，購買 1,908；研究用固定分層 1,600 筆，其中購買 248 筆，六特徵，排除 PageValues。DOI [10.24432/C5F88Q](https://doi.org/10.24432/C5F88Q)。
- **技術設備**：UCI AI4I 2020 Predictive Maintenance，原始 10,000 筆；研究用固定分層 2,400 筆，其中故障 81 筆，六特徵，排除識別碼及故障原因結果欄。DOI [10.24432/C5HS5C](https://doi.org/10.24432/C5HS5C)。**此資料為合成工業資料，不是真實工廠記錄。**
- 兩份資料皆 CC BY 4.0，實驗子集與來源歸屬存於 [公開資料資料夾](../../public_datasets/)。
- 協定為 80/20 Holdout、Train-only 前處理與 Classical Reduct＋LEM2；Centralized 與 Fed C2–C5，六種決策策略。同架構／Seed 共用規則集合。原 8,820 筆三資料集基線未修改。

## 代表性比較：真實執行，四 Seeds 平均

| 資料 | 架構 | 分類選擇 | Train Coverage | Test Coverage | Conflict | Accuracy | Balanced Accuracy | 少數類別 Recall |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 電商 | Centralized | First Match（六策略績效一致） | 4.06% | 4.53% | 0.00% | 84.45% | 50.45% | 1.00% |
| 電商 | Fed C3 | Global Strength | 23.20% | 21.33% | 1.95% | 84.14% | 51.49% | 4.00% |
| 電商 | Fed C5 | Global Strength | 25.00% | 22.73% | 2.58% | 84.53% | 52.13% | 5.00% |
| AI4I | Centralized | First Match | 66.04% | 66.82% | 0.21% | 96.35% | 50.59% | 1.56% |
| AI4I | Fed C3 | Global Strength | 98.31% | 98.54% | 2.03% | 96.15% | 52.75% | 6.25% |
| AI4I | Fed C5 | Global Strength | 100.00% | 100.00% | 5.99% | 96.35% | 49.84% | 0.00% |
| AI4I | Fed C5 | First Match | 100.00% | 100.00% | 5.99% | 95.47% | 53.91% | 9.38% |

來源：[完整結果](../data/PUBLIC_COMMERCE_TECH_PILOT_RESULTS.csv)及[四 Seeds 策略彙整](../data/PUBLIC_COMMERCE_TECH_PILOT_POLICY_SUMMARY.csv)。百分比為四 Seeds 配置平均；此表不同架構會產生不同規則集合，不能只將效果歸因於決策選擇。

## 研究判讀

**電商失敗模式：No Match 主導。** Centralized Test Coverage 僅 4.53%，Conflict 0%。六策略績效相同，不是都擅長電商，而是多數測試資料沒有規則命中、回退多數類別。約 84% Accuracy 接近未購買的多數比例，**不能當成有效購買預測能力**。要優先研究 Train-only 補充規則、穩健離散化與 Candidate Coverage；光改 Conflict Winner 收益有限。

**工業失敗模式：Coverage 高但稀有故障漏報。** Fed C5 Test Coverage 100%，Global Strength 故障 Recall 卻是 0%；同一組規則使用 First Match 則有 9.38% Recall，代價是 Accuracy 從 96.35% 降到 95.47%。這說明 **Coverage 不是正確性，Accuracy 不是少數類別能力**。在四 Seed 探索中，Fed C4 Population Global 平均 Balanced Accuracy 54.82%、故障 Recall 10.94%，仍遠不及部署要求，也不能宣稱普遍最優。

**真正的下一步**：分開測 No Match 的可驗證補充規則，與已命中規則但少數類別決策失敗的勝者選擇。測試多個不同特性的資料集，增加 Seeds、non-IID、完整特徵、外部分割及 Risk–Coverage；所有門檻只用 Train 內部 validation 選定，Test 僅供評估。不要將 No Match 直接稱為已實現的 Reject／Abstain。

## 重現資料

- [公開 CC BY 資料子集與來源註記](../../public_datasets/)
- [四 Seeds 完整實驗與來源雜湊 Manifest](../data/PUBLIC_COMMERCE_TECH_PILOT_MANIFEST.json)
- [280 行原始結果](../data/PUBLIC_COMMERCE_TECH_PILOT_RESULTS.csv)
- [四 Seeds 六策略結果](../data/PUBLIC_COMMERCE_TECH_PILOT_POLICY_SUMMARY.csv)
- [六策略各資料集勝出／平票](../data/PUBLIC_COMMERCE_TECH_PILOT_WIN_COUNTS.csv)
- [GitHub Actions 可重現執行](https://github.com/Jimmy0307/LEM2/actions/workflows/public-commerce-tech-uci.yml)

*風險與限制：只使用各資料集六個預先選定特徵；電商資料歷史性與單一來源偏差；AI4I 是合成故障資料；僅四 Seeds，罕見類別在每次測試只有少數樣本；不代表真實部署效能。*
