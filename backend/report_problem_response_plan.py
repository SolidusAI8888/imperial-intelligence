from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from app.services.problem_response_pipeline import build_problem_response_plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the reviewed responder selection plan")
    parser.add_argument("problem_id")
    args = parser.parse_args()
    print(json.dumps(asdict(build_problem_response_plan(args.problem_id)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
