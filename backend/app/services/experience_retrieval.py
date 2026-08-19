from __future__ import annotations

from dataclasses import dataclass
import re

from app.models.knowledge import HistoricalExperienceUnit
from app.services.knowledge_repository import load_all_experiences
from app.services.problem_knowledge_repository import load_problem_spec


_CJK_RE = re.compile(r"[\u3400-\u9fff]+")
_LATIN_RE = re.compile(r"[A-Za-z0-9_]+")


@dataclass(frozen=True)
class ExperienceRecall:
    heu_id: str
    person_id: str
    title: str
    score: float
    matched_terms: tuple[str, ...]
    status: str


def _terms(text: str) -> set[str]:
    """Create lightweight deterministic recall terms for Chinese/Latin text.

    This is a recall layer, not a semantic judge. Chinese spans contribute
    overlapping 2- and 3-character n-grams; Latin text contributes lowercase
    word tokens. Final responder eligibility remains problem-specific and is
    never granted here.
    """
    terms: set[str] = set()
    for span in _CJK_RE.findall(text):
        for size in (2, 3):
            if len(span) >= size:
                terms.update(span[i : i + size] for i in range(len(span) - size + 1))
    terms.update(token.lower() for token in _LATIN_RE.findall(text))
    return terms


def _heu_text(heu: HistoricalExperienceUnit) -> str:
    return " ".join(
        [
            heu.title,
            heu.challenge,
            *heu.response_or_choice,
            *heu.experienced_outcome,
            *heu.explicit_reflection,
            *heu.interpretation,
        ]
    )


def _query_text(question: str, problem_id: str | None) -> str:
    if not problem_id:
        return question
    spec = load_problem_spec(problem_id)
    return " ".join(
        [question, spec.normalized_question, *spec.retrieval_dimensions]
    )


def recall_reusable_experiences(
    question: str,
    *,
    problem_id: str | None = None,
    limit: int = 20,
    minimum_score: float = 0.01,
) -> list[ExperienceRecall]:
    """Recall reviewed/accepted HEUs potentially relevant to a question.

    The function deliberately stops before Insight selection, candidate scoring,
    or responder eligibility. A new question can therefore reuse accumulated
    biography/experience knowledge without inheriting another problem's answer
    permissions.
    """
    if not question.strip():
        raise ValueError("question must not be empty")
    if limit < 1:
        raise ValueError("limit must be >= 1")

    query_terms = _terms(_query_text(question, problem_id))
    if not query_terms:
        return []

    rows: list[ExperienceRecall] = []
    for heu in load_all_experiences():
        if heu.status not in {"reviewed", "accepted"}:
            continue
        experience_terms = _terms(_heu_text(heu))
        matched = tuple(sorted(query_terms & experience_terms))
        if not matched:
            continue
        score = len(matched) / max(1, len(query_terms))
        if score < minimum_score:
            continue
        rows.append(
            ExperienceRecall(
                heu_id=heu.heu_id,
                person_id=heu.experience_owner,
                title=heu.title,
                score=round(score, 4),
                matched_terms=matched,
                status="recall_only_not_responder_eligible",
            )
        )

    rows.sort(key=lambda item: (-item.score, item.person_id, item.heu_id))
    return rows[:limit]
