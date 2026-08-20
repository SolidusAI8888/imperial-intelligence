from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.services.problem_draft_readiness_service import inspect_problem_draft_readiness
from app.services.problem_draft_review_packet import build_problem_draft_review_packet


@dataclass(frozen=True)
class ProblemDraftReviewDecisionResult:
    problem_id: str
    persisted: bool
    reviewer: str
    selected_insight_count: int
    problem_definition_reviewed: bool
    insight_selection_reviewed: bool
    responder_eligibility_changed: bool
    answer_permission_changed: bool
    status: str


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return data


def _dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


def apply_problem_draft_review_decision(
    draft_problem_id: str,
    *,
    reviewer: str,
    retrieval_dimensions: list[str],
    selected_insight_ids_by_person: dict[str, list[str]],
    problem_definition_reviewed: bool,
    insight_selection_reviewed: bool,
    note: str | None = None,
    persist: bool = False,
) -> ProblemDraftReviewDecisionResult:
    """Apply explicit human review work without granting responder eligibility.

    Only problem-definition fields and problem-specific Insight selections are writable
    here. Candidate scores, responder eligibility, answer permission, and registration
    fields are intentionally outside this service.
    """
    reviewer = reviewer.strip()
    if not reviewer:
        raise ValueError("reviewer must not be empty")

    dimensions = [item.strip() for item in retrieval_dimensions if item.strip()]
    if problem_definition_reviewed and not dimensions:
        raise ValueError("reviewed problem definition requires retrieval_dimensions")

    packet = build_problem_draft_review_packet(draft_problem_id)
    packet_by_person = {candidate.person_id: candidate for candidate in packet.candidates}

    unknown_people = set(selected_insight_ids_by_person) - set(packet_by_person)
    if unknown_people:
        raise ValueError(f"Unknown draft candidates: {sorted(unknown_people)}")

    normalized_selections: dict[str, list[str]] = {}
    for person_id, requested in selected_insight_ids_by_person.items():
        allowed = {
            suggestion.insight_id
            for suggestion in packet_by_person[person_id].existing_insight_suggestions
        }
        chosen = list(dict.fromkeys(requested))
        invalid = set(chosen) - allowed
        if invalid:
            raise ValueError(
                f"Candidate {person_id} selected Insights not supported by recalled reviewed HEUs: "
                f"{sorted(invalid)}"
            )
        normalized_selections[person_id] = chosen

    if insight_selection_reviewed:
        missing_decisions = set(packet_by_person) - set(normalized_selections)
        if missing_decisions:
            raise ValueError(
                "insight_selection_reviewed requires an explicit selection decision for every "
                f"draft candidate; missing: {sorted(missing_decisions)}"
            )

    readiness = inspect_problem_draft_readiness(draft_problem_id)
    manifest_path = Path(readiness.manifest_path)
    profile_path = Path(readiness.candidate_profile_path)
    manifest = _load_yaml(manifest_path)
    profile = _load_yaml(profile_path)

    manifest["retrieval_dimensions"] = dimensions
    review_gate = manifest.setdefault("review_gate", {})
    review_gate["problem_definition_reviewed"] = bool(problem_definition_reviewed)
    review_gate["insight_selection_reviewed"] = bool(insight_selection_reviewed)

    total_selected = 0
    for row in profile.get("candidates") or []:
        person_id = str(row.get("person_id", ""))
        if person_id in normalized_selections:
            row["selected_insight_ids"] = normalized_selections[person_id]
        total_selected += len(row.get("selected_insight_ids") or [])

    history = manifest.setdefault("review_history", [])
    history.append(
        {
            "reviewer": reviewer,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "action": "problem_definition_and_insight_selection_review",
            "problem_definition_reviewed": bool(problem_definition_reviewed),
            "insight_selection_reviewed": bool(insight_selection_reviewed),
            "selected_insight_count": total_selected,
            "note": note,
            "safety_boundary": (
                "This action did not change candidate scores, responder eligibility, "
                "answer permission, or registration state."
            ),
        }
    )

    if persist:
        manifest_tmp = manifest_path.with_suffix(".yaml.tmp")
        profile_tmp = profile_path.with_suffix(".yaml.tmp")
        profile_tmp.write_text(_dump_yaml(profile), encoding="utf-8")
        manifest_tmp.write_text(_dump_yaml(manifest), encoding="utf-8")
        profile_tmp.replace(profile_path)
        manifest_tmp.replace(manifest_path)

    return ProblemDraftReviewDecisionResult(
        problem_id=draft_problem_id,
        persisted=persist,
        reviewer=reviewer,
        selected_insight_count=total_selected,
        problem_definition_reviewed=bool(problem_definition_reviewed),
        insight_selection_reviewed=bool(insight_selection_reviewed),
        responder_eligibility_changed=False,
        answer_permission_changed=False,
        status="review_decision_validated_no_eligibility_or_answer_permission_change",
    )
