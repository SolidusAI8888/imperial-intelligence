import pytest

from app.services.problem_response_pipeline import (
    build_grounded_response_bundle,
    build_problem_response_plan,
    build_selected_runtime_context,
)


FIRST_PROBLEM_ID = "Q-FATE-AGENCY-001"


def test_reviewed_problem_selects_ranked_responder() -> None:
    plan = build_problem_response_plan(FIRST_PROBLEM_ID)
    assert plan.person_id == "tang_taizong"
    assert plan.total_score > 0
    assert plan.evidence_ids
    assert plan.heu_ids
    assert plan.insight_ids
    assert plan.status == "responder_selected_from_reviewed_problem_profile"


def test_selected_runtime_context_uses_only_profile_chain() -> None:
    plan = build_problem_response_plan(FIRST_PROBLEM_ID)
    context = build_selected_runtime_context(FIRST_PROBLEM_ID)
    assert context.person_id == plan.person_id
    assert {heu.heu_id for heu in context.experiences} == set(plan.heu_ids)
    assert {insight.insight_id for insight in context.insights} == set(plan.insight_ids)


def test_grounded_bundle_reconciles_canonical_evidence() -> None:
    bundle = build_grounded_response_bundle(FIRST_PROBLEM_ID)
    assert bundle.plan.person_id == "tang_taizong"
    assert bundle.evidence_ids == bundle.plan.evidence_ids
    assert bundle.insight_statements
    assert bundle.grounded_context
    assert bundle.status == "ready_for_grounded_answer_generation"


def test_unknown_problem_cannot_skip_problem_specific_review() -> None:
    with pytest.raises(KeyError):
        build_problem_response_plan("Q-UNREVIEWED-NEW-PROBLEM")
