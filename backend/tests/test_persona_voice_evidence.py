import pytest

from app.services.persona_voice_evidence import (
    build_persona_voice_profile,
    parse_persona_voice_evidence,
    select_runtime_voice_evidence,
    style_answer_opening,
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


def test_runtime_selection_cannot_mix_another_persons_voice() -> None:
    yongzheng = parse_persona_voice_evidence(_record())
    qianlong = parse_persona_voice_evidence(
        _record(voice_evidence_id="PVC-QING-0002", person_id="qing_qianlong")
    )

    selected = select_runtime_voice_evidence(
        [qianlong, yongzheng], person_id="qing_yongzheng"
    )

    assert selected == (yongzheng,)


def test_profile_aggregates_weighted_features_without_copying_source_text() -> None:
    direct = parse_persona_voice_evidence(_record(text="reviewed words must not be copied"))
    corroborating = parse_persona_voice_evidence(
        _record(
            voice_evidence_id="PVC-QING-0003",
            passage_id="CN-QING-VOICE-0002-P000002",
            text="separate reviewed passage",
        )
    )
    candidate = parse_persona_voice_evidence(
        _record(
            voice_evidence_id="PVC-QING-0002",
            status="candidate",
            voice_features=["conciliatory"],
        )
    )

    profile = build_persona_voice_profile(
        "qing_yongzheng", [candidate, direct, corroborating]
    )

    assert profile is not None
    assert profile.voice_evidence_ids == ("PVC-QING-0001", "PVC-QING-0003")
    assert profile.voice_features == ("direct", "terse")
    assert profile.distinct_passage_count == 2
    assert profile.distinct_source_count == 1
    assert profile.total_evidence_weight == 1.92
    assert profile.runtime_style_ready is True
    assert profile.gate_blockers == ()
    opening = style_answer_opening("default", profile)
    assert opening.startswith("先说要害")
    assert "reviewed words must not be copied" not in opening


def test_single_reviewed_passage_cannot_define_general_persona_style() -> None:
    profile = build_persona_voice_profile(
        "qing_yongzheng", [parse_persona_voice_evidence(_record())]
    )

    assert profile is not None
    assert profile.runtime_style_ready is False
    assert profile.applied_voice_evidence_ids == ()
    assert profile.gate_blockers == (
        "fewer_than_2_independent_voice_passages",
        "voice_evidence_weight_below_1.20",
        "no_style_features_corroborated_by_2_passages",
    )
    assert style_answer_opening("neutral opening", profile) == "neutral opening"


def test_duplicate_annotations_of_one_passage_do_not_bypass_style_gate() -> None:
    duplicate = parse_persona_voice_evidence(
        _record(voice_evidence_id="PVC-QING-0002")
    )
    profile = build_persona_voice_profile(
        "qing_yongzheng", [parse_persona_voice_evidence(_record()), duplicate]
    )

    assert profile is not None
    assert profile.evidence_count == 2
    assert profile.distinct_passage_count == 1
    assert profile.total_evidence_weight == 0.96
    assert profile.runtime_style_ready is False


def test_uncorroborated_feature_does_not_change_persona_style() -> None:
    second_passage = parse_persona_voice_evidence(
        _record(
            voice_evidence_id="PVC-QING-0002",
            passage_id="CN-QING-VOICE-0002-P000002",
            voice_features=["conciliatory"],
            decision_features=[],
            rhetoric_features=[],
        )
    )
    profile = build_persona_voice_profile(
        "qing_yongzheng", [parse_persona_voice_evidence(_record()), second_passage]
    )

    assert profile is not None
    assert profile.distinct_passage_count == 2
    assert profile.total_evidence_weight == 1.92
    assert profile.voice_features == ()
    assert profile.runtime_style_ready is False
    assert profile.gate_blockers == (
        "no_style_features_corroborated_by_2_passages",
    )
    assert style_answer_opening("neutral opening", profile) == "neutral opening"


def test_blank_identity_fields_are_rejected() -> None:
    with pytest.raises(ValueError, match="blank persona voice evidence fields"):
        parse_persona_voice_evidence(_record(person_id=""))
