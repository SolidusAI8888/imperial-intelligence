from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROBLEM_ROOT = PROJECT_ROOT / "knowledge" / "problems"


@dataclass(frozen=True)
class ProblemKnowledgeSpec:
    problem_id: str
    raw_question: str
    normalized_question: str
    retrieval_dimensions: tuple[str, ...]
    candidate_profile_path: Path
    reusable_layers: tuple[str, ...]
    problem_specific_layers: tuple[str, ...]
    status: str


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return data


def problem_manifest_path(problem_id: str) -> Path:
    return PROBLEM_ROOT / f"{problem_id}.yaml"


def load_problem_spec(problem_id: str) -> ProblemKnowledgeSpec:
    path = problem_manifest_path(problem_id)
    if not path.exists():
        raise KeyError(f"Unknown problem_id: {problem_id}")

    raw = _load_yaml(path)
    if raw.get("problem_id") != problem_id:
        raise ValueError(f"Problem manifest ID mismatch: {path}")

    policy = raw.get("knowledge_policy") or {}
    reusable = tuple(policy.get("reusable_layers") or ())
    problem_specific = tuple(policy.get("problem_specific_layers") or ())

    if not {"HER", "HEU"}.issubset(set(reusable)):
        raise ValueError(f"Problem {problem_id} must preserve HER/HEU as reusable layers")
    if not {"insight_selection", "candidate_scoring", "responder_eligibility"}.issubset(
        set(problem_specific)
    ):
        raise ValueError(f"Problem {problem_id} is missing problem-specific reasoning gates")

    candidate_profile = raw.get("candidate_profile")
    if not candidate_profile:
        raise ValueError(f"Problem {problem_id} has no candidate_profile")
    profile_path = PROJECT_ROOT / candidate_profile
    if not profile_path.exists():
        raise ValueError(f"Problem {problem_id} candidate profile does not exist: {candidate_profile}")

    retrieval_dimensions = tuple(str(item) for item in (raw.get("retrieval_dimensions") or ()))
    if not retrieval_dimensions:
        raise ValueError(f"Problem {problem_id} must define retrieval_dimensions")

    return ProblemKnowledgeSpec(
        problem_id=problem_id,
        raw_question=str(raw.get("raw_question", "")),
        normalized_question=str(raw.get("normalized_question", "")),
        retrieval_dimensions=retrieval_dimensions,
        candidate_profile_path=profile_path,
        reusable_layers=reusable,
        problem_specific_layers=problem_specific,
        status=str(raw.get("status", "draft")),
    )


def load_problem_candidate_profile(problem_id: str) -> dict:
    spec = load_problem_spec(problem_id)
    profile = _load_yaml(spec.candidate_profile_path)
    if profile.get("problem_id") != problem_id:
        raise ValueError(
            f"Candidate profile problem_id mismatch for {problem_id}: "
            f"{spec.candidate_profile_path}"
        )
    candidates = profile.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError(f"Problem {problem_id} candidate profile must contain a list")
    return profile
