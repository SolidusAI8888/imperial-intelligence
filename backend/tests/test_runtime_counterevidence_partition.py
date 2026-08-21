from types import SimpleNamespace

from app.services.runtime_candidate_assessment import _partition_problem_insights


def _insight(insight_id: str, statement: str, *, applies_when=(), limits=()):
    return SimpleNamespace(
        insight_id=insight_id,
        statement=statement,
        applies_when=applies_when,
        limits=limits,
    )


def test_limit_only_counterevidence_is_not_silently_ignored() -> None:
    question = "团队反复犯错时，领导者应该先换人还是先改制度？"
    supporting = _insight(
        "I-SUPPORT",
        "团队治理中先校正制度与反馈机制，再判断是否需要人员调整。",
        applies_when=("团队制度失灵",),
    )
    counterevidence = _insight(
        "I-LIMIT",
        "边疆战事中应先稳定粮道与军心。",
        limits=("不适用于团队治理、制度调整或人员更换问题",),
    )

    positive, conflicting = _partition_problem_insights(question, [supporting, counterevidence])

    assert [item.insight_id for item in positive] == ["I-SUPPORT"]
    assert [item.insight_id for item in conflicting] == ["I-LIMIT"]


def test_unrelated_limits_do_not_create_counterevidence() -> None:
    question = "团队反复犯错时，领导者应该先换人还是先改制度？"
    insight = _insight(
        "I-OTHER",
        "团队治理中先校正制度与反馈机制。",
        limits=("不适用于边疆粮道调度",),
    )

    positive, conflicting = _partition_problem_insights(question, [insight])

    assert [item.insight_id for item in positive] == ["I-OTHER"]
    assert conflicting == []
