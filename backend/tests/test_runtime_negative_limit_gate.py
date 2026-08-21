from types import SimpleNamespace

from app.services.runtime_candidate_assessment import (
    _insight_conflicts_with_question,
    _insight_relevant_to_question,
)


def test_matching_limit_blocks_otherwise_relevant_insight() -> None:
    question = "团队管理出现问题时，应该先换人还是先改制度？"
    insight = SimpleNamespace(
        statement="制度调整时应先判断信息是否真实，再决定是否更换人员。",
        applies_when=("组织制度调整与人员安排",),
        limits=("不适用于团队管理或团队人员调整",),
    )

    assert _insight_relevant_to_question(question, insight) is True
    assert _insight_conflicts_with_question(question, insight) is True


def test_unrelated_limit_does_not_block_relevant_insight() -> None:
    question = "团队管理出现问题时，应该先换人还是先改制度？"
    insight = SimpleNamespace(
        statement="制度调整时应先判断信息是否真实，再决定是否更换人员。",
        applies_when=("团队制度调整与人员安排",),
        limits=("不适用于边疆军事补给或战场粮道问题",),
    )

    assert _insight_relevant_to_question(question, insight) is True
    assert _insight_conflicts_with_question(question, insight) is False
