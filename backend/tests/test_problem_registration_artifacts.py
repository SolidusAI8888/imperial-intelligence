from pathlib import Path

import yaml

from app.services.cross_dynasty_selector import CandidateExperience, score_candidate
from app.services.problem_draft_package import (
    build_problem_draft_package,
    persist_problem_draft_package,
)
from app.services.problem_knowledge_repository import load_problem_candidate_profile
from app.services.problem_registration_artifacts import (
    build_problem_registration_package,
    persist_problem_registration_package,
)


QUESTION = "一个人在职业低谷时，是应该坚持原来的方向，还是及时改变？"


def _write(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _reviewed_runtime_candidate() -> tuple[dict, float]:
    raw = load_problem_candidate_profile("Q-FATE-AGENCY-001")["candidates"][0]
    scores = dict(raw["scores"])
    scored = score_candidate(
        CandidateExperience(
            persona_id=raw["persona_id"],
            dynasty=raw["dynasty"],
            evidence_ids=tuple(raw["evidence_ids"]),
            experience_similarity=float(scores["experience_similarity"]),
            evidence_strength=float(scores["evidence_strength"]),
            stage_relevance=float(scores["stage_relevance"]),
            lesson_clarity=float(scores["lesson_clarity"]),
            transferability=float(scores["transferability"]),
            counterevidence_quality=float(scores["counterevidence_quality"]),
            rationale=raw["rationale"],
        )
    )
    return raw, scored.total_score


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

    reviewed, aggregate_score = _reviewed_runtime_candidate()
    candidate = profile["candidates"][0]
    candidate["person_id"] = reviewed["persona_id"]
    candidate["selected_insight_ids"] = list(reviewed["insight_ids"])
    candidate["candidate_score"] = aggregate_score
    candidate["responder_eligible"] = True
    candidate["registration_candidate"] = {
        "dynasty": reviewed["dynasty"],
        "evidence_ids": list(reviewed["evidence_ids"]),
        "heu_ids": list(reviewed["heu_ids"]),
        "insight_ids": list(reviewed["insight_ids"]),
        "scores": dict(reviewed["scores"]),
        "rationale": reviewed["rationale"],
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
    assert manifest["registration_audit"]["runtime_evidence_chain_validated"] is True
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


def test_registration_package_rejects_evidence_outside_reviewed_chain(tmp_path: Path) -> None:
    manifest_path, profile_path, _ = _review_ready_paths(tmp_path)
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile["candidates"][0]["registration_candidate"]["evidence_ids"] = ["NOT-IN-CHAIN"]
    _write(profile_path, profile)

    try:
        build_problem_registration_package(
            manifest_path,
            profile_path,
            registered_problem_id="Q-CAREER-DIRECTION-001",
        )
    except ValueError as exc:
        assert "outside its HER chain" in str(exc)
    else:
        raise AssertionError("out-of-chain evidence must block registration")


def test_registration_persistence_writes_profile_then_manifest_targets(tmp_path: Path) -> None:
    draft_root = tmp_path / "drafts"
    project_root = tmp_path / "project"
    manifest_path, profile_path, _ = _review_ready_paths(draft_root)
    package = build_problem_registration_package(
        manifest_path,
        profile_path,
        registered_problem_id="Q-CAREER-DIRECTION-001",
    )

    written_manifest, written_profile = persist_problem_registration_package(
        package,
        project_root=project_root,
    )

    assert written_manifest.exists()
    assert written_profile.exists()
    assert yaml.safe_load(written_manifest.read_text(encoding="utf-8"))["problem_id"] == package.registered_problem_id
    assert yaml.safe_load(written_profile.read_text(encoding="utf-8"))["problem_id"] == package.registered_problem_id


def test_registration_persistence_never_overwrites_existing_problem(tmp_path: Path) -> None:
    draft_root = tmp_path / "drafts"
    project_root = tmp_path / "project"
    manifest_path, profile_path, _ = _review_ready_paths(draft_root)
    package = build_problem_registration_package(
        manifest_path,
        profile_path,
        registered_problem_id="Q-CAREER-DIRECTION-001",
    )
    target_manifest = project_root / package.manifest.relative_path
    target_manifest.parent.mkdir(parents=True, exist_ok=True)
    target_manifest.write_text("existing: true\n", encoding="utf-8")

    try:
        persist_problem_registration_package(package, project_root=project_root)
    except FileExistsError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("existing registered Problems must never be overwritten")

    assert target_manifest.read_text(encoding="utf-8") == "existing: true\n"
    assert not (project_root / package.candidate_profile.relative_path).exists()
