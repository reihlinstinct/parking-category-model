"""Export a trained Keras model to TFLite (float16 weights) for the mobile apps."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import cli_spec


def build_parser() -> argparse.ArgumentParser:
    spec = cli_spec.COMMANDS["export"]
    parser = argparse.ArgumentParser(description=f"{spec.summary}. {spec.description[0]}")
    for opt in spec.options:
        parser.add_argument(opt.flag, dest=opt.flag.lstrip("-").replace("-", "_"),
                            metavar=opt.metavar, type=Path, required=opt.required,
                            help=opt.help)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    import tensorflow as tf

    model = tf.keras.models.load_model(args.model)
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float16]
    args.out.write_bytes(converter.convert())


if __name__ == "__main__":
    main()
