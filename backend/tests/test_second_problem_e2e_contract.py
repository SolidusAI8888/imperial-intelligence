from app.services.cross_dynasty_selector import problem_candidates, rank_candidates
from app.services.problem_knowledge_repository import load_problem_spec


def test_second_problem_does_not_inherit_first_problem_ranking_contract():
    spec = load_problem_spec("Q-CAREER-PIVOT-001")
    assert spec.raw_question.startswith("一个人在职业低谷时")
    assert spec.problem_id != "Q-FATE-AGENCY-001"

    ranked = rank_candidates(problem_candidates(spec.problem_id))
    assert [item.persona_id for item in ranked[:3]] == [
        "tang_gaozu",
        "tang_taizong",
        "liu_bang",
    ]
