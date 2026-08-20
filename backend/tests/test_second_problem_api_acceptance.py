from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
PROBLEM_ID = "Q-CAREER-PIVOT-001"


def test_second_problem_answer_api_uses_selected_responder():
    response = client.get(f"/problems/{PROBLEM_ID}/answer")
    assert response.status_code == 200
    data = response.json()
    assert data["problem_id"] == PROBLEM_ID
    assert data["person_id"] == "tang_gaozu"
    assert data["status"] == "rendered_from_reviewed_grounded_bundle"
    assert data["evidence_ids"]


def test_second_problem_continue_api_keeps_role_then_reroutes_drift():
    followup = client.post(
        f"/problems/{PROBLEM_ID}/continue",
        json={
            "question": "你刚才说要根据新信息修正决定，那我该怎么看自己是不是只是在逃避失败？",
            "conversation_history": [
                {"role": "user", "content": "一个人在职业低谷时，是应该坚持原来的方向，还是及时改变？"},
                {"role": "assistant", "content": "先判断原路径是否仍有效，并允许根据新信息修正。"},
            ],
        },
    )
    assert followup.status_code == 200
    followup_data = followup.json()
    assert followup_data["route"] == "continue_current_responder"
    assert followup_data["person_id"] == "tang_gaozu"

    drift = client.post(
        f"/problems/{PROBLEM_ID}/continue",
        json={"question": "宋代财政制度是怎样设计的？", "conversation_history": []},
    )
    assert drift.status_code == 200
    drift_data = drift.json()
    assert drift_data["route"] == "new_problem_required"
    assert drift_data["requires_new_problem"] is True
    assert drift_data["research_package"]["proposed_problem_id"].startswith("Q-RESEARCH-")
    assert drift_data["research_package"]["can_render_answer"] is False
