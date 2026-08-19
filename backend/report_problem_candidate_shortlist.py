from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from app.services.problem_candidate_shortlist import build_candidate_research_shortlist


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a research-only emperor shortlist for a question")
    parser.add_argument("question")
    parser.add_argument("--problem-id", default=None)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    rows = build_candidate_research_shortlist(
        args.question,
        problem_id=args.problem_id,
        candidate_limit=args.limit,
    )
    print(json.dumps([asdict(row) for row in rows], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
