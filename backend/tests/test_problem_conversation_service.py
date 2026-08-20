from types import SimpleNamespace

from app.services.problem_conversation_service import continue_problem_conversation


def _spec():
    return SimpleNamespace(
        raw_question="一个人在职业低谷时，是应该坚持原来的方向，还是及时改变？",
        normalized_question="职业低谷中的坚持与转向",
        retrieval_dimensions=("职业低谷", "坚持", "改变方向", "处境判断"),
    )


def test_related_followup_keeps_current_responder(monkeypatch):
    monkeypatch.setattr(
        "app.services.problem_conversation_service.load_problem_spec", lambda _: _spec()
    )
    answer = SimpleNamespace(
        person_id="tang_taizong",
        historical_voice="reviewed answer",
        modern_translation="modern",
        cautions=("bounded",),
        evidence_ids=("E-1",),
        insight_ids=("I-1",),
    )
    monkeypatch.setattr(
        "app.services.problem_conversation_service.render_grounded_answer",
        lambda problem_id, question=None: answer,
    )

    result = continue_problem_conversation(
        "Q-CAREER-001",
        "但是你刚才说要改变方向，具体什么时候才应该改变？",
        conversation_history=("我现在处于职业低谷。", "先判断约束和机会。"),
    )

    assert result.route == "continue_current_responder"
    assert result.person_id == "tang_taizong"
    assert result.requires_new_problem is False
    assert result.evidence_ids == ("E-1",)


def test_materially_new_question_requires_new_problem(monkeypatch):
    monkeypatch.setattr(
        "app.services.problem_conversation_service.load_problem_spec", lambda _: _spec()
    )

    result = continue_problem_conversation(
        "Q-CAREER-001",
        "宋代的财政制度如何设计？",
        continuity_threshold=0.30,
    )

    assert result.route == "new_problem_required"
    assert result.person_id is None
    assert result.requires_new_problem is True
    assert result.historical_voice is None


def test_empty_followup_rejected(monkeypatch):
    monkeypatch.setattr(
        "app.services.problem_conversation_service.load_problem_spec", lambda _: _spec()
    )
    try:
        continue_problem_conversation("Q-CAREER-001", " ")
    except ValueError as exc:
        assert "at least two" in str(exc)
    else:
        raise AssertionError("expected short follow-up to fail")
