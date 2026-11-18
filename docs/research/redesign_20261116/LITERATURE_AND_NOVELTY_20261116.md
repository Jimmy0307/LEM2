# 文獻比對與新穎性評估（2026-11-16）

查核方式：[V] 已由 Crossref／官方會議頁／JMLR 頁或 PDF 確認；[S] 僅由搜尋結果或二手引用確認；UNVERIFIED 無法確認。這是有限度的檢索；**未找到先行研究不等於證明新穎**。

## 1. 必須正面比較的最接近先行研究
1. **Wozniak, K., Sousa, J., Sniezynski, B. (2026). Rule-Based Federated Learning for Healthcare. ICCS 2026, LNCS, 563–578. doi:10.1007/978-3-032-29921-5_38** [V]
   聯邦 LEM2／PRISM／RIPPER；全域等寬離散化（僅用 min/max）；伺服器 UNION + first-match + 多數類預設；只做 **IID** 隨機等分，≤5 Clients。沒有 label skew、全域可信度、TRUE 規則處理或 first-match 以外的衝突策略。→ 本研究的「聯邦 LEM2 + UNION」本身**不是新的**。
2. **Flores, J.L., Calvo, B., Pérez, A. (2026). Federated discretization for supervised classification. Data Mining and Knowledge Discovery 40(5), 85. doi:10.1007/s10618-026-01247-2** [V]
   一輪式聯邦離散化（GMM 代表點），含 entropy-based 變體。→ 本研究的 MDLP_HIST 只是增量變化，不宣稱新穎。

## 2. 其他相關
- Przybyła-Kasperek & Kusztal (2025), ICCS, doi:10.1007/978-3-031-97567-7_11 [S]：分散決策表的衝突分析 + LEM2 等，報告 LEM2 在分散資料上表現差，但未指出單類別 → 空約簡機制；合併原始表，非隱私保護 FL。
- Daole et al. (2024) FUZZ-IEEE, doi:10.1109/FUZZ-IEEE60900.2024.10612109 [V]：非 IID 下聯邦模糊規則分類器（衝突處理細節 UNVERIFIED）。
- Zhang & Yu (2024) LR-XFL, AAAI 38(19) [S/V]：依規則品質加權聚合 Client 邏輯規則。
- Kwatra & Torra (2024) DISCOLEAF, PSD 2024 [V]；Cheng et al. (2021) SecureBoost [V]；Li et al. (2023) FedTree, MLSys [V]：直方圖彙總的先例。
- Cheung et al. (1996) IEEE TKDE；Kantarcioglu & Clifton (2004) IEEE TKDE [V]：由本地計數加總得到全域 support／confidence（分散式關聯規則）。
- Ye, Hu, Wu (2010) IEEE ISKE [V]：水平分割資料的隱私保護屬性約簡。
- Bazan, Skowron, Synak (1994) Dynamic reducts, ISMIS [S]：跨子表穩定性。

## 3. 經典方法
Pawlak (1982) [V]；Ziarko (1993) VPRS, JCSS 46(1):39–59 [V]；Grzymala-Busse (1992) LERS [V]、MLEM2 (2002) [S]；Clark & Grzymala-Busse (2011) GrC、Clark, Grzymala-Busse & Hippe (2014) Fundamenta Informaticae 132(3) 機率近似 [V]；Fayyad & Irani (1993) MDLP, IJCAI 1022–1028 [V]；Kerber (1992) ChiMerge, AAAI 123–128 [V]；Nguyen & Skowron (1995) JCIS'95 Boolean reasoning 量化 [S]、Nguyen (1998) RSCTC, doi:10.1007/3-540-69115-4_75（最佳切點 NP-hard）[V]；Demšar (2006) JMLR 7 [V]；Holm (1979) [S]；Benavoli, Corani & Mangili (2016) JMLR 17 [V]；Benavoli et al. (2017) JMLR 18 [V]；Romano et al. (2022) PMLB, Bioinformatics 38(3) [V]；Bischl et al. (2021) OpenML Benchmarking Suites, NeurIPS D&B [S，作者清單引用前需再核對]。

## 4. 新穎性評估（保守）
| 主張 | 檢索結果 | 可安全使用的說法 |
|---|---|---|
| (i) 單類別 Client → 空約簡 → TRUE→d 在 label skew 下膨脹 Coverage／Conflict | 未找到直接先行研究；但「決策常數 ⇒ POS=U ⇒ 空約簡」是 Rough Set 基本性質 | 「在有限檢索中，未見到對此失效模式在聯邦 label skew 下的命名與量化分析」 |
| (ii) 以聯邦全域可信度篩選局部確定規則 | 部分重疊（分散式關聯規則 confidence、VPRS、規則品質加權） | 只能說是既有元件的組合 |
| (iii) 以跨 Client（留一 Client）規則衝突回饋選切點 | 未找到直接先行研究；且本研究實驗顯示衝突懲罰項**沒有幫助** | 不主張；報告為負面結果 |
| (iv) Nguyen–Skowron 辨識切點的聯邦化（FED_MD），把異類不可辨識對分解為 Client 內 + 跨 Client | 未找到直接先行研究；但核心是既有 MD heuristic + 加總型計數 | 「既有離散化法的聯邦化實作」，不是新演算法；新穎性須進一步檢索與理論分析後再談 |
| (v) 直方圖彙總 MDLP | 部分重疊，Flores et al. 2026 很接近 | 增量，不主張 |
