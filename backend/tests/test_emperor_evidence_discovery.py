from app.services.emperor_evidence_discovery import (
    discover_emperor_evidence,
    discovery_coverage,
)


def test_tang_taizong_has_discoverable_canonical_evidence() -> None:
    hits = discover_emperor_evidence("tang_taizong", limit=10)
    assert hits
    assert all(hit.canonical_id.startswith("CN-TANG-") for hit in hits)
    assert any("李世民" in hit.matched_terms or "唐太宗" in hit.matched_terms for hit in hits)


def test_liu_bang_has_discoverable_canonical_evidence() -> None:
    hits = discover_emperor_evidence("liu_bang", limit=10)
    assert hits
    assert all(hit.canonical_id.startswith("CN-HAN-") for hit in hits)


def test_song_taizu_has_discoverable_canonical_evidence() -> None:
    hits = discover_emperor_evidence("song_taizu", limit=10)
    assert hits
    assert all(hit.canonical_id.startswith("CN-SONG-") for hit in hits)


def test_discovery_scans_complete_registered_roster() -> None:
    report = discovery_coverage(limit_per_emperor=1)
    assert report["registered"] == 69
    assert report["discoverable"] + report["undiscoverable"] == 69
    assert len(report["rows"]) == 69
