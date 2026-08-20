from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.problem_registration_artifacts import (
    build_problem_registration_package,
    persist_problem_registration_package,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a fully reviewed Problem draft and generate registration artifacts."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("candidate_profile", type=Path)
    parser.add_argument("registered_problem_id")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Persist into knowledge/problems and knowledge/problem_profiles. Default is dry-run.",
    )
    args = parser.parse_args()

    package = build_problem_registration_package(
        args.manifest,
        args.candidate_profile,
        registered_problem_id=args.registered_problem_id,
    )

    result = {
        "source_draft_problem_id": package.source_draft_problem_id,
        "registered_problem_id": package.registered_problem_id,
        "manifest_path": package.manifest.relative_path,
        "candidate_profile_path": package.candidate_profile.relative_path,
        "status": package.status,
        "write_performed": False,
    }
    if args.write:
        manifest_path, profile_path = persist_problem_registration_package(package)
        result["manifest_path"] = str(manifest_path)
        result["candidate_profile_path"] = str(profile_path)
        result["write_performed"] = True
        result["status"] = "registered_artifacts_persisted"

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
