from app.services.problem_candidate_shortlist import build_candidate_research_shortlist


FIRST_QUESTION = "面对浩瀚的历史和剧烈的时代变革，个体的命运到底由谁主宰？"


def test_shortlist_groups_recalled_experience_by_person() -> None:
    rows = build_candidate_research_shortlist(
        FIRST_QUESTION,
        problem_id="Q-FATE-AGENCY-001",
        candidate_limit=20,
    )
    assert rows
    assert len({row.person_id for row in rows}) == len(rows)
    assert all(row.heu_ids for row in rows)
    assert all(row.status == "research_shortlist_not_responder_eligible" for row in rows)


def test_shortlist_is_deterministic_and_ranked() -> None:
    first = build_candidate_research_shortlist(FIRST_QUESTION, problem_id="Q-FATE-AGENCY-001")
    second = build_candidate_research_shortlist(FIRST_QUESTION, problem_id="Q-FATE-AGENCY-001")
    assert first == second
    assert all(
        (a.best_recall_score, a.aggregate_recall_score) >=
        (b.best_recall_score, b.aggregate_recall_score)
        for a, b in zip(first, first[1:])
    )


def test_unregistered_question_can_recall_people_but_cannot_gain_eligibility() -> None:
    rows = build_candidate_research_shortlist(
        "一个人在职业低谷时，是应该坚持原来的方向，还是及时改变？",
        candidate_limit=10,
    )
    assert all("not_responder_eligible" in row.status for row in rows)


def test_candidate_limit_validation() -> None:
    try:
        build_candidate_research_shortlist("测试", candidate_limit=0)
    except ValueError as exc:
        assert "candidate_limit" in str(exc)
    else:
        raise AssertionError("candidate_limit=0 must be rejected")
