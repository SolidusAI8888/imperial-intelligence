from fastapi.testclient import TestClient

from app.main import app


def test_auto_consult_unseen_question_returns_runtime_research_package():
    client = TestClient(app)
    question = "一个管理者发现团队连续犯同样的错误时，应该先换人还是先改制度？"

    response = client.post("/consult/auto", json={"question": question})

    assert response.status_code == 200
    body = response.json()
    assert body["proposed_problem_id"].startswith("Q-RESEARCH-")
    assert body["raw_question"] == question
    assert body["status"] == "research_package_requires_human_review"
    assert body["can_render_answer"] is False
    assert "selected_emperor_id" not in body
    assert all(candidate["responder_eligible"] is False for candidate in body["candidates"])
