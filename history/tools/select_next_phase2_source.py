#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "history" / "source_registry" / "phase2_core_histories.yaml"
CORPUS_ROOT = ROOT / "history" / "source_corpus" / "china"


def load_sources() -> list[dict]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return data["sources"]


def report_path(source: dict) -> Path:
    return CORPUS_ROOT / source["dynasty_group"] / source["corpus_key"] / "ingestion_report.json"


def is_complete(source: dict) -> bool:
    path = report_path(source)
    if not path.exists():
        return False
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    expected_titles = report.get("expected_titles") or []
    archived = int(report.get("archived_file_pairs", 0))
    errors = report.get("errors") or []
    return bool(expected_titles) and not errors and archived >= len(expected_titles)


def next_source_id() -> str | None:
    for source in load_sources():
        if not is_complete(source):
            return source["source_id"]
    return None


def status() -> dict:
    sources = load_sources()
    complete = [source["source_id"] for source in sources if is_complete(source)]
    pending = [source["source_id"] for source in sources if not is_complete(source)]
    return {
        "total": len(sources),
        "complete": len(complete),
        "pending": len(pending),
        "complete_source_ids": complete,
        "pending_source_ids": pending,
        "next_source_id": pending[0] if pending else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = status()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["next_source_id"] or "")


if __name__ == "__main__":
    main()
