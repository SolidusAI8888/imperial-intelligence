from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.services.knowledge_repository import VOICE_EVIDENCE_ROOT
from app.services.persona_voice_evidence import parse_persona_voice_evidence
from app.services.persona_voice_review import build_persona_voice_review_packet
from app.services.source_corpus_passage import SOURCE_CORPUS_ROOT


@dataclass(frozen=True)
class PersonaVoiceReviewQueueItem:
    voice_evidence_id: str
    person_id: str
    source_id: str
    passage_id: str
    source_kind: str
    contemporaneous: bool
    current_status: str
    candidate_text: str
    archive_context_excerpt: str | None
    voice_features: tuple[str, ...]
    decision_features: tuple[str, ...]
    rhetoric_features: tuple[str, ...]
    confidence: float
    canonical_passage_found: bool
    archived_file_integrity_verified: bool
    candidate_text_matches_archive: bool
    required_attestations: tuple[str, ...]
    conflicting_candidate_ids: tuple[str, ...]
    review_fingerprint: str
    approval_ready: bool
    blockers: tuple[str, ...]
    review_attested: bool
    runtime_eligible: bool
    review_packet_endpoint: str
    next_action: str
    status: str


@dataclass(frozen=True)
class PersonaVoiceReviewQueue:
    total_records: int
    candidate_records: int
    ready_candidate_records: int
    blocked_candidate_records: int
    unattested_reviewed_records: int
    runtime_eligible_reviewed_records: int
    rejected_records: int
    queue_state: str
    filtered_records: int
    returned_records: int
    offset: int
    limit: int
    has_more: bool
    items: tuple[PersonaVoiceReviewQueueItem, ...]
    status: str


def _load_records(root: Path):
    records = []
    for path in sorted(root.rglob("*.yaml")) if root.exists() else ():
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Expected YAML mapping: {path}")
        records.append(parse_persona_voice_evidence(raw))
    return records


def build_persona_voice_review_queue(
    *,
    person_id: str | None = None,
    queue_state: str = "all",
    offset: int = 0,
    limit: int = 50,
    voice_root: Path | None = None,
    corpus_root: Path | None = None,
) -> PersonaVoiceReviewQueue:
    """Build a read-only human queue without auto-approving any PVC record."""

    root = voice_root or VOICE_EVIDENCE_ROOT
    records = _load_records(root)
    normalized_queue_state = queue_state.strip()
    allowed_queue_states = {"all", "ready", "blocked", "attestation_repair"}
    if normalized_queue_state not in allowed_queue_states:
        raise ValueError(
            "queue_state must be one of: all, ready, blocked, attestation_repair"
        )
    if offset < 0:
        raise ValueError("offset must be greater than or equal to 0")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    if person_id is not None:
        normalized_person_id = person_id.strip()
        if not normalized_person_id:
            raise ValueError("person_id filter must not be blank")
        records = [record for record in records if record.person_id == normalized_person_id]

    candidate_keys = Counter(
        (record.person_id, record.passage_id)
        for record in records
        if record.status == "candidate"
    )
    items: list[PersonaVoiceReviewQueueItem] = []
    for record in records:
        if record.status == "candidate":
            packet = build_persona_voice_review_packet(
                record.voice_evidence_id,
                voice_root=root,
                corpus_root=corpus_root or SOURCE_CORPUS_ROOT,
            )
            blockers = list(packet.blockers)
            if (
                candidate_keys[(record.person_id, record.passage_id)] > 1
                and "duplicate_candidates_for_person_and_passage" not in blockers
            ):
                blockers.append("duplicate_candidates_for_person_and_passage")
            items.append(
                PersonaVoiceReviewQueueItem(
                    voice_evidence_id=record.voice_evidence_id,
                    person_id=record.person_id,
                    source_id=record.source_id,
                    passage_id=record.passage_id,
                    source_kind=packet.source_kind,
                    contemporaneous=packet.contemporaneous,
                    current_status=record.status,
                    candidate_text=packet.candidate_text,
                    archive_context_excerpt=packet.archive_context_excerpt,
                    voice_features=packet.voice_features,
                    decision_features=packet.decision_features,
                    rhetoric_features=packet.rhetoric_features,
                    confidence=packet.confidence,
                    canonical_passage_found=packet.canonical_passage_found,
                    archived_file_integrity_verified=(
                        packet.archived_file_integrity_verified
                    ),
                    candidate_text_matches_archive=(
                        packet.candidate_text_matches_archive
                    ),
                    required_attestations=packet.required_attestations,
                    conflicting_candidate_ids=packet.conflicting_candidate_ids,
                    review_fingerprint=packet.review_fingerprint,
                    approval_ready=not blockers,
                    blockers=tuple(blockers),
                    review_attested=False,
                    runtime_eligible=False,
                    review_packet_endpoint=(
                        f"/persona-voice/{record.voice_evidence_id}/review-packet"
                    ),
                    next_action=(
                        packet.next_action
                        if not blockers
                        else "resolve_review_packet_blockers_before_decision"
                    ),
                    status=(
                        "candidate_ready_for_explicit_human_review"
                        if not blockers
                        else "candidate_blocked_before_human_review"
                    ),
                )
            )
        elif record.status == "reviewed" and not record.runtime_eligible:
            packet = build_persona_voice_review_packet(
                record.voice_evidence_id,
                voice_root=root,
                corpus_root=corpus_root or SOURCE_CORPUS_ROOT,
            )
            repair_blockers = ["reviewed_record_missing_complete_attestation"]
            repair_blockers.extend(
                blocker
                for blocker in packet.blockers
                if blocker != "voice_evidence_status_is_not_candidate"
            )
            archive_repair_required = len(repair_blockers) > 1
            items.append(
                PersonaVoiceReviewQueueItem(
                    voice_evidence_id=record.voice_evidence_id,
                    person_id=record.person_id,
                    source_id=record.source_id,
                    passage_id=record.passage_id,
                    source_kind=packet.source_kind,
                    contemporaneous=packet.contemporaneous,
                    current_status=record.status,
                    candidate_text=packet.candidate_text,
                    archive_context_excerpt=packet.archive_context_excerpt,
                    voice_features=packet.voice_features,
                    decision_features=packet.decision_features,
                    rhetoric_features=packet.rhetoric_features,
                    confidence=packet.confidence,
                    canonical_passage_found=packet.canonical_passage_found,
                    archived_file_integrity_verified=(
                        packet.archived_file_integrity_verified
                    ),
                    candidate_text_matches_archive=(
                        packet.candidate_text_matches_archive
                    ),
                    required_attestations=packet.required_attestations,
                    conflicting_candidate_ids=packet.conflicting_candidate_ids,
                    review_fingerprint=packet.review_fingerprint,
                    approval_ready=False,
                    blockers=tuple(repair_blockers),
                    review_attested=record.review_attested,
                    runtime_eligible=False,
                    review_packet_endpoint=(
                        f"/persona-voice/{record.voice_evidence_id}/review-packet"
                    ),
                    next_action=(
                        "resolve_review_packet_blockers_before_decision"
                        if archive_repair_required
                        else "repair_review_attestations_before_runtime_use"
                    ),
                    status="reviewed_record_requires_attestation_repair",
                )
            )

    items.sort(
        key=lambda item: (
            not item.approval_ready,
            item.person_id,
            item.voice_evidence_id,
        )
    )
    candidate_count = sum(record.status == "candidate" for record in records)
    ready_count = sum(item.approval_ready for item in items)
    if normalized_queue_state == "ready":
        filtered_items = [item for item in items if item.approval_ready]
    elif normalized_queue_state == "blocked":
        filtered_items = [
            item
            for item in items
            if item.current_status == "candidate" and not item.approval_ready
        ]
    elif normalized_queue_state == "attestation_repair":
        filtered_items = [
            item
            for item in items
            if item.status == "reviewed_record_requires_attestation_repair"
        ]
    else:
        filtered_items = items
    page = filtered_items[offset : offset + limit]
    return PersonaVoiceReviewQueue(
        total_records=len(records),
        candidate_records=candidate_count,
        ready_candidate_records=ready_count,
        blocked_candidate_records=candidate_count - ready_count,
        unattested_reviewed_records=sum(
            record.status == "reviewed" and not record.runtime_eligible
            for record in records
        ),
        runtime_eligible_reviewed_records=sum(
            record.status == "reviewed" and record.runtime_eligible
            for record in records
        ),
        rejected_records=sum(record.status == "rejected" for record in records),
        queue_state=normalized_queue_state,
        filtered_records=len(filtered_items),
        returned_records=len(page),
        offset=offset,
        limit=limit,
        has_more=offset + len(page) < len(filtered_items),
        items=tuple(page),
        status="persona_voice_review_queue_read_only_no_automatic_approval",
    )
