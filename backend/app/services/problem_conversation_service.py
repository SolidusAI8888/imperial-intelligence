from __future__ import annotations

from dataclasses import dataclass
import re

from app.services.grounded_answer_renderer import render_grounded_answer
from app.services.problem_knowledge_repository import load_problem_spec
from app.services.problem_research_package import (
    ProblemResearchPackage,
    build_problem_research_package,
)


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


@dataclass(frozen=True)
class ProblemConversationTurn:
    problem_id: str
    person_id: str | None
    user_question: str
    route: str
    route_reason: str
    historical_voice: str | None
    modern_translation: str | None
    cautions: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    insight_ids: tuple[str, ...]
    requires_new_problem: bool
    research_package: ProblemResearchPackage | None
    status: str


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(text or "") if token.strip()}


def _continuity_score(problem_text: str, followup: str, history: tuple[str, ...]) -> float:
    anchor = _tokens(problem_text)
    follow = _tokens(followup)
    if not follow:
        return 0.0

    overlap = len(anchor & follow) / max(1, len(follow))
    if history:
        recent = _tokens(" ".join(history[-4:]))
        overlap = max(overlap, len(recent & follow) / max(1, len(follow)))

    continuation_markers = {
        "你刚才", "你前面", "你说", "刚才说", "前面说", "这个观点", "这个判断",
        "这些经历", "这个例子", "这件事", "但是你", "可是你", "我不同意",
        "我反对", "你的依据", "你的证据", "具体一点", "再举例", "那你的意思",
        "那么你的意思", "那我该怎么办", "那具体怎么办",
    }
    if any(marker in followup for marker in continuation_markers):
        overlap = max(overlap, 0.45)
    return min(1.0, overlap)


def continue_problem_conversation(
    problem_id: str,
    followup_question: str,
    *,
    conversation_history: tuple[str, ...] = (),
    continuity_threshold: float = 0.20,
    candidate_limit: int = 20,
) -> ProblemConversationTurn:
    """Continue a reviewed Problem or automatically start research on semantic drift.

    A related follow-up reuses the existing reviewed responder/evidence bundle. A
    materially different follow-up is never answered under stale permissions; instead
    this service immediately builds the non-answerable new-Problem research package so
    the product can continue into fresh role selection without a second client call.
    """
    question = followup_question.strip()
    if len(question) < 2:
        raise ValueError("followup_question must contain at least two characters")
    if candidate_limit < 1 or candidate_limit > 50:
        raise ValueError("candidate_limit must be between 1 and 50")

    spec = load_problem_spec(problem_id)
    problem_text = " ".join(
        [spec.raw_question, spec.normalized_question, *spec.retrieval_dimensions]
    )
    score = _continuity_score(problem_text, question, conversation_history)

    if score < continuity_threshold:
        research = build_problem_research_package(question, candidate_limit=candidate_limit)
        return ProblemConversationTurn(
            problem_id=problem_id,
            person_id=None,
            user_question=question,
            route="new_problem_required",
            route_reason=(
                f"Follow-up continuity score {score:.2f} is below {continuity_threshold:.2f}; "
                "the existing Problem's reviewed responder permission cannot be reused, so new-Problem research has started."
            ),
            historical_voice=None,
            modern_translation=None,
            cautions=(
                "This question is materially different from the reviewed Problem. The returned research package is recall-only and does not grant answer permission.",
            ),
            evidence_ids=(),
            insight_ids=(),
            requires_new_problem=True,
            research_package=research,
            status="problem_drift_requires_new_problem_research",
        )

    answer = render_grounded_answer(problem_id, question=question)
    return ProblemConversationTurn(
        problem_id=problem_id,
        person_id=answer.person_id,
        user_question=question,
        route="continue_current_responder",
        route_reason=(
            f"Follow-up continuity score {score:.2f} is within the reviewed Problem scope; "
            "the existing responder may continue under the same evidence gates."
        ),
        historical_voice=answer.historical_voice,
        modern_translation=answer.modern_translation,
        cautions=answer.cautions,
        evidence_ids=answer.evidence_ids,
        insight_ids=answer.insight_ids,
        requires_new_problem=False,
        research_package=None,
        status="continued_with_reviewed_problem_responder",
    )
