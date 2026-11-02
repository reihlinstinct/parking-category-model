"""Photo-to-106-category classifier: code only, no data and no weights."""

import sys as _sys

__version__ = "0.1.0"

MIN_PYTHON = (3, 11)


def _check_python_version() -> None:
    if _sys.version_info < MIN_PYTHON:
        raise SystemExit(
            "parking-category-model requires Python "
            f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ "
            "(you are running "
            f"{_sys.version_info.major}.{_sys.version_info.minor}.{_sys.version_info.micro}). "
            "Python 3.10 is end-of-life; please use a newer interpreter."
        )


_check_python_version()
