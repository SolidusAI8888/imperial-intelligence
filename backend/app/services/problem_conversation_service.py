from __future__ import annotations

from dataclasses import dataclass
import re

from app.services.grounded_answer_renderer import render_grounded_answer
from app.services.problem_knowledge_repository import load_problem_spec


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
        "你", "你说", "刚才", "前面", "这个", "这些", "为什么", "那", "那么",
        "但是", "可是", "依据", "证据", "举例", "具体", "怎么办", "意思",
        "不同意", "反对", "真的吗", "如何", "怎样", "为何",
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
) -> ProblemConversationTurn:
    """Continue a reviewed Problem only when the follow-up remains inside its scope.

    The service deliberately refuses to let a materially new question borrow the
    original Problem's reviewed responder permission. Related follow-ups reuse the
    same reviewed response pipeline and responder; drifted questions are routed back
    to new-problem research instead of being answered under stale eligibility.
    """
    question = followup_question.strip()
    if len(question) < 2:
        raise ValueError("followup_question must contain at least two characters")

    spec = load_problem_spec(problem_id)
    problem_text = " ".join(
        [spec.raw_question, spec.normalized_question, *spec.retrieval_dimensions]
    )
    score = _continuity_score(problem_text, question, conversation_history)

    if score < continuity_threshold:
        return ProblemConversationTurn(
            problem_id=problem_id,
            person_id=None,
            user_question=question,
            route="new_problem_required",
            route_reason=(
                f"Follow-up continuity score {score:.2f} is below {continuity_threshold:.2f}; "
                "the existing Problem's reviewed responder permission cannot be reused."
            ),
            historical_voice=None,
            modern_translation=None,
            cautions=(
                "This question appears materially different from the reviewed Problem and must re-enter problem research and role selection.",
            ),
            evidence_ids=(),
            insight_ids=(),
            requires_new_problem=True,
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
        status="continued_with_reviewed_problem_responder",
    )
