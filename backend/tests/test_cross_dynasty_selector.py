from app.services.cross_dynasty_selector import (
    first_fate_question_candidates,
    rank_candidates,
    select_best_candidate,
)


def test_first_fate_question_compares_han_tang_song() -> None:
    candidates = first_fate_question_candidates()
    assert {candidate.dynasty for candidate in candidates} == {"han", "tang", "song"}
    assert {candidate.persona_id for candidate in candidates} == {
        "liu_bang",
        "tang_taizong",
        "song_taizu",
    }
    assert all(candidate.evidence_ids for candidate in candidates)


def test_first_fate_question_selects_tang_taizong_from_scores() -> None:
    ranked = rank_candidates(first_fate_question_candidates())
    assert ranked[0].persona_id == "tang_taizong"
    assert ranked[0].total_score > ranked[1].total_score > ranked[2].total_score


def test_ranking_is_explainable_and_bounded() -> None:
    ranked = rank_candidates(first_fate_question_candidates())
    assert all(0 <= candidate.total_score <= 1 for candidate in ranked)
    assert all(candidate.rationale for candidate in ranked)


def test_select_best_candidate_rejects_empty_pool() -> None:
    try:
        select_best_candidate([])
    except ValueError as exc:
        assert "No eligible historical candidates" in str(exc)
    else:
        raise AssertionError("empty candidate pool must be rejected")
