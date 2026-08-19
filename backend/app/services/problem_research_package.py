from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re

from app.services.problem_insight_review_queue import build_problem_insight_review_queue


_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ProblemResearchCandidate:
    person_id: str
    heu_ids: tuple[str, ...]
    retrieval_score: float
    review_priority: int
    status: str
    responder_eligible: bool


@dataclass(frozen=True)
class ProblemResearchPackage:
    proposed_problem_id: str
    raw_question: str
    normalized_question: str
    candidates: tuple[ProblemResearchCandidate, ...]
    status: str
    can_render_answer: bool
    required_next_gate: str


def normalize_research_question(question: str) -> str:
    normalized = _WS_RE.sub(" ", question).strip()
    if len(normalized) < 2:
        raise ValueError("question must contain at least 2 non-whitespace characters")
    return normalized


def provisional_problem_id(question: str) -> str:
    normalized = normalize_research_question(question)
    digest = sha256(normalized.encode("utf-8")).hexdigest()[:12].upper()
    return f"Q-RESEARCH-{digest}"


def build_problem_research_package(
    question: str,
    *,
    candidate_limit: int = 20,
) -> ProblemResearchPackage:
    """Build a non-persistent research package for a brand-new user question.

    This is an intake/research artifact only. It may recall reviewed HER/HEU material
    and prioritize people for problem-specific Insight review, but it cannot register
    a Problem manifest, create an approved candidate profile, grant responder
    eligibility, or render an answer.
    """
    if candidate_limit < 1 or candidate_limit > 50:
        raise ValueError("candidate_limit must be between 1 and 50")

    normalized = normalize_research_question(question)
    review_queue = build_problem_insight_review_queue(
        normalized,
        problem_id=None,
        candidate_limit=candidate_limit,
    )
    candidates = tuple(
        ProblemResearchCandidate(
            person_id=item.person_id,
            heu_ids=item.heu_ids,
            retrieval_score=item.retrieval_score,
            review_priority=item.review_priority,
            status="research_candidate_requires_problem_specific_review",
            responder_eligible=False,
        )
        for item in review_queue
    )

    return ProblemResearchPackage(
        proposed_problem_id=provisional_problem_id(normalized),
        raw_question=question,
        normalized_question=normalized,
        candidates=candidates,
        status="research_package_requires_human_review",
        can_render_answer=False,
        required_next_gate=(
            "Review recalled HEUs, create/select problem-specific Insights, then create a reviewed "
            "Problem manifest and candidate profile before candidate scoring or responder eligibility."
        ),
    )
