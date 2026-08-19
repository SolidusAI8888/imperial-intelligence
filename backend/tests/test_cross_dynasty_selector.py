from app.services.cross_dynasty_selector import (
    first_fate_question_candidates,
    rank_candidates,
    screen_all_han_tang_song_emperors,
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
ELIGIBLE_IDS = {
    "liu_bang",
    "han_wendi",
    "han_jingdi",
    "han_wudi",
    "tang_gaozu",
    "tang_taizong",
    "song_taizu",
    "song_renzong",
}


def test_first_fate_question_compares_han_tang_song() -> None:
    candidates = first_fate_question_candidates()
    assert {candidate.dynasty for candidate in candidates} == {"han", "tang", "song"}
    assert {candidate.persona_id for candidate in candidates} == ELIGIBLE_IDS
    assert all(candidate.evidence_ids for candidate in candidates)


def test_complete_han_tang_song_roster_is_screened_before_selection() -> None:
    screened = screen_all_han_tang_song_emperors()
    assert len(screened) == 69
    assert {item.dynasty for item in screened} == {"han", "tang", "song"}
    ids = {item.persona_id for item in screened}
    assert {"liu_bang", "han_wudi", "han_guangwudi", "tang_gaozu", "tang_taizong", "tang_xuanzong", "song_taizu", "song_renzong", "song_gaozong", "song_bingdi"}.issubset(ids)

    eligible = {item.persona_id for item in screened if item.eligible}
    assert eligible == ELIGIBLE_IDS
    assert all(item.total_score is None for item in screened if not item.eligible)
    assert all("完整知识链" in item.reason for item in screened if not item.eligible)


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


def test_new_batch_candidates_have_real_canonical_evidence() -> None:
    candidates = {candidate.persona_id: candidate for candidate in first_fate_question_candidates()}
    assert "CN-HAN-0002-V004-P0004" in candidates["han_wendi"].evidence_ids
    assert "CN-HAN-0002-V005-P0017" in candidates["han_jingdi"].evidence_ids
    assert "CN-HAN-0002-V006-P0009" in candidates["han_wudi"].evidence_ids
    assert "CN-TANG-0001-V001-P0004" in candidates["tang_gaozu"].evidence_ids
    assert "CN-SONG-0001-V010-P0016" in candidates["song_renzong"].evidence_ids
    assert load_person_experiences("han_wendi")[0].heu_id == "HEU-HAN-000002"
    assert load_person_experiences("han_jingdi")[0].heu_id == "HEU-HAN-000004"
    assert load_person_experiences("han_wudi")[0].heu_id == "HEU-HAN-000003"
    assert load_person_experiences("tang_gaozu")[0].heu_id == "HEU-TANG-000004"
    assert load_person_experiences("song_renzong")[0].heu_id == "HEU-SONG-000002"


def test_first_fate_question_selects_tang_taizong_from_scores() -> None:
    ranked = rank_candidates(first_fate_question_candidates())
    assert ranked[0].persona_id == "tang_taizong"
    assert [item.persona_id for item in ranked[:4]] == [
        "tang_taizong",
        "song_renzong",
        "tang_gaozu",
        "han_wendi",
    ]
    assert all(a.total_score > b.total_score for a, b in zip(ranked, ranked[1:]))


def test_ranking_is_explainable_and_bounded() -> None:
    ranked = rank_candidates(first_fate_question_candidates())
    assert len(ranked) == 8
    assert all(0 <= candidate.total_score <= 1 for candidate in ranked)
    assert all(candidate.rationale for candidate in ranked)


def test_select_best_candidate_rejects_empty_pool() -> None:
    try:
        select_best_candidate([])
    except ValueError as exc:
        assert "No eligible historical candidates" in str(exc)
    else:
        raise AssertionError("empty candidate pool must be rejected")
