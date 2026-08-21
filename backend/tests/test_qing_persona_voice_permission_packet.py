import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "history" / "tools" / "build_qing_persona_voice_permission_packet.py"


def _module():
    spec = importlib.util.spec_from_file_location("qing_voice_permission_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_permission_packet_covers_all_four_blocked_source_families() -> None:
    packet = _module().build_permission_packet()

    assert packet["source_count"] == 4
    assert packet["request_ready_source_count"] == 4
    assert packet["all_sources_request_ready"] is True
    assert [request["source_id"] for request in packet["permission_requests"]] == [
        "CN-QING-VOICE-0001",
        "CN-QING-VOICE-0002",
        "CN-QING-VOICE-0003",
        "CN-QING-VOICE-0004",
    ]
    assert all(
        request["registry_status"] == "blocked_with_reason"
        for request in packet["permission_requests"]
    )


def test_permission_requests_are_specific_and_provenance_backed() -> None:
    packet = _module().build_permission_packet()

    for request in packet["permission_requests"]:
        assert "permitted_research_export_or_machine_access" in request[
            "requested_authorizations"
        ]
        assert "research_storage_quotation_and_publication_reuse_terms" in request[
            "requested_authorizations"
        ]
        assert request["catalogue_scope"]
        assert request["current_restrictions"]
        assert request["provenance"]
        assert request["request_ready"] is True


def test_grand_council_request_preserves_completed_overlap_control() -> None:
    packet = _module().build_permission_packet()
    request = next(
        item
        for item in packet["permission_requests"]
        if item["source_id"] == "CN-QING-VOICE-0004"
    )

    assert request["overlap_control_recorded"] is True
    assert "不跨系列合并文本" in request["overlap_policy"]
    assert "stable_item_locator_export" in request["requested_authorizations"]
    assert "digitization_coverage_statement" in request["requested_authorizations"]


def test_packet_creation_never_grants_or_sends_permission() -> None:
    packet = _module().build_permission_packet()

    assert packet["sent_to_archive"] is False
    assert packet["authorization_received"] is False
    assert packet["automated_ingestion_allowed"] is False
    assert packet["pvc_creation_allowed"] is False
    assert all(
        not request["automated_ingestion_allowed"]
        and not request["pvc_creation_allowed"]
        for request in packet["permission_requests"]
    )
    assert packet["status"] == (
        "permission_packet_ready_for_external_submission_not_authorized"
    )
    assert "does not contact" in packet["safety_note"]
