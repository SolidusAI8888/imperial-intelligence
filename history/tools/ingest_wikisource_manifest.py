#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from ingest_wikisource_phase1 import EXTRACTOR_VERSION, archive_source


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "history/source_registry/phase2_core_histories.yaml"


def load_manifest(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "sources" not in data:
        raise ValueError(f"invalid ingestion manifest: {path}")
    source_ids = [item.get("source_id") for item in data["sources"]]
    if any(not sid for sid in source_ids):
        raise ValueError("every source must have a stable source_id")
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("duplicate source_id in ingestion manifest")
    return data


def ordered_sources(manifest: dict) -> list[dict]:
    sources = manifest["sources"]
    order = manifest.get("order", [])
    if not order:
        return sources
    out: list[dict] = []
    seen: set[str] = set()
    for group in order:
        for source in sources:
            if source.get("dynasty_group") == group:
                out.append(source)
                seen.add(source["source_id"])
    out.extend(source for source in sources if source["source_id"] not in seen)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--source-id", help="Ingest one registered source only")
    parser.add_argument("--list", action="store_true", help="List registered sources without network ingestion")
    args = parser.parse_args()

    manifest_path = args.manifest
    if not manifest_path.is_absolute():
        manifest_path = (ROOT / manifest_path).resolve()
    manifest = load_manifest(manifest_path)
    sources = ordered_sources(manifest)

    if args.source_id:
        sources = [source for source in sources if source["source_id"] == args.source_id]
        if not sources:
            raise SystemExit(f"unknown source id: {args.source_id}")

    if args.list:
        print(json.dumps({
            "extractor_version": EXTRACTOR_VERSION,
            "manifest": str(manifest_path.relative_to(ROOT)),
            "sources": [
                {
                    "source_id": source["source_id"],
                    "title": source["title"],
                    "dynasty_group": source["dynasty_group"],
                    "volume_min": source["volume_min"],
                    "volume_max": source["volume_max"],
                }
                for source in sources
            ],
        }, ensure_ascii=False, indent=2))
        return

    reports = [archive_source(source) for source in sources]
    failed = sum(len(report["errors"]) for report in reports)
    print(json.dumps({
        "extractor_version": EXTRACTOR_VERSION,
        "manifest": str(manifest_path.relative_to(ROOT)),
        "sources_processed": len(reports),
        "archived_or_refreshed": sum(len(report["pages"]) for report in reports),
        "skipped_current": sum(len(report["skipped_current"]) for report in reports),
        "errors": failed,
    }, ensure_ascii=False, indent=2), flush=True)
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
