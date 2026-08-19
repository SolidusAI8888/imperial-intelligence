from __future__ import annotations

import json

from app.services.emperor_eligibility import (
    all_registered_emperors,
    assert_candidate_registry_consistency,
    eligibility_summary,
)


def main() -> None:
    assert_candidate_registry_consistency()
    summary = eligibility_summary()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\nRemaining emperors by dynasty:")
    for dynasty in ("han", "tang", "song"):
        names = [
            f"{row.title}({row.name})"
            for row in all_registered_emperors()
            if row.dynasty == dynasty and not row.eligible
        ]
        print(f"{dynasty}: {len(names)}")
        print("、".join(names))


if __name__ == "__main__":
    main()
