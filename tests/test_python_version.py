"""Runtime Python-version guard (#33)."""

import parking_category_model as pkg


def test_python_version_guard_accepts_current():
    pkg._check_python_version()  # no SystemExit on a supported interpreter


def test_python_version_guard_rejects_old(monkeypatch):
    monkeypatch.setattr(pkg._sys, "version_info", (3, 10, 9))
    try:
        pkg._check_python_version()
    except SystemExit as exc:
        assert "requires Python 3.11+" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("guard did not exit on Python 3.10")
