import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import Config
from app.services.training_service import train_centralized

parser = argparse.ArgumentParser()
parser.add_argument("--epochs", type=int, default=2)
parser.add_argument("--batch-size", type=int, default=16)
parser.add_argument("--head-only", action="store_true")
parser.add_argument("--loss", choices=["weighted_crossentropy", "focal"], default="weighted_crossentropy")
parser.add_argument("--architecture", choices=["MobileNetV3Small", "EfficientNetB0"], default="MobileNetV3Small")
parser.add_argument("--criterion", choices=["macro_f1", "accuracy"], default="macro_f1")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
metrics = train_centralized(root / "data" / "splits", Config.IMAGE_DIR, Config.MODEL_PATH, Config.MODEL_METADATA_PATH, root / "reports" / "metrics" / "centralized.json", args.epochs, args.batch_size, not args.head_only, args.loss, args.architecture, args.criterion)
print(metrics)
