"""Transfer-learning training. Needs the `train` extra (TensorFlow).

Expects a folder with one sub-folder per class id (see labels.json). The folder lives outside
this repository; the code never copies, logs or uploads images.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import cli_spec, labels, preprocessing


def build_model(n_classes: int, size: int = preprocessing.IMAGE_SIZE):
    import tensorflow as tf

    base = tf.keras.applications.MobileNetV3Small(
        input_shape=(size, size, 3), include_top=False, weights="imagenet", pooling="avg"
    )
    base.trainable = False
    inputs = tf.keras.Input(shape=(size, size, 3))
    x = tf.keras.layers.RandomFlip("horizontal")(inputs)
    x = tf.keras.layers.RandomRotation(0.05)(x)
    x = tf.keras.layers.RandomZoom(0.1)(x)
    x = base(x, training=False)
    x = tf.keras.layers.Dropout(0.2)(x)
    outputs = tf.keras.layers.Dense(n_classes, activation="softmax")(x)
    model = tf.keras.Model(inputs, outputs)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def load_dataset(data_dir: Path, class_ids: list[str]):
    """Return (x, y): metadata-free uint8 images and integer labels in labels.json order."""
    import numpy as np

    xs, ys = [], []
    for index, class_id in enumerate(class_ids):
        for path in preprocessing.list_images(data_dir / class_id):
            xs.append(preprocessing.load_image(path))
            ys.append(index)
    if not xs:
        raise SystemExit("no images found")
    return np.stack(xs), np.asarray(ys)


def build_parser() -> argparse.ArgumentParser:
    spec = cli_spec.COMMANDS["train"]
    parser = argparse.ArgumentParser(description=f"{spec.summary}. {spec.description[0]}")
    for opt in spec.options:
        kwargs: dict = {"help": opt.help, "required": opt.required}
        if opt.flag == "--data-dir" or opt.flag == "--out":
            kwargs["type"] = Path
        elif opt.flag in ("--epochs", "--seed"):
            kwargs["type"] = int
        elif opt.flag == "--val-split":
            kwargs["type"] = float
        else:  # pragma: no cover - defensive
            raise ValueError(f"unmapped option type: {opt.flag}")
        defaults = {"--epochs": 10, "--val-split": 0.2, "--seed": 0}
        if opt.flag in defaults:
            kwargs["default"] = defaults[opt.flag]
        parser.add_argument(opt.flag, dest=opt.flag.lstrip("-").replace("-", "_"),
                            metavar=opt.metavar, **kwargs)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    import numpy as np

    classes = labels.load()
    x, y = load_dataset(args.data_dir, [c.id for c in classes])
    rng = np.random.default_rng(args.seed)
    order = rng.permutation(len(x))
    x, y = x[order], y[order]
    cut = int(len(x) * (1 - args.val_split))
    model = build_model(len(classes))
    model.fit(
        preprocessing.to_model_input(x[:cut]),
        y[:cut],
        validation_data=(preprocessing.to_model_input(x[cut:]), y[cut:]),
        epochs=args.epochs,
    )
    model.save(args.out)


if __name__ == "__main__":
    main()
