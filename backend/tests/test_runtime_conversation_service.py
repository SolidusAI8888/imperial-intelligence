from app.services.problem_research_package import provisional_problem_id
from app.services.runtime_candidate_assessment import RuntimeProblemAssessment
from app.services.runtime_conversation_service import continue_runtime_conversation
from app.services.runtime_grounded_answer import RuntimeRenderedGroundedAnswer


def _assessment(question: str, person_id: str = "tang_taizong", ready: bool = True) -> RuntimeProblemAssessment:
    return RuntimeProblemAssessment(
        problem_id=provisional_problem_id(question),
        question=question,
        candidates=(),
        selected_person_id=person_id if ready else None,
        auto_answer_ready=ready,
        status="test",
    )


def _answer(question: str, problem_id: str, person_id: str = "tang_taizong") -> RuntimeRenderedGroundedAnswer:
    return RuntimeRenderedGroundedAnswer(
        problem_id=problem_id,
        person_id=person_id,
        question=question,
        historical_voice="grounded",
        modern_translation="bounded",
        cautions=("bounded",),
        evidence_ids=("E1",),
        insight_ids=("I1",),
        status="rendered_from_runtime_reviewed_grounded_bundle",
    )


def test_related_runtime_followup_reuses_anchor_bundle(monkeypatch) -> None:
    anchor = "团队连续犯同样的错误时，应该先换人还是先改制度？"
    followup = "你刚才说的制度具体应该怎么改？"
    pid = provisional_problem_id(anchor)
    monkeypatch.setattr("app.services.runtime_conversation_service.assess_runtime_problem", lambda q, candidate_limit=20: _assessment(q))
    monkeypatch.setattr("app.services.runtime_conversation_service.render_runtime_grounded_answer", lambda q, anchor_question=None, candidate_limit=20: _answer(q, provisional_problem_id(anchor_question or q)))

    result = continue_runtime_conversation(pid, anchor, followup, previous_person_id="tang_taizong")

    assert result.route == "continue_current_runtime_responder"
    assert result.active_problem_id == pid
    assert result.person_id == "tang_taizong"
    assert result.responder_switched is False
    assert result.status == "continued_with_runtime_grounded_responder"


def test_runtime_drift_runs_fresh_selection_and_can_switch_responder(monkeypatch) -> None:
    anchor = "团队连续犯同样的错误时，应该先换人还是先改制度？"
    followup = "国家刚结束长期战争后应该先减税还是继续扩军？"
    pid = provisional_problem_id(anchor)

    def assess(q: str, candidate_limit: int = 20):
        return _assessment(q, "tang_taizong" if q == anchor else "han_wendi")

    monkeypatch.setattr("app.services.runtime_conversation_service.assess_runtime_problem", assess)
    monkeypatch.setattr("app.services.runtime_conversation_service.render_runtime_grounded_answer", lambda q, anchor_question=None, candidate_limit=20: _answer(q, provisional_problem_id(q), "han_wendi"))

    result = continue_runtime_conversation(pid, anchor, followup, previous_person_id="tang_taizong")

    assert result.route == "drift_reselected_runtime_responder"
    assert result.active_problem_id == provisional_problem_id(followup)
    assert result.person_id == "han_wendi"
    assert result.responder_switched is True
    assert result.status == "runtime_problem_drift_reselected_and_answered"


def test_runtime_problem_id_must_match_anchor_question() -> None:
    try:
        continue_runtime_conversation("Q-RESEARCH-0000000000000000", "原始问题是什么？", "你刚才是什么意思？")
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("expected ValueError")
