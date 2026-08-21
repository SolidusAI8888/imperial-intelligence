from fastapi.testclient import TestClient

from app.main import app
from app.services.runtime_explainability import explain_runtime_problem


client = TestClient(app)


def test_runtime_explanation_exposes_ranked_evidence_gate_decision() -> None:
    question = "一个人在职业低谷时，是应该坚持原来的方向，还是及时改变？"
    result = explain_runtime_problem(question, candidate_limit=20)

    assert result.problem_id.startswith("Q-RESEARCH-")
    assert result.question == question
    assert result.status == "runtime_selection_explanation_read_only"
    assert result.candidates
    assert [item.rank for item in result.candidates] == list(range(1, len(result.candidates) + 1))
    assert [item.candidate_score for item in result.candidates] == sorted([item.candidate_score for item in result.candidates], reverse=True)
    assert all(item.selection_reason for item in result.candidates)
    assert all(isinstance(item.conflicting_insight_ids, tuple) for item in result.candidates)
    assert all(isinstance(item.voice_evidence_ids, tuple) for item in result.candidates)
    assert result.decision_summary
    if result.selected_person_id is not None:
        selected = next(item for item in result.candidates if item.person_id == result.selected_person_id)
        assert selected.recommended_eligible is True
        assert selected.selection_reason.startswith("selected as")


def test_runtime_explanation_endpoint_is_read_only_and_auditable() -> None:
    question = "团队反复犯同样的错误时，领导者应该先换人还是先改制度？"
    response = client.post("/problems/explain", json={"question": question, "candidate_limit": 10})

    assert response.status_code == 200
    data = response.json()
    assert data["problem_id"].startswith("Q-RESEARCH-")
    assert data["question"] == question
    assert data["status"] == "runtime_selection_explanation_read_only"
    assert data["candidates"]
    assert all("gate_blockers" in candidate for candidate in data["candidates"])
    assert all("evidence_ids" in candidate for candidate in data["candidates"])
    assert all("heu_ids" in candidate for candidate in data["candidates"])
    assert all("insight_ids" in candidate for candidate in data["candidates"])
    assert all("conflicting_insight_ids" in candidate for candidate in data["candidates"])
    assert all("voice_evidence_ids" in candidate for candidate in data["candidates"])
