from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_new_problem_research_endpoint_returns_non_answerable_package() -> None:
    response = client.post(
        "/problems/research",
        json={
            "question": "一个人在职业低谷时，是应该坚持原来的方向，还是及时改变？",
            "candidate_limit": 10,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["proposed_problem_id"].startswith("Q-RESEARCH-")
    assert data["status"] == "research_package_requires_human_review"
    assert data["can_render_answer"] is False
    assert all(item["responder_eligible"] is False for item in data["candidates"])


def test_provisional_research_id_cannot_be_used_as_answer_permission() -> None:
    research = client.post(
        "/problems/research",
        json={"question": "面对不确定的环境，一个人应该如何决定下一步？"},
    )
    assert research.status_code == 200
    provisional_id = research.json()["proposed_problem_id"]

    answer = client.get(f"/problems/{provisional_id}/answer")
    assert answer.status_code == 404


def test_research_endpoint_rejects_candidate_limit_above_gate() -> None:
    response = client.post(
        "/problems/research",
        json={"question": "我该怎么选？", "candidate_limit": 51},
    )
    assert response.status_code == 422
