#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "history" / "source_registry" / "qing_persona_voice_sources.yaml"
INGESTIBLE_STATUSES = {"catalog_verified_ready_for_manifest", "ready_for_ingestion"}


def load_source(source_id: str) -> dict:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    for source in data.get("sources") or []:
        if source.get("source_id") == source_id:
            return source
    raise ValueError(f"unknown Qing persona voice source: {source_id}")


def build_access_review_packet(source_id: str) -> dict:
    """Turn archival access facts into a fail-closed ingestion decision."""

    source = load_source(source_id)
    review = source.get("access_review") or {}
    unresolved = tuple(source.get("remaining_requirements") or ())
    decision = review.get("decision", "access_review_not_recorded")
    automated_ingestion_allowed = bool(
        source.get("status") in INGESTIBLE_STATUSES
        and review
        and not unresolved
        and decision == "automated_ingestion_authorized"
    )
    provenance = tuple(
        dict.fromkeys(
            [*(source.get("provenance") or ()), *(review.get("provenance") or ())]
        )
    )

    return {
        "source_id": source["source_id"],
        "title": source["title"],
        "holding_institution": source.get("holding_institution"),
        "registry_status": source["status"],
        "review_recorded": bool(review),
        "reviewed_at": review.get("reviewed_at"),
        "access_mode": review.get("access_mode"),
        "online_catalogue_access": review.get("online_catalogue_access", False),
        "online_full_text_access": review.get("online_full_text_access", False),
        "bulk_machine_access_confirmed": review.get(
            "bulk_machine_access_confirmed", False
        ),
        "restrictions": tuple(review.get("restrictions") or ()),
        "reuse_permission": review.get("reuse_permission", "not_reviewed"),
        "unresolved_requirements": unresolved,
        "automated_ingestion_allowed": automated_ingestion_allowed,
        "pvc_creation_allowed": automated_ingestion_allowed,
        "decision": decision,
        "next_action": (
            "resolve access, locator, reuse, and transcription requirements before manifest creation"
            if unresolved
            else "prepare a source-specific ingestion manifest"
        ),
        "provenance": provenance,
        "safety_note": (
            "catalog discoverability and on-site consultation do not authorize automated collection"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    packet = build_access_review_packet(args.source_id)
    print(
        json.dumps(packet, ensure_ascii=False, indent=2)
        if args.json
        else packet["decision"]
    )


if __name__ == "__main__":
    main()
