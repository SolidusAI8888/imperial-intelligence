#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests
import yaml
from bs4 import BeautifulSoup

API = "https://zh.wikisource.org/w/api.php"
ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "history/source_registry/phase1_sources.yaml"
UA = "ImperialIntelligenceHistoricalCorpus/1.0 (research archival ingestion; GitHub project)"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA})
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def api(params: dict) -> dict:
    """Call MediaWiki API with rate-limit-aware retry.

    GitHub-hosted runners can share public egress IPs and Wikisource may throttle them.
    A 429 must therefore pause and retry the same page, not be counted as a missing page.
    """
    params = {**params, "format": "json", "formatversion": 2, "maxlag": 5}
    last_error: Exception | None = None
    for attempt in range(12):
        try:
            r = SESSION.get(API, params=params, timeout=90)
            if r.status_code in RETRYABLE_STATUS:
                retry_after = r.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait = max(5, int(retry_after))
                elif r.status_code == 429:
                    wait = min(900, 60 * (2 ** min(attempt, 4)))
                else:
                    wait = min(180, 5 * (2 ** min(attempt, 5)))
                print(f"API throttled/status={r.status_code}; waiting {wait}s before retry {attempt + 1}/12")
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                code = data["error"].get("code", "")
                if code == "maxlag":
                    wait = min(120, 10 * (attempt + 1))
                    print(f"MediaWiki maxlag; waiting {wait}s")
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"MediaWiki API error: {data['error']}")
            return data
        except Exception as exc:
            last_error = exc
            if attempt == 11:
                break
            wait = min(120, 2 ** min(attempt, 6))
            print(f"API request error: {exc}; waiting {wait}s before retry {attempt + 1}/12")
            time.sleep(wait)
    raise RuntimeError(f"MediaWiki API request failed after retries: {last_error}")


def page_exists(title: str) -> bool:
    data = api({"action": "query", "titles": title})
    return not data["query"]["pages"][0].get("missing", False)


def discover_volume_titles(root_page: str, vmin: int, vmax: int) -> list[str]:
    """Prefer pages linked from the work index; fall back to common title formats."""
    found: set[str] = set()
    plcontinue = None
    while True:
        params = {"action": "query", "prop": "links", "titles": root_page, "pllimit": "max"}
        if plcontinue:
            params["plcontinue"] = plcontinue
        data = api(params)
        page = data["query"]["pages"][0]
        for link in page.get("links", []):
            title = link["title"]
            if not title.startswith(root_page + "/卷"):
                continue
            m = re.match(rf"^{re.escape(root_page)}/卷0*(\d+)(.*)$", title)
            if not m:
                continue
            n = int(m.group(1))
            if vmin <= n <= vmax:
                found.add(title)
        cont = data.get("continue")
        if not cont:
            break
        plcontinue = cont.get("plcontinue")

    by_num = {int(re.match(rf"^{re.escape(root_page)}/卷0*(\d+)", t).group(1)) for t in found}
    for n in range(vmin, vmax + 1):
        if n in by_num:
            continue
        candidates = [
            f"{root_page}/卷{n:03d}", f"{root_page}/卷{n:02d}", f"{root_page}/卷{n}",
            f"{root_page}/卷{n:03d}上", f"{root_page}/卷{n:03d}中", f"{root_page}/卷{n:03d}下",
        ]
        existing = [t for t in candidates if page_exists(t)]
        parts = [t for t in existing if t.endswith(("上", "中", "下"))]
        if parts:
            found.update(parts)
        elif existing:
            found.add(existing[0])
        time.sleep(0.15)

    def key(title: str):
        m = re.match(rf"^{re.escape(root_page)}/卷0*(\d+)(.*)$", title)
        suffix = m.group(2)
        rank = {"": 0, "上": 1, "中": 2, "下": 3}.get(suffix, 9)
        return int(m.group(1)), rank, suffix

    return sorted(found, key=key)


def fetch_rendered(title: str) -> tuple[str, int, str]:
    data = api({"action": "parse", "page": title, "prop": "text|revid|displaytitle", "disableeditsection": 1})
    p = data["parse"]
    return p["text"], int(p["revid"]), p.get("displaytitle", title)


def clean_original_paragraphs(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one(".mw-parser-output") or soup
    for sel in [
        "table", ".navbox", ".metadata", ".hatnote", ".sistersitebox", ".ambox", ".infobox",
        ".mw-editsection", "sup.reference", ".reference", ".references", "style", "script",
    ]:
        for node in root.select(sel):
            node.decompose()

    paragraphs: list[str] = []
    for node in root.find_all(["p", "dd"], recursive=True):
        if node.find_parent(["table", "ol", "ul"]):
            continue
        text = node.get_text("", strip=True)
        text = re.sub(r"\[\s*\d+\s*\]", "", text)
        text = re.sub(r"\s+", "", text)
        if not text:
            continue
        if any(x in text for x in ["維基百科條目：", "维基百科条目：", "本文的各章節標題都是為便利閱讀所添加", "本文的各章节标题都是为便利阅读所添加"]):
            continue
        paragraphs.append(text)
    return paragraphs


def suffix_code(title: str, root_page: str) -> tuple[int, str]:
    m = re.match(rf"^{re.escape(root_page)}/卷0*(\d+)(.*)$", title)
    n = int(m.group(1))
    suffix = m.group(2)
    code = {"": "", "上": "a", "中": "b", "下": "c"}.get(
        suffix, "x" + hashlib.sha1(suffix.encode()).hexdigest()[:4]
    )
    return n, code


def archive_source(src: dict) -> dict:
    source_id = src["source_id"]
    dynasty = src["dynasty_group"]
    root_page = src["root_page"]
    key = src["corpus_key"]
    base = ROOT / f"history/source_corpus/china/{dynasty}/{key}"
    text_dir = base / "text"
    prov_dir = base / "provenance"
    text_dir.mkdir(parents=True, exist_ok=True)
    prov_dir.mkdir(parents=True, exist_ok=True)

    titles = discover_volume_titles(root_page, int(src["volume_min"]), int(src["volume_max"]))
    report = {
        "source_id": source_id,
        "title": src["title"],
        "expected_range": [src["volume_min"], src["volume_max"]],
        "pages": [],
        "skipped_existing": [],
        "errors": [],
    }

    for idx, title in enumerate(titles, start=1):
        n, part = suffix_code(title, root_page)
        stem = f"{n:03d}{part}"
        text_path = text_dir / f"{stem}.txt"
        prov_path = prov_dir / f"{stem}.yaml"

        if text_path.exists() and prov_path.exists():
            report["skipped_existing"].append({"page": title, "file": f"{stem}.txt"})
            print(f"[{source_id}] {idx}/{len(titles)} SKIP existing {title}", flush=True)
            continue

        try:
            html, revid, displaytitle = fetch_rendered(title)
            paras = clean_original_paragraphs(html)
            if not paras:
                raise ValueError("no archival paragraphs extracted")
            lines = []
            for i, para in enumerate(paras, start=1):
                cid = f"{source_id}-V{n:03d}{part.upper()}-P{i:04d}"
                lines.append(f"[{cid}]\n{para}")
            body = "\n\n".join(lines) + "\n"
            text_path.write_text(body, encoding="utf-8")
            sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
            prov = {
                "source_id": source_id,
                "volume": n,
                "part": part or None,
                "wikisource_page": title,
                "revision_id": revid,
                "permanent_url": f"https://zh.wikisource.org/w/index.php?title={quote(title)}&oldid={revid}",
                "display_title": displaytitle,
                "paragraph_count": len(paras),
                "sha256": sha256,
                "rights": "Ancient work public domain; Wikisource editorial contributions reused under CC BY-SA 4.0; attribution retained in provenance.",
                "extraction": "Rendered Wikisource text; navigation, references, tables, and obvious editorial notices removed; paragraph order preserved.",
            }
            prov_path.write_text(
                yaml.safe_dump(prov, allow_unicode=True, sort_keys=False), encoding="utf-8"
            )
            report["pages"].append(
                {"page": title, "file": f"{stem}.txt", "paragraphs": len(paras), "revid": revid, "sha256": sha256}
            )
        except Exception as e:
            error = {"page": title, "error": str(e)}
            report["errors"].append(error)
            print(f"[{source_id}] ERROR {title}: {e}", flush=True)
        print(f"[{source_id}] {idx}/{len(titles)} {title}", flush=True)
        time.sleep(0.35)

    (base / "ingestion_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    all_reports = []
    for dynasty in manifest["order"]:
        for src in [s for s in manifest["sources"] if s["dynasty_group"] == dynasty]:
            all_reports.append(archive_source(src))
    summary = {
        "sources": len(all_reports),
        "archived_pages_this_run": sum(len(r["pages"]) for r in all_reports),
        "skipped_existing": sum(len(r["skipped_existing"]) for r in all_reports),
        "errors": sum(len(r["errors"]) for r in all_reports),
        "reports": [
            {
                "source_id": r["source_id"],
                "archived_this_run": len(r["pages"]),
                "skipped_existing": len(r["skipped_existing"]),
                "errors": len(r["errors"]),
            }
            for r in all_reports
        ],
    }
    out = ROOT / "history/source_corpus/PHASE1_INGESTION_SUMMARY.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if summary["errors"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
