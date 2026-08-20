from __future__ import annotations

from dataclasses import dataclass

from app.models.knowledge import RuntimeContext
from app.services.knowledge_repository import (
    load_person_experiences,
    load_person_insights,
    load_person_records,
    load_person_role_links,
)
from app.services.knowledge_runtime import build_runtime_context
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


def _join_items(items: list[str]) -> str:
    cleaned = [item.strip() for item in items if item and item.strip()]
    return "；".join(cleaned)


def _build_runtime_context(question: str, *, candidate_limit: int = 20) -> tuple[RuntimeContext, tuple[str, ...], tuple[str, ...]]:
    assessment = assess_runtime_problem(question, candidate_limit=candidate_limit)
    if not assessment.auto_answer_ready or not assessment.selected_person_id:
        raise ValueError("Runtime problem has not passed the automatic evidence gate")

    selected = next(
        (
            candidate
            for candidate in assessment.candidates
            if candidate.person_id == assessment.selected_person_id and candidate.auto_answer_ready
        ),
        None,
    )
    if selected is None:
        raise ValueError("Selected runtime responder is not answer-ready")

    heu_ids = set(selected.heu_ids)
    insight_ids = set(selected.insight_ids)
    experiences = [
        heu
        for heu in load_person_experiences(selected.person_id)
        if heu.heu_id in heu_ids and heu.status in {"reviewed", "accepted"}
    ]
    record_ids = {record_id for heu in experiences for record_id in heu.record_links}
    records = [
        record
        for record in load_person_records(selected.person_id)
        if record.record_id in record_ids and record.status in {"reviewed", "accepted"}
    ]
    insights = [
        insight
        for insight in load_person_insights(selected.person_id)
        if insight.insight_id in insight_ids and insight.status in {"reviewed", "accepted"}
    ]
    role_links = [
        link
        for link in load_person_role_links(selected.person_id)
        if link.heu_id in heu_ids and link.responder_eligible
    ]

    context = build_runtime_context(
        problem_id=assessment.problem_id,
        question=assessment.question,
        person_id=selected.person_id,
        records=records,
        experiences=experiences,
        insights=insights,
        role_links=role_links,
    )
    evidence_ids = tuple(
        sorted(
            {
                canonical_id
                for record in context.records
                for source in record.sources
                for canonical_id in source.canonical_ids
            }
        )
    )
    if evidence_ids != selected.evidence_ids:
        raise ValueError("Runtime answer evidence diverges from automatic candidate assessment")

    return context, evidence_ids, tuple(sorted(insight_ids))


def render_runtime_grounded_answer(
    question: str,
    *,
    candidate_limit: int = 20,
) -> RuntimeRenderedGroundedAnswer:
    """Render an unseen question only after reviewed reusable knowledge passes the automatic gate.

    No Problem manifest is persisted and no reviewed artifact is mutated. The answer is built from
    the same reviewed HER -> HEU -> Insight -> eligible Role Link chain used by the assessment.
    """
    context, evidence_ids, insight_ids = _build_runtime_context(
        question,
        candidate_limit=candidate_limit,
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

    insight_text = "；".join(insight.statement for insight in context.insights)
    historical_voice = "\n\n".join(
        [
            "若只依据我一生中已经有史料支持的经历来回答，我不会把这个问题归结为一个简单因素。",
            *experience_paragraphs,
            f"从这些经历中，当前经过审核、可以支持的判断是：{insight_text}。",
        ]
    )
    modern_translation = (
        "把这些历史经验迁移到今天时，较稳妥的做法是把上述判断当作决策检查项，"
        "而不是把历史人物的处境直接等同于现代个人处境，也不能把某种行动解释成结果保证。"
    )
    cautions = (
        "该回答来自运行时自动召回，但只使用 reviewed/accepted HER、HEU、Insight 与 responder-eligible Role Link。",
        "运行时自动通过证据门不等于创建或批准新的永久 Problem 文件；其结论仍受当前知识覆盖范围限制。",
        "现代迁移属于解释层，不把帝王治理经验直接视为现代个人生活的等价处方。",
    )

    return RuntimeRenderedGroundedAnswer(
        problem_id=context.problem_id,
        person_id=context.person_id,
        question=context.question,
        historical_voice=historical_voice,
        modern_translation=modern_translation,
        cautions=cautions,
        evidence_ids=evidence_ids,
        insight_ids=insight_ids,
        status="rendered_from_runtime_reviewed_grounded_bundle",
    )
