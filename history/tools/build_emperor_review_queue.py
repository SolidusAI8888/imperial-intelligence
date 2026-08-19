#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.emperor_review_queue import build_review_queue  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona-id", action="append", dest="persona_ids")
    parser.add_argument("--evidence-limit", type=int, default=5)
    parser.add_argument("--format", choices=("json", "yaml"), default="yaml")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = build_review_queue(
        persona_ids=args.persona_ids,
        evidence_limit=args.evidence_limit,
    )
    if args.format == "json":
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    else:
        rendered = yaml.safe_dump(report, allow_unicode=True, sort_keys=False)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
