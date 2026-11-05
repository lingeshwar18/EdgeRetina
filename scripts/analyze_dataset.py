import json
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parents[1]
frame = pd.read_csv(root / "data" / "raw" / "train.csv")
label_column = "diagnosis"
id_column = "id" if "id" in frame.columns else "id_code"
splits = {name: pd.read_csv(root / "data" / "splits" / f"{name}.csv") for name in ("train", "val", "test")}
distribution = {str(int(label)): int(count) for label, count in frame[label_column].value_counts().sort_index().items()}
report = {
    "rows": len(frame),
    "unique_ids": int(frame[id_column].nunique()),
    "label_column": label_column,
    "id_column": id_column,
    "class_distribution": distribution,
    "imbalance_ratio_majority_to_minority": max(distribution.values()) / min(distribution.values()),
    "split_sizes": {name: len(value) for name, value in splits.items()},
    "split_class_distribution": {name: {str(int(label)): int(count) for label, count in value[label_column].value_counts().sort_index().items()} for name, value in splits.items()},
}
output = root / "reports" / "validation" / "dataset_analysis.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))