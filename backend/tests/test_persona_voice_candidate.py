import hashlib
import json

from fastapi.testclient import TestClient
import yaml

from app.main import app
from app.services.persona_voice_candidate import (
    PersonaVoiceCandidateResult,
    create_persona_voice_candidate,
)
from app.services.persona_voice_evidence import parse_persona_voice_evidence
from app.services.persona_voice_review import build_persona_voice_review_packet


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
                "file": "001.txt",
                "sha256": hashlib.sha256(passage_path.read_bytes()).hexdigest(),
            }
        ],
    }
    (passage_path.parent.parent / "ingestion_report.json").write_text(
        json.dumps(report), encoding="utf-8"
    )
    return voice_root, corpus_root, passage_path


def _create(voice_root, corpus_root, **overrides):
    values = {
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
        "proposed_by": "researcher@example",
        "voice_root": voice_root,
        "corpus_root": corpus_root,
    }
    values.update(overrides)
    return create_persona_voice_candidate(**values)


def test_dry_run_candidate_is_deterministic_and_never_runtime_eligible(tmp_path) -> None:
    voice_root, corpus_root, _passage_path = _roots(tmp_path)

    first = _create(voice_root, corpus_root)
    second = _create(voice_root, corpus_root)

    assert first.voice_evidence_id == second.voice_evidence_id
    assert first.voice_evidence_id.startswith("PVC-TANG-")
    assert first.persisted is False
    assert first.review_required is True
    assert first.runtime_eligible is False
    assert not (voice_root / "tang_taizong").exists()


def test_persisted_candidate_flows_into_review_packet_but_not_runtime(tmp_path) -> None:
    voice_root, corpus_root, _passage_path = _roots(tmp_path)

    result = _create(voice_root, corpus_root, persist=True)
    target = voice_root / "tang_taizong" / f"{result.voice_evidence_id}.yaml"
    raw = yaml.safe_load(target.read_text(encoding="utf-8"))
    evidence = parse_persona_voice_evidence(raw)
    packet = build_persona_voice_review_packet(
        result.voice_evidence_id,
        voice_root=voice_root,
        corpus_root=corpus_root,
    )

    assert result.persisted is True
    assert raw["status"] == "candidate"
    assert raw["candidate"]["proposed_by"] == "researcher@example"
    assert evidence.runtime_eligible is False
    assert packet.approval_ready is True


def test_repeating_same_persisted_candidate_is_idempotent(tmp_path) -> None:
    voice_root, corpus_root, _passage_path = _roots(tmp_path)

    first = _create(voice_root, corpus_root, persist=True)
    second = _create(voice_root, corpus_root, persist=True)

    assert first.voice_evidence_id == second.voice_evidence_id
    assert second.persisted is True
    assert len(list(voice_root.rglob("*.yaml"))) == 1


def test_candidate_creation_rejects_unverified_or_changed_archive(tmp_path) -> None:
    voice_root, corpus_root, passage_path = _roots(tmp_path)
    passage_path.write_text(
        passage_path.read_text(encoding="utf-8") + "changed", encoding="utf-8"
    )

    try:
        _create(voice_root, corpus_root)
    except ValueError as exc:
        assert "integrity verification" in str(exc)
    else:
        raise AssertionError("changed archive should not produce a PVC candidate")


def test_candidate_creation_requires_interpretable_feature_tags(tmp_path) -> None:
    voice_root, corpus_root, _passage_path = _roots(tmp_path)

    try:
        _create(
            voice_root,
            corpus_root,
            voice_features=[],
            decision_features=[],
            rhetoric_features=[],
        )
    except ValueError as exc:
        assert "at least one feature tag" in str(exc)
    else:
        raise AssertionError("untagged excerpt should not produce a PVC candidate")


def test_candidate_creation_rejects_unstable_feature_tag(tmp_path) -> None:
    voice_root, corpus_root, _passage_path = _roots(tmp_path)

    try:
        _create(voice_root, corpus_root, voice_features=["Direct prose!"])
    except ValueError as exc:
        assert "snake_case" in str(exc)
    else:
        raise AssertionError("unstable feature tag should be rejected")


def test_candidate_api_returns_review_required_dry_run(monkeypatch) -> None:
    result = PersonaVoiceCandidateResult(
        voice_evidence_id="PVC-TANG-ABCDEF123456",
        person_id="tang_taizong",
        source_id="CN-TANG-0004",
        passage_id="CN-TANG-0004-V001-P0002",
        candidate_path="knowledge/persona_voice/tang_taizong/example.yaml",
        persisted=False,
        review_required=True,
        runtime_eligible=False,
        status="persona_voice_candidate_requires_explicit_human_review",
    )
    monkeypatch.setattr(
        "app.main.create_persona_voice_candidate", lambda **_kwargs: result
    )

    response = client.post(
        "/persona-voice/candidates",
        json={
            "person_id": "tang_taizong",
            "source_id": "CN-TANG-0004",
            "passage_id": "CN-TANG-0004-V001-P0002",
            "source_kind": "imperial_verbatim",
            "contemporaneous": False,
            "text": "太宗問魏徵曰：「何謂為明君暗君？」",
            "voice_features": ["direct"],
            "decision_features": [],
            "rhetoric_features": ["asks_questions"],
            "confidence": 0.9,
            "proposed_by": "researcher@example",
            "persist": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["persisted"] is False
    assert response.json()["review_required"] is True
    assert response.json()["runtime_eligible"] is False
