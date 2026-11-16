# 研究證據索引（Research Evidence Index）

所有路徑相對於儲存庫根目錄；`data/` 指 `docs/research/redesign_20261116/data/`。每個檔案的 SHA-256（以 LF 正規化，等於 Git blob 內容）列在 `RESEARCH_DATA_SHA256_INDEX_20261116.json`，用 `python -m experiments.redesign_20261116.evidence_index` 驗證。

## 證據等級
| 等級 | 意義 |
|---|---|
| Historical Baseline | 原始研究分支 `research/report-ready-dashboard-20261109`（`87e31c4`）的結果，本研究不修改 |
| Exploratory Evidence | 用已探索過的來源或 Seeds 得到，可以產生假設，不能確認 |
| Confirmatory Evidence | 預先註冊（`89fd52b`）、在新來源與新 Seeds 上執行一次的結果 |
| Independent Review | 不依賴原分析程式的重算、一致性測試與稽核 |
| Corrected Interpretation | 原始數據不變、只更正文字解讀的項目 |
| Negative Findings | 經過檢驗但沒有效果的設計 |
| Open Limitations | 已知、尚未解決的限制 |
| Future Research | 下一階段的研究問題（見 `NEXT_RESEARCH_ROADMAP.md`） |

## 1. Historical Baseline（未修改；與 `87e31c4` 比對只差首頁導覽連結）
| 研究 | 位置 | 備註 |
|---|---|---|
| 42 Seeds Classical／Federated C2–C5 | `docs/research/seed_sweep_1_42/`；分支 `research/seed-sweep-1-42-20261108`、`research/teacher-evidence-42-20261109` | Seeds 1–42 |
| 六策略比較、Conflict／平票 | `docs/research/teacher_dashboard/conflict/`、`data/ADAPTIVE_SIX_20_*`、`CONFLICT_EXACT_42SEEDS.csv` | 本研究重新解讀：六策略差異大多來自 TRUE 規則 |
| G4 Router、G8 加速 | `docs/research/teacher_dashboard/g4_g8/`、`data/G4_ROUTER_UCI20_*` | `tests/test_fedrs_parity.py` 逐位重現 Router 數字 |
| 離散化／缺值／Router 控制消融 A/B/C | `docs/research/teacher_dashboard/g4_g8/controlled_ablation.html`、`data/CONTROL_A_*`、`CONTROL_B_*`、`CONTROL_C_*` | |
| UCI20、Next12、Extreme7 | `docs/research/public_datasets_20/`、`public_datasets_next12/`、`data/EXTREME_UCI_PILOT_*` | UCI20 在本研究 Gate 0–4 中再次使用，因此只算探索性 |
| PMLB117 | `docs/research/teacher_dashboard/pmlb_117/`、`data/PMLB_117_*` | |
| 161 份歷史來源清單 | `docs/research/teacher_dashboard/data/TEACHER_DATASET_MASTER_20261114.csv` | Gate 5 排除對照 |

## 2. 重建研究各 Gate

| Gate | 等級 | 程式 | 原始輸出 | Manifest | 分析輸出 | Seeds | 規模／失敗 | 資料提交 | 報告 |
|---|---|---|---|---|---|---|---|---|---|
| 0 重現 | Independent Review | `tests/test_fedrs_parity.py`、`tests/test_fedrs_units.py` | — | — | — | 11、23 | 3 案例＋單元測試 | `4b35744` | §1 |
| 1 退化規則 | Exploratory | `experiments/redesign_20261116/gate1_degeneracy.py` | `REDESIGN_G1_DEGENERACY_{CONFIG,POLICIES,STRUCTURE,CLIENTS}.csv` | `REDESIGN_G1_DEGENERACY_MANIFEST.json` | `analyze_g1.py` → `G1_*.csv` | 11、23、101–108 | 1,200；24 失敗（Control C 不可行，`*_FAILURES.csv`） | `4b35744`；分析於 `54f0282` 重算 | §2 |
| 2 離散化 | Exploratory | `gate2_discretization.py`（`--memory`） | `REDESIGN_G2_DISCRETIZATION_*.csv`、`*_MEMORY_*` | 同名 `*_MANIFEST.json` | `analyze_g2_g4.py` → `G2_*.csv`、`G2G4_*.csv` | 同上 | 5,610 ＋ 561 記憶體量測；0 失敗 | `4b35744`、`54f0282` | §3 |
| 3 雜訊 | Exploratory | `gate3_noise.py` | `REDESIGN_G3_NOISE_{REAL,SYNTHETIC}_*.csv` | 同名 `*_MANIFEST.json` | `analyze_g3.py` → `G3_*.csv` | 同上；合成資料另有 generator seed | 4,320 ＋ 1,620；0 失敗 | `54f0282` | §4 |
| 4 衝突感知切點 | Exploratory／Negative Findings | `gate2_discretization.py --p4`、`fedrs/conflict_cuts.py` | `REDESIGN_G4_PROTOTYPES_*.csv` | `REDESIGN_G4_PROTOTYPES_MANIFEST.json` | `G2G4_*.csv`、`G4_LOCO_CHOICES.csv` | 同上 | 5,100；0 失敗 | `89fd52b` | §5 |
| 5 煙霧測試 | Disclosed pre-freeze run | `gate5_confirmatory.py` | `REDESIGN_G5_CONFIRMATORY_SMOKE_*.csv` | `*_SMOKE_MANIFEST.json` | — | 1 份來源、1 個 Seed | 14 任務 | `89fd52b` | §6、修訂紀錄 |
| 5 確認性驗證 | **Confirmatory** | `gate5_confirmatory.py`、`confirmatory_registry.py` | `REDESIGN_G5_CONFIRMATORY_{CONFIG,POLICIES,STRUCTURE,FAILURES}.csv`、`CONFIRMATORY_SOURCE_REGISTRY.csv` | `REDESIGN_G5_CONFIRMATORY_MANIFEST.json`（code `e57e306`） | `analyze_g5.py` → `G5_*.csv` | 1001–1010 | 10,710；0 失敗；51 份來源 | `54f0282` | §6 |
| 5 獨立重算 | Independent Review | `verify_g5_independent.py` | — | `G5_INDEPENDENT_RECOMPUTATION_20261116.json` | `G5_INDEPENDENT_RECOMPUTATION_20261116.csv` | 1001–1010 | 13 項比較逐值一致 | 本輪 | `FINALIZATION_REVISIONS` |
| 5 來源稽核 | Independent Review／Open Limitation | `source_metadata_audit.py` | OpenML API metadata 快照 | — | `G5_SOURCE_METADATA_AUDIT_20261116.csv`（＋`_FAILURES.csv`） | — | 51/51 取得 | 本輪 | `SOURCE_INDEPENDENCE_REVIEW` |
| 5 來源敏感度 | **Post-hoc**（非預註冊） | `verify_g5_independent.py` | — | — | `G5_POSTHOC_SOURCE_SENSITIVITY_20261116.csv` | 1001–1010 | 49／48 份來源 | 本輪 | 報告 §7.1 |
| 6 發布 | — | `publish_site_data.py`、`publish_finalization_site_data.py` | 網站資料 `docs/research/teacher_dashboard/data/redesign_20261116/` | `REDESIGN_SITE_MANIFEST.json` | — | — | — | `54f0282`、`647b5e9`、本輪 | — |

**Provenance 限制**：Gate 1–4 的 Manifest `git_commit` 欄位記錄的是執行當下的 HEAD（`87e31c4`／`4b35744`），當時 `fedrs/` 程式尚未提交，所以這個欄位**不能**精確指出產生資料的程式版本。程式後來在 `4b35744`／`89fd52b` 提交。Gate 5 的程式在執行前已提交（`e57e306`），Manifest 可以準確追溯。

## 3. 主要結論與證據等級
| 結論 | 等級 | 證據 |
|---|---|---|
| 單類別 Client → 空約簡 → TRUE→d 是數學必然 | 理論＋測試 | 報告 §0.1；`test_fedrs_units.py` |
| TRUE→d 造成大量 Coverage 與 Conflict（α=0.1） | Exploratory → Confirmatory 再現 | `G1_STRUCTURE_DECOMPOSITION.csv`；`G5_STRUCTURE.csv` |
| H1：M2 > M0（三個分布） | **Confirmatory PASS** | `G5_PRIMARY_HYPOTHESES.csv`；獨立重算；家族敏感度；post-hoc 來源敏感度 |
| H2：M1 > M0（α=0.1），效果小 | **Confirmatory PASS** | 同上 |
| M2 低於 R1（三個分布平均） | 次要描述性；只有 IID 兩種檢定都支持 | `G5_SECONDARY_DESCRIPTIVE.csv`；Corrected Interpretation |
| M2 低於集中式 CART；IID／α=0.5 低於聯邦 CART | 次要描述性 | 同上 |
| 衝突懲罰（FCP、LOCO 衝突項、FED_MD_XC）無效 | Negative Findings | Gate 4；Gate 5 M3 |
| 「切得越細衝突必然越多」不成立 | Exploratory（反例） | `G2_COUNTEREXAMPLES_FINER_VS_CONFLICT.csv` |
| 六策略在處理 TRUE 規則後差異很小 | Exploratory＋Confirmatory 描述性 | `G1_POLICY_SPREAD_FRIEDMAN.csv`、`G5_POLICY_FRIEDMAN.csv` |
| Classical 正域對標籤雜訊極敏感；VPRS 耐雜訊但增加衝突 | Exploratory | `G3_*` |
| 51 份來源中 ada、gina 很可能與歷史來源同源 | Open Limitation（metadata 層級） | `G5_SOURCE_METADATA_AUDIT_20261116.csv` |
