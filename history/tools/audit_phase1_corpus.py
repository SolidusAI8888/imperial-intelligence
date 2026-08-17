#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "history/source_registry/phase1_sources.yaml"
EXTRACTOR_VERSION = 2


def main() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    total_expected = total_pairs = total_errors = 0
    for src in manifest["sources"]:
        base = ROOT / f"history/source_corpus/china/{src['dynasty_group']}/{src['corpus_key']}"
        report_path = base / "ingestion_report.json"
        errors = []
        expected_titles = []
        report_version = 0
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            errors = report.get("errors", [])
            expected_titles = report.get("expected_titles", [])
            report_version = int(report.get("extractor_version", 0))
        text_dir = base / "text"; prov_dir = base / "provenance"
        pairs = 0; v2_pairs = 0
        if text_dir.exists():
            for text_path in text_dir.glob("*.txt"):
                prov_path = prov_dir / f"{text_path.stem}.yaml"
                if not prov_path.exists():
                    continue
                pairs += 1
                try:
                    prov = yaml.safe_load(prov_path.read_text(encoding="utf-8")) or {}
                    if int(prov.get("extractor_version", 0)) >= EXTRACTOR_VERSION:
                        v2_pairs += 1
                except Exception:
                    pass
        expected = len(expected_titles)
        ok = bool(expected) and report_version >= EXTRACTOR_VERSION and not errors and pairs >= expected and v2_pairs >= expected
        rows.append({
            "source_id": src["source_id"], "expected_units": expected,
            "file_pairs": pairs, "v2_file_pairs": v2_pairs,
            "errors": len(errors), "complete": ok,
        })
        total_expected += expected; total_pairs += v2_pairs; total_errors += len(errors)

    summary = {
        "extractor_version": EXTRACTOR_VERSION,
        "sources": len(rows), "expected_units": total_expected,
        "v2_file_pairs": total_pairs, "errors": total_errors,
        "complete": all(r["complete"] for r in rows), "reports": rows,
    }
    out = ROOT / "history/source_corpus/PHASE1_INGESTION_SUMMARY.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["complete"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
