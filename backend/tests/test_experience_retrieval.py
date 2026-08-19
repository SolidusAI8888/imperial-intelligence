from app.services.experience_retrieval import recall_reusable_experiences


FIRST_QUESTION = "面对浩瀚的历史和剧烈的时代变革，个体的命运到底由谁主宰？"


def test_problem_aware_recall_reuses_reviewed_heus() -> None:
    rows = recall_reusable_experiences(
        FIRST_QUESTION,
        problem_id="Q-FATE-AGENCY-001",
        limit=50,
    )
    assert rows
    ids = {row.person_id for row in rows}
    assert "tang_taizong" in ids
    assert all(row.status == "recall_only_not_responder_eligible" for row in rows)
    assert all(row.score > 0 for row in rows)


def test_unregistered_question_can_recall_experience_without_inheriting_problem_eligibility() -> None:
    rows = recall_reusable_experiences(
        "当一次重大决策没能解决危机时，我应该怎样重新判断局势？",
        limit=50,
    )
    assert rows
    assert all("eligible" in row.status for row in rows)
    assert all(row.status.startswith("recall_only") for row in rows)


def test_recall_rejects_empty_question() -> None:
    try:
        recall_reusable_experiences("   ")
    except ValueError as exc:
        assert "question" in str(exc)
    else:
        raise AssertionError("empty question must be rejected")
