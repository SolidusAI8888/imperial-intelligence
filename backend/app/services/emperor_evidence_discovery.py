from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EMPEROR_REGISTRY_PATH = PROJECT_ROOT / "knowledge" / "personas" / "han_tang_song_emperor_registry.yaml"
CORPUS_ROOT = PROJECT_ROOT / "history" / "source_corpus" / "china"
CANONICAL_RE = re.compile(r"\[(CN-[A-Z0-9-]+-V\d+-P\d+)\]")


@dataclass(frozen=True)
class EvidenceHit:
    persona_id: str
    dynasty: str
    canonical_id: str
    source_path: str
    matched_terms: tuple[str, ...]
    excerpt: str
    score: int


def _load_registry() -> dict:
    with EMPEROR_REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict) or "dynasties" not in data:
        raise ValueError("Invalid emperor registry")
    return data


def _terms_for_emperor(emperor: dict) -> tuple[str, ...]:
    terms = [emperor.get("name", ""), emperor.get("temple_or_posthumous", "")]
    return tuple(dict.fromkeys(term for term in terms if term and len(term) >= 2))


def _iter_passages(text: str):
    matches = list(CANONICAL_RE.finditer(text))
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            yield match.group(1), body


def discover_emperor_evidence(persona_id: str, *, limit: int = 20) -> list[EvidenceHit]:
    registry = _load_registry()
    target_dynasty = None
    target = None
    for dynasty, dynasty_data in registry["dynasties"].items():
        for emperor in dynasty_data["emperors"]:
            if emperor["persona_id"] == persona_id:
                target_dynasty = dynasty
                target = emperor
                break
        if target is not None:
            break
    if target is None or target_dynasty is None:
        raise KeyError(f"Unknown emperor persona_id: {persona_id}")

    terms = _terms_for_emperor(target)
    if not terms:
        return []

    dynasty_root = CORPUS_ROOT / target_dynasty
    if not dynasty_root.exists():
        return []

    hits: list[EvidenceHit] = []
    for path in dynasty_root.rglob("*.txt"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for canonical_id, passage in _iter_passages(text):
            matched = tuple(term for term in terms if term in passage)
            if not matched:
                continue
            # Prefer passages that mention both personal name and imperial title,
            # and substantive passages over tiny index/navigation fragments.
            score = len(matched) * 100 + min(len(passage), 800) // 40
            hits.append(
                EvidenceHit(
                    persona_id=persona_id,
                    dynasty=target_dynasty,
                    canonical_id=canonical_id,
                    source_path=str(path.relative_to(PROJECT_ROOT)),
                    matched_terms=matched,
                    excerpt=passage[:800],
                    score=score,
                )
            )

    hits.sort(key=lambda item: (-item.score, item.canonical_id))
    return hits[:limit]


def discovery_coverage(*, min_hits: int = 1, limit_per_emperor: int = 5) -> dict:
    registry = _load_registry()
    rows = []
    for dynasty, dynasty_data in registry["dynasties"].items():
        for emperor in dynasty_data["emperors"]:
            hits = discover_emperor_evidence(emperor["persona_id"], limit=limit_per_emperor)
            rows.append(
                {
                    "persona_id": emperor["persona_id"],
                    "dynasty": dynasty,
                    "name": emperor["name"],
                    "title": emperor["temple_or_posthumous"],
                    "hit_count": len(hits),
                    "discoverable": len(hits) >= min_hits,
                    "top_evidence_ids": [hit.canonical_id for hit in hits],
                }
            )
    return {
        "registered": len(rows),
        "discoverable": sum(1 for row in rows if row["discoverable"]),
        "undiscoverable": sum(1 for row in rows if not row["discoverable"]),
        "rows": rows,
    }
