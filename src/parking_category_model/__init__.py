"""Photo-to-106-category classifier: code only, no data and no weights."""

import sys as _sys

__version__ = "0.1.0"

MIN_PYTHON = (3, 11)


def _check_python_version() -> None:
    if _sys.version_info < MIN_PYTHON:
        raise SystemExit(
            "parking-category-model requires Python "
            f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ "
            "(you are running " + ".".join(str(v) for v in _sys.version_info[:3]) + "). "
            "Python 3.10 is end-of-life; please use a newer interpreter."
        )


_check_python_version()
