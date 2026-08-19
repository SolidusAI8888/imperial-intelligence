from app.services.problem_candidate_shortlist import build_candidate_research_shortlist


def test_problem_candidate_shortlist_smoke() -> None:
    rows = build_candidate_research_shortlist(
        "面对时代变化，个人还能改变多少自己的处境？",
        candidate_limit=5,
    )
    assert isinstance(rows, list)
