#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "history/source_registry/phase1_sources.yaml"
CANONICAL_BLOCK = re.compile(r"\[(?P<cid>CN-[A-Z]+-\d{4}-V[^\]]+-P\d{4})\]\n(?P<text>.*?)(?=\n\n\[CN-|\Z)", re.S)


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def flatten_cues(config: dict) -> tuple[dict[str, list[str]], list[str], list[str]]:
    groups = {k: list(v or []) for k, v in (config.get("lexical_cues") or {}).items()}
    boosts = list(config.get("phrase_boosts") or [])
    limits = list(config.get("negative_or_limit_cues") or [])
    return groups, boosts, limits


def score_text(text: str, groups: dict[str, list[str]], boosts: list[str], limits: list[str]) -> dict:
    matched: list[str] = []
    matched_groups: list[str] = []
    score = 0.0

    for group, cues in groups.items():
        group_hits = []
        for cue in cues:
            if cue and cue in text:
                group_hits.append(cue)
                score += min(text.count(cue), 3) * 1.0
        if group_hits:
            matched_groups.append(group)
            matched.extend(group_hits)

    for phrase in boosts:
        if phrase and phrase in text:
            matched.append(phrase)
            score += 3.0

    limit_hits = [cue for cue in limits if cue and cue in text]
    if limit_hits:
        matched.extend(limit_hits)
        score += min(len(limit_hits), 3) * 0.75

    # Diversity of cue groups matters more than raw repetition of one common character.
    score += max(0, len(set(matched_groups)) - 1) * 1.5

    return {
        "score": round(score, 3),
        "matched_cues": sorted(set(matched), key=lambda x: (len(x), x)),
        "cue_groups": sorted(set(matched_groups)),
        "has_limit_or_failure_signal": bool(limit_hits),
    }


def parse_blocks(path: Path) -> list[tuple[str, str]]:
    body = path.read_text(encoding="utf-8")
    return [(m.group("cid"), m.group("text").strip()) for m in CANONICAL_BLOCK.finditer(body)]


def context_slice(blocks: list[tuple[str, str]], idx: int, window: int) -> tuple[list[str], str]:
    lo = max(0, idx - window)
    hi = min(len(blocks), idx + window + 1)
    selected = blocks[lo:hi]
    ids = [cid for cid, _ in selected]
    text = "\n\n".join(f"[{cid}]\n{txt}" for cid, txt in selected)
    return ids, text


def retrieve(problem_id: str) -> dict:
    problem_path = ROOT / f"knowledge/problems/{problem_id}.yaml"
    cue_path = ROOT / f"knowledge/problems/{problem_id}.retrieval.yaml"
    if not problem_path.exists() or not cue_path.exists():
        raise SystemExit(f"missing problem or retrieval config for {problem_id}")

    problem = load_yaml(problem_path)
    cue_config = load_yaml(cue_path)
    manifest = load_yaml(MANIFEST)
    groups, boosts, limits = flatten_cues(cue_config)
    window = int(cue_config.get("context_window_paragraphs", 2))
    per_source_limit = int(cue_config.get("candidate_limit_per_source", 80))

    source_map = {s["source_id"]: s for s in manifest["sources"]}
    grouped: dict[str, list[dict]] = defaultdict(list)

    for source_id, source in source_map.items():
        base = ROOT / "history/source_corpus/china" / source["dynasty_group"] / source["corpus_key"] / "text"
        if not base.exists():
            continue
        for text_path in sorted(base.glob("*.txt")):
            blocks = parse_blocks(text_path)
            for idx, (cid, text) in enumerate(blocks):
                result = score_text(text, groups, boosts, limits)
                if result["score"] <= 0:
                    continue
                context_ids, context_text = context_slice(blocks, idx, window)
                grouped[source_id].append({
                    "source_id": source_id,
                    "source_title": source["title"],
                    "file": str(text_path.relative_to(ROOT)),
                    "anchor_canonical_id": cid,
                    "context_canonical_ids": context_ids,
                    "text": context_text,
                    "matched_cues": result["matched_cues"],
                    "cue_groups": result["cue_groups"],
                    "lexical_score": result["score"],
                    "has_limit_or_failure_signal": result["has_limit_or_failure_signal"],
                    "review_status": "unreviewed",
                    "review_note": None,
                })

    candidates: list[dict] = []
    for source_id in [s["source_id"] for dynasty in manifest["order"] for s in manifest["sources"] if s["dynasty_group"] == dynasty]:
        rows = grouped.get(source_id, [])
        rows.sort(key=lambda r: (-r["lexical_score"], r["anchor_canonical_id"]))
        # Keep at least some constraint/failure evidence even if it ranks slightly lower.
        top = rows[:per_source_limit]
        if rows:
            limit_rows = [r for r in rows if r["has_limit_or_failure_signal"]][: max(5, per_source_limit // 8)]
            seen = {r["anchor_canonical_id"] for r in top}
            for row in limit_rows:
                if row["anchor_canonical_id"] not in seen:
                    top.append(row)
                    seen.add(row["anchor_canonical_id"])
        top.sort(key=lambda r: (-r["lexical_score"], r["anchor_canonical_id"]))
        for row in top:
            row["candidate_id"] = f"CE-{problem_id.removeprefix('Q-')}-{len(candidates)+1:04d}"
            candidates.append(row)

    return {
        "problem_id": problem_id,
        "raw_question": problem.get("raw_question"),
        "retrieval_version": "lexical-bootstrap-v1",
        "generated_from": [
            str(problem_path.relative_to(ROOT)),
            str(cue_path.relative_to(ROOT)),
            str(MANIFEST.relative_to(ROOT)),
        ],
        "corpus_scope": [s["source_id"] for s in manifest["sources"]],
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--problem-id", default="Q-FATE-AGENCY-001")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    result = retrieve(args.problem_id)
    output = Path(args.output) if args.output else ROOT / f"knowledge/evidence/{args.problem_id}.candidates.yaml"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(result, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")
    print(json.dumps({
        "problem_id": result["problem_id"],
        "retrieval_version": result["retrieval_version"],
        "candidate_count": result["candidate_count"],
        "output": str(output.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
