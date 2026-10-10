# parking-category-model

[![CI](https://github.com/reihlinstinct/parking-category-model/actions/workflows/ci.yml/badge.svg)](https://github.com/reihlinstinct/parking-category-model/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)

Code to train, evaluate and export (TFLite) a photo-to-category classifier for municipal parking
reports. **This repo contains code only: no photos, no labels tied to photos, no model weights.**
See [docs/PRIVACY.md](docs/PRIVACY.md).

## Layout

| Path | Purpose |
| --- | --- |
| `src/parking_category_model/labels.json` | class id, municipal 106 code, Hebrew name, Hebrew text template |
| `src/parking_category_model/preprocessing.py` | resize, orientation fix, EXIF drop |
| `src/parking_category_model/train.py` | transfer learning (MobileNetV3-Small) |
| `src/parking_category_model/evaluate.py`, `metrics.py` | confusion matrix, per-class precision/recall |
| `src/parking_category_model/export.py` | Keras to TFLite |
| `tools/privacy_guard.py` | CI guard against images, weights, plates, GPS, addresses, secrets |
| `docs/` | model card, privacy rules, [roadmap](docs/ROADMAP.md) |

## Use

```bash
pip install -e ".[dev]"          # tests and lint, no TensorFlow
pytest && ruff check . && python tools/privacy_guard.py

pip install -e ".[train]"        # training needs TensorFlow
python -m parking_category_model.train --data-dir /path/outside/repo/data --out model.keras
python -m parking_category_model.evaluate --model model.keras --data-dir /path/outside/repo/data
python -m parking_category_model.export --model model.keras --out model.tflite
```

The data folder has one sub-folder per class id from `labels.json`. Keep it, and the outputs, out of git.

## Category codes

`code_status` in `labels.json` says how far a code can be trusted: `verified`, `fallback` (nearest
existing code), or `unverified` (a person must choose). Text templates use the placeholders
`{street}`, `{house_number}`, `{time}`, `{plate}`.

## Contributing

One issue per change, one PR per issue, full description in each commit body. CI must be green. Do not
attach photos or real report details to issues or PRs.
