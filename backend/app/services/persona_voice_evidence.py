from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
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

_MIN_STYLE_PASSAGES = 2
_MIN_STYLE_EVIDENCE_WEIGHT = 1.20


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
    reviewer: str | None
    reviewed_at: str | None
    review_decision: str | None
    passage_link_verified: bool
    transcription_checked: bool
    feature_tags_reviewed: bool

    @property
    def review_attested(self) -> bool:
        return bool(
            self.reviewer
            and self.reviewed_at
            and self.review_decision == "approved"
            and self.passage_link_verified
            and self.transcription_checked
            and self.feature_tags_reviewed
        )

    @property
    def runtime_eligible(self) -> bool:
        return bool(
            self.status == "reviewed"
            and self.review_attested
            and self.passage_id.strip()
            and self.text.strip()
        )

    @property
    def evidence_weight(self) -> float:
        base = _SOURCE_KIND_WEIGHTS[self.source_kind]
        contemporaneous_factor = 1.0 if self.contemporaneous else 0.8
        return round(base * contemporaneous_factor * self.confidence, 4)


@dataclass(frozen=True)
class PersonaVoiceProfile:
    """Auditable style-only guidance compiled from reviewed voice evidence."""

    person_id: str
    voice_evidence_ids: tuple[str, ...]
    voice_features: tuple[str, ...]
    decision_features: tuple[str, ...]
    rhetoric_features: tuple[str, ...]
    evidence_count: int = 0
    distinct_passage_count: int = 0
    distinct_source_count: int = 0
    total_evidence_weight: float = 0.0
    runtime_style_ready: bool = False
    gate_blockers: tuple[str, ...] = ()

    @property
    def applied_voice_evidence_ids(self) -> tuple[str, ...]:
        """Return only evidence IDs that actually affected runtime wording."""

        return self.voice_evidence_ids if self.runtime_style_ready else ()


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

    review = record.get("review") or {}
    if not isinstance(review, Mapping):
        raise ValueError("review must be a mapping")
    review_checks = (
        "passage_link_verified",
        "transcription_checked",
        "feature_tags_reviewed",
    )
    invalid_checks = [
        field
        for field in review_checks
        if field in review and not isinstance(review[field], bool)
    ]
    if invalid_checks:
        raise ValueError(f"review checks must be boolean: {', '.join(invalid_checks)}")
    review_decision = str(review.get("decision", "")).strip() or None
    if review_decision not in {None, "approved", "rejected"}:
        raise ValueError("review decision must be approved or rejected")
    reviewed_at = str(review.get("reviewed_at", "")).strip() or None
    if reviewed_at:
        try:
            datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("reviewed_at must be an ISO-8601 datetime") from exc

    evidence = PersonaVoiceEvidence(
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
        reviewer=(str(review.get("reviewer", "")).strip() or None),
        reviewed_at=reviewed_at,
        review_decision=review_decision,
        passage_link_verified=review.get("passage_link_verified") is True,
        transcription_checked=review.get("transcription_checked") is True,
        feature_tags_reviewed=review.get("feature_tags_reviewed") is True,
    )
    required_nonempty = {
        "voice_evidence_id": evidence.voice_evidence_id,
        "person_id": evidence.person_id,
        "source_id": evidence.source_id,
        "text": evidence.text,
    }
    blank = [field for field, value in required_nonempty.items() if not value]
    if blank:
        raise ValueError(f"blank persona voice evidence fields: {', '.join(blank)}")
    return evidence


def select_runtime_voice_evidence(
    records: Iterable[PersonaVoiceEvidence], *, person_id: str | None = None, limit: int = 8
) -> tuple[PersonaVoiceEvidence, ...]:
    if limit < 1:
        raise ValueError("limit must be positive")
    eligible = [
        record
        for record in records
        if record.runtime_eligible and (person_id is None or record.person_id == person_id)
    ]
    eligible.sort(key=lambda item: (-item.evidence_weight, item.voice_evidence_id))
    return tuple(eligible[:limit])


def _rank_features(
    records: tuple[PersonaVoiceEvidence, ...],
    field: str,
    *,
    limit: int = 3,
    minimum_passages: int = _MIN_STYLE_PASSAGES,
) -> tuple[str, ...]:
    passage_scores: dict[str, dict[str, float]] = defaultdict(dict)
    for record in records:
        for feature in getattr(record, field):
            passage_scores[feature][record.passage_id] = max(
                record.evidence_weight,
                passage_scores[feature].get(record.passage_id, 0.0),
            )
    scores = {
        feature: sum(weights.values())
        for feature, weights in passage_scores.items()
        if len(weights) >= minimum_passages
    }
    return tuple(
        feature
        for feature, _score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]
    )


def build_persona_voice_profile(
    person_id: str,
    records: Iterable[PersonaVoiceEvidence],
    *, evidence_limit: int = 8,
) -> PersonaVoiceProfile | None:
    """Compile reviewed evidence into style metadata without creating factual claims."""

    selected = select_runtime_voice_evidence(records, person_id=person_id, limit=evidence_limit)
    if not selected:
        return None
    distinct_passages = {record.passage_id for record in selected}
    distinct_sources = {record.source_id for record in selected}
    passage_weights: dict[str, float] = {}
    for record in selected:
        passage_weights[record.passage_id] = max(
            record.evidence_weight, passage_weights.get(record.passage_id, 0.0)
        )
    total_evidence_weight = round(sum(passage_weights.values()), 4)
    voice_features = _rank_features(selected, "voice_features")
    decision_features = _rank_features(selected, "decision_features")
    rhetoric_features = _rank_features(selected, "rhetoric_features")
    blockers: list[str] = []
    if len(distinct_passages) < _MIN_STYLE_PASSAGES:
        blockers.append("fewer_than_2_independent_voice_passages")
    if total_evidence_weight < _MIN_STYLE_EVIDENCE_WEIGHT:
        blockers.append("voice_evidence_weight_below_1.20")
    if not (voice_features or decision_features or rhetoric_features):
        blockers.append("no_style_features_corroborated_by_2_passages")
    return PersonaVoiceProfile(
        person_id=person_id,
        voice_evidence_ids=tuple(record.voice_evidence_id for record in selected),
        voice_features=voice_features,
        decision_features=decision_features,
        rhetoric_features=rhetoric_features,
        evidence_count=len(selected),
        distinct_passage_count=len(distinct_passages),
        distinct_source_count=len(distinct_sources),
        total_evidence_weight=total_evidence_weight,
        runtime_style_ready=not blockers,
        gate_blockers=tuple(blockers),
    )


def style_answer_opening(default: str, profile: PersonaVoiceProfile | None) -> str:
    """Apply conservative structural style; never copy evidence text or add historical facts."""

    if profile is None or not profile.runtime_style_ready:
        return default
    features = set(profile.voice_features)
    if "terse" in features or "direct" in features:
        return "先说要害：这不是一个可以归结为单一因素的问题。"
    if "admonitory" in features:
        return "此事不可轻率：它不能被归结为单一因素。"
    if "conciliatory" in features:
        return "我愿先把不同处境分开来看：这不是一个可以归结为单一因素的问题。"
    return default
