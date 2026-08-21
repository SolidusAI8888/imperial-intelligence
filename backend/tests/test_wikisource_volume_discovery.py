from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "history" / "tools" / "ingest_wikisource_phase1.py"


def _load_script():
    tools = str(SCRIPT.parent)
    if tools not in sys.path:
        sys.path.insert(0, tools)
    spec = spec_from_file_location("ingest_wikisource_phase1_volume_test", SCRIPT)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_chinese_volume_numbers_round_trip() -> None:
    module = _load_script()
    for number, text in ((1, "一"), (10, "十"), (11, "十一"), (101, "一百零一"), (210, "二百一十"), (348, "三百四十八")):
        assert module.format_chinese_number(number) == text
        assert module.parse_chinese_number(text) == number


def test_volume_parser_accepts_arabic_and_chinese_titles() -> None:
    module = _load_script()
    assert module.parse_volume_title("文獻通考/卷三百四十八", "文獻通考") == (348, "")
    assert module.parse_volume_title("資治通鑒/卷007上", "資治通鑒") == (7, "上")
    assert module.parse_volume_title("文獻通考/自序", "文獻通考") is None


def test_discovery_uses_chinese_root_links_without_fallback(monkeypatch) -> None:
    module = _load_script()
    monkeypatch.setattr(
        module,
        "api",
        lambda params: {
            "query": {
                "pages": [
                    {
                        "title": "文獻通考",
                        "links": [
                            {"title": "文獻通考/卷二"},
                            {"title": "文獻通考/卷一"},
                        ],
                    }
                ]
            }
        },
    )
    monkeypatch.setattr(
        module,
        "existing_titles",
        lambda candidates: (_ for _ in ()).throw(AssertionError("fallback not expected")),
    )

    assert module.discover_volume_titles("文獻通考", 1, 2) == [
        "文獻通考/卷一",
        "文獻通考/卷二",
    ]


def test_discovery_probes_chinese_volume_when_root_has_no_links(monkeypatch) -> None:
    module = _load_script()
    monkeypatch.setattr(
        module,
        "api",
        lambda params: {"query": {"pages": [{"title": "五代會要", "links": []}]}},
    )
    monkeypatch.setattr(
        module,
        "existing_titles",
        lambda candidates: {"五代會要/卷一"} if "五代會要/卷一" in candidates else set(),
    )

    assert module.discover_volume_titles("五代會要", 1, 1) == ["五代會要/卷一"]


def test_numbered_archiver_records_zero_page_discovery_as_error(tmp_path, monkeypatch) -> None:
    module = _load_script()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "discover_volume_titles", lambda root, low, high: [])

    report = module.archive_source({
        "source_id": "CN-TEST-0001",
        "title": "测试史料",
        "root_page": "测试史料",
        "dynasty_group": "test",
        "corpus_key": "test_source",
        "volume_min": 1,
        "volume_max": 2,
    })

    assert report["archived_file_pairs"] == 0
    assert report["errors"][0]["error_type"] == "VolumeDiscoveryError"
