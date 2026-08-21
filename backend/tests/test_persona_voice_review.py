import hashlib
import json

from fastapi.testclient import TestClient
import pytest
import yaml

from app.main import app
from app.services.persona_voice_evidence import parse_persona_voice_evidence
from app.services.persona_voice_review import (
    PersonaVoiceReviewDecisionResult,
    PersonaVoiceReviewPacket,
    StalePersonaVoiceReviewError,
    apply_persona_voice_review_decision,
    build_persona_voice_review_packet,
)


client = TestClient(app)


def _candidate() -> dict:
    return {
        "voice_evidence_id": "PVC-TANG-REVIEW-0001",
        "person_id": "tang_taizong",
        "source_id": "CN-TANG-0004",
        "passage_id": "CN-TANG-0004-V001-P0002",
        "source_kind": "imperial_verbatim",
        "contemporaneous": False,
        "text": "太宗問魏徵曰：「何謂為明君暗君？」",
        "voice_features": ["direct"],
        "decision_features": ["requests_counterargument"],
        "rhetoric_features": ["asks_questions"],
        "confidence": 0.9,
        "status": "candidate",
    }


def _roots(tmp_path):
    voice_root = tmp_path / "persona_voice"
    candidate_path = voice_root / "tang" / "PVC-TANG-REVIEW-0001.yaml"
    candidate_path.parent.mkdir(parents=True)
    candidate_path.write_text(
        yaml.safe_dump(_candidate(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    corpus_root = tmp_path / "source_corpus"
    passage_path = corpus_root / "tang" / "text" / "001.txt"
    passage_path.parent.mkdir(parents=True)
    passage_path.write_text(
        "[CN-TANG-0004-V001-P0002]\n"
        "貞觀二年，太宗問魏徵曰：「何謂為明君暗君？」徵曰：「兼聽則明。」\n",
        encoding="utf-8",
    )
    report = {
        "source_id": "CN-TANG-0004",
        "pages": [
            {
                "file": "001.txt",
                "sha256": hashlib.sha256(passage_path.read_bytes()).hexdigest(),
            }
        ],
    }
    (passage_path.parent.parent / "ingestion_report.json").write_text(
        json.dumps(report), encoding="utf-8"
    )
    return voice_root, corpus_root, candidate_path


def test_review_packet_requires_exact_archived_passage_trace(tmp_path) -> None:
    voice_root, corpus_root, _candidate_path = _roots(tmp_path)

    packet = build_persona_voice_review_packet(
        "PVC-TANG-REVIEW-0001",
        voice_root=voice_root,
        corpus_root=corpus_root,
    )

    assert packet.canonical_passage_found is True
    assert packet.archived_file_integrity_verified is True
    assert packet.candidate_text_matches_archive is True
    assert packet.candidate_text == "太宗問魏徵曰：「何謂為明君暗君？」"
    assert packet.archive_context_excerpt is not None
    assert packet.candidate_text in packet.archive_context_excerpt
    assert packet.voice_features == ("direct",)
    assert packet.decision_features == ("requests_counterargument",)
    assert packet.rhetoric_features == ("asks_questions",)
    assert packet.confidence == 0.9
    assert packet.feature_tag_count == 3
    assert packet.requires_person_identity_review is True
    assert packet.required_attestations == (
        "passage_link_verified",
        "person_identity_verified",
        "transcription_checked",
        "feature_tags_reviewed",
    )
    assert packet.conflicting_candidate_ids == ()
    assert packet.review_fingerprint.startswith("PVC-REVIEW-SHA256-")
    assert len(packet.review_fingerprint) == len("PVC-REVIEW-SHA256-") + 64
    assert build_persona_voice_review_packet(
        "PVC-TANG-REVIEW-0001",
        voice_root=voice_root,
        corpus_root=corpus_root,
    ).review_fingerprint == packet.review_fingerprint
    assert packet.approval_ready is True
    assert packet.blockers == ()
    assert packet.next_action == (
        "record_explicit_human_review_with_all_attestations"
    )


def test_review_packet_blocks_transcription_not_present_in_archive(tmp_path) -> None:
    voice_root, corpus_root, candidate_path = _roots(tmp_path)
    raw = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    raw["text"] = "这句话并不存在于归档段落中"
    candidate_path.write_text(
        yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    packet = build_persona_voice_review_packet(
        "PVC-TANG-REVIEW-0001",
        voice_root=voice_root,
        corpus_root=corpus_root,
    )

    assert packet.approval_ready is False
    assert packet.blockers == ("candidate_text_not_found_in_canonical_passage",)
    assert packet.archive_context_excerpt is None
    assert packet.next_action == "resolve_review_packet_blockers_before_decision"


def test_review_packet_blocks_archived_file_changed_after_ingestion(tmp_path) -> None:
    voice_root, corpus_root, _candidate_path = _roots(tmp_path)
    original = build_persona_voice_review_packet(
        "PVC-TANG-REVIEW-0001",
        voice_root=voice_root,
        corpus_root=corpus_root,
    )
    passage_path = corpus_root / "tang" / "text" / "001.txt"
    passage_path.write_text(
        passage_path.read_text(encoding="utf-8") + "被修改",
        encoding="utf-8",
    )

    packet = build_persona_voice_review_packet(
        "PVC-TANG-REVIEW-0001",
        voice_root=voice_root,
        corpus_root=corpus_root,
    )

    assert packet.canonical_passage_found is True
    assert packet.archived_file_integrity_verified is False
    assert packet.approval_ready is False
    assert packet.blockers == ("archived_file_not_verified_by_ingestion_report",)
    assert packet.review_fingerprint != original.review_fingerprint


def test_review_fingerprint_changes_when_candidate_features_change(tmp_path) -> None:
    voice_root, corpus_root, candidate_path = _roots(tmp_path)
    original = build_persona_voice_review_packet(
        "PVC-TANG-REVIEW-0001",
        voice_root=voice_root,
        corpus_root=corpus_root,
    )
    raw = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    raw["voice_features"].append("concise")
    candidate_path.write_text(
        yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    changed = build_persona_voice_review_packet(
        "PVC-TANG-REVIEW-0001",
        voice_root=voice_root,
        corpus_root=corpus_root,
    )

    assert original.approval_ready is True
    assert changed.approval_ready is True
    assert changed.voice_features == ("direct", "concise")
    assert changed.review_fingerprint != original.review_fingerprint


def test_duplicate_candidate_is_blocked_in_packet_and_decision_service(tmp_path) -> None:
    voice_root, corpus_root, candidate_path = _roots(tmp_path)
    duplicate = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    duplicate["voice_evidence_id"] = "PVC-TANG-REVIEW-0002"
    candidate_path.with_name("PVC-TANG-REVIEW-0002.yaml").write_text(
        yaml.safe_dump(duplicate, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    packet = build_persona_voice_review_packet(
        "PVC-TANG-REVIEW-0001",
        voice_root=voice_root,
        corpus_root=corpus_root,
    )

    assert packet.approval_ready is False
    assert packet.conflicting_candidate_ids == ("PVC-TANG-REVIEW-0002",)
    assert "duplicate_candidates_for_person_and_passage" in packet.blockers
    with pytest.raises(ValueError, match="duplicate_candidates_for_person_and_passage"):
        apply_persona_voice_review_decision(
            "PVC-TANG-REVIEW-0001",
            reviewer="historian@example",
            decision="approved",
            review_fingerprint=packet.review_fingerprint,
            passage_link_verified=True,
            person_identity_verified=True,
            transcription_checked=True,
            feature_tags_reviewed=True,
            voice_root=voice_root,
            corpus_root=corpus_root,
        )


def test_status_only_approval_is_rejected(tmp_path) -> None:
    voice_root, corpus_root, _candidate_path = _roots(tmp_path)
    packet = build_persona_voice_review_packet(
        "PVC-TANG-REVIEW-0001",
        voice_root=voice_root,
        corpus_root=corpus_root,
    )

    try:
        apply_persona_voice_review_decision(
            "PVC-TANG-REVIEW-0001",
            reviewer="historian@example",
            decision="approved",
            review_fingerprint=packet.review_fingerprint,
            passage_link_verified=True,
            person_identity_verified=True,
            transcription_checked=False,
            feature_tags_reviewed=True,
            voice_root=voice_root,
            corpus_root=corpus_root,
        )
    except ValueError as exc:
        assert "all four review attestations" in str(exc)
    else:
        raise AssertionError("status-only approval should be rejected")


def test_stale_review_fingerprint_is_rejected_after_candidate_change(tmp_path) -> None:
    voice_root, corpus_root, candidate_path = _roots(tmp_path)
    packet = build_persona_voice_review_packet(
        "PVC-TANG-REVIEW-0001",
        voice_root=voice_root,
        corpus_root=corpus_root,
    )
    raw = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    raw["rhetoric_features"] = ["uses_historical_examples"]
    candidate_path.write_text(
        yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    with pytest.raises(StalePersonaVoiceReviewError, match="fingerprint is stale"):
        apply_persona_voice_review_decision(
            "PVC-TANG-REVIEW-0001",
            reviewer="historian@example",
            decision="approved",
            review_fingerprint=packet.review_fingerprint,
            passage_link_verified=True,
            person_identity_verified=True,
            transcription_checked=True,
            feature_tags_reviewed=True,
            voice_root=voice_root,
            corpus_root=corpus_root,
        )


def test_explicit_review_persists_attestation_and_unlocks_runtime_record(tmp_path) -> None:
    voice_root, corpus_root, candidate_path = _roots(tmp_path)
    packet = build_persona_voice_review_packet(
        "PVC-TANG-REVIEW-0001",
        voice_root=voice_root,
        corpus_root=corpus_root,
    )

    result = apply_persona_voice_review_decision(
        "PVC-TANG-REVIEW-0001",
        reviewer="historian@example",
        decision="approved",
        review_fingerprint=packet.review_fingerprint,
        passage_link_verified=True,
        person_identity_verified=True,
        transcription_checked=True,
        feature_tags_reviewed=True,
        note="Compared against the archived passage.",
        persist=True,
        voice_root=voice_root,
        corpus_root=corpus_root,
    )

    raw = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    evidence = parse_persona_voice_evidence(raw)
    assert result.persisted is True
    assert result.runtime_eligible_after_persist is True
    assert raw["status"] == "reviewed"
    assert raw["review"]["decision"] == "approved"
    assert raw["review"]["review_fingerprint"] == packet.review_fingerprint
    assert result.review_fingerprint == packet.review_fingerprint
    assert result.fingerprint_verified is True
    assert evidence.review_attested is True
    assert evidence.runtime_eligible is True


def test_review_packet_api_is_read_only_and_typed(monkeypatch) -> None:
    packet = PersonaVoiceReviewPacket(
        voice_evidence_id="PVC-TANG-REVIEW-0001",
        person_id="tang_taizong",
        source_id="CN-TANG-0004",
        passage_id="CN-TANG-0004-V001-P0002",
        source_kind="imperial_verbatim",
        contemporaneous=False,
        current_status="candidate",
        candidate_text="太宗問魏徵曰：「何謂為明君暗君？」",
        archive_context_excerpt="太宗問魏徵曰：「何謂為明君暗君？」徵曰……",
        voice_features=("direct",),
        decision_features=("requests_counterargument",),
        rhetoric_features=("asks_questions",),
        confidence=0.9,
        canonical_passage_found=True,
        archived_file_integrity_verified=True,
        candidate_text_matches_archive=True,
        archived_passage_path="history/source_corpus/example.txt",
        feature_tag_count=3,
        requires_person_identity_review=True,
        required_attestations=(
            "passage_link_verified",
            "person_identity_verified",
            "transcription_checked",
            "feature_tags_reviewed",
        ),
        conflicting_candidate_ids=(),
        review_fingerprint="PVC-REVIEW-SHA256-" + "A" * 64,
        approval_ready=True,
        blockers=(),
        next_action="record_explicit_human_review_with_all_attestations",
        status="ready_for_explicit_human_voice_review",
    )
    monkeypatch.setattr(
        "app.main.build_persona_voice_review_packet", lambda _voice_id: packet
    )

    response = client.get("/persona-voice/PVC-TANG-REVIEW-0001/review-packet")

    assert response.status_code == 200
    assert response.json()["approval_ready"] is True
    assert response.json()["candidate_text"] == "太宗問魏徵曰：「何謂為明君暗君？」"
    assert response.json()["required_attestations"] == [
        "passage_link_verified",
        "person_identity_verified",
        "transcription_checked",
        "feature_tags_reviewed",
    ]
    assert response.json()["conflicting_candidate_ids"] == []
    assert response.json()["review_fingerprint"] == (
        "PVC-REVIEW-SHA256-" + "A" * 64
    )


def test_review_decision_api_exposes_dry_run_without_runtime_unlock(monkeypatch) -> None:
    result = PersonaVoiceReviewDecisionResult(
        voice_evidence_id="PVC-TANG-REVIEW-0001",
        reviewer="historian@example",
        decision="approved",
        review_fingerprint="PVC-REVIEW-SHA256-" + "A" * 64,
        fingerprint_verified=True,
        resulting_status="reviewed",
        persisted=False,
        runtime_eligible_after_persist=False,
        status="voice_review_decision_validated_style_only_no_answer_permission_change",
    )
    monkeypatch.setattr(
        "app.main.apply_persona_voice_review_decision", lambda *args, **kwargs: result
    )

    response = client.post(
        "/persona-voice/PVC-TANG-REVIEW-0001/review",
        json={
            "reviewer": "historian@example",
            "decision": "approved",
            "review_fingerprint": "PVC-REVIEW-SHA256-" + "A" * 64,
            "passage_link_verified": True,
            "person_identity_verified": True,
            "transcription_checked": True,
            "feature_tags_reviewed": True,
            "persist": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["persisted"] is False
    assert response.json()["runtime_eligible_after_persist"] is False
    assert response.json()["fingerprint_verified"] is True


def test_review_decision_api_returns_conflict_for_stale_packet(monkeypatch) -> None:
    def _raise_stale(*_args, **_kwargs):
        raise StalePersonaVoiceReviewError("review fingerprint is stale; reload")

    monkeypatch.setattr("app.main.apply_persona_voice_review_decision", _raise_stale)

    response = client.post(
        "/persona-voice/PVC-TANG-REVIEW-0001/review",
        json={
            "reviewer": "historian@example",
            "decision": "approved",
            "review_fingerprint": "PVC-REVIEW-SHA256-" + "A" * 64,
            "passage_link_verified": True,
            "person_identity_verified": True,
            "transcription_checked": True,
            "feature_tags_reviewed": True,
            "persist": False,
        },
    )

    assert response.status_code == 409
    assert "fingerprint is stale" in response.json()["detail"]
