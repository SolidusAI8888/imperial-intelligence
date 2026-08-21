#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "history" / "source_registry" / "qing_persona_voice_sources.yaml"
COMPLETE_STATUSES = {"ingested", "documented_unavailable"}
BLOCKED_STATUS = "blocked_with_reason"
ACTIONABLE_STATUSES = {
    "pending_source_discovery",
    "catalog_verified_access_review_required",
    "catalog_verified_ready_for_manifest",
    "ready_for_ingestion",
}


def load_sources() -> list[dict]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    sources = data.get("sources") or []
    priority = data.get("priority_order") or []
    if not isinstance(sources, list):
        raise ValueError("Qing persona voice sources must be a list")

    order = {group: index for index, group in enumerate(priority)}
    seen: set[str] = set()
    for source in sources:
        required = {
            "source_id",
            "source_key",
            "title",
            "priority_group",
            "evidence_tier",
            "source_kinds",
            "acquisition_strategy",
            "status",
        }
        missing = sorted(required - set(source))
        if missing:
            raise ValueError(f"source missing required fields: {', '.join(missing)}")
        source_id = source["source_id"]
        if source_id in seen:
            raise ValueError(f"duplicate source ID: {source_id}")
        seen.add(source_id)
        if source["priority_group"] not in order:
            raise ValueError(f"unknown priority group for {source_id}")
        if source["status"] == "pending_source_discovery":
            if source["acquisition_strategy"] != "source_discovery_required":
                raise ValueError(f"pending discovery strategy mismatch for {source_id}")
            if not source.get("resolution_requirements"):
                raise ValueError(f"pending discovery requirements missing for {source_id}")
        if source["status"] == "catalog_verified_access_review_required":
            if source["acquisition_strategy"] != "archival_access_review_required":
                raise ValueError(f"verified catalog strategy mismatch for {source_id}")
            if not (
                source.get("holding_institution")
                and source.get("discovered_scope")
                and source.get("provenance")
                and source.get("remaining_requirements")
            ):
                raise ValueError(f"verified catalog evidence incomplete for {source_id}")
        if source["status"] == BLOCKED_STATUS and not (
            source.get("block_reason") and source.get("provenance")
        ):
            raise ValueError(f"blocked source lacks reason or provenance: {source_id}")
        if source["status"] == "documented_unavailable" and not (
            source.get("unavailability_reason") and source.get("provenance")
        ):
            raise ValueError(f"unavailable source lacks reason or provenance: {source_id}")
        if source["status"] == "ingested" and not (
            source.get("corpus_path") and source.get("ingestion_report")
        ):
            raise ValueError(f"ingested source lacks archive evidence: {source_id}")

    return sorted(
        sources,
        key=lambda source: (order[source["priority_group"]], source["source_id"]),
    )


def is_complete(source: dict) -> bool:
    return source["status"] in COMPLETE_STATUSES


def next_actionable_source() -> dict | None:
    return next(
        (source for source in load_sources() if source["status"] in ACTIONABLE_STATUSES),
        None,
    )


def status() -> dict:
    sources = load_sources()
    complete = [source for source in sources if is_complete(source)]
    blocked = [source for source in sources if source["status"] == BLOCKED_STATUS]
    pending = [source for source in sources if not is_complete(source)]
    discovery = [
        source for source in sources if source["status"] == "pending_source_discovery"
    ]
    access_review = [
        source
        for source in sources
        if source["status"] == "catalog_verified_access_review_required"
    ]
    next_source = next_actionable_source()
    return {
        "total": len(sources),
        "complete": len(complete),
        "pending": len(pending),
        "blocked": len(blocked),
        "discovery_required_source_ids": [source["source_id"] for source in discovery],
        "access_review_required_source_ids": [
            source["source_id"] for source in access_review
        ],
        "complete_source_ids": [source["source_id"] for source in complete],
        "blocked_source_ids": [source["source_id"] for source in blocked],
        "next_source_id": next_source["source_id"] if next_source else None,
        "next_source_title": next_source["title"] if next_source else None,
        "next_source_strategy": (
            next_source["acquisition_strategy"] if next_source else None
        ),
        "completion_warning": (
            "registration or source discovery never implies that historical content was collected"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = status()
    print(
        json.dumps(result, ensure_ascii=False, indent=2)
        if args.json
        else (result["next_source_id"] or "")
    )


if __name__ == "__main__":
    main()
