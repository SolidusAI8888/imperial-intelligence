from app.models.api import ConsultationRequest, ProblemGroundedAnswerResponse
from app.services.auto_consultation_service import AutoConsultationService
from app.services.runtime_candidate_assessment import RuntimeProblemAssessment
from app.services.runtime_grounded_answer import RuntimeRenderedGroundedAnswer


def test_unseen_question_renders_when_runtime_evidence_gate_is_ready(monkeypatch) -> None:
    question = "团队连续犯同样的错误时，应该先换人还是先改制度？"

    monkeypatch.setattr(
        "app.services.auto_consultation_service.assess_runtime_problem",
        lambda _question: RuntimeProblemAssessment(
            problem_id="Q-RESEARCH-0123456789ABCDEF",
            question=question,
            candidates=(),
            selected_person_id="tang_taizong",
            auto_answer_ready=True,
            status="automatic_candidate_selected_evidence_gate_ready",
        ),
    )
    monkeypatch.setattr(
        "app.services.auto_consultation_service.render_runtime_grounded_answer",
        lambda _question: RuntimeRenderedGroundedAnswer(
            problem_id="Q-RESEARCH-0123456789ABCDEF",
            person_id="tang_taizong",
            question=question,
            historical_voice="reviewed historical voice",
            modern_translation="bounded modern transfer",
            cautions=("evidence bounded",),
            evidence_ids=("CN-TANG-0001-V001-P0001", "CN-TANG-0002-V001-P0001"),
            insight_ids=("INS-TANG-TAIZONG-001",),
            status="rendered_from_runtime_reviewed_grounded_bundle",
        ),
    )

    service = AutoConsultationService(consultation_service=None)
    result = service.consult(ConsultationRequest(question=question))

    assert isinstance(result, ProblemGroundedAnswerResponse)
    assert result.problem_id == "Q-RESEARCH-0123456789ABCDEF"
    assert result.person_id == "tang_taizong"
    assert result.status == "rendered_from_runtime_reviewed_grounded_bundle"
    assert len(result.evidence_ids) == 2
    assert result.insight_ids == ["INS-TANG-TAIZONG-001"]


def test_unseen_question_still_stops_at_research_when_evidence_gate_is_not_ready(monkeypatch) -> None:
    question = "如果完全没有相关历史经验，系统应该怎么办？"

    monkeypatch.setattr(
        "app.services.auto_consultation_service.assess_runtime_problem",
        lambda _question: RuntimeProblemAssessment(
            problem_id="Q-RESEARCH-FEDCBA9876543210",
            question=question,
            candidates=(),
            selected_person_id=None,
            auto_answer_ready=False,
            status="automatic_assessment_complete_evidence_gate_not_ready",
        ),
    )

    service = AutoConsultationService(consultation_service=None)
    result = service.consult(ConsultationRequest(question=question))

    assert result.status == "research_package_requires_human_review"
    assert result.can_render_answer is False
