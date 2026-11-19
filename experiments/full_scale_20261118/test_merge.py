import pandas as pd
import pytest
from experiments.full_scale_20261118.merge_shard import coalesce_metadata


def test_source_metadata_across_scenarios_must_have_identical_hashes():
    entries = pd.DataFrame([{"dataset": "A", "raw_sha256": "raw", "prepared_sha256": "prepared", "used_rows": 20},
                            {"dataset": "A", "raw_sha256": "raw", "prepared_sha256": "prepared", "used_rows": 20}])
    assert len(coalesce_metadata(entries)) == 1
    entries.loc[1, "raw_sha256"] = "different"
    with pytest.raises(ValueError, match="SOURCE_METADATA_MISMATCH"):
        coalesce_metadata(entries)
