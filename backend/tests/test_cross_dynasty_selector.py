from app.services.cross_dynasty_selector import (
    first_fate_question_candidates,
    rank_candidates,
    select_best_candidate,
)
from app.services.knowledge_repository import (
    load_person_experiences,
    load_person_insights,
    load_person_records,
    load_person_role_links,
)
from app.services.knowledge_runtime import build_runtime_context


QUESTION = "面对浩瀚的历史和剧烈的时代变革，个体的命运到底由谁主宰？"


def test_first_fate_question_compares_han_tang_song() -> None:
    candidates = first_fate_question_candidates()
    assert {candidate.dynasty for candidate in candidates} == {"han", "tang", "song"}
    assert {candidate.persona_id for candidate in candidates} == {
        "liu_bang",
        "tang_taizong",
        "song_taizu",
    }
    assert all(candidate.evidence_ids for candidate in candidates)


def test_every_ranked_candidate_has_runtime_valid_reviewed_chain() -> None:
    for candidate in first_fate_question_candidates():
        records = load_person_records(candidate.persona_id)
        experiences = load_person_experiences(candidate.persona_id)
        insights = load_person_insights(candidate.persona_id)
        role_links = load_person_role_links(candidate.persona_id)

        assert records
        assert experiences
        assert insights
        assert role_links
        assert all(item.status in {"reviewed", "accepted"} for item in records)
        assert all(item.status in {"reviewed", "accepted"} for item in experiences)
        assert all(item.status in {"reviewed", "accepted"} for item in insights)

        context = build_runtime_context(
            problem_id="Q-FATE-AGENCY-001",
            question=QUESTION,
            person_id=candidate.persona_id,
            records=records,
            experiences=experiences,
            insights=insights,
            role_links=role_links,
        )
        assert context.person_id == candidate.persona_id
        assert context.life_course_rule == "full_lifetime"


def test_han_and_song_candidates_are_not_code_only_placeholders() -> None:
    han = next(c for c in first_fate_question_candidates() if c.persona_id == "liu_bang")
    song = next(c for c in first_fate_question_candidates() if c.persona_id == "song_taizu")
    assert "CN-HAN-0001-V008-P0011" in han.evidence_ids
    assert "CN-SONG-0001-V001-P0010" in song.evidence_ids
    assert load_person_experiences("liu_bang")[0].heu_id == "HEU-HAN-000001"
    assert load_person_experiences("song_taizu")[0].heu_id == "HEU-SONG-000001"


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
