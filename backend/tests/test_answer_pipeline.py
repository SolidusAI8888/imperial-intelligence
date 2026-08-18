from app.services.answer_pipeline import (
    FIRST_PROBLEM_ID,
    FIRST_QUESTION,
    build_first_question_context,
    generate_first_question_answer,
)


def test_first_question_context_loads_reviewed_chain() -> None:
    context = build_first_question_context()

    assert context.problem_id == FIRST_PROBLEM_ID
    assert context.question == FIRST_QUESTION
    assert context.person_id == "tang_taizong"
    assert context.life_course_rule == "full_lifetime"
    assert len(context.records) == 5
    assert len(context.experiences) == 3
    assert len(context.insights) == 2
    assert len(context.role_links) == 3


def test_first_question_answer_is_grounded_and_first_person() -> None:
    result = generate_first_question_answer()

    assert result.problem_id == FIRST_PROBLEM_ID
    assert result.person_id == "tang_taizong"
    assert "我亲历草创，也亲历守成" in result.answer
    assert "朕闻过矣" in result.answer
    assert "犯而无隐" in result.answer
    assert "人不能主宰全部命运" in result.answer
    assert "CN-TANG-0004-V001-P0003" in result.evidence_ids
    assert "HEU-TANG-000001" in result.grounded_context
    assert "INS-TANG-000001" in result.grounded_context


def test_first_question_answer_preserves_current_scope_limit() -> None:
    result = generate_first_question_answer()
    assert any("尚未完成汉、宋反例" in caution for caution in result.cautions)
