# PR #6 合併前修正紀錄與驗收狀態

**日期**：2026-11-16  
**PR**：https://github.com/Jimmy0307/LEM2/pull/6  
**Base**：`research/report-ready-dashboard-20261109`  
**Head**：`research/federated-rule-degeneracy-redesign-20261116`  
**狀態**：Draft / **人工審閱前不合併**。

## 已完成且有已提交證據的修正

| 類別 | 原問題 | 本次處置 | 證據 |
|---|---|---|---|
| P1 結論方向 | `G5_SECONDARY_DESCRIPTIVE.csv` 定義 `mean_diff=treatment-baseline`；報告誤把 R1−M2、C2−M2 當作 M2−R1、M2−C2 | 報告 §6.2、§6.2.1、Q4、Q5 改成**統一方向 M2−對照**；原始 CSV 不動 | `data/G5_ARM_MEANS.csv`、`data/G5_SECONDARY_DESCRIPTIVE.csv` |
| P1 網站 | 沒有明確列出對照組方向，來源獨立性說法過強 | 新增依網站 CSV 即時計算的 M2−R1/C1/C2 表，且要求符號吻合；調整51份來源措辭 | `docs/research/teacher_dashboard/redesign/index.html` |
| P1 來源獨立性 | 「51份從未用過」可能被讀成已完成原始列級比對 | 與歷史161筆名稱／家族標籤做可重現核對：**精確名稱交集0**，但列出三組名稱近似的人工查核案例；清楚限定為註冊規則層級 | `SOURCE_INDEPENDENCE_REVIEW_20261116.md` |
| P1 研究網站 SHA | Windows 的 CRLF 工作樹先計算 SHA，但 Git 以LF儲存；22份已發布 CSV 的 Manifest SHA 都與網站原始Blob位元組不一致 | 經每份原始研究CSV與網站CSV**位元組完全相同**、舊 SHA 與純CRLF轉換結果一致後，只修訂網站 Manifest 的 `published_sha256`，不動資料 | `experiments/redesign_20261116/reconcile_publication_manifest.py`、`REDESIGN_SITE_MANIFEST.json` |
| P2 CI範圍 | 原CI只測單元與舊引擎Parity，報告改錯方向不會阻斷 | 新增7項資料／假設／路由方向／來源／Manifest的完整性測試，並將新報告與網站修改納入CI觸發路徑；驗證預註冊提交順序 | `tests/test_fedrs_publication_integrity.py`、`.github/workflows/redesign-fedrs-tests.yml` |
| P2 本機主工作樹 | Claude通報 `D:\Desk\LEM2` 1339個未提交刪除 | 不碰本機，保留可只讀的PowerShell診斷與安全復原條件 | `LOCAL_WORKTREE_SAFETY_20261116.md` |

### 強基準校正數據（均為 M2 − 對照；pp）

| 分布 | M2−R1 集中RS | M2−C1 集中CART | M2−C2 聯邦CART |
|---|---:|---:|---:|
| IID | −1.77 | −4.55 | **−3.27** |
| α=0.5 | −0.76 | −4.91 | **−2.08** |
| α=0.1 | −0.97 | −7.22 | **+0.84（n.s.）** |

原始 H1：M2−M0 在三種分布 **+6.09、+5.60、+4.33 pp**；H2：M1−M0於α=.1 **+0.53 pp**。這四個主檢定的原始配對、來源、統計和預註冊文件**沒有因更正文句而被改動**。

## 尚無法由遠端自動完成的事項

1. **本機1,339筆未提交刪除的實際狀態**：此項只能在使用者Windows本機核對，不能將遠端Draft PR狀態代替本機檔案健康證明。禁止直接 `git clean`、`git reset --hard` 或盲目 `git restore`。
2. **真正原始列級的51 vs 歷史161來源獨立性**：目前僅有預註冊家族別名／名稱／Metadata哈希，未完成整個原始採集鏈與列級交疊比對。這是確認性結論的外推限制，不應偷偷改掉預註冊樣本。
3. **大型 Git 原始CSV（約219MB，最大單檔約52MB）**：這次**保留PR歷史不改寫**。將來可採版本化Release／物件儲存庫或DVC與SHA/Manifest索引，但需要確認讀取與保留期限，不能逕自刪掉已提交實驗結果。
4. **正式投稿前**：尚需第二組新來源獨立重現、更多特徵／Client、實際隱私與通訊協定、與真正FedTree等對照；CI通過僅代表現有代碼與已提交實驗數據一致，**不是**獨立重跑10,710任務。

## 閘門規則

- H1/H2仍以原始 `G5_PRIMARY_HYPOTHESES.csv` 為準；**不許**依次要資料的高分改動主假設或樣本。
- 次要對照 `G5_SECONDARY_DESCRIPTIVE.csv`：`mean_diff=treatment-baseline`，若文字要以M2為主角，必須取正確符號，並保留CI／p值未校正與非劣性限制。
- 網站與報告的結論應指回文件與已發布資料，不許只顯示單一模型排名。
- 原分支與42 Seeds基準不更動；PR維持Draft，待人工核閱與CI通過後再決定是否標為Ready for Review。
