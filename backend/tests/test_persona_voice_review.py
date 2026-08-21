import hashlib
import json

from fastapi.testclient import TestClient
import yaml

from app.main import app
from app.services.persona_voice_evidence import parse_persona_voice_evidence
from app.services.persona_voice_review import (
    PersonaVoiceReviewDecisionResult,
    PersonaVoiceReviewPacket,
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
    assert packet.feature_tag_count == 3
    assert packet.requires_person_identity_review is True
    assert packet.approval_ready is True
    assert packet.blockers == ()


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


def test_review_packet_blocks_archived_file_changed_after_ingestion(tmp_path) -> None:
    voice_root, corpus_root, _candidate_path = _roots(tmp_path)
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


def test_status_only_approval_is_rejected(tmp_path) -> None:
    voice_root, corpus_root, _candidate_path = _roots(tmp_path)

    try:
        apply_persona_voice_review_decision(
            "PVC-TANG-REVIEW-0001",
            reviewer="historian@example",
            decision="approved",
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


def test_explicit_review_persists_attestation_and_unlocks_runtime_record(tmp_path) -> None:
    voice_root, corpus_root, candidate_path = _roots(tmp_path)

    result = apply_persona_voice_review_decision(
        "PVC-TANG-REVIEW-0001",
        reviewer="historian@example",
        decision="approved",
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
    assert evidence.review_attested is True
    assert evidence.runtime_eligible is True


def test_review_packet_api_is_read_only_and_typed(monkeypatch) -> None:
    packet = PersonaVoiceReviewPacket(
        voice_evidence_id="PVC-TANG-REVIEW-0001",
        person_id="tang_taizong",
        source_id="CN-TANG-0004",
        passage_id="CN-TANG-0004-V001-P0002",
        current_status="candidate",
        canonical_passage_found=True,
        archived_file_integrity_verified=True,
        candidate_text_matches_archive=True,
        archived_passage_path="history/source_corpus/example.txt",
        feature_tag_count=3,
        requires_person_identity_review=True,
        approval_ready=True,
        blockers=(),
        status="ready_for_explicit_human_voice_review",
    )
    monkeypatch.setattr(
        "app.main.build_persona_voice_review_packet", lambda _voice_id: packet
    )

    response = client.get("/persona-voice/PVC-TANG-REVIEW-0001/review-packet")

    assert response.status_code == 200
    assert response.json()["approval_ready"] is True


def test_review_decision_api_exposes_dry_run_without_runtime_unlock(monkeypatch) -> None:
    result = PersonaVoiceReviewDecisionResult(
        voice_evidence_id="PVC-TANG-REVIEW-0001",
        reviewer="historian@example",
        decision="approved",
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
