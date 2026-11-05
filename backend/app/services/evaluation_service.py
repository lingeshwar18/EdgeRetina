import json
import math
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, mean_absolute_error, precision_score, recall_score, cohen_kappa_score

from ..config import CLASS_NAMES


def evaluate_predictions(y_true: list[int], y_pred: list[int], output_path: Path | None = None) -> dict:
    qwk = float(cohen_kappa_score(y_true, y_pred, weights="quadratic"))
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_precision": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "qwk": qwk if math.isfinite(qwk) else None,
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=list(CLASS_NAMES)).tolist(),
        "per_class": classification_report(y_true, y_pred, labels=list(CLASS_NAMES), output_dict=True, zero_division=0),
        "support": [int(value) for value in confusion_matrix(y_true, y_pred, labels=list(CLASS_NAMES)).sum(axis=1)],
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
