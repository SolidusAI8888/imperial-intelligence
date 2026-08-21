from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


_SOURCE_KIND_WEIGHTS = {
    "imperial_verbatim": 1.00,
    "vermilion_rescript": 1.00,
    "imperial_edict": 0.95,
    "court_diary": 0.90,
    "memorial_response": 0.90,
    "institutional_record": 0.70,
    "later_compilation": 0.45,
}


@dataclass(frozen=True)
class PersonaVoiceEvidence:
    voice_evidence_id: str
    person_id: str
    source_id: str
    passage_id: str
    source_kind: str
    contemporaneous: bool
    text: str
    voice_features: tuple[str, ...]
    decision_features: tuple[str, ...]
    rhetoric_features: tuple[str, ...]
    confidence: float
    status: str

    @property
    def runtime_eligible(self) -> bool:
        return self.status == "reviewed" and bool(self.passage_id.strip()) and bool(self.text.strip())

    @property
    def evidence_weight(self) -> float:
        base = _SOURCE_KIND_WEIGHTS[self.source_kind]
        contemporaneous_factor = 1.0 if self.contemporaneous else 0.8
        return round(base * contemporaneous_factor * self.confidence, 4)


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a list")
    items = tuple(str(item).strip() for item in value if str(item).strip())
    return items


def parse_persona_voice_evidence(record: Mapping[str, object]) -> PersonaVoiceEvidence:
    required = (
        "voice_evidence_id",
        "person_id",
        "source_id",
        "passage_id",
        "source_kind",
        "contemporaneous",
        "text",
        "confidence",
        "status",
    )
    missing = [field for field in required if field not in record]
    if missing:
        raise ValueError(f"missing persona voice evidence fields: {', '.join(missing)}")

    source_kind = str(record["source_kind"])
    if source_kind not in _SOURCE_KIND_WEIGHTS:
        raise ValueError(f"unsupported source_kind: {source_kind}")

    status = str(record["status"])
    if status not in {"candidate", "reviewed", "rejected"}:
        raise ValueError(f"unsupported status: {status}")

    confidence = float(record["confidence"])
    if confidence < 0 or confidence > 1:
        raise ValueError("confidence must be between 0 and 1")

    contemporaneous = record["contemporaneous"]
    if not isinstance(contemporaneous, bool):
        raise ValueError("contemporaneous must be boolean")

    return PersonaVoiceEvidence(
        voice_evidence_id=str(record["voice_evidence_id"]).strip(),
        person_id=str(record["person_id"]).strip(),
        source_id=str(record["source_id"]).strip(),
        passage_id=str(record["passage_id"]).strip(),
        source_kind=source_kind,
        contemporaneous=contemporaneous,
        text=str(record["text"]).strip(),
        voice_features=_string_tuple(record.get("voice_features"), "voice_features"),
        decision_features=_string_tuple(record.get("decision_features"), "decision_features"),
        rhetoric_features=_string_tuple(record.get("rhetoric_features"), "rhetoric_features"),
        confidence=confidence,
        status=status,
    )


def select_runtime_voice_evidence(
    records: Iterable[PersonaVoiceEvidence], *, limit: int = 8
) -> tuple[PersonaVoiceEvidence, ...]:
    if limit < 1:
        raise ValueError("limit must be positive")
    eligible = [record for record in records if record.runtime_eligible]
    eligible.sort(key=lambda item: (-item.evidence_weight, item.voice_evidence_id))
    return tuple(eligible[:limit])
