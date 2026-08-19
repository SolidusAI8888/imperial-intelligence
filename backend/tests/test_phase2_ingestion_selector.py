import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "history" / "tools" / "select_next_phase2_source.py"


def _module():
    spec = importlib.util.spec_from_file_location("phase2_selector", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase2_selector_starts_with_sanguozhi_on_clean_repo() -> None:
    module = _module()
    result = module.status()
    assert result["total"] == 18
    assert result["complete"] == 0
    assert result["pending"] == 18
    assert result["next_source_id"] == "CN-SANGUO-0001"


def test_phase2_selector_manifest_ids_are_unique() -> None:
    module = _module()
    ids = [source["source_id"] for source in module.load_sources()]
    assert len(ids) == len(set(ids)) == 18
