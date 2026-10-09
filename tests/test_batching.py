from mockgen import state
from conftest import entry, save_entries


def test_tail_fills_across_firms_without_crossing_tier_or_dependencies(repo):
    save_entries(repo, [
        entry("A-001"), entry("A-002"), entry("B-001", unit="B"),
        entry("C-001", unit="C", doc_type="word_memo"),
        entry("B-002", unit="B", related=[{"id": "B-001", "rel": "copy_of"}]),
        entry("A-003", tier="sol"),
    ])
    batch = state.next_batch("haiku", None, None, 6, "test")
    assert set(batch["files"]) == {"A-001", "A-002", "B-001", "C-001"}
    assert batch["unit"] == "mixed"
    assert state.next_batch("haiku", None, None, 6, "other")["files"] == []


def test_scientific_workbooks_and_project_copies_use_stronger_tier(repo):
    save_entries(repo, [
        entry("A-001", doc_type="wb_results"),
        entry("A-002", projects=["PRJ0001"]),
        entry("A-003", tier="haiku_low", doc_type="wb_results"),
        entry("A-004"),
    ])
    assert state.next_batch("haiku", None, None, 6, "test")["files"] == ["A-004"]
    assert set(state.next_batch("sol", None, None, 6, "test")["files"]) == {"A-001", "A-002", "A-003"}


def test_failed_pilot_promotion_moves_remaining_bounded_admin_to_stronger_tier(repo):
    import yaml
    save_entries(repo, [entry("A-001")])
    config = repo / "config/models.yaml"
    data = yaml.safe_load(config.read_text())
    data["writer_policy"]["promoted_tiers"] = ["haiku"]
    config.write_text(yaml.safe_dump(data))
    assert state.next_batch("haiku", None, None, 6, "test")["files"] == []
    assert state.next_batch("sol", None, None, 6, "test")["files"] == ["A-001"]


def test_tail_respects_explicit_firm_and_type_filters(repo):
    save_entries(repo, [entry("A-001"), entry("A-002", doc_type="word_memo"), entry("B-001", unit="B")])
    assert state.next_batch("haiku", "A", "wb_tracker", 6, "test")["files"] == ["A-001"]


def test_large_pool_keeps_batches_within_a_firm_and_type(repo):
    save_entries(repo, [entry(f"{unit}-{i:03d}", unit=unit) for unit in "ABCDEFG" for i in range(7)])
    batch = state.next_batch("haiku", None, None, 8, "test")
    assert len(batch["files"]) == 7
    assert {i.split("-")[0] for i in batch["files"]} == {batch["unit"]}
