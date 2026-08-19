from app.services.problem_insight_review_queue import build_problem_insight_review_queue


QUESTION = "一个人在职业低谷时，是应该坚持原来的方向，还是及时改变？"


def test_review_queue_is_research_only_and_prioritized() -> None:
    rows = build_problem_insight_review_queue(QUESTION, candidate_limit=10)
    assert rows
    assert [row.review_priority for row in rows] == list(range(1, len(rows) + 1))
    assert all(row.status == "awaiting_problem_specific_insight_review" for row in rows)
    assert all(row.heu_ids for row in rows)
    assert all("Do not grant responder eligibility" in row.required_action for row in rows)


def test_review_queue_does_not_create_answer_permissions() -> None:
    rows = build_problem_insight_review_queue(QUESTION, candidate_limit=10)
    serialized = " ".join(
        [
            row.status + " " + row.required_action
            for row in rows
        ]
    )
    assert "responder_eligible=true" not in serialized.lower()
    assert "awaiting_problem_specific_insight_review" in serialized
