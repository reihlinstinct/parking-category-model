"""Image preprocessing shared by training and inference.

Re-encoding from pixels drops EXIF (GPS, time, device) before anything is cached or used.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

IMAGE_SIZE = 224
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})


def load_image(source: Path | str | Image.Image, size: int = IMAGE_SIZE) -> np.ndarray:
    """Return a (size, size, 3) uint8 array: orientation fixed, RGB, center-cropped, no metadata."""
    img = Image.open(source) if not isinstance(source, Image.Image) else source
    img = ImageOps.exif_transpose(img).convert("RGB")
    img = ImageOps.fit(img, (size, size), method=Image.Resampling.BILINEAR)
    return np.asarray(img, dtype=np.uint8).copy()


def to_model_input(pixels: np.ndarray) -> np.ndarray:
    """Scale uint8 pixels to float32 in [-1, 1], the range MobileNet-style models expect."""
    if pixels.dtype != np.uint8:
        raise TypeError("expected uint8 pixels")
    return pixels.astype(np.float32) / 127.5 - 1.0


def list_images(folder: Path) -> list[Path]:
    return sorted(p for p in Path(folder).rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS)
