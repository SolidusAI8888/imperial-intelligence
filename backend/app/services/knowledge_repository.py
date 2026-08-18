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


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_first_question_records() -> list[HistoricalRecord]:
    her_dir = RESEARCH_ROOT / "her"
    return [
        HistoricalRecord.model_validate(_load_yaml(path))
        for path in sorted(her_dir.glob("HER-TANG-*.yaml"))
    ]


def load_first_question_experiences() -> list[HistoricalExperienceUnit]:
    heu_dir = RESEARCH_ROOT / "heu"
    return [
        HistoricalExperienceUnit.model_validate(_load_yaml(path))
        for path in sorted(heu_dir.glob("HEU-TANG-*.yaml"))
    ]


def load_first_question_insights() -> list[Insight]:
    insight_dir = RESEARCH_ROOT / "insight"
    return [
        Insight.model_validate(_load_yaml(path))
        for path in sorted(insight_dir.glob("INS-TANG-*.yaml"))
    ]


def load_first_question_role_links() -> list[RoleExperienceLink]:
    data = _load_yaml(RESEARCH_ROOT / "role_links" / "ROLE-TANG-TAIZONG.yaml")
    person_id = data["person_id"]
    life_course_rule = data.get("life_course_rule", "full_lifetime")
    links = []
    for raw in data["links"]:
        links.append(
            RoleExperienceLink(
                person_id=person_id,
                heu_id=raw["heu_id"],
                relation=raw["relation"],
                responder_eligible=raw["responder_eligible"],
                personal_experience_strength=raw["personal_experience_strength"],
                life_course_rule=life_course_rule,
            )
        )
    return links
