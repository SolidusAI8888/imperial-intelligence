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


def test_phase2_selector_tracks_current_repository_progress() -> None:
    module = _module()
    result = module.status()
    assert result["total"] == 18
    assert result["complete"] + result["pending"] == 18
    assert len(result["complete_source_ids"]) == result["complete"]
    assert len(result["pending_source_ids"]) == result["pending"]
    if result["pending_source_ids"]:
        assert result["next_source_id"] == result["pending_source_ids"][0]
    else:
        assert result["next_source_id"] is None


def test_phase2_selector_manifest_ids_are_unique() -> None:
    module = _module()
    ids = [source["source_id"] for source in module.load_sources()]
    assert len(ids) == len(set(ids)) == 18
