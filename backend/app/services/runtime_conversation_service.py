from __future__ import annotations

from dataclasses import dataclass
import re

from app.services.problem_research_package import ProblemResearchPackage, build_problem_research_package, provisional_problem_id
from app.services.runtime_candidate_assessment import assess_runtime_problem
from app.services.runtime_grounded_answer import render_runtime_grounded_answer

_WORD_RE = re.compile(r"[A-Za-z0-9_]+")
_CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff]+")


@dataclass(frozen=True)
class RuntimeConversationTurn:
    original_problem_id: str
    active_problem_id: str
    person_id: str | None
    previous_person_id: str | None
    user_question: str
    route: str
    route_reason: str
    responder_switched: bool
    historical_voice: str | None
    modern_translation: str | None
    cautions: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    insight_ids: tuple[str, ...]
    research_package: ProblemResearchPackage | None
    status: str
    voice_evidence_ids: tuple[str, ...] = ()


def _tokens(text: str) -> set[str]:
    """Return word tokens plus Chinese character bigrams.

    Single-character Chinese overlap badly overestimates semantic continuity because unrelated
    questions often share generic characters such as 应、该、先. Bigrams preserve lightweight,
    dependency-free matching while sharply reducing those false positives.
    """
    text = text or ""
    tokens = {word.lower() for word in _WORD_RE.findall(text)}
    for run in _CJK_RUN_RE.findall(text):
        if len(run) == 1:
            tokens.add(run)
        else:
            tokens.update(run[index : index + 2] for index in range(len(run) - 1))
    return tokens


def _continuity_score(anchor_question: str, followup: str, history: tuple[str, ...]) -> float:
    follow = _tokens(followup)
    if not follow:
        return 0.0
    anchor = _tokens(anchor_question)
    score = len(anchor & follow) / max(1, len(follow))
    if history:
        recent = _tokens(" ".join(history[-4:]))
        score = max(score, len(recent & follow) / max(1, len(follow)))
    continuation_markers = {
        "你刚才", "你前面", "你说", "刚才说", "前面说", "这个观点", "这个判断",
        "这些经历", "这个例子", "这件事", "但是你", "可是你", "我不同意", "我反对",
        "你的依据", "你的证据", "具体一点", "再举例", "那你的意思", "那么你的意思",
        "那我该怎么办", "那具体怎么办", "为什么", "怎么做",
    }
    if any(marker in followup for marker in continuation_markers):
        score = max(score, 0.45)
    return min(1.0, score)


def continue_runtime_conversation(
    original_problem_id: str,
    original_question: str,
    followup_question: str,
    *,
    previous_person_id: str | None = None,
    conversation_history: tuple[str, ...] = (),
    continuity_threshold: float = 0.20,
    candidate_limit: int = 20,
) -> RuntimeConversationTurn:
    """Continue an unpersisted runtime Problem and automatically reselect on semantic drift.

    The original question is the stateless session anchor. Its deterministic provisional ID must
    match the supplied runtime Problem ID, preventing clients from reusing one runtime permission
    for unrelated text. Related follow-ups reuse the same reviewed evidence bundle. Drifted
    follow-ups undergo a fresh automatic assessment: when the evidence gate passes, a new runtime
    Problem and responder are selected immediately; otherwise the turn safely stops at research.
    """
    anchor = original_question.strip()
    question = followup_question.strip()
    if len(anchor) < 2 or len(question) < 2:
        raise ValueError("original_question and followup_question must contain at least two characters")
    if candidate_limit < 1 or candidate_limit > 50:
        raise ValueError("candidate_limit must be between 1 and 50")
    expected_problem_id = provisional_problem_id(anchor)
    if original_problem_id != expected_problem_id:
        raise ValueError("runtime problem_id does not match the deterministic original_question ID")

    anchor_assessment = assess_runtime_problem(anchor, candidate_limit=candidate_limit)
    if not anchor_assessment.auto_answer_ready or not anchor_assessment.selected_person_id:
        raise ValueError("original runtime Problem no longer passes the automatic evidence gate")
    current_person_id = anchor_assessment.selected_person_id
    if previous_person_id is not None and previous_person_id != current_person_id:
        raise ValueError("previous_person_id does not match the current evidence-gated responder")

    score = _continuity_score(anchor, question, conversation_history)
    if score >= continuity_threshold:
        answer = render_runtime_grounded_answer(question, anchor_question=anchor, candidate_limit=candidate_limit)
        return RuntimeConversationTurn(
            original_problem_id=original_problem_id,
            active_problem_id=original_problem_id,
            person_id=answer.person_id,
            previous_person_id=current_person_id,
            user_question=question,
            route="continue_current_runtime_responder",
            route_reason=(f"Follow-up continuity score {score:.2f} is within runtime Problem scope; the same reviewed evidence bundle remains authoritative."),
            responder_switched=False,
            historical_voice=answer.historical_voice,
            modern_translation=answer.modern_translation,
            cautions=answer.cautions,
            evidence_ids=answer.evidence_ids,
            insight_ids=answer.insight_ids,
            research_package=None,
            status="continued_with_runtime_grounded_responder",
            voice_evidence_ids=getattr(answer, "voice_evidence_ids", ()),
        )

    drift_assessment = assess_runtime_problem(question, candidate_limit=candidate_limit)
    if drift_assessment.auto_answer_ready and drift_assessment.selected_person_id:
        answer = render_runtime_grounded_answer(question, candidate_limit=candidate_limit)
        return RuntimeConversationTurn(
            original_problem_id=original_problem_id,
            active_problem_id=drift_assessment.problem_id,
            person_id=answer.person_id,
            previous_person_id=current_person_id,
            user_question=question,
            route="drift_reselected_runtime_responder",
            route_reason=(f"Follow-up continuity score {score:.2f} is below {continuity_threshold:.2f}; a fresh runtime Problem passed the evidence gate and a responder was reselected."),
            responder_switched=answer.person_id != current_person_id,
            historical_voice=answer.historical_voice,
            modern_translation=answer.modern_translation,
            cautions=answer.cautions,
            evidence_ids=answer.evidence_ids,
            insight_ids=answer.insight_ids,
            research_package=None,
            status="runtime_problem_drift_reselected_and_answered",
            voice_evidence_ids=getattr(answer, "voice_evidence_ids", ()),
        )

    research = build_problem_research_package(question, candidate_limit=candidate_limit)
    return RuntimeConversationTurn(
        original_problem_id=original_problem_id,
        active_problem_id=drift_assessment.problem_id,
        person_id=None,
        previous_person_id=current_person_id,
        user_question=question,
        route="drift_requires_new_problem_research",
        route_reason=(f"Follow-up continuity score {score:.2f} is below {continuity_threshold:.2f}; fresh runtime assessment did not pass the evidence gate."),
        responder_switched=False,
        historical_voice=None,
        modern_translation=None,
        cautions=("The drifted question cannot inherit the prior runtime responder permission.",),
        evidence_ids=(),
        insight_ids=(),
        research_package=research,
        status="runtime_problem_drift_requires_research",
        voice_evidence_ids=(),
    )
