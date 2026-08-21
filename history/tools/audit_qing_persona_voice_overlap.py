#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "history" / "source_registry" / "qing_persona_voice_sources.yaml"
SOURCE_ID = "CN-QING-VOICE-0004"
MANIFEST_READY_STATUSES = {
    "catalog_verified_ready_for_manifest",
    "ready_for_ingestion",
}


def load_source() -> dict:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    for source in data.get("sources") or ():
        if source.get("source_id") == SOURCE_ID:
            return source
    raise ValueError(f"missing Qing persona voice source: {SOURCE_ID}")


def audit_overlap() -> dict:
    """Verify that every normalized Grand Council subseries has one safe action."""

    source = load_source()
    subseries = tuple(source.get("discovered_scope", {}).get("normalized_subseries") or ())
    review = source.get("overlap_review") or {}
    rules = tuple(review.get("rules") or ())
    names = [rule.get("subseries") for rule in rules]
    counts = Counter(names)
    missing = tuple(name for name in subseries if counts[name] == 0)
    duplicate = tuple(sorted(name for name, count in counts.items() if count > 1))
    unexpected = tuple(sorted(name for name in counts if name not in subseries))
    invalid_actions = tuple(
        sorted(
            rule.get("subseries", "")
            for rule in rules
            if rule.get("action")
            not in {"link_not_merge", "exclude_from_source", "retain_under_source"}
        )
    )
    reviewed = len(subseries) - len(missing)
    overlap_control_complete = bool(
        review
        and subseries
        and not missing
        and not duplicate
        and not unexpected
        and not invalid_actions
        and len(rules) == len(subseries)
    )
    unresolved = tuple(source.get("remaining_requirements") or ())
    manifest_design_allowed = bool(
        overlap_control_complete
        and source.get("status") in MANIFEST_READY_STATUSES
        and not unresolved
    )

    return {
        "source_id": SOURCE_ID,
        "total_subseries": len(subseries),
        "reviewed_subseries": reviewed,
        "missing_subseries": missing,
        "duplicate_subseries": duplicate,
        "unexpected_subseries": unexpected,
        "invalid_action_subseries": invalid_actions,
        "link_only_subseries": tuple(
            rule["subseries"] for rule in rules if rule.get("action") == "link_not_merge"
        ),
        "excluded_subseries": tuple(
            rule["subseries"]
            for rule in rules
            if rule.get("action") == "exclude_from_source"
        ),
        "retained_subseries": tuple(
            rule["subseries"]
            for rule in rules
            if rule.get("action") == "retain_under_source"
        ),
        "overlap_control_complete": overlap_control_complete,
        "registry_status": source.get("status"),
        "unresolved_requirements": unresolved,
        "manifest_design_allowed": manifest_design_allowed,
        "status": (
            "overlap_review_complete_access_still_blocked"
            if overlap_control_complete and not manifest_design_allowed
            else "overlap_review_requires_repair"
        ),
        "safety_note": (
            "record copies and source originals remain linked but never merged across series"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = audit_overlap()
    print(
        json.dumps(result, ensure_ascii=False, indent=2)
        if args.json
        else result["status"]
    )


if __name__ == "__main__":
    main()
