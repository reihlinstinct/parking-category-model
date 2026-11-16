import io

import numpy as np
from PIL import Image

from parking_category_model import preprocessing


def synthetic_jpeg_with_exif() -> bytes:
    img = Image.new("RGB", (320, 200), (200, 30, 30))
    exif = Image.Exif()
    exif[0x010F] = "synthetic-camera"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def test_output_shape_and_dtype():
    pixels = preprocessing.load_image(Image.new("RGB", (640, 480), "white"))
    assert pixels.shape == (224, 224, 3)
    assert pixels.dtype == np.uint8


def test_input_exif_is_dropped():
    source = Image.open(io.BytesIO(synthetic_jpeg_with_exif()))
    assert source.getexif()
    pixels = preprocessing.load_image(source)
    assert not Image.fromarray(pixels).getexif()


def test_model_input_range():
    arr = preprocessing.to_model_input(np.array([[[0, 127, 255]]], dtype=np.uint8))
    assert arr.dtype == np.float32
    assert arr.min() >= -1.0 and arr.max() <= 1.0


def test_list_images_filters_extensions(tmp_path):
    Image.new("RGB", (8, 8)).save(tmp_path / "a.png")
    (tmp_path / "b.txt").write_text("x")
    assert [p.name for p in preprocessing.list_images(tmp_path)] == ["a.png"]
