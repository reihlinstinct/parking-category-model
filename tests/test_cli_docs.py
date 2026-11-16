"""Man pages and --help for every shipped CLI module command (issue #26).

- --help smoke test for every real shipped entrypoint.
- Drift test: committed man/man1/* pages match tools/build_man_pages.py output.
- Spec-vs-code: every spec option appears in the module's --help and vice versa.

Stdlib only, offline; entry modules import heavy deps lazily inside main(), so
--help works without TensorFlow or numpy.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import build_man_pages  # noqa: E402

from parking_category_model import cli_spec  # noqa: E402


def run_help(module: str) -> str:
    proc = subprocess.run(
        [sys.executable, "-m", module, "--help"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"},
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_help_smoke_every_shipped_command():
    for cmd in cli_spec.COMMANDS.values():
        out = run_help(cmd.module)
        flat = " ".join(out.split())  # argparse wraps help text
        assert cmd.summary in flat
        for opt in cmd.options:
            assert opt.flag in flat
            assert " ".join(opt.help.split()) in flat


def test_help_exposes_no_unspecced_flags():
    for cmd in cli_spec.COMMANDS.values():
        out = run_help(cmd.module)
        import re

        flags = set(re.findall(r"--[a-z][a-z0-9-]*", out)) - {"--help"}
        assert flags == {o.flag for o in cmd.options}


def test_man_pages_up_to_date():
    assert build_man_pages.main(["--check"]) == 0


def test_man_pages_cover_exactly_the_shipped_commands():
    committed = {p.name for p in (ROOT / "man" / "man1").glob("*.1")}
    expected = {f"{cli_spec.PROGRAM}-{c.name}.1" for c in cli_spec.COMMANDS.values()}
    assert committed == expected
