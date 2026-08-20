from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.services.problem_draft_readiness_service import inspect_problem_draft_readiness


@dataclass(frozen=True)
class ResponderEligibilityDecision:
    person_id: str
    eligible: bool
    rationale: str


@dataclass(frozen=True)
class ProblemDraftResponderReviewResult:
    problem_id: str
    reviewer: str
    persisted: bool
    reviewed_candidates: int
    eligible_candidates: int
    responder_eligibility_reviewed: bool
    answer_permission: bool
    status: str


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return data


def _dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


def apply_problem_draft_responder_review(
    draft_problem_id: str,
    *,
    reviewer: str,
    decisions: list[ResponderEligibilityDecision],
    approve_answer_permission: bool,
    note: str | None = None,
    persist: bool = False,
) -> ProblemDraftResponderReviewResult:
    """Record explicit responder eligibility review after candidate scoring."""
    reviewer = reviewer.strip()
    if not reviewer:
        raise ValueError("reviewer must not be empty")
    if not decisions:
        raise ValueError("at least one responder eligibility decision is required")

    readiness = inspect_problem_draft_readiness(draft_problem_id)
    manifest_path = Path(readiness.manifest_path)
    profile_path = Path(readiness.candidate_profile_path)
    manifest = _load_yaml(manifest_path)
    profile = _load_yaml(profile_path)

    review_gate = manifest.get("review_gate") or {}
    approval_gate = profile.setdefault("approval_gate", {})
    if review_gate.get("problem_definition_reviewed") is not True:
        raise ValueError("responder review requires reviewed problem definition")
    if review_gate.get("insight_selection_reviewed") is not True:
        raise ValueError("responder review requires reviewed Insight selection")
    if approval_gate.get("candidate_scoring_completed") is not True:
        raise ValueError("responder review requires completed candidate scoring")

    rows = profile.get("candidates") or []
    if not rows:
        raise ValueError("draft has no candidates")
    by_person = {str(row.get("person_id", "")): row for row in rows}

    requested_people = [decision.person_id for decision in decisions]
    if len(set(requested_people)) != len(requested_people):
        raise ValueError("duplicate responder eligibility decision")
    unknown = set(requested_people) - set(by_person)
    if unknown:
        raise ValueError(f"Unknown draft candidates: {sorted(unknown)}")
    missing = set(by_person) - set(requested_people)
    if missing:
        raise ValueError(
            "responder eligibility review must explicitly decide every candidate; "
            f"missing={sorted(missing)}"
        )

    for decision in decisions:
        row = by_person[decision.person_id]
        rationale = decision.rationale.strip()
        if not rationale:
            raise ValueError(
                f"Candidate {decision.person_id} responder eligibility rationale must not be empty"
            )
        if row.get("candidate_score") is None:
            raise ValueError(f"Candidate {decision.person_id} has not been scored")
        registration_candidate = row.get("registration_candidate")
        if not isinstance(registration_candidate, dict) or not registration_candidate:
            raise ValueError(
                f"Candidate {decision.person_id} is missing the evidence-gated registration payload"
            )
        if not row.get("selected_insight_ids"):
            raise ValueError(f"Candidate {decision.person_id} has no reviewed selected Insight")

        row["responder_eligible"] = bool(decision.eligible)
        row["responder_eligibility_rationale"] = rationale
        row["status"] = (
            "responder_eligible_reviewed"
            if decision.eligible
            else "responder_ineligible_reviewed"
        )

    eligible_count = sum(1 for row in rows if row.get("responder_eligible") is True)
    if approve_answer_permission and eligible_count == 0:
        raise ValueError("answer permission cannot be approved without an eligible responder")

    approval_gate["responder_eligibility_reviewed"] = True
    approval_gate["answer_permission"] = bool(approve_answer_permission)
    review_gate["can_render_answer"] = bool(approve_answer_permission)
    review_gate["responder_eligibility_locked"] = False
    manifest["review_gate"] = review_gate

    manifest.setdefault("review_history", []).append(
        {
            "reviewer": reviewer,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "action": "problem_specific_responder_eligibility_review",
            "reviewed_candidates": len(decisions),
            "eligible_candidates": eligible_count,
            "answer_permission": bool(approve_answer_permission),
            "note": note,
        }
    )

    if persist:
        manifest_tmp = manifest_path.with_suffix(".yaml.tmp")
        profile_tmp = profile_path.with_suffix(".yaml.tmp")
        profile_tmp.write_text(_dump_yaml(profile), encoding="utf-8")
        manifest_tmp.write_text(_dump_yaml(manifest), encoding="utf-8")
        profile_tmp.replace(profile_path)
        manifest_tmp.replace(manifest_path)

    return ProblemDraftResponderReviewResult(
        problem_id=draft_problem_id,
        reviewer=reviewer,
        persisted=persist,
        reviewed_candidates=len(decisions),
        eligible_candidates=eligible_count,
        responder_eligibility_reviewed=True,
        answer_permission=bool(approve_answer_permission),
        status=(
            "responder_review_complete_answer_permission_approved"
            if approve_answer_permission
            else "responder_review_complete_answer_permission_withheld"
        ),
    )
