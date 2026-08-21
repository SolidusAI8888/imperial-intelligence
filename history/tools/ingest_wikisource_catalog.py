#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "history/source_registry/phase3_catalog_sources.yaml"
EXTRACTOR_VERSION = 3


def _phase1_module():
    import ingest_wikisource_phase1 as phase1
    return phase1


def api(params: dict) -> dict:
    return _phase1_module().api(params)


def fetch_rendered(title: str):
    return _phase1_module().fetch_rendered(title)


def clean_original_blocks(html: str) -> list[str]:
    return _phase1_module().clean_original_blocks(html)


def load_manifest(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
        raise ValueError(f"invalid catalog manifest: {path}")
    ids = [row.get("source_id") for row in data["sources"]]
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("catalog sources require unique stable source_id values")
    return data


def page_links(title: str) -> list[str]:
    found: list[str] = []
    cont = None
    while True:
        params = {"action": "query", "prop": "links", "titles": title, "pllimit": "max"}
        if cont:
            params["plcontinue"] = cont
        data = api(params)
        pages = data.get("query", {}).get("pages", [])
        if not pages or pages[0].get("missing"):
            return []
        found.extend(link["title"] for link in pages[0].get("links", []))
        nxt = data.get("continue")
        if not nxt:
            break
        cont = nxt.get("plcontinue")
    return list(dict.fromkeys(found))


def _volume_number(title: str) -> tuple[int, str] | None:
    m = re.search(r"/卷0*(\d+)([^/]*)$", title)
    if not m:
        return None
    return int(m.group(1)), m.group(2)


def discover_child_pages(child_title: str) -> list[str]:
    """Discover direct and one-level-deep volume pages beneath one catalog child work."""
    candidates: set[str] = set()
    first = page_links(child_title)
    for title in first:
        if _volume_number(title):
            candidates.add(title)
    for intermediate in first:
        if intermediate == child_title or _volume_number(intermediate):
            continue
        if not (intermediate.startswith(child_title + "/") or "實錄" in intermediate or "政紀" in intermediate):
            continue
        try:
            for title in page_links(intermediate):
                if _volume_number(title):
                    candidates.add(title)
        except Exception:
            continue
    return sorted(candidates, key=lambda t: (_volume_number(t)[0], _volume_number(t)[1], t))


def safe_slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return value or "child"


def archive_catalog_source(source: dict) -> dict:
    source_id = source["source_id"]
    base = ROOT / "history" / "source_corpus" / "china" / source["dynasty_group"] / source["corpus_key"]
    text_dir = base / "text"
    prov_dir = base / "provenance"
    text_dir.mkdir(parents=True, exist_ok=True)
    prov_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "source_id": source_id,
        "title": source["title"],
        "extractor_version": EXTRACTOR_VERSION,
        "acquisition_strategy": source["acquisition_strategy"],
        "host_completeness": source.get("host_completeness"),
        "historical_extent_note": source.get("historical_extent_note"),
        "child_catalog": [],
        "pages": [],
        "skipped_current": [],
        "errors": [],
        "source_complete": False,
        "archive_scope_status": "partial_host_archive",
    }

    for child_index, child in enumerate(source.get("child_works") or [], 1):
        child_title = child["title"]
        host_title = child.get("host_title", child_title)
        child_key = safe_slug(child["key"])
        try:
            titles = discover_child_pages(host_title)
        except Exception as exc:
            report["errors"].append({"child": child_title, "error_type": type(exc).__name__, "error": str(exc)})
            titles = []
        report["child_catalog"].append({
            "key": child["key"],
            "title": child_title,
            "host_title": host_title,
            "discovered_pages": len(titles),
        })

        for idx, title in enumerate(titles, 1):
            volume = _volume_number(title)
            if not volume:
                continue
            n, suffix = volume
            suffix_hash = "" if not suffix else "_" + hashlib.sha1(suffix.encode()).hexdigest()[:6]
            stem = f"{child_index:02d}_{child_key}_{n:04d}{suffix_hash}"
            text_path = text_dir / f"{stem}.txt"
            prov_path = prov_dir / f"{stem}.yaml"
            if text_path.exists() and prov_path.exists():
                report["skipped_current"].append({"page": title, "file": text_path.name})
                continue
            try:
                html, revid, displaytitle = fetch_rendered(title)
                blocks = clean_original_blocks(html)
                if not blocks:
                    raise ValueError("no archival source blocks extracted")
                lines = []
                for pnum, block in enumerate(blocks, 1):
                    cid = f"{source_id}-{child_index:02d}-V{n:04d}-P{pnum:04d}"
                    lines.append(f"[{cid}]\n{block}")
                body = "\n\n".join(lines) + "\n"
                text_path.write_text(body, encoding="utf-8")
                digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
                prov = {
                    "source_id": source_id,
                    "catalog_child_key": child["key"],
                    "catalog_child_title": child_title,
                    "volume": n,
                    "volume_suffix": suffix or None,
                    "wikisource_page": title,
                    "revision_id": revid,
                    "permanent_url": f"https://zh.wikisource.org/w/index.php?title={quote(title)}&oldid={revid}",
                    "display_title": displaytitle,
                    "block_count": len(blocks),
                    "sha256": digest,
                    "extractor_version": EXTRACTOR_VERSION,
                    "host_completeness": source.get("host_completeness"),
                    "source_complete_claim": False,
                    "rights": "Ancient work public domain; Wikisource editorial contributions reused under CC BY-SA 4.0; attribution retained in provenance.",
                }
                prov_path.write_text(yaml.safe_dump(prov, allow_unicode=True, sort_keys=False), encoding="utf-8")
                report["pages"].append({"page": title, "file": text_path.name, "blocks": len(blocks), "revid": revid, "sha256": digest})
            except Exception as exc:
                report["errors"].append({"page": title, "error_type": type(exc).__name__, "error": str(exc)})
            print(f"[{source_id}] {child_title} {idx}/{len(titles)} {title}", flush=True)
            time.sleep(0.35)

    report["archived_file_pairs"] = sum(1 for p in text_dir.glob("*.txt") if (prov_dir / f"{p.stem}.yaml").exists())
    report["discovered_page_count"] = sum(item["discovered_pages"] for item in report["child_catalog"])
    if not report["discovered_page_count"]:
        report["errors"].append({
            "source": source["title"],
            "error_type": "CatalogDiscoveryError",
            "error": "no catalog child pages discovered for a registered catalog source",
        })
    report["archive_scope_complete"] = (
        not report["errors"] and report["discovered_page_count"] > 0 and report["archived_file_pairs"] >= report["discovered_page_count"]
    )
    report["source_complete"] = bool(report["archive_scope_complete"] and source.get("host_completeness") == "verified_complete")
    report["archive_scope_status"] = "host_catalog_archived" if report["archive_scope_complete"] else "partial_host_archive"
    (base / "ingestion_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--source-id")
    parser.add_argument("--catalog-only", action="store_true")
    args = parser.parse_args()
    manifest_path = args.manifest if args.manifest.is_absolute() else (ROOT / args.manifest).resolve()
    manifest = load_manifest(manifest_path)
    sources = manifest["sources"]
    if args.source_id:
        sources = [row for row in sources if row["source_id"] == args.source_id]
        if not sources:
            raise SystemExit(f"unknown source id: {args.source_id}")
    if args.catalog_only:
        out = []
        for source in sources:
            children = []
            for child in source.get("child_works") or []:
                host_title = child.get("host_title", child["title"])
                children.append({
                    "key": child["key"],
                    "title": child["title"],
                    "host_title": host_title,
                    "pages": discover_child_pages(host_title),
                })
            out.append({"source_id": source["source_id"], "children": children})
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    reports = [archive_catalog_source(source) for source in sources]
    print(json.dumps({
        "sources_processed": len(reports),
        "discovered_pages": sum(r["discovered_page_count"] for r in reports),
        "archived_file_pairs": sum(r["archived_file_pairs"] for r in reports),
        "errors": sum(len(r["errors"]) for r in reports),
        "source_complete_claims": sum(1 for r in reports if r["source_complete"]),
    }, ensure_ascii=False, indent=2))
    if any(r["errors"] for r in reports):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
