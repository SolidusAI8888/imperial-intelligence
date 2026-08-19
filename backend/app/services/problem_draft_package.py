from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from app.services.problem_research_package import (
    ProblemResearchPackage,
    build_problem_research_package,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DRAFT_ROOT = PROJECT_ROOT / "knowledge" / "problem_drafts"


@dataclass(frozen=True)
class ProblemDraftArtifact:
    relative_path: str
    content: str
    status: str


@dataclass(frozen=True)
class ProblemDraftPackage:
    problem_id: str
    manifest: ProblemDraftArtifact
    candidate_profile: ProblemDraftArtifact
    status: str
    responder_eligible: bool
    can_render_answer: bool
    required_next_gate: str


def _dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


def build_problem_draft_package(
    question: str,
    *,
    candidate_limit: int = 20,
) -> ProblemDraftPackage:
    """Convert research intake into reviewable, non-authoritative draft artifacts."""
    research: ProblemResearchPackage = build_problem_research_package(
        question,
        candidate_limit=candidate_limit,
    )
    problem_id = research.proposed_problem_id
    profile_rel = f"knowledge/problem_drafts/{problem_id}/candidate_profile.yaml"
    manifest_rel = f"knowledge/problem_drafts/{problem_id}/manifest.yaml"

    manifest = {
        "problem_id": problem_id,
        "raw_question": research.raw_question,
        "normalized_question": research.normalized_question,
        "status": "draft_requires_problem_specific_review",
        "knowledge_policy": {
            "reusable_layers": ["HER", "HEU"],
            "problem_specific_layers": [
                "insight_selection",
                "candidate_scoring",
                "responder_eligibility",
            ],
            "rule": (
                "This draft may reuse reviewed HER/HEU evidence, but recalled evidence does not "
                "become a problem-specific Insight or responder permission without review."
            ),
        },
        "candidate_profile": profile_rel,
        "review_gate": {
            "required": True,
            "problem_definition_reviewed": False,
            "insight_selection_reviewed": False,
            "can_render_answer": False,
            "responder_eligibility_locked": True,
            "next_step": research.required_next_gate,
        },
    }

    profile = {
        "problem_id": problem_id,
        "status": "draft_research_candidates_only",
        "candidates": [
            {
                "person_id": candidate.person_id,
                "recalled_heu_ids": list(candidate.heu_ids),
                "retrieval_score": candidate.retrieval_score,
                "review_priority": candidate.review_priority,
                "selected_insight_ids": [],
                "candidate_score": None,
                "status": "requires_problem_specific_review",
                "responder_eligible": False,
            }
            for candidate in research.candidates
        ],
        "approval_gate": {
            "candidate_scoring_completed": False,
            "responder_eligibility_reviewed": False,
            "answer_permission": False,
        },
    }

    return ProblemDraftPackage(
        problem_id=problem_id,
        manifest=ProblemDraftArtifact(manifest_rel, _dump_yaml(manifest), "draft_only"),
        candidate_profile=ProblemDraftArtifact(profile_rel, _dump_yaml(profile), "draft_only"),
        status="draft_package_requires_human_review",
        responder_eligible=False,
        can_render_answer=False,
        required_next_gate=research.required_next_gate,
    )


def persist_problem_draft_package(
    package: ProblemDraftPackage,
    *,
    root: Path = DRAFT_ROOT,
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """Persist drafts only under a dedicated draft root; never register a Problem."""
    target_dir = root / package.problem_id
    manifest_path = target_dir / "manifest.yaml"
    profile_path = target_dir / "candidate_profile.yaml"

    if not overwrite and (manifest_path.exists() or profile_path.exists()):
        raise FileExistsError(f"Draft package already exists: {target_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(package.manifest.content, encoding="utf-8")
    profile_path.write_text(package.candidate_profile.content, encoding="utf-8")
    return manifest_path, profile_path
