from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict

from app.services.experience_retrieval import recall_reusable_experiences


@dataclass(frozen=True)
class CandidateResearchShortlistRow:
    person_id: str
    heu_ids: tuple[str, ...]
    best_recall_score: float
    aggregate_recall_score: float
    matched_terms: tuple[str, ...]
    status: str


def build_candidate_research_shortlist(
    question: str,
    *,
    problem_id: str | None = None,
    recall_limit: int = 50,
    candidate_limit: int = 20,
) -> list[CandidateResearchShortlistRow]:
    """Group reusable HEU recall into a person-level research shortlist.

    This is deliberately a research-stage operation. It does not select Insights,
    calculate final candidate scores, grant responder eligibility, or choose an
    emperor. A person appears here only because one or more reviewed HEUs may be
    relevant enough to deserve problem-specific review.
    """
    if candidate_limit < 1:
        raise ValueError("candidate_limit must be >= 1")

    recalled = recall_reusable_experiences(
        question,
        problem_id=problem_id,
        limit=recall_limit,
    )

    by_person: dict[str, list] = defaultdict(list)
    for row in recalled:
        by_person[row.person_id].append(row)

    shortlist: list[CandidateResearchShortlistRow] = []
    for person_id, rows in by_person.items():
        ordered = sorted(rows, key=lambda item: (-item.score, item.heu_id))
        all_terms = sorted({term for row in ordered for term in row.matched_terms})
        shortlist.append(
            CandidateResearchShortlistRow(
                person_id=person_id,
                heu_ids=tuple(row.heu_id for row in ordered),
                best_recall_score=max(row.score for row in ordered),
                aggregate_recall_score=round(sum(row.score for row in ordered), 4),
                matched_terms=tuple(all_terms),
                status="research_shortlist_not_responder_eligible",
            )
        )

    shortlist.sort(
        key=lambda item: (
            -item.best_recall_score,
            -item.aggregate_recall_score,
            item.person_id,
        )
    )
    return shortlist[:candidate_limit]
