"""Enforce the repository layout contract in .repo-layout.yml.

Reads .repo-layout.yml (JSON syntax, which is also valid YAML) and the
tracked file list, then fails on:
  - a missing required root file or directory (community standards);
  - a tracked top-level directory not listed in the contract;
  - a root file matching a deny pattern or no allow pattern;
  - a file inside a listed directory matching none of its allow patterns.

Standard library only; no network. Usage:
  python3 tools/check_repo_layout.py [--root DIR]
Exit 0 when the layout conforms, 1 with one line per violation otherwise.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def load_contract(root: Path) -> dict[str, Any]:
    """Read and minimally validate the layout contract."""
    contract_path = root / ".repo-layout.yml"
    if not contract_path.is_file():
        raise SystemExit(f"missing layout contract: {contract_path}")
    contract: dict[str, Any] = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("version") != 1:
        raise SystemExit("unsupported .repo-layout.yml version")
    return contract


def tracked_files(root: Path) -> list[str]:
    """Return the repository's tracked file paths."""
    cmd = ["git", "ls-files"]
    out = subprocess.run(cmd, cwd=root, check=True, capture_output=True, text=True)
    return [line for line in out.stdout.splitlines() if line]


def check(root: Path) -> list[str]:
    """Return one line per layout violation, empty when the tree conforms."""
    contract = load_contract(root)
    violations: list[str] = []

    for required in contract["required"]:
        if required.endswith("/"):
            if not (root / required.rstrip("/")).is_dir():
                violations.append(f"required directory missing: {required}")
        elif not (root / required).is_file():
            violations.append(f"required file missing: {required}")

    files = tracked_files(root)
    dirs = contract["directories"]
    root_rules = contract["root"]
    deny_patterns = root_rules.get("deny", [])

    for path in files:
        parts = path.split("/")
        if len(parts) == 1:
            name = parts[0]
            if any(fnmatch.fnmatchcase(name, pat) for pat in deny_patterns):
                violations.append(f"denied at repository root: {path}")
            elif not any(fnmatch.fnmatchcase(name, pat) for pat in root_rules["allow"]):
                violations.append(f"not allowed at repository root: {path}")
            continue
        top = parts[0]
        if top not in dirs:
            violations.append(f"unlisted top-level directory: {top}/ (via {path})")
            continue
        name = parts[-1]
        if not any(fnmatch.fnmatchcase(name, pat) for pat in dirs[top]["allow"]):
            violations.append(f"type not allowed in {top}/: {path}")
    return violations


def main() -> int:
    """Run the layout check; print violations and return the exit code."""
    summary = (__doc__ or "").splitlines()[0]
    parser = argparse.ArgumentParser(description=summary)
    parser.add_argument("--root", default=".", help="repository root (default: cwd)")
    args = parser.parse_args()
    violations = check(Path(args.root).resolve())
    out = sys.stdout
    for violation in violations:
        out.write(f"layout violation: {violation}\n")
    if violations:
        count = len(violations)
        msg = f"{count} layout violation(s); see .repo-layout.yml and CONTRIBUTING.md"
        out.write(msg + "\n")
        return 1
    out.write("layout OK\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
