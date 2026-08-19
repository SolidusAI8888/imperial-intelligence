from __future__ import annotations

import json
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = PROJECT_ROOT / "history" / "source_registry" / "phase1_sources.yaml"
SUMMARY = PROJECT_ROOT / "history" / "source_corpus" / "PHASE1_INGESTION_SUMMARY.json"

EXPECTED_SOURCE_IDS = {
    "CN-HAN-0001",
    "CN-HAN-0002",
    "CN-HAN-0003",
    "CN-TANG-0001",
    "CN-TANG-0002",
    "CN-TANG-0003",
    "CN-TANG-0004",
    "CN-SONG-0001",
}


def test_registered_primary_source_corpus_is_complete() -> None:
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    registered_ids = {item["source_id"] for item in registry["sources"]}
    reported = {item["source_id"]: item for item in summary["reports"]}

    assert registered_ids == EXPECTED_SOURCE_IDS
    assert set(reported) == EXPECTED_SOURCE_IDS
    assert summary["extractor_version"] == 3
    assert summary["sources"] == 8
    assert summary["expected_units"] == 1419
    assert summary["v3_file_pairs"] == 1419
    assert summary["ingestion_errors"] == 0
    assert summary["contaminated_files"] == 0
    assert summary["unexpected_units"] == 0
    assert summary["complete"] is True

    for source_id, report in reported.items():
        assert report["complete"] is True, source_id
        assert report["missing_units"] == 0, source_id
        assert report["unexpected_units"] == 0, source_id
        assert report["ingestion_errors"] == 0, source_id
        assert report["contaminated_files"] == 0, source_id
        assert report["v3_file_pairs"] == report["expected_units"], source_id
