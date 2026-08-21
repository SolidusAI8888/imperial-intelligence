from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from app.services.knowledge_repository import PROJECT_ROOT


SOURCE_CORPUS_ROOT = PROJECT_ROOT / "history" / "source_corpus"


@dataclass(frozen=True)
class ArchivedPassage:
    source_id: str
    passage_id: str
    path: Path
    text: str
    integrity_verified: bool


def normalized_source_text(value: str) -> str:
    return " ".join(value.split())


def _archive_file_integrity_verified(path: Path, source_id: str) -> bool:
    report_path = path.parent.parent / "ingestion_report.json"
    if not report_path.exists():
        return False
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if not isinstance(report, dict) or report.get("source_id") != source_id:
        return False
    pages = report.get("pages")
    if not isinstance(pages, list):
        return False
    page = next(
        (
            item
            for item in pages
            if isinstance(item, dict)
            and item.get("file") == path.name
            and item.get("sha256")
        ),
        None,
    )
    if page is None:
        return False
    actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    return actual_hash == page["sha256"]


def find_archived_passage(
    source_id: str,
    passage_id: str,
    *,
    corpus_root: Path | None = None,
) -> ArchivedPassage | None:
    """Resolve one canonical passage and verify its ingested source-file checksum."""

    root = corpus_root or SOURCE_CORPUS_ROOT
    marker = f"[{passage_id}]"
    for path in sorted(root.rglob("*.txt")) if root.exists() else ():
        text = path.read_text(encoding="utf-8")
        marker_start = text.find(marker)
        if marker_start < 0:
            continue
        if marker_start > 0 and text[marker_start - 1] != "\n":
            continue
        content_start = marker_start + len(marker)
        next_marker = text.find("\n[CN-", content_start)
        passage = text[content_start : next_marker if next_marker >= 0 else None].strip()
        return ArchivedPassage(
            source_id=source_id,
            passage_id=passage_id,
            path=path,
            text=passage,
            integrity_verified=_archive_file_integrity_verified(path, source_id),
        )
    return None
