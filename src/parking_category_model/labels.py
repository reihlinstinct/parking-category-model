"""Load and validate the class table (class id -> 106 code, Hebrew name, text template)."""

from __future__ import annotations

import json
import string
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

ALLOWED_PLACEHOLDERS = frozenset({"street", "house_number", "time", "plate"})
CODE_STATUSES = frozenset({"verified", "fallback", "unverified"})


@dataclass(frozen=True)
class LabelClass:
    id: str
    code_106: int | None
    code_status: str
    name_he: str
    text_template_he: str

    def render(self, **fields: str) -> str:
        """Fill the Hebrew text template. All placeholders must be supplied."""
        return self.text_template_he.format(**fields)


class LabelError(ValueError):
    """Raised when labels.json is malformed."""


def _placeholders(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def parse(raw: dict) -> list[LabelClass]:
    if raw.get("schema_version") != 1:
        raise LabelError("unsupported schema_version")
    classes: list[LabelClass] = []
    seen: set[str] = set()
    for item in raw.get("classes", []):
        cls = LabelClass(**item)
        if cls.id in seen:
            raise LabelError(f"duplicate class id: {cls.id}")
        seen.add(cls.id)
        if cls.code_status not in CODE_STATUSES:
            raise LabelError(f"{cls.id}: bad code_status {cls.code_status!r}")
        if cls.code_106 is None and cls.code_status != "unverified":
            raise LabelError(f"{cls.id}: missing code must be marked unverified")
        if cls.code_106 is not None and not isinstance(cls.code_106, int):
            raise LabelError(f"{cls.id}: code_106 must be an integer")
        unknown = _placeholders(cls.text_template_he) - ALLOWED_PLACEHOLDERS
        if unknown:
            raise LabelError(f"{cls.id}: unknown placeholders {sorted(unknown)}")
        classes.append(cls)
    if not classes:
        raise LabelError("no classes defined")
    return classes


def load(path: Path | None = None) -> list[LabelClass]:
    """Load the class table. Class order is the model output order."""
    if path is None:
        text = resources.files("parking_category_model").joinpath("labels.json").read_text("utf-8")
    else:
        text = Path(path).read_text("utf-8")
    return parse(json.loads(text))
