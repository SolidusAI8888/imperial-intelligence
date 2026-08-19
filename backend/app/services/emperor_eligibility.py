from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from app.services.cross_dynasty_selector import first_fate_question_candidates


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EMPEROR_REGISTRY_PATH = PROJECT_ROOT / "knowledge" / "personas" / "han_tang_song_emperor_registry.yaml"


@dataclass(frozen=True)
class EmperorEligibility:
    persona_id: str
    dynasty: str
    name: str
    title: str
    eligible: bool
    reason: str


def _load_registry() -> dict:
    with EMPEROR_REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict) or "dynasties" not in data:
        raise ValueError("Invalid Han/Tang/Song emperor registry")
    return data


def all_registered_emperors() -> list[EmperorEligibility]:
    registry = _load_registry()
    eligible_ids = {candidate.persona_id for candidate in first_fate_question_candidates()}
    rows: list[EmperorEligibility] = []

    for dynasty, dynasty_data in registry["dynasties"].items():
        for emperor in dynasty_data["emperors"]:
            persona_id = emperor["persona_id"]
            eligible = persona_id in eligible_ids
            rows.append(
                EmperorEligibility(
                    persona_id=persona_id,
                    dynasty=dynasty,
                    name=emperor["name"],
                    title=emperor["temple_or_posthumous"],
                    eligible=eligible,
                    reason=(
                        "reviewed Q-FATE-AGENCY-001 HER -> HEU -> Insight -> Role Link chain available"
                        if eligible
                        else "Q-FATE-AGENCY-001 reviewed knowledge chain not yet complete"
                    ),
                )
            )

    return rows


def eligibility_summary() -> dict:
    rows = all_registered_emperors()
    by_dynasty: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = by_dynasty.setdefault(row.dynasty, {"registered": 0, "eligible": 0, "remaining": 0})
        bucket["registered"] += 1
        if row.eligible:
            bucket["eligible"] += 1
        else:
            bucket["remaining"] += 1

    return {
        "registered": len(rows),
        "eligible": sum(1 for row in rows if row.eligible),
        "remaining": sum(1 for row in rows if not row.eligible),
        "by_dynasty": by_dynasty,
    }


def assert_candidate_registry_consistency() -> None:
    rows = all_registered_emperors()
    registry_ids = {row.persona_id for row in rows}
    candidate_ids = {candidate.persona_id for candidate in first_fate_question_candidates()}
    missing = sorted(candidate_ids - registry_ids)
    if missing:
        raise ValueError(f"Eligible candidates missing from emperor registry: {missing}")
