# LEM2 38-Slide Evidence Audit — 2026-10-26

Audit rule: **RED = factual/conceptual inconsistency; YELLOW = evidence-supported number but over-interpretation / ambiguous label; GREEN = internally consistent and source-supported.**

| Slide | Before | Problem found | Correction applied |
|---:|:---:|---|---|
| 1 | YELLOW | 數字正確，但缺少 single frozen split 邊界 | 首頁直接標註 seed=42 單一 frozen split；描述性 evidence |
| 2 | GREEN | 老師問題 checklist 與後續結構一致 | 保留 |
| 3 | GREEN | Rows / headers / factors / classes / 80-20 數字一致 | 保留 |
| 4 | YELLOW | 「voting weight fitting」「不存在 leakage」措辭過度絕對 | 改為 support/score construction；結論限定為 code/data-flow audit |
| 5 | GREEN | 六方法公式/定義與 implementation 一致 | 保留 |
| 6 | YELLOW | Hayes metrics 數字正確，但容易被讀成可泛化 winner | 加 single-split 描述性限制 |
| 7 | YELLOW | Car metrics 數字正確，但同上 | 加 single-split 描述性限制 |
| 8 | YELLOW | Balance metrics 數字正確，但同上 | 加 single-split 描述性限制 |
| 9 | GREEN | Overall/Target/Candidate Coverage 定義一致 | 保留 |
| 10 | YELLOW | Target/Candidate 欄實際是 class-wise coverage 的 macro average，標籤太像單一 class 指標 | 改成 Macro Target / Macro Candidate 並改 subtitle |
| 11 | GREEN | class-level candidate coverage 數字與 CSV 一致 | 保留 |
| 12 | GREEN | 3+3 toy example 的 T/U/P 與 winner 轉換正確 | 保留 |
| 13 | YELLOW | 把不同 policy winner 的 evidence 寫成 old/new，容易誤以為 evidence 被修改；over-correct 語意過強 | 改成 STD-winner / PS-winner evidence，案例只做 mechanism |
| 14 | GREEN | GS、P、PG 公式與 implementation 一致 | 保留 |
| 15 | YELLOW | old/new winner 標籤易誤解 evidence mutation | 改成 GS-winner / PG-winner evidence，結論限於 scoring 行為 |
| 16 | RED | 把 Target 1–5 固定定義為 corrected/corrected/harmed/harmed/missing；與 Hayes 等真實 cases 矛盾 | 改為 case ID only；Target 編號不帶 outcome 語義 |
| 17 | GREEN | X-ray pipeline M(x)→Candidate→Evidence→Winner 定義一致 | 保留 |
| 18 | GREEN | Balance T1 T_L=19/U_L=16、T_R=18/U_R=18 與 evidence 一致 | 保留 |
| 19 | GREEN | 讀法先看 true candidate 再看 transition 合理 | 保留 |
| 20 | YELLOW | 15 selected cases 容易被讀成 statistical sample | 改成 mechanism anatomy，不做抽樣推論 |
| 21 | RED | Balance T4 left_weight 寫成 1，frozen CSV 為 3 | 修正 left_weight=3 |
| 22 | RED | Car T2 safety、Car T3 lug_boot/safety 與 frozen CSV 不一致 | 修正 T2 safety=med；T3 lug_boot=small, safety=high |
| 23 | RED | Hayes T2 marital_status 寫成 1，frozen CSV 為 2 | 修正 marital_status=2 |
| 24 | GREEN | Conflict operational definition |Candidate(x)|>1 正確 | 保留 |
| 25 | RED | 「12 structural configurations」與後頁「不能把 908 全叫 structural」自相矛盾 | 改成 12 dataset×C configurations |
| 26 | YELLOW | aggregate C=5 workload 高，但原文容易暗示 client count 單調效果 | 加入 Hayes 非單調與非因果限制 |
| 27 | GREEN | 908→392 unique、persistence 分布算術一致，並已有 causal caveat | 保留 |
| 28 | YELLOW | candidate signature 被稱作 decision boundary，語義過度 | 改為 competing-decision combination / candidate signature |
| 29 | RED | fragmentation→shorter rules→more matches→conflict 的箭頭被寫成已證實因果鏈 | 改成已證實 direct condition + 待驗證 working hypothesis |
| 30 | YELLOW | bias / over-correction 用語把演算法 weighting 行為價值化 | 改成 neutral weighting behavior + observed transition outcomes |
| 31 | YELLOW | 908 occurrences 共分母可描述比較，但非獨立樣本；「no universal winner」過強 | 明示重複 objects、改成 frozen-sweep descriptive ranking |
| 32 | RED | rule-length / matching-rule mediator 數字未與目前 908-case evidence bundle 同源驗證，卻拿來支撐 causal chain | 整頁重做，只留已驗證的 dataset×C conflict rates |
| 33 | RED | global rule count / reduct instability 被用來排除機制，但未在同一 frozen evidence bundle 中閉環 | 整頁重做成三個可重現事實；未驗證 mediator 明列待辦 |
| 34 | YELLOW | 43 寫成「次數」但易被理解成 43 unique cases；borderline 無定義 | 改為 43 policy-transition events，移除 borderline |
| 35 | YELLOW | A>0「較像 Corrected」暗示已驗證 predictive association | 改為 directional diagnostic；禁止由符號直接推 corrected probability |
| 36 | YELLOW | 「沒有 universal winner」「candidate boundaries」措辭過強 | 限定為 frozen sweep descriptive top resolver / candidate signatures |
| 37 | GREEN | Code/evidence/CI closure 與既有 branch 狀態一致 | 保留並加 deck re-audit stamp |
| 38 | GREEN | 已主動列出不能宣稱的事項，研究邊界方向正確 | 更新 terminology，讓 final claims 與前頁完全一致 |

## Summary

- RED before correction: **8 slides** (16, 21, 22, 23, 25, 29, 32, 33).
- YELLOW before correction: interpretation/label issues were corrected rather than treated as new empirical findings.
- The corrected deck deliberately removes unsupported mediator claims from slides 32–33 instead of preserving attractive but weak causal storytelling.
- No new algorithm, metric, or dataset result was invented during this audit; corrections are constrained to frozen project evidence and internal consistency.
