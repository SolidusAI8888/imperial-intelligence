from __future__ import annotations

from app.services.emperor_evidence_discovery import discovery_coverage


def main() -> None:
    report = discovery_coverage(limit_per_emperor=5)
    print(
        "registered={registered} discoverable={discoverable} undiscoverable={undiscoverable}".format(
            **report
        )
    )
    for row in report["rows"]:
        evidence = ",".join(row["top_evidence_ids"][:3]) or "-"
        print(
            f"{row['dynasty']}\t{row['persona_id']}\t{row['name']}\t"
            f"hits={row['hit_count']}\tevidence={evidence}"
        )


if __name__ == "__main__":
    main()
