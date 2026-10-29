from pathlib import Path
import importlib.util
import pandas as pd

BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("demo", BASE / "lem2_metric_and_selection_demo.py")
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)


def test_three_dataset_means_match_expected_values():
    df = pd.read_csv(BASE / "CENTRALIZED_VS_FEDERATED.csv")
    out = demo.compute_three_dataset_means(df).set_index("policy")
    expected = {
        "FIRST": (79.56, 64.55, 65.99),
        "SIMPLE": (78.18, 62.69, 64.30),
        "STD": (80.93, 66.46, 67.13),
        "GS": (80.65, 66.75, 66.82),
        "PS": (80.93, 66.46, 67.13),
        "PG": (80.65, 66.75, 66.82),
    }
    for policy, values in expected.items():
        got = tuple(round(float(out.loc[policy, c]), 2) for c in demo.METRIC_COLS)
        assert got == values


def test_overall_descriptive_mean_matches_expected_values():
    df = pd.read_csv(BASE / "CENTRALIZED_VS_FEDERATED.csv")
    got = demo.overall_descriptive_mean(df)
    assert round(float(got["central_accuracy"]), 2) == 80.15
    assert round(float(got["central_balanced_accuracy"]), 2) == 65.61
    assert round(float(got["central_macro_f1"]), 2) == 66.37
