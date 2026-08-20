from app.models.api import ConsultationRequest, ProblemResearchPackageResponse
from app.services.auto_consultation_service import AutoConsultationService


def test_unseen_question_enters_runtime_problem_research_instead_of_first_question_fallback():
    service = AutoConsultationService(consultation_service=None)  # registered-answer path is not used here
    question = "一个管理者发现团队连续犯同样的错误时，应该先换人还是先改制度？"

    result = service.consult(ConsultationRequest(question=question))

    assert isinstance(result, ProblemResearchPackageResponse)
    assert result.proposed_problem_id.startswith("Q-RESEARCH-")
    assert result.raw_question == question
    assert result.normalized_question == question
    assert result.status == "research_package_requires_human_review"
    assert result.can_render_answer is False
    assert all(candidate.responder_eligible is False for candidate in result.candidates)


def test_unseen_question_runtime_problem_id_is_stable():
    service = AutoConsultationService(consultation_service=None)
    request = ConsultationRequest(question="创业失败以后，是继续原项目还是换一个方向？")

    first = service.consult(request)
    second = service.consult(request)

    assert isinstance(first, ProblemResearchPackageResponse)
    assert isinstance(second, ProblemResearchPackageResponse)
    assert first.proposed_problem_id == second.proposed_problem_id
