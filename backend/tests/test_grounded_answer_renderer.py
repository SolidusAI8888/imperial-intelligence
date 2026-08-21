import pytest

from app.services.grounded_answer_renderer import render_grounded_answer
from app.services.persona_voice_evidence import parse_persona_voice_evidence


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


def test_renderer_applies_only_reviewed_selected_person_voice_metadata(monkeypatch) -> None:
    evidence = parse_persona_voice_evidence(
        {
            "voice_evidence_id": "PVC-TANG-0001",
            "person_id": "tang_taizong",
            "source_id": "CN-TANG-0004",
            "passage_id": "CN-TANG-0004-P000001",
            "source_kind": "imperial_verbatim",
            "contemporaneous": True,
            "text": "This reviewed source text must not be copied into the answer.",
            "voice_features": ["direct", "terse"],
            "decision_features": ["requests_counterargument"],
            "rhetoric_features": ["asks_questions"],
            "confidence": 0.95,
            "status": "reviewed",
        }
    )
    corroborating = parse_persona_voice_evidence(
        {
            "voice_evidence_id": "PVC-TANG-0002",
            "person_id": "tang_taizong",
            "source_id": "CN-TANG-0004",
            "passage_id": "CN-TANG-0004-P000002",
            "source_kind": "imperial_verbatim",
            "contemporaneous": True,
            "text": "A separate reviewed passage that must not be copied either.",
            "voice_features": ["direct", "terse"],
            "decision_features": ["requests_counterargument"],
            "rhetoric_features": ["asks_questions"],
            "confidence": 0.90,
            "status": "reviewed",
        }
    )
    monkeypatch.setattr(
        "app.services.grounded_answer_renderer.load_person_voice_evidence",
        lambda person_id: [evidence, corroborating]
        if person_id == "tang_taizong"
        else [],
    )

    answer = render_grounded_answer(FIRST_PROBLEM_ID)

    assert answer.historical_voice.startswith("先说要害")
    assert answer.voice_evidence_ids == ("PVC-TANG-0001", "PVC-TANG-0002")
    assert evidence.text not in answer.historical_voice
    assert answer.evidence_ids


def test_unknown_problem_cannot_be_rendered() -> None:
    with pytest.raises(KeyError):
        render_grounded_answer("Q-UNREVIEWED-NEW-PROBLEM")
