from app.services.runtime_candidate_assessment import (
    RuntimeCandidateAssessment,
    _select_runtime_candidate,
)


def _candidate(
    person_id: str,
    *,
    candidate_score: float,
    recommended_eligible: bool,
    auto_answer_ready: bool,
) -> RuntimeCandidateAssessment:
    return RuntimeCandidateAssessment(
        person_id=person_id,
        retrieval_score=0.9,
        candidate_score=candidate_score,
        evidence_ids=("E1", "E2") if auto_answer_ready else ("E1",),
        heu_ids=("H1",),
        insight_ids=("I1",),
        conflicting_insight_ids=(),
        recommended_eligible=recommended_eligible,
        auto_answer_ready=auto_answer_ready,
        rationale="test candidate",
    )


def test_answer_ready_candidate_is_not_blocked_by_higher_ranked_incomplete_candidate() -> None:
    candidates = [
        _candidate("higher_score_incomplete", candidate_score=0.88, recommended_eligible=True, auto_answer_ready=False),
        _candidate("slightly_lower_score_but_ready", candidate_score=0.82, recommended_eligible=True, auto_answer_ready=True),
    ]
    selected = _select_runtime_candidate(candidates)
    assert selected is not None
    assert selected.person_id == "slightly_lower_score_but_ready"
    assert selected.auto_answer_ready is True


def test_highest_ranked_eligible_candidate_is_retained_when_nobody_can_answer() -> None:
    candidates = [
        _candidate("highest_eligible", candidate_score=0.71, recommended_eligible=True, auto_answer_ready=False),
        _candidate("lower_eligible", candidate_score=0.68, recommended_eligible=True, auto_answer_ready=False),
    ]
    selected = _select_runtime_candidate(candidates)
    assert selected is not None
    assert selected.person_id == "highest_eligible"
    assert selected.auto_answer_ready is False
