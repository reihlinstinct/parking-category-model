#!/usr/bin/env python3
"""Fail if the repository contains images, model weights, plates, GPS, addresses or secrets.

Usage: python tools/privacy_guard.py [root]
Exit code 0 = clean, 1 = findings (printed, without echoing the matched text).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

FORBIDDEN_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".gif", ".bmp", ".tif", ".tiff",
    ".tflite", ".keras", ".h5", ".onnx", ".pt", ".pth", ".npz", ".npy", ".ckpt", ".pb",
    ".csv", ".sqlite", ".db", ".zip", ".tar", ".gz", ".pem", ".key",
}
# Files that must mention the patterns themselves.
CONTENT_ALLOWLIST = {"tools/privacy_guard.py", "tests/test_privacy_guard.py"}

CONTENT_RULES = {
    "possible licence plate (7-8 digits)": re.compile(r"(?<![\d.])\d{2,3}[- ]?\d{2,3}[- ]?\d{2,3}(?![\d.])"),
    "GPS coordinate pair": re.compile(r"-?\d{1,3}\.\d{4,}\s*,\s*-?\d{1,3}\.\d{4,}"),
    "EXIF GPS tag": re.compile(r"GPS(Latitude|Longitude)", re.IGNORECASE),
    "email address": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "municipal or government URL": re.compile(r"https?://[^\s\"')]*\.(muni|gov)\.il", re.IGNORECASE),
    "street address (Hebrew street word + literal name)": re.compile(r"(?:רחוב|רח')\s+[^\s{]"),
    "private key or token": re.compile(
        r"BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}"
    ),
}


def tracked_files(root: Path) -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            check=True, capture_output=True,
        ).stdout
        names = [n for n in out.decode("utf-8").split("\0") if n]
    except (subprocess.CalledProcessError, FileNotFoundError):
        skip = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".venv"}
        names = [
            str(p.relative_to(root))
            for p in root.rglob("*")
            if p.is_file() and not skip & set(p.parts) and not any(x.endswith(".egg-info") for x in p.parts)
        ]
    return [root / n for n in names if (root / n).is_file()]


def scan(root: Path) -> list[str]:
    findings: list[str] = []
    for path in tracked_files(root):
        rel = path.relative_to(root).as_posix()
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append(f"{rel}: forbidden file type {path.suffix.lower()}")
            continue
        data = path.read_bytes()
        if b"\0" in data:
            findings.append(f"{rel}: binary file")
            continue
        if rel in CONTENT_ALLOWLIST:
            continue
        text = data.decode("utf-8", errors="replace")
        for label, pattern in CONTENT_RULES.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{rel}:{line}: {label}")
    return findings


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    findings = scan(root)
    for finding in findings:
        print(finding)
    if findings:
        print(f"privacy guard: {len(findings)} finding(s)", file=sys.stderr)
        return 1
    print("privacy guard: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
