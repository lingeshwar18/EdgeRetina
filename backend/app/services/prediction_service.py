from pathlib import Path
from uuid import uuid4

import numpy as np
from PIL import Image

from ..config import CLASS_NAMES, Config
from .prediction_agent import PredictionAgent
from .gradcam_service import gradcam, save_gradcam_overlay


agent = PredictionAgent()


def predict_image(path: Path) -> dict:
    result = agent.predict(path)
    try:
        from ..models.model_loader import load_verified_model
        from .preprocessing import load_and_preprocess
        model, _ = load_verified_model()
        tensor, _ = load_and_preprocess(path)
        heatmap = gradcam(model, np.expand_dims(tensor, axis=0), result["class_id"])
        with Image.open(path) as source:
            original = source.convert("RGB")
        output_dir = Path(__file__).resolve().parents[2] / ".." / "reports" / "gradcam"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{uuid4().hex}.png"
        save_gradcam_overlay(original, heatmap, output_path)
        result["gradcam_path"] = str(output_path)
    except (ValueError, RuntimeError, OSError) as exc:
        result["gradcam_error"] = f"Grad-CAM unavailable: {exc}"
    return result
