from __future__ import annotations

from dataclasses import dataclass
import re

from app.services.problem_draft_package import DRAFT_ROOT
from app.services.problem_promotion_readiness import assess_problem_draft_promotion


_DRAFT_ID_RE = re.compile(r"^Q-RESEARCH-[A-F0-9]{16}$")


@dataclass(frozen=True)
class ProblemDraftReadinessStatus:
    problem_id: str
    ready: bool
    blockers: tuple[str, ...]
    status: str
    manifest_path: str
    candidate_profile_path: str


def inspect_problem_draft_readiness(draft_problem_id: str) -> ProblemDraftReadinessStatus:
    """Inspect a persisted draft without mutating review or approval state.

    Draft IDs are strictly validated before filesystem resolution so callers cannot
    use this read-only endpoint to inspect arbitrary paths. The assessment delegates
    to the same promotion-readiness gate used by registration, ensuring the API and
    promotion path report the same blockers.
    """
    if not _DRAFT_ID_RE.fullmatch(draft_problem_id):
        raise ValueError(f"Invalid draft_problem_id: {draft_problem_id}")

    target_dir = DRAFT_ROOT / draft_problem_id
    manifest_path = target_dir / "manifest.yaml"
    profile_path = target_dir / "candidate_profile.yaml"
    if not manifest_path.exists() or not profile_path.exists():
        raise FileNotFoundError(f"Persisted draft package not found: {draft_problem_id}")

    readiness = assess_problem_draft_promotion(manifest_path, profile_path)
    if readiness.problem_id != draft_problem_id:
        raise ValueError(
            f"Draft problem_id mismatch: expected {draft_problem_id}, got {readiness.problem_id}"
        )

    return ProblemDraftReadinessStatus(
        problem_id=readiness.problem_id,
        ready=readiness.ready,
        blockers=readiness.blockers,
        status=readiness.status,
        manifest_path=str(manifest_path),
        candidate_profile_path=str(profile_path),
    )
