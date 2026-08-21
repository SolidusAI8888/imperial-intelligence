from types import SimpleNamespace

from app.services.runtime_candidate_assessment import _insight_relevant_to_question


def test_limits_are_counterevidence_not_positive_relevance_source() -> None:
    question = "团队管理出现问题时，应该先换人还是先改制度？"
    insight = SimpleNamespace(
        statement="边疆战事中应先稳定粮道，再决定是否继续进兵。",
        applies_when=("军事补给与边疆战争",),
        limits=("不适用于团队管理、组织制度或人员调整问题",),
    )

    assert _insight_relevant_to_question(question, insight) is False
