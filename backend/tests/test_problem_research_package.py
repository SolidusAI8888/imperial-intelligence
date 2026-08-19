from app.services.problem_research_package import (
    build_problem_research_package,
    normalize_research_question,
    provisional_problem_id,
)


QUESTION = "  一个人在职业低谷时，  是应该坚持原来的方向，还是及时改变？  "


def test_research_question_normalization_and_id_are_deterministic() -> None:
    normalized = normalize_research_question(QUESTION)
    assert normalized == "一个人在职业低谷时， 是应该坚持原来的方向，还是及时改变？"
    assert provisional_problem_id(QUESTION) == provisional_problem_id(normalized)
    assert provisional_problem_id(QUESTION).startswith("Q-RESEARCH-")


def test_new_problem_package_never_grants_answer_permission() -> None:
    package = build_problem_research_package(QUESTION, candidate_limit=10)
    assert package.status == "research_package_requires_human_review"
    assert package.can_render_answer is False
    assert package.proposed_problem_id.startswith("Q-RESEARCH-")
    assert all(candidate.responder_eligible is False for candidate in package.candidates)
    assert all(
        candidate.status == "research_candidate_requires_problem_specific_review"
        for candidate in package.candidates
    )
    assert "Problem manifest" in package.required_next_gate


def test_even_known_question_research_intake_does_not_inherit_eligibility() -> None:
    package = build_problem_research_package(
        "面对浩瀚的历史和剧烈的时代变革，个体的命运到底由谁主宰？",
        candidate_limit=20,
    )
    assert package.can_render_answer is False
    assert all(candidate.responder_eligible is False for candidate in package.candidates)


def test_candidate_limit_is_bounded() -> None:
    try:
        build_problem_research_package(QUESTION, candidate_limit=51)
    except ValueError as exc:
        assert "between 1 and 50" in str(exc)
    else:
        raise AssertionError("candidate_limit above 50 must be rejected")
