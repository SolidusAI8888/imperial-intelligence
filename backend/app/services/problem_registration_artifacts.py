from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml

from app.services.cross_dynasty_selector import CandidateExperience, score_candidate
from app.services.knowledge_repository import (
    load_person_experiences,
    load_person_insights,
    load_person_records,
    load_person_role_links,
)
from app.services.knowledge_runtime import build_runtime_context
from app.services.problem_promotion_readiness import assess_problem_draft_promotion


_PROBLEM_ID_RE = re.compile(r"^Q-[A-Z0-9][A-Z0-9-]{2,63}$")


@dataclass(frozen=True)
class RegistrationArtifact:
    relative_path: str
    content: str
    status: str


@dataclass(frozen=True)
class ProblemRegistrationPackage:
    source_draft_problem_id: str
    registered_problem_id: str
    manifest: RegistrationArtifact
    candidate_profile: RegistrationArtifact
    status: str


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return data


def _dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


def _validate_target_problem_id(problem_id: str) -> None:
    if problem_id.startswith("Q-RESEARCH-"):
        raise ValueError("registered problem_id cannot use the provisional Q-RESEARCH namespace")
    if not _PROBLEM_ID_RE.fullmatch(problem_id):
        raise ValueError("registered problem_id must match Q-[A-Z0-9-] and be 4-65 characters")


def _runtime_candidate_from_reviewed_row(
    row: dict,
    *,
    registered_problem_id: str,
    question: str,
) -> dict:
    person_id = str(row["person_id"])
    payload = dict(row["registration_candidate"])
    requested_heus = set(payload["heu_ids"])
    requested_insights = set(payload["insight_ids"])

    experiences = [
        heu for heu in load_person_experiences(person_id) if heu.heu_id in requested_heus
    ]
    if {heu.heu_id for heu in experiences} != requested_heus:
        raise ValueError(f"Registration candidate {person_id} references missing HEU data")

    record_ids = {record_id for heu in experiences for record_id in heu.record_links}
    records = [
        record for record in load_person_records(person_id) if record.record_id in record_ids
    ]
    if {record.record_id for record in records} != record_ids:
        raise ValueError(f"Registration candidate {person_id} references missing HER data")

    insights = [
        insight
        for insight in load_person_insights(person_id)
        if insight.insight_id in requested_insights
    ]
    if {insight.insight_id for insight in insights} != requested_insights:
        raise ValueError(f"Registration candidate {person_id} references missing Insight data")

    reviewed_objects = [*records, *experiences, *insights]
    if any(item.status not in {"reviewed", "accepted"} for item in reviewed_objects):
        raise ValueError(f"Registration candidate {person_id} contains unreviewed knowledge")

    role_links = [
        link for link in load_person_role_links(person_id) if link.heu_id in requested_heus
    ]
    build_runtime_context(
        problem_id=registered_problem_id,
        question=question,
        person_id=person_id,
        records=records,
        experiences=experiences,
        insights=insights,
        role_links=role_links,
    )

    chain_evidence = {
        canonical_id
        for record in records
        for source in record.sources
        for canonical_id in source.canonical_ids
    }
    declared_evidence = set(payload.get("evidence_ids") or ())
    if not declared_evidence:
        raise ValueError(f"Registration candidate {person_id} must declare canonical evidence IDs")
    if not declared_evidence.issubset(chain_evidence):
        missing = sorted(declared_evidence - chain_evidence)
        raise ValueError(
            f"Registration candidate {person_id} declares evidence outside its HER chain: {missing}"
        )

    scores = dict(payload["scores"])
    candidate = CandidateExperience(
        persona_id=person_id,
        dynasty=str(payload["dynasty"]),
        evidence_ids=tuple(sorted(chain_evidence)),
        experience_similarity=float(scores["experience_similarity"]),
        evidence_strength=float(scores["evidence_strength"]),
        stage_relevance=float(scores["stage_relevance"]),
        lesson_clarity=float(scores["lesson_clarity"]),
        transferability=float(scores["transferability"]),
        counterevidence_quality=float(scores["counterevidence_quality"]),
        rationale=str(payload["rationale"]),
    )
    expected_score = score_candidate(candidate).total_score
    if round(float(row["candidate_score"]), 4) != expected_score:
        raise ValueError(
            f"Registration candidate {person_id} aggregate score does not match reviewed dimensions"
        )

    return {
        "persona_id": person_id,
        "dynasty": payload["dynasty"],
        "evidence_ids": list(payload["evidence_ids"]),
        "heu_ids": list(payload["heu_ids"]),
        "insight_ids": list(payload["insight_ids"]),
        "scores": scores,
        "rationale": payload["rationale"],
    }


def build_problem_registration_package(
    manifest_path: Path,
    candidate_profile_path: Path,
    *,
    registered_problem_id: str,
) -> ProblemRegistrationPackage:
    """Build registration artifacts only after every explicit review and evidence gate passes.

    This function does not persist or register anything. It converts a fully reviewed
    draft into deterministic registration artifacts so a later explicit write can be
    audited separately. Only responder-eligible candidates are emitted into the runtime
    candidate profile because the selector treats every registered profile row as an
    eligible responder. Each emitted row is validated against reviewed HER/HEU/Insight
    ownership and canonical source evidence before artifact generation.
    """
    _validate_target_problem_id(registered_problem_id)
    readiness = assess_problem_draft_promotion(manifest_path, candidate_profile_path)
    if not readiness.ready:
        joined = ", ".join(readiness.blockers)
        raise ValueError(f"Problem draft is not ready for registration: {joined}")

    draft_manifest = _load_yaml(manifest_path)
    draft_profile = _load_yaml(candidate_profile_path)
    source_problem_id = str(draft_manifest["problem_id"])

    profile_rel = f"knowledge/problem_profiles/{registered_problem_id}.yaml"
    manifest_rel = f"knowledge/problems/{registered_problem_id}.yaml"

    manifest = {
        "problem_id": registered_problem_id,
        "raw_question": draft_manifest["raw_question"],
        "normalized_question": draft_manifest["normalized_question"],
        "retrieval_dimensions": list(draft_manifest["retrieval_dimensions"]),
        "knowledge_policy": draft_manifest["knowledge_policy"],
        "candidate_profile": profile_rel,
        "registration_audit": {
            "source_draft_problem_id": source_problem_id,
            "problem_definition_reviewed": True,
            "insight_selection_reviewed": True,
            "candidate_scoring_completed": True,
            "responder_eligibility_reviewed": True,
            "answer_permission": True,
            "runtime_evidence_chain_validated": True,
        },
        "status": "registered_reviewed",
    }

    registered_candidates = [
        _runtime_candidate_from_reviewed_row(
            row,
            registered_problem_id=registered_problem_id,
            question=str(draft_manifest["raw_question"]),
        )
        for row in draft_profile["candidates"]
        if row.get("responder_eligible") is True
    ]

    profile = {
        "problem_id": registered_problem_id,
        "source_draft_problem_id": source_problem_id,
        "status": "registered_reviewed_candidates",
        "candidates": registered_candidates,
    }

    return ProblemRegistrationPackage(
        source_draft_problem_id=source_problem_id,
        registered_problem_id=registered_problem_id,
        manifest=RegistrationArtifact(manifest_rel, _dump_yaml(manifest), "ready_to_persist"),
        candidate_profile=RegistrationArtifact(profile_rel, _dump_yaml(profile), "ready_to_persist"),
        status="registration_artifacts_ready_explicit_write_required",
    )
