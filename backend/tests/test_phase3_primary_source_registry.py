from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "history" / "source_registry" / "phase3_primary_sources.yaml"
ALL_SOURCES = ROOT / "history" / "source_registry" / "all_dynasties_sources.yaml"


def test_phase3_registry_prioritizes_qing_primary_sources():
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    assert data["priority_order"][0] == "qing_core"
    sources = data["sources"]
    assert sources[0]["source_id"] == "CN-QING-0001"
    assert sources[0]["title"] == "清實錄"
    assert sources[0]["evidence_tier"] == "primary_imperial_record"
    assert sources[1]["source_id"] == "CN-QING-0002"
    assert sources[1]["title"] == "大清會典"


def test_phase3_ids_are_unique_and_registered_project_wide():
    phase3 = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["sources"]
    ids = [source["source_id"] for source in phase3]
    assert len(ids) == len(set(ids))

    all_sources_text = ALL_SOURCES.read_text(encoding="utf-8")
    for source_id in ids:
        assert source_id in all_sources_text


def test_numbered_volume_sources_have_complete_extractor_fields():
    sources = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["sources"]
    numbered = [source for source in sources if source["acquisition_strategy"] == "wikisource_numbered_volumes"]
    assert {source["source_id"] for source in numbered} == {
        "CN-TONGJIAN-0001",
        "CN-TANG-0005",
        "CN-WUDAI-0003",
        "CN-TONGKAO-0001",
    }
    for source in numbered:
        assert source["root_page"]
        assert source["dynasty_group"]
        assert source["corpus_key"]
        assert source["volume_min"] == 1
        assert source["volume_max"] >= source["volume_min"]
        assert source["status"] == "ready_for_ingestion"


def test_catalog_required_sources_are_not_falsely_marked_ingested():
    sources = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["sources"]
    catalog = [source for source in sources if source["acquisition_strategy"] == "catalog_required"]
    assert catalog
    assert all(source["status"] == "pending_catalog_resolution" for source in catalog)
