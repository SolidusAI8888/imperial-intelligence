#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "history" / "source_registry" / "phase3_primary_sources.yaml"
CORPUS_ROOT = ROOT / "history" / "source_corpus" / "china"


def load_sources() -> list[dict]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    groups = data.get("priority_order") or []
    sources = data.get("sources") or []
    if not isinstance(sources, list):
        raise ValueError("phase3 manifest sources must be a list")
    seen: set[str] = set()
    for source in sources:
        source_id = source.get("source_id")
        if not source_id or source_id in seen:
            raise ValueError("phase3 source IDs must be present and unique")
        seen.add(source_id)
    if not groups:
        return sources
    order = {group: idx for idx, group in enumerate(groups)}
    return sorted(sources, key=lambda item: (order.get(item.get("priority_group"), 999), item["source_id"]))


def report_path(source: dict) -> Path | None:
    dynasty_group = source.get("dynasty_group")
    corpus_key = source.get("corpus_key")
    if not dynasty_group or not corpus_key:
        return None
    return CORPUS_ROOT / dynasty_group / corpus_key / "ingestion_report.json"


def ingestion_complete(source: dict) -> bool:
    path = report_path(source)
    if path is None or not path.exists():
        return False
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    expected_titles = report.get("expected_titles") or []
    archived = int(report.get("archived_file_pairs", 0))
    errors = report.get("errors") or []
    return bool(expected_titles) and not errors and archived >= len(expected_titles)


def terminal_non_ingested(source: dict) -> bool:
    return source.get("status") in {"documented_unavailable", "blocked_with_reason"}


def is_complete(source: dict) -> bool:
    return ingestion_complete(source) or terminal_non_ingested(source)


def next_actionable_source() -> dict | None:
    for source in load_sources():
        if is_complete(source):
            continue
        return source
    return None


def status() -> dict:
    sources = load_sources()
    complete = [source for source in sources if is_complete(source)]
    pending = [source for source in sources if not is_complete(source)]
    ready = [source for source in pending if source.get("acquisition_strategy") == "wikisource_numbered_volumes"]
    catalog = [source for source in pending if source.get("acquisition_strategy") == "catalog_required"]
    next_source = pending[0] if pending else None
    return {
        "total": len(sources),
        "complete": len(complete),
        "pending": len(pending),
        "ready_for_numbered_ingestion": [source["source_id"] for source in ready],
        "catalog_resolution_required": [source["source_id"] for source in catalog],
        "next_source_id": next_source["source_id"] if next_source else None,
        "next_source_strategy": next_source.get("acquisition_strategy") if next_source else None,
        "next_source_title": next_source.get("title") if next_source else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--next-numbered", action="store_true", help="Return next source compatible with numbered-volume ingestion")
    args = parser.parse_args()

    if args.next_numbered:
        for source in load_sources():
            if not is_complete(source) and source.get("acquisition_strategy") == "wikisource_numbered_volumes":
                print(source["source_id"])
                return
        print("")
        return

    result = status()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["next_source_id"] or "")


if __name__ == "__main__":
    main()
