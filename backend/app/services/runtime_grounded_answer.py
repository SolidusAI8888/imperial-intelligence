from __future__ import annotations

from dataclasses import dataclass

from app.models.knowledge import RuntimeContext
from app.services.knowledge_repository import (
    load_person_experiences,
    load_person_insights,
    load_person_records,
    load_person_role_links,
    load_person_voice_evidence,
)
from app.services.knowledge_runtime import build_runtime_context
from app.services.persona_voice_evidence import (
    PersonaVoiceProfile,
    build_persona_voice_profile,
    style_answer_opening,
)
from app.services.runtime_candidate_assessment import assess_runtime_problem


@dataclass(frozen=True)
class RuntimeRenderedGroundedAnswer:
    problem_id: str
    person_id: str
    question: str
    historical_voice: str
    modern_translation: str
    cautions: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    insight_ids: tuple[str, ...]
    status: str
    voice_evidence_ids: tuple[str, ...] = ()


def _join_items(items: list[str]) -> str:
    cleaned = [item.strip() for item in items if item and item.strip()]
    return "；".join(cleaned)


def _build_runtime_context(question: str, *, candidate_limit: int = 20) -> tuple[RuntimeContext, tuple[str, ...], tuple[str, ...], PersonaVoiceProfile | None]:
    assessment = assess_runtime_problem(question, candidate_limit=candidate_limit)
    if not assessment.auto_answer_ready or not assessment.selected_person_id:
        raise ValueError("Runtime problem has not passed the automatic evidence gate")
    selected = next((c for c in assessment.candidates if c.person_id == assessment.selected_person_id and c.auto_answer_ready), None)
    if selected is None:
        raise ValueError("Selected runtime responder is not answer-ready")
    heu_ids, insight_ids = set(selected.heu_ids), set(selected.insight_ids)
    experiences = [h for h in load_person_experiences(selected.person_id) if h.heu_id in heu_ids and h.status in {"reviewed", "accepted"}]
    record_ids = {rid for h in experiences for rid in h.record_links}
    records = [r for r in load_person_records(selected.person_id) if r.record_id in record_ids and r.status in {"reviewed", "accepted"}]
    insights = [i for i in load_person_insights(selected.person_id) if i.insight_id in insight_ids and i.status in {"reviewed", "accepted"}]
    role_links = [l for l in load_person_role_links(selected.person_id) if l.heu_id in heu_ids and l.responder_eligible]
    context = build_runtime_context(problem_id=assessment.problem_id, question=assessment.question, person_id=selected.person_id, records=records, experiences=experiences, insights=insights, role_links=role_links)
    evidence_ids = tuple(sorted({cid for r in context.records for s in r.sources for cid in s.canonical_ids}))
    if evidence_ids != selected.evidence_ids:
        raise ValueError("Runtime answer evidence diverges from automatic candidate assessment")
    voice_profile = build_persona_voice_profile(
        selected.person_id, load_person_voice_evidence(selected.person_id)
    )
    return context, evidence_ids, tuple(sorted(insight_ids)), voice_profile


def render_runtime_grounded_answer(question: str, *, anchor_question: str | None = None, candidate_limit: int = 20) -> RuntimeRenderedGroundedAnswer:
    """Render from a fresh or anchored runtime evidence bundle.

    Related follow-ups may supply anchor_question so the original evidence-gated Problem remains
    authoritative while the visible answer addresses the new turn. No permanent Problem is created.
    """
    anchor = anchor_question or question
    context, evidence_ids, insight_ids, voice_profile = _build_runtime_context(anchor, candidate_limit=candidate_limit)
    experience_paragraphs: list[str] = []
    for heu in context.experiences:
        parts = [f"我曾面对这样的处境：{heu.challenge.strip()}"]
        choices = _join_items(list(heu.response_or_choice))
        if choices:
            parts.append(f"当时采取的应对包括：{choices}")
        outcomes = _join_items(list(heu.experienced_outcome))
        if outcomes:
            parts.append(f"随后实际经历的结果包括：{outcomes}")
        reflections = _join_items(list(heu.explicit_reflection))
        if reflections:
            parts.append(f"后来能够明确留下的反思是：{reflections}")
        experience_paragraphs.append("。".join(parts) + "。")
    insight_text = "；".join(insight.statement for insight in context.insights)
    historical_voice = "\n\n".join([
        style_answer_opening(
            "若只依据我一生中已经有史料支持的经历来回答，我不会把这个问题归结为一个简单因素。",
            voice_profile,
        ),
        *experience_paragraphs,
        f"从这些经历中，当前经过审核、可以支持的判断是：{insight_text}。",
    ])
    modern_translation = "把这些历史经验迁移到今天时，较稳妥的做法是把上述判断当作决策检查项，而不是把历史人物的处境直接等同于现代个人处境，也不能把某种行动解释成结果保证。"
    cautions = (
        "该回答来自运行时自动召回，但只使用 reviewed/accepted HER、HEU、Insight 与 responder-eligible Role Link。",
        "运行时自动通过证据门不等于创建或批准新的永久 Problem 文件；其结论仍受当前知识覆盖范围限制。",
        "现代迁移属于解释层，不把帝王治理经验直接视为现代个人生活的等价处方。",
    )
    return RuntimeRenderedGroundedAnswer(problem_id=context.problem_id, person_id=context.person_id, question=question, historical_voice=historical_voice, modern_translation=modern_translation, cautions=cautions, evidence_ids=evidence_ids, insight_ids=insight_ids, status="rendered_from_runtime_reviewed_grounded_bundle", voice_evidence_ids=voice_profile.voice_evidence_ids if voice_profile else ())
