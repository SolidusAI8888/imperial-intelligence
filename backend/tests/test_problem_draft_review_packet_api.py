from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from app.main import app
import app.services.problem_draft_readiness_service as readiness_service


client = TestClient(app)
DRAFT_ID = "Q-RESEARCH-FEDCBA9876543210"


def _write_draft(root: Path) -> None:
    target = root / DRAFT_ID
    target.mkdir(parents=True)
    (target / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "problem_id": DRAFT_ID,
                "raw_question": "成功之后为什么反而容易犯错？",
                "normalized_question": "成功后的风险与自我约束",
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
                        "recalled_heu_ids": ["HEU-TANG-000001", "HEU-TANG-000003"],
                        "retrieval_score": 0.75,
                        "review_priority": 1,
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


def test_review_packet_surfaces_reviewed_heus_and_existing_insight_as_suggestion(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(readiness_service, "DRAFT_ROOT", tmp_path)
    _write_draft(tmp_path)

    response = client.get(f"/problems/drafts/{DRAFT_ID}/review-packet")
    assert response.status_code == 200
    data = response.json()
    assert data["problem_id"] == DRAFT_ID
    assert data["status"] == "human_review_packet_no_automatic_approval"
    assert data["readiness_status"] == "blocked_pending_problem_specific_review"
    assert data["candidates"][0]["person_id"] == "tang_taizong"
    assert data["candidates"][0]["responder_eligible"] is False
    assert data["candidates"][0]["selected_insight_ids"] == []
    assert data["candidates"][0]["candidate_score"] is None

    heu_ids = {item["heu_id"] for item in data["candidates"][0]["recalled_heus"]}
    assert heu_ids == {"HEU-TANG-000001", "HEU-TANG-000003"}
    assert all(item["status"] in {"reviewed", "accepted"} for item in data["candidates"][0]["recalled_heus"])

    suggestions = data["candidates"][0]["existing_insight_suggestions"]
    assert any(item["insight_id"] == "INS-TANG-000001" for item in suggestions)
    assert all(
        item["status"] == "suggestion_only_requires_problem_specific_review"
        for item in suggestions
    )

    profile = yaml.safe_load(
        (tmp_path / DRAFT_ID / "candidate_profile.yaml").read_text(encoding="utf-8")
    )
    assert profile["candidates"][0]["selected_insight_ids"] == []
    assert profile["candidates"][0]["responder_eligible"] is False
    assert profile["approval_gate"]["answer_permission"] is False


def test_review_packet_rejects_unavailable_recalled_heu(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(readiness_service, "DRAFT_ROOT", tmp_path)
    _write_draft(tmp_path)
    profile_path = tmp_path / DRAFT_ID / "candidate_profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile["candidates"][0]["recalled_heu_ids"].append("HEU-TANG-999999")
    profile_path.write_text(yaml.safe_dump(profile, allow_unicode=True, sort_keys=False), encoding="utf-8")

    response = client.get(f"/problems/drafts/{DRAFT_ID}/review-packet")
    assert response.status_code == 422
    assert "unavailable/unreviewed recalled HEUs" in response.json()["detail"]
