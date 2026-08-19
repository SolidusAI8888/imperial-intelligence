from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Iterable

import yaml

from app.services.emperor_evidence_discovery import discover_emperor_evidence
from app.services.emperor_eligibility import all_registered_emperors


PROJECT_ROOT = Path(__file__).resolve().parents[3]
QUEUE_POLICY_PATH = PROJECT_ROOT / "knowledge" / "research" / "R-000001" / "review" / "EMPEROR-QUEUE-POLICY.yaml"


def _load_policy() -> dict:
    with QUEUE_POLICY_PATH.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("Invalid emperor review queue policy")
    return data


def build_review_queue(
    *,
    persona_ids: Iterable[str] | None = None,
    evidence_limit: int = 5,
) -> dict:
    """Build a deterministic queue of *candidate* evidence for manual/reviewed knowledge work.

    This function never creates HER/HEU/Insight/Role Link records and never changes
    eligibility. It only orders the remaining emperors by how much canonical evidence
    is already discoverable in the archived source corpus.
    """
    policy = _load_policy()
    requested = set(persona_ids or [])
    restrict = persona_ids is not None

    rows = []
    for emperor in all_registered_emperors():
        if emperor.eligible:
            continue
        if restrict and emperor.persona_id not in requested:
            continue

        hits = discover_emperor_evidence(emperor.persona_id, limit=evidence_limit)
        top_score = hits[0].score if hits else 0
        evidence_count = len(hits)
        readiness = (
            "ready_for_evidence_review"
            if evidence_count >= int(policy["minimum_candidate_hits_for_review"])
            else "needs_more_candidate_evidence"
        )
        priority_score = top_score + min(evidence_count, evidence_limit) * int(policy["hit_count_weight"])

        rows.append(
            {
                "persona_id": emperor.persona_id,
                "dynasty": emperor.dynasty,
                "name": emperor.name,
                "title": emperor.title,
                "eligibility": "not_yet_eligible",
                "readiness": readiness,
                "priority_score": priority_score,
                "candidate_evidence": [asdict(hit) for hit in hits],
            }
        )

    rows.sort(key=lambda row: (-row["priority_score"], row["dynasty"], row["persona_id"]))
    return {
        "problem_id": policy["problem_id"],
        "policy_version": policy["version"],
        "registered_remaining": len(rows),
        "ready_for_evidence_review": sum(1 for row in rows if row["readiness"] == "ready_for_evidence_review"),
        "needs_more_candidate_evidence": sum(1 for row in rows if row["readiness"] == "needs_more_candidate_evidence"),
        "rows": rows,
    }
