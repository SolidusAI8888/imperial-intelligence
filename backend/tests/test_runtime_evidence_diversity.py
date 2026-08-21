from types import SimpleNamespace

from app.services.runtime_candidate_assessment import _has_independent_record_support


def test_multiple_citations_on_one_record_do_not_count_as_independent_support() -> None:
    records = [SimpleNamespace(record_id="HER-ONE")]
    assert _has_independent_record_support(records) is False


def test_two_distinct_reviewed_records_satisfy_independent_support_gate() -> None:
    records = [
        SimpleNamespace(record_id="HER-ONE"),
        SimpleNamespace(record_id="HER-TWO"),
    ]
    assert _has_independent_record_support(records) is True


def test_duplicate_record_objects_do_not_fake_independent_support() -> None:
    records = [
        SimpleNamespace(record_id="HER-ONE"),
        SimpleNamespace(record_id="HER-ONE"),
    ]
    assert _has_independent_record_support(records) is False
