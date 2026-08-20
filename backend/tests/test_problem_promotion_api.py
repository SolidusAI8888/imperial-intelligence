from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.problem_draft_package import (
    build_problem_draft_package,
    persist_problem_draft_package,
)
from app.services.problem_promotion_service import promote_problem_draft


client = TestClient(app)
QUESTION = "一个人在职业低谷时，是应该坚持原来的方向，还是及时改变？"


def test_promotion_service_rejects_path_like_draft_id(tmp_path: Path) -> None:
    try:
        promote_problem_draft(
            "../../knowledge/problems/Q-FATE-AGENCY-001",
            "Q-CAREER-DIRECTION-001",
            draft_root=tmp_path,
        )
    except ValueError as exc:
        assert "Q-RESEARCH" in str(exc)
    else:
        raise AssertionError("path-like draft ids must be rejected")


def test_unreviewed_draft_cannot_be_promoted(tmp_path: Path) -> None:
    package = build_problem_draft_package(QUESTION, candidate_limit=10)
    persist_problem_draft_package(package, root=tmp_path)

    try:
        promote_problem_draft(
            package.problem_id,
            "Q-CAREER-DIRECTION-001",
            draft_root=tmp_path,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("an unreviewed draft must never produce registration artifacts")


def test_promotion_api_is_dry_run_by_default_and_reports_missing_draft() -> None:
    response = client.post(
        "/problems/promote",
        json={
            "draft_problem_id": "Q-RESEARCH-AAAAAAAAAAAA",
            "registered_problem_id": "Q-CAREER-DIRECTION-001",
        },
    )
    assert response.status_code == 404


def test_promotion_api_rejects_research_namespace_as_registered_id() -> None:
    response = client.post(
        "/problems/promote",
        json={
            "draft_problem_id": "Q-RESEARCH-AAAAAAAAAAAA",
            "registered_problem_id": "Q-RESEARCH-BBBBBBBBBBBB",
        },
    )
    assert response.status_code == 422
