import importlib.util
from copy import deepcopy
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


def test_permission_packet_audit_confirms_exact_registry_coverage() -> None:
    audit = _module().audit_permission_packet()

    assert audit["expected_source_count"] == 4
    assert audit["request_count"] == 4
    assert audit["missing_source_ids"] == ()
    assert audit["duplicate_source_ids"] == ()
    assert audit["unexpected_source_ids"] == ()
    assert audit["incomplete_request_source_ids"] == ()
    assert audit["authorization_mismatch_source_ids"] == ()
    assert audit["unsafe_request_source_ids"] == ()
    assert audit["questions_complete"] is True
    assert audit["top_level_safety_preserved"] is True
    assert audit["audit_passed"] is True
    assert audit["status"] == "permission_packet_structure_valid_no_authorization"


def test_permission_packet_audit_fails_closed_on_omission_or_unsafe_flag() -> None:
    module = _module()
    packet = deepcopy(module.build_permission_packet())
    packet["permission_requests"] = list(packet["permission_requests"])[1:]
    packet["permission_requests"][0]["automated_ingestion_allowed"] = True
    packet["automated_ingestion_allowed"] = True

    audit = module.audit_permission_packet(packet)

    assert audit["missing_source_ids"] == ("CN-QING-VOICE-0001",)
    assert audit["unsafe_request_source_ids"] == ("CN-QING-VOICE-0002",)
    assert audit["top_level_safety_preserved"] is False
    assert audit["audit_passed"] is False
    assert audit["automatic_submission_allowed"] is False
    assert audit["automated_ingestion_allowed"] is False
    assert audit["pvc_creation_allowed"] is False
    assert audit["status"] == "permission_packet_structure_requires_repair"


def test_permission_packet_audit_detects_changed_authorization_questions() -> None:
    module = _module()
    packet = deepcopy(module.build_permission_packet())
    request = list(packet["permission_requests"])[0]
    request["requested_authorizations"] = tuple(
        authorization
        for authorization in request["requested_authorizations"]
        if authorization != "research_storage_quotation_and_publication_reuse_terms"
    )

    audit = module.audit_permission_packet(packet)

    assert audit["authorization_mismatch_source_ids"] == (
        "CN-QING-VOICE-0001",
    )
    assert audit["audit_passed"] is False
