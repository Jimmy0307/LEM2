# 粗糙集／LEM2：教授報告用全資料集原始筆數、實驗筆數與分類任務

**凍結日期：2026-11-14。** 161 筆研究登錄記錄（包含不同批次、重複來源及未成功項目），**不是 161 個獨立資料領域**。PMLB 117 個候選中 109 個實際完成，8 個失敗；PMLB 含合成任務與同源變體。

**Rows 的正確讀法：** 原始 Rows 是上游來源筆數；實際 Rows 是本批次真正進入訓練／驗證／測試切分前的資料池筆數。特徵亦要分開看原始欄位數與真正使用欄位數。PMLB 此輪每份最多900筆、6特徵，不是以原始十萬筆進行全量 Fit。

**Task 的正確讀法：**每份資料的決策欄位是分類標籤。PMLB 的程式使用通用欄名 `target`，中文任務名稱有些只能作閱讀輔助，無法替代上游資料字典；原始語義待查者已明確註明。UCI 的各式轉換目標（如葡萄酒品質二元化）也不能與原始多類別標籤混為一談。

**六策略測試內容：**固定 Classical 正域約簡＋LEM2 規則集合，比較 First Match、Simple Voting、Standard Voting、Global Strength、Population Standard、Population Global；主要評估 Balanced Accuracy、Macro-F1、Accuracy、規則 Coverage、Conflict、正確候選是否存在，並在 PMLB109 比較 IID 與 Non-IID α=.5／.1 × Seeds 1、7、42（981 組規則系統／5886 筆策略結果）。

**來源保留方式：** UCI 部分已有 Prepared CSV；PMLB 因各資料表原始授權未完全核對，不重新散布 raw rows，只留固定上游 commit、原始與 Prepared SHA-256、實驗結果、程式及來源連結。請用[全欄位 CSV](../data/TEACHER_DATASET_MASTER_20261114.csv)與[原始 JSON](../data/TEACHER_DATASET_MASTER_20261114.json)追溯。

## PMLB 117 候選（109 成功、8 未通過）

| # | 資料集（官方來源） | 原始 Rows | 實際 Rows | 原始特徵 → 實際特徵 | 類別數 | 要預測／分類什麼 | 狀態 |
|---:|---|---:|---:|---|---:|---|---|
| 1 | [adult](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/adult) | 48842 | 900 | 14 → 6 | 2 | 成人收入是否超過收入門檻 | 已通過 |
| 2 | [agaricus_lepiota](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/agaricus_lepiota) | 8145 | 900 | 22 → 6 | 2 | 蘑菇可食用性分類 | 已通過 |
| 3 | [allbp](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/allbp) | 3772 | — | 29 → — | 3 | 甲狀腺異常類型（allbp 任務） | 未通過（不能計入） |
| 4 | [allhyper](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/allhyper) | 3771 | — | 29 → — | 4 | 甲狀腺甲亢相關類別 | 未通過（不能計入） |
| 5 | [allhypo](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/allhypo) | 3770 | 900 | 29 → 6 | 3 | 甲狀腺甲低相關類別 | 已通過 |
| 6 | [allrep](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/allrep) | 3772 | 900 | 29 → 6 | 4 | 甲狀腺替代性分類任務 | 已通過 |
| 7 | [analcatdata_authorship](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/analcatdata_authorship) | 841 | 841 | 70 → 6 | 4 | 文本作者歸屬 | 已通過 |
| 8 | [analcatdata_dmft](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/analcatdata_dmft) | 797 | 797 | 4 → 4 | 6 | 牙科 DMFT 相關離散分類 | 已通過 |
| 9 | [analcatdata_germangss](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/analcatdata_germangss) | 400 | 400 | 5 → 5 | 4 | 社會調查類別分類 | 已通過 |
| 10 | [analcatdata_lawsuit](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/analcatdata_lawsuit) | 264 | 264 | 4 → 4 | 2 | 訴訟相關類別分類 | 已通過 |
| 11 | [ann_thyroid](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/ann_thyroid) | 7200 | 900 | 21 → 6 | 3 | 甲狀腺疾病分類 | 已通過 |
| 12 | [auto_insurance_symboling](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/auto_insurance_symboling) | 205 | — | 24 → — | 6 | 汽車保險風險等級 | 未通過（不能計入） |
| 13 | [backache](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/backache) | 180 | 180 | 32 → 6 | 2 | 背痛或脊柱狀態分類 | 已通過 |
| 14 | [balance_scale](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/balance_scale) | 625 | 625 | 4 → 4 | 3 | 天平狀態（左／平衡／右） | 已通過 |
| 15 | [banana](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/banana) | 5300 | 900 | 2 → 2 | 2 | 合成香蕉形狀兩類分布 | 已通過 |
| 16 | [biomed](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/biomed) | 209 | 209 | 8 → 6 | 2 | 生物醫學來源的二元標籤 | 已通過 |
| 17 | [breast_cancer](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/breast_cancer) | 286 | 286 | 9 → 6 | 2 | 乳癌相關歷史資料類別 | 已通過 |
| 18 | [breast_cancer_wisconsin_diagnostic](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/breast_cancer_wisconsin_diagnostic) | 569 | 569 | 30 → 6 | 2 | 乳癌良性／惡性 | 已通過 |
| 19 | [breast_cancer_wisconsin_original](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/breast_cancer_wisconsin_original) | 699 | 699 | 9 → 6 | 2 | 乳癌良性／惡性 | 已通過 |
| 20 | [bupa](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/bupa) | 345 | 345 | 5 → 5 | 2 | 肝臟相關二元分類 | 已通過 |
| 21 | [calendarDOW](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/calendarDOW) | 399 | 399 | 32 → 6 | 5 | 日期／星期類別任務 | 已通過 |
| 22 | [car_evaluation](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/car_evaluation) | 1728 | 900 | 6 → 6 | 4 | 汽車整體評級分類 | 已通過 |
| 23 | [cars](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/cars) | 392 | 392 | 8 → 6 | 3 | 車輛來源的多類分類 | 已通過 |
| 24 | [chess](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/chess) | 3196 | 900 | 36 → 6 | 2 | 西洋棋局面勝負 | 已通過 |
| 25 | [churn](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/churn) | 5000 | 900 | 20 → 6 | 2 | 客戶流失與否 | 已通過 |
| 26 | [clean1](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/clean1) | 476 | 476 | 168 → 6 | 2 | PMLB clean1 的原始 target 類別（語義待查） | 已通過 |
| 27 | [clean2](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/clean2) | 6598 | 900 | 168 → 6 | 2 | PMLB clean2 的原始 target 類別（語義待查） | 已通過 |
| 28 | [coil2000](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/coil2000) | 9822 | 900 | 85 → 6 | 2 | 保險產品購買／回應 | 已通過 |
| 29 | [congressional_voting_records](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/congressional_voting_records) | 435 | 435 | 16 → 6 | 2 | 國會投票紀錄對應政黨 | 已通過 |
| 30 | [connect_4](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/connect_4) | 67557 | 900 | 42 → 6 | 3 | 四子棋局面結果 | 已通過 |
| 31 | [contraceptive_method](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/contraceptive_method) | 1473 | 900 | 9 → 6 | 3 | 避孕方式類別 | 已通過 |
| 32 | [corral](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/corral) | 160 | 160 | 6 → 6 | 2 | 布林條件相關合成規則 | 已通過 |
| 33 | [credit_approval_australia](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/credit_approval_australia) | 690 | 690 | 15 → 6 | 2 | 信用核准／不核准 | 已通過 |
| 34 | [credit_approval_germany](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/credit_approval_germany) | 1000 | 900 | 20 → 6 | 2 | 信用風險好／壞 | 已通過 |
| 35 | [dermatology](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/dermatology) | 366 | 366 | 34 → 6 | 6 | 皮膚疾病分類 | 已通過 |
| 36 | [dis](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/dis) | 3772 | 900 | 29 → 6 | 2 | PMLB dis 原始 target（上游語義待查） | 已通過 |
| 37 | [dna](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/dna) | 3186 | 900 | 180 → 6 | 3 | DNA 序列類別辨識 | 已通過 |
| 38 | [ecoli](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/ecoli) | 327 | 327 | 7 → 6 | 5 | 蛋白質細胞定位類別 | 已通過 |
| 39 | [fars](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/fars) | 100968 | — | 29 → — | 8 | 交通事故相關類別 | 未通過（不能計入） |
| 40 | [flags](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/flags) | 178 | 178 | 43 → 6 | 5 | 國旗屬性對應分類目標（具體定義待核） | 已通過 |
| 41 | [GAMETES_Epistasis_2_Way_1000atts_0.4H_EDM_1_EDM_1_1](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/GAMETES_Epistasis_2_Way_1000atts_0.4H_EDM_1_EDM_1_1) | 1600 | 900 | 1000 → 6 | 2 | 合成基因交互作用（epistasis）與異質性條件下的二元分類 | 已通過 |
| 42 | [GAMETES_Epistasis_2_Way_20atts_0.1H_EDM_1_1](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/GAMETES_Epistasis_2_Way_20atts_0.1H_EDM_1_1) | 1600 | 900 | 20 → 6 | 2 | 合成基因交互作用（epistasis）與異質性條件下的二元分類 | 已通過 |
| 43 | [GAMETES_Epistasis_2_Way_20atts_0.4H_EDM_1_1](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/GAMETES_Epistasis_2_Way_20atts_0.4H_EDM_1_1) | 1600 | 900 | 20 → 6 | 2 | 合成基因交互作用（epistasis）與異質性條件下的二元分類 | 已通過 |
| 44 | [GAMETES_Epistasis_3_Way_20atts_0.2H_EDM_1_1](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/GAMETES_Epistasis_3_Way_20atts_0.2H_EDM_1_1) | 1600 | 900 | 20 → 6 | 2 | 合成基因交互作用（epistasis）與異質性條件下的二元分類 | 已通過 |
| 45 | [GAMETES_Heterogeneity_20atts_1600_Het_0.4_0.2_50_EDM_2_001](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/GAMETES_Heterogeneity_20atts_1600_Het_0.4_0.2_50_EDM_2_001) | 1600 | 900 | 20 → 6 | 2 | 合成基因交互作用（epistasis）與異質性條件下的二元分類 | 已通過 |
| 46 | [GAMETES_Heterogeneity_20atts_1600_Het_0.4_0.2_75_EDM_2_001](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/GAMETES_Heterogeneity_20atts_1600_Het_0.4_0.2_75_EDM_2_001) | 1600 | 900 | 20 → 6 | 2 | 合成基因交互作用（epistasis）與異質性條件下的二元分類 | 已通過 |
| 47 | [glass2](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/glass2) | 163 | 163 | 9 → 6 | 2 | 玻璃類別（二元任務變體） | 已通過 |
| 48 | [haberman](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/haberman) | 306 | 306 | 3 → 3 | 2 | 乳癌手術後存活狀態（歷史資料） | 已通過 |
| 49 | [hayes_roth](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/hayes_roth) | 160 | 160 | 4 → 4 | 3 | Hayes–Roth 概念分類 | 已通過 |
| 50 | [heart_disease_cleveland](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/heart_disease_cleveland) | 303 | 303 | 13 → 6 | 2 | 心臟病有無 | 已通過 |
| 51 | [heart_disease_hungarian](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/heart_disease_hungarian) | 294 | 294 | 13 → 6 | 2 | 心臟病有無（匈牙利樣本） | 已通過 |
| 52 | [heart_disease_va_long_beach](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/heart_disease_va_long_beach) | 200 | 200 | 13 → 6 | 2 | 心臟病有無（VA Long Beach） | 已通過 |
| 53 | [hepatitis](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/hepatitis) | 155 | 155 | 19 → 6 | 2 | 肝炎患者存活狀態 | 已通過 |
| 54 | [Hill_Valley_with_noise](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/Hill_Valley_with_noise) | 1212 | 900 | 100 → 6 | 2 | 山谷／山峰形狀分類；有／無雜訊變體 | 已通過 |
| 55 | [Hill_Valley_without_noise](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/Hill_Valley_without_noise) | 1212 | 900 | 100 → 6 | 2 | 山谷／山峰形狀分類；有／無雜訊變體 | 已通過 |
| 56 | [horse_colic_lesion_type](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/horse_colic_lesion_type) | 368 | 368 | 20 → 6 | 5 | 馬匹腹絞痛病灶類型 | 已通過 |
| 57 | [horse_colic_outcome](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/horse_colic_outcome) | 366 | 366 | 21 → 6 | 3 | 馬匹腹絞痛結局 | 已通過 |
| 58 | [horse_colic_surgery](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/horse_colic_surgery) | 368 | 368 | 20 → 6 | 2 | 馬匹腹絞痛是否手術 | 已通過 |
| 59 | [hypothyroid](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/hypothyroid) | 3163 | 900 | 25 → 6 | 2 | 甲狀腺機能低下與否 | 已通過 |
| 60 | [ionosphere](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/ionosphere) | 351 | 351 | 34 → 6 | 2 | 雷達回波好／壞 | 已通過 |
| 61 | [iris](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/iris) | 150 | 150 | 4 → 4 | 3 | 鳶尾花品種（三類） | 已通過 |
| 62 | [irish](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/irish) | 500 | 500 | 5 → 5 | 2 | PMLB irish 的原始二元 target（待查） | 已通過 |
| 63 | [kr_vs_kp](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/kr_vs_kp) | 3196 | 900 | 36 → 6 | 2 | 西洋棋國王＋車對國王＋兵局勢 | 已通過 |
| 64 | [led24](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/led24) | 3200 | 900 | 24 → 6 | 10 | 合成七段顯示器數字辨識 | 已通過 |
| 65 | [led7](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/led7) | 3200 | 900 | 7 → 6 | 10 | 合成七段顯示器數字辨識 | 已通過 |
| 66 | [magic](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/magic) | 19020 | 900 | 10 → 6 | 2 | 伽瑪訊號與背景 | 已通過 |
| 67 | [mfeat_factors](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/mfeat_factors) | 2000 | 900 | 216 → 6 | 10 | 手寫數字辨識；使用不同特徵表示（factors） | 已通過 |
| 68 | [mfeat_fourier](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/mfeat_fourier) | 2000 | 900 | 76 → 6 | 10 | 手寫數字辨識；使用不同特徵表示（fourier） | 已通過 |
| 69 | [mfeat_karhunen](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/mfeat_karhunen) | 2000 | 900 | 64 → 6 | 10 | 手寫數字辨識；使用不同特徵表示（karhunen） | 已通過 |
| 70 | [mfeat_morphological](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/mfeat_morphological) | 2000 | 900 | 6 → 6 | 10 | 手寫數字辨識；使用不同特徵表示（morphological） | 已通過 |
| 71 | [mfeat_pixel](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/mfeat_pixel) | 2000 | 900 | 240 → 6 | 10 | 手寫數字辨識；使用不同特徵表示（pixel） | 已通過 |
| 72 | [mfeat_zernike](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/mfeat_zernike) | 2000 | 900 | 47 → 6 | 10 | 手寫數字辨識；使用不同特徵表示（zernike） | 已通過 |
| 73 | [mnist](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/mnist) | 70000 | 900 | 784 → 6 | 10 | 手寫數字 0–9 | 已通過 |
| 74 | [mofn_3_7_10](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/mofn_3_7_10) | 1324 | 900 | 10 → 6 | 2 | 合成 m-of-n 布林判定 | 已通過 |
| 75 | [monk1](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/monk1) | 556 | 556 | 6 → 6 | 2 | MONK 合成規則概念分類 | 已通過 |
| 76 | [monk2](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/monk2) | 601 | 601 | 6 → 6 | 2 | MONK 合成規則概念分類 | 已通過 |
| 77 | [monk3](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/monk3) | 554 | 554 | 6 → 6 | 2 | MONK 合成規則概念分類 | 已通過 |
| 78 | [mushroom](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/mushroom) | 8124 | 900 | 22 → 6 | 2 | 蘑菇可食用性 | 已通過 |
| 79 | [new_thyroid](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/new_thyroid) | 215 | 215 | 5 → 5 | 3 | 甲狀腺類別 | 已通過 |
| 80 | [nursery](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/nursery) | 12958 | 900 | 8 → 6 | 4 | 幼兒園入園推薦等級 | 已通過 |
| 81 | [optdigits](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/optdigits) | 5620 | 900 | 64 → 6 | 10 | 手寫數字識別 | 已通過 |
| 82 | [page_blocks](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/page_blocks) | 5473 | — | 10 → — | 5 | 文件頁面區塊類別 | 未通過（不能計入） |
| 83 | [parity5+5](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/parity5+5) | 1124 | 900 | 10 → 6 | 2 | 合成位元奇偶分類 | 已通過 |
| 84 | [pendigits](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/pendigits) | 10992 | 900 | 16 → 6 | 10 | 筆跡數字辨識 | 已通過 |
| 85 | [penguins](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/penguins) | 344 | 344 | 7 → 6 | 3 | 企鵝物種 | 已通過 |
| 86 | [phoneme](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/phoneme) | 5404 | 900 | 5 → 5 | 2 | 語音音素類別 | 已通過 |
| 87 | [prnn_crabs](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/prnn_crabs) | 200 | 200 | 7 → 6 | 2 | 螃蟹類別／性別相關分類 | 已通過 |
| 88 | [prnn_synth](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/prnn_synth) | 250 | 250 | 2 → 2 | 2 | 合成二元分類問題 | 已通過 |
| 89 | [profb](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/profb) | 672 | 672 | 9 → 6 | 2 | PMLB profb 原始二元 target（待查） | 已通過 |
| 90 | [ring](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/ring) | 7400 | 900 | 20 → 6 | 2 | 合成環形二元分類 | 已通過 |
| 91 | [saheart](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/saheart) | 462 | 462 | 9 → 6 | 2 | 南非心臟病分類 | 已通過 |
| 92 | [satimage](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/satimage) | 6435 | 900 | 36 → 6 | 6 | 衛星影像地表類別 | 已通過 |
| 93 | [schizo](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/schizo) | 340 | 340 | 14 → 6 | 3 | 精神健康研究來源類別（標籤定義待核） | 已通過 |
| 94 | [segmentation](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/segmentation) | 2310 | 900 | 19 → 6 | 7 | 影像分割區域類別 | 已通過 |
| 95 | [shuttle](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/shuttle) | 58000 | — | 9 → — | 7 | 太空梭資料狀態分類 | 未通過（不能計入） |
| 96 | [sleep](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/sleep) | 105908 | 900 | 13 → 6 | 5 | 睡眠狀態分類 | 已通過 |
| 97 | [sonar](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/sonar) | 208 | 208 | 60 → 6 | 2 | 聲納金屬／岩石 | 已通過 |
| 98 | [spambase](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/spambase) | 4601 | 900 | 57 → 6 | 2 | 垃圾郵件與否 | 已通過 |
| 99 | [spect](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/spect) | 267 | 267 | 22 → 6 | 2 | 心臟影像正常／異常 | 已通過 |
| 100 | [spectf](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/spectf) | 349 | 349 | 44 → 6 | 2 | 心臟影像正常／異常 | 已通過 |
| 101 | [splice](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/splice) | 3188 | 900 | 60 → 6 | 3 | DNA 剪接位點類別 | 已通過 |
| 102 | [tae](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/tae) | 151 | 151 | 5 → 5 | 3 | 助教教學評鑑等級 | 已通過 |
| 103 | [texture](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/texture) | 5500 | 900 | 40 → 6 | 11 | 紋理影像類別 | 已通過 |
| 104 | [threeOf9](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/threeOf9) | 512 | 512 | 9 → 6 | 2 | 合成三取九布林判定 | 已通過 |
| 105 | [tic_tac_toe](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/tic_tac_toe) | 958 | 900 | 9 → 6 | 2 | 井字棋終局結果 | 已通過 |
| 106 | [titanic](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/titanic) | 2207 | 900 | 8 → 6 | 2 | 乘客生存與否 | 已通過 |
| 107 | [tokyo1](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/tokyo1) | 959 | 900 | 44 → 6 | 2 | PMLB tokyo1 二元 target（待查） | 已通過 |
| 108 | [twonorm](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/twonorm) | 7400 | 900 | 20 → 6 | 2 | 合成兩常態分布二元分類 | 已通過 |
| 109 | [vehicle](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/vehicle) | 846 | 846 | 18 → 6 | 4 | 車輛輪廓類別 | 已通過 |
| 110 | [vowel](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/vowel) | 990 | 900 | 13 → 6 | 11 | 元音語音類別 | 已通過 |
| 111 | [waveform_21](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/waveform_21) | 5000 | 900 | 21 → 6 | 3 | 合成波形類別辨識 | 已通過 |
| 112 | [waveform_40](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/waveform_40) | 5000 | 900 | 40 → 6 | 3 | 合成波形類別辨識 | 已通過 |
| 113 | [wine_quality_red](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/wine_quality_red) | 1599 | — | 11 → — | 6 | 紅葡萄酒品質等級 | 未通過（不能計入） |
| 114 | [wine_quality_white](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/wine_quality_white) | 4898 | — | 11 → — | 7 | 白葡萄酒品質等級 | 未通過（不能計入） |
| 115 | [wine_recognition](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/wine_recognition) | 178 | 178 | 13 → 6 | 3 | 葡萄酒化學類別 | 已通過 |
| 116 | [xd6](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/xd6) | 973 | 900 | 9 → 6 | 2 | PMLB xd6 原始二元 target（待查） | 已通過 |
| 117 | [yeast](https://github.com/EpistasisLab/pmlb/tree/7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68/datasets/yeast) | 1479 | 900 | 8 → 6 | 9 | 酵母菌蛋白質定位 | 已通過 |

## UCI 20 份

| # | 資料集（官方來源） | 原始 Rows | 實際 Rows | 原始特徵 → 實際特徵 | 類別數 | 要預測／分類什麼 | 狀態 |
|---:|---|---:|---:|---|---:|---|---|
| 1 | [Adult Income](https://archive.ics.uci.edu/dataset/2) | 48842 | 1800 | — → 6 | 2 | 成人年收入是否高於 50K | 已通過 |
| 2 | [Bank Marketing](https://archive.ics.uci.edu/dataset/222) | 45211 | 1800 | — → 6 | 2 | 銀行行銷活動是否成功訂購產品 | 已通過 |
| 3 | [Banknote Authentication](https://archive.ics.uci.edu/dataset/267) | 1372 | 1372 | — → 4 | 2 | 紙鈔真偽分類 | 已通過 |
| 4 | [Breast Cancer Wisconsin Diagnostic](https://archive.ics.uci.edu/dataset/17) | 569 | 569 | — → 6 | 2 | 乳房腫瘤良性／惡性 | 已通過 |
| 5 | [Covertype](https://archive.ics.uci.edu/dataset/31) | 581012 | 1800 | — → 6 | 7 | 森林地表覆蓋植被類別 | 已通過 |
| 6 | [Dry Bean](https://archive.ics.uci.edu/dataset/602) | 13611 | 1600 | — → 6 | 7 | 乾豆品種（七類） | 已通過 |
| 7 | [EEG Eye State](https://archive.ics.uci.edu/dataset/264) | 14980 | 1800 | — → 6 | 2 | 腦波所對應眼睛睜閉狀態 | 已通過 |
| 8 | [Statlog German Credit](https://archive.ics.uci.edu/dataset/144) | 1000 | 1000 | — → 6 | 2 | 信用風險好／壞 | 已通過 |
| 9 | [Electrical Grid Stability Simulated Data](https://archive.ics.uci.edu/dataset/471) | 10000 | 1800 | — → 6 | 2 | 模擬電網穩定／不穩定 | 已通過 |
| 10 | [Haberman Survival](https://archive.ics.uci.edu/dataset/43) | 306 | 306 | — → 3 | 2 | 乳癌手術後存活狀態 | 已通過 |
| 11 | [HTRU2](https://archive.ics.uci.edu/dataset/372) | 17898 | 1800 | — → 6 | 2 | 是否為脈衝星候選訊號 | 已通過 |
| 12 | [Iris](https://archive.ics.uci.edu/dataset/53) | 150 | 150 | — → 4 | 3 | 鳶尾花三種品種 | 已通過 |
| 13 | [Letter Recognition](https://archive.ics.uci.edu/dataset/59) | 20000 | 900 | — → 6 | 26 | 英文字母 26 類 | 已通過 |
| 14 | [MAGIC Gamma Telescope](https://archive.ics.uci.edu/dataset/159) | 19020 | 1800 | — → 6 | 2 | 望遠鏡訊號為伽瑪射線／背景 | 已通過 |
| 15 | [Mushroom](https://archive.ics.uci.edu/dataset/73) | 8124 | 1600 | — → 6 | 2 | 蘑菇可食用／有毒 | 已通過 |
| 16 | [Phishing Websites](https://archive.ics.uci.edu/dataset/327) | 11055 | 1600 | — → 6 | 2 | 釣魚網站／合法網站 | 已通過 |
| 17 | [Rice Cammeo/Osmancik](https://archive.ics.uci.edu/dataset/545) | 3810 | 1600 | — → 6 | 2 | 稻米品種 Cammeo／Osmancik | 已通過 |
| 18 | [Sonar Mines vs Rocks](https://archive.ics.uci.edu/dataset/151) | 208 | 208 | — → 6 | 2 | 聲納目標為岩石／金屬 | 已通過 |
| 19 | [Spambase](https://archive.ics.uci.edu/dataset/94) | 4601 | 1800 | — → 6 | 2 | 電子郵件是否垃圾郵件 | 已通過 |
| 20 | [Wine](https://archive.ics.uci.edu/dataset/109) | 178 | 178 | — → 6 | 3 | 葡萄酒化學特徵的三類辨識 | 已通過 |

## UCI 12 份

| # | 資料集（官方來源） | 原始 Rows | 實際 Rows | 原始特徵 → 實際特徵 | 類別數 | 要預測／分類什麼 | 狀態 |
|---:|---|---:|---:|---|---:|---|---|
| 1 | [Ionosphere Radar Return](https://archive.ics.uci.edu/dataset/52) | 351 | 351 | 34 → 6 | 2 | 351 cases, 34 raw continuous features, binary radar validity | 已通過 |
| 2 | [Yeast Protein Localization](https://archive.ics.uci.edu/dataset/110) | 1484 | 1200 | 8 → 6 | 10 | Ten-class protein localization, class imbalance and rare classes | 已通過 |
| 3 | [Image Segmentation](https://archive.ics.uci.edu/dataset/50) | 210 | 210 | 19 → 6 | 7 | Seven regional image labels from 3x3 image regions; potential shared-image leakage | 已通過 |
| 4 | [Statlog Vehicle Silhouettes](https://archive.ics.uci.edu/dataset/149) | 846 | 845 | 18 → 6 | 4 | Four classes and 18 extracted shape attributes; orientation shift sensitivity | 已通過 |
| 5 | [Heart Disease Cleveland (binary)](https://archive.ics.uci.edu/dataset/45) | 303 | 303 | 13 → 6 | 2 | 303 records, continuous and categorical clinical measures; binary presence >0；目標轉換：heart_disease_binary_gt0 | 已通過 |
| 6 | [Raisin Morphology](https://archive.ics.uci.edu/dataset/850) | 900 | 900 | 7 → 6 | 2 | 900 rows, two balanced visual grain varieties and continuous shape features | 已通過 |
| 7 | [Wine Quality (binary>=6 protocol)](https://archive.ics.uci.edu/dataset/186) | 6497 | 1600 | 11 → 6 | 2 | Originally ordered wine quality labels; explicit secondary BINARY >=6 target task；目標轉換：wine_quality_binary_ge6 | 已通過 |
| 8 | [Student Final-Grade (binary >=10)](https://archive.ics.uci.edu/dataset/320) | 649 | 649 | 30 → 6 | 2 | 649 source records, six PRE-grade features only; explicit G3 final score >=10 target；目標轉換：student_final_grade_ge10 | 已通過 |
| 9 | [Vertebral Column](https://archive.ics.uci.edu/dataset/212) | 310 | 310 | 6 → 6 | 3 | 310 rows, six continuous biomechanics variables, possible two-vs-three target variant | 已通過 |
| 10 | [Higher-Ed Dropout and Academic Success](https://archive.ics.uci.edu/dataset/697) | 4424 | 1800 | 36 → 6 | 3 | 4424 records, three classes, 36 source predictors; pre-enrollment coded attributes only | 已通過 |
| 11 | [Blood Transfusion Service Center](https://archive.ics.uci.edu/dataset/176) | 748 | 748 | 4 → 4 | 2 | Taiwan donor retention 748 records, RFM/T numeric and 24% positive | 已通過 |
| 12 | [Fertility](https://archive.ics.uci.edu/dataset/244) | 100 | 100 | 9 → 6 | 2 | 100 volunteers, rare binary outcome and small sample instability | 已通過 |

## UCI 極端7份

| # | 資料集（官方來源） | 原始 Rows | 實際 Rows | 原始特徵 → 實際特徵 | 類別數 | 要預測／分類什麼 | 狀態 |
|---:|---|---:|---:|---|---:|---|---|
| 1 | [Contraceptive Method Choice](https://archive.ics.uci.edu/dataset/30/contraceptive+method+choice) | 1473 | 1473 | 9 → 9 | 3 | 避孕方法三類選擇 | 已通過 |
| 2 | [Glass Identification](https://archive.ics.uci.edu/dataset/42/glass+identification) | 214 | 214 | 9 → 9 | 6 | 玻璃物理成分類型 | 已通過 |
| 3 | [Nursery capped at 1800](https://archive.ics.uci.edu/dataset/76/nursery) | 12960 | 1800 | 8 → 8 | 5 | 幼兒園入學推薦類別 | 已通過 |
| 4 | [Tic-Tac-Toe Endgame](https://archive.ics.uci.edu/dataset/101/tic+tac+toe+endgame) | 958 | 958 | 9 → 9 | 2 | 井字棋終局結果 | 已通過 |
| 5 | [Congressional Voting first 10 of 16 features](https://archive.ics.uci.edu/dataset/105/congressional+voting+records) | 435 | 435 | 16 → 10 | 2 | 國會投票對應政黨 | 已通過 |
| 6 | [Wisconsin Breast Cancer Original](https://archive.ics.uci.edu/dataset/15/breast+cancer+wisconsin+original) | 699 | 699 | 9 → 9 | 2 | 乳癌良性／惡性 | 已通過 |
| 7 | [Zoo first 10 of 16 features](https://archive.ics.uci.edu/dataset/111/zoo) | 101 | 101 | 16 → 10 | 7 | 動物類別 | 已通過 |

## 電商與設備2份

| # | 資料集（官方來源） | 原始 Rows | 實際 Rows | 原始特徵 → 實際特徵 | 類別數 | 要預測／分類什麼 | 狀態 |
|---:|---|---:|---:|---|---:|---|---|
| 1 | [AI4I Synthetic Predictive Maintenance (stratified public subset 2400)](https://archive.ics.uci.edu/dataset/601/ai4i) | 10000 | 2400 | 6 → 6 | 2 | 合成設備是否發生機械故障（Machine Failure） | 已通過 |
| 2 | [Online Shoppers Conversion (stratified public subset 1600)](https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset) | 12330 | 1600 | 17 → 6 | 2 | 網購瀏覽工作階段是否購買（Revenue） | 已通過 |

## 原始42 Seeds的3份

| # | 資料集（官方來源） | 原始 Rows | 實際 Rows | 原始特徵 → 實際特徵 | 類別數 | 要預測／分類什麼 | 狀態 |
|---:|---|---:|---:|---|---:|---|---|
| 1 | [Balance Scale](https://archive.ics.uci.edu/dataset/12) | 625 | 625 | 4 → 4 | 3 | 天平左傾／平衡／右傾 | 已通過 |
| 2 | [Car Evaluation](https://archive.ics.uci.edu/dataset/19) | 1728 | 1728 | 6 → 6 | 4 | 車輛可接受程度四等級 | 已通過 |
| 3 | [Hayes-Roth](https://archive.ics.uci.edu/dataset/44) | 160 | 160 | 4 → 4 | 3 | Hayes-Roth 概念分類 | 已通過 |

## 研究稽核與報告入口

- [完整117來源來源稽核／Rows／實際抽樣／原始 SHA](../data/PMLB_117_3SEED_SOURCE_AUDIT.csv)
- [109成功資料的G4–G8實驗報告](./G4_G8_109_DATASET_VALIDATION_REPORT.md)
- [5886筆六策略結果](../data/PMLB_117_3SEED_SIX_POLICY_RAW.csv)
- [PMLB109三Seeds完整狀態](../data/PMLB_117_3SEED_MANIFEST.json)
- [UCI20/12可追溯來源](../data/PUBLIC20_MANIFEST.json)／[UCI12](../data/PUBLIC_NEXT12_MANIFEST.json)
- [G8原始36組CPU量測](../data/PMLB_G8_REAL_CPU_STAIRCASE_36.csv)

**學術限制：** 多個 PMLB 任務可能是同源資料或合成資料；原始 Rows 不代表本輪 Fit 列數；若需要精確解釋每個 `target` 的編碼，必須回原始資料卡查證，不能從資料集名稱猜測當作已確認事實。
