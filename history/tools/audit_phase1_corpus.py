#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "history/source_registry/phase1_sources.yaml"
EXTRACTOR_VERSION = 3

FORBIDDEN_MARKERS = (
    "姊妹计划:", "姊妹計畫:", "姊妹计划：", "姊妹計畫：",
    "维基百科", "維基百科", "文言維基", "文言维基",
    "数据项", "資料項", "数据项目", "資料項目",
    "此作品在全世界都属于公有领域", "此作品在全世界都屬於公有領域",
)
ARROW_CHARS = ("◄", "►", "←", "→", "↤", "↦")
CID_RE = re.compile(r"^\[(CN-[A-Z]+-\d{4}-V\d{3}[A-Z]*-P\d{4})\]$", re.MULTILINE)


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


def audit_text_file(text_path: Path, source_id: str) -> list[str]:
    problems: list[str] = []
    text = text_path.read_text(encoding="utf-8")
    if not text.strip():
        return ["empty_text"]

    for marker in FORBIDDEN_MARKERS:
        if marker in text:
            problems.append(f"editorial_marker:{marker}")
    if any(ch in text for ch in ARROW_CHARS):
        problems.append("navigation_arrow")

    cids = CID_RE.findall(text)
    if not cids:
        problems.append("missing_canonical_ids")
    elif any(not cid.startswith(source_id + "-") for cid in cids):
        problems.append("wrong_source_id_in_canonical_id")
    if len(cids) != len(set(cids)):
        problems.append("duplicate_canonical_ids")
    return problems


def main() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    total_expected = total_v3_pairs = total_errors = total_contaminated = total_unexpected = 0

    for src in manifest["sources"]:
        base = ROOT / f"history/source_corpus/china/{src['dynasty_group']}/{src['corpus_key']}"
        report_path = base / "ingestion_report.json"
        errors: list[dict] = []
        expected_titles: list[str] = []
        report_version = 0

        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            errors = report.get("errors", [])
            expected_titles = report.get("expected_titles", [])
            report_version = int(report.get("extractor_version", 0))

        expected_stems = {stem_for_title(title, src["root_page"]) for title in expected_titles}
        text_dir = base / "text"
        prov_dir = base / "provenance"
        actual_text_stems = {p.stem for p in text_dir.glob("*.txt")} if text_dir.exists() else set()
        actual_prov_stems = {p.stem for p in prov_dir.glob("*.yaml")} if prov_dir.exists() else set()
        paired_stems = actual_text_stems & actual_prov_stems
        unexpected_stems = sorted((actual_text_stems | actual_prov_stems) - expected_stems)
        missing_stems = sorted(expected_stems - paired_stems)

        v3_pairs = 0
        contaminated_files: list[dict] = []
        for stem in sorted(expected_stems & paired_stems):
            text_path = text_dir / f"{stem}.txt"
            prov_path = prov_dir / f"{stem}.yaml"
            try:
                prov = yaml.safe_load(prov_path.read_text(encoding="utf-8")) or {}
                if int(prov.get("extractor_version", 0)) >= EXTRACTOR_VERSION:
                    v3_pairs += 1
            except Exception:
                pass

            problems = audit_text_file(text_path, src["source_id"])
            if problems:
                contaminated_files.append({"file": text_path.name, "problems": problems})

        expected = len(expected_stems)
        ok = (
            bool(expected)
            and report_version >= EXTRACTOR_VERSION
            and not errors
            and not missing_stems
            and not unexpected_stems
            and v3_pairs == expected
            and not contaminated_files
        )

        rows.append({
            "source_id": src["source_id"],
            "expected_units": expected,
            "file_pairs": len(paired_stems),
            "v3_file_pairs": v3_pairs,
            "missing_units": len(missing_stems),
            "missing_examples": missing_stems[:10],
            "unexpected_units": len(unexpected_stems),
            "unexpected_examples": unexpected_stems[:10],
            "ingestion_errors": len(errors),
            "contaminated_files": len(contaminated_files),
            "contamination_examples": contaminated_files[:10],
            "complete": ok,
        })
        total_expected += expected
        total_v3_pairs += v3_pairs
        total_errors += len(errors)
        total_contaminated += len(contaminated_files)
        total_unexpected += len(unexpected_stems)

    summary = {
        "extractor_version": EXTRACTOR_VERSION,
        "sources": len(rows),
        "expected_units": total_expected,
        "v3_file_pairs": total_v3_pairs,
        "ingestion_errors": total_errors,
        "contaminated_files": total_contaminated,
        "unexpected_units": total_unexpected,
        "complete": all(r["complete"] for r in rows),
        "reports": rows,
    }

    out = ROOT / "history/source_corpus/PHASE1_INGESTION_SUMMARY.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["complete"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
