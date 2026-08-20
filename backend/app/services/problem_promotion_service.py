from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from app.services.problem_draft_package import DRAFT_ROOT
from app.services.problem_registration_artifacts import (
    build_problem_registration_package,
    persist_problem_registration_package,
)


_DRAFT_ID_RE = re.compile(r"^Q-RESEARCH-[A-F0-9]{12}$")
_REGISTERED_ID_RE = re.compile(r"^Q-[A-Z0-9][A-Z0-9-]{2,63}$")


@dataclass(frozen=True)
class ProblemPromotionResult:
    source_draft_problem_id: str
    registered_problem_id: str
    manifest_path: str
    candidate_profile_path: str
    status: str
    persisted: bool


def promote_problem_draft(
    draft_problem_id: str,
    registered_problem_id: str,
    *,
    persist: bool = False,
    draft_root: Path = DRAFT_ROOT,
) -> ProblemPromotionResult:
    """Validate a reviewed draft and optionally persist its registered artifacts.

    The draft id is restricted to the generated Q-RESEARCH namespace so API callers
    cannot use path traversal or arbitrary filesystem paths. Registration still runs
    the full evidence/readiness validation implemented by
    build_problem_registration_package; this service never changes review flags.
    """
    if not _DRAFT_ID_RE.fullmatch(draft_problem_id):
        raise ValueError("draft_problem_id must match Q-RESEARCH-<12 hex characters>")
    if not _REGISTERED_ID_RE.fullmatch(registered_problem_id):
        raise ValueError("registered_problem_id must be a valid Q-* identifier")
    if registered_problem_id.startswith("Q-RESEARCH-"):
        raise ValueError("registered_problem_id cannot use the Q-RESEARCH namespace")

    draft_dir = draft_root / draft_problem_id
    manifest_path = draft_dir / "manifest.yaml"
    profile_path = draft_dir / "candidate_profile.yaml"
    if not manifest_path.exists() or not profile_path.exists():
        raise FileNotFoundError(f"Problem draft package not found: {draft_problem_id}")

    package = build_problem_registration_package(
        manifest_path,
        profile_path,
        registered_problem_id=registered_problem_id,
    )

    output_manifest = package.manifest.relative_path
    output_profile = package.candidate_profile.relative_path
    status = package.status
    persisted = False
    if persist:
        written_manifest, written_profile = persist_problem_registration_package(package)
        output_manifest = str(written_manifest)
        output_profile = str(written_profile)
        status = "registered_artifacts_persisted"
        persisted = True

    return ProblemPromotionResult(
        source_draft_problem_id=package.source_draft_problem_id,
        registered_problem_id=package.registered_problem_id,
        manifest_path=output_manifest,
        candidate_profile_path=output_profile,
        status=status,
        persisted=persisted,
    )
