# 研究封版狀態（Research Final Status，2026-11-16）

**分支**：`research/federated-rule-degeneracy-redesign-20261116`　**PR**：https://github.com/Jimmy0307/LEM2/pull/6（base：`research/report-ready-dashboard-20261109`，**未合併**）
**原始研究基準**：`research/report-ready-dashboard-20261109` @ `87e31c4`（未修改）

## 1. 完成度
| 階段 | 狀態 | 證據等級 |
|---|---|---|
| Gate 0 原始管線重現 | PASS（逐位一致） | Independent Review |
| Gate 1 退化規則 | 完成（1,200 模型；24 個 Control C 不可行已記錄） | Exploratory |
| Gate 2 離散化 | 完成（5,610 模型＋561 記憶體量測） | Exploratory |
| Gate 3 雜訊／六策略 | 完成（5,940 模型） | Exploratory |
| Gate 4 衝突感知切點 | 完成（5,100 模型；主要是負面結果） | Exploratory／Negative |
| Gate 5 確認性驗證 | **H1 三個分布 PASS；H2 PASS（效果小）**；10,710 任務、0 失敗 | Confirmatory（預註冊 `89fd52b`） |
| 終版稽核 | 獨立重算一致；126 任務重新執行逐值相同；來源獨立性 PARTIALLY VERIFIED | Independent Review |

## 2. 可驗證成果
| 主張 | 數值 | 怎麼驗證 |
|---|---|---|
| H1：M2 − M0（Test BA） | IID **+6.09** pp [3.91, 8.50]；α=0.5 **+5.60** [3.64, 7.75]；α=0.1 **+4.33** [2.91, 5.83]；Holm p < 0.0001 | `verify_g5_independent --check` |
| H2：M1 − M0（α=0.1） | **+0.53** pp [0.17, 0.96]；p = 0.0007 | 同上 |
| 家族層級敏感度（37 家族） | 三個 H1 全部仍通過 | `G5_H1_FAMILY_SENSITIVITY.csv` |
| Post-hoc 來源敏感度（排除 ada、gina；或再排除 sylvine） | H1 +4.49～+6.51 pp、H2 +0.54 pp，全部符合預註冊通過規則 | `G5_POSTHOC_SOURCE_SENSITIVITY_20261116.csv` |
| TRUE→d 的結構影響（α=0.1，EW3＋A） | 68.6% 配置含 TRUE 規則；Coverage 中 42.4 pp 只靠它命中；Conflict 中 35.2 pp 由它造成 | `G5_STRUCTURE.csv` |
| 重現鏈 | 抽 126 個確認性任務重新執行，POLICIES／STRUCTURE／CONFIG 逐值相同 | `spotcheck_g5_rerun` |

外部對照（次要、描述性，p 未校正，**沒有**非劣性檢定；方向一律為 M2 − 對照，單位 pp）：

| 對照 | IID | α=0.5 | α=0.1 |
|---|---:|---:|---:|
| R1 集中式 RS 辨識切點 | −1.77 | −0.76 | −0.97 |
| C1 集中式 CART | −4.55 | −4.91 | −7.22 |
| C2 聯邦 CART 投票 | −3.27 | −2.08 | +0.84（不顯著） |

## 3. 學術狀態
- **確認的**：在本預註冊協定與這 51 份來源上，FED_MD_HIST＋B2 比原始 EW3＋UNION 好；只改規則層（B2）也有小幅但可檢出的改善。
- **沒有確認的**：新演算法、一般最佳、優於 CART、優於先行研究、任何隱私保證、在完整特徵或更多 Client 上的效果。
- **新穎性**：不宣稱。有效的成分是 Nguyen–Skowron 辨識切點的聯邦化；最接近的先行研究是 Wozniak et al. 2026（聯邦 LEM2）與 Flores et al. 2026（聯邦離散化），兩者都還沒有正面比較。
- **定位建議**：比較適合寫成「聯邦 Rough Set 規則歸納的失效模式（局部確定 ≠ 全域確定）與評估方法論」，而不是新演算法論文。

## 4. 尚未解決（Open Limitations）
| # | 項目 | 狀態 |
|---|---|---|
| L1 | 來源獨立性只到 metadata／文獻層級；ada、gina 很可能與歷史來源同源；sylvine 未驗證；AutoML 挑戰賽其他 7 份的上游未知 | PARTIALLY VERIFIED |
| L2 | 受限設定：前 6 特徵、≤1,800 列、3 Client；絕對 BA 約 44–50% | 已揭露 |
| L3 | FED_MD 只是模擬：沒有通訊協定、沒有安全聚合、沒有 DP；樸素通訊約 7.7×10⁶ 數字／Client | 已揭露 |
| L4 | Gate 1–4 Manifest 的 `git_commit` 不能精確指出程式版本 | 已揭露 |
| L5 | 「獨立」重算與審查都由同一位作者（AI 協助）完成，沒有外部團隊重現 | NOT VERIFIED |
| L6 | 研究頁尚未公開部署（GitHub Pages 來源是原始分支） | BLOCKED（需要人類決定） |

## 5. 入口
- 主報告：`RESEARCH_REPORT_20261116.md`
- 證據索引：`RESEARCH_EVIDENCE_INDEX.md`　｜　架構：`ALGORITHM_ARCHITECTURE.md`　｜　重現：`REPRODUCIBILITY_GUIDE.md`
- PR 審查：`PR6_FINAL_REVIEW.md`　｜　修訂日誌：`FINALIZATION_REVISIONS_20261116.md`　｜　資料治理：`DATA_GOVERNANCE.md`
- 下一步：`NEXT_RESEARCH_ROADMAP.md`
- 預註冊（凍結）：`PREREGISTRATION_CONFIRMATORY_20261116.md`；實作修訂：`PREREGISTRATION_AMENDMENTS_20261116.md`
