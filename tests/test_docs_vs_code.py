"""Two-way doc-vs-code check for the CLI surface of the training modules.

Every flag a `python -m parking_category_model.*` entry module exposes must
appear in the docs, and every flag or module the docs present as CLI syntax
must exist in the code. Stdlib only, offline; modules are parsed as text so
no training dependency is needed.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src" / "parking_category_model"
DOC_FILES = [ROOT / "README.md"] + sorted((ROOT / "docs").rglob("*.md"))
ALLOWLIST = ROOT / ".github" / "docs-vs-code-allowlist.txt"

SPAN_RE = re.compile(r"```[^\n]*\n(.*?)```|`([^`\n]+)`", re.S)
FLAG_RE = re.compile(r"--[a-z][a-z0-9-]*")
MODULE_RE = re.compile(r"python3? -m (parking_category_model\.[a-z_]+)(?![\w.-])")


def _allowlist() -> dict[str, str]:
    out: dict[str, str] = {}
    if ALLOWLIST.is_file():
        for line in ALLOWLIST.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            token, _, reason = line.partition("#")
            token = token.strip()
            assert reason.strip(), f"allowlist entry without a reason: {line}"
            out[token] = reason.strip()
    return out


def cli_modules() -> dict[str, set[str]]:
    """{module: flags} for every package module that builds an ArgumentParser."""
    out: dict[str, set[str]] = {}
    for path in sorted(PKG.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "ArgumentParser" not in text:
            continue
        flags = set(re.findall(r'add_argument\(\s*["\'](--[a-z-]+)["\']', text))
        flags.discard("--help")
        out[path.stem] = flags
    return out


def doc_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in DOC_FILES)


def doc_spans(text: str):
    for m in SPAN_RE.finditer(text):
        yield m.group(1) if m.group(1) is not None else m.group(2)


def doc_flags(text: str) -> set[str]:
    """Flags the docs present as CLI syntax: backticked `--flag` anywhere, plus
    any `--flag` on a CLI command line (fenced or inline) after the invocation."""
    out = set(re.findall(r"`(--[a-z][a-z0-9-]*)`", text))
    for span in doc_spans(text):
        for m in MODULE_RE.finditer(span):
            rest = span[m.end():].split("\n", 1)[0]
            out.update(FLAG_RE.findall(rest))
    return out


def test_every_cli_token_is_documented():
    text = doc_text().casefold()
    allowed = _allowlist()
    missing = []
    for module, flags in cli_modules().items():
        if f"parking_category_model.{module}" not in text and module not in allowed:
            missing.append(module)
        missing.extend(f for f in sorted(flags) if f.casefold() not in text and f not in allowed)
    assert not missing, f"CLI tokens missing from docs: {missing}"


def test_every_documented_token_exists():
    modules = cli_modules()
    known_flags = {f.casefold() for flags in modules.values() for f in flags}
    allowed = {k.casefold() for k in _allowlist()}
    stale: set[str] = set()
    for doc in DOC_FILES:
        text = doc.read_text(encoding="utf-8")
        for token in doc_flags(text):
            if token.casefold() not in known_flags | allowed:
                stale.add(f"{doc.relative_to(ROOT)}: flag {token}")
        for token in MODULE_RE.findall(text):
            module = token.rsplit(".", 1)[1]
            if module not in modules and module not in _allowlist():
                stale.add(f"{doc.relative_to(ROOT)}: module {token}")
    assert not stale, f"documented CLI tokens missing from code: {sorted(stale)}"


def test_doc_flags_catches_fake_flag_in_fence():
    fence = (
        "```bash\n"
        "python -m parking_category_model.train --data-dir d --out m.keras --totally-fake-flag\n"
        "```\n"
    )
    found = doc_flags(fence)
    assert "--totally-fake-flag" in found
    assert "--data-dir" in found


def test_doc_flags_catches_fake_flag_inline():
    assert "--totally-fake-flag" in doc_flags(
        "`python -m parking_category_model.evaluate --model m.keras --totally-fake-flag`"
    )
