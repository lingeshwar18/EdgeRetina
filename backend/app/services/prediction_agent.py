"""Production-style prediction orchestration for the EdgeRetina research app."""
from pathlib import Path

import numpy as np
import tensorflow as tf

from ..config import CLASS_NAMES, Config
from ..models.model_loader import load_verified_model
from .preprocessing import load_and_preprocess, validate_image


class PredictionAgent:
    def __init__(self):
        self._models = None
        self._signature = None
        self._available_models = []

    def _load_models(self):
        current_signature = tuple(sorted(str(path) + str(path.stat().st_mtime_ns) for path in Config.MODEL_PATH.parent.parent.joinpath("ensemble").glob("*.keras"))) if Config.MODEL_PATH.parent.parent.joinpath("ensemble").exists() else ()
        if self._models is not None and self._signature == current_signature:
            return self._models
        ensemble_dir = Config.MODEL_PATH.parent.parent / "ensemble"
        candidates = [(path, path.with_suffix(".json")) for path in sorted(ensemble_dir.glob("*.keras"))] if ensemble_dir.exists() else []
        # Only use the two completed ensemble checkpoints for prediction. Older
        # baseline/federated checkpoints can have incompatible preprocessing and
        # must never silently contaminate the verified ensemble result.
        if not candidates:
            candidates = [(Config.MODEL_PATH, Config.MODEL_METADATA_PATH)]
        loaded = []
        for model_path, metadata_path in candidates:
            try:
                loaded.append(load_verified_model(model_path, metadata_path))
            except (OSError, RuntimeError, ValueError):
                continue
        if not loaded:
            raise RuntimeError("No metadata-verified trained model is available")
        def test_accuracy(item):
            return float(item[1].get("test_metrics", {}).get("accuracy", -1))

        best_model = max(loaded, key=test_accuracy)
        self._models = [best_model]
        self._available_models = [info for _model, info in loaded]
        self._signature = current_signature
        return self._models

    def predict(self, path: Path) -> dict:
        quality = validate_image(path)
        if not quality.get("valid"):
            raise ValueError("Image quality or retinal-content check failed.")
        tensor, _ = load_and_preprocess(path)
        original = np.expand_dims(tensor, axis=0)
        flipped = np.flip(original, axis=2).copy()
        batch = np.concatenate([original, flipped])
        outputs = []
        metadata = []
        for model, info in self._load_models():
            probabilities = np.mean(model.predict(batch, verbose=0), axis=0)
            if not np.all(np.isfinite(probabilities)):
                raise RuntimeError(f"{info.get('architecture', 'Model')} produced invalid prediction probabilities.")
            outputs.append(probabilities)
            metadata.append(info)
        probabilities = np.mean(outputs, axis=0)
        class_id = int(np.argmax(probabilities))
        confidence = float(probabilities[class_id])
        severity_expectation = float(np.dot(probabilities, np.arange(len(CLASS_NAMES))))
        entropy = float(-np.sum(probabilities * np.log(np.clip(probabilities, 1e-8, 1.0))))
        available_models = [{"architecture": info.get("architecture", "unknown"), "test_accuracy": info.get("test_metrics", {}).get("accuracy"), "macro_f1": info.get("test_metrics", {}).get("macro_f1")} for info in self._available_models]
        return {
            "class_id": class_id,
            "class_name": CLASS_NAMES[class_id],
            "confidence": confidence,
            "uncertain": confidence < Config.CONFIDENCE_THRESHOLD or entropy > 1.45,
            "uncertainty": {"entropy": entropy, "severity_expectation": severity_expectation},
            "probabilities": {CLASS_NAMES[index]: float(probabilities[index]) for index in range(len(CLASS_NAMES))},
            "model_source": metadata[0].get("architecture", "EdgeRetina model"),
            "models_used": [info.get("architecture", "unknown") for info in metadata],
            "available_models": available_models,
            "best_model": metadata[0].get("architecture", "EdgeRetina model"),
            "quality": quality,
            "tta": "original + horizontal flip",
        }
