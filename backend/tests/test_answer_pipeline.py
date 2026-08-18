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
    assert len(context.records) == 6
    assert len(context.experiences) == 3
    assert len(context.insights) == 2
    assert len(context.role_links) == 3


def test_first_question_answer_is_grounded_and_first_person() -> None:
    result = generate_first_question_answer()

    assert result.problem_id == FIRST_PROBLEM_ID
    assert result.person_id == "tang_taizong"
    assert "朕少年逢隋末乱世" in result.answer
    assert "《旧唐书》《新唐书》皆记此事" in result.answer
    assert "朕闻过矣" in result.answer
    assert "犯而无隐" in result.answer
    assert "人不能主宰全部命运" in result.answer
    assert "CN-TANG-0001-V002-P0004" in result.evidence_ids
    assert "CN-TANG-0002-V002-P0004" in result.evidence_ids
    assert "CN-TANG-0004-V001-P0003" in result.evidence_ids
    assert "HEU-TANG-000001" in result.grounded_context
    assert "INS-TANG-000001" in result.grounded_context


def test_answer_keeps_modern_generalization_out_of_persona_voice() -> None:
    result = generate_first_question_answer()

    assert "不能控制所有制度、资源和偶然" not in result.answer
    assert "真正值得经营" not in result.answer
    assert len(result.reasoning) == 3
    assert any("阶段变化" in item for item in result.reasoning)
    assert any("纠错机制" in item for item in result.reasoning)
    assert any("综合边界" in item for item in result.reasoning)


def test_first_question_answer_preserves_current_scope_limit() -> None:
    result = generate_first_question_answer()
    assert any("《资治通鉴》相关交叉验证尚未纳入" in caution for caution in result.cautions)
