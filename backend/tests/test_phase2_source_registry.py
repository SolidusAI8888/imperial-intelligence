from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
PHASE2 = ROOT / "history" / "source_registry" / "phase2_core_histories.yaml"
ALL = ROOT / "history" / "source_registry" / "all_dynasties_sources.yaml"


def test_phase2_core_histories_registers_all_missing_dynastic_histories() -> None:
    phase2 = yaml.safe_load(PHASE2.read_text(encoding="utf-8"))
    sources = phase2["sources"]
    assert len(sources) == 18
    assert len({source["source_id"] for source in sources}) == 18
    assert all(source["volume_min"] == 1 for source in sources)
    assert all(source["volume_max"] >= source["volume_min"] for source in sources)
    assert {source["title"] for source in sources} == {
        "三國志", "晉書", "宋書", "南齊書", "梁書", "陳書", "魏書", "北齊書", "周書",
        "隋書", "南史", "北史", "舊五代史", "新五代史", "遼史", "金史", "元史", "明史",
    }


def test_phase2_ids_are_frozen_in_all_dynasties_registry() -> None:
    phase2 = yaml.safe_load(PHASE2.read_text(encoding="utf-8"))
    all_sources = yaml.safe_load(ALL.read_text(encoding="utf-8"))
    core = all_sources["source_groups"]["core_dynastic_histories"]
    global_ids = {item.get("source_id") for item in core if item.get("source_id")}
    assert {source["source_id"] for source in phase2["sources"]} == global_ids


def test_phase2_expected_volume_floor_is_large_enough_for_real_expansion() -> None:
    phase2 = yaml.safe_load(PHASE2.read_text(encoding="utf-8"))
    expected = sum(source["volume_max"] - source["volume_min"] + 1 for source in phase2["sources"])
    assert expected == 1942
