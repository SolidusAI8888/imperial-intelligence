from __future__ import annotations

from pathlib import Path

import yaml

from app.models.knowledge import (
    HistoricalExperienceUnit,
    HistoricalRecord,
    Insight,
    RoleExperienceLink,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RESEARCH_ROOT = PROJECT_ROOT / "knowledge" / "research" / "R-000001"
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
_PERSON_PREFIX = {
    "liu_bang": "HAN",
    "tang_taizong": "TANG",
    "song_taizu": "SONG",
}
_ROLE_FILE = {
    "liu_bang": "ROLE-LIU-BANG.yaml",
    "tang_taizong": "ROLE-TANG-TAIZONG.yaml",
    "song_taizu": "ROLE-SONG-TAIZU.yaml",
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


def _person_prefix(person_id: str) -> str:
    try:
        return _PERSON_PREFIX[person_id]
    except KeyError as exc:
        raise ValueError(f"Unsupported first-question candidate: {person_id}") from exc


def load_person_records(person_id: str) -> list[HistoricalRecord]:
    prefix = _person_prefix(person_id)
    return [
        HistoricalRecord.model_validate(_normalize_record(_load_yaml(path)))
        for path in sorted((RESEARCH_ROOT / "her").glob(f"HER-{prefix}-*.yaml"))
    ]


def load_person_experiences(person_id: str) -> list[HistoricalExperienceUnit]:
    prefix = _person_prefix(person_id)
    return [
        HistoricalExperienceUnit.model_validate(_load_yaml(path))
        for path in sorted((RESEARCH_ROOT / "heu").glob(f"HEU-{prefix}-*.yaml"))
    ]


def load_person_insights(person_id: str) -> list[Insight]:
    prefix = _person_prefix(person_id)
    return [
        Insight.model_validate(_load_yaml(path))
        for path in sorted((RESEARCH_ROOT / "insight").glob(f"INS-{prefix}-*.yaml"))
    ]


def load_person_role_links(person_id: str) -> list[RoleExperienceLink]:
    try:
        filename = _ROLE_FILE[person_id]
    except KeyError as exc:
        raise ValueError(f"Unsupported first-question candidate: {person_id}") from exc

    data = _load_yaml(RESEARCH_ROOT / "role_links" / filename)
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


def load_first_question_records() -> list[HistoricalRecord]:
    return load_person_records("tang_taizong")


def load_first_question_experiences() -> list[HistoricalExperienceUnit]:
    return load_person_experiences("tang_taizong")


def load_first_question_insights() -> list[Insight]:
    return load_person_insights("tang_taizong")


def load_first_question_role_links() -> list[RoleExperienceLink]:
    return load_person_role_links("tang_taizong")
