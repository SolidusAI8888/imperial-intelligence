from __future__ import annotations

from dataclasses import dataclass

from app.services.problem_candidate_shortlist import build_candidate_research_shortlist


@dataclass(frozen=True)
class ProblemInsightReviewItem:
    person_id: str
    heu_ids: tuple[str, ...]
    retrieval_score: float
    review_priority: int
    status: str
    required_action: str


def build_problem_insight_review_queue(
    question: str,
    *,
    problem_id: str | None = None,
    candidate_limit: int = 20,
) -> list[ProblemInsightReviewItem]:
    """Turn a research shortlist into a human-review queue for problem-specific insight work.

    This stage intentionally grants no responder eligibility. Reviewers must decide whether the
    recalled HEUs genuinely support a problem-specific insight, whether additional HER/HEU evidence
    is required, and whether a later candidate profile may include the person.
    """
    shortlist = build_candidate_research_shortlist(
        question,
        problem_id=problem_id,
        candidate_limit=candidate_limit,
    )

    queue: list[ProblemInsightReviewItem] = []
    for index, row in enumerate(shortlist, start=1):
        queue.append(
            ProblemInsightReviewItem(
                person_id=row.person_id,
                heu_ids=row.heu_ids,
                retrieval_score=row.best_recall_score,
                review_priority=index,
                status="awaiting_problem_specific_insight_review",
                required_action=(
                    "Review recalled HEUs against this problem; create or select a problem-specific "
                    "Insight only if evidence supports it. Do not grant responder eligibility here."
                ),
            )
        )
    return queue
