from __future__ import annotations

from dataclasses import dataclass

from app.services.cross_dynasty_selector import CandidateExperience, score_candidate
from app.services.knowledge_repository import (
    load_person_experiences,
    load_person_insights,
    load_person_records,
    load_person_role_links,
)
from app.services.problem_research_package import build_problem_research_package


_REVIEWED = {"reviewed", "accepted"}
_ROLE_STRENGTH = {
    "none": 0.0,
    "weak": 0.3,
    "medium": 0.55,
    "strong": 0.8,
    "primary": 1.0,
}


@dataclass(frozen=True)
class RuntimeCandidateAssessment:
    person_id: str
    retrieval_score: float
    candidate_score: float
    evidence_ids: tuple[str, ...]
    heu_ids: tuple[str, ...]
    insight_ids: tuple[str, ...]
    recommended_eligible: bool
    auto_answer_ready: bool
    rationale: str


@dataclass(frozen=True)
class RuntimeProblemAssessment:
    problem_id: str
    question: str
    candidates: tuple[RuntimeCandidateAssessment, ...]
    selected_person_id: str | None
    auto_answer_ready: bool
    status: str


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def assess_runtime_problem(question: str, *, candidate_limit: int = 20) -> RuntimeProblemAssessment:
    """Automatically assess an unregistered problem using only reviewed knowledge.

    This stage is advisory and deterministic: it computes problem-aware candidate scores and an
    eligibility recommendation from recalled reviewed HER/HEU/Insight/role-link chains. It does not
    mutate reviewed Problem files or grant answer permission by itself.
    """
    research = build_problem_research_package(question, candidate_limit=candidate_limit)
    assessed: list[RuntimeCandidateAssessment] = []

    for recalled in research.candidates:
        person_id = recalled.person_id
        recalled_heu_ids = set(recalled.heu_ids)
        heus = [
            heu
            for heu in load_person_experiences(person_id)
            if heu.heu_id in recalled_heu_ids and heu.status in _REVIEWED
        ]
        if not heus:
            continue

        heu_ids = {heu.heu_id for heu in heus}
        insights = [
            insight
            for insight in load_person_insights(person_id)
            if insight.status in _REVIEWED
            and insight.derived_from_heus
            and set(insight.derived_from_heus).issubset(heu_ids)
        ]

        record_ids = {record_id for heu in heus for record_id in heu.record_links}
        records = [
            record
            for record in load_person_records(person_id)
            if record.record_id in record_ids and record.status in _REVIEWED
        ]
        canonical_ids = sorted(
            {
                canonical_id
                for record in records
                for source in record.sources
                for canonical_id in source.canonical_ids
            }
        )

        role_links = [
            link
            for link in load_person_role_links(person_id)
            if link.heu_id in heu_ids and link.responder_eligible
        ]
        role_relevance = max(
            (_ROLE_STRENGTH.get(link.personal_experience_strength, 0.0) for link in role_links),
            default=0.0,
        )

        dynasties = {record.dynasty for record in records if record.dynasty and record.dynasty != "Unknown"}
        dynasty = next(iter(dynasties)) if len(dynasties) == 1 else "Unknown"

        experience_similarity = _clamp(recalled.retrieval_score)
        evidence_strength = _clamp(0.4 + 0.08 * len(records) + 0.04 * len(canonical_ids))
        lesson_clarity = _clamp(
            0.35
            + 0.08 * sum(bool(heu.explicit_reflection) for heu in heus)
            + 0.05 * sum(bool(heu.interpretation) for heu in heus)
            + 0.06 * len(insights)
        )
        transferability = _clamp(
            0.35 + 0.08 * len(insights) + 0.03 * sum(len(insight.applies_when) for insight in insights)
        )
        counterevidence_quality = _clamp(
            0.3 + 0.15 * sum(bool(insight.limits) for insight in insights)
        )

        rationale = (
            f"automatic assessment from {len(heus)} reviewed HEU(s), {len(records)} reviewed HER(s), "
            f"{len(insights)} reviewed Insight(s), {len(canonical_ids)} canonical evidence id(s), "
            f"and {len(role_links)} eligible role link(s)"
        )
        scored = score_candidate(
            CandidateExperience(
                persona_id=person_id,
                dynasty=dynasty,
                evidence_ids=tuple(canonical_ids),
                experience_similarity=experience_similarity,
                evidence_strength=evidence_strength,
                stage_relevance=_clamp(role_relevance),
                lesson_clarity=lesson_clarity,
                transferability=transferability,
                counterevidence_quality=counterevidence_quality,
                rationale=rationale,
            )
        )

        chain_complete = bool(records and canonical_ids and insights and role_links and dynasty != "Unknown")
        recommended = bool(chain_complete and recalled.retrieval_score >= 0.35 and scored.total_score >= 0.6)
        answer_ready = bool(
            recommended
            and scored.total_score >= 0.72
            and len(canonical_ids) >= 2
            and len(insights) >= 1
        )
        assessed.append(
            RuntimeCandidateAssessment(
                person_id=person_id,
                retrieval_score=recalled.retrieval_score,
                candidate_score=scored.total_score,
                evidence_ids=tuple(canonical_ids),
                heu_ids=tuple(sorted(heu_ids)),
                insight_ids=tuple(sorted(insight.insight_id for insight in insights)),
                recommended_eligible=recommended,
                auto_answer_ready=answer_ready,
                rationale=rationale,
            )
        )

    assessed.sort(key=lambda item: (-item.candidate_score, -item.retrieval_score, item.person_id))
    selected = next((item for item in assessed if item.recommended_eligible), None)
    ready = bool(selected and selected.auto_answer_ready)
    return RuntimeProblemAssessment(
        problem_id=research.proposed_problem_id,
        question=research.normalized_question,
        candidates=tuple(assessed),
        selected_person_id=selected.person_id if selected else None,
        auto_answer_ready=ready,
        status=(
            "automatic_candidate_selected_evidence_gate_ready"
            if ready
            else "automatic_assessment_complete_evidence_gate_not_ready"
        ),
    )
