from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "history" / "source_registry" / "phase3_catalog_sources.yaml"
SCRIPT = ROOT / "history" / "tools" / "ingest_wikisource_catalog.py"


def _load_script():
    tools = str(SCRIPT.parent)
    if tools not in sys.path:
        sys.path.insert(0, tools)
    spec = spec_from_file_location("ingest_wikisource_catalog", SCRIPT)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_qing_shilu_catalog_is_explicitly_partial_and_has_reign_children():
    source = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))["sources"][0]
    assert source["source_id"] == "CN-QING-0001"
    assert source["root_page"] == "清實錄"
    assert source["host_completeness"] == "explicitly_incomplete"
    assert source["completion_semantics"]["current_expected_result"] == "partial_host_archive"
    titles = [item["title"] for item in source["child_works"]]
    assert len(titles) == 13
    assert titles[0] == "滿洲實錄"
    assert titles[-1] == "宣統政紀"
    assert "聖祖仁皇帝實錄" in titles
    assert "世宗憲皇帝實錄" in titles
    assert "高宗純皇帝實錄" in titles


def test_ming_shilu_catalog_keeps_luwai_supplements_separate():
    source = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))["sources"][1]
    assert source["source_id"] == "CN-MING-0002"
    assert source["root_page"] == "明實錄"
    assert source["host_completeness"] == "explicitly_incomplete"
    titles = [item["title"] for item in source["child_works"]]
    assert len(titles) == 13
    assert titles[0] == "太祖高皇帝實錄"
    assert titles[-1] == "熹宗悊皇帝實錄"
    assert set(source["excluded_supplemental_works"]) == {"崇禎長編", "弘光實錄鈔", "永曆實錄"}
    assert not set(source["excluded_supplemental_works"]) & set(titles)
    host_titles = [item["host_title"] for item in source["child_works"]]
    assert all(title.startswith("明實錄/") for title in host_titles)
    assert "明實錄/成祖文皇帝實錄" in host_titles
    assert "明實錄/大明純皇帝實錄" in host_titles


def test_catalog_volume_parser_accepts_nested_shilu_titles():
    module = _load_script()
    assert module._volume_number("聖祖仁皇帝實錄/卷123") == (123, "")
    assert module._volume_number("某實錄/第一部/卷004上") == (4, "上")
    assert module._volume_number("清實錄") is None


def test_ming_catalog_uses_host_title_for_discovery(tmp_path, monkeypatch):
    module = _load_script()
    source = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))["sources"][1]
    requested = []

    def discover(title):
        requested.append(title)
        return ["大明太祖高皇帝實錄/卷001"] if title.endswith("太祖高皇帝實錄") else []

    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "discover_child_pages", discover)
    monkeypatch.setattr(module, "fetch_rendered", lambda title: ("<p>史料正文</p>", 1, title))
    monkeypatch.setattr(module, "clean_original_blocks", lambda html: ["史料正文"])
    monkeypatch.setattr(module.time, "sleep", lambda _: None)

    report = module.archive_catalog_source(source)

    assert requested[0] == "明實錄/太祖高皇帝實錄"
    assert "明實錄/成祖文皇帝實錄" in requested
    assert report["child_catalog"][0]["host_title"] == requested[0]
    assert report["archived_file_pairs"] == 1


def test_catalog_ingestor_never_claims_incomplete_host_is_full_source(tmp_path, monkeypatch):
    module = _load_script()
    source = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))["sources"][0]
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "discover_child_pages", lambda title: [f"{title}/卷1"])
    monkeypatch.setattr(module, "fetch_rendered", lambda title: ("<div class='mw-parser-output'><p>史料正文</p></div>", 1, title))
    monkeypatch.setattr(module, "clean_original_blocks", lambda html: ["史料正文"])
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    report = module.archive_catalog_source(source)
    assert report["archive_scope_complete"] is True
    assert report["source_complete"] is False
    assert report["archive_scope_status"] == "host_catalog_archived"
    assert report["archived_file_pairs"] == 13


def test_catalog_ingestor_rejects_silent_zero_page_success(tmp_path, monkeypatch):
    module = _load_script()
    source = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))["sources"][1]
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "discover_child_pages", lambda title: [])

    report = module.archive_catalog_source(source)

    assert report["archive_scope_complete"] is False
    assert report["errors"] == [{
        "source": "明實錄",
        "error_type": "CatalogDiscoveryError",
        "error": "no catalog child pages discovered for a registered catalog source",
    }]
