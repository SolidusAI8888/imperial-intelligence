from __future__ import annotations

from pathlib import Path

import yaml

from app.models.knowledge import (
    HistoricalExperienceUnit,
    HistoricalRecord,
    Insight,
    RoleExperienceLink,
)
from app.services.persona_voice_evidence import (
    PersonaVoiceEvidence,
    parse_persona_voice_evidence,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RESEARCH_ROOT = PROJECT_ROOT / "knowledge" / "research" / "R-000001"
VOICE_EVIDENCE_ROOT = PROJECT_ROOT / "knowledge" / "persona_voice"
_ALLOWED_RECORD_TYPES = {
    "discussion",
    "memorial",
    "edict",
    "event",
    "appointment",
    "battle",
    "institution",
    "reflection",
    "other",
}


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def _normalize_record(raw: dict) -> dict:
    data = dict(raw)

    if "dynasty" not in data:
        time = data.get("time") or {}
        data["dynasty"] = time.get("dynasty", "Unknown")
        reign = time.get("reign")
        year = time.get("year")
        if "time_label" not in data:
            if reign and year is not None:
                data["time_label"] = f"{reign}{year}年"
            elif reign:
                data["time_label"] = str(reign)

    participants = data.get("participants", [])
    if participants and isinstance(participants[0], dict):
        data["participants"] = [
            item.get("person_id") or item.get("name")
            for item in participants
            if item.get("person_id") or item.get("name")
        ]

    if data.get("status") == "verified":
        data["status"] = "reviewed"

    if data.get("record_type") not in _ALLOWED_RECORD_TYPES:
        data["record_type"] = "other"

    return data


def _all_records() -> list[HistoricalRecord]:
    return [
        HistoricalRecord.model_validate(_normalize_record(_load_yaml(path)))
        for path in sorted((RESEARCH_ROOT / "her").glob("HER-*.yaml"))
    ]


def _all_experiences() -> list[HistoricalExperienceUnit]:
    return [
        HistoricalExperienceUnit.model_validate(_load_yaml(path))
        for path in sorted((RESEARCH_ROOT / "heu").glob("HEU-*.yaml"))
    ]


def _all_insights() -> list[Insight]:
    return [
        Insight.model_validate(_load_yaml(path))
        for path in sorted((RESEARCH_ROOT / "insight").glob("INS-*.yaml"))
    ]


def load_all_records() -> list[HistoricalRecord]:
    """Return the reusable factual historical-record inventory."""
    return _all_records()


def load_all_experiences() -> list[HistoricalExperienceUnit]:
    """Return person-owned HEUs without applying any problem-specific eligibility gate."""
    return _all_experiences()


def load_person_records(person_id: str) -> list[HistoricalRecord]:
    """Load only HERs in which the requested person is an explicit participant."""
    return [record for record in _all_records() if person_id in record.participants]


def load_person_experiences(person_id: str) -> list[HistoricalExperienceUnit]:
    """Load only experience units explicitly owned by the requested person."""
    return [heu for heu in _all_experiences() if heu.experience_owner == person_id]


def load_person_insights(person_id: str) -> list[Insight]:
    """Load insights derived exclusively from this person's HEU set.

    Insight files deliberately do not duplicate a person_id. Ownership is
    therefore derived from the reviewed HEU links rather than from dynasty
    filename prefixes. This prevents one emperor from inheriting another
    emperor's insight merely because both belong to the same dynasty.
    """
    owned_heu_ids = {heu.heu_id for heu in load_person_experiences(person_id)}
    if not owned_heu_ids:
        return []
    return [
        insight
        for insight in _all_insights()
        if insight.derived_from_heus
        and set(insight.derived_from_heus).issubset(owned_heu_ids)
    ]


def load_person_role_links(person_id: str) -> list[RoleExperienceLink]:
    """Load role links by the person_id stored inside each role-link file."""
    matches: list[dict] = []
    for path in sorted((RESEARCH_ROOT / "role_links").glob("ROLE-*.yaml")):
        data = _load_yaml(path)
        if data.get("person_id") == person_id:
            matches.append(data)

    if not matches:
        return []
    if len(matches) > 1:
        raise ValueError(f"Multiple role-link files found for person: {person_id}")

    data = matches[0]
    life_course_rule = data.get("life_course_rule", "full_lifetime")
    return [
        RoleExperienceLink(
            person_id=data["person_id"],
            heu_id=raw["heu_id"],
            relation=raw["relation"],
            responder_eligible=raw["responder_eligible"],
            personal_experience_strength=raw["personal_experience_strength"],
            life_course_rule=life_course_rule,
        )
        for raw in data["links"]
    ]


def load_all_persona_voice_evidence() -> list[PersonaVoiceEvidence]:
    """Load auditable PVC records; an absent corpus is a valid empty state."""

    if not VOICE_EVIDENCE_ROOT.exists():
        return []
    return [
        parse_persona_voice_evidence(_load_yaml(path))
        for path in sorted(VOICE_EVIDENCE_ROOT.rglob("*.yaml"))
    ]


def load_person_voice_evidence(person_id: str) -> list[PersonaVoiceEvidence]:
    return [
        evidence
        for evidence in load_all_persona_voice_evidence()
        if evidence.person_id == person_id
    ]


def load_first_question_records() -> list[HistoricalRecord]:
    return load_person_records("tang_taizong")


def load_first_question_experiences() -> list[HistoricalExperienceUnit]:
    return load_person_experiences("tang_taizong")


def load_first_question_insights() -> list[Insight]:
    return load_person_insights("tang_taizong")


def load_first_question_role_links() -> list[RoleExperienceLink]:
    return load_person_role_links("tang_taizong")
