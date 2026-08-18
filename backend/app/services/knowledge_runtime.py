from __future__ import annotations

from app.models.knowledge import (
    HistoricalExperienceUnit,
    HistoricalRecord,
    Insight,
    RoleExperienceLink,
    RuntimeContext,
)


def build_runtime_context(
    *,
    problem_id: str,
    question: str,
    person_id: str,
    records: list[HistoricalRecord],
    experiences: list[HistoricalExperienceUnit],
    insights: list[Insight],
    role_links: list[RoleExperienceLink],
) -> RuntimeContext:
    """Build and validate the complete knowledge chain for one persona response.

    This function intentionally performs no retrieval and no role selection.
    Upstream research/retrieval must already have produced reviewed objects.
    RuntimeContext validation guarantees:

    Source Corpus -> HER -> HEU -> Insight -> Role Link -> Persona Runtime

    and enforces the full-lifetime persona rule.
    """

    return RuntimeContext(
        problem_id=problem_id,
        question=question,
        person_id=person_id,
        life_course_rule="full_lifetime",
        records=records,
        experiences=experiences,
        insights=insights,
        role_links=role_links,
    )


def render_grounded_context(context: RuntimeContext) -> str:
    """Render a compact, auditable context for the persona layer.

    Historical facts, lived experience, and transferable insights remain
    explicitly separated so the final answer step cannot silently collapse them.
    """

    lines: list[str] = [
        f"Problem ID: {context.problem_id}",
        f"Question: {context.question}",
        f"Responder: {context.person_id}",
        "Life-course rule: full_lifetime",
        "",
        "[HISTORICAL RECORDS — factual layer]",
    ]

    for record in context.records:
        canonical_ids = [cid for source in record.sources for cid in source.canonical_ids]
        lines.extend(
            [
                f"- {record.record_id}: {record.title}",
                f"  Record: {record.historical_record}",
                f"  Canonical IDs: {', '.join(canonical_ids)}",
            ]
        )

    lines.append("")
    lines.append("[HISTORICAL EXPERIENCES — person-centered layer]")
    for heu in context.experiences:
        lines.extend(
            [
                f"- {heu.heu_id}: {heu.title}",
                f"  Owner: {heu.experience_owner}",
                f"  Challenge: {heu.challenge}",
                f"  Response/choice: {' | '.join(heu.response_or_choice)}",
                f"  Outcome: {' | '.join(heu.experienced_outcome)}",
            ]
        )
        if heu.explicit_reflection:
            lines.append(f"  Explicit reflection: {' | '.join(heu.explicit_reflection)}")

    lines.append("")
    lines.append("[INSIGHTS — derived layer]")
    for insight in context.insights:
        lines.extend(
            [
                f"- {insight.insight_id}: {insight.statement}",
                f"  Derived from: {', '.join(insight.derived_from_heus)}",
            ]
        )
        if insight.limits:
            lines.append(f"  Limits: {' | '.join(insight.limits)}")

    lines.extend(
        [
            "",
            "[ANSWER RULES]",
            "- Speak as the selected historical persona using complete-lifetime experience.",
            "- Begin from personally relevant historical experience before general advice.",
            "- Do not invent motives, emotions, events, or reflections absent from the supplied context.",
            "- Do not treat an Insight as a directly recorded historical quotation.",
            "- Preserve uncertainty and limits where the evidence is incomplete.",
        ]
    )

    return "\n".join(lines)
