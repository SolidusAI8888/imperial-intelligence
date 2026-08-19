from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


_REQUIRED_SCORE_KEYS = {
    "experience_similarity",
    "evidence_strength",
    "stage_relevance",
    "lesson_clarity",
    "transferability",
    "counterevidence_quality",
}


@dataclass(frozen=True)
class PromotionReadiness:
    problem_id: str
    ready: bool
    blockers: tuple[str, ...]
    status: str


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return data


def _validate_registration_candidate(row: dict, blockers: list[str]) -> None:
    person_id = str(row.get("person_id", "unknown"))
    payload = row.get("registration_candidate")
    if not isinstance(payload, dict):
        blockers.append(f"eligible_candidate_missing_registration_payload:{person_id}")
        return

    if not payload.get("dynasty"):
        blockers.append(f"eligible_candidate_missing_dynasty:{person_id}")
    if not payload.get("heu_ids"):
        blockers.append(f"eligible_candidate_missing_registration_heus:{person_id}")
    if not payload.get("insight_ids"):
        blockers.append(f"eligible_candidate_missing_registration_insights:{person_id}")
    if not payload.get("rationale"):
        blockers.append(f"eligible_candidate_missing_rationale:{person_id}")

    scores = payload.get("scores")
    if not isinstance(scores, dict) or not _REQUIRED_SCORE_KEYS.issubset(scores):
        blockers.append(f"eligible_candidate_missing_score_dimensions:{person_id}")
    elif any(scores.get(key) is None for key in _REQUIRED_SCORE_KEYS):
        blockers.append(f"eligible_candidate_incomplete_score_dimensions:{person_id}")

    selected = set(row.get("selected_insight_ids") or ())
    registered = set(payload.get("insight_ids") or ())
    if selected and registered != selected:
        blockers.append(f"eligible_candidate_insight_selection_mismatch:{person_id}")


def assess_problem_draft_promotion(manifest_path: Path, candidate_profile_path: Path) -> PromotionReadiness:
    """Assess whether a reviewed draft is structurally ready for explicit registration.

    This function never promotes files and never grants answer permission. It only
    verifies that humans have explicitly recorded the problem-specific review gates
    and the full runtime candidate payload required before a later registration
    artifact may be generated.
    """
    manifest = _load_yaml(manifest_path)
    profile = _load_yaml(candidate_profile_path)
    problem_id = str(manifest.get("problem_id", ""))
    blockers: list[str] = []

    if not problem_id:
        blockers.append("manifest_missing_problem_id")
    if profile.get("problem_id") != problem_id:
        blockers.append("candidate_profile_problem_id_mismatch")
    if not manifest.get("retrieval_dimensions"):
        blockers.append("retrieval_dimensions_not_reviewed")

    review = manifest.get("review_gate") or {}
    approval = profile.get("approval_gate") or {}

    if review.get("problem_definition_reviewed") is not True:
        blockers.append("problem_definition_not_reviewed")
    if review.get("insight_selection_reviewed") is not True:
        blockers.append("insight_selection_not_reviewed")
    if approval.get("candidate_scoring_completed") is not True:
        blockers.append("candidate_scoring_not_completed")
    if approval.get("responder_eligibility_reviewed") is not True:
        blockers.append("responder_eligibility_not_reviewed")
    if approval.get("answer_permission") is not True:
        blockers.append("answer_permission_not_approved")

    candidates = profile.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        blockers.append("no_reviewed_candidates")
    else:
        eligible = [row for row in candidates if row.get("responder_eligible") is True]
        if not eligible:
            blockers.append("no_responder_eligible_candidate")
        for row in eligible:
            if not row.get("selected_insight_ids"):
                blockers.append(
                    f"eligible_candidate_missing_selected_insights:{row.get('person_id', 'unknown')}"
                )
            if row.get("candidate_score") is None:
                blockers.append(
                    f"eligible_candidate_missing_score:{row.get('person_id', 'unknown')}"
                )
            _validate_registration_candidate(row, blockers)

    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    return PromotionReadiness(
        problem_id=problem_id,
        ready=ready,
        blockers=tuple(blockers),
        status=(
            "ready_for_explicit_registration_review"
            if ready
            else "blocked_pending_problem_specific_review"
        ),
    )
