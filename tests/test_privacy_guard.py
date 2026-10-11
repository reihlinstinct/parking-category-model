import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "privacy_guard", Path(__file__).resolve().parents[1] / "tools" / "privacy_guard.py"
)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


def scan_with(tmp_path, name, content):
    target = tmp_path / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content if isinstance(content, bytes) else content.encode())
    return guard.scan(tmp_path)


def test_clean_repo(tmp_path):
    assert scan_with(tmp_path, "a.py", "print('hello')\n") == []


@pytest.mark.parametrize("name", ["x.jpg", "m.tflite", "w.keras", "d.csv"])
def test_forbidden_suffix(tmp_path, name):
    assert scan_with(tmp_path, name, "x")


def test_binary_with_innocent_name(tmp_path):
    assert scan_with(tmp_path, "notes.txt", b"\xff\xd8\xff\x00\x10JFIF")


def test_plate(tmp_path):
    digits = "".join(["12", "345", "67"])
    assert scan_with(tmp_path, "a.md", f"car {digits}")


def test_gps_pair(tmp_path):
    pair = ", ".join(["31.74562", "35.21983"])
    assert scan_with(tmp_path, "a.md", pair)


def test_email(tmp_path):
    assert scan_with(tmp_path, "a.md", "someone" + "@" + "example.com")


def test_hebrew_street(tmp_path):
    assert scan_with(tmp_path, "a.md", "\u05e8\u05d7\u05d5\u05d1 \u05d0\u05dc\u05d5\u05e0\u05d9")


def test_placeholder_street_allowed(tmp_path):
    assert scan_with(tmp_path, "a.md", "\u05e8\u05d7\u05d5\u05d1 {street}") == []


def test_municipal_url(tmp_path):
    assert scan_with(tmp_path, "a.md", "https://example." + "muni.il/x")


def test_real_repo_is_clean():
    assert guard.scan(Path(__file__).resolve().parents[1]) == []


def test_public_commit_and_signing_fingerprints_are_not_plates(tmp_path):
    (tmp_path / "workflow.yml").write_text("uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1\nfpr=D9AD033086DA866791E1616FFFEAA024C5F45CBA\n")
    assert guard.scan(tmp_path) == []


def test_fingerprint_exception_keeps_private_data_checks(tmp_path):
    (tmp_path / "workflow.yml").write_text("fpr=D9AD033086DA866791E1616FFFEAA024C5F45CBA\nplate=12345678\nmail=person@example.com\n")
    findings = guard.scan(tmp_path)
    assert any("licence plate" in x for x in findings)
    assert any("email address" in x for x in findings)
