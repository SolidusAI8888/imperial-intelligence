from app.models.api import ConsultationRequest, ProblemResearchPackageResponse
from app.services.auto_consultation_service import AutoConsultationService


def test_runtime_problem_builder_exposes_recalled_candidates_when_available():
    service = AutoConsultationService(consultation_service=None)
    result = service.consult(ConsultationRequest(question="一个人在职业低谷时应该坚持还是改变方向？"))

    assert isinstance(result, ProblemResearchPackageResponse)
    assert result.candidates
    assert all(candidate.heu_ids for candidate in result.candidates)
    scores = [candidate.retrieval_score for candidate in result.candidates]
    assert scores == sorted(scores, reverse=True)
