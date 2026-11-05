"""Run comparable real experiments; each candidate writes its own artifact."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import Config
from app.services.training_service import train_centralized

parser = argparse.ArgumentParser()
parser.add_argument("--epochs", type=int, default=2)
parser.add_argument("--batch-size", type=int, default=64)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
experiments = []
for architecture, loss in (("MobileNetV3Small", "weighted_crossentropy"), ("EfficientNetB0", "focal")):
    name = f"{architecture}_{loss}"
    metrics = train_centralized(root / "data" / "splits", Config.IMAGE_DIR, root / "models" / "experiments" / f"{name}.keras", root / "models" / "experiments" / f"{name}.json", root / "reports" / "experiments" / f"{name}.json", args.epochs, args.batch_size, True, loss, architecture)
    experiments.append({"name": name, "architecture": architecture, "loss": loss, **metrics})
(root / "reports" / "experiments").mkdir(parents=True, exist_ok=True)
(root / "reports" / "experiments" / "results.json").write_text(json.dumps(experiments, indent=2), encoding="utf-8")
print(json.dumps(experiments, indent=2))