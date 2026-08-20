from fastapi.testclient import TestClient

from app.main import app


def test_unseen_auto_consultation_is_successful_research_not_422():
    client = TestClient(app)
    response = client.post(
        "/consult/auto",
        json={"question": "如果一个组织内部信息越来越失真，领导者应该先改汇报机制还是先换人？"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "research_package_requires_human_review"
    assert body["proposed_problem_id"].startswith("Q-RESEARCH-")
    assert body["can_render_answer"] is False
    assert body["required_next_gate"]
    assert all(item["responder_eligible"] is False for item in body["candidates"])
