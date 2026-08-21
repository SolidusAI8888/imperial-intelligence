from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

import yaml

from app.services.knowledge_repository import PROJECT_ROOT, VOICE_EVIDENCE_ROOT
from app.services.persona_voice_evidence import parse_persona_voice_evidence


SOURCE_CORPUS_ROOT = PROJECT_ROOT / "history" / "source_corpus"
_VOICE_ID_RE = re.compile(r"^PVC-[A-Z0-9][A-Z0-9-]{2,63}$")


@dataclass(frozen=True)
class PersonaVoiceReviewPacket:
    voice_evidence_id: str
    person_id: str
    source_id: str
    passage_id: str
    current_status: str
    canonical_passage_found: bool
    archived_file_integrity_verified: bool
    candidate_text_matches_archive: bool
    archived_passage_path: str | None
    feature_tag_count: int
    approval_ready: bool
    blockers: tuple[str, ...]
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


def _normalized_text(value: str) -> str:
    return " ".join(value.split())


def _find_archived_passage(passage_id: str, root: Path) -> tuple[Path, str] | None:
    marker = f"[{passage_id}]"
    for path in sorted(root.rglob("*.txt")) if root.exists() else ():
        text = path.read_text(encoding="utf-8")
        marker_start = text.find(marker)
        if marker_start < 0:
            continue
        if marker_start > 0 and text[marker_start - 1] != "\n":
            continue
        content_start = marker_start + len(marker)
        next_marker = text.find("\n[CN-", content_start)
        passage = text[content_start : next_marker if next_marker >= 0 else None].strip()
        return path, passage
    return None


def _archive_file_integrity_verified(path: Path, source_id: str) -> bool:
    report_path = path.parent.parent / "ingestion_report.json"
    if not report_path.exists():
        return False
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if report.get("source_id") != source_id:
        return False
    page = next(
        (
            item
            for item in report.get("pages") or ()
            if item.get("file") == path.name and item.get("sha256")
        ),
        None,
    )
    if page is None:
        return False
    actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    return actual_hash == page["sha256"]


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

    archived = _find_archived_passage(
        evidence.passage_id, corpus_root or SOURCE_CORPUS_ROOT
    )
    archived_path: str | None = None
    integrity_verified = False
    text_matches = False
    if archived is None:
        blockers.append("canonical_passage_not_found_in_source_corpus")
    else:
        path, passage_text = archived
        archived_path = str(path)
        integrity_verified = _archive_file_integrity_verified(path, evidence.source_id)
        if not integrity_verified:
            blockers.append("archived_file_not_verified_by_ingestion_report")
        candidate_text = _normalized_text(evidence.text)
        text_matches = bool(candidate_text) and candidate_text in _normalized_text(
            passage_text
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
    if len(_normalized_text(evidence.text).replace(" ", "")) < 12:
        blockers.append("candidate_text_too_short_for_voice_review")

    return PersonaVoiceReviewPacket(
        voice_evidence_id=evidence.voice_evidence_id,
        person_id=evidence.person_id,
        source_id=evidence.source_id,
        passage_id=evidence.passage_id,
        current_status=evidence.status,
        canonical_passage_found=archived is not None,
        archived_file_integrity_verified=integrity_verified,
        candidate_text_matches_archive=text_matches,
        archived_passage_path=archived_path,
        feature_tag_count=feature_tag_count,
        approval_ready=not blockers,
        blockers=tuple(blockers),
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
        passage_link_verified and transcription_checked and feature_tags_reviewed
    )
    if decision == "approved" and not packet.approval_ready:
        raise ValueError(f"voice evidence approval blocked: {list(packet.blockers)}")
    if decision == "approved" and not checks_complete:
        raise ValueError("approved voice evidence requires all three review attestations")

    raw = _load_yaml(record_path)
    raw["status"] = "reviewed" if decision == "approved" else "rejected"
    raw["review"] = {
        "reviewer": normalized_reviewer,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "passage_link_verified": bool(passage_link_verified),
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
