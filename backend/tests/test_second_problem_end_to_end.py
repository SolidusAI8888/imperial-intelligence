from app.services.cross_dynasty_selector import rank_candidates, problem_candidates
from app.services.grounded_answer_renderer import render_grounded_answer
from app.services.problem_conversation_service import continue_problem_conversation


PROBLEM_ID = "Q-CAREER-PIVOT-001"


def test_second_problem_selects_tang_gaozu_from_real_reviewed_knowledge():
    ranked = rank_candidates(problem_candidates(PROBLEM_ID))
    assert len(ranked) >= 3
    assert ranked[0].persona_id == "tang_gaozu"
    assert ranked[0].total_score > ranked[1].total_score


def test_second_problem_renders_real_grounded_answer():
    answer = render_grounded_answer(PROBLEM_ID)
    assert answer.problem_id == PROBLEM_ID
    assert answer.person_id == "tang_gaozu"
    assert answer.evidence_ids
    assert "INS-TANG-000003" in answer.insight_ids
    assert "原有路径" in answer.historical_voice or "修正" in answer.historical_voice


def test_second_problem_continues_with_same_responder_for_related_followup():
    turn = continue_problem_conversation(
        PROBLEM_ID,
        "你刚才说可以根据新信息修正决定，那怎么判断我是在理性调整，而不是因为受挫就逃避？",
        conversation_history=(
            "一个人在职业低谷时，是应该坚持原来的方向，还是及时改变？",
            "应区分原路径是否仍有效，并允许根据新信息修正决定。",
        ),
    )
    assert turn.route == "continue_current_responder"
    assert turn.person_id == "tang_gaozu"
    assert turn.requires_new_problem is False
    assert turn.evidence_ids


def test_second_problem_routes_material_topic_change_to_fresh_research():
    turn = continue_problem_conversation(
        PROBLEM_ID,
        "宋代财政制度是怎样设计的？",
        continuity_threshold=0.30,
    )
    assert turn.route == "new_problem_required"
    assert turn.requires_new_problem is True
    assert turn.research_package is not None
    assert turn.research_package.proposed_problem_id.startswith("Q-RESEARCH-")
    assert turn.research_package.can_render_answer is False
