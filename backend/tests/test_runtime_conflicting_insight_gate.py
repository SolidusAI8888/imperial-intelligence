from types import SimpleNamespace

import app.services.runtime_candidate_assessment as runtime_assessment


def test_conflicting_reviewed_insight_stops_auto_answer_without_hiding_candidate(monkeypatch) -> None:
    question = "团队管理出现问题时，应该先换人还是先改制度？"
    research = SimpleNamespace(
        proposed_problem_id="Q-RESEARCH-CONFLICT",
        normalized_question=question,
        candidates=(
            SimpleNamespace(person_id="candidate", heu_ids=("HEU-1",), retrieval_score=0.9),
        ),
    )
    heu = SimpleNamespace(
        heu_id="HEU-1",
        status="reviewed",
        record_links=("HER-1",),
        explicit_reflection=("reflection",),
        interpretation=("interpretation",),
    )
    supporting = SimpleNamespace(
        insight_id="INSIGHT-SUPPORT",
        status="reviewed",
        derived_from_heus=("HEU-1",),
        statement="团队制度失灵时，应先核实信息再决定是否更换人员。",
        applies_when=("团队制度调整与人员安排",),
        limits=("不适用于边疆粮道问题",),
    )
    conflicting = SimpleNamespace(
        insight_id="INSIGHT-CONFLICT",
        status="reviewed",
        derived_from_heus=("HEU-1",),
        statement="组织制度调整前应先判断信息质量。",
        applies_when=("团队管理与制度调整",),
        limits=("不适用于团队管理中的人员更换决策",),
    )
    record = SimpleNamespace(
        record_id="HER-1",
        status="reviewed",
        dynasty="tang",
        sources=(SimpleNamespace(canonical_ids=("CANON-1", "CANON-2")),),
    )
    role_link = SimpleNamespace(
        heu_id="HEU-1",
        responder_eligible=True,
        personal_experience_strength="primary",
    )

    monkeypatch.setattr(runtime_assessment, "build_problem_research_package", lambda *args, **kwargs: research)
    monkeypatch.setattr(runtime_assessment, "load_person_experiences", lambda person_id: [heu])
    monkeypatch.setattr(runtime_assessment, "load_person_insights", lambda person_id: [supporting, conflicting])
    monkeypatch.setattr(runtime_assessment, "load_person_records", lambda person_id: [record])
    monkeypatch.setattr(runtime_assessment, "load_person_role_links", lambda person_id: [role_link])
    monkeypatch.setattr(
        runtime_assessment,
        "score_candidate",
        lambda candidate: SimpleNamespace(total_score=0.9),
    )

    result = runtime_assessment.assess_runtime_problem(question)

    assert result.selected_person_id == "candidate"
    assert result.auto_answer_ready is False
    assert result.status == "automatic_assessment_complete_evidence_gate_not_ready"
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.recommended_eligible is True
    assert candidate.auto_answer_ready is False
    assert candidate.insight_ids == ("INSIGHT-SUPPORT",)
    assert "1 directly conflicting reviewed Insight(s)" in candidate.rationale


def test_partition_keeps_direct_counterevidence_visible() -> None:
    question = "团队管理出现问题时，应该先换人还是先改制度？"
    supporting = SimpleNamespace(
        statement="团队制度调整时先核实信息。",
        applies_when=("团队制度调整",),
        limits=("不适用于边疆粮道问题",),
    )
    conflicting = SimpleNamespace(
        statement="团队制度调整时先核实信息。",
        applies_when=("团队管理",),
        limits=("不适用于团队管理中的换人决策",),
    )

    usable, counterevidence = runtime_assessment._partition_problem_insights(
        question,
        [supporting, conflicting],
    )

    assert usable == [supporting]
    assert counterevidence == [conflicting]
