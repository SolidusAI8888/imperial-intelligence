from pathlib import Path

import yaml

from app.services.problem_draft_package import (
    build_problem_draft_package,
    persist_problem_draft_package,
)
from app.services.problem_promotion_readiness import assess_problem_draft_promotion


QUESTION = "一个人在职业低谷时，是应该坚持原来的方向，还是及时改变？"


def _write(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_fresh_draft_is_blocked_from_promotion(tmp_path: Path) -> None:
    package = build_problem_draft_package(QUESTION, candidate_limit=5)
    manifest_path, profile_path = persist_problem_draft_package(package, root=tmp_path)

    result = assess_problem_draft_promotion(manifest_path, profile_path)

    assert result.ready is False
    assert result.status == "blocked_pending_problem_specific_review"
    assert "problem_definition_not_reviewed" in result.blockers
    assert "insight_selection_not_reviewed" in result.blockers
    assert "candidate_scoring_not_completed" in result.blockers
    assert "responder_eligibility_not_reviewed" in result.blockers
    assert "answer_permission_not_approved" in result.blockers


def test_reviewed_draft_can_be_marked_ready_without_being_promoted(tmp_path: Path) -> None:
    package = build_problem_draft_package(QUESTION, candidate_limit=5)
    manifest_path, profile_path = persist_problem_draft_package(package, root=tmp_path)

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))

    manifest["review_gate"]["problem_definition_reviewed"] = True
    manifest["review_gate"]["insight_selection_reviewed"] = True
    profile["approval_gate"]["candidate_scoring_completed"] = True
    profile["approval_gate"]["responder_eligibility_reviewed"] = True
    profile["approval_gate"]["answer_permission"] = True

    candidate = profile["candidates"][0]
    candidate["selected_insight_ids"] = ["INS-REVIEWED-EXAMPLE"]
    candidate["candidate_score"] = 0.8
    candidate["responder_eligible"] = True

    _write(manifest_path, manifest)
    _write(profile_path, profile)

    result = assess_problem_draft_promotion(manifest_path, profile_path)

    assert result.ready is True
    assert result.blockers == ()
    assert result.status == "ready_for_explicit_registration_review"
    assert manifest_path.exists()
    assert profile_path.exists()


def test_eligible_candidate_requires_reviewed_insight_and_score(tmp_path: Path) -> None:
    package = build_problem_draft_package(QUESTION, candidate_limit=5)
    manifest_path, profile_path = persist_problem_draft_package(package, root=tmp_path)
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))

    manifest["review_gate"]["problem_definition_reviewed"] = True
    manifest["review_gate"]["insight_selection_reviewed"] = True
    profile["approval_gate"] = {
        "candidate_scoring_completed": True,
        "responder_eligibility_reviewed": True,
        "answer_permission": True,
    }
    profile["candidates"][0]["responder_eligible"] = True
    _write(manifest_path, manifest)
    _write(profile_path, profile)

    result = assess_problem_draft_promotion(manifest_path, profile_path)

    assert result.ready is False
    assert any(blocker.startswith("eligible_candidate_missing_selected_insights:") for blocker in result.blockers)
    assert any(blocker.startswith("eligible_candidate_missing_score:") for blocker in result.blockers)
