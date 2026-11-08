"""Offline tests for scripts/check_install_pins.py (#40). No network."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).absolute().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_install_pins", ROOT / "scripts" / "check_install_pins.py"
)
pins = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pins  # dataclasses look the module up
SPEC.loader.exec_module(pins)

HASHED = "pip install --require-hashes -r requirements/dev.txt"
PROJECT = "pip install --no-deps --no-build-isolation -e ."


def rules(text: str, path: str = "README.md") -> list[str]:
    if path.endswith(".md") and "```" not in text:
        text = f"```bash\n{text}\n```\n"
    return [f.rule for f in pins.scan_text(path, text)]


# --- install commands -------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "pip install requests",
        "pip3 install requests",
        "pip3.13 install requests",
        "/opt/venv/bin/pip install requests",
        "python -m pip install requests",
        "python3.12 -m pip install requests",
        '"$PY" -m pip install requests',
    ],
)
def test_named_install_flagged(command):
    assert any("named" in r for r in rules(command))


@pytest.mark.parametrize(
    "command",
    [
        "python -m pip --disable-pip-version-check install requests",
        "pip -q install requests",
        "pip --retries 5 install requests",
        "pip --no-cache-dir --log /tmp/x install requests",
    ],
)
def test_global_options_do_not_hide_install(command):
    assert any("named" in r for r in rules(command))


def test_pinned_but_unhashed_named_install_flagged():
    assert rules("pip install numpy==2.4.6")


@pytest.mark.parametrize("command", ["pipx install ruff", "uv tool install ruff", "easy_install ruff"])
def test_tool_installers_flagged(command):
    assert any("not hash-locked" in r for r in rules(command))


def test_requirements_install_without_require_hashes_flagged():
    assert any("without --require-hashes" in r for r in rules("pip install -r requirements/dev.txt"))
    assert any("without --require-hashes" in r for r in rules("uv pip install -r requirements/core.txt"))


@pytest.mark.parametrize(
    "command",
    [
        HASHED,
        "pip install --require-hashes --requirement=requirements/core.txt",
        "pip install --require-hashes -rrequirements/build.txt -r ./requirements/dev.txt",
        "uv pip install --require-hashes -r requirements/dev.txt",
        PROJECT,
        "pip install --no-deps --no-build-isolation .",
        "pip install --no-deps --no-build-isolation /wheels/parking_category_model-0.1.0-py3-none-any.whl",
        "pip install --no-deps -r requirements/train.txt",
        "pip freeze",
        "pip --version",
        "uv pip compile --universal pyproject.toml -o requirements/core.txt",
    ],
)
def test_allowed_shapes(command):
    assert rules(command) == []


def test_unknown_requirements_file_flagged():
    assert any("not a maintained lock" in r for r in rules("pip install --require-hashes -r other.txt"))
    assert any(
        "not a maintained lock" in r
        for r in rules("pip install --require-hashes -c constraints.txt -r requirements/dev.txt")
    )


def test_pins_only_lock_needs_no_deps():
    assert any("without --no-deps" in r for r in rules("pip install -r requirements/train.txt"))


@pytest.mark.parametrize(
    "command",
    [
        'pip install -e ".[dev]"',
        "pip install .",
        "pip install --no-deps -e .",
        "pip install --no-build-isolation .",
        "pip install /wheels/parking_category_model-0.1.0-py3-none-any.whl",
    ],
)
def test_local_project_needs_no_deps_and_no_build_isolation(command):
    assert any("local project" in r for r in rules(command))


@pytest.mark.parametrize(
    "command",
    ["pip install git+https://example.invalid/x.git", "pip install --no-deps https://example.invalid/x.whl"],
)
def test_url_install_flagged(command):
    assert any("named" in r for r in rules(command))


@pytest.mark.parametrize("command", ["$PIP install requests", '"${PIP}" install -r requirements/dev.txt'])
def test_installer_behind_variable_flagged(command):
    assert any("variable" in r for r in rules(command))


@pytest.mark.parametrize(
    "command",
    [
        "sudo pip install requests",
        "env PIP_NO_CACHE_DIR=1 pip install requests",
        "echo ok && pip install requests",
        'bash -c "pip install requests"',
        "sh -c 'cd /src; python3 -m pip install requests'",
        f"{HASHED} && pip install requests",
    ],
)
def test_wrapped_and_chained_commands_flagged(command):
    assert rules(command)


def test_markdown_fence_continuation_and_inline_span():
    text = "```bash\npip install \\\n  requests\n```\n\nRun `pip install requests` first.\n"
    found = pins.scan_text("docs/x.md", text)
    assert [f.line for f in found] == [2, 6]


def test_markdown_prose_and_comments_not_commands():
    text = "Never pip install requests by name.\n\n```bash\n# pip install requests\n```\n"
    assert pins.scan_text("docs/x.md", text) == []


def test_dockerfile_run_lines():
    text = 'FROM python:3.12\nRUN pip install \\\n    requests\nRUN ["pip", "install", "ruff"]\nCOPY . /src\n'
    assert [f.line for f in pins.scan_text("Dockerfile", text)] == [2, 4]


def test_workflow_run_steps_and_blocks():
    text = (
        'jobs:\n  t:\n    steps:\n      - run: pip install -e ".[dev]"\n'
        "      - run: |\n          echo hi\n          pip install ruff\n      - uses: x/y@v1\n"
    )
    assert [f.line for f in pins.scan_text(".github/workflows/ci.yml", text)] == [4, 7]


def test_untracked_kinds_not_scanned():
    assert pins.scan_text("src/notes.txt", "pip install requests") == []


# --- locks ------------------------------------------------------------------


def test_real_repo_is_clean():
    violations, notes = pins.check(ROOT)
    assert violations == []
    assert len(notes) == len(pins.load_pending(ROOT)[0])


@pytest.fixture
def repo(tmp_path):
    shutil.copy(ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    shutil.copytree(ROOT / "requirements", tmp_path / "requirements")
    assert pins.check_locks(tmp_path) == []
    return tmp_path


def edit(path: Path, old: str, new: str, count: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, count), encoding="utf-8")


def rewrite_evidence(root: Path) -> None:
    (root / pins.EVIDENCE).write_text(json.dumps(pins.build_evidence(root)), encoding="utf-8")


def first_hash_line(path: Path) -> str:
    return next(line for line in path.read_text(encoding="utf-8").splitlines() if "--hash=sha256:" in line)


def test_unhashed_pin_flagged(repo):
    lock = repo / "requirements/core.txt"
    lines = lock.read_text(encoding="utf-8").splitlines()
    i = next(n for n, line in enumerate(lines) if line.startswith("pillow=="))
    j = i + 1
    while lines[j].lstrip().startswith("--hash"):
        j += 1
    lines[i:j] = ["pillow==13.0.0"]
    lock.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rewrite_evidence(repo)
    assert any("without a sha256 hash" in e for e in pins.check_locks(repo))


def test_range_pin_flagged(repo):
    edit(repo / "requirements/train.txt", "keras==", "keras>=")
    rewrite_evidence(repo)
    assert any("not an exact == pin" in e for e in pins.check_locks(repo))


def test_option_line_flagged(repo):
    lock = repo / "requirements/train.txt"
    lock.write_text(
        lock.read_text(encoding="utf-8") + "--index-url https://example.invalid/simple\n", encoding="utf-8"
    )
    rewrite_evidence(repo)
    assert any("option line" in e for e in pins.check_locks(repo))


def test_malformed_hash_flagged(repo):
    lock = repo / "requirements/build.txt"
    line = first_hash_line(lock)
    edit(lock, line, line.replace("sha256:", "md5:"))
    rewrite_evidence(repo)
    assert any("malformed hash" in e for e in pins.check_locks(repo))


def test_pins_only_lock_must_not_carry_hashes(repo):
    edit(repo / "requirements/train.txt", "keras==3.15.1", "keras==3.15.1 --hash=sha256:" + "0" * 64)
    rewrite_evidence(repo)
    assert any("pins-only lock carries hashes" in e for e in pins.check_locks(repo))


def test_lock_edited_without_evidence_flagged(repo):
    lock = repo / "requirements/dev.txt"
    line = first_hash_line(lock)
    edit(lock, line, line[:-3] + ("0" if line[-3] != "0" else "1") + line[-2:])
    assert any("lock changed without new evidence" in e for e in pins.check_locks(repo))


def test_floor_change_without_relock_flagged(repo):
    edit(repo / "pyproject.toml", '"numpy>=1.24"', '"numpy>=3"')
    errors = pins.check_locks(repo)
    assert any("outside '>=3'" in e for e in errors)
    assert any("inputs (pyproject floors" in e for e in errors)


def test_missing_evidence_file_flagged(repo):
    (repo / pins.EVIDENCE).unlink()
    assert any("missing or unreadable" in e for e in pins.check_locks(repo))


def test_header_without_command_flagged(repo):
    edit(repo / "requirements/dev.txt", "--extra dev", "--extra devx")
    rewrite_evidence(repo)
    assert any("header does not show" in e for e in pins.check_locks(repo))


def test_top_level_requirement_missing_from_lock_flagged(repo):
    lock = repo / "requirements/train.txt"
    lines = lock.read_text(encoding="utf-8").splitlines()
    i = lines.index("tensorflow==2.21.0")
    lock.write_text("\n".join(lines[:i] + lines[i + 2 :]) + "\n", encoding="utf-8")
    rewrite_evidence(repo)
    assert any("top-level requirement tensorflow is not pinned" in e for e in pins.check_locks(repo))


def test_build_in_drift_flagged(repo):
    (repo / "requirements/build.in").write_text("setuptools>=70\n", encoding="utf-8")
    rewrite_evidence(repo)
    assert any("differs from [build-system] requires" in e for e in pins.check_locks(repo))


def test_pin_disagreeing_with_core_flagged(repo):
    edit(repo / "requirements/train.txt", "pillow==13.0.0", "pillow==12.9.9")
    rewrite_evidence(repo)
    assert any("disagrees with requirements/core.txt" in e for e in pins.check_locks(repo))


def test_missing_lock_flagged(repo):
    (repo / "requirements/core.txt").unlink()
    assert any("maintained lock is missing" in e for e in pins.check_locks(repo))


def test_evidence_written_by_tool_matches_committed():
    committed = json.loads((ROOT / pins.EVIDENCE).read_text(encoding="utf-8"))
    assert committed == pins.build_evidence(ROOT)


# --- pending workflow lines -------------------------------------------------


def test_pending_allowlist_names_exactly_the_current_workflow_lines():
    entries, errors = pins.load_pending(ROOT)
    assert errors == []
    current = set()
    for wf in sorted((ROOT / ".github/workflows").glob("*.yml")):
        rel = wf.relative_to(ROOT).as_posix()
        current |= {(f.path, f.line, f.text) for f in pins.scan_text(rel, wf.read_text(encoding="utf-8"))}
    # Today: ci.yml lines 20 and 32. The workflow change empties `current`
    # and deletes the file in the same commit, so this stays exact both ways.
    assert {(e["path"], e["line"], e["command"]) for e in entries} == current
    if (ROOT / pins.PENDING).is_file():
        assert entries, f"nothing is pending; delete {pins.PENDING}"


def workflow_repo(tmp_path, entries):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / ".github/workflows/ci.yml").write_text(
        "steps:\n  - run: pip install ruff\n", encoding="utf-8"
    )
    (tmp_path / "requirements").mkdir()
    (tmp_path / pins.PENDING).write_text(json.dumps({"entries": entries}), encoding="utf-8")
    violations, notes = pins.check(tmp_path)
    return [v for v in violations if not v.startswith("requirements/") or pins.PENDING in v], notes


def test_listed_workflow_line_is_pending_not_violation(tmp_path):
    entry = {"path": ".github/workflows/ci.yml", "line": 2, "command": "pip install ruff"}
    violations, notes = workflow_repo(tmp_path, [entry])
    assert violations == []
    assert notes == [".github/workflows/ci.yml:2: pip install ruff"]


def test_unlisted_workflow_line_fails(tmp_path):
    violations, _ = workflow_repo(tmp_path, [])
    assert any(v.startswith(".github/workflows/ci.yml:2:") for v in violations)


def test_stale_pending_entry_fails(tmp_path):
    stale = {"path": ".github/workflows/ci.yml", "line": 9, "command": "pip install ruff"}
    violations, _ = workflow_repo(tmp_path, [stale])
    assert any("matches no violating line" in v for v in violations)


def test_pending_accepts_only_workflow_paths(tmp_path):
    (tmp_path / "README.md").write_text("```\npip install ruff\n```\n", encoding="utf-8")
    entry = {"path": "README.md", "line": 2, "command": "pip install ruff"}
    violations, _ = workflow_repo(tmp_path, [entry])
    assert any("only .github/workflows/ lines may be pending" in v for v in violations)
    assert any(v.startswith("README.md:2:") for v in violations)


def test_main_exit_codes(capsys):
    assert pins.main(["--root", str(ROOT)]) == 0
    assert "install pins OK (" in capsys.readouterr().out
