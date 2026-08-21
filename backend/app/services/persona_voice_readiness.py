from __future__ import annotations

from dataclasses import dataclass

from app.services.knowledge_repository import load_person_voice_evidence
from app.services.persona_voice_evidence import build_persona_voice_profile


@dataclass(frozen=True)
class PersonaVoiceReadiness:
    person_id: str
    total_records: int
    candidate_records: int
    reviewed_records: int
    rejected_records: int
    attested_reviewed_records: int
    traceable_reviewed_records: int
    runtime_style_ready: bool
    selected_voice_evidence_ids: tuple[str, ...]
    applied_voice_evidence_ids: tuple[str, ...]
    distinct_passage_count: int
    distinct_source_count: int
    total_evidence_weight: float
    gate_blockers: tuple[str, ...]
    voice_features: tuple[str, ...]
    decision_features: tuple[str, ...]
    rhetoric_features: tuple[str, ...]
    fallback_reason: str | None
    status: str


def inspect_persona_voice_readiness(person_id: str) -> PersonaVoiceReadiness:
    """Report optional PVC coverage without turning style readiness into answer permission."""

    normalized_person_id = person_id.strip()
    if not normalized_person_id:
        raise ValueError("person_id must not be blank")

    records = load_person_voice_evidence(normalized_person_id)
    reviewed = [record for record in records if record.status == "reviewed"]
    attested = [record for record in reviewed if record.review_attested]
    traceable = [record for record in reviewed if record.runtime_eligible]
    profile = build_persona_voice_profile(normalized_person_id, traceable)
    runtime_style_ready = bool(profile and profile.runtime_style_ready)

    if not records:
        fallback_reason = "no_voice_evidence_records"
    elif not reviewed:
        fallback_reason = "no_reviewed_voice_evidence"
    elif not attested:
        fallback_reason = "no_attested_reviewed_voice_evidence"
    elif not traceable:
        fallback_reason = "no_traceable_reviewed_voice_evidence"
    elif profile and profile.gate_blockers:
        fallback_reason = profile.gate_blockers[0]
    else:
        fallback_reason = None

    return PersonaVoiceReadiness(
        person_id=normalized_person_id,
        total_records=len(records),
        candidate_records=sum(record.status == "candidate" for record in records),
        reviewed_records=len(reviewed),
        rejected_records=sum(record.status == "rejected" for record in records),
        attested_reviewed_records=len(attested),
        traceable_reviewed_records=len(traceable),
        runtime_style_ready=runtime_style_ready,
        selected_voice_evidence_ids=(profile.voice_evidence_ids if profile else ()),
        applied_voice_evidence_ids=(
            profile.applied_voice_evidence_ids if profile else ()
        ),
        distinct_passage_count=(profile.distinct_passage_count if profile else 0),
        distinct_source_count=(profile.distinct_source_count if profile else 0),
        total_evidence_weight=(profile.total_evidence_weight if profile else 0.0),
        gate_blockers=(profile.gate_blockers if profile else ()),
        voice_features=(profile.voice_features if profile else ()),
        decision_features=(profile.decision_features if profile else ()),
        rhetoric_features=(profile.rhetoric_features if profile else ()),
        fallback_reason=fallback_reason,
        status=(
            "runtime_voice_style_ready"
            if runtime_style_ready
            else "neutral_voice_fallback_required"
        ),
    )
