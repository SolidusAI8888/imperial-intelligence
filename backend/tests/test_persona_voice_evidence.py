import pytest

from app.services.persona_voice_evidence import (
    parse_persona_voice_evidence,
    select_runtime_voice_evidence,
)


def _record(**overrides):
    record = {
        "voice_evidence_id": "PVC-QING-0001",
        "person_id": "qing_yongzheng",
        "source_id": "CN-QING-VOICE-0002",
        "passage_id": "CN-QING-VOICE-0002-P000001",
        "source_kind": "vermilion_rescript",
        "contemporaneous": True,
        "text": "sample reviewed transcription",
        "voice_features": ["direct", "terse"],
        "decision_features": ["demands_specifics"],
        "rhetoric_features": ["gives_concrete_orders"],
        "confidence": 0.96,
        "status": "reviewed",
    }
    record.update(overrides)
    return record


def test_reviewed_direct_voice_evidence_is_runtime_eligible():
    evidence = parse_persona_voice_evidence(_record())
    assert evidence.runtime_eligible is True
    assert evidence.evidence_weight == 0.96


def test_candidate_voice_evidence_cannot_affect_runtime():
    evidence = parse_persona_voice_evidence(_record(status="candidate"))
    assert evidence.runtime_eligible is False


def test_direct_imperial_words_outweigh_later_compilation():
    direct = parse_persona_voice_evidence(_record())
    later = parse_persona_voice_evidence(
        _record(
            voice_evidence_id="PVC-QING-0002",
            source_id="CN-QING-0003",
            source_kind="later_compilation",
            contemporaneous=False,
            confidence=1.0,
        )
    )
    selected = select_runtime_voice_evidence([later, direct])
    assert selected[0].voice_evidence_id == direct.voice_evidence_id
    assert direct.evidence_weight > later.evidence_weight


def test_reviewed_record_without_passage_trace_is_not_runtime_eligible():
    evidence = parse_persona_voice_evidence(_record(passage_id=""))
    assert evidence.runtime_eligible is False


def test_rejects_unknown_source_kind():
    with pytest.raises(ValueError, match="unsupported source_kind"):
        parse_persona_voice_evidence(_record(source_kind="internet_summary"))
