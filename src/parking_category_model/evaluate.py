"""Evaluate a trained model on a private folder laid out like the training data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import labels, metrics, preprocessing
from .train import load_dataset


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    import tensorflow as tf

    classes = labels.load()
    names = [c.id for c in classes]
    x, y = load_dataset(args.data_dir, names)
    model = tf.keras.models.load_model(args.model)
    pred = model.predict(preprocessing.to_model_input(x)).argmax(axis=1)
    matrix = metrics.confusion_matrix(y, pred, len(names))
    print(
        json.dumps(
            {
                "accuracy": metrics.accuracy(matrix),
                "per_class": metrics.per_class_report(matrix, names),
                "confusion_matrix": matrix.tolist(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
