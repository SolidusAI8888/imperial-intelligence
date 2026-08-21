from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
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


_PERSON_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]{2,63}$")
_SOURCE_ID_RE = re.compile(r"^CN-[A-Z0-9][A-Z0-9-]{2,79}$")
_PASSAGE_ID_RE = re.compile(r"^CN-[A-Z0-9-]+-P[0-9]{4,}$")
_FEATURE_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


@dataclass(frozen=True)
class PersonaVoiceCandidateResult:
    voice_evidence_id: str
    person_id: str
    source_id: str
    passage_id: str
    candidate_path: str
    persisted: bool
    review_required: bool
    runtime_eligible: bool
    status: str


def _clean_features(values: list[str]) -> list[str]:
    cleaned = sorted({value.strip() for value in values if value.strip()})
    invalid = [value for value in cleaned if not _FEATURE_RE.fullmatch(value)]
    if invalid:
        raise ValueError(f"feature tags must be stable snake_case identifiers: {invalid}")
    return cleaned


def _stable_voice_evidence_id(
    person_id: str,
    source_id: str,
    passage_id: str,
    text: str,
    source_kind: str,
) -> str:
    dynasty = person_id.split("_", 1)[0].upper()
    identity = "\n".join(
        (person_id, source_id, passage_id, normalized_source_text(text), source_kind)
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12].upper()
    return f"PVC-{dynasty}-{digest}"


def _same_candidate(existing: dict, proposed: dict) -> bool:
    fields = (
        "voice_evidence_id",
        "person_id",
        "source_id",
        "passage_id",
        "source_kind",
        "contemporaneous",
        "text",
        "voice_features",
        "decision_features",
        "rhetoric_features",
        "confidence",
        "status",
    )
    return all(existing.get(field) == proposed.get(field) for field in fields)


def create_persona_voice_candidate(
    *,
    person_id: str,
    source_id: str,
    passage_id: str,
    source_kind: str,
    contemporaneous: bool,
    text: str,
    voice_features: list[str],
    decision_features: list[str],
    rhetoric_features: list[str],
    confidence: float,
    proposed_by: str,
    note: str | None = None,
    persist: bool = False,
    voice_root: Path | None = None,
    corpus_root: Path | None = None,
) -> PersonaVoiceCandidateResult:
    """Create a deterministic review candidate only from verified archived text."""

    normalized_person_id = person_id.strip()
    if not _PERSON_ID_RE.fullmatch(normalized_person_id):
        raise ValueError("person_id must be a stable lowercase identifier")
    normalized_source_id = source_id.strip()
    normalized_passage_id = passage_id.strip()
    if not _SOURCE_ID_RE.fullmatch(normalized_source_id):
        raise ValueError("source_id must be a stable CN-* identifier")
    if not _PASSAGE_ID_RE.fullmatch(normalized_passage_id):
        raise ValueError("passage_id must be a canonical CN-*-P#### identifier")
    normalized_proposer = proposed_by.strip()
    if not normalized_proposer:
        raise ValueError("proposed_by must not be empty")
    if not normalized_passage_id.startswith(f"{normalized_source_id}-"):
        raise ValueError("passage_id must belong to source_id")

    normalized_text = normalized_source_text(text)
    if len(normalized_text.replace(" ", "")) < 12:
        raise ValueError("persona voice candidate text must contain at least 12 characters")
    cleaned_voice = _clean_features(voice_features)
    cleaned_decision = _clean_features(decision_features)
    cleaned_rhetoric = _clean_features(rhetoric_features)
    if not (cleaned_voice or cleaned_decision or cleaned_rhetoric):
        raise ValueError("persona voice candidate requires at least one feature tag")

    archived = find_archived_passage(
        normalized_source_id,
        normalized_passage_id,
        corpus_root=corpus_root or SOURCE_CORPUS_ROOT,
    )
    if archived is None:
        raise ValueError("canonical passage was not found in the source corpus")
    if not archived.integrity_verified:
        raise ValueError("archived source file failed ingestion-report integrity verification")
    if normalized_text not in normalized_source_text(archived.text):
        raise ValueError("candidate text was not found in the canonical archived passage")

    voice_evidence_id = _stable_voice_evidence_id(
        normalized_person_id,
        normalized_source_id,
        normalized_passage_id,
        normalized_text,
        source_kind,
    )
    raw = {
        "voice_evidence_id": voice_evidence_id,
        "person_id": normalized_person_id,
        "source_id": normalized_source_id,
        "passage_id": normalized_passage_id,
        "source_kind": source_kind,
        "contemporaneous": contemporaneous,
        "text": text.strip(),
        "voice_features": cleaned_voice,
        "decision_features": cleaned_decision,
        "rhetoric_features": cleaned_rhetoric,
        "confidence": confidence,
        "status": "candidate",
        "candidate": {
            "proposed_by": normalized_proposer,
            "proposed_at": datetime.now(timezone.utc).isoformat(),
            "note": (note or "").strip() or None,
            "safety_boundary": (
                "Candidate creation never grants runtime style or factual answer permission."
            ),
        },
    }
    evidence = parse_persona_voice_evidence(raw)
    root = voice_root or VOICE_EVIDENCE_ROOT
    target = root / normalized_person_id / f"{voice_evidence_id}.yaml"
    if persist:
        if target.exists():
            existing = yaml.safe_load(target.read_text(encoding="utf-8"))
            if not isinstance(existing, dict) or not _same_candidate(existing, raw):
                raise FileExistsError(f"Conflicting PVC candidate already exists: {target}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(".yaml.tmp")
            temporary.write_text(
                yaml.safe_dump(raw, allow_unicode=True, sort_keys=False, width=100),
                encoding="utf-8",
            )
            temporary.replace(target)

    return PersonaVoiceCandidateResult(
        voice_evidence_id=voice_evidence_id,
        person_id=evidence.person_id,
        source_id=evidence.source_id,
        passage_id=evidence.passage_id,
        candidate_path=str(target),
        persisted=persist,
        review_required=True,
        runtime_eligible=False,
        status="persona_voice_candidate_requires_explicit_human_review",
    )
