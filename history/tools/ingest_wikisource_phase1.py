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

API = "https://zh.wikisource.org/w/api.php"
ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "history/source_registry/phase1_sources.yaml"
UA = "ImperialIntelligenceHistoricalCorpus/3.0 (research archival ingestion; GitHub project)"
EXTRACTOR_VERSION = 3
SESSION = None
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

EDITORIAL_MARKERS = (
    "姊妹计划:", "姊妹計畫:", "姊妹计划：", "姊妹計畫：",
    "维基百科", "維基百科", "文言維基", "文言维基",
    "数据项", "資料項", "数据项目", "資料項目",
    "此作品在全世界都属于公有领域", "此作品在全世界都屬於公有領域",
    "本文的各章节标题都是为便利阅读所添加", "本文的各章節標題都是為便利閱讀所添加",
)
ARROW_CHARS = ("◄", "►", "←", "→", "↤", "↦")
EDITORIAL_SELECTORS = [
    ".navbox", ".metadata", ".hatnote", ".sistersitebox", ".ambox", ".infobox",
    ".mw-editsection", "sup.reference", ".reference", ".references", "style", "script",
    "table.licenseContainer", "table.plainlinks", "table.mbox-small", ".ws-noexport",
    ".ws-header", ".ws-footer", "#headerContainer", "#footerContainer", ".mw-indicators",
    ".noprint", ".nomobile", ".plainlinks.navigation-not-searchable", ".sisterproject",
]

CN_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "兩": 2, "两": 2,
    "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}
CN_UNITS = {"十": 10, "百": 100, "千": 1000}
VOLUME_NUMBER_PATTERN = r"[0-9零〇一二兩两三四五六七八九十百千]+"


def _session():
    global SESSION
    if SESSION is None:
        import requests

        SESSION = requests.Session()
        SESSION.headers.update({"User-Agent": UA})
    return SESSION


def api(params: dict) -> dict:
    params = {**params, "format": "json", "formatversion": 2, "maxlag": 5}
    last_error: Exception | None = None
    for attempt in range(16):
        try:
            r = _session().get(API, params=params, timeout=120)
            if r.status_code in RETRYABLE_STATUS:
                retry_after = r.headers.get("Retry-After", "")
                if retry_after.isdigit():
                    wait = max(10, int(retry_after))
                elif r.status_code == 429:
                    wait = min(900, 45 * (2 ** min(attempt, 4)))
                else:
                    wait = min(240, 5 * (2 ** min(attempt, 6)))
                print(f"API status={r.status_code}; wait {wait}s ({attempt + 1}/16)", flush=True)
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                code = data["error"].get("code", "")
                if code in {"maxlag", "ratelimited"}:
                    wait = min(180, 10 * (attempt + 1))
                    print(f"MediaWiki {code}; wait {wait}s", flush=True)
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"MediaWiki API error: {data['error']}")
            return data
        except Exception as exc:
            last_error = exc
            if attempt == 15:
                break
            wait = min(180, 2 ** min(attempt, 7))
            print(f"API request error: {exc}; wait {wait}s ({attempt + 1}/16)", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"MediaWiki API request failed after retries: {last_error}")


def existing_titles(candidates: list[str]) -> set[str]:
    out: set[str] = set()
    for i in range(0, len(candidates), 40):
        batch = candidates[i:i + 40]
        data = api({"action": "query", "titles": "|".join(batch), "redirects": 1})
        for page in data["query"]["pages"]:
            if not page.get("missing", False):
                out.add(page["title"])
        time.sleep(0.15)
    return out


def parse_chinese_number(value: str) -> int:
    if value.isdigit():
        return int(value)
    total = 0
    digit = 0
    for char in value:
        if char in CN_DIGITS:
            digit = CN_DIGITS[char]
        elif char in CN_UNITS:
            total += (digit or 1) * CN_UNITS[char]
            digit = 0
        else:
            raise ValueError(f"unsupported Chinese numeral: {value}")
    return total + digit


def format_chinese_number(value: int) -> str:
    if value < 1 or value > 9999:
        raise ValueError("Chinese volume number must be between 1 and 9999")
    digits = "零一二三四五六七八九"
    units = ("", "十", "百", "千")
    result: list[str] = []
    pending_zero = False
    text = str(value)
    for index, char in enumerate(text):
        digit = int(char)
        position = len(text) - index - 1
        if digit == 0:
            if result and any(next_char != "0" for next_char in text[index + 1:]):
                pending_zero = True
            continue
        if pending_zero:
            result.append("零")
            pending_zero = False
        if not (digit == 1 and position == 1 and not result):
            result.append(digits[digit])
        result.append(units[position])
    return "".join(result)


def parse_volume_title(title: str, root_page: str) -> tuple[int, str] | None:
    match = re.match(
        rf"^{re.escape(root_page)}/卷(?P<number>{VOLUME_NUMBER_PATTERN})(?P<suffix>.*)$",
        title,
    )
    if not match:
        return None
    return parse_chinese_number(match.group("number")), match.group("suffix")


def discover_volume_titles(root_page: str, vmin: int, vmax: int) -> list[str]:
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
            volume = parse_volume_title(title, root_page)
            if volume and vmin <= volume[0] <= vmax:
                found.add(title)
        cont = data.get("continue")
        if not cont:
            break
        plcontinue = cont.get("plcontinue")

    by_num = {parse_volume_title(title, root_page)[0] for title in found}
    for n in range(vmin, vmax + 1):
        if n in by_num:
            continue
        nums = list(dict.fromkeys([f"{n:03d}", f"{n:02d}", str(n), format_chinese_number(n)]))
        candidates = [f"{root_page}/卷{num}{suffix}" for num in nums for suffix in ["", "上", "中", "下"]]
        existing = existing_titles(candidates)
        parts = [t for t in existing if t.endswith(("上", "中", "下"))]
        if parts:
            found.update(parts)
        elif existing:
            found.add(sorted(existing, key=len)[0])

    def key(title: str):
        number, suffix = parse_volume_title(title, root_page)
        return number, {"": 0, "上": 1, "中": 2, "下": 3}.get(suffix, 9), suffix

    return sorted(found, key=key)


def fetch_rendered(title: str) -> tuple[str, int, str]:
    data = api({"action": "parse", "page": title, "prop": "text|revid|displaytitle", "disableeditsection": 1})
    p = data["parse"]
    return p["text"], int(p["revid"]), p.get("displaytitle", title)


def normalize_text(text: str) -> str:
    text = re.sub(r"\[\s*\d+\s*\]", "", text)
    text = re.sub(r"\s+", "", text)
    return text.strip()


def is_editorial_text(text: str) -> bool:
    if not text:
        return True
    if any(marker in text for marker in EDITORIAL_MARKERS):
        return True
    if any(ch in text for ch in ARROW_CHARS):
        return True
    if re.fullmatch(r"[\W_]+", text, flags=re.UNICODE):
        return True
    if text in {"上一卷", "下一卷", "上一頁", "下一頁", "上一页", "下一页"}:
        return True
    return False


def clean_original_blocks(html: str) -> list[str]:
    """Extract source text while excluding Wikisource navigation/editorial chrome.

    V3 keeps historical table cells but rejects known Wikisource UI containers and
    obvious navigation/editorial strings such as sister-project links and arrows.
    """
    from bs4 import BeautifulSoup, Tag

    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one(".mw-parser-output") or soup

    for sel in EDITORIAL_SELECTORS:
        for node in root.select(sel):
            node.decompose()

    tags = {"p", "dd", "li", "blockquote", "th", "td"}
    blocks: list[str] = []
    for node in root.find_all(list(tags), recursive=True):
        if not isinstance(node, Tag):
            continue
        if any(getattr(parent, "name", None) in tags for parent in node.parents if parent is not root):
            continue

        editorial_ancestor = False
        for parent in node.parents:
            if parent is root:
                break
            classes = set(parent.get("class", [])) if isinstance(parent, Tag) else set()
            pid = parent.get("id") if isinstance(parent, Tag) else None
            if ({"ws-noexport", "noprint", "navbox", "metadata", "sistersitebox", "hatnote"} & classes
                    or pid in {"headerContainer", "footerContainer"}):
                editorial_ancestor = True
                break
        if editorial_ancestor:
            continue

        text = normalize_text(node.get_text("", strip=True))
        if is_editorial_text(text):
            continue
        blocks.append(text)

    if blocks:
        return blocks

    for node in root.find_all("div", recursive=True):
        if node.find(["p", "dd", "li", "th", "td", "blockquote"]):
            continue
        text = normalize_text(node.get_text("", strip=True))
        if len(text) >= 20 and not is_editorial_text(text):
            blocks.append(text)
    return blocks


def suffix_code(title: str, root_page: str) -> tuple[int, str]:
    volume = parse_volume_title(title, root_page)
    if not volume:
        raise ValueError(f"unrecognized volume title: {title}")
    n, suffix = volume
    code = {"": "", "上": "a", "中": "b", "下": "c", "a": "a", "b": "b", "c": "c"}.get(
        suffix, "x" + hashlib.sha1(suffix.encode()).hexdigest()[:4]
    )
    return n, code


def is_current_complete(text_path: Path, prov_path: Path) -> bool:
    if not (text_path.exists() and prov_path.exists()):
        return False
    try:
        prov = yaml.safe_load(prov_path.read_text(encoding="utf-8")) or {}
        return int(prov.get("extractor_version", 0)) >= EXTRACTOR_VERSION
    except Exception:
        return False


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
        "extractor_version": EXTRACTOR_VERSION,
        "expected_titles": titles,
        "pages": [],
        "skipped_current": [],
        "errors": [],
    }
    if not titles:
        report["errors"].append({
            "source": root_page,
            "error_type": "VolumeDiscoveryError",
            "error": "no volume pages discovered for a registered numbered source",
        })

    for idx, title in enumerate(titles, 1):
        n, part = suffix_code(title, root_page)
        stem = f"{n:03d}{part}"
        text_path = text_dir / f"{stem}.txt"
        prov_path = prov_dir / f"{stem}.yaml"

        if is_current_complete(text_path, prov_path):
            report["skipped_current"].append({"page": title, "file": f"{stem}.txt"})
            print(f"[{source_id}] {idx}/{len(titles)} SKIP v{EXTRACTOR_VERSION} {title}", flush=True)
            continue

        try:
            html, revid, displaytitle = fetch_rendered(title)
            blocks = clean_original_blocks(html)
            if not blocks:
                raise ValueError("no archival source blocks extracted")

            lines = []
            for i, block in enumerate(blocks, 1):
                cid = f"{source_id}-V{n:03d}{part.upper()}-P{i:04d}"
                lines.append(f"[{cid}]\n{block}")
            body = "\n\n".join(lines) + "\n"

            contamination = [m for m in EDITORIAL_MARKERS if m in body]
            if any(ch in body for ch in ARROW_CHARS):
                contamination.append("navigation_arrow")
            if contamination:
                raise ValueError(f"editorial contamination detected: {sorted(set(contamination))}")

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
                "block_count": len(blocks),
                "sha256": sha256,
                "extractor_version": EXTRACTOR_VERSION,
                "rights": "Ancient work public domain; Wikisource editorial contributions reused under CC BY-SA 4.0; attribution retained in provenance.",
                "extraction": "Rendered Wikisource source text; Wikisource navigation/editorial chrome removed; paragraph/list/blockquote and historical table-cell text preserved in document order.",
            }
            prov_path.write_text(yaml.safe_dump(prov, allow_unicode=True, sort_keys=False), encoding="utf-8")
            report["pages"].append({"page": title, "file": f"{stem}.txt", "blocks": len(blocks), "revid": revid, "sha256": sha256})
        except Exception as exc:
            report["errors"].append({"page": title, "error_type": type(exc).__name__, "error": str(exc)})
            print(f"[{source_id}] ERROR {title}: {type(exc).__name__}: {exc}", flush=True)

        print(f"[{source_id}] {idx}/{len(titles)} {title}", flush=True)
        time.sleep(0.45)

    report["archived_file_pairs"] = sum(1 for p in text_dir.glob("*.txt") if (prov_dir / (p.stem + ".yaml")).exists())
    (base / "ingestion_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", help="Ingest one registered source only")
    args = parser.parse_args()

    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    sources = manifest["sources"]
    if args.source_id:
        sources = [s for s in sources if s["source_id"] == args.source_id]
        if not sources:
            raise SystemExit(f"unknown source id: {args.source_id}")
    else:
        ordered = []
        for dynasty in manifest["order"]:
            ordered.extend([s for s in sources if s["dynasty_group"] == dynasty])
        sources = ordered

    reports = [archive_source(src) for src in sources]
    failed = sum(len(r["errors"]) for r in reports)
    print(json.dumps({
        "extractor_version": EXTRACTOR_VERSION,
        "sources_processed": len(reports),
        "archived_or_refreshed": sum(len(r["pages"]) for r in reports),
        "skipped_current": sum(len(r["skipped_current"]) for r in reports),
        "errors": failed,
    }, ensure_ascii=False, indent=2), flush=True)

    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
