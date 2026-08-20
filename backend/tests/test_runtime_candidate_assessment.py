from app.services.runtime_candidate_assessment import assess_runtime_problem


def test_runtime_assessment_scores_reviewed_candidates_for_unregistered_problem() -> None:
    question = "一个人在职业低谷时，是应该坚持原来的方向，还是及时改变？"
    result = assess_runtime_problem(question, candidate_limit=20)

    assert result.problem_id.startswith("Q-RESEARCH-")
    assert result.question == question
    assert result.status in {
        "automatic_candidate_selected_evidence_gate_ready",
        "automatic_assessment_complete_evidence_gate_not_ready",
    }
    assert result.candidates
    assert all(0 <= item.retrieval_score <= 1 for item in result.candidates)
    assert all(0 <= item.candidate_score <= 1 for item in result.candidates)
    assert all(item.heu_ids for item in result.candidates)
    assert [item.candidate_score for item in result.candidates] == sorted(
        [item.candidate_score for item in result.candidates], reverse=True
    )
    if result.selected_person_id is not None:
        selected = next(item for item in result.candidates if item.person_id == result.selected_person_id)
        assert selected.recommended_eligible is True


def test_runtime_assessment_is_deterministic_for_same_question() -> None:
    question = "团队反复犯同样的错误时，领导者应该先换人还是先改制度？"
    first = assess_runtime_problem(question, candidate_limit=10)
    second = assess_runtime_problem(question, candidate_limit=10)

    assert first.problem_id == second.problem_id
    assert first.selected_person_id == second.selected_person_id
    assert [
        (item.person_id, item.candidate_score, item.recommended_eligible)
        for item in first.candidates
    ] == [
        (item.person_id, item.candidate_score, item.recommended_eligible)
        for item in second.candidates
    ]
