import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "history" / "tools" / "build_qing_persona_voice_access_review.py"


def _module():
    spec = importlib.util.spec_from_file_location("qing_voice_access_review", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_shangyu_access_review_fails_closed_until_permission_is_resolved() -> None:
    packet = _module().build_access_review_packet("CN-QING-VOICE-0001")

    assert packet["review_recorded"] is True
    assert packet["online_catalogue_access"] is True
    assert packet["online_full_text_access"] is False
    assert packet["bulk_machine_access_confirmed"] is False
    assert packet["reuse_permission"] == "written_archive_permission_required"
    assert "reuse_rights" in packet["unresolved_requirements"]
    assert packet["automated_ingestion_allowed"] is False
    assert packet["pvc_creation_allowed"] is False
    assert packet["decision"] == "automated_ingestion_not_authorized"
    assert len(packet["provenance"]) >= 4


def test_zhupi_access_review_also_fails_closed() -> None:
    packet = _module().build_access_review_packet("CN-QING-VOICE-0002")

    assert packet["review_recorded"] is True
    assert packet["online_catalogue_access"] is True
    assert packet["online_full_text_access"] is False
    assert packet["reuse_permission"] == "written_archive_permission_required"
    assert packet["decision"] == "automated_ingestion_not_authorized"
    assert packet["automated_ingestion_allowed"] is False
    assert packet["pvc_creation_allowed"] is False


def test_source_without_access_review_is_explicitly_unreviewed() -> None:
    packet = _module().build_access_review_packet("CN-QING-VOICE-0003")

    assert packet["review_recorded"] is False
    assert packet["decision"] == "access_review_not_recorded"
    assert packet["automated_ingestion_allowed"] is False


def test_unknown_source_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown Qing persona voice source"):
        _module().build_access_review_packet("CN-QING-VOICE-9999")
