import importlib.util
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "history" / "source_registry" / "qing_persona_voice_sources.yaml"
POLICY = ROOT / "knowledge" / "research" / "qing_persona_source_policy.yaml"
ALL_SOURCES = ROOT / "history" / "source_registry" / "all_dynasties_sources.yaml"
SELECTOR = ROOT / "history" / "tools" / "select_next_qing_persona_voice_source.py"


def _selector_module():
    spec = importlib.util.spec_from_file_location("qing_voice_selector", SELECTOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_qing_voice_registry_has_stable_prioritized_source_ids() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    sources = data["sources"]
    assert [source["source_id"] for source in sources] == [
        "CN-QING-VOICE-0001",
        "CN-QING-VOICE-0002",
        "CN-QING-VOICE-0003",
        "CN-QING-VOICE-0004",
    ]
    assert sources[0]["title"] == "上諭檔"
    assert sources[1]["title"] == "朱批奏摺"
    assert sources[2]["title"] == "起居注"
    assert data["priority_order"][0] == "direct_imperial_words"


def test_discovered_voice_sources_are_not_falsely_marked_collectable_or_complete() -> None:
    sources = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["sources"]
    for source in sources:
        assert source["status"] != "ingested"
        assert "host" not in source
        assert "volume_min" not in source
        assert "volume_max" not in source
    assert [source["status"] for source in sources] == [
        "blocked_with_reason",
        "blocked_with_reason",
        "blocked_with_reason",
        "catalog_verified_access_review_required",
    ]
    for source in sources[:3]:
        assert source["holding_institution"] == "中国第一历史档案馆"
        assert source["provenance"]
        assert source["remaining_requirements"]
    assert sources[3]["discovered_scope"]["fonds"] == "军机处"
    assert sources[3]["discovered_scope"]["opened_archival_items_announced"] == 814000
    assert "series_partition_and_overlap_control" in sources[3]["remaining_requirements"]


def test_registry_matches_knowledge_policy_and_project_wide_registry() -> None:
    source_ids = {
        source["source_id"]
        for source in yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["sources"]
    }
    policy_ids = {
        source["source_id"]
        for group in yaml.safe_load(POLICY.read_text(encoding="utf-8"))["priority_order"]
        for source in group["sources"]
        if source["source_id"].startswith("CN-QING-VOICE-")
    }
    all_source_ids = {
        source["source_id"]
        for source in yaml.safe_load(ALL_SOURCES.read_text(encoding="utf-8"))[
            "source_groups"
        ]["persona_voice_primary_records"]
    }
    assert source_ids == policy_ids == all_source_ids


def test_selector_reports_discovery_as_pending_not_complete() -> None:
    module = _selector_module()
    result = module.status()
    assert result["total"] == 4
    assert result["complete"] == 0
    assert result["pending"] == 4
    assert result["blocked"] == 3
    assert result["discovery_required_source_ids"] == []
    assert result["access_review_required_source_ids"] == [
        "CN-QING-VOICE-0004",
    ]
    assert result["permission_required_source_ids"] == [
        "CN-QING-VOICE-0001",
        "CN-QING-VOICE-0002",
        "CN-QING-VOICE-0003",
    ]
    assert result["blocked_source_ids"] == [
        "CN-QING-VOICE-0001",
        "CN-QING-VOICE-0002",
        "CN-QING-VOICE-0003",
    ]
    assert result["next_source_id"] == "CN-QING-VOICE-0004"
    assert result["next_source_strategy"] == "archival_access_review_required"
    assert "never implies" in result["completion_warning"]
