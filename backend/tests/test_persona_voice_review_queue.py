import hashlib
import json

from fastapi.testclient import TestClient
import pytest
import yaml

from app.main import app
from app.services.persona_voice_candidate import create_persona_voice_candidate
from app.services.persona_voice_review_queue import (
    PersonaVoiceReviewQueue,
    build_persona_voice_review_queue,
)


client = TestClient(app)


def _roots(tmp_path):
    voice_root = tmp_path / "persona_voice"
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
                "file": passage_path.name,
                "sha256": hashlib.sha256(passage_path.read_bytes()).hexdigest(),
            }
        ],
    }
    (passage_path.parent.parent / "ingestion_report.json").write_text(
        json.dumps(report), encoding="utf-8"
    )
    result = create_persona_voice_candidate(
        person_id="tang_taizong",
        source_id="CN-TANG-0004",
        passage_id="CN-TANG-0004-V001-P0002",
        source_kind="imperial_verbatim",
        contemporaneous=False,
        text="太宗問魏徵曰：「何謂為明君暗君？」",
        voice_features=["direct"],
        decision_features=["requests_counterargument"],
        rhetoric_features=["asks_questions"],
        confidence=0.9,
        proposed_by="researcher@example",
        persist=True,
        voice_root=voice_root,
        corpus_root=corpus_root,
    )
    candidate_path = voice_root / "tang_taizong" / f"{result.voice_evidence_id}.yaml"
    return voice_root, corpus_root, candidate_path


def test_queue_surfaces_verified_candidate_without_approving_it(tmp_path) -> None:
    voice_root, corpus_root, _candidate_path = _roots(tmp_path)

    queue = build_persona_voice_review_queue(
        voice_root=voice_root, corpus_root=corpus_root
    )

    assert queue.total_records == 1
    assert queue.candidate_records == 1
    assert queue.ready_candidate_records == 1
    assert queue.blocked_candidate_records == 0
    assert queue.items[0].approval_ready is True
    assert queue.items[0].runtime_eligible is False
    assert queue.items[0].archived_file_integrity_verified is True
    assert queue.items[0].candidate_text_matches_archive is True
    assert queue.items[0].candidate_text in queue.items[0].archive_context_excerpt
    assert queue.items[0].voice_features == ("direct",)
    assert queue.items[0].required_attestations == (
        "passage_link_verified",
        "person_identity_verified",
        "transcription_checked",
        "feature_tags_reviewed",
    )
    assert queue.items[0].review_packet_endpoint.endswith("/review-packet")
    assert queue.items[0].next_action == (
        "record_explicit_human_review_with_all_attestations"
    )
    assert queue.items[0].status == "candidate_ready_for_explicit_human_review"


def test_queue_blocks_multiple_candidates_for_same_person_and_passage(tmp_path) -> None:
    voice_root, corpus_root, candidate_path = _roots(tmp_path)
    duplicate = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    duplicate["voice_evidence_id"] = "PVC-TANG-DUPLICATE-0001"
    duplicate_path = candidate_path.with_name("PVC-TANG-DUPLICATE-0001.yaml")
    duplicate_path.write_text(
        yaml.safe_dump(duplicate, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    queue = build_persona_voice_review_queue(
        voice_root=voice_root, corpus_root=corpus_root
    )

    assert queue.candidate_records == 2
    assert queue.ready_candidate_records == 0
    assert queue.blocked_candidate_records == 2
    assert all(
        "duplicate_candidates_for_person_and_passage" in item.blockers
        for item in queue.items
    )
    assert all(
        item.next_action == "resolve_review_packet_blockers_before_decision"
        for item in queue.items
    )


def test_queue_repairs_reviewed_label_without_attestation(tmp_path) -> None:
    voice_root, corpus_root, candidate_path = _roots(tmp_path)
    raw = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    raw["status"] = "reviewed"
    candidate_path.write_text(
        yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    queue = build_persona_voice_review_queue(
        voice_root=voice_root, corpus_root=corpus_root
    )

    assert queue.candidate_records == 0
    assert queue.unattested_reviewed_records == 1
    assert queue.items[0].blockers == (
        "reviewed_record_missing_complete_attestation",
    )
    assert queue.items[0].archived_file_integrity_verified is True
    assert queue.items[0].candidate_text_matches_archive is True
    assert queue.items[0].next_action == (
        "repair_review_attestations_before_runtime_use"
    )
    assert queue.items[0].status == "reviewed_record_requires_attestation_repair"


def test_reviewed_attestation_repair_also_fails_on_changed_archive(tmp_path) -> None:
    voice_root, corpus_root, candidate_path = _roots(tmp_path)
    raw = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    raw["status"] = "reviewed"
    candidate_path.write_text(
        yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    passage_path = corpus_root / "tang" / "text" / "001.txt"
    passage_path.write_text(
        passage_path.read_text(encoding="utf-8") + "归档已变化",
        encoding="utf-8",
    )

    queue = build_persona_voice_review_queue(
        queue_state="attestation_repair",
        voice_root=voice_root,
        corpus_root=corpus_root,
    )

    assert queue.filtered_records == 1
    assert queue.items[0].archived_file_integrity_verified is False
    assert queue.items[0].blockers == (
        "reviewed_record_missing_complete_attestation",
        "archived_file_not_verified_by_ingestion_report",
    )
    assert queue.items[0].next_action == (
        "resolve_review_packet_blockers_before_decision"
    )
    assert queue.items[0].runtime_eligible is False


def test_queue_person_filter_is_exact(tmp_path) -> None:
    voice_root, corpus_root, _candidate_path = _roots(tmp_path)

    queue = build_persona_voice_review_queue(
        person_id="qing_yongzheng",
        voice_root=voice_root,
        corpus_root=corpus_root,
    )

    assert queue.total_records == 0
    assert queue.items == ()


def test_review_queue_endpoint_returns_typed_empty_queue(monkeypatch) -> None:
    queue = PersonaVoiceReviewQueue(
        total_records=0,
        candidate_records=0,
        ready_candidate_records=0,
        blocked_candidate_records=0,
        unattested_reviewed_records=0,
        runtime_eligible_reviewed_records=0,
        rejected_records=0,
        queue_state="all",
        filtered_records=0,
        returned_records=0,
        offset=0,
        limit=50,
        has_more=False,
        items=(),
        status="persona_voice_review_queue_read_only_no_automatic_approval",
    )
    monkeypatch.setattr(
        "app.main.build_persona_voice_review_queue", lambda **_kwargs: queue
    )

    response = client.get("/persona-voice/review-queue")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["candidate_records"] == 0


def test_repository_candidates_are_ready_for_review_but_never_runtime_eligible() -> None:
    queue = build_persona_voice_review_queue(person_id="tang_taizong")

    assert queue.total_records == 3
    assert queue.candidate_records == 3
    assert queue.ready_candidate_records == 3
    assert queue.blocked_candidate_records == 0
    assert {item.passage_id for item in queue.items} == {
        "CN-TANG-0004-V001-P0002",
        "CN-TANG-0004-V001-P0003",
        "CN-TANG-0004-V001-P0013",
    }
    assert all(item.approval_ready for item in queue.items)
    assert all(not item.review_attested for item in queue.items)
    assert all(not item.runtime_eligible for item in queue.items)


def test_repository_queue_supports_stable_pagination() -> None:
    first = build_persona_voice_review_queue(
        person_id="tang_taizong", queue_state="ready", offset=0, limit=2
    )
    second = build_persona_voice_review_queue(
        person_id="tang_taizong", queue_state="ready", offset=2, limit=2
    )

    assert first.queue_state == "ready"
    assert first.filtered_records == 3
    assert first.returned_records == 2
    assert first.has_more is True
    assert second.returned_records == 1
    assert second.has_more is False
    assert {item.voice_evidence_id for item in first.items}.isdisjoint(
        {item.voice_evidence_id for item in second.items}
    )


def test_queue_state_filters_blocked_and_attestation_repair_records(tmp_path) -> None:
    voice_root, corpus_root, candidate_path = _roots(tmp_path)
    duplicate = yaml.safe_load(candidate_path.read_text(encoding="utf-8"))
    duplicate["voice_evidence_id"] = "PVC-TANG-DUPLICATE-0001"
    candidate_path.with_name("PVC-TANG-DUPLICATE-0001.yaml").write_text(
        yaml.safe_dump(duplicate, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    blocked = build_persona_voice_review_queue(
        queue_state="blocked", voice_root=voice_root, corpus_root=corpus_root
    )
    repair = build_persona_voice_review_queue(
        queue_state="attestation_repair",
        voice_root=voice_root,
        corpus_root=corpus_root,
    )

    assert blocked.filtered_records == 2
    assert blocked.returned_records == 2
    assert all(not item.approval_ready for item in blocked.items)
    assert repair.filtered_records == 0
    assert repair.items == ()


def test_review_queue_endpoint_validates_filter_and_page_bounds() -> None:
    invalid_state = client.get(
        "/persona-voice/review-queue", params={"queue_state": "approved"}
    )
    invalid_offset = client.get(
        "/persona-voice/review-queue", params={"offset": -1}
    )
    invalid_limit = client.get(
        "/persona-voice/review-queue", params={"limit": 101}
    )

    assert invalid_state.status_code == 422
    assert invalid_offset.status_code == 422
    assert invalid_limit.status_code == 422


def test_review_queue_service_rejects_invalid_filter_and_page_bounds() -> None:
    with pytest.raises(ValueError, match="queue_state must be one of"):
        build_persona_voice_review_queue(queue_state="approved")
    with pytest.raises(ValueError, match="offset must be"):
        build_persona_voice_review_queue(offset=-1)
    with pytest.raises(ValueError, match="limit must be"):
        build_persona_voice_review_queue(limit=101)


def test_review_queue_endpoint_exposes_page_metadata() -> None:
    response = client.get(
        "/persona-voice/review-queue",
        params={
            "person_id": "tang_taizong",
            "queue_state": "ready",
            "offset": 0,
            "limit": 2,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["queue_state"] == "ready"
    assert data["filtered_records"] == 3
    assert data["returned_records"] == 2
    assert data["has_more"] is True
    assert len(data["items"]) == 2
    assert all(item["candidate_text"] for item in data["items"])
    assert all(item["archive_context_excerpt"] for item in data["items"])
    assert all(item["archived_file_integrity_verified"] for item in data["items"])
