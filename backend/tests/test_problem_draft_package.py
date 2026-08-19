from pathlib import Path

import yaml

from app.services.problem_draft_package import (
    build_problem_draft_package,
    persist_problem_draft_package,
)


QUESTION = "一个人在职业低谷时，是应该坚持原来的方向，还是及时改变？"


def test_draft_package_preserves_evidence_gates() -> None:
    package = build_problem_draft_package(QUESTION, candidate_limit=10)

    assert package.status == "draft_package_requires_human_review"
    assert package.responder_eligible is False
    assert package.can_render_answer is False
    assert package.problem_id.startswith("Q-RESEARCH-")

    manifest = yaml.safe_load(package.manifest.content)
    profile = yaml.safe_load(package.candidate_profile.content)

    assert manifest["status"] == "draft_requires_problem_specific_review"
    assert manifest["review_gate"]["required"] is True
    assert manifest["review_gate"]["can_render_answer"] is False
    assert manifest["review_gate"]["responder_eligibility_locked"] is True
    assert profile["status"] == "draft_research_candidates_only"
    assert profile["approval_gate"]["candidate_scoring_completed"] is False
    assert profile["approval_gate"]["responder_eligibility_reviewed"] is False
    assert profile["approval_gate"]["answer_permission"] is False
    assert all(candidate["responder_eligible"] is False for candidate in profile["candidates"])


def test_persist_draft_package_writes_only_under_supplied_draft_root(tmp_path: Path) -> None:
    package = build_problem_draft_package(QUESTION, candidate_limit=5)
    manifest_path, profile_path = persist_problem_draft_package(package, root=tmp_path)

    assert manifest_path == tmp_path / package.problem_id / "manifest.yaml"
    assert profile_path == tmp_path / package.problem_id / "candidate_profile.yaml"
    assert manifest_path.exists()
    assert profile_path.exists()
    assert yaml.safe_load(manifest_path.read_text(encoding="utf-8"))["problem_id"] == package.problem_id


def test_persist_draft_package_refuses_silent_overwrite(tmp_path: Path) -> None:
    package = build_problem_draft_package(QUESTION, candidate_limit=5)
    persist_problem_draft_package(package, root=tmp_path)

    try:
        persist_problem_draft_package(package, root=tmp_path)
    except FileExistsError as exc:
        assert package.problem_id in str(exc)
    else:
        raise AssertionError("Existing draft packages must be protected by default")
