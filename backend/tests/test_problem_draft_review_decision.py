from types import SimpleNamespace

import yaml

from app.services.problem_draft_review_decision import apply_problem_draft_review_decision
from app.services.problem_draft_review_packet import (
    DraftCandidateReviewPacket,
    ExistingInsightSuggestion,
    ProblemDraftReviewPacket,
)


def _packet() -> ProblemDraftReviewPacket:
    suggestion = ExistingInsightSuggestion(
        insight_id="INS-TEST-001",
        statement="reviewed statement",
        derived_from_heus=("HEU-TEST-001",),
        applies_when=("test",),
        limits=("limit",),
        status="suggestion_only_requires_problem_specific_review",
    )
    candidate = DraftCandidateReviewPacket(
        person_id="test_person",
        review_priority=1,
        retrieval_score=0.8,
        recalled_heus=(),
        existing_insight_suggestions=(suggestion,),
        selected_insight_ids=(),
        candidate_score=None,
        responder_eligible=False,
        status="review_packet_only_no_approval_side_effects",
    )
    return ProblemDraftReviewPacket(
        problem_id="Q-RESEARCH-TEST",
        raw_question="test?",
        normalized_question="test",
        retrieval_dimensions=(),
        candidates=(candidate,),
        readiness_status="blocked",
        readiness_blockers=("review",),
        status="human_review_packet_no_automatic_approval",
    )


def _files(tmp_path):
    manifest_path = tmp_path / "manifest.yaml"
    profile_path = tmp_path / "candidate_profile.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "problem_id": "Q-RESEARCH-TEST",
                "retrieval_dimensions": [],
                "review_gate": {
                    "problem_definition_reviewed": False,
                    "insight_selection_reviewed": False,
                    "can_render_answer": False,
                    "responder_eligibility_locked": True,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    profile_path.write_text(
        yaml.safe_dump(
            {
                "problem_id": "Q-RESEARCH-TEST",
                "candidates": [
                    {
                        "person_id": "test_person",
                        "selected_insight_ids": [],
                        "candidate_score": None,
                        "responder_eligible": False,
                    }
                ],
                "approval_gate": {
                    "candidate_scoring_completed": False,
                    "responder_eligibility_reviewed": False,
                    "answer_permission": False,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return manifest_path, profile_path


def test_review_decision_persists_only_review_fields(monkeypatch, tmp_path) -> None:
    manifest_path, profile_path = _files(tmp_path)
    monkeypatch.setattr(
        "app.services.problem_draft_review_decision.build_problem_draft_review_packet",
        lambda _: _packet(),
    )
    monkeypatch.setattr(
        "app.services.problem_draft_review_decision.inspect_problem_draft_readiness",
        lambda _: SimpleNamespace(
            manifest_path=str(manifest_path), candidate_profile_path=str(profile_path)
        ),
    )

    result = apply_problem_draft_review_decision(
        "Q-RESEARCH-TEST",
        reviewer="historian@example",
        retrieval_dimensions=["career transition", "constraint vs agency"],
        selected_insight_ids_by_person={"test_person": ["INS-TEST-001"]},
        problem_definition_reviewed=True,
        insight_selection_reviewed=True,
        persist=True,
    )

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    candidate = profile["candidates"][0]
    assert result.persisted is True
    assert result.responder_eligibility_changed is False
    assert result.answer_permission_changed is False
    assert manifest["review_gate"]["problem_definition_reviewed"] is True
    assert manifest["review_gate"]["insight_selection_reviewed"] is True
    assert manifest["review_history"][-1]["reviewer"] == "historian@example"
    assert candidate["selected_insight_ids"] == ["INS-TEST-001"]
    assert candidate["candidate_score"] is None
    assert candidate["responder_eligible"] is False
    assert profile["approval_gate"]["answer_permission"] is False


def test_review_decision_rejects_unreviewed_or_unrecalled_insight(monkeypatch, tmp_path) -> None:
    manifest_path, profile_path = _files(tmp_path)
    monkeypatch.setattr(
        "app.services.problem_draft_review_decision.build_problem_draft_review_packet",
        lambda _: _packet(),
    )
    monkeypatch.setattr(
        "app.services.problem_draft_review_decision.inspect_problem_draft_readiness",
        lambda _: SimpleNamespace(
            manifest_path=str(manifest_path), candidate_profile_path=str(profile_path)
        ),
    )

    try:
        apply_problem_draft_review_decision(
            "Q-RESEARCH-TEST",
            reviewer="historian@example",
            retrieval_dimensions=["career transition"],
            selected_insight_ids_by_person={"test_person": ["INS-NOT-ALLOWED"]},
            problem_definition_reviewed=True,
            insight_selection_reviewed=True,
            persist=True,
        )
    except ValueError as exc:
        assert "not supported by recalled reviewed HEUs" in str(exc)
    else:
        raise AssertionError("invalid Insight selection should be rejected")
