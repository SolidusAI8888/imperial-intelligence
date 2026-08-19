from app.services.emperor_review_queue import build_review_queue


def test_review_queue_excludes_already_eligible_emperors() -> None:
    report = build_review_queue(
        persona_ids=["tang_taizong", "han_wudi", "han_jingdi", "han_zhaodi", "tang_xuanzong", "song_gaozong"],
        evidence_limit=2,
    )
    ids = {row["persona_id"] for row in report["rows"]}
    assert "tang_taizong" not in ids
    assert "han_wudi" not in ids
    assert "han_jingdi" not in ids
    assert ids == {"han_zhaodi", "tang_xuanzong", "song_gaozong"}
    assert report["registered_remaining"] == 3


def test_review_queue_never_promotes_candidate_evidence_to_eligibility() -> None:
    report = build_review_queue(persona_ids=["han_zhaodi"], evidence_limit=3)
    assert len(report["rows"]) == 1
    row = report["rows"][0]
    assert row["eligibility"] == "not_yet_eligible"
    assert row["readiness"] in {"ready_for_evidence_review", "needs_more_candidate_evidence"}
    assert all(hit["persona_id"] == "han_zhaodi" for hit in row["candidate_evidence"])


def test_review_queue_priority_is_deterministic_and_bounded_to_requested_rows() -> None:
    ids = ["han_zhaodi", "tang_xuanzong", "song_gaozong"]
    first = build_review_queue(persona_ids=ids, evidence_limit=1)
    second = build_review_queue(persona_ids=reversed(ids), evidence_limit=1)
    assert [(row["persona_id"], row["priority_score"]) for row in first["rows"]] == [
        (row["persona_id"], row["priority_score"]) for row in second["rows"]
    ]
    assert first["ready_for_evidence_review"] + first["needs_more_candidate_evidence"] == 3
