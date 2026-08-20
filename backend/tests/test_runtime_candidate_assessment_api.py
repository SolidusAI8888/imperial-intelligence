from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_runtime_assessment_endpoint_returns_ranked_evidence_gated_candidates() -> None:
    response = client.post(
        "/problems/assess",
        json={
            "question": "一个人在职业低谷时，是应该坚持原来的方向，还是及时改变？",
            "candidate_limit": 20,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["problem_id"].startswith("Q-RESEARCH-")
    assert data["candidates"]
    assert data["status"] in {
        "automatic_candidate_selected_evidence_gate_ready",
        "automatic_assessment_complete_evidence_gate_not_ready",
    }
    scores = [item["candidate_score"] for item in data["candidates"]]
    assert scores == sorted(scores, reverse=True)
    assert all("recommended_eligible" in item for item in data["candidates"])
    assert all("auto_answer_ready" in item for item in data["candidates"])
