from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance

from ..config import IMAGE_SIZE, PREPROCESSING_VERSION


def _crop_black_border(image: Image.Image) -> Image.Image:
    array = np.asarray(image.convert("RGB"))
    brightness = array.mean(axis=2)
    active = brightness > 8
    if not active.any():
        return image.convert("RGB")
    rows = np.where(active.any(axis=1))[0]
    cols = np.where(active.any(axis=0))[0]
    return image.convert("RGB").crop((cols[0], rows[0], cols[-1] + 1, rows[-1] + 1))


def load_and_preprocess(path: str | Path) -> tuple[np.ndarray, Image.Image]:
    with Image.open(path) as source:
        image = _crop_black_border(source)
        image = image.resize(IMAGE_SIZE, Image.Resampling.BILINEAR)
        image = ImageEnhance.Contrast(image).enhance(1.05)
        rgb = np.asarray(image, dtype=np.float32) / 127.5 - 1.0
    return rgb, image


def validate_image(path: str | Path) -> dict:
    try:
        with Image.open(path) as image:
            rgb = np.asarray(image.convert("RGB"))
        brightness = float(rgb.mean())
        black_border_ratio = float((rgb.mean(axis=2) < 8).mean())
        valid = rgb.shape[0] >= 64 and rgb.shape[1] >= 64 and brightness > 8 and black_border_ratio < 0.98
        return {"valid": valid, "width": int(rgb.shape[1]), "height": int(rgb.shape[0]), "brightness": brightness, "black_border_ratio": black_border_ratio}
    except (OSError, ValueError) as exc:
        return {"valid": False, "error": str(exc)}


def preprocessing_metadata() -> dict:
    return {"version": PREPROCESSING_VERSION, "image_size": list(IMAGE_SIZE), "normalization": "[-1, 1]"}
