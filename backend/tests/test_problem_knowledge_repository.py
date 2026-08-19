import pytest

from app.services.problem_knowledge_repository import (
    load_problem_candidate_profile,
    load_problem_spec,
    validate_registered_problem_manifest,
)


def test_first_problem_declares_reusable_experience_layers() -> None:
    spec = load_problem_spec("Q-FATE-AGENCY-001")
    assert {"HER", "HEU"}.issubset(set(spec.reusable_layers))
    assert {
        "insight_selection",
        "candidate_scoring",
        "responder_eligibility",
    }.issubset(set(spec.problem_specific_layers))
    assert spec.raw_question.startswith("面对浩瀚的历史")


def test_problem_manifest_resolves_problem_specific_candidate_profile() -> None:
    profile = load_problem_candidate_profile("Q-FATE-AGENCY-001")
    assert profile["problem_id"] == "Q-FATE-AGENCY-001"
    assert len(profile["candidates"]) >= 8
    assert all("heu_ids" in item and "insight_ids" in item for item in profile["candidates"])


def test_unknown_problem_does_not_reuse_first_question_eligibility() -> None:
    with pytest.raises(KeyError, match="Unknown problem_id"):
        load_problem_spec("Q-UNREGISTERED-999")


def test_provisional_research_id_cannot_be_registered() -> None:
    with pytest.raises(ValueError, match="provisional research ID"):
        validate_registered_problem_manifest(
            {
                "problem_id": "Q-RESEARCH-ABC123",
                "status": "retrieval_ready",
                "candidate_profile": "knowledge/research/example.yaml",
            }
        )


def test_draft_status_cannot_be_registered() -> None:
    with pytest.raises(ValueError, match="non-registered status"):
        validate_registered_problem_manifest(
            {
                "problem_id": "Q-CAREER-001",
                "status": "draft_requires_problem_specific_review",
                "candidate_profile": "knowledge/research/example.yaml",
            }
        )


def test_candidate_profile_cannot_point_to_draft_area() -> None:
    with pytest.raises(ValueError, match="non-authoritative draft area"):
        validate_registered_problem_manifest(
            {
                "problem_id": "Q-CAREER-001",
                "status": "retrieval_ready",
                "candidate_profile": "knowledge/problem_drafts/Q-CAREER-001/candidate_profile.yaml",
            }
        )
