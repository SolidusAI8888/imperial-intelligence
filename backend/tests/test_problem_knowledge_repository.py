import pytest

from app.services.problem_knowledge_repository import (
    load_problem_candidate_profile,
    load_problem_spec,
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
