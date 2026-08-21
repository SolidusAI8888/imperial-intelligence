from __future__ import annotations

from dataclasses import dataclass
import re

from app.services.cross_dynasty_selector import CandidateExperience, score_candidate
from app.services.knowledge_repository import (
    load_person_experiences,
    load_person_insights,
    load_person_records,
    load_person_role_links,
)
from app.services.problem_research_package import build_problem_research_package


_REVIEWED = {"reviewed", "accepted"}
_ROLE_STRENGTH = {"none": 0.0, "weak": 0.3, "medium": 0.55, "strong": 0.8, "primary": 1.0}
_CJK_RE = re.compile(r"[\u3400-\u9fff]+")
_LATIN_RE = re.compile(r"[A-Za-z0-9_]+")
_NONINFORMATIVE_CJK_TERMS = {
    "一个", "个人", "时候", "如果", "因为", "所以", "但是", "还是", "是否",
    "应该", "应该先", "该先", "可以", "需要", "如何", "怎么", "怎样", "什么", "问题", "事情",
    "自己", "他们", "我们", "这个", "那个", "进行", "面对", "已经", "可能",
}


@dataclass(frozen=True)
class RuntimeCandidateAssessment:
    person_id: str
    retrieval_score: float
    candidate_score: float
    evidence_ids: tuple[str, ...]
    heu_ids: tuple[str, ...]
    insight_ids: tuple[str, ...]
    conflicting_insight_ids: tuple[str, ...]
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


def _relevance_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for span in _CJK_RE.findall(text):
        for size in (2, 3):
            if len(span) >= size:
                terms.update(span[i : i + size] for i in range(len(span) - size + 1))
    terms.difference_update(_NONINFORMATIVE_CJK_TERMS)
    terms.update(token.lower() for token in _LATIN_RE.findall(text))
    return terms


def _insight_relevant_to_question(question: str, insight: object) -> bool:
    query_terms = _relevance_terms(question)
    if not query_terms:
        return False
    positive_text = " ".join([getattr(insight, "statement", ""), *getattr(insight, "applies_when", ())])
    return bool(query_terms & _relevance_terms(positive_text))


def _insight_conflicts_with_question(question: str, insight: object) -> bool:
    query_terms = _relevance_terms(question)
    if not query_terms:
        return False
    limits_text = " ".join(getattr(insight, "limits", ()))
    return bool(limits_text and query_terms & _relevance_terms(limits_text))


def _partition_problem_insights(question: str, insights: list[object] | tuple[object, ...]) -> tuple[list[object], list[object]]:
    # Counterevidence is intentionally evaluated independently from positive relevance.
    # A reviewed Insight may be about another context while its limits explicitly say
    # that the current problem is outside its safe transfer boundary. Silently dropping
    # such a limit would allow supporting evidence to overrule known reviewed caution.
    conflicting = [insight for insight in insights if _insight_conflicts_with_question(question, insight)]
    conflicting_ids = {getattr(insight, "insight_id", id(insight)) for insight in conflicting}
    supporting = [
        insight for insight in insights
        if _insight_relevant_to_question(question, insight)
        and getattr(insight, "insight_id", id(insight)) not in conflicting_ids
    ]
    return supporting, conflicting


def _has_independent_record_support(records: list[object] | tuple[object, ...]) -> bool:
    """Automatic answers require support from at least two reviewed HER objects.

    Multiple canonical passages attached to one HER are useful traceability, but they
    do not constitute independent historical-record support. Keeping this distinction
    at the final answer gate prevents one synthesized record from satisfying the
    apparent evidence-count requirement by carrying several citations.
    """
    record_ids = {getattr(record, "record_id", "") for record in records}
    record_ids.discard("")
    return len(record_ids) >= 2


def _select_runtime_candidate(candidates: list[RuntimeCandidateAssessment] | tuple[RuntimeCandidateAssessment, ...]) -> RuntimeCandidateAssessment | None:
    answer_ready = next((item for item in candidates if item.auto_answer_ready), None)
    if answer_ready is not None:
        return answer_ready
    return next((item for item in candidates if item.recommended_eligible), None)


def assess_runtime_problem(question: str, *, candidate_limit: int = 20) -> RuntimeProblemAssessment:
    research = build_problem_research_package(question, candidate_limit=candidate_limit)
    assessed: list[RuntimeCandidateAssessment] = []
    for recalled in research.candidates:
        person_id = recalled.person_id
        recalled_heu_ids = set(recalled.heu_ids)
        heus = [heu for heu in load_person_experiences(person_id) if heu.heu_id in recalled_heu_ids and heu.status in _REVIEWED]
        if not heus:
            continue
        heu_ids = {heu.heu_id for heu in heus}
        derived_insights = [
            insight for insight in load_person_insights(person_id)
            if insight.status in _REVIEWED and insight.derived_from_heus and set(insight.derived_from_heus).issubset(heu_ids)
        ]
        insights, conflicting_insights = _partition_problem_insights(research.normalized_question, derived_insights)
        required_record_ids = {record_id for heu in heus for record_id in heu.record_links}
        records = [record for record in load_person_records(person_id) if record.record_id in required_record_ids and record.status in _REVIEWED]
        loaded_record_ids = {record.record_id for record in records}
        canonical_ids = sorted({canonical_id for record in records for source in record.sources for canonical_id in source.canonical_ids})
        role_links = [link for link in load_person_role_links(person_id) if link.heu_id in heu_ids and link.responder_eligible]
        role_relevance = max((_ROLE_STRENGTH.get(link.personal_experience_strength, 0.0) for link in role_links), default=0.0)
        dynasties = {record.dynasty for record in records if record.dynasty and record.dynasty != "Unknown"}
        dynasty = next(iter(dynasties)) if len(dynasties) == 1 else "Unknown"
        evidence_strength = _clamp(0.4 + 0.08 * len(records) + 0.04 * len(canonical_ids))
        lesson_clarity = _clamp(0.35 + 0.08 * sum(bool(heu.explicit_reflection) for heu in heus) + 0.05 * sum(bool(heu.interpretation) for heu in heus) + 0.06 * len(insights))
        transferability = _clamp(0.35 + 0.08 * len(insights) + 0.03 * sum(len(insight.applies_when) for insight in insights))
        counterevidence_quality = _clamp(0.3 + 0.15 * sum(bool(insight.limits) for insight in insights) + 0.2 * bool(conflicting_insights))
        rationale = (
            f"automatic assessment from {len(heus)} reviewed HEU(s), {len(records)} reviewed HER(s), "
            f"{len(insights)} problem-relevant reviewed supporting Insight(s), {len(conflicting_insights)} directly conflicting reviewed Insight(s) out of "
            f"{len(derived_insights)} derived Insight(s), {len(canonical_ids)} canonical evidence id(s), and {len(role_links)} eligible role link(s)"
        )
        scored = score_candidate(CandidateExperience(
            persona_id=person_id, dynasty=dynasty, evidence_ids=tuple(canonical_ids),
            experience_similarity=_clamp(recalled.retrieval_score), evidence_strength=evidence_strength,
            stage_relevance=_clamp(role_relevance), lesson_clarity=lesson_clarity,
            transferability=transferability, counterevidence_quality=counterevidence_quality, rationale=rationale,
        ))
        all_required_records_reviewed = bool(required_record_ids) and required_record_ids == loaded_record_ids
        chain_complete = bool(all_required_records_reviewed and canonical_ids and insights and role_links and dynasty != "Unknown")
        recommended = bool(chain_complete and recalled.retrieval_score >= 0.35 and scored.total_score >= 0.6)
        independent_record_support = _has_independent_record_support(records)
        answer_ready = bool(
            recommended and not conflicting_insights and scored.total_score >= 0.72
            and len(canonical_ids) >= 2 and independent_record_support and len(insights) >= 1
        )
        assessed.append(RuntimeCandidateAssessment(
            person_id=person_id, retrieval_score=recalled.retrieval_score, candidate_score=scored.total_score,
            evidence_ids=tuple(canonical_ids), heu_ids=tuple(sorted(heu_ids)),
            insight_ids=tuple(sorted(insight.insight_id for insight in insights)),
            conflicting_insight_ids=tuple(sorted(insight.insight_id for insight in conflicting_insights)),
            recommended_eligible=recommended, auto_answer_ready=answer_ready, rationale=rationale,
        ))
    assessed.sort(key=lambda item: (-item.candidate_score, -item.retrieval_score, item.person_id))
    selected = _select_runtime_candidate(assessed)
    ready = bool(selected and selected.auto_answer_ready)
    return RuntimeProblemAssessment(
        problem_id=research.proposed_problem_id, question=research.normalized_question, candidates=tuple(assessed),
        selected_person_id=selected.person_id if selected else None, auto_answer_ready=ready,
        status="automatic_candidate_selected_evidence_gate_ready" if ready else "automatic_assessment_complete_evidence_gate_not_ready",
    )
