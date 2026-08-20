from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "history" / "source_registry" / "phase3_qing_huidian.yaml"


def test_daqing_huidian_uses_verified_siku_numbered_edition():
    source = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    assert source["source_id"] == "CN-QING-0002"
    assert source["title"] == "大清會典"
    assert source["edition_title"] == "欽定大清會典 (四庫全書本)"
    assert source["root_page"] == "欽定大清會典 (四庫全書本)"
    assert source["acquisition_strategy"] == "wikisource_numbered_volumes"
    assert source["volume_min"] == 1
    assert source["volume_max"] == 100
    assert source["edition_scope"]["expected_volumes"] == 100


def test_daqing_huidian_completion_is_edition_scoped_not_family_scoped():
    source = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    scope = source["edition_scope"]
    assert scope["completion_claim"] == "edition_complete_only"
    assert "not of every" in scope["note"]
