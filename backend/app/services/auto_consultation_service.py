from __future__ import annotations

from dataclasses import asdict

from app.models.api import (
    AutoConsultationResponse,
    CandidateRanking,
    CandidateScreening,
    ConsultationRequest,
    ProblemGroundedAnswerResponse,
    ProblemResearchPackageResponse,
)
from app.services.consultation_service import ConsultationService
from app.services.cross_dynasty_selector import (
    first_fate_question_candidates,
    rank_candidates,
    screen_all_han_tang_song_emperors,
)
from app.services.problem_research_package import build_problem_research_package
from app.services.runtime_candidate_assessment import assess_runtime_problem
from app.services.runtime_grounded_answer import render_runtime_grounded_answer


class AutoConsultationService:
    def __init__(self, consultation_service: ConsultationService | None) -> None:
        self.consultation_service = consultation_service

    @staticmethod
    def _supports(question: str) -> bool:
        normalized = "".join(question.split())
        return "命运" in normalized and ("主宰" in normalized or "谁决定" in normalized)

    def consult(
        self, request: ConsultationRequest
    ) -> AutoConsultationResponse | ProblemGroundedAnswerResponse | ProblemResearchPackageResponse:
        """Answer a registered question or run an unseen question through the runtime evidence gate.

        For an unseen question, reviewed reusable knowledge is automatically recalled and scored. If
        the selected candidate passes the automatic evidence gate, a grounded answer is rendered
        without requiring a hand-written Problem file. Otherwise the request safely stops at the
        research package and no responder eligibility is granted.
        """
        if not self._supports(request.question):
            assessment = assess_runtime_problem(request.question)
            if assessment.auto_answer_ready:
                rendered = render_runtime_grounded_answer(request.question)
                return ProblemGroundedAnswerResponse.model_validate(asdict(rendered))

            package = build_problem_research_package(request.question)
            return ProblemResearchPackageResponse.model_validate(asdict(package))

        screened = screen_all_han_tang_song_emperors()
        ranked = rank_candidates(first_fate_question_candidates())
        if not ranked:
            raise ValueError("No reviewed emperor knowledge chain is eligible for this question")
        selected = ranked[0]

        if self.consultation_service is None:
            raise ValueError("Consultation service is required for a reviewed grounded answer")
        consultation = self.consultation_service.consult(selected.persona_id, request)

        return AutoConsultationResponse(
            selected_emperor_id=selected.persona_id,
            screened_emperors=[
                CandidateScreening(
                    emperor_id=item.persona_id,
                    name=item.name,
                    title=item.title,
                    dynasty=item.dynasty,
                    eligible=item.eligible,
                    score=item.total_score,
                    reason=item.reason,
                )
                for item in screened
            ],
            rankings=[
                CandidateRanking(
                    emperor_id=item.persona_id,
                    dynasty=item.dynasty,
                    score=item.total_score,
                    rationale=item.rationale,
                    evidence_ids=list(item.evidence_ids),
                )
                for item in ranked
            ],
            consultation=consultation,
        )
