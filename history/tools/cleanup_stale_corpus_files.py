#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "history/source_registry/phase1_sources.yaml"


def stem_for_title(title: str, root_page: str) -> str:
    match = re.match(rf"^{re.escape(root_page)}/卷0*(\d+)(.*)$", title)
    if not match:
        raise ValueError(f"unrecognized volume title: {title}")
    volume = int(match.group(1))
    suffix = match.group(2)
    part = {"": "", "上": "a", "中": "b", "下": "c", "a": "a", "b": "b", "c": "c"}.get(
        suffix, "x" + hashlib.sha1(suffix.encode()).hexdigest()[:4]
    )
    return f"{volume:03d}{part}"


def main() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    removed: list[str] = []

    for src in manifest["sources"]:
        base = ROOT / f"history/source_corpus/china/{src['dynasty_group']}/{src['corpus_key']}"
        report_path = base / "ingestion_report.json"
        if not report_path.exists():
            continue

        report = json.loads(report_path.read_text(encoding="utf-8"))
        expected_titles = report.get("expected_titles", [])
        if not expected_titles:
            continue

        expected_stems = {stem_for_title(title, src["root_page"]) for title in expected_titles}
        text_dir = base / "text"
        prov_dir = base / "provenance"
        existing_stems = {p.stem for p in text_dir.glob("*.txt")} | {p.stem for p in prov_dir.glob("*.yaml")}
        stale = sorted(existing_stems - expected_stems)

        for stem in stale:
            for path in (text_dir / f"{stem}.txt", prov_dir / f"{stem}.yaml"):
                if path.exists():
                    path.unlink()
                    removed.append(str(path.relative_to(ROOT)))

    print(json.dumps({"removed_files": len(removed), "files": removed}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
