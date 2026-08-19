from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml

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


def build_problem_registration_package(
    manifest_path: Path,
    candidate_profile_path: Path,
    *,
    registered_problem_id: str,
) -> ProblemRegistrationPackage:
    """Build authoritative-looking artifacts only after every explicit review gate passes.

    This function does not persist or register anything. It converts a fully reviewed
    draft into deterministic registration artifacts so a later explicit write can be
    audited separately. Only responder-eligible candidates are emitted into the runtime
    candidate profile because the selector treats every registered profile row as an
    eligible responder.
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
        },
        "status": "registered_reviewed",
    }

    registered_candidates: list[dict] = []
    for row in draft_profile["candidates"]:
        if row.get("responder_eligible") is not True:
            continue
        payload = dict(row["registration_candidate"])
        registered_candidates.append(
            {
                "persona_id": row["person_id"],
                "dynasty": payload["dynasty"],
                "evidence_ids": list(payload.get("evidence_ids") or ()),
                "heu_ids": list(payload["heu_ids"]),
                "insight_ids": list(payload["insight_ids"]),
                "scores": dict(payload["scores"]),
                "rationale": payload["rationale"],
            }
        )

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
