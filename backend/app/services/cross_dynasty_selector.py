from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

from app.services.knowledge_repository import (
    load_person_experiences,
    load_person_insights,
    load_person_records,
    load_person_role_links,
)
from app.services.knowledge_runtime import build_runtime_context


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROFILE_PATH = (
    PROJECT_ROOT
    / "knowledge"
    / "research"
    / "R-000001"
    / "candidate"
    / "FATE-AGENCY-CANDIDATES.yaml"
)
ROSTER_PATH = PROJECT_ROOT / "knowledge" / "personas" / "han_tang_song_emperor_registry.yaml"
FIRST_PROBLEM_ID = "Q-FATE-AGENCY-001"
FIRST_QUESTION = "面对浩瀚的历史和剧烈的时代变革，个体的命运到底由谁主宰？"


@dataclass(frozen=True)
class CandidateExperience:
    persona_id: str
    dynasty: str
    evidence_ids: tuple[str, ...]
    experience_similarity: float
    evidence_strength: float
    stage_relevance: float
    lesson_clarity: float
    transferability: float
    counterevidence_quality: float
    rationale: str


@dataclass(frozen=True)
class CandidateScore:
    persona_id: str
    dynasty: str
    total_score: float
    evidence_ids: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class EmperorScreening:
    persona_id: str
    name: str
    title: str
    dynasty: str
    eligible: bool
    total_score: float | None
    reason: str


_WEIGHTS = {
    "experience_similarity": 0.30,
    "evidence_strength": 0.20,
    "stage_relevance": 0.15,
    "lesson_clarity": 0.15,
    "transferability": 0.15,
    "counterevidence_quality": 0.05,
}


def score_candidate(candidate: CandidateExperience) -> CandidateScore:
    total = (
        candidate.experience_similarity * _WEIGHTS["experience_similarity"]
        + candidate.evidence_strength * _WEIGHTS["evidence_strength"]
        + candidate.stage_relevance * _WEIGHTS["stage_relevance"]
        + candidate.lesson_clarity * _WEIGHTS["lesson_clarity"]
        + candidate.transferability * _WEIGHTS["transferability"]
        + candidate.counterevidence_quality * _WEIGHTS["counterevidence_quality"]
    )
    return CandidateScore(
        persona_id=candidate.persona_id,
        dynasty=candidate.dynasty,
        total_score=round(total, 4),
        evidence_ids=candidate.evidence_ids,
        rationale=candidate.rationale,
    )


def rank_candidates(candidates: Iterable[CandidateExperience]) -> list[CandidateScore]:
    ranked = [score_candidate(candidate) for candidate in candidates]
    return sorted(ranked, key=lambda item: (-item.total_score, item.persona_id))


def select_best_candidate(candidates: Iterable[CandidateExperience]) -> CandidateScore:
    ranked = rank_candidates(candidates)
    if not ranked:
        raise ValueError("No eligible historical candidates")
    return ranked[0]


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML mapping: {path}")
    return data


def _load_profile() -> dict:
    data = _load_yaml(PROFILE_PATH)
    if data.get("problem_id") != FIRST_PROBLEM_ID:
        raise ValueError("Invalid first-question candidate profile")
    return data


def _reviewed_candidate(raw: dict) -> CandidateExperience:
    person_id = raw["persona_id"]
    requested_heus = set(raw["heu_ids"])
    requested_insights = set(raw["insight_ids"])

    all_experiences = load_person_experiences(person_id)
    experiences = [heu for heu in all_experiences if heu.heu_id in requested_heus]
    if {heu.heu_id for heu in experiences} != requested_heus:
        raise ValueError(f"Candidate {person_id} references missing HEU data")

    record_ids = {record_id for heu in experiences for record_id in heu.record_links}
    records = [record for record in load_person_records(person_id) if record.record_id in record_ids]
    if {record.record_id for record in records} != record_ids:
        raise ValueError(f"Candidate {person_id} references missing HER data")

    insights = [
        insight
        for insight in load_person_insights(person_id)
        if insight.insight_id in requested_insights
    ]
    if {insight.insight_id for insight in insights} != requested_insights:
        raise ValueError(f"Candidate {person_id} references missing Insight data")

    role_links = [
        link for link in load_person_role_links(person_id) if link.heu_id in requested_heus
    ]

    reviewed_objects = [*records, *experiences, *insights]
    if any(item.status not in {"reviewed", "accepted"} for item in reviewed_objects):
        raise ValueError(f"Candidate {person_id} contains unreviewed knowledge")

    build_runtime_context(
        problem_id=FIRST_PROBLEM_ID,
        question=FIRST_QUESTION,
        person_id=person_id,
        records=records,
        experiences=experiences,
        insights=insights,
        role_links=role_links,
    )

    chain_evidence = {
        canonical_id
        for record in records
        for source in record.sources
        for canonical_id in source.canonical_ids
    }
    declared_evidence = set(raw.get("evidence_ids", []))
    if not declared_evidence.issubset(chain_evidence):
        missing = sorted(declared_evidence - chain_evidence)
        raise ValueError(f"Candidate {person_id} declares evidence outside its HER chain: {missing}")

    scores = raw["scores"]
    return CandidateExperience(
        persona_id=person_id,
        dynasty=raw["dynasty"],
        evidence_ids=tuple(sorted(chain_evidence)),
        experience_similarity=float(scores["experience_similarity"]),
        evidence_strength=float(scores["evidence_strength"]),
        stage_relevance=float(scores["stage_relevance"]),
        lesson_clarity=float(scores["lesson_clarity"]),
        transferability=float(scores["transferability"]),
        counterevidence_quality=float(scores["counterevidence_quality"]),
        rationale=raw["rationale"],
    )


def first_fate_question_candidates() -> list[CandidateExperience]:
    """Return reviewed responders after screening begins from the complete emperor roster."""

    profile = _load_profile()
    return [_reviewed_candidate(raw) for raw in profile["candidates"]]


def screen_all_han_tang_song_emperors() -> list[EmperorScreening]:
    """Screen every registered Han, Tang and Song emperor for this question.

    All emperors are considered. Only emperors with a reviewed HER -> HEU -> Insight -> Role Link
    chain may receive a non-null score or win selection. This prevents fame-based preselection while
    preserving the project's evidence gate.
    """

    roster = _load_yaml(ROSTER_PATH)
    ranked = {item.persona_id: item for item in rank_candidates(first_fate_question_candidates())}
    screened: list[EmperorScreening] = []

    for dynasty, dynasty_data in roster["dynasties"].items():
        for emperor in dynasty_data["emperors"]:
            persona_id = emperor["persona_id"]
            eligible = ranked.get(persona_id)
            if eligible is not None:
                screened.append(
                    EmperorScreening(
                        persona_id=persona_id,
                        name=emperor["name"],
                        title=emperor["temple_or_posthumous"],
                        dynasty=dynasty,
                        eligible=True,
                        total_score=eligible.total_score,
                        reason=eligible.rationale,
                    )
                )
            else:
                screened.append(
                    EmperorScreening(
                        persona_id=persona_id,
                        name=emperor["name"],
                        title=emperor["temple_or_posthumous"],
                        dynasty=dynasty,
                        eligible=False,
                        total_score=None,
                        reason=(
                            "已进入本题全皇帝筛选池，但尚未建立并审核本题所需的 "
                            "HER → HEU → Insight → Role Link 完整知识链，因此当前不能胜出或回答。"
                        ),
                    )
                )

    return screened
