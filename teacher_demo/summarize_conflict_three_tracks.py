"""No-imputation aggregation of 3 independent rule-level studies from 6 actual sources."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
FOLDER=Path("three_tracks_incoming")
OUT=Path("docs/research/teacher_dashboard/three_tracks")
KEYS={"letter":"A","wine":"B","grid_stability":"B",
      "haberman":"C","banknote":"C","rice":"C"}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cols={"A_LETTER_PER_CLASS":"TRACK_A_LETTER_PER_CLASS.csv",
          "A_LETTER_OBJECT_RECAP":"TRACK_A_LETTER_OBJECT_CASES.csv",
          "A_LETTER_RULE_AUDIT":"TRACK_A_LETTER_INDUCED_RULES.csv",
          "B_CONFLICT_AWARE_TRAIN_ONLY_PRUNE":"TRACK_B_WINE_GRID_PRUNING.csv",
          "C_SAFE_TRAIN_ONLY_SUPPLEMENT":"TRACK_C_SAFE_SUPPLEMENT_SUMMARY.csv",
          "C_MARGINAL_RULE_ADD":"TRACK_C_RULE_BY_RULE_MARGINAL.csv"}
    entries=[];groups={k:[] for k in cols}
    for key,track in KEYS.items():
        receipt=FOLDER/f"TRACK_{track}_{key}.json"
        result=FOLDER/f"TRACK_{track}_{key}.csv"
        if not receipt.is_file() or not result.is_file():
            raise AssertionError(f"Missing entire measured result {key}: {receipt}")
        p=json.loads(receipt.read_text())
        f=pd.read_csv(result,low_memory=False)
        assert p["dataset"]==key and p["track"]==track and p["seed"]==42
        assert p["row_count"]==len(f) and len(f)>0
        assert set(f["dataset"])=={key} and set(f.seed)=={42}
        assert set(f.client_count)=={0,3}
        entries.append(p)
        for label,block in f.groupby("track"):
            if label not in groups:raise AssertionError("Unexpected track "+label)
            groups[label].append(block.copy())
    counts={}
    for k,ls in groups.items():
        if not ls:raise AssertionError("Missing evidence "+k)
        frame=pd.concat(ls,ignore_index=True).dropna(axis=1,how="all")
        frame.to_csv(OUT/cols[k],index=False,float_format="%.10f")
        counts[k]=len(frame)
    a=pd.concat(groups["A_LETTER_PER_CLASS"],ignore_index=True)
    assert len(a)==52 and a.groupby("client_count").size().eq(26).all()
    assert a.groupby("client_count").objects.sum().nunique()==1
    for cli,group in a.groupby("client_count"):
        assert group.class_rules.ge(0).all()
    b=pd.concat(groups["B_CONFLICT_AWARE_TRAIN_ONLY_PRUNE"],ignore_index=True)
    assert len(b)==4
    assert (b.rules_removed>=0).all()
    assert (b.remaining_rules==b.original_rule_count-b.rules_removed).all()
    c=pd.concat(groups["C_SAFE_TRAIN_ONLY_SUPPLEMENT"],ignore_index=True)
    assert len(c)==6 and (c.accepted_supplements<=c.threshold_passed_candidates).all()
    assert (c.test_new_coverage_pct>=c.test_orig_coverage_pct-1e-8).all()
    assert (c.test_new_conflict_pct>=c.test_orig_conflict_pct-1e-8).all()
    man={
      "status":"SIX_REAL_DATASET_RULE_LEVEL_TRACKS_PASS",
      "seed":[42],"dataset_count":6,"tracks":{
        "A":{"dataset":"letter","class_count":26,"purpose":"Per-class exact matched/candidate/conflict and rule antecedent audit"},
        "B":{"datasets":["wine","grid_stability"],"purpose":"Greedy removal based only on in-sample TRAIN conflict/candidate; TEST remains untouched",
             "warning":"Train-only IN-SAMPLE pruning on model's training data, not out-of-sample internal validation"},
        "C":{"datasets":["haberman","banknote","rice"],"purpose":"Sequential marginal added coverage versus added conflict and correct candidate on TRAIN",
             "warning":"Structural union and fallback-only supplementation are distinct; report both"}},
      "dataset_receipts":entries,"output_row_counts":counts,
      "base_method":"Classical positive-region reduct+LEM2, C0/C3, seed42, 80/20 holdout",
      "stopping_condition":"No dataset imputed or omitted; original rule count/cov/conf/candidate matched saved PUBLIC20 baselines",
      "caveats":["Not multiple seeds", "No nested validation", "No DRSA or VC-DomLEM implementation", "Rules reused for diagnostics only; never tuned from TEST"]}
    (OUT/"MANIFEST.json").write_text(json.dumps(man,indent=2,ensure_ascii=False),encoding="utf-8")
    markdown=[
      "# 三條規則層級研究線：實驗證據與限制","",
      "來源：六份已發布公開資料子集；所有模型使用既有 Classical 約簡＋LEM2，Seed 42。獨立 C0/C3 規則集。",
      "所有改動的決策都只參照 Train；最後 Test 只計算結果。這仍是單一 Seed 的探索性實驗。","",
      "## Track A｜Letter：26 類候選與衝突分解",
      f"- 逐類別樣本／命中／正確候選率：[資料表]({cols['A_LETTER_PER_CLASS']})",
      f"- 逐測試物件是否真正命中正確決策：[資料表]({cols['A_LETTER_OBJECT_RECAP']})",
      f"- 逐條規則前件、訓練支持度、純度與測試命中：[資料表]({cols['A_LETTER_RULE_AUDIT']})","",
      "## Track B｜Wine／Grid：Train-only Conflict-Aware Pruning",
      f"- [規則修剪前後的 Train/Test Coverage、Conflict、正確候選與 BA]({cols['B_CONFLICT_AWARE_TRAIN_ONLY_PRUNE']})",
      "- 固定訓練集評分 = 正確候選率 − 0.70×衝突率 − 0.10×No Match 率；規則刪除以 Train 內的分布判斷，不以 Test 調參。",
      "- 注意：現有規則是在整個 Train 上歸納，所以這不是獨立內部驗證；下一步需 Nested Train/Validation，不能用它宣稱泛化最佳。","",
      "## Track C｜Haberman／Banknote／Rice：逐條新增規則的邊際效益",
      f"- [每一條候選補充規則的邊際 Coverage／Conflict／Candidate 與 Train-only Gate 結果]({cols['C_MARGINAL_RULE_ADD']})",
      f"- [安全選入後 Train/Test 結果與回退分類影響]({cols['C_SAFE_TRAIN_ONLY_SUPPLEMENT']})",
      "- 保留 Structural Union 與 No-Match fallback-only 兩種處理的不同定義；不將它們混稱為相同 Coverage。","",
      "## 解讀前必讀",
      "- 凍結基線：[`PUBLIC20_BASE_RESULTS.csv`](../data/PUBLIC20_BASE_RESULTS.csv)。",
      "- 方法使用同一 Seed 42；尚無 42 Seeds 的統計有效性。",
      "- 不保證 Conflict-Aware 剪枝一定優於原始 LEM2；負面或零效益一樣會儲存。",
      "- 這些模型不是原典 MLEM2 補充規則或 VC-DomLEM。",
      "- [本批可重現實驗 manifest](MANIFEST.json)。"]
    (OUT/"README.md").write_text("\n".join(markdown)+"\n",encoding="utf-8")
    print("THREE_TRACKS_SIX_DATASETS_PASS",counts,flush=True)
if __name__=="__main__":main()
