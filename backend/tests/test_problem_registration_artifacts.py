from pathlib import Path

import yaml

from app.services.problem_draft_package import (
    build_problem_draft_package,
    persist_problem_draft_package,
)
from app.services.problem_registration_artifacts import build_problem_registration_package


QUESTION = "一个人在职业低谷时，是应该坚持原来的方向，还是及时改变？"


def _write(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _review_ready_paths(tmp_path: Path) -> tuple[Path, Path, str]:
    package = build_problem_draft_package(QUESTION, candidate_limit=5)
    manifest_path, profile_path = persist_problem_draft_package(package, root=tmp_path)
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))

    manifest["retrieval_dimensions"] = ["方向调整", "长期坚持与策略变化"]
    manifest["review_gate"]["problem_definition_reviewed"] = True
    manifest["review_gate"]["insight_selection_reviewed"] = True
    profile["approval_gate"] = {
        "candidate_scoring_completed": True,
        "responder_eligibility_reviewed": True,
        "answer_permission": True,
    }

    candidate = profile["candidates"][0]
    insight_id = "INS-REVIEWED-EXAMPLE"
    candidate["selected_insight_ids"] = [insight_id]
    candidate["candidate_score"] = 0.8
    candidate["responder_eligible"] = True
    candidate["registration_candidate"] = {
        "dynasty": "唐",
        "evidence_ids": ["SRC-EXAMPLE-001"],
        "heu_ids": [candidate["recalled_heu_ids"][0]],
        "insight_ids": [insight_id],
        "scores": {
            "experience_similarity": 0.8,
            "evidence_strength": 0.9,
            "stage_relevance": 0.7,
            "lesson_clarity": 0.8,
            "transferability": 0.8,
            "counterevidence_quality": 0.6,
        },
        "rationale": "Reviewed example payload for registration structure.",
    }
    _write(manifest_path, manifest)
    _write(profile_path, profile)
    return manifest_path, profile_path, package.problem_id


def test_registration_package_rewrites_provisional_id_and_paths(tmp_path: Path) -> None:
    manifest_path, profile_path, source_id = _review_ready_paths(tmp_path)

    package = build_problem_registration_package(
        manifest_path,
        profile_path,
        registered_problem_id="Q-CAREER-DIRECTION-001",
    )

    manifest = yaml.safe_load(package.manifest.content)
    profile = yaml.safe_load(package.candidate_profile.content)

    assert package.source_draft_problem_id == source_id
    assert package.registered_problem_id == "Q-CAREER-DIRECTION-001"
    assert package.manifest.relative_path == "knowledge/problems/Q-CAREER-DIRECTION-001.yaml"
    assert package.candidate_profile.relative_path == "knowledge/problem_profiles/Q-CAREER-DIRECTION-001.yaml"
    assert manifest["problem_id"] == "Q-CAREER-DIRECTION-001"
    assert manifest["candidate_profile"] == package.candidate_profile.relative_path
    assert manifest["status"] == "registered_reviewed"
    assert manifest["registration_audit"]["source_draft_problem_id"] == source_id
    assert profile["problem_id"] == "Q-CAREER-DIRECTION-001"
    assert len(profile["candidates"]) == 1
    assert profile["candidates"][0]["persona_id"]
    assert "responder_eligible" not in profile["candidates"][0]


def test_registration_package_refuses_unreviewed_draft(tmp_path: Path) -> None:
    package = build_problem_draft_package(QUESTION, candidate_limit=5)
    manifest_path, profile_path = persist_problem_draft_package(package, root=tmp_path)

    try:
        build_problem_registration_package(
            manifest_path,
            profile_path,
            registered_problem_id="Q-CAREER-DIRECTION-001",
        )
    except ValueError as exc:
        assert "not ready for registration" in str(exc)
    else:
        raise AssertionError("unreviewed draft must not generate registration artifacts")


def test_registration_package_refuses_provisional_target_id(tmp_path: Path) -> None:
    manifest_path, profile_path, source_id = _review_ready_paths(tmp_path)

    try:
        build_problem_registration_package(
            manifest_path,
            profile_path,
            registered_problem_id=source_id,
        )
    except ValueError as exc:
        assert "provisional" in str(exc)
    else:
        raise AssertionError("provisional IDs must not be registered")
