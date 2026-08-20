from types import SimpleNamespace

import yaml

from app.services.problem_draft_candidate_scoring import (
    CandidateScoringDecision,
    apply_problem_draft_candidate_scores,
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
                        "person_id": "test_person",
                        "recalled_heu_ids": ["HEU-TEST-001"],
                        "selected_insight_ids": ["INS-TEST-001"],
                        "candidate_score": None,
                        "registration_candidate": {},
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


def _patch_reviewed_chain(monkeypatch, manifest_path, profile_path):
    monkeypatch.setattr(
        "app.services.problem_draft_candidate_scoring.inspect_problem_draft_readiness",
        lambda _: SimpleNamespace(
            manifest_path=str(manifest_path), candidate_profile_path=str(profile_path)
        ),
    )
    heu = SimpleNamespace(
        heu_id="HEU-TEST-001", status="reviewed", record_links=["HER-TEST-001"]
    )
    insight = SimpleNamespace(
        insight_id="INS-TEST-001",
        status="reviewed",
        derived_from_heus=["HEU-TEST-001"],
    )
    record = SimpleNamespace(
        record_id="HER-TEST-001",
        status="reviewed",
        dynasty="tang",
        sources=[SimpleNamespace(canonical_ids=["CANON-TEST-001"])],
    )
    monkeypatch.setattr(
        "app.services.problem_draft_candidate_scoring.load_person_experiences", lambda _: [heu]
    )
    monkeypatch.setattr(
        "app.services.problem_draft_candidate_scoring.load_person_insights", lambda _: [insight]
    )
    monkeypatch.setattr(
        "app.services.problem_draft_candidate_scoring.load_person_records", lambda _: [record]
    )


def test_scoring_persists_runtime_payload_without_granting_eligibility(monkeypatch, tmp_path):
    manifest_path, profile_path = _files(tmp_path)
    _patch_reviewed_chain(monkeypatch, manifest_path, profile_path)

    result = apply_problem_draft_candidate_scores(
        "Q-RESEARCH-TEST",
        reviewer="historian@example",
        decisions=[
            CandidateScoringDecision(
                person_id="test_person",
                scores={
                    "experience_similarity": 0.8,
                    "evidence_strength": 0.9,
                    "stage_relevance": 0.7,
                    "lesson_clarity": 0.8,
                    "transferability": 0.6,
                    "counterevidence_quality": 0.5,
                },
                rationale="Reviewed against the problem-specific dimensions.",
            )
        ],
        persist=True,
    )

    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    row = profile["candidates"][0]
    assert result.candidate_scoring_completed is True
    assert result.responder_eligibility_changed is False
    assert result.answer_permission_changed is False
    assert row["candidate_score"] == 0.755
    assert row["registration_candidate"]["dynasty"] == "tang"
    assert row["registration_candidate"]["evidence_ids"] == ["CANON-TEST-001"]
    assert row["registration_candidate"]["insight_ids"] == ["INS-TEST-001"]
    assert row["responder_eligible"] is False
    assert profile["approval_gate"]["responder_eligibility_reviewed"] is False
    assert profile["approval_gate"]["answer_permission"] is False
    assert manifest["review_history"][-1]["action"] == "problem_specific_candidate_scoring"


def test_scoring_rejects_before_insight_review(monkeypatch, tmp_path):
    manifest_path, profile_path = _files(tmp_path)
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["review_gate"]["insight_selection_reviewed"] = False
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    _patch_reviewed_chain(monkeypatch, manifest_path, profile_path)

    try:
        apply_problem_draft_candidate_scores(
            "Q-RESEARCH-TEST",
            reviewer="historian@example",
            decisions=[
                CandidateScoringDecision(
                    person_id="test_person",
                    scores={key: 0.5 for key in (
                        "experience_similarity",
                        "evidence_strength",
                        "stage_relevance",
                        "lesson_clarity",
                        "transferability",
                        "counterevidence_quality",
                    )},
                    rationale="Should not be accepted yet.",
                )
            ],
        )
    except ValueError as exc:
        assert "requires reviewed Insight selection" in str(exc)
    else:
        raise AssertionError("scoring before Insight review should be rejected")
