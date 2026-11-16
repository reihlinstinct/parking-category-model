import pytest

from parking_category_model import labels


def test_shipped_labels_load():
    classes = labels.load()
    ids = [c.id for c in classes]
    assert ids[:2] == ["sidewalk", "red_white_curb"]
    assert len(ids) == len(set(ids))
    by_id = {c.id: c for c in classes}
    assert by_id["sidewalk"].code_106 == 1145
    assert by_id["red_white_curb"].code_106 == 1144


def test_render_fills_template():
    sidewalk = labels.load()[0]
    text = sidewalk.render(street="S", house_number="1", time="T", plate="P")
    assert "{" not in text


def test_missing_code_must_be_unverified():
    raw = {
        "schema_version": 1,
        "classes": [
            {"id": "a", "code_106": None, "code_status": "verified", "name_he": "x",
             "text_template_he": "x"}
        ],
    }
    with pytest.raises(labels.LabelError):
        labels.parse(raw)


def test_unknown_placeholder_rejected():
    raw = {
        "schema_version": 1,
        "classes": [
            {"id": "a", "code_106": 1, "code_status": "verified", "name_he": "x",
             "text_template_he": "{owner_name}"}
        ],
    }
    with pytest.raises(labels.LabelError):
        labels.parse(raw)


def test_duplicate_ids_rejected():
    item = {"id": "a", "code_106": 1, "code_status": "verified", "name_he": "x",
            "text_template_he": "x"}
    with pytest.raises(labels.LabelError):
        labels.parse({"schema_version": 1, "classes": [item, dict(item)]})
