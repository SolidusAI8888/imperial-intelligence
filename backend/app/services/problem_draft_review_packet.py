from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from app.services.knowledge_repository import load_person_experiences, load_person_insights
from app.services.problem_draft_readiness_service import inspect_problem_draft_readiness


@dataclass(frozen=True)
class ReviewHEUSummary:
    heu_id: str
    title: str
    challenge: str
    response_or_choice: tuple[str, ...]
    experienced_outcome: tuple[str, ...]
    explicit_reflection: tuple[str, ...]
    interpretation: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class ExistingInsightSuggestion:
    insight_id: str
    statement: str
    derived_from_heus: tuple[str, ...]
    applies_when: tuple[str, ...]
    limits: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class DraftCandidateReviewPacket:
    person_id: str
    review_priority: int
    retrieval_score: float
    recalled_heus: tuple[ReviewHEUSummary, ...]
    existing_insight_suggestions: tuple[ExistingInsightSuggestion, ...]
    selected_insight_ids: tuple[str, ...]
    candidate_score: float | None
    responder_eligible: bool
    status: str


@dataclass(frozen=True)
class ProblemDraftReviewPacket:
    problem_id: str
    raw_question: str
    normalized_question: str
    retrieval_dimensions: tuple[str, ...]
    candidates: tuple[DraftCandidateReviewPacket, ...]
    readiness_status: str
    readiness_blockers: tuple[str, ...]
    status: str


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return data


def build_problem_draft_review_packet(draft_problem_id: str) -> ProblemDraftReviewPacket:
    """Build an evidence-facing, read-only packet for human problem review.

    Existing reviewed/accepted Insights are surfaced only as suggestions when they are
    fully derived from recalled HEUs for the same person. Nothing in this service selects
    an Insight, assigns a score, changes responder eligibility, or approves an answer.
    """
    readiness = inspect_problem_draft_readiness(draft_problem_id)
    manifest = _load_yaml(Path(readiness.manifest_path))
    profile = _load_yaml(Path(readiness.candidate_profile_path))

    packets: list[DraftCandidateReviewPacket] = []
    for row in profile.get("candidates") or []:
        person_id = str(row.get("person_id", ""))
        recalled_ids = set(row.get("recalled_heu_ids") or ())

        heus = [
            heu
            for heu in load_person_experiences(person_id)
            if heu.heu_id in recalled_ids and heu.status in {"reviewed", "accepted"}
        ]
        heus.sort(key=lambda item: item.heu_id)
        found_ids = {heu.heu_id for heu in heus}
        missing = recalled_ids - found_ids
        if missing:
            raise ValueError(
                f"Draft candidate {person_id} references unavailable/unreviewed recalled HEUs: "
                f"{sorted(missing)}"
            )

        suggestions = []
        for insight in load_person_insights(person_id):
            derived = set(insight.derived_from_heus)
            if insight.status not in {"reviewed", "accepted"}:
                continue
            if derived and derived.issubset(recalled_ids):
                suggestions.append(
                    ExistingInsightSuggestion(
                        insight_id=insight.insight_id,
                        statement=insight.statement,
                        derived_from_heus=tuple(insight.derived_from_heus),
                        applies_when=tuple(insight.applies_when),
                        limits=tuple(insight.limits),
                        status="suggestion_only_requires_problem_specific_review",
                    )
                )
        suggestions.sort(key=lambda item: item.insight_id)

        packets.append(
            DraftCandidateReviewPacket(
                person_id=person_id,
                review_priority=int(row.get("review_priority") or 0),
                retrieval_score=float(row.get("retrieval_score") or 0.0),
                recalled_heus=tuple(
                    ReviewHEUSummary(
                        heu_id=heu.heu_id,
                        title=heu.title,
                        challenge=heu.challenge,
                        response_or_choice=tuple(heu.response_or_choice),
                        experienced_outcome=tuple(heu.experienced_outcome),
                        explicit_reflection=tuple(heu.explicit_reflection),
                        interpretation=tuple(heu.interpretation),
                        status=heu.status,
                    )
                    for heu in heus
                ),
                existing_insight_suggestions=tuple(suggestions),
                selected_insight_ids=tuple(row.get("selected_insight_ids") or ()),
                candidate_score=row.get("candidate_score"),
                responder_eligible=row.get("responder_eligible") is True,
                status="review_packet_only_no_approval_side_effects",
            )
        )

    packets.sort(key=lambda item: (item.review_priority, item.person_id))
    return ProblemDraftReviewPacket(
        problem_id=draft_problem_id,
        raw_question=str(manifest.get("raw_question", "")),
        normalized_question=str(manifest.get("normalized_question", "")),
        retrieval_dimensions=tuple(manifest.get("retrieval_dimensions") or ()),
        candidates=tuple(packets),
        readiness_status=readiness.status,
        readiness_blockers=readiness.blockers,
        status="human_review_packet_no_automatic_approval",
    )
