from types import SimpleNamespace

from app.services.runtime_candidate_assessment import _insight_relevant_to_question


def _insight(statement: str, *, applies_when: tuple[str, ...] = (), limits: tuple[str, ...] = ()):
    return SimpleNamespace(statement=statement, applies_when=applies_when, limits=limits)


def test_runtime_insight_gate_accepts_problem_relevant_insight() -> None:
    question = "团队反复犯同样的错误时，领导者应该先换人还是先改制度？"
    insight = _insight(
        "当组织反复出现相同错误时，应先检查制度与信息反馈机制，再判断是否属于个人能力问题。",
        applies_when=("团队重复犯错且流程可能存在缺陷",),
    )

    assert _insight_relevant_to_question(question, insight) is True


def test_runtime_insight_gate_rejects_unrelated_insight_from_same_recalled_experience() -> None:
    question = "团队反复犯同样的错误时，领导者应该先换人还是先改制度？"
    insight = _insight(
        "面对边疆军事威胁时，集中兵力与明确后勤路线比追求短期声势更重要。",
        applies_when=("边疆战争与军事部署",),
        limits=("不适用于纯粹的组织人事治理",),
    )

    assert _insight_relevant_to_question(question, insight) is False


def test_runtime_insight_gate_uses_application_conditions_not_only_statement() -> None:
    question = "创业失败以后，是继续原项目还是换一个方向？"
    insight = _insight(
        "先识别哪些条件仍可改变，再决定是否坚持。",
        applies_when=("创业方向需要在坚持与转向之间做选择",),
    )

    assert _insight_relevant_to_question(question, insight) is True


def test_runtime_insight_gate_does_not_treat_negative_limit_as_positive_relevance() -> None:
    question = "团队管理出现问题时，应该先换人还是先改制度？"
    insight = _insight(
        "边疆战事中应先稳定粮道，再决定是否继续进兵。",
        applies_when=("军事补给与边疆战争",),
        limits=("不适用于团队管理、组织制度或人员调整问题",),
    )

    assert _insight_relevant_to_question(question, insight) is False


def test_runtime_insight_gate_keeps_relevant_insight_even_when_limits_are_present() -> None:
    question = "团队管理出现问题时，应该先换人还是先改制度？"
    insight = _insight(
        "团队管理反复失灵时，应先检查制度与反馈机制，再判断是否需要换人。",
        applies_when=("组织治理与人员调整",),
        limits=("不适用于紧急军事指挥",),
    )

    assert _insight_relevant_to_question(question, insight) is True
