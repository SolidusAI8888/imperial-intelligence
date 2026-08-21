import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "history" / "tools" / "audit_qing_persona_voice_overlap.py"


def _module():
    spec = importlib.util.spec_from_file_location("qing_voice_overlap", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_every_grand_council_subseries_has_exactly_one_overlap_action() -> None:
    result = _module().audit_overlap()

    assert result["total_subseries"] == 6
    assert result["reviewed_subseries"] == 6
    assert result["missing_subseries"] == ()
    assert result["duplicate_subseries"] == ()
    assert result["unexpected_subseries"] == ()
    assert result["invalid_action_subseries"] == ()
    assert result["overlap_control_complete"] is True


def test_copies_are_linked_and_separately_registered_edicts_are_excluded() -> None:
    result = _module().audit_overlap()

    assert result["link_only_subseries"] == ("汉文录副奏折", "满文录副奏折")
    assert result["excluded_subseries"] == ("满文上谕档",)
    assert result["retained_subseries"] == (
        "满文议复档",
        "满文专档",
        "满文寄信档",
    )
    assert "never merged" in result["safety_note"]


def test_overlap_completion_does_not_bypass_access_and_reuse_gate() -> None:
    result = _module().audit_overlap()

    assert result["registry_status"] == "blocked_with_reason"
    assert result["manifest_design_allowed"] is False
    assert "reuse_rights" in result["unresolved_requirements"]
    assert result["status"] == "overlap_review_complete_access_still_blocked"
