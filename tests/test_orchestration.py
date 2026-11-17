"""Synthetic orchestration tests for train/evaluate/export (issue #14).

TensorFlow and model I/O are replaced by fakes: no paid runs, no real
photos and no real weights. Images are tiny synthetic PNGs in tmp_path.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image

from parking_category_model import evaluate, export, labels, train

CLASS_IDS = [c.id for c in labels.load()]


def fake_tf(monkeypatch) -> MagicMock:
    module = MagicMock(name="tensorflow")
    monkeypatch.setitem(sys.modules, "tensorflow", module)
    return module


def make_dataset(root, per_class: int = 2):
    for index, class_id in enumerate(CLASS_IDS):
        folder = root / class_id
        folder.mkdir(parents=True)
        for i in range(per_class):
            Image.new("RGB", (8, 8), (index * 40, i * 80, 120)).save(folder / f"{i}.png")
    return root


def test_train_parser_defaults_and_types():
    args = train.build_parser().parse_args(["--data-dir", "in", "--out", "out"])
    assert args.epochs == 10
    assert args.val_split == 0.2
    assert args.seed == 0
    assert str(args.data_dir) == "in"
    args = train.build_parser().parse_args(
        ["--data-dir", "in", "--out", "out", "--epochs", "3", "--val-split", "0.5", "--seed", "9"]
    )
    assert (args.epochs, args.val_split, args.seed) == (3, 0.5, 9)


def test_train_parser_requires_data_dir_and_out():
    with pytest.raises(SystemExit):
        train.build_parser().parse_args([])


def test_load_dataset_orders_labels_and_pixels(tmp_path):
    make_dataset(tmp_path)
    x, y = train.load_dataset(tmp_path, CLASS_IDS)
    assert x.shape == (len(CLASS_IDS) * 2, 224, 224, 3)
    assert x.dtype == np.uint8
    assert sorted(set(y.tolist())) == list(range(len(CLASS_IDS)))
    # First two rows belong to the first class id, in labels.json order.
    assert y[:2].tolist() == [0, 0]


def test_load_dataset_empty_fails_closed(tmp_path):
    with pytest.raises(SystemExit, match="no images found"):
        train.load_dataset(tmp_path, CLASS_IDS)


def test_build_model_imagenet_base_frozen_and_compiled(monkeypatch):
    tf = fake_tf(monkeypatch)
    model = train.build_model(5)
    tf.keras.applications.MobileNetV3Small.assert_called_once_with(
        input_shape=(224, 224, 3), include_top=False, weights="imagenet", pooling="avg"
    )
    base = tf.keras.applications.MobileNetV3Small.return_value
    assert base.trainable is False
    assert model is tf.keras.Model.return_value
    compile_kwargs = model.compile.call_args.kwargs
    assert compile_kwargs["loss"] == "sparse_categorical_crossentropy"
    assert compile_kwargs["metrics"] == ["accuracy"]


def test_train_main_fits_on_split_and_saves(tmp_path, monkeypatch):
    make_dataset(tmp_path)
    model = MagicMock(name="model")
    monkeypatch.setattr(train, "build_model", lambda n_classes: model)
    out = tmp_path / "model.keras"
    train.main(
        ["--data-dir", str(tmp_path), "--out", str(out), "--epochs", "1", "--val-split", "0.4"]
    )
    model.fit.assert_called_once()
    fit_kwargs = model.fit.call_args.kwargs
    assert fit_kwargs["epochs"] == 1
    x_train, y_train = model.fit.call_args.args
    x_val, y_val = fit_kwargs["validation_data"]
    assert len(x_train) + len(x_val) == len(CLASS_IDS) * 2
    assert len(x_train) == len(y_train) and len(x_val) == len(y_val)
    model.save.assert_called_once_with(out)


def test_evaluate_parser_requires_paths():
    with pytest.raises(SystemExit):
        evaluate.build_parser().parse_args([])


def test_evaluate_main_prints_metrics_json(tmp_path, monkeypatch, capsys):
    make_dataset(tmp_path)
    tf = fake_tf(monkeypatch)
    model = tf.keras.models.load_model.return_value
    n = len(CLASS_IDS)
    model.predict.return_value = np.tile(np.arange(n, dtype=np.float32), (n * 2, 1))
    evaluate.main(["--data-dir", str(tmp_path), "--model", "synthetic.keras"])
    tf.keras.models.load_model.assert_called_once_with(Path("synthetic.keras"))
    report = json.loads(capsys.readouterr().out)
    assert set(report) == {"accuracy", "per_class", "confusion_matrix"}
    assert 0.0 <= report["accuracy"] <= 1.0
    assert len(report["confusion_matrix"]) == n
    assert all(len(row) == n for row in report["confusion_matrix"])
    assert set(report["per_class"]) == set(CLASS_IDS)


def test_export_parser_requires_paths():
    with pytest.raises(SystemExit):
        export.build_parser().parse_args([])


def test_export_main_writes_converted_bytes(tmp_path, monkeypatch):
    tf = fake_tf(monkeypatch)
    converter = tf.lite.TFLiteConverter.from_keras_model.return_value
    converter.convert.return_value = b"synthetic-tflite"
    out = tmp_path / "model.tflite"
    export.main(["--model", "synthetic.keras", "--out", str(out)])
    tf.keras.models.load_model.assert_called_once_with(Path("synthetic.keras"))
    assert converter.optimizations == [tf.lite.Optimize.DEFAULT]
    assert converter.target_spec.supported_types == [tf.float16]
    assert out.read_bytes() == b"synthetic-tflite"
