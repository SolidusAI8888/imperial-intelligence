from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from app.main import app
import app.services.problem_draft_readiness_service as readiness_service


client = TestClient(app)
DRAFT_ID = "Q-RESEARCH-0123456789ABCDEF"


def _write_blocked_draft(root: Path) -> None:
    target = root / DRAFT_ID
    target.mkdir(parents=True)
    (target / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "problem_id": DRAFT_ID,
                "raw_question": "职业方向怎么选？",
                "normalized_question": "职业方向怎么选？",
                "retrieval_dimensions": [],
                "review_gate": {
                    "problem_definition_reviewed": False,
                    "insight_selection_reviewed": False,
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (target / "candidate_profile.yaml").write_text(
        yaml.safe_dump(
            {
                "problem_id": DRAFT_ID,
                "candidates": [
                    {
                        "person_id": "tang_taizong",
                        "selected_insight_ids": [],
                        "candidate_score": None,
                        "responder_eligible": False,
                    }
                ],
                "approval_gate": {
                    "candidate_scoring_completed": False,
                    "responder_eligibility_reviewed": False,
                    "answer_permission": False,
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_readiness_api_reports_exact_blockers_without_promoting(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(readiness_service, "DRAFT_ROOT", tmp_path)
    _write_blocked_draft(tmp_path)

    response = client.get(f"/problems/drafts/{DRAFT_ID}/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["problem_id"] == DRAFT_ID
    assert data["ready"] is False
    assert data["status"] == "blocked_pending_problem_specific_review"
    assert "retrieval_dimensions_not_reviewed" in data["blockers"]
    assert "problem_definition_not_reviewed" in data["blockers"]
    assert "insight_selection_not_reviewed" in data["blockers"]
    assert "candidate_scoring_not_completed" in data["blockers"]
    assert "responder_eligibility_not_reviewed" in data["blockers"]
    assert "answer_permission_not_approved" in data["blockers"]
    assert "no_responder_eligible_candidate" in data["blockers"]

    manifest = yaml.safe_load((tmp_path / DRAFT_ID / "manifest.yaml").read_text(encoding="utf-8"))
    profile = yaml.safe_load(
        (tmp_path / DRAFT_ID / "candidate_profile.yaml").read_text(encoding="utf-8")
    )
    assert manifest["review_gate"]["problem_definition_reviewed"] is False
    assert profile["approval_gate"]["answer_permission"] is False
    assert profile["candidates"][0]["responder_eligible"] is False


def test_readiness_api_rejects_path_like_draft_id() -> None:
    response = client.get("/problems/drafts/..%2FQ-RESEARCH-0123456789ABCDEF/readiness")
    assert response.status_code in {404, 422}


def test_readiness_api_returns_404_for_missing_valid_draft(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(readiness_service, "DRAFT_ROOT", tmp_path)
    response = client.get(f"/problems/drafts/{DRAFT_ID}/readiness")
    assert response.status_code == 404
