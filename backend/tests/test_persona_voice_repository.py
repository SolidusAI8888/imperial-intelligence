import yaml

from app.services import knowledge_repository


def test_persona_voice_repository_loads_nested_records_and_filters_by_person(
    tmp_path, monkeypatch
) -> None:
    root = tmp_path / "persona_voice"
    target = root / "qing" / "yongzheng" / "PVC-QING-0001.yaml"
    target.parent.mkdir(parents=True)
    target.write_text(
        yaml.safe_dump(
            {
                "voice_evidence_id": "PVC-QING-0001",
                "person_id": "qing_yongzheng",
                "source_id": "CN-QING-VOICE-0002",
                "passage_id": "CN-QING-VOICE-0002-P000001",
                "source_kind": "vermilion_rescript",
                "contemporaneous": True,
                "text": "reviewed transcription",
                "voice_features": ["direct"],
                "decision_features": ["demands_specifics"],
                "rhetoric_features": ["gives_concrete_orders"],
                "confidence": 0.96,
                "status": "reviewed",
                "review": {
                    "reviewer": "historian@example",
                    "reviewed_at": "2026-08-21T00:00:00+00:00",
                    "decision": "approved",
                    "review_fingerprint": "PVC-REVIEW-SHA256-" + "A" * 64,
                    "passage_link_verified": True,
                    "person_identity_verified": True,
                    "transcription_checked": True,
                    "feature_tags_reviewed": True,
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(knowledge_repository, "VOICE_EVIDENCE_ROOT", root)

    loaded = knowledge_repository.load_person_voice_evidence("qing_yongzheng")

    assert [item.voice_evidence_id for item in loaded] == ["PVC-QING-0001"]
    assert knowledge_repository.load_person_voice_evidence("qing_qianlong") == []


def test_missing_persona_voice_corpus_is_an_empty_valid_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        knowledge_repository, "VOICE_EVIDENCE_ROOT", tmp_path / "not-created"
    )

    assert knowledge_repository.load_all_persona_voice_evidence() == []
