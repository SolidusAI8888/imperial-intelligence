from __future__ import annotations

from dataclasses import dataclass

from app.services.knowledge_repository import load_person_voice_evidence
from app.services.persona_voice_evidence import build_persona_voice_profile
from app.services.runtime_candidate_assessment import assess_runtime_problem


@dataclass(frozen=True)
class RuntimeCandidateExplanation:
    rank: int
    person_id: str
    retrieval_score: float
    candidate_score: float
    recommended_eligible: bool
    auto_answer_ready: bool
    evidence_ids: tuple[str, ...]
    heu_ids: tuple[str, ...]
    insight_ids: tuple[str, ...]
    conflicting_insight_ids: tuple[str, ...]
    voice_evidence_ids: tuple[str, ...]
    gate_blockers: tuple[str, ...]
    selection_reason: str


@dataclass(frozen=True)
class RuntimeProblemExplanation:
    problem_id: str
    question: str
    selected_person_id: str | None
    auto_answer_ready: bool
    candidates: tuple[RuntimeCandidateExplanation, ...]
    decision_summary: str
    status: str


def _gate_blockers(candidate) -> tuple[str, ...]:
    blockers: list[str] = []
    if candidate.retrieval_score < 0.35:
        blockers.append("retrieval_score_below_0.35")
    if candidate.candidate_score < 0.60:
        blockers.append("candidate_score_below_0.60")
    if not candidate.evidence_ids:
        blockers.append("missing_reviewed_canonical_evidence")
    elif len(candidate.evidence_ids) < 2:
        blockers.append("fewer_than_2_canonical_evidence_ids")
    if not candidate.insight_ids:
        blockers.append("missing_reviewed_problem_relevant_insight")
    if candidate.conflicting_insight_ids:
        blockers.append("reviewed_counterevidence_conflicts_with_problem")
    if not candidate.recommended_eligible:
        blockers.append("responder_eligibility_gate_not_met")
    elif candidate.candidate_score < 0.72:
        blockers.append("auto_answer_score_below_0.72")
    return tuple(blockers)


def _voice_evidence_ids(person_id: str) -> tuple[str, ...]:
    profile = build_persona_voice_profile(
        person_id, load_person_voice_evidence(person_id)
    )
    return profile.applied_voice_evidence_ids if profile else ()


def explain_runtime_problem(question: str, *, candidate_limit: int = 20) -> RuntimeProblemExplanation:
    assessment = assess_runtime_problem(question, candidate_limit=candidate_limit)
    explanations = tuple(
        RuntimeCandidateExplanation(
            rank=index, person_id=candidate.person_id, retrieval_score=candidate.retrieval_score,
            candidate_score=candidate.candidate_score, recommended_eligible=candidate.recommended_eligible,
            auto_answer_ready=candidate.auto_answer_ready, evidence_ids=candidate.evidence_ids,
            heu_ids=candidate.heu_ids, insight_ids=candidate.insight_ids,
            conflicting_insight_ids=candidate.conflicting_insight_ids,
            voice_evidence_ids=_voice_evidence_ids(candidate.person_id),
            gate_blockers=_gate_blockers(candidate),
            selection_reason=(
                "selected as the highest-ranked evidence-gated responder"
                if candidate.person_id == assessment.selected_person_id
                else "not selected; ranked below the selected responder or failed an evidence gate"
            ),
        ) for index, candidate in enumerate(assessment.candidates, start=1)
    )
    if assessment.selected_person_id and assessment.auto_answer_ready:
        summary = f"Selected {assessment.selected_person_id}: the highest-ranked eligible candidate also passed the stricter automatic-answer evidence gate."
    elif assessment.selected_person_id:
        summary = f"Candidate {assessment.selected_person_id} is recommended eligible, but the automatic answer gate is not ready; no runtime answer should be rendered."
    else:
        summary = "No candidate passed the responder eligibility gate; runtime must remain in research mode."
    return RuntimeProblemExplanation(
        problem_id=assessment.problem_id, question=assessment.question,
        selected_person_id=assessment.selected_person_id, auto_answer_ready=assessment.auto_answer_ready,
        candidates=explanations, decision_summary=summary, status="runtime_selection_explanation_read_only",
    )
