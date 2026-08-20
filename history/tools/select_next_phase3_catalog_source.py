#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "history" / "source_registry" / "phase3_catalog_sources.yaml"
CORPUS_ROOT = ROOT / "history" / "source_corpus" / "china"


def sources() -> list[dict]:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["sources"]


def report_path(source: dict) -> Path:
    return CORPUS_ROOT / source["dynasty_group"] / source["corpus_key"] / "ingestion_report.json"


def archive_scope_complete(source: dict) -> bool:
    path = report_path(source)
    if not path.exists():
        return False
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return report.get("archive_scope_complete") is True and not report.get("errors")


def status() -> dict:
    rows = sources()
    complete = [row["source_id"] for row in rows if archive_scope_complete(row)]
    pending = [row["source_id"] for row in rows if not archive_scope_complete(row)]
    return {
        "total_catalog_sources": len(rows),
        "host_archive_complete": len(complete),
        "host_archive_pending": len(pending),
        "complete_source_ids": complete,
        "pending_source_ids": pending,
        "next_source_id": pending[0] if pending else None,
        "warning": "host_archive_complete never implies historical source completeness when host_completeness is explicitly_incomplete",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = status()
    print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else (data["next_source_id"] or ""))


if __name__ == "__main__":
    main()
