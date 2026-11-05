import json
from pathlib import Path

from ..config import CLASS_NAMES, Config, IMAGE_SIZE, PREPROCESSING_VERSION


class ModelValidationError(RuntimeError):
    pass


def load_verified_model(model_path: Path | None = None, metadata_path: Path | None = None):
    model_path = model_path or Config.MODEL_PATH
    metadata_path = metadata_path or Config.MODEL_METADATA_PATH
    if not model_path.exists():
        raise ModelValidationError(f"Trained model not found: {model_path}")
    if not metadata_path.exists():
        raise ModelValidationError(f"Model metadata not found: {metadata_path}")
    with metadata_path.open(encoding="utf-8") as handle:
        metadata = json.load(handle)
    expected = {str(key): value for key, value in CLASS_NAMES.items()}
    if metadata.get("class_names") != expected:
        raise ModelValidationError("Model class mapping does not match the canonical EdgeRetina mapping")
    if metadata.get("num_classes") != len(CLASS_NAMES) or metadata.get("image_size") != list(IMAGE_SIZE):
        raise ModelValidationError("Model metadata has an incompatible output or image size")
    if metadata.get("preprocessing_version") != PREPROCESSING_VERSION or not metadata.get("trained"):
        raise ModelValidationError("Model metadata does not describe a trained compatible model")
    import tensorflow as tf

    model = tf.keras.models.load_model(model_path, compile=False)
    if model.output_shape[-1] != len(CLASS_NAMES):
        raise ModelValidationError("Model output does not contain five class probabilities")
    return model, metadata
