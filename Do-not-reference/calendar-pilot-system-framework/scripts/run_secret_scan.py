#!/usr/bin/env python3
"""Small zero-dependency secret scan for CI evidence bundles."""
from __future__ import annotations

import argparse
import re
from pathlib import Path
import sys

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret)\s*[:=]\s*['\"]?[A-Za-z0-9_./~+=-]{12,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_./~+=-]{20,}"),
]
TEXT_SUFFIXES = {".json", ".jsonl", ".txt", ".md", ".log", ".yml", ".yaml"}


def scan_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    hits: list[str] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                hits.append(f"{path}:{idx}: potential secret matched {pattern.pattern}")
                break
    return hits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    args = parser.parse_args()
    root = Path(args.path)
    hits: list[str] = []
    paths = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
    for path in paths:
        if path.suffix.lower() in TEXT_SUFFIXES:
            hits.extend(scan_file(path))
    if hits:
        print("secret scan failed:")
        for hit in hits:
            print(hit)
        raise SystemExit(1)
    print(f"secret scan ok: {root}")


if __name__ == "__main__":
    main()
