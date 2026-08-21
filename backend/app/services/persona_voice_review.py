from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re

import yaml

from app.services.knowledge_repository import VOICE_EVIDENCE_ROOT
from app.services.persona_voice_evidence import parse_persona_voice_evidence
from app.services.source_corpus_passage import (
    SOURCE_CORPUS_ROOT,
    find_archived_passage,
    normalized_source_text,
)


_VOICE_ID_RE = re.compile(r"^PVC-[A-Z0-9][A-Z0-9-]{2,63}$")


@dataclass(frozen=True)
class PersonaVoiceReviewPacket:
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
    archived_passage_path: str | None
    feature_tag_count: int
    requires_person_identity_review: bool
    required_attestations: tuple[str, ...]
    approval_ready: bool
    blockers: tuple[str, ...]
    next_action: str
    status: str


@dataclass(frozen=True)
class PersonaVoiceReviewDecisionResult:
    voice_evidence_id: str
    reviewer: str
    decision: str
    resulting_status: str
    persisted: bool
    runtime_eligible_after_persist: bool
    status: str


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return data


def _find_record_path(voice_evidence_id: str, root: Path) -> Path:
    if not _VOICE_ID_RE.fullmatch(voice_evidence_id):
        raise ValueError("voice_evidence_id must match PVC-<stable uppercase identifier>")
    matches = (
        [
            path
            for path in sorted(root.rglob("*.yaml"))
            if _load_yaml(path).get("voice_evidence_id") == voice_evidence_id
        ]
        if root.exists()
        else []
    )
    if not matches:
        raise FileNotFoundError(f"Persona voice evidence not found: {voice_evidence_id}")
    if len(matches) > 1:
        raise ValueError(f"Duplicate persona voice evidence ID: {voice_evidence_id}")
    return matches[0]


def _archive_context_excerpt(
    archived_text: str, candidate_text: str, *, context_characters: int = 160
) -> str | None:
    """Return bounded source context only when the stored excerpt matches exactly."""

    index = archived_text.find(candidate_text)
    if index < 0:
        return None
    start = max(0, index - context_characters)
    end = min(len(archived_text), index + len(candidate_text) + context_characters)
    excerpt = archived_text[start:end].strip()
    if start:
        excerpt = f"…{excerpt}"
    if end < len(archived_text):
        excerpt = f"{excerpt}…"
    return excerpt


def build_persona_voice_review_packet(
    voice_evidence_id: str,
    *,
    voice_root: Path | None = None,
    corpus_root: Path | None = None,
) -> PersonaVoiceReviewPacket:
    """Validate a PVC candidate against immutable archived source text."""

    record_path = _find_record_path(voice_evidence_id, voice_root or VOICE_EVIDENCE_ROOT)
    raw = _load_yaml(record_path)
    evidence = parse_persona_voice_evidence(raw)
    blockers: list[str] = []
    if evidence.status != "candidate":
        blockers.append("voice_evidence_status_is_not_candidate")
    if not evidence.passage_id.startswith(f"{evidence.source_id}-"):
        blockers.append("passage_id_does_not_match_source_id")

    archived = find_archived_passage(
        evidence.source_id,
        evidence.passage_id,
        corpus_root=corpus_root or SOURCE_CORPUS_ROOT,
    )
    archived_path: str | None = None
    archive_context_excerpt: str | None = None
    integrity_verified = False
    text_matches = False
    if archived is None:
        blockers.append("canonical_passage_not_found_in_source_corpus")
    else:
        archived_path = str(archived.path)
        archive_context_excerpt = _archive_context_excerpt(
            archived.text, evidence.text
        )
        integrity_verified = archived.integrity_verified
        if not integrity_verified:
            blockers.append("archived_file_not_verified_by_ingestion_report")
        candidate_text = normalized_source_text(evidence.text)
        text_matches = bool(candidate_text) and candidate_text in normalized_source_text(
            archived.text
        )
        if not text_matches:
            blockers.append("candidate_text_not_found_in_canonical_passage")

    feature_tag_count = sum(
        len(features)
        for features in (
            evidence.voice_features,
            evidence.decision_features,
            evidence.rhetoric_features,
        )
    )
    if not feature_tag_count:
        blockers.append("candidate_has_no_voice_or_decision_or_rhetoric_features")
    if len(normalized_source_text(evidence.text).replace(" ", "")) < 12:
        blockers.append("candidate_text_too_short_for_voice_review")

    return PersonaVoiceReviewPacket(
        voice_evidence_id=evidence.voice_evidence_id,
        person_id=evidence.person_id,
        source_id=evidence.source_id,
        passage_id=evidence.passage_id,
        source_kind=evidence.source_kind,
        contemporaneous=evidence.contemporaneous,
        current_status=evidence.status,
        candidate_text=evidence.text,
        archive_context_excerpt=archive_context_excerpt,
        voice_features=evidence.voice_features,
        decision_features=evidence.decision_features,
        rhetoric_features=evidence.rhetoric_features,
        confidence=evidence.confidence,
        canonical_passage_found=archived is not None,
        archived_file_integrity_verified=integrity_verified,
        candidate_text_matches_archive=text_matches,
        archived_passage_path=archived_path,
        feature_tag_count=feature_tag_count,
        requires_person_identity_review=True,
        required_attestations=(
            "passage_link_verified",
            "person_identity_verified",
            "transcription_checked",
            "feature_tags_reviewed",
        ),
        approval_ready=not blockers,
        blockers=tuple(blockers),
        next_action=(
            "record_explicit_human_review_with_all_attestations"
            if not blockers
            else "resolve_review_packet_blockers_before_decision"
        ),
        status=(
            "ready_for_explicit_human_voice_review"
            if not blockers
            else "blocked_before_human_voice_approval"
        ),
    )


def apply_persona_voice_review_decision(
    voice_evidence_id: str,
    *,
    reviewer: str,
    decision: str,
    passage_link_verified: bool,
    person_identity_verified: bool,
    transcription_checked: bool,
    feature_tags_reviewed: bool,
    note: str | None = None,
    persist: bool = False,
    voice_root: Path | None = None,
    corpus_root: Path | None = None,
) -> PersonaVoiceReviewDecisionResult:
    """Persist an explicit review without allowing a status-only approval shortcut."""

    normalized_reviewer = reviewer.strip()
    if not normalized_reviewer:
        raise ValueError("reviewer must not be empty")
    if decision not in {"approved", "rejected"}:
        raise ValueError("decision must be approved or rejected")
    if decision == "rejected" and not (note or "").strip():
        raise ValueError("rejected voice evidence requires a review note")

    resolved_voice_root = voice_root or VOICE_EVIDENCE_ROOT
    record_path = _find_record_path(voice_evidence_id, resolved_voice_root)
    packet = build_persona_voice_review_packet(
        voice_evidence_id,
        voice_root=resolved_voice_root,
        corpus_root=corpus_root or SOURCE_CORPUS_ROOT,
    )
    checks_complete = bool(
        passage_link_verified
        and person_identity_verified
        and transcription_checked
        and feature_tags_reviewed
    )
    if decision == "approved" and not packet.approval_ready:
        raise ValueError(f"voice evidence approval blocked: {list(packet.blockers)}")
    if decision == "approved" and not checks_complete:
        raise ValueError("approved voice evidence requires all four review attestations")

    raw = _load_yaml(record_path)
    raw["status"] = "reviewed" if decision == "approved" else "rejected"
    raw["review"] = {
        "reviewer": normalized_reviewer,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "passage_link_verified": bool(passage_link_verified),
        "person_identity_verified": bool(person_identity_verified),
        "transcription_checked": bool(transcription_checked),
        "feature_tags_reviewed": bool(feature_tags_reviewed),
        "note": (note or "").strip() or None,
        "safety_boundary": (
            "Voice review affects optional style metadata only and grants no factual answer permission."
        ),
    }
    reviewed = parse_persona_voice_evidence(raw)
    if persist:
        temporary = record_path.with_suffix(".yaml.tmp")
        temporary.write_text(
            yaml.safe_dump(raw, allow_unicode=True, sort_keys=False, width=100),
            encoding="utf-8",
        )
        temporary.replace(record_path)

    return PersonaVoiceReviewDecisionResult(
        voice_evidence_id=voice_evidence_id,
        reviewer=normalized_reviewer,
        decision=decision,
        resulting_status=reviewed.status,
        persisted=persist,
        runtime_eligible_after_persist=bool(persist and reviewed.runtime_eligible),
        status="voice_review_decision_validated_style_only_no_answer_permission_change",
    )
