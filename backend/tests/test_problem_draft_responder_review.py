from types import SimpleNamespace

import yaml

from app.services.problem_draft_responder_review import (
    ResponderEligibilityDecision,
    apply_problem_draft_responder_review,
)


def _files(tmp_path):
    manifest_path = tmp_path / "manifest.yaml"
    profile_path = tmp_path / "candidate_profile.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "problem_id": "Q-RESEARCH-TEST",
                "review_gate": {
                    "problem_definition_reviewed": True,
                    "insight_selection_reviewed": True,
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
                        "person_id": "a",
                        "selected_insight_ids": ["INS-A"],
                        "candidate_score": 0.8,
                        "registration_candidate": {"dynasty": "han", "evidence_ids": ["E-A"]},
                        "responder_eligible": False,
                    },
                    {
                        "person_id": "b",
                        "selected_insight_ids": ["INS-B"],
                        "candidate_score": 0.7,
                        "registration_candidate": {"dynasty": "tang", "evidence_ids": ["E-B"]},
                        "responder_eligible": False,
                    },
                ],
                "approval_gate": {
                    "candidate_scoring_completed": True,
                    "responder_eligibility_reviewed": False,
                    "answer_permission": False,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return manifest_path, profile_path


def _patch_readiness(monkeypatch, manifest_path, profile_path):
    monkeypatch.setattr(
        "app.services.problem_draft_responder_review.inspect_problem_draft_readiness",
        lambda _: SimpleNamespace(
            manifest_path=str(manifest_path), candidate_profile_path=str(profile_path)
        ),
    )


def test_review_can_approve_one_responder_and_answer_permission(monkeypatch, tmp_path):
    manifest_path, profile_path = _files(tmp_path)
    _patch_readiness(monkeypatch, manifest_path, profile_path)

    result = apply_problem_draft_responder_review(
        "Q-RESEARCH-TEST",
        reviewer="historian@example",
        decisions=[
            ResponderEligibilityDecision("a", True, "Best reviewed fit."),
            ResponderEligibilityDecision("b", False, "Useful evidence but weaker transfer."),
        ],
        approve_answer_permission=True,
        persist=True,
    )

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    assert result.eligible_candidates == 1
    assert result.answer_permission is True
    assert profile["approval_gate"]["responder_eligibility_reviewed"] is True
    assert profile["approval_gate"]["answer_permission"] is True
    assert profile["candidates"][0]["responder_eligible"] is True
    assert profile["candidates"][1]["responder_eligible"] is False
    assert manifest["review_gate"]["can_render_answer"] is True
    assert manifest["review_history"][-1]["action"] == "problem_specific_responder_eligibility_review"


def test_review_requires_decision_for_every_candidate(monkeypatch, tmp_path):
    manifest_path, profile_path = _files(tmp_path)
    _patch_readiness(monkeypatch, manifest_path, profile_path)

    try:
        apply_problem_draft_responder_review(
            "Q-RESEARCH-TEST",
            reviewer="historian@example",
            decisions=[ResponderEligibilityDecision("a", True, "Reviewed.")],
            approve_answer_permission=True,
        )
    except ValueError as exc:
        assert "explicitly decide every candidate" in str(exc)
    else:
        raise AssertionError("expected missing candidate decision to fail")


def test_answer_permission_cannot_be_approved_without_eligible_responder(monkeypatch, tmp_path):
    manifest_path, profile_path = _files(tmp_path)
    _patch_readiness(monkeypatch, manifest_path, profile_path)

    try:
        apply_problem_draft_responder_review(
            "Q-RESEARCH-TEST",
            reviewer="historian@example",
            decisions=[
                ResponderEligibilityDecision("a", False, "Not strong enough."),
                ResponderEligibilityDecision("b", False, "Not strong enough."),
            ],
            approve_answer_permission=True,
        )
    except ValueError as exc:
        assert "without an eligible responder" in str(exc)
    else:
        raise AssertionError("expected answer permission guard to fail")


def test_review_requires_completed_scoring(monkeypatch, tmp_path):
    manifest_path, profile_path = _files(tmp_path)
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile["approval_gate"]["candidate_scoring_completed"] = False
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    _patch_readiness(monkeypatch, manifest_path, profile_path)

    try:
        apply_problem_draft_responder_review(
            "Q-RESEARCH-TEST",
            reviewer="historian@example",
            decisions=[
                ResponderEligibilityDecision("a", True, "Reviewed."),
                ResponderEligibilityDecision("b", False, "Reviewed."),
            ],
            approve_answer_permission=False,
        )
    except ValueError as exc:
        assert "completed candidate scoring" in str(exc)
    else:
        raise AssertionError("expected scoring gate to fail")
