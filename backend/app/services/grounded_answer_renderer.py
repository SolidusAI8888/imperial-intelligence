from __future__ import annotations

from dataclasses import dataclass

from app.services.problem_response_pipeline import build_grounded_response_bundle
from app.services.knowledge_repository import load_person_voice_evidence
from app.services.persona_voice_evidence import build_persona_voice_profile, style_answer_opening


@dataclass(frozen=True)
class RenderedGroundedAnswer:
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


def render_grounded_answer(problem_id: str, question: str | None = None) -> RenderedGroundedAnswer:
    """Render a deterministic answer only from the reviewed response bundle.

    The renderer is intentionally conservative. Historical first-person prose may
    restate reviewed HEU challenge/choice/outcome material and reviewed Insights,
    but it may not introduce new events, quotations, motives or source awareness.
    Modern transfer is kept outside the historical voice and framed as a bounded
    interpretation rather than as a guaranteed prescription.
    """
    bundle = build_grounded_response_bundle(problem_id, question)
    context = bundle.context
    voice_profile = build_persona_voice_profile(
        context.person_id, load_person_voice_evidence(context.person_id)
    )

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

    insight_text = "；".join(bundle.insight_statements)
    historical_voice = "\n\n".join(
        [
            style_answer_opening(
                "若只依据我一生中已经有史料支持的经历来回答，我不会把这个问题归结为一个简单因素。",
                voice_profile,
            ),
            *experience_paragraphs,
            f"从这些经历中，当前经过审核、可以支持的判断是：{insight_text}。",
        ]
    )

    modern_translation = (
        "把这些历史经验迁移到今天时，较稳妥的做法是把上述判断当作决策检查项，"
        "而不是把历史人物的处境直接等同于现代个人处境，也不能把某种行动解释成结果保证。"
    )

    cautions = (
        "历史人物第一人称部分仅重述当前 reviewed/accepted HEU 与 Insight 可支持的内容；未加入新的历史事件、动机或伪造引语。",
        "史料名称与证据编号属于现代证据层，不应被写成历史人物本人知道后世编纂史书。",
        "现代迁移属于解释层，不把帝王治理经验直接视为现代个人生活的等价处方。",
    )

    return RenderedGroundedAnswer(
        problem_id=context.problem_id,
        person_id=context.person_id,
        question=context.question,
        historical_voice=historical_voice,
        modern_translation=modern_translation,
        cautions=cautions,
        evidence_ids=bundle.evidence_ids,
        insight_ids=bundle.plan.insight_ids,
        status="rendered_from_reviewed_grounded_bundle",
        voice_evidence_ids=(
            voice_profile.applied_voice_evidence_ids if voice_profile else ()
        ),
    )
