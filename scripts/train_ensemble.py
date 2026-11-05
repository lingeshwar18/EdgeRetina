"""Train two independent, metadata-verified models for ensemble prediction."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import Config
from app.services.training_service import train_centralized

parser = argparse.ArgumentParser()
parser.add_argument("--epochs", type=int, default=2)
parser.add_argument("--batch-size", type=int, default=64)
parser.add_argument("--status-file", type=Path, default=None)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
output = root / "models" / "ensemble"


def update_status(status: str, message: str, progress: int, current_model: str | None = None, metrics=None):
    if not args.status_file:
        return
    args.status_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {"status": status, "message": message, "progress": progress, "current_model": current_model, "metrics": metrics, "output": "", "pid": os.getpid()}
    args.status_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")


metrics = {}
try:
    for index, (architecture, loss) in enumerate((("MobileNetV3Small", "weighted_crossentropy"), ("EfficientNetB0", "focal"))):
        name = architecture.lower()
        progress = 5 if index == 0 else 55
        update_status("running", f"Training {architecture}. This may take several minutes.", progress, architecture, metrics)
        print(f"Training {architecture}...", flush=True)
        metrics[architecture] = train_centralized(root / "data" / "splits", Config.IMAGE_DIR, output / f"{name}.keras", output / f"{name}.json", root / "reports" / "experiments" / f"{name}.json", args.epochs, args.batch_size, True, loss, architecture, "macro_f1", root / "reports" / "experiments" / f"{name}_history.json")
    update_status("completed", "Verified multi-model ensemble is ready.", 100, "Complete", metrics)
except BaseException as exc:
    update_status("failed", str(exc), 0, None, metrics)
    raise
