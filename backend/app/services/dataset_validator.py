import json
from pathlib import Path

import pandas as pd
from PIL import Image

from ..config import CLASS_NAMES


def validate_dataset(csv_path: Path, image_dir: Path, report_dir: Path) -> dict:
    report_dir.mkdir(parents=True, exist_ok=True)
    result = {"csv_exists": csv_path.exists(), "image_dir_exists": image_dir.exists(), "total": 0, "valid": 0, "invalid": 0, "missing": 0, "corrupt": 0, "duplicate_ids": 0, "class_counts": {str(key): 0 for key in CLASS_NAMES}}
    if not csv_path.exists():
        return result
    frame = pd.read_csv(csv_path)
    image_column = "id" if "id" in frame.columns else "id_code" if "id_code" in frame.columns else None
    if image_column is None or "diagnosis" not in frame.columns:
        raise ValueError("APTOS CSV must contain id or id_code, and diagnosis columns")
    result["total"] = len(frame)
    result["duplicate_ids"] = int(frame[image_column].duplicated().sum())
    for label, count in frame["diagnosis"].value_counts().to_dict().items():
        if int(label) in CLASS_NAMES:
            result["class_counts"][str(int(label))] = int(count)
    rows = []
    for record in frame.to_dict("records"):
        image_id = str(record[image_column])
        path = image_dir / image_id
        if not path.suffix:
            candidates = list(image_dir.glob(f"{image_id}.*"))
            path = candidates[0] if candidates else path
        status = "valid"
        if not path.exists():
            status = "missing"
            result["missing"] += 1
        else:
            try:
                with Image.open(path) as image:
                    image.verify()
            except (OSError, ValueError):
                status = "corrupt"
                result["corrupt"] += 1
        if status == "valid" and int(record["diagnosis"]) in CLASS_NAMES:
            result["valid"] += 1
        else:
            result["invalid"] += 1
        rows.append({"id": image_id, "diagnosis": record["diagnosis"], "status": status, "path": str(path)})
    pd.DataFrame(rows).to_csv(report_dir / "dataset_validation.csv", index=False)
    (report_dir / "dataset_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
