from types import SimpleNamespace

from app.models.api import ConsultationRequest, ProblemGroundedAnswerResponse
from app.services.auto_consultation_service import AutoConsultationService
from app.services.persona_voice_evidence import PersonaVoiceProfile
from app.services.runtime_candidate_assessment import RuntimeProblemAssessment
from app.services.runtime_grounded_answer import (
    RuntimeRenderedGroundedAnswer,
    render_runtime_grounded_answer,
)


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


def test_runtime_renderer_applies_audited_voice_profile_without_using_it_as_fact(
    monkeypatch,
) -> None:
    question = "团队应该如何面对反复出现的问题？"
    context = SimpleNamespace(
        problem_id="Q-RESEARCH-0123456789ABCDEF",
        person_id="tang_taizong",
        experiences=(),
        insights=(SimpleNamespace(statement="先查明可验证的原因，再决定行动。"),),
    )
    profile = PersonaVoiceProfile(
        person_id="tang_taizong",
        voice_evidence_ids=("PVC-TANG-0001", "PVC-TANG-0002"),
        voice_features=("direct",),
        decision_features=("demands_specifics",),
        rhetoric_features=(),
        evidence_count=2,
        distinct_passage_count=2,
        distinct_source_count=1,
        total_evidence_weight=1.9,
        runtime_style_ready=True,
    )
    monkeypatch.setattr(
        "app.services.runtime_grounded_answer._build_runtime_context",
        lambda anchor, candidate_limit=20: (context, ("E-1", "E-2"), ("I-1",), profile),
    )

    answer = render_runtime_grounded_answer(question)

    assert answer.historical_voice.startswith("先说要害")
    assert "先查明可验证的原因" in answer.historical_voice
    assert answer.voice_evidence_ids == ("PVC-TANG-0001", "PVC-TANG-0002")
    assert answer.evidence_ids == ("E-1", "E-2")
