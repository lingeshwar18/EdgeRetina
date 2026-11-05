import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import CLASS_NAMES, Config, IMAGE_SIZE, PREPROCESSING_VERSION, SEED
from app.services.evaluation_service import evaluate_predictions
from app.services.training_service import ImageSequence

root = Path(__file__).resolve().parents[1]
model = tf.keras.models.load_model(Config.MODEL_PATH, compile=False)
test = pd.read_csv(root / "data" / "splits" / "test.csv")
probabilities = model.predict(ImageSequence(test, Config.IMAGE_DIR, batch_size=32), verbose=1)
metrics = evaluate_predictions(test["diagnosis"].astype(int).tolist(), np.argmax(probabilities, axis=1).tolist(), root / "reports" / "metrics" / "centralized.json")
metadata = {"architecture": "MobileNetV3Small", "num_classes": len(CLASS_NAMES), "class_names": {str(key): value for key, value in CLASS_NAMES.items()}, "image_size": list(IMAGE_SIZE), "preprocessing_version": PREPROCESSING_VERSION, "training_seed": SEED, "trained": True, "training_stage": "weighted_head_checkpoint", "test_metrics": metrics}
Config.MODEL_METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
Config.MODEL_METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
print(json.dumps(metrics, indent=2))
