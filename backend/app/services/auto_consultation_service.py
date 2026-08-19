from __future__ import annotations

from app.models.api import AutoConsultationResponse, CandidateRanking, ConsultationRequest
from app.services.consultation_service import ConsultationService
from app.services.cross_dynasty_selector import first_fate_question_candidates, rank_candidates


class AutoConsultationService:
    def __init__(self, consultation_service: ConsultationService) -> None:
        self.consultation_service = consultation_service

    @staticmethod
    def _supports(question: str) -> bool:
        normalized = "".join(question.split())
        return "命运" in normalized and ("主宰" in normalized or "谁决定" in normalized)

    def consult(self, request: ConsultationRequest) -> AutoConsultationResponse:
        if not self._supports(request.question):
            raise ValueError("Cross-dynasty auto selection is not yet grounded for this question")

        ranked = rank_candidates(first_fate_question_candidates())
        selected = ranked[0]

        consultation = self.consultation_service.consult(selected.persona_id, request)

        return AutoConsultationResponse(
            selected_emperor_id=selected.persona_id,
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
