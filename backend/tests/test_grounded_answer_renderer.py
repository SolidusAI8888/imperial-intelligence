import pytest

from app.services.grounded_answer_renderer import render_grounded_answer


FIRST_PROBLEM_ID = "Q-FATE-AGENCY-001"


def test_renderer_uses_reviewed_selected_responder() -> None:
    answer = render_grounded_answer(FIRST_PROBLEM_ID)
    assert answer.person_id == "tang_taizong"
    assert answer.evidence_ids
    assert answer.insight_ids
    assert answer.historical_voice
    assert answer.modern_translation
    assert answer.status == "rendered_from_reviewed_grounded_bundle"


def test_renderer_keeps_evidence_metadata_out_of_historical_voice() -> None:
    answer = render_grounded_answer(FIRST_PROBLEM_ID)
    assert "CN-" not in answer.historical_voice
    assert "《旧唐书》" not in answer.historical_voice
    assert "《新唐书》" not in answer.historical_voice
    assert "《贞观政要》" not in answer.historical_voice


def test_renderer_does_not_invent_direct_quote_markers() -> None:
    answer = render_grounded_answer(FIRST_PROBLEM_ID)
    assert "朕曰" not in answer.historical_voice
    assert "我曾说" not in answer.historical_voice
    assert "据《" not in answer.historical_voice


def test_unknown_problem_cannot_be_rendered() -> None:
    with pytest.raises(KeyError):
        render_grounded_answer("Q-UNREVIEWED-NEW-PROBLEM")
