from app.services.emperor_eligibility import eligibility_summary
from app.services.emperor_evidence_discovery import discovery_coverage


def test_batch_reports_share_same_complete_roster() -> None:
    eligibility = eligibility_summary()
    discovery = discovery_coverage(limit_per_emperor=1)
    assert eligibility["registered"] == 69
    assert discovery["registered"] == 69
    assert eligibility["registered"] == discovery["registered"]
    assert eligibility["eligible"] >= 3
