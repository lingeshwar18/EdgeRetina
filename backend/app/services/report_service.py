import json
import csv
from pathlib import Path


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (OSError, json.JSONDecodeError):
        return None


def _read_csv(path: Path):
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError:
        return []


def load_reports(root: Path) -> dict:
    report = {"histories": {}, "ensemble": {}, "client_distribution": [], "rounds": []}
    for name, path in {
        "centralized": root / "metrics" / "centralized.json",
        "federated": root / "metrics" / "federated.json",
        "dataset": root / "validation" / "dataset_analysis.json",
    }.items():
        report[name] = _read_json(path)

    privacy_path = root / "privacy" / "privacy_results.csv"
    report["privacy"] = privacy_path.read_text(encoding="utf-8") if privacy_path.exists() else None
    for key, filename in {"MobileNetV3Small": "mobilenetv3small", "EfficientNetB0": "efficientnetb0"}.items():
        metadata = _read_json(root.parent / "models" / "ensemble" / f"{filename}.json")
        if metadata and metadata.get("test_metrics"):
            report["ensemble"][key] = metadata["test_metrics"]
        history = _read_json(root / "experiments" / f"{filename}_history.json")
        if history:
            report["histories"][key] = history

    report["histories"]["Centralized baseline"] = _read_json(root / "metrics" / "MobileNetV3Small_history.json") or []
    report["client_distribution"] = _read_csv(root / "federated" / "client_distribution.csv")
    report["rounds"] = _read_json(root / "federated" / "rounds.json") or []
    return report
