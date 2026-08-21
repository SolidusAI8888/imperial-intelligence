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
    traceable_reviewed_records: int
    runtime_style_ready: bool
    selected_voice_evidence_ids: tuple[str, ...]
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
    traceable = [record for record in reviewed if record.runtime_eligible]
    profile = build_persona_voice_profile(normalized_person_id, traceable)
    has_features = bool(
        profile
        and (profile.voice_features or profile.decision_features or profile.rhetoric_features)
    )

    if not records:
        fallback_reason = "no_voice_evidence_records"
    elif not reviewed:
        fallback_reason = "no_reviewed_voice_evidence"
    elif not traceable:
        fallback_reason = "no_traceable_reviewed_voice_evidence"
    elif not has_features:
        fallback_reason = "reviewed_voice_evidence_has_no_style_features"
    else:
        fallback_reason = None

    return PersonaVoiceReadiness(
        person_id=normalized_person_id,
        total_records=len(records),
        candidate_records=sum(record.status == "candidate" for record in records),
        reviewed_records=len(reviewed),
        rejected_records=sum(record.status == "rejected" for record in records),
        traceable_reviewed_records=len(traceable),
        runtime_style_ready=has_features,
        selected_voice_evidence_ids=(profile.voice_evidence_ids if profile else ()),
        voice_features=(profile.voice_features if profile else ()),
        decision_features=(profile.decision_features if profile else ()),
        rhetoric_features=(profile.rhetoric_features if profile else ()),
        fallback_reason=fallback_reason,
        status=(
            "runtime_voice_style_ready"
            if has_features
            else "neutral_voice_fallback_required"
        ),
    )
