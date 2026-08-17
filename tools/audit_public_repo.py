#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    "history/source_corpus",
}
SENSITIVE_FILENAMES = {".env", "id_rsa", "id_ed25519"}
SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "generic_secret_assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|secret|password|access[_-]?token|auth[_-]?token)\s*[:=]\s*['\"]([^'\"]{12,})['\"]"
    ),
}
LOCAL_PATH_PATTERNS = [
    re.compile(r"/Users/[^/\s]+/"),
    re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\"),
]


def should_skip(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return any(rel == d or rel.startswith(d + "/") for d in SKIP_DIRS)


def main() -> None:
    findings: list[str] = []
    local_paths: list[str] = []

    for path in ROOT.rglob("*"):
        if not path.is_file() or should_skip(path):
            continue
        if path.name in SENSITIVE_FILENAMES or path.suffix.lower() in {".pem", ".p12", ".pfx"}:
            findings.append(f"sensitive filename tracked: {path.relative_to(ROOT)}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{name}: {path.relative_to(ROOT)}")
        for pattern in LOCAL_PATH_PATTERNS:
            if pattern.search(text):
                local_paths.append(str(path.relative_to(ROOT)))
                break

    print("Public repository current-tree audit")
    print(f"secret/sensitive findings: {len(findings)}")
    for item in findings:
        print(f"  - {item}")
    print(f"files containing local user paths: {len(local_paths)}")
    for item in local_paths[:50]:
        print(f"  - {item}")

    if findings:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
