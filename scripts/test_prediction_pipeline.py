"""Run a real prediction against one image from each available label."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import CLASS_NAMES, Config
from app.services.prediction_service import predict_image

if __name__ == "__main__":
    frame = pd.read_csv(Config.CSV_PATH)
    image_column = "id" if "id" in frame.columns else "id_code"
    for label in CLASS_NAMES:
        record = frame[frame.diagnosis == label].iloc[0]
        matches = list(Config.IMAGE_DIR.glob(f"{record[image_column]}.*"))
        result = predict_image(matches[0])
        print(f"Expected: {CLASS_NAMES[label]} | Predicted: {result['class_name']} | Probabilities: {result['probabilities']}")
