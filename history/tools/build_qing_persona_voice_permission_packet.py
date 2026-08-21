#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "history" / "source_registry" / "qing_persona_voice_sources.yaml"
BLOCKED_STATUS = "blocked_with_reason"
PERMISSION_STRATEGY = "archival_permission_required"
DENIED_DECISION = "automated_ingestion_not_authorized"

AUTHORIZATION_BY_REQUIREMENT = {
    "emperor_and_reign_partition": "emperor_and_reign_partition_metadata",
    "stable_item_or_page_locator_export": "stable_item_or_page_locator_export",
    "stable_item_locator": "stable_item_locator_export",
    "machine_access_or_permitted_research_export": "permitted_research_export_or_machine_access",
    "reuse_rights": "research_storage_quotation_and_publication_reuse_terms",
    "transcription_and_language_handling": "image_transcription_and_language_processing_terms",
    "image_and_transcription_availability": "image_and_transcription_access",
    "digitization_completeness": "digitization_coverage_statement",
}


def _load_manifest() -> dict:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
        raise ValueError("Qing persona voice source registry must contain a source list")
    return data


def _request_for_source(source: dict) -> dict:
    review = source.get("access_review") or {}
    requirements = tuple(source.get("remaining_requirements") or ())
    requested_authorizations = tuple(
        AUTHORIZATION_BY_REQUIREMENT.get(item, f"resolution_for_{item}")
        for item in requirements
    )
    provenance = tuple(
        dict.fromkeys(
            [*(source.get("provenance") or ()), *(review.get("provenance") or ())]
        )
    )
    request_ready = bool(
        source.get("status") == BLOCKED_STATUS
        and source.get("acquisition_strategy") == PERMISSION_STRATEGY
        and source.get("holding_institution")
        and review
        and review.get("decision") == DENIED_DECISION
        and review.get("reuse_permission") == "written_archive_permission_required"
        and requirements
        and provenance
    )
    overlap_review = source.get("overlap_review") or {}

    return {
        "source_id": source["source_id"],
        "title": source["title"],
        "holding_institution": source.get("holding_institution"),
        "registry_status": source.get("status"),
        "request_ready": request_ready,
        "catalogue_scope": source.get("discovered_scope") or {},
        "requested_authorizations": requested_authorizations,
        "unresolved_requirements": requirements,
        "current_access_mode": review.get("access_mode"),
        "current_restrictions": tuple(review.get("restrictions") or ()),
        "overlap_control_recorded": bool(overlap_review),
        "overlap_policy": overlap_review.get("policy"),
        "automated_ingestion_allowed": False,
        "pvc_creation_allowed": False,
        "decision": "external_authorization_required_before_manifest_or_pvc",
        "provenance": provenance,
    }


def build_permission_packet() -> dict:
    """Prepare an unsent, fail-closed archive permission request specification."""

    data = _load_manifest()
    sources = tuple(data["sources"])
    source_ids = [source.get("source_id") for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Qing persona voice source registry contains duplicate source IDs")
    requests = tuple(_request_for_source(source) for source in sources)
    ready = sum(request["request_ready"] for request in requests)

    return {
        "packet_id": "QING-PERSONA-VOICE-PERMISSION-REQUEST-V1",
        "holding_institution": "中国第一历史档案馆",
        "purpose": (
            "request terms for a provenance-preserving research export, passage-level citation, "
            "and separately reviewed persona-voice analysis"
        ),
        "source_count": len(requests),
        "request_ready_source_count": ready,
        "all_sources_request_ready": ready == len(requests) and bool(requests),
        "permission_requests": requests,
        "questions_for_archive": (
            "Can stable item, page, or catalogue locators be included in an approved export?",
            "May approved research copies be locally hashed, transcribed, and indexed?",
            "What storage, quotation, attribution, and publication terms apply?",
            "What emperor, reign, language, and digitization-coverage metadata can be exported?",
        ),
        "sent_to_archive": False,
        "authorization_received": False,
        "automated_ingestion_allowed": False,
        "pvc_creation_allowed": False,
        "status": "permission_packet_ready_for_external_submission_not_authorized",
        "safety_note": (
            "preparing this packet does not contact the archive or grant collection and reuse rights"
        ),
    }


def audit_permission_packet(packet: dict | None = None) -> dict:
    """Check packet coverage and safety without authorizing or submitting it."""

    resolved_packet = packet or build_permission_packet()
    data = _load_manifest()
    sources = tuple(data["sources"])
    expected_ids = tuple(source["source_id"] for source in sources)
    expected_by_id = {source["source_id"]: source for source in sources}
    raw_requests = resolved_packet.get("permission_requests") or ()
    requests = tuple(item for item in raw_requests if isinstance(item, dict))
    request_ids = [request.get("source_id") for request in requests]
    counts = Counter(request_ids)
    missing_ids = tuple(source_id for source_id in expected_ids if counts[source_id] == 0)
    duplicate_ids = tuple(
        sorted(str(source_id) for source_id, count in counts.items() if count > 1)
    )
    unexpected_ids = tuple(
        sorted(
            str(source_id)
            for source_id in counts
            if source_id not in expected_by_id
        )
    )
    incomplete_ids: list[str] = []
    authorization_mismatch_ids: list[str] = []
    unsafe_ids: list[str] = []
    required_fields = (
        "source_id",
        "title",
        "holding_institution",
        "catalogue_scope",
        "requested_authorizations",
        "unresolved_requirements",
        "current_access_mode",
        "current_restrictions",
        "decision",
        "provenance",
    )
    for request in requests:
        source_id = str(request.get("source_id") or "")
        source = expected_by_id.get(source_id)
        if source is None:
            continue
        if not request.get("request_ready") or any(
            not request.get(field) for field in required_fields
        ):
            incomplete_ids.append(source_id)
        expected_authorizations = {
            AUTHORIZATION_BY_REQUIREMENT.get(item, f"resolution_for_{item}")
            for item in source.get("remaining_requirements") or ()
        }
        if set(request.get("requested_authorizations") or ()) != expected_authorizations:
            authorization_mismatch_ids.append(source_id)
        if request.get("automated_ingestion_allowed") or request.get(
            "pvc_creation_allowed"
        ):
            unsafe_ids.append(source_id)

    questions = tuple(resolved_packet.get("questions_for_archive") or ())
    questions_complete = len(questions) >= 4 and all(
        isinstance(question, str) and question.strip() for question in questions
    )
    top_level_safety_preserved = bool(
        resolved_packet.get("sent_to_archive") is False
        and resolved_packet.get("authorization_received") is False
        and resolved_packet.get("automated_ingestion_allowed") is False
        and resolved_packet.get("pvc_creation_allowed") is False
    )
    audit_passed = bool(
        expected_ids
        and len(requests) == len(expected_ids)
        and not missing_ids
        and not duplicate_ids
        and not unexpected_ids
        and not incomplete_ids
        and not authorization_mismatch_ids
        and not unsafe_ids
        and questions_complete
        and top_level_safety_preserved
    )
    return {
        "packet_id": resolved_packet.get("packet_id"),
        "expected_source_count": len(expected_ids),
        "request_count": len(requests),
        "missing_source_ids": missing_ids,
        "duplicate_source_ids": duplicate_ids,
        "unexpected_source_ids": unexpected_ids,
        "incomplete_request_source_ids": tuple(sorted(incomplete_ids)),
        "authorization_mismatch_source_ids": tuple(
            sorted(authorization_mismatch_ids)
        ),
        "unsafe_request_source_ids": tuple(sorted(unsafe_ids)),
        "questions_complete": questions_complete,
        "top_level_safety_preserved": top_level_safety_preserved,
        "audit_passed": audit_passed,
        "automatic_submission_allowed": False,
        "automated_ingestion_allowed": False,
        "pvc_creation_allowed": False,
        "status": (
            "permission_packet_structure_valid_no_authorization"
            if audit_passed
            else "permission_packet_structure_requires_repair"
        ),
        "safety_note": (
            "a valid packet remains unsent and cannot grant archive, ingestion, or PVC permission"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    result = (
        audit_permission_packet()
        if args.audit
        else build_permission_packet()
    )
    print(
        json.dumps(result, ensure_ascii=False, indent=2)
        if args.json
        else result["status"]
    )


if __name__ == "__main__":
    main()
