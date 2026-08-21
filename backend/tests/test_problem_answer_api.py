from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_reviewed_problem_answer_endpoint_uses_grounded_renderer() -> None:
    response = client.get("/problems/Q-FATE-AGENCY-001/answer")
    assert response.status_code == 200
    data = response.json()
    assert data["problem_id"] == "Q-FATE-AGENCY-001"
    assert data["person_id"] == "tang_taizong"
    assert data["historical_voice"]
    assert data["modern_translation"]
    assert data["evidence_ids"]
    assert data["insight_ids"]
    assert data["voice_evidence_ids"] == []
    assert data["status"] == "rendered_from_reviewed_grounded_bundle"
    assert "CN-" not in data["historical_voice"]


def test_unknown_problem_answer_endpoint_is_not_allowed_to_borrow_review() -> None:
    response = client.get("/problems/Q-UNREVIEWED-NEW-PROBLEM/answer")
    assert response.status_code == 404
