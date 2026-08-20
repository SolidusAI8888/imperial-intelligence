from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.services.cross_dynasty_selector import CandidateExperience, score_candidate
from app.services.knowledge_repository import (
    load_person_experiences,
    load_person_insights,
    load_person_records,
)
from app.services.problem_draft_readiness_service import inspect_problem_draft_readiness


_SCORE_KEYS = (
    "experience_similarity",
    "evidence_strength",
    "stage_relevance",
    "lesson_clarity",
    "transferability",
    "counterevidence_quality",
)


@dataclass(frozen=True)
class CandidateScoringDecision:
    person_id: str
    scores: dict[str, float]
    rationale: str


@dataclass(frozen=True)
class ProblemDraftCandidateScoringResult:
    problem_id: str
    reviewer: str
    persisted: bool
    scored_candidates: int
    candidate_scoring_completed: bool
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


def _normalize_scores(raw: dict[str, float]) -> dict[str, float]:
    if set(raw) != set(_SCORE_KEYS):
        missing = sorted(set(_SCORE_KEYS) - set(raw))
        extra = sorted(set(raw) - set(_SCORE_KEYS))
        raise ValueError(f"Candidate score dimensions mismatch; missing={missing}, extra={extra}")
    scores = {key: float(raw[key]) for key in _SCORE_KEYS}
    if any(value < 0 or value > 1 for value in scores.values()):
        raise ValueError("Candidate score dimensions must be between 0 and 1")
    return scores


def apply_problem_draft_candidate_scores(
    draft_problem_id: str,
    *,
    reviewer: str,
    decisions: list[CandidateScoringDecision],
    note: str | None = None,
    persist: bool = False,
) -> ProblemDraftCandidateScoringResult:
    """Persist explicit problem-specific scoring without granting answer permission.

    Scoring is allowed only after problem definition and Insight selection have been
    explicitly reviewed. Runtime registration fields are derived from reviewed
    HER/HEU/Insight evidence instead of being accepted from the caller.
    """
    reviewer = reviewer.strip()
    if not reviewer:
        raise ValueError("reviewer must not be empty")
    if not decisions:
        raise ValueError("at least one candidate scoring decision is required")

    readiness = inspect_problem_draft_readiness(draft_problem_id)
    manifest_path = Path(readiness.manifest_path)
    profile_path = Path(readiness.candidate_profile_path)
    manifest = _load_yaml(manifest_path)
    profile = _load_yaml(profile_path)

    review_gate = manifest.get("review_gate") or {}
    if not review_gate.get("problem_definition_reviewed"):
        raise ValueError("candidate scoring requires reviewed problem definition")
    if not review_gate.get("insight_selection_reviewed"):
        raise ValueError("candidate scoring requires reviewed Insight selection")

    rows = profile.get("candidates") or []
    by_person = {str(row.get("person_id", "")): row for row in rows}
    requested_people = [decision.person_id for decision in decisions]
    if len(set(requested_people)) != len(requested_people):
        raise ValueError("duplicate candidate scoring decision")
    unknown = set(requested_people) - set(by_person)
    if unknown:
        raise ValueError(f"Unknown draft candidates: {sorted(unknown)}")

    for decision in decisions:
        person_id = decision.person_id
        row = by_person[person_id]
        selected_insights = list(dict.fromkeys(row.get("selected_insight_ids") or []))
        if not selected_insights:
            raise ValueError(f"Candidate {person_id} has no reviewed selected Insight")

        recalled_heus = set(row.get("recalled_heu_ids") or [])
        experiences = [
            heu for heu in load_person_experiences(person_id) if heu.heu_id in recalled_heus
        ]
        if {heu.heu_id for heu in experiences} != recalled_heus:
            raise ValueError(f"Candidate {person_id} references missing recalled HEU data")
        if any(heu.status not in {"reviewed", "accepted"} for heu in experiences):
            raise ValueError(f"Candidate {person_id} contains unreviewed HEU data")

        insight_set = set(selected_insights)
        insights = [
            insight for insight in load_person_insights(person_id) if insight.insight_id in insight_set
        ]
        if {insight.insight_id for insight in insights} != insight_set:
            raise ValueError(f"Candidate {person_id} references missing selected Insight data")
        if any(insight.status not in {"reviewed", "accepted"} for insight in insights):
            raise ValueError(f"Candidate {person_id} contains unreviewed selected Insight")
        for insight in insights:
            if not set(insight.derived_from_heus).issubset(recalled_heus):
                raise ValueError(
                    f"Candidate {person_id} selected Insight {insight.insight_id} is outside recalled HEUs"
                )

        record_ids = {record_id for heu in experiences for record_id in heu.record_links}
        records = [
            record for record in load_person_records(person_id) if record.record_id in record_ids
        ]
        if {record.record_id for record in records} != record_ids:
            raise ValueError(f"Candidate {person_id} references missing HER data")
        if any(record.status not in {"reviewed", "accepted"} for record in records):
            raise ValueError(f"Candidate {person_id} contains unreviewed HER data")

        dynasties = {record.dynasty for record in records if record.dynasty and record.dynasty != "Unknown"}
        if len(dynasties) != 1:
            raise ValueError(f"Candidate {person_id} must resolve to exactly one dynasty")
        dynasty = next(iter(dynasties))
        evidence_ids = sorted(
            {
                canonical_id
                for record in records
                for source in record.sources
                for canonical_id in source.canonical_ids
            }
        )
        if not evidence_ids:
            raise ValueError(f"Candidate {person_id} has no canonical evidence IDs")

        rationale = decision.rationale.strip()
        if not rationale:
            raise ValueError(f"Candidate {person_id} scoring rationale must not be empty")
        scores = _normalize_scores(decision.scores)
        candidate = CandidateExperience(
            persona_id=person_id,
            dynasty=dynasty,
            evidence_ids=tuple(evidence_ids),
            experience_similarity=scores["experience_similarity"],
            evidence_strength=scores["evidence_strength"],
            stage_relevance=scores["stage_relevance"],
            lesson_clarity=scores["lesson_clarity"],
            transferability=scores["transferability"],
            counterevidence_quality=scores["counterevidence_quality"],
            rationale=rationale,
        )
        aggregate = score_candidate(candidate).total_score

        row["candidate_score"] = aggregate
        row["registration_candidate"] = {
            "dynasty": dynasty,
            "evidence_ids": evidence_ids,
            "heu_ids": sorted(recalled_heus),
            "insight_ids": selected_insights,
            "scores": scores,
            "rationale": rationale,
        }
        row["status"] = "candidate_scored_requires_responder_eligibility_review"

    approval_gate = profile.setdefault("approval_gate", {})
    completed = bool(rows) and all(row.get("candidate_score") is not None for row in rows)
    approval_gate["candidate_scoring_completed"] = completed

    manifest.setdefault("review_history", []).append(
        {
            "reviewer": reviewer,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "action": "problem_specific_candidate_scoring",
            "scored_candidates": len(decisions),
            "candidate_scoring_completed": completed,
            "note": note,
            "safety_boundary": (
                "This action did not change responder eligibility, answer permission, "
                "or registration state."
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

    return ProblemDraftCandidateScoringResult(
        problem_id=draft_problem_id,
        reviewer=reviewer,
        persisted=persist,
        scored_candidates=len(decisions),
        candidate_scoring_completed=completed,
        responder_eligibility_changed=False,
        answer_permission_changed=False,
        status="candidate_scores_validated_no_eligibility_or_answer_permission_change",
    )
