from __future__ import annotations

from dataclasses import dataclass

from app.models.knowledge import RuntimeContext
from app.services.cross_dynasty_selector import problem_candidates, rank_candidates
from app.services.knowledge_repository import (
    load_person_experiences,
    load_person_insights,
    load_person_records,
    load_person_role_links,
)
from app.services.knowledge_runtime import build_runtime_context, render_grounded_context
from app.services.problem_knowledge_repository import (
    load_problem_candidate_profile,
    load_problem_spec,
)


@dataclass(frozen=True)
class ProblemResponsePlan:
    problem_id: str
    person_id: str
    total_score: float
    evidence_ids: tuple[str, ...]
    heu_ids: tuple[str, ...]
    insight_ids: tuple[str, ...]
    rationale: str
    status: str


@dataclass(frozen=True)
class GroundedResponseBundle:
    plan: ProblemResponsePlan
    context: RuntimeContext
    grounded_context: str
    evidence_ids: tuple[str, ...]
    insight_statements: tuple[str, ...]
    status: str


def _selected_profile_row(problem_id: str, person_id: str) -> dict:
    profile = load_problem_candidate_profile(problem_id)
    matches = [row for row in profile["candidates"] if row.get("persona_id") == person_id]
    if len(matches) != 1:
        raise ValueError(f"Problem {problem_id} must contain exactly one candidate row for {person_id}")
    return matches[0]


def build_problem_response_plan(problem_id: str) -> ProblemResponsePlan:
    """Select the highest-scoring responder only from a reviewed problem profile.

    Research recall/shortlisting/review queues are intentionally not accepted here.
    `problem_candidates()` is the eligibility gate: it validates the declared HER -> HEU ->
    Insight chain, reviewed statuses, role links, canonical evidence and runtime context before
    a candidate can receive a score.
    """
    spec = load_problem_spec(problem_id)
    if spec.status not in {"retrieval_ready", "reviewed", "accepted"}:
        raise ValueError(f"Problem {problem_id} is not ready for responder selection")

    ranked = rank_candidates(problem_candidates(problem_id))
    if not ranked:
        raise ValueError(f"Problem {problem_id} has no responder-eligible candidates")

    winner = ranked[0]
    row = _selected_profile_row(problem_id, winner.persona_id)
    return ProblemResponsePlan(
        problem_id=problem_id,
        person_id=winner.persona_id,
        total_score=winner.total_score,
        evidence_ids=winner.evidence_ids,
        heu_ids=tuple(row["heu_ids"]),
        insight_ids=tuple(row["insight_ids"]),
        rationale=winner.rationale,
        status="responder_selected_from_reviewed_problem_profile",
    )


def build_selected_runtime_context(problem_id: str, question: str | None = None) -> RuntimeContext:
    plan = build_problem_response_plan(problem_id)
    spec = load_problem_spec(problem_id)
    person_id = plan.person_id

    experiences = [heu for heu in load_person_experiences(person_id) if heu.heu_id in set(plan.heu_ids)]
    record_ids = {record_id for heu in experiences for record_id in heu.record_links}
    records = [record for record in load_person_records(person_id) if record.record_id in record_ids]
    insights = [insight for insight in load_person_insights(person_id) if insight.insight_id in set(plan.insight_ids)]
    role_links = [link for link in load_person_role_links(person_id) if link.heu_id in set(plan.heu_ids)]

    return build_runtime_context(
        problem_id=problem_id,
        question=question or spec.raw_question,
        person_id=person_id,
        records=records,
        experiences=experiences,
        insights=insights,
        role_links=role_links,
    )


def build_grounded_response_bundle(problem_id: str, question: str | None = None) -> GroundedResponseBundle:
    """Build the complete evidence-constrained input bundle for answer generation.

    This is the final deterministic gate before a prose/persona renderer. It deliberately does
    not invent historical speech. Any downstream renderer may use only this reviewed bundle and
    must keep source names/citations outside first-person historical voice.
    """
    plan = build_problem_response_plan(problem_id)
    context = build_selected_runtime_context(problem_id, question)
    evidence_ids = tuple(sorted({canonical_id for record in context.records for source in record.sources for canonical_id in source.canonical_ids}))
    if evidence_ids != plan.evidence_ids:
        raise ValueError(f"Problem {problem_id} selected runtime evidence diverges from candidate profile")

    return GroundedResponseBundle(
        plan=plan,
        context=context,
        grounded_context=render_grounded_context(context),
        evidence_ids=evidence_ids,
        insight_statements=tuple(insight.statement for insight in context.insights),
        status="ready_for_grounded_answer_generation",
    )
