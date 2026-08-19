from app.services.emperor_eligibility import (
    all_registered_emperors,
    assert_candidate_registry_consistency,
    eligibility_summary,
)


ELIGIBLE_IDS = {
    "liu_bang",
    "han_wendi",
    "tang_gaozu",
    "tang_taizong",
    "song_taizu",
    "song_renzong",
}


def test_all_registered_emperors_are_screened() -> None:
    rows = all_registered_emperors()
    assert len(rows) == 69
    assert {row.dynasty for row in rows} == {"han", "tang", "song"}
    assert len({row.persona_id for row in rows}) == 69


def test_current_first_question_eligibility_is_explicit() -> None:
    rows = all_registered_emperors()
    eligible = {row.persona_id for row in rows if row.eligible}
    assert eligible == ELIGIBLE_IDS
    assert all(row.reason for row in rows)


def test_eligibility_summary_tracks_remaining_work() -> None:
    summary = eligibility_summary()
    assert summary["registered"] == 69
    assert summary["eligible"] == 6
    assert summary["remaining"] == 63
    assert sum(item["registered"] for item in summary["by_dynasty"].values()) == 69
    assert sum(item["eligible"] for item in summary["by_dynasty"].values()) == 6


def test_candidate_registry_consistency() -> None:
    assert_candidate_registry_consistency()
