#!/usr/bin/env python3
from __future__ import annotations

import argparse
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    packet = build_permission_packet()
    print(
        json.dumps(packet, ensure_ascii=False, indent=2)
        if args.json
        else packet["status"]
    )


if __name__ == "__main__":
    main()
