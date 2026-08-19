from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = PROJECT_ROOT / "history" / "source_registry" / "all_dynasties_sources.yaml"


def test_all_dynasties_source_registry_exists_and_extends_phase1() -> None:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    assert data["scope"] == "all_chinese_dynasties"
    histories = data["source_groups"]["core_dynastic_histories"]
    titles = {item["title"] for item in histories}

    required = {
        "史記",
        "漢書",
        "後漢書",
        "三國志",
        "晉書",
        "宋書",
        "南齊書",
        "梁書",
        "陳書",
        "魏書",
        "北齊書",
        "周書",
        "隋書",
        "南史",
        "北史",
        "舊唐書",
        "新唐書",
        "舊五代史",
        "新五代史",
        "宋史",
        "遼史",
        "金史",
        "元史",
        "明史",
    }
    assert required.issubset(titles)


def test_all_dynasties_registry_includes_governance_and_record_corpora() -> None:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    titles = {
        item["title"]
        for item in data["source_groups"]["chronological_and_governance_corpora"]
    }
    assert {"資治通鑑", "貞觀政要", "唐會要", "宋會要輯稿", "明實錄", "清實錄"}.issubset(titles)
