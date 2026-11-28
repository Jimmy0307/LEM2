"""Build every table needed for the final LEM2 report (means only; read-only on all run directories).

Inputs (WSL):
  main     /home/user/lem2_runs/expanded_188_42seeds            (code 56e293c, 2,700 s per model)
  supp     /home/user/lem2_runs/expanded_accel_nolimit          (code 805ade0, no deadline; 6 heavy datasets)
  protocol /home/user/lem2_runs/protocol_compare_20261128       (code d24d1cc, 80/20 vs nested 80(64/16)/20)
Output: <out>/ (default D:/Desk/LEM2_expanded_resume/report_data) — CSV tables, compact model-level
        results (.csv.gz) and REPORT_DATA.md (Traditional Chinese, auto-generated).

Averaging (meeting decision #1: compare means only, no standard deviations): per (dataset, scenario,
rule variant, policy) average over seeds first, then average over datasets (each dataset weight 1).
Policy comparisons use only datasets complete in the lane being summarised, so every mean is paired.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

RUNS = Path("/home/user/lem2_runs")
LANES = {"main": RUNS / "expanded_188_42seeds", "supp": RUNS / "expanded_accel_nolimit",
         "protocol": RUNS / "protocol_compare_20261128"}
SCENARIOS = ("CENTRALIZED", "FED_IID", "FED_A05", "FED_A01")
SC_ZH = {"CENTRALIZED": "集中式", "FED_IID": "聯邦 IID", "FED_A05": "聯邦 α=0.5", "FED_A01": "聯邦 α=0.1"}
VARIANTS = ("A_ALL_RULES", "B2_TRUE_AS_FALLBACK")
VAR_ZH = {"A_ALL_RULES": "A（全部規則）", "B2_TRUE_AS_FALLBACK": "B2（TRUE 規則只當後備）"}
POLICIES = ("FIRST_MATCH", "SIMPLE_VOTING", "STANDARD_VOTING", "GLOBAL_STRENGTH", "POPULATION_STANDARD",
            "POPULATION_GLOBAL")
sys.path.insert(0, "/home/user/lem2_protocol")
try:
    from fedrs.experiment import POLICY_ORDER  # validation tie-break order used throughout the project
except Exception:  # pragma: no cover
    POLICY_ORDER = POLICIES


# ------------------------------------------------------------------ loading
def load_lane(root: Path, protocol: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, status = [], []
    for ds_dir in sorted((root / "checkpoints").iterdir()):
        if not ds_dir.is_dir():
            continue
        names = {p.name for p in ds_dir.iterdir()}
        ok = fail = 0
        for seed in range(1, 43):
            for sc in SCENARIOS:
                base = f"seed{seed:02d}__{sc}"
                if base + ".json" in names:
                    rec = json.loads((ds_dir / f"{base}.json").read_text())
                    ok += 1
                    for r in rec["rows"]:
                        keep = {k: r[k] for k in r if k in (
                            "dataset", "seed", "rule_variant", "selection_policy", "accuracy_pct",
                            "balanced_accuracy_pct", "rule_count", "train_rows", "protocol", "split",
                            "test_coverage_pct", "coverage_pct", "candidate_coverage_pct", "conflict_rate_pct")}
                        keep["scenario"] = sc
                        rows.append(keep)
                elif base + ".failure.json" in names:
                    fail += 1
        if ok or fail:
            status.append({"dataset_dir": ds_dir.name, "ok": ok, "failed": fail, "decided": ok + fail})
    df = pd.DataFrame(rows)
    if not protocol and len(df):
        df = df.rename(columns={"test_coverage_pct": "coverage_pct"})
    return df, pd.DataFrame(status)


def complete_datasets(status: pd.DataFrame, require_all_ok: bool) -> set:
    full = status[status.decided == 168]
    if require_all_ok:
        full = full[full.ok == 168]
    return set(full.dataset_dir.str.replace("__", ":", n=1))


def dataset_mean(df: pd.DataFrame, keys: list, metrics: list) -> pd.DataFrame:
    """seed-average within dataset, then dataset-average (equal weight per dataset)."""
    per_ds = df.groupby(["dataset", *keys], observed=True)[metrics].mean().reset_index()
    out = per_ds.groupby(keys, observed=True)[metrics].mean().reset_index()
    out.insert(len(keys), "datasets", per_ds.groupby(keys, observed=True).dataset.nunique().values)
    return out


# --------------------------------------------------------------- summaries
def policy_table(df: pd.DataFrame) -> pd.DataFrame:
    return dataset_mean(df, ["scenario", "rule_variant", "selection_policy"],
                        ["accuracy_pct", "balanced_accuracy_pct"])


def structure_table(df: pd.DataFrame) -> pd.DataFrame:
    one = df[df.selection_policy == POLICIES[0]]  # structure columns do not depend on the policy
    return dataset_mean(one, ["scenario", "rule_variant"],
                        ["coverage_pct", "candidate_coverage_pct", "conflict_rate_pct", "rule_count"])


def spread_table(df: pd.DataFrame) -> pd.DataFrame:
    per_model = df.groupby(["dataset", "seed", "scenario", "rule_variant"]).accuracy_pct.agg(["max", "min"])
    per_model["policy_spread_pp"] = per_model["max"] - per_model["min"]
    conflict = df[df.selection_policy == POLICIES[0]].set_index(["dataset", "seed", "scenario", "rule_variant"]).conflict_rate_pct
    per_model = per_model.join(conflict).reset_index()
    per_model["spread_zero"] = (per_model.policy_spread_pp < 1e-9).astype(float) * 100
    return dataset_mean(per_model, ["scenario", "rule_variant"], ["policy_spread_pp", "conflict_rate_pct", "spread_zero"])


def central_vs_fed(df: pd.DataFrame) -> pd.DataFrame:
    piv = df.pivot_table(index=["dataset", "seed", "rule_variant", "selection_policy"], columns="scenario",
                         values="accuracy_pct")
    rows = []
    for sc in SCENARIOS[1:]:
        if sc in piv and "CENTRALIZED" in piv:
            d = (piv[sc] - piv["CENTRALIZED"]).rename("delta_acc_pp").reset_index().dropna()
            d["scenario"] = sc
            rows.append(d)
    if not rows:
        return pd.DataFrame()
    d = pd.concat(rows)
    return dataset_mean(d, ["scenario", "rule_variant", "selection_policy"], ["delta_acc_pp"])


def protocol_tables(p: pd.DataFrame) -> dict:
    """80/20 holdout vs nested 80(64/16)/20, paired on the same outer test split."""
    key = ["dataset", "seed", "scenario", "rule_variant"]
    test_n = p[(p.protocol == "NESTED_64_16_20") & (p.split == "test")]
    val_n = p[(p.protocol == "NESTED_64_16_20") & (p.split == "val")]
    test_h = p[(p.protocol == "HOLDOUT_80_20") & (p.split == "test")]
    out = {}
    # fixed-policy test means under each protocol
    both = pd.concat([test_h.assign(proto="HOLDOUT_80_20"), test_n.assign(proto="NESTED_64_16_20")])
    out["fixed_policy"] = dataset_mean(both, ["proto", "scenario", "rule_variant", "selection_policy"],
                                       ["accuracy_pct", "balanced_accuracy_pct"])
    # validation selection (primary: accuracy; secondary: balanced accuracy), tie order = POLICY_ORDER
    order = {p_: i for i, p_ in enumerate(POLICY_ORDER)}
    sel_rows = []
    vt = val_n.merge(test_n, on=key + ["selection_policy"], suffixes=("_val", "_test"))
    ht = test_h.set_index(key + ["selection_policy"])
    for crit in ("accuracy_pct", "balanced_accuracy_pct"):
        tmp = vt.assign(_ord=vt.selection_policy.map(order))
        tmp = tmp.sort_values(key + [f"{crit}_val", "_ord"], ascending=[True] * len(key) + [False, True])
        chosen = tmp.groupby(key, sort=False).head(1).set_index(key)
        best_test = vt.groupby(key)[f"{crit}_test"].max()
        best_hold = test_h.groupby(key)[crit].max()
        frame = pd.DataFrame({
            "selected_policy": chosen.selection_policy,
            "nested_selected_test": chosen[f"{crit}_test"],
            "nested_oracle_test": best_test,
            "holdout_oracle_test": best_hold,
        }).dropna(subset=["nested_selected_test"])
        frame["selected_is_best"] = (frame.nested_selected_test >= frame.nested_oracle_test - 1e-9).astype(float) * 100
        hold_same = []
        for idx, pol in frame.selected_policy.items():
            try:
                hold_same.append(ht.loc[(*idx, pol), crit])
            except KeyError:
                hold_same.append(np.nan)
        frame["holdout_same_policy_test"] = hold_same
        frame = frame.reset_index()
        frame["criterion"] = crit
        sel_rows.append(frame)
    sel = pd.concat(sel_rows)
    out["selection_models"] = sel
    out["selection"] = dataset_mean(sel, ["criterion", "scenario", "rule_variant"],
                                    ["nested_selected_test", "nested_oracle_test", "holdout_same_policy_test",
                                     "holdout_oracle_test", "selected_is_best"])
    counts = sel.groupby(["criterion", "scenario", "rule_variant", "selected_policy"]).size().rename("models").reset_index()
    counts["share_pct"] = 100 * counts.models / counts.groupby(["criterion", "scenario", "rule_variant"]).models.transform("sum")
    out["selection_counts"] = counts
    # extra 20 % training data: HOLDOUT minus NESTED, same policy, same test rows
    m = test_h.merge(test_n, on=key + ["selection_policy"], suffixes=("_h", "_n"))
    m["delta_acc_pp"] = m.accuracy_pct_h - m.accuracy_pct_n
    m["delta_ba_pp"] = m.balanced_accuracy_pct_h - m.balanced_accuracy_pct_n
    m["delta_rules"] = m.rule_count_h - m.rule_count_n
    out["holdout_minus_nested"] = dataset_mean(m, ["scenario", "rule_variant", "selection_policy"],
                                               ["delta_acc_pp", "delta_ba_pp", "delta_rules"])
    return out


# ------------------------------------------------------------------- render
def md_table(df: pd.DataFrame, cols: list, headers: list, fmt: dict | None = None) -> str:
    fmt = fmt or {}
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" if i == 0 else "---:" for i in range(len(headers))) + "|"]
    for r in df.itertuples(index=False):
        vals = []
        for c in cols:
            v = getattr(r, c)
            if isinstance(v, (float, np.floating)):
                vals.append(fmt.get(c, "{:.2f}").format(v))
            else:
                vals.append(SC_ZH.get(v, VAR_ZH.get(v, str(v))))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def wide_policy(tab: pd.DataFrame, value: str) -> pd.DataFrame:
    w = tab.pivot_table(index=["scenario", "rule_variant"], columns="selection_policy", values=value).reset_index()
    w["scenario"] = pd.Categorical(w.scenario, SCENARIOS, ordered=True)
    return w.sort_values(["rule_variant", "scenario"])[["scenario", "rule_variant", *[p for p in POLICIES if p in w]]]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="/mnt/d/Desk/LEM2_expanded_resume/report_data")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    main_df, main_st = load_lane(LANES["main"])
    supp_df, supp_st = load_lane(LANES["supp"])
    prot_df, prot_st = load_lane(LANES["protocol"], protocol=True)
    for name, st in (("main", main_st), ("supp", supp_st), ("protocol", prot_st)):
        st.to_csv(out / f"COMPLETENESS_{name}.csv", index=False)

    main_full = complete_datasets(main_st, require_all_ok=True)          # 180: no timeout at 2,700 s
    supp_full = complete_datasets(supp_st, require_all_ok=True)          # heavy datasets finished without deadline
    prot_full = complete_datasets(prot_st, require_all_ok=True) if len(prot_st) else set()
    m = main_df[main_df.dataset.isin(main_full)]
    combined = pd.concat([m, supp_df[supp_df.dataset.isin(supp_full - main_full)]])

    tables = {
        "T1_main_policy_means": policy_table(m),
        "T2_main_structure_means": structure_table(m),
        "T3_main_policy_spread": spread_table(m),
        "T4_main_central_vs_federated": central_vs_fed(m),
        "T5_combined_policy_means": policy_table(combined),
        "T6_supp_policy_means": policy_table(supp_df[supp_df.dataset.isin(supp_full)]) if len(supp_df) else pd.DataFrame(),
    }
    prot = {}
    if len(prot_df):
        p = prot_df[prot_df.dataset.isin(prot_full)] if prot_full else prot_df.iloc[0:0]
        if len(p):
            prot = protocol_tables(p)
            for k, v in prot.items():
                if k != "selection_models":
                    tables[f"P_{k}"] = v
    for k, v in tables.items():
        if len(v):
            v.to_csv(out / f"{k}.csv", index=False)
    with gzip.open(out / "MODEL_RESULTS_main_complete.csv.gz", "wt") as fh:
        m.to_csv(fh, index=False)
    if len(prot_df):
        with gzip.open(out / "MODEL_RESULTS_protocol.csv.gz", "wt") as fh:
            prot_df.to_csv(fh, index=False)
        if "selection_models" in prot:
            with gzip.open(out / "MODEL_SELECTION_protocol.csv.gz", "wt") as fh:
                prot["selection_models"].to_csv(fh, index=False)

    # ---------------------------------------------------------------- markdown
    now = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    n_main_ds, n_prot_ds = len(main_full), len(prot_full)
    L = [f"# LEM2 研究報告資料（自動產生）\n\n產生時間：{now}。本檔由 `tools/expanded_resume_20261122/report_data.py` 依各實驗的檢查點自動產生，**只列平均值**（會議決議 #1）：每份資料先對 Seed 平均，再對資料集平均（每份資料權重相同）；同一張表的方法都使用同一批資料與同一批模型（配對比較）。\n",
         "## 0. 資料與完成度",
         md_table(pd.DataFrame([
             {"lane": "主實驗（56e293c，每模型 2,700 秒）", "ds": int((main_st.decided == 168).sum()), "full": n_main_ds,
              "ok": int(main_st.ok.sum()), "fail": int(main_st.failed.sum())},
             {"lane": "補跑（805ade0，不設時限）", "ds": int((supp_st.decided == 168).sum()) if len(supp_st) else 0,
              "full": len(supp_full), "ok": int(supp_st.ok.sum()) if len(supp_st) else 0, "fail": int(supp_st.failed.sum()) if len(supp_st) else 0},
             {"lane": "#4 協定比較（d24d1cc）", "ds": int((prot_st.decided == 168).sum()) if len(prot_st) else 0,
              "full": n_prot_ds, "ok": int(prot_st.ok.sum()) if len(prot_st) else 0, "fail": int(prot_st.failed.sum()) if len(prot_st) else 0},
         ]), ["lane", "ds", "full", "ok", "fail"],
             ["實驗", "168 個模型都有結果的資料數", "其中全部成功的資料數", "成功模型", "失敗／逾時模型"],
             {"ds": "{:.0f}", "full": "{:.0f}", "ok": "{:.0f}", "fail": "{:.0f}"}),
         "\n`openml_1169`、`openml_42732` 在此機器上無法完成（見 `status_20261128/`），不納入任何平均。\n"]
    for title, key, value, note in (
            ("1. 主實驗：六種策略的平均準確率（Accuracy %）", "T1_main_policy_means", "accuracy_pct",
             f"資料：主實驗中 168 個模型全部成功的 {n_main_ds} 份資料。"),
            ("2. 主實驗：六種策略的平均 Balanced Accuracy（%）", "T1_main_policy_means", "balanced_accuracy_pct", "")):
        t = tables[key]
        if len(t):
            w = wide_policy(t, value)
            L += [f"## {title}", note, md_table(w, list(w.columns), ["情境", "規則版本", *list(w.columns[2:])])]
    t = tables["T2_main_structure_means"]
    if len(t):
        t = t.assign(scenario=pd.Categorical(t.scenario, SCENARIOS, ordered=True)).sort_values(["rule_variant", "scenario"])
        L += ["## 3. 主實驗：規則覆蓋與衝突（平均）",
              md_table(t, ["scenario", "rule_variant", "coverage_pct", "candidate_coverage_pct", "conflict_rate_pct", "rule_count"],
                       ["情境", "規則版本", "測試覆蓋率 %", "正確類別在候選中 %", "衝突率 %", "規則數"], {"rule_count": "{:.0f}"})]
    t = tables["T3_main_policy_spread"]
    if len(t):
        t = t.assign(scenario=pd.Categorical(t.scenario, SCENARIOS, ordered=True)).sort_values(["rule_variant", "scenario"])
        L += ["## 4. 為什麼六種策略差不多",
              "策略只在「命中多個不同類別規則」的衝突列上才可能給出不同答案。下表是每個模型「六策略最高與最低準確率的差」的平均，以及六策略完全相同的模型比例。",
              md_table(t, ["scenario", "rule_variant", "policy_spread_pp", "conflict_rate_pct", "spread_zero"],
                       ["情境", "規則版本", "六策略差距（百分點）", "衝突率 %", "六策略完全相同的模型 %"])]
    t = tables["T4_main_central_vs_federated"]
    if len(t):
        w = t.pivot_table(index=["scenario", "rule_variant"], columns="selection_policy", values="delta_acc_pp").reset_index()
        w["scenario"] = pd.Categorical(w.scenario, SCENARIOS, ordered=True)
        w = w.sort_values(["rule_variant", "scenario"])[["scenario", "rule_variant", *[p for p in POLICIES if p in w]]]
        L += ["## 5. 集中式 vs 聯邦：準確率差（聯邦 − 集中式，百分點）", md_table(w, list(w.columns), ["情境", "規則版本", *list(w.columns[2:])])]
    t = tables["T6_supp_policy_means"]
    if len(t):
        w = wide_policy(t, "accuracy_pct")
        L += ["## 6. 補跑（不設時限）的 6 份重型資料：平均準確率（%）",
              "合約不同（加速程式、無時限），與主實驗分開陳述；預測結果與原始程式逐值相同（見 `accel_supplementary/`）。",
              md_table(w, list(w.columns), ["情境", "規則版本", *list(w.columns[2:])])]
    if prot:
        s = prot["selection"].assign(scenario=lambda d: pd.Categorical(d.scenario, SCENARIOS, ordered=True)).sort_values(["criterion", "rule_variant", "scenario"])
        L += [f"## 7. #4 協定比較：80/20 vs 80(60/20)/20（{n_prot_ds} 份資料，同一個外層 20% 測試集）",
              "- 80(60/20)/20：用 64% 學規則，在 16% 驗證集上選出準確率最高的策略（平手依專案固定順序），再看它在測試集的表現。\n- 80/20：用整個 80% 學規則。\n- 「最佳（事後）」是直接看測試集挑最好的策略，只當上限參考，實務上不可得。",
              "### 7.1 以驗證集「準確率」選策略（主要）"]
        s1 = s[s.criterion == "accuracy_pct"]
        L.append(md_table(s1, ["scenario", "rule_variant", "nested_selected_test", "nested_oracle_test", "holdout_same_policy_test",
                               "holdout_oracle_test", "selected_is_best"],
                          ["情境", "規則版本", "巢狀：驗證選出的策略（測試準確率）", "巢狀：最佳（事後）", "80/20：同一策略", "80/20：最佳（事後）", "驗證選中最佳的比例 %"]))
        s2 = s[s.criterion == "balanced_accuracy_pct"]
        L += ["### 7.2 以驗證集「Balanced Accuracy」選策略（次要）",
              md_table(s2, ["scenario", "rule_variant", "nested_selected_test", "nested_oracle_test", "holdout_same_policy_test",
                            "holdout_oracle_test", "selected_is_best"],
                       ["情境", "規則版本", "巢狀：驗證選出（測試 BA）", "巢狀：最佳（事後）", "80/20：同一策略", "80/20：最佳（事後）", "驗證選中最佳的比例 %"])]
        f = prot["fixed_policy"]
        for proto, zh in (("HOLDOUT_80_20", "80/20"), ("NESTED_64_16_20", "80(60/20)/20")):
            w = wide_policy(f[f.proto == proto], "accuracy_pct")
            L += [f"### 7.3 固定策略的平均測試準確率：{zh}", md_table(w, list(w.columns), ["情境", "規則版本", *list(w.columns[2:])])]
        d = prot["holdout_minus_nested"]
        w = d.pivot_table(index=["scenario", "rule_variant"], columns="selection_policy", values="delta_acc_pp").reset_index()
        w["scenario"] = pd.Categorical(w.scenario, SCENARIOS, ordered=True)
        w = w.sort_values(["rule_variant", "scenario"])[["scenario", "rule_variant", *[p for p in POLICIES if p in w]]]
        L += ["### 7.4 多用 20% 資料學規則的效果（80/20 − 巢狀，同一策略，百分點）", md_table(w, list(w.columns), ["情境", "規則版本", *list(w.columns[2:])])]
        c = prot["selection_counts"]
        c = c[c.criterion == "accuracy_pct"].pivot_table(index=["scenario", "rule_variant"], columns="selected_policy", values="share_pct", fill_value=0).reset_index()
        c["scenario"] = pd.Categorical(c.scenario, SCENARIOS, ordered=True)
        c = c.sort_values(["rule_variant", "scenario"])
        L += ["### 7.5 驗證集選出各策略的比例（%，依模型計）", md_table(c, list(c.columns), ["情境", "規則版本", *list(c.columns[2:])])]
    elif len(prot_df):
        L += ["## 7. #4 協定比較", f"尚未有任何資料完成全部 168 個模型（目前已完成 {int(prot_st.ok.sum())} 個模型）。"]
    L += ["## 8. 檔案",
          "- 各表 CSV：`T*.csv`（主實驗／補跑）、`P_*.csv`（#4 協定比較）；完成度：`COMPLETENESS_*.csv`。",
          "- 模型層級資料：`MODEL_RESULTS_main_complete.csv.gz`、`MODEL_RESULTS_protocol.csv.gz`、`MODEL_SELECTION_protocol.csv.gz`。",
          "- 限制與無法完成的資料：`../status_20261128/`；記憶體與資料大小：`../memory_analysis/`；加速與補跑：`../accel_supplementary/`。"]
    (out / "REPORT_DATA.md").write_text("\n\n".join(L) + "\n", encoding="utf-8")
    print(f"main complete datasets={n_main_ds} supp={len(supp_full)} protocol complete={n_prot_ds} -> {out}")


if __name__ == "__main__":
    main()
