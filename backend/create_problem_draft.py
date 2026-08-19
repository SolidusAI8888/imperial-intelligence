from __future__ import annotations

import argparse
from dataclasses import asdict
import json

from app.services.problem_draft_package import (
    build_problem_draft_package,
    persist_problem_draft_package,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a non-authoritative review draft for a new problem"
    )
    parser.add_argument("question")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    package = build_problem_draft_package(args.question, candidate_limit=args.limit)
    payload = asdict(package)

    if args.write:
        manifest_path, profile_path = persist_problem_draft_package(
            package,
            overwrite=args.overwrite,
        )
        payload["written_paths"] = [str(manifest_path), str(profile_path)]

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
