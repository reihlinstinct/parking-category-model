"""Transfer-learning training. Needs the `train` extra (TensorFlow).

Expects a folder with one sub-folder per class id (see labels.json). The folder lives outside
this repository; the code never copies, logs or uploads images.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import labels, preprocessing


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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True, help="private folder, outside git")
    parser.add_argument("--out", type=Path, required=True, help="where to write the .keras file")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

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
