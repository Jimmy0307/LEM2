from experiments.full_scale_20261118.registry import source_registry, assign_shards
from experiments.full_scale_20261118.workflow_matrix import build_matrices


def test_registry_retains_duplicates_but_excludes_them_from_execution():
    registry = source_registry()
    pmlb = registry.set_index("dataset").loc["PMLB:iris"]
    assert pmlb.same_source_as == "UCI20:iris"
    assert pmlb.status == "EXCLUDED_SAME_SOURCE"
    assert registry.set_index("dataset").loc["PMLB:glass2"].related_source == "EXT7:glass"
    assert registry[registry.status == "PENDING"].dataset.nunique() >= 100


def test_largest_sources_get_separate_shards_and_assignment_is_stable():
    registry = source_registry()
    assigned = assign_shards(registry, 24)
    eligible = assigned[assigned.status == "PENDING"]
    largest = eligible.sort_values(["original_rows", "dataset"], ascending=[False, True]).head(10)
    for row in largest.itertuples():
        assert (eligible.shard == row.shard).sum() == 1
    assert assign_shards(registry.sample(frac=1, random_state=1), 24).set_index("dataset").shard.to_dict() == assigned.set_index("dataset").shard.to_dict()


def test_workflow_matrix_has_one_dataset_entry_and_a_job_for_every_shard():
    datasets, shards = build_matrices(24)
    assert len(datasets["include"]) == 188
    assert len({x["dataset"] for x in datasets["include"]}) == 188
    assert len({x["token"] for x in datasets["include"]}) == 188
    assert shards["shard"] == list(range(24))
