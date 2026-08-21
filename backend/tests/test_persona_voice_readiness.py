from fastapi.testclient import TestClient

from app.main import app
from app.services.persona_voice_evidence import parse_persona_voice_evidence
from app.services.persona_voice_readiness import inspect_persona_voice_readiness


client = TestClient(app)


def _record(**overrides):
    record = {
        "voice_evidence_id": "PVC-QING-0001",
        "person_id": "qing_yongzheng",
        "source_id": "CN-QING-VOICE-0002",
        "passage_id": "CN-QING-VOICE-0002-P000001",
        "source_kind": "vermilion_rescript",
        "contemporaneous": True,
        "text": "reviewed transcription",
        "voice_features": ["direct", "terse"],
        "decision_features": ["demands_specifics"],
        "rhetoric_features": ["gives_concrete_orders"],
        "confidence": 0.96,
        "status": "reviewed",
    }
    record.update(overrides)
    return parse_persona_voice_evidence(record)


def test_readiness_reports_selected_reviewed_traceable_voice_evidence(
    monkeypatch,
) -> None:
    records = [
        _record(),
        _record(voice_evidence_id="PVC-QING-0002", status="candidate"),
        _record(voice_evidence_id="PVC-QING-0003", status="rejected"),
    ]
    monkeypatch.setattr(
        "app.services.persona_voice_readiness.load_person_voice_evidence",
        lambda person_id: records if person_id == "qing_yongzheng" else [],
    )

    result = inspect_persona_voice_readiness("qing_yongzheng")

    assert result.total_records == 3
    assert result.reviewed_records == 1
    assert result.candidate_records == 1
    assert result.rejected_records == 1
    assert result.traceable_reviewed_records == 1
    assert result.runtime_style_ready is True
    assert result.selected_voice_evidence_ids == ("PVC-QING-0001",)
    assert result.fallback_reason is None
    assert result.status == "runtime_voice_style_ready"


def test_untraceable_reviewed_evidence_reports_neutral_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.persona_voice_readiness.load_person_voice_evidence",
        lambda _person_id: [_record(passage_id="")],
    )

    result = inspect_persona_voice_readiness("qing_yongzheng")

    assert result.reviewed_records == 1
    assert result.traceable_reviewed_records == 0
    assert result.runtime_style_ready is False
    assert result.fallback_reason == "no_traceable_reviewed_voice_evidence"
    assert result.status == "neutral_voice_fallback_required"


def test_voice_readiness_endpoint_exposes_honest_empty_corpus_fallback() -> None:
    response = client.get("/personas/tang_taizong/voice-readiness")

    assert response.status_code == 200
    data = response.json()
    assert data["person_id"] == "tang_taizong"
    assert data["total_records"] == 0
    assert data["runtime_style_ready"] is False
    assert data["selected_voice_evidence_ids"] == []
    assert data["fallback_reason"] == "no_voice_evidence_records"
    assert data["status"] == "neutral_voice_fallback_required"
